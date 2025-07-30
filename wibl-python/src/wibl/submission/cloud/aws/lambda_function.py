## \file lambda_function.py
#  \brief AWS Lambda to transfer a processed (GeoJSON) S3 file to DCDB
#
# This is designed to run as an AWS Lambda, responding to a file appearing in a given
# S3 bucket.  The script pulls the file locally, then transmits to DCDB via their
# submission API.
#
# Copyright 2021 Center for Coastal and Ocean Mapping & NOAA-UNH Joint
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

import os
import json
from typing import Dict, Any

import requests
import boto3

# Local modules
from wibl.core import getenv
import wibl.core.config as conf
import wibl.core.datasource as ds
import wibl.core.notification as nt
from wibl.submission.cloud.aws import get_config_file
from wibl_manager import ManagerInterface, MetadataType, GeoJSONMetadata, ReturnCodes, UploadStatus

s3 = boto3.resource('s3')


## Helper function to read a local file with an AWS Lambda event in JSON format
#
# For local testing of the code, you need to provide a simulated Lambda event.  This helper
# function can be used to parse a JSON file (format as for the Lambda, best downloaded from
# AWS directly) and ready it for use in the handler.
#
# \param event_file Filename for the local file to read and parse
# \return JSON dictionary from the specified file
def read_local_event(event_file: str) -> Dict:
    """For local testing, you need to simulate an AWS Lambda event stucture to give the code something
       to do.  You can download the JSON for a typical event from the AWS Lambda console and store it
       locally.  This helper function can be called interactively to load this information.
    """
    with open(event_file) as f:
        event = json.load(f)
    return event

## Send a specified GeoJSON dictionary to the user's specified end-point
# TODO: This should be moved outside of the cloud/aws package since it is used by non-AWS code (e.g., dcdb_upload)
# Manage the process for formatting the POST request to DCDB's submission API, transmitting the file into
# the DCDB incoming buffers.  Among other things, this makes sure that the provider identification is
# embedded in the unique identifier (since DCDB uses this to work out where to route the data).  A local
# mode is also provided so you can test the upload without having to be connected, or annoy DCDB.
#
# \param source_info    Metadata for the current file (sourceID, logger name, soundings, etc.)
# \param provider_id    DCDB recognition code for the person authorising the upload
# \param provider_auth  DCDB authorisation key for upload
# \param local_file     Filename for the local GeoJSON file to transmit
# \param config         Configuration dictionary
# \return True if the upload succeeded, otherwise False

