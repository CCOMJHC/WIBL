# WIBL file metadata model and RESTful endpoint definitions.
#
# When data is first uploaded into the cloud as WIBL files, we need to keep track of
# whether the data is succesfully processed, and how long it takes.  The data model and
# associated REST endpoint here allow for manipulation of metadata in a local database.
# The REST API is to generate an instance in the database with POST with minimal data
# when the file is first opened, and then update with PUT when the upload is complete.
# Timestamps are applied at the server for the current time when the initial entry is
# made, and when it is updated (so that we can also get performance metrics out of
# the database).
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

from datetime import datetime, timezone
from flask import abort
from flask_restful import Resource, reqparse, fields, marshal_with
import boto3

from wibl_manager.app_globals import db, s3_client
from wibl_manager import ReturnCodes, ProcessingStatus


class WIBLDataModel(db.Model):
    """
    Data model for WIBL file metadata during processing, held in a suitable database (controlled externally)

    Attributes:
    :param fileid:          Primary key, usually the file's name (assuming that it's a UUID)
    :type fileid:           str
    :param processtime:     String representation (ISO format) for when the file was first picked up for processing.  Added
                            automatically by the REST server on POST.
    :type processtime:      str
    :param updatetime:      String representation (ISO format) for when the PUT update to the metadata is received. Added
                            automatically by the REST server.
    :type updatetime:       str, optional
    :param notifytime:      String representation (ISO format) for when a notification about any processing failure is sent out.
    :type notifytime:       str, optional
    :param logger:          Unique identifier used for the logger generating the data.
    :type logger:           str, optional
    :param platform:        Name of the platform being used to host the logger (may be anonymous).
    :type platform:         str, optional
    :param size:            Size of the file in MB.
    :type size:             float
    :param observations:    Number of raw observations of depth in the file.
    :type observations:     int, optional
    :param soundings:       Number of processed (output) soundings in the converted file.
    :type soundings:        int, optional
    :param starttime:       String representation (ISO format) for the earliest output sounding in the processed file.
    :type starttime:        str, optional
    :param endtime:         String representation (ISO format) for the latest output sounding in the processed file.
    :type endtime:          str, optional
    :param status:          Status indicator for processing of the file to GeoJSON.  Set to 'started' on POST, but can then be
                            updated through PUT to reflect the results of processing.
    :type status:           :enum: `return_codes.ProcessStatus`
    :param messages:        Messages returned during processing (usually error/warnings)
    :type messages:         str, optional
    """
    fileid = db.Column(db.String(40), primary_key=True)
    processtime = db.Column(db.String(30))
    updatetime = db.Column(db.String(30))
    notifytime = db.Column(db.String(30))
    logger = db.Column(db.String(80))
    platform = db.Column(db.String(80))
    size = db.Column(db.Float, nullable=False)
    observations = db.Column(db.Integer)
    soundings = db.Column(db.Integer)
    starttime = db.Column(db.String(30))
    endtime = db.Column(db.String(30))
    status = db.Column(db.Integer)
    messages = db.Column(db.String(1024))

    def __repr__(self):
        """
        Generate a simple string representation of the data model for debugging purposes.
        """
        return f'file {self.fileid} at {self.processtime} for logger {self.logger} on {self.platform} size {self.size} MB, status={self.status}.'

# Request parser to handle POST requests on the WIBL end-point (which require only a size to start with)
WIBL_Args = reqparse.RequestParser()
WIBL_Args.add_argument('size', type=float, help='Size of the WIBL file in MB.', required=True)

# Request parser to hanndle PUT requests on an existing WIBL metadata record, after processing is completed
WIBL_Update_Args = reqparse.RequestParser()
WIBL_Update_Args.add_argument('logger', type=str, help='Logger name (unique ID) value.')
WIBL_Update_Args.add_argument('platform', type=str, help='Name of the observing platform.')
WIBL_Update_Args.add_argument('size', type=float, help='Size of the WIBL file in MB.')
WIBL_Update_Args.add_argument('observations', type=int, help='Number of soundings in the file.')
WIBL_Update_Args.add_argument('soundings', type=int, help='Number of soundings after processing.')
WIBL_Update_Args.add_argument('startTime', type=str, help='First output sounding time.')
WIBL_Update_Args.add_argument('endTime', type=str, help='Last output sounding time.')
WIBL_Update_Args.add_argument('notifyTime', type=str, help='Time of processing failure notification.')
WIBL_Update_Args.add_argument('status', type=int, help='Status of conversion code run.')
WIBL_Update_Args.add_argument('messages', type=str, help='Messages generated during processing.')

# Data dictionary for marshalling the objects returned from the database (WIBLDataModel) into JSON
wibl_resource_fields = {
    'fileid':           fields.String,
    'processtime':      fields.String,
    'updatetime':       fields.String,
    'notifytime':       fields.String,
    'logger':           fields.String,
    'platform':         fields.String,
    'size':             fields.Float,
    'observations':     fields.Integer,
    'soundings':        fields.Integer,
    'starttime':        fields.String,
    'endtime':          fields.String,
    'status':           fields.Integer,
    'messages':         fields.String
}

