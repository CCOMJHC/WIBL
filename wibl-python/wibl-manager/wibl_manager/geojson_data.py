# Data model and REST endpoint to manipulate GeoJSON metadata in the database
#
# When data is being converted into GeoJSON format, it is then uploaded to the archive;
# this data model and associated REST endpoint maintains in the database a list of all
# the files that have been picked up for upload, and their statistics.  The REST API is
# to generate an instance in the database with POST with minimal data when the file is
# first opened, and then update with PUT when the upload is complete.  Timestamps are
# applied at the server for the current time when the initial entry is made, and when
# it is updated (so that we can also get performance metrics out of the database).
#
# Copyright 2023 Center for Coastal and Ocean Mapping & NOAA-UNH Joint
# Hydrographic Center, University of New Hampshire.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

import boto3
import os
import requests
from datetime import datetime, timezone
from flask import abort
from flask_restful import Resource, reqparse, fields, marshal_with

from wibl_manager.app_globals import db
from wibl_manager import ReturnCodes, UploadStatus


# Data model for GeoJSON metadata stored in the database
class GeoJSONDataModel(db.Model):
    """
    Data model for GeoJSON file metadata in the database.

    :param fileid:      Primary key, usually the file's name (assuming that it's a UUID)
    :type fileid:       str
    :param uploadtime:  String representation (ISO format) for when the file was first picked up for upload.  Added
                        automatically by the REST server on POST.
    :type uploadtime:   str
    :param updatetime:  String representation (ISO format) for when the PUT update to the metadata is received. Added
                        automatically by the REST server.
    :type updatetime:   str, optional
    :param notifytime:  String representation (ISO format) for when a notification about any processing failure is sent out.
    :type notifytime:   str, optional
    :param logger:      Unique identifier used for the logger generating the data.
    :type logger:       str, optional
    :param size:        Size of the file in MB.
    :type size:         float
    :param soundings:   Number of processed (output) soundings in the converted file.
    :type soundings:    int, optional
    :param status:      Status indicator for upload of the file to the archive.  Set to 'started' on POST, but can then be
                        updated through PUT to reflect the results of processing.
    :type status:       :enum: `return_codes.UploadStatus`
    :param messages:    Messages returned during processing (usually error/warnings)
    :type messages:     str, optional  
    """
    fileid = db.Column(db.String(40), primary_key=True)
    uploadtime = db.Column(db.String(30))
    updatetime = db.Column(db.String(30))
    notifytime = db.Column(db.String(30))
    logger = db.Column(db.String(80))
    size = db.Column(db.Float, nullable=False)
    soundings = db.Column(db.Integer)
    status = db.Column(db.Integer)
    messages = db.Column(db.String(1024))

    def __repr__(self):
        """
        Generate a simple text version of the data model for debugging.
        """
        return f'file {self.fileid}, size {self.size} MB at {self.uploadtime} for logger {self.logger} with {self.soundings} observations, status={self.status}'

# Arguments passable to the GeoJSON end-point to POST a new record's metadata
GeoJSON_Args = reqparse.RequestParser()
GeoJSON_Args.add_argument('size', type=float, help='Size of the GeoJSON file in MB.', required=True)

# Arguments passable to the GeoJSON end-point for PUT updates to an existing file's metadata
GeoJSON_Update_Args = reqparse.RequestParser()
GeoJSON_Update_Args.add_argument('notifyTime',type=str, help='Time of upload failure notification.')
GeoJSON_Update_Args.add_argument('logger', type=str, help='Logger name (unique ID) value.')
GeoJSON_Update_Args.add_argument('size', type=float, help='Size of the GeoJSON file in MB.')
GeoJSON_Update_Args.add_argument('soundings', type=int, help='Number of soundings in the file.')
GeoJSON_Update_Args.add_argument('status', type=int, help='Status of archive upload attempt.')
GeoJSON_Update_Args.add_argument('messages', type=str, help='Messages generated during upload.')

# Data mapping for marshalling GeoJSONDataModel for transfer
geojson_resource_fields = {
    'fileid':       fields.String,
    'uploadtime':   fields.String,
    'updatetime':   fields.String,
    'notifytime':   fields.String,
    'logger':       fields.String,
    'size':         fields.Float,
    'soundings':    fields.Integer,
    'status':       fields.Integer,
    'messages':     fields.String
}

data_rest_url = os.environ['MANAGEMENT_URL'] + 'data/'