def transmit_geojson(source_info: Dict[str,Any], provider_id: str, provider_auth: str, local_file: str,
                     config: Dict[str,Any]) -> bool:
    auth_token: str = provider_auth.strip()
    headers = {
        'x-auth-token': auth_token
    }
    # The unique ID that we provide to DCDB must be preceeded by our provider ID and a hyphen.
    # This should happen before the code gets to here, but just in case, we enforce this requirement.
    if provider_id not in source_info['sourceID']:
        dest_uniqueID = provider_id + '-' + source_info['sourceID']
    else:
        dest_uniqueID = source_info['sourceID']

    filesize = os.path.getsize(local_file)/(1024.0*1024.0)
    filename = os.path.split(local_file)[-1]
    if filename == '':
        # TODO: Should the upload fail if we can't report status to the manager?
        print(f'warning: unable to determine of file to upload. local_file was: {local_file}.')
    manager: ManagerInterface = ManagerInterface(MetadataType.GEOJSON_METADATA, filename, config['verbose'])
    if not manager.register(filesize):
        # TODO: Should the upload fail if we can't report status to the manager?
        print('warning: failed to register file with REST management service.')
    meta: GeoJSONMetadata = GeoJSONMetadata()
    meta.size = filesize
    meta.logger = source_info["logger"]
    meta.soundings = source_info["soundings"]
    meta.status = UploadStatus.UPLOAD_STARTED.value
    
    if config['verbose']:
        print(f'Source ID is: {source_info["sourceID"]}; ' + 
              f'Destination object uniqueID is: {dest_uniqueID}; ' +
              f'Authorisation token is: {auth_token}')

    files = {
        'file': (local_file, open(local_file, 'rb')),
        'metadataInput': (None, '{\n    "uniqueID": "' + dest_uniqueID + '"\n}')
    }

    upload_point = getenv('UPLOAD_POINT')

    if config['verbose']:
        print(f'Transmitting for source ID {source_info["sourceID"]} to {upload_point} as destination ID {dest_uniqueID}.')

    response = requests.post(upload_point, headers=headers, files=files)

    if config['verbose']:
        print(f'Submission status for file {local_file} was {response.status_code}')
        print(f'\tResponse text was: {response.text}')

    json_response = response.json()

    if config['verbose']:
        print(f'POST response is {json_response}')
    try:
        json_code = json_response['success']
        if json_code:
            rc = True
            meta.status = UploadStatus.UPLOAD_SUCCESSFUL.value
        else:
            rc = False
            meta.status = UploadStatus.UPLOAD_FAILED.value
            manager.logmsg(f'error: DCDB responded {json_response}')

    except json.decoder.JSONDecodeError:
        rc = False
        meta.status = UploadStatus.UPLOAD_FAILED.value
        manager.logmsg(f'error: DCDB responded {json_response}')

    manager.update(meta)
    return rc


def lambda_handler(event, context):
    try:
        config = conf.read_config(get_config_file())
    except conf.BadConfiguration:
        return {
            'statusCode':   ReturnCodes.FAILED.value,
            'body':         'Bad configuration file.'
            }
    
    # Construct a data source to handle the input items, and a controller to manage the transmission of
    # data from buckets to local files.  We instanatiate the DataSource and CloudController sub-classes
    # explicitly, since this code is also specific to AWS.
    # When using direct S3 triggers or custom WIBL lambda-generated SNS event payloads, use:
    source = ds.AWSSource(event, config)
    # When using S3->SNS triggers, use:
    #source = ds.AWSSourceSNSTrigger(event, config)
    controller = ds.AWSController(config)
    notifier = nt.SNSNotifier(getenv('NOTIFICATION_ARN'))

    # We obtain the DCDB provider uniqueID (i.e., the six-letter identifier for the Trusted Node) and
    # authorisation string (the shared secret for authentication) from the environment; they should be
    # stored there when the Lambda is created.
    provider_id = getenv('PROVIDER_ID')
    provider_auth = getenv('PROVIDER_AUTH')
    
    # Loop through all of the source files in the incoming bucket, attempting to upload each in turn, and
    # keeping track of those that succeed and fail.
    item = source.nextSource()
    succeeded = []
    failed = []
    while item is not None:
        local_file, source_info = controller.obtain(item)
        print(f'Source information is {source_info}.')
        if not source_info['sourceID']:
            if config['verbose']:
                print(f'Failed to transfer item {item} because it has no SourceID specified.')
            failed.append(item)
        else:
            rc = transmit_geojson(source_info, provider_id, provider_auth, local_file, config)
            if rc:
                if config['verbose']:
                    print(f'Succeeded in transferring item {item}')
                succeeded.append(item)
                item.dest_size = item.source_size
                notifier.notify(item)
            else:
                if config['verbose']:
                    print(f'Failed to transfer item {item}')
                failed.append(item)
        item = source.nextSource()
    
    # Status report for the user
    if failed:
        status_code = ReturnCodes.FAILED.value
    else:
        status_code = ReturnCodes.OK.value
    n_succeed = len(succeeded)
    n_fail = len(failed)
    n_total = n_succeed + n_fail
    rtn = {
        'statusCode':   status_code,
        'body':         f'Success on {n_succeed}, failed on {n_fail}; total {n_total}.'
    }

    return rtn
