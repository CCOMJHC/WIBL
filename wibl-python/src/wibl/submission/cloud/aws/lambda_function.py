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
import traceback

# Local modules
from wibl.core import getenv
import wibl.core.config as conf
import wibl.core.datasource as ds
import wibl.core.notification as nt
from wibl.submission.cloud.aws import get_config_file
from wibl_manager import ManagerInterface, MetadataType, GeoJSONMetadata, ReturnCodes, GeoJSONStatus

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

def transmit_geojson(source_info: Dict[str, Any], provider_id: str, provider_auth: str, local_file: str,
                     config: Dict[str, Any]) -> bool:
    is_local = config['local']
    is_verbose = config['verbose']

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

    filename = os.path.split(local_file)[-1]
    if filename == '':
        print(f'warning: unable to determine of file to upload. local_file was: {local_file}.')
    manager: ManagerInterface = ManagerInterface(MetadataType.GEOJSON_METADATA, filename, is_verbose)

    rc, meta = manager.lookup()
    if not rc:
        if is_verbose:
            print(f'error: failed to find metadata on {filename} from database manager.')
        return rc

    clearedStatus = meta.status & GeoJSONStatus.EMPTY_UPLOAD.value
    meta.status = clearedStatus | GeoJSONStatus.UPLOAD_STARTED.value

    if is_verbose:
        print(f'Source ID is: {source_info["sourceID"]}; ' +
              f'Destination object uniqueID is: {dest_uniqueID}; ' +
              f'Authorisation token is specified? {auth_token is not None and len(auth_token) > 0}')

    files = {
        'file': (local_file, open(local_file, 'rb')),
    }
    payload = {
        'metadataInput': f'{{"uniqueID":"{dest_uniqueID}"}}'
    }

    upload_point = getenv('UPLOAD_POINT')

    if is_local:
        print(f'Local mode: Transmitting to {upload_point} for source ID {source_info["sourceID"]} with '
              f'destination ID {dest_uniqueID}.')
    else:
        if is_verbose:
            print(f'Transmitting for source ID {source_info["sourceID"]} to {upload_point} '
                  f'as destination ID {dest_uniqueID}.')

    response = requests.post(upload_point.rstrip('/'), headers=headers, files=files, data=payload)
    if is_verbose:
        print(f'Submission status for file {local_file} was {response.status_code}; '
              f'Response text was: {response.text}')
    try:
        json_response = response.json()
        if is_verbose:
            print(f'POST response is {json_response}')
        json_code = json_response['success']
        if json_code:
            rc = True
            meta.status = clearedStatus | GeoJSONStatus.UPLOAD_SUCCESSFUL.value
            submission_ids = ', '.join(json_response['submissionIds'])
            manager.logmsg(f'submission id(s): {submission_ids}')
            if is_local:
                print(f"Submission ID(s) were: {submission_ids}")
        else:
            rc = False
            meta.status = clearedStatus | GeoJSONStatus.UPLOAD_FAILED.value
            manager.logmsg(f'error: DCDB responded {json_response}')
    except (json.decoder.JSONDecodeError, KeyError) as e:
        rc = False
        meta.status = clearedStatus | GeoJSONStatus.UPLOAD_FAILED.value
        manager.logmsg(f'error: DCDB responded {response.text}')
        manager.logmsg(f'error: {type(e).__name__}: {e}')
        manager.logmsg(f'error: failure trace:\n{traceback.format_exc()}')

    manager.update(meta)
    return rc


def lambda_handler(event, context):
    try:
        config = conf.read_config(get_config_file())
    except conf.BadConfiguration:
        return {
            'statusCode': ReturnCodes.FAILED.value,
            'body': 'Bad configuration file.'
        }

    is_verbose = config['verbose']

    # Construct a data source to handle the input items, and a controller to manage the transmission of
    # data from buckets to local files. We instantiate the DataSource and CloudController sub-classes
    # explicitly, since this code is also specific to AWS.
    # When using direct S3 triggers or custom WIBL lambda-generated SNS event payloads, use:
    source = ds.AWSSource(event, config)
    # When using S3->SNS triggers, use:
    # source = ds.AWSSourceSNSTrigger(event, config)
    controller = ds.AWSController(config)
    notifier = nt.SNSNotifier(getenv('NOTIFICATION_ARN'))

    # We obtain the DCDB provider uniqueID (i.e., the six-letter identifier for the Trusted Node) from the environment
    # and authorisation string (the shared secret for authentication) from AWS SSM
    provider_id = getenv('PROVIDER_ID')

    ssm = boto3.client('ssm')
    provider_auth = ssm.get_parameter(
        Name=getenv('PROVIDER_PATH'),
        WithDecryption=True
    )['Parameter']['Value']

    # Loop through all the source files in the incoming bucket, attempting to upload each in turn, and
    # keeping track of those that succeed and fail.
    item = source.nextSource()
    succeeded = []
    failed = []
    while item is not None:
        local_file, source_info = controller.obtain(item)
        print(f'Source information is {source_info}.')
        if not source_info['sourceID']:
            if is_verbose:
                print(f'Failed to transfer item {item} because it has no SourceID specified.')
            failed.append(item)
        else:
            rc = transmit_geojson(source_info, provider_id, provider_auth, local_file, config)
            if rc:
                if is_verbose:
                    print(f'Succeeded in transferring item {item}')
                succeeded.append(item)
                item.dest_size = item.source_size
                notifier.notify(item)
            else:
                if is_verbose:
                    print(f'Failed to transfer item {item}')
                failed.append(item)
        item = source.nextSource()