class GeoJSONData(Resource):
    """
    A RESTful endpoint for manipulating metadata on GeoJSON files in a local database.  The design here
    expects that the client will generate a POST when the file is first picked up for upload to the archive,
    and then update with PUT when the upload is complete (and update the status indicator).  GET is provided
    for individual file extraction (or "all" for an index of all files currently in the database), and
    DELETE is provided to remove metadata entries.
    """
    @marshal_with(geojson_resource_fields)
    def get(self, fileid):
        """
        Lookup for a single file's metadata, or all files if :param: `fileid` is "all"

        :param fileid:  Filename to look up (typically a UUID)
        :type fileid:   str
        :return:        Metadata instance for the file or list of all file, or NOT_FOUND if the record doesn't exist
        :rtype:         tuple   The marshalling decorator should convert to JSON-serialisable form.
        """
        if fileid == 'all':
            result = db.session.query(GeoJSONDataModel).all()
        else:
            result = GeoJSONDataModel.query.filter_by(fileid=fileid).first()
        return result

    @marshal_with(geojson_resource_fields)
    def post(self, fileid):
        """
        Initial creation of a metadata entry for a GeoJSON file being uploaded.  Only the 'size' parameter is
        required at creation time; the server automatically sets the 'uploadtime' element to the current time
        and defaults the other values in the metadata to "unknown" states that are recognisable.

        :param fileid:  Filename to look up (typically a UUID)
        :type fileid:   str
        :return:        The initial state of the metadata for the file and RECORD_CREATED, or RECORD_CONFLICT if
                        the record already exists.
        :rtype:         tuple   The marchalling decorator should convert to JSON-serliasable form.
        """
        result = GeoJSONDataModel.query.filter_by(fileid=fileid).first()
        if result:
            abort(ReturnCodes.RECORD_CONFLICT.value, description='That GeoJSON file already exists in the database; use PUT to update.')
        args = GeoJSON_Args.parse_args()
        timestamp = datetime.now(timezone.utc).isoformat()
        geojson_file = GeoJSONDataModel(fileid=fileid, uploadtime=timestamp, updatetime='Unknown', notifytime='Unknown',
                                        logger='Unknown', size=args['size'],
                                        soundings=-1, status=UploadStatus.UPLOAD_STARTED.value)
        # Add to the dashboard statistics
        requests.post(data_rest_url + "GeojsonFileCount")

        db.session.add(geojson_file)
        db.session.commit()

        return geojson_file, ReturnCodes.RECORD_CREATED.value

    @marshal_with(geojson_resource_fields)
    def put(self, fileid):
        """
        Update of the metadata for a single GeoJSON file after upload.  All variables can be set through the data
        parameters in the request, although the server automatically sets the 'updatetime' component to the current
        UTC time for the call.  All of the metadata elements are optional.

        :param fileid:  Filename to look up (typically a UUID)
        :type fileid:   str
        :return:        The updated state of the metadata for the file and RECORD_CREATED, or NOT_FOUND if the
                        record doesn't exist.
        :rtype:         tuple   The marshalling decorator should convert to JSON-serliasable form.
        """
        args = GeoJSON_Update_Args.parse_args()
        geojson_file = GeoJSONDataModel.query.filter_by(fileid=fileid).first()
        if not geojson_file:
            abort(ReturnCodes.FILE_NOT_FOUND.value, description='That GeoJSON file does not exist in database; use POST to add.')
        timestamp = datetime.now(timezone.utc).isoformat()
        geojson_file.updatetime = timestamp
        if args['notifyTime']:
            geojson_file.notifytime = args['notifyTime']
        if args['logger']:
            geojson_file.logger = args['logger']
        if args['size']:
            geojson_file.size = args['size']
        if args['soundings']:
            geojson_file.soundings = args['soundings']
        if args['status']:
            # File always starts with status 0
            # So if the status changes to 1 or 2, add it to the data.
            match args['status']:
                case 1:
                    requests.post(data_rest_url + "SubmittedTotal")
                case 2:
                    requests.post(data_rest_url + "UploadFailedTotal")
            geojson_file.status = args['status']
        if args['messages']:
            geojson_file.messages = args['messages'][:1024]
        db.session.commit()
        return geojson_file, ReturnCodes.RECORD_CREATED.value

    def delete(self, fileid):
        """
        Remove a metadata record from the database for a single file.

        :param fileid:  Filename to look up (typically a UUID)
        :type fileid:   str
        :return:        RECORD_DELETED or NOT_FOUHD if the record doesn't exist.
        :rtype:         int   The marshalling decorator should convert to JSON-serliasable form.
        
        """
        if fileid == 'all':
            db.session.query(GeoJSONDataModel).delete()
            db.session.commit()
            return ReturnCodes.RECORD_DELETED.value

        geojson_file = GeoJSONDataModel.query.filter_by(fileid=fileid).first()
        if not geojson_file:
            abort(ReturnCodes.FILE_NOT_FOUND.value, description='That GeoJSON file does not exist in the database, and therefore cannot be deleted.')
        db.session.delete(geojson_file)
        db.session.commit()

        # delete on the cloud
        # s3 = boto3.client('s3',
        #               endpoint_url="http://localstack:4566",
        #               use_ssl=False,
        #               aws_access_key_id='test',
        #               aws_secret_access_key='test')
        # s3.delete_object(Bucket='geojson-test', Key=fileid)

        return ReturnCodes.RECORD_DELETED.value