class WIBLData(Resource):
    """
    RESTful end-point for manipulating the WIBL data file database component.  The design here assumes
    that the user will use POST to generate an initial metadata entry when the file is first picked up
    for processing, and then update it with PUT when the results of the processing are known.  GET is
    provided for metadata lookup (GET 'all' for everything) and DELETE for file removal.
    """
    @marshal_with(wibl_resource_fields)
    def get(self, fileid):
        """
        Lookup for a single file's metadata, or all files if :param: `fileid` is "all".

        :param fileid:  Filename to look up (typically a UUID)
        :type fileid:   str
        :return:        Metadata instance for the file or list of all file, or NOT_FOUND if the record doesn't exist
        :rtype:         tuple   The marshalling decorator should convert to JSON-serialisable form.
        """
        if fileid == 'all':
            result = db.session.query(WIBLDataModel).all()
            # TODO: Add check for if result is None, in which case, set to empty list
            #   As it stands now, if there are no records, 'all' results in 404, which seems
            #   wrong.
        else:
            result = WIBLDataModel.query.filter_by(fileid=fileid).first()
        return result

    @marshal_with(wibl_resource_fields)
    def post(self, fileid):
        """
        Initial creation of a metadata entry for a WIBL file being processed.  Only the 'size' parameter is
        required at creation time; the server automatically sets the 'processtime' element to the current time
        and defaults the other values in the metadata to "unknown" states that are recognisable.

        :param fileid:  Filename to look up (typically a UUID)
        :type fileid:   str
        :return:        The initial state of the metadata for the file and RECORD_CREATED, or RECORD_CONFLICT if
                        the record already exists.
        :rtype:         tuple   The marchalling decorator should convert to JSON-serliasable form.
        """
        result = WIBLDataModel.query.filter_by(fileid=fileid).first()
        if result:
            abort(ReturnCodes.RECORD_CONFLICT.value, description='That WIBL file already exists in the database; use PUT to update.')
        args = WIBL_Args.parse_args()
        timestamp = datetime.now(timezone.utc).isoformat()
        wibl_file = WIBLDataModel(fileid=fileid, processtime=timestamp, updatetime='Unknown', notifytime='Unknown',
                                  logger='Unknown', platform='Unknown', size=args['size'],
                                  observations=-1, soundings=-1, starttime='Unknown', endtime='Unknown',
                                  status=ProcessingStatus.PROCESSING_STARTED.value, messages='')
        db.session.add(wibl_file)
        db.session.commit()

        # post on the cloud
        # s3_client.put_object(Body=wibl_file, Bucket='wibl-test', Key=fileid)
        return wibl_file, ReturnCodes.RECORD_CREATED.value
    
    @marshal_with(wibl_resource_fields)
    def put(self, fileid):
        """
        Update of the metadata for a single WIBL file after processing.  All variables can be set through the data
        parameters in the request, although the server automatically sets the 'updatetime' component to the current
        UTC time for the call.  All of the metadata elements are optional.

        :param fileid:  Filename to look up (typically a UUID)
        :type fileid:   str
        :return:        The updated state of the metadata for the file and RECORD_CREATED, or NOT_FOUND if the
                        record doesn't exist.
        :rtype:         tuple   The marshalling decorator should convert to JSON-serlisable form.
        """
        args = WIBL_Update_Args.parse_args()
        wibl_file = WIBLDataModel.query.filter_by(fileid=fileid).first()
        if not wibl_file:
            abort(ReturnCodes.FILE_NOT_FOUND.value, description='That WIBL file does not exist in database; use POST to add.')
        timestamp = datetime.now(timezone.utc).isoformat()
        wibl_file.updatetime = timestamp
        if args['notifyTime']:
            wibl_file.notifytime = args['notifyTime']
        if args['logger']:
            wibl_file.logger = args['logger']
        if args['platform']:
            wibl_file.platform = args['platform']
        if args['size']:
            wibl_file.size = args['size']
        if args['observations']:
            wibl_file.observations = args['observations']
        if args['soundings']:
            wibl_file.soundings = args['soundings']
        if args['startTime']:
            wibl_file.starttime = args['startTime']
        if args['endTime']:
            wibl_file.endtime = args['endTime']
        if args['status']:
            wibl_file.status = args['status']
        if args['messages']:
            wibl_file.messages = args['messages'][:1024]
        db.session.commit()

        # s3_client.put_object(Body=wibl_file, Bucket='wibl-test', Key=fileid)

        return wibl_file, ReturnCodes.RECORD_CREATED.value

    def delete(self, fileid):
        """
        Remove a metadata record from the database for a single file.

        :param fileid:  Filename to look up (typically a UUID)
        :type fileid:   str
        :return:        RECORD_DELETED or NOT_FOUHD if the record doesn't exist.
        :rtype:         int   The marshalling decorator should convert to JSON-serliasable form.
        
        """

        if fileid == 'all':
            db.session.query(WIBLDataModel).delete()
            db.session.commit()   
            return ReturnCodes.RECORD_DELETED.value
        
        wibl_file = WIBLDataModel.query.filter_by(fileid=fileid).first()
        if not wibl_file:
            abort(ReturnCodes.FILE_NOT_FOUND.value, description='That WIBL file does not exist in the database, and therefore cannot be deleted.')
        db.session.delete(wibl_file)
        db.session.commit()

        # delete on the cloud
        # s3_client.delete_object(Bucket='wibl-test', Key=fileid)

        return ReturnCodes.RECORD_DELETED.value
