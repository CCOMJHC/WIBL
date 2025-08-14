# lambda_function.py
#
# This allows an AWS Lambda to be generated to run schema-based JSON metadata validation
# against GeoJSON files.  The Lambda is designed to be triggered by an AWS Simple
# Notification Service (SNS) event.
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

import os
from typing import Dict, Any

from csbschema import validate_data, DEFAULT_VALIDATOR_VERSION

import wibl.core.datasource as ds
import wibl.core.notification as nt
from wibl_manager import ManagerInterface, ReturnCodes, ProcessingStatus, MetadataType
from wibl.core import getenv
import wibl.core.config as conf
from wibl.validation.cloud.aws import get_config_file

def validate_metadata(local_file: str, config: Dict[str,Any]) -> bool:
    verbose = config['verbose']

    # Although we need to check the GeoJSON file for metadata, we need to update the status of the
    # WIBL file, since failed metadata is really a processing failure.  Hence, we need to generate
    # the WIBL file name from the GeoJSON file name (by subtracting the extension)
    source_file_path = local_file.replace('.json', '.wibl')
    source_file_name = os.path.split(source_file_path)[-1]
    if source_file_name == '':
        raise ValueError(f"Unable to determine filename from source file path: '{source_file_path}'")

    manager: ManagerInterface = ManagerInterface(MetadataType.WIBL_METADATA, source_file_name, config['verbose'])
    rc, meta = manager.lookup()
    if not rc:
        if verbose:
            print(f'error: failed to find metadata on {source_file_name} from database manager.')
        return rc

    if verbose:
        print(f'info: Validating metadata in {source_file_name} for schema version {DEFAULT_VALIDATOR_VERSION}.')
    
    rc, validate_info = validate_data(local_file)
    if rc:
        meta.status = ProcessingStatus.PROCESSING_SUCCESSFUL.value
    else:
        meta.status = ProcessingStatus.PROCESSING_FAILED.value
        if config['local']:
            print(validate_info.__str__())
        manager.logmsg(validate_info.__str__())

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

    if config['verbose']:
        print(f"event: {event}")
        print(f"notifier: {getenv('NOTIFICATION_ARN')}")

    # When using direct S3 triggers or custom WIBL lambda-generated SNS event payloads, use:
    source = ds.AWSSource(event, config)
    # When using S3->SNS triggers, use:
    # source = ds.AWSSourceSNSTrigger(event, config)
    controller = ds.AWSController(config)
    notifier = nt.SNSNotifier(getenv('NOTIFICATION_ARN'))

    # Since we're getting SNS notifications, there can only be one item to process
    # for each invocation.
    item: ds.DataItem = source.nextSource()
    local_file, source_info = controller.obtain(item)
    if not source_info['sourceID']:
        if config['verbose']:
            print(f'error: failed to transfer {item} because it has no SourceID specified.')
        return {
            'statusCode':   ReturnCodes.FAILED.value,
            'body':         'Bad SourceID on specified file.'
        }
    rc = validate_metadata(local_file, config)
    rtn = {
        'statusCode':   0,
        'body':         None
    }
    if rc:
        rtn['status_code'] = ReturnCodes.OK.value
        rtn['body'] = 'Succeeded metadata validation'
        item.dest_size = item.source_size
        notifier.notify(item, verbose=config['verbose'])
        if config['verbose']:
            print(f'info: succeeded in validating {item}.')
    else:
        rtn['status_code'] = ReturnCodes.FAILED.value
        rtn['body'] = 'Failed metadata validation'
        if config['verbose']:
            print(f'info: failed in validating {item}')

    return rtn
