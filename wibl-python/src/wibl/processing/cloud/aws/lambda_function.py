##\file lambda_function.py
# \brief Drive the conversion and time-stamping of logger binary files with output in GeoJSON
#
# The low-cost data loggers generate data as binary outputs which are time referenced to the logger's
# internal reference time.  For submission into the DCDB database, we need it to be referenced to UTC,
# and we need to interpolate the positioning data to the times of the depth measurements recorded; we
# also need to convert to GeoJSON so that it can be pulled into their databases more easily.  This script
# orchestrates this process for a single file, and is expected to run as an AWS Lambda in response to
# the file being uploaded into an incoming S3 bucket.  The output goes into a "well known" S3 bucket
# that is used to stage data before it goes off to DCDB (via another Lambda).
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

import json
from typing import Dict, Any
from datetime import datetime

import boto3

import wibl.core.config as conf
import wibl.core.logger_file as lf
import wibl.core.datasource as ds
import wibl.core.notification as nt
from wibl.core.algorithm import UnknownAlgorithm
from wibl.core import getenv, Lineage
import wibl.core.timestamping as ts
import wibl.core.geojson_convert as gj
from wibl.processing.cloud.aws import get_config_file
from wibl_manager import ManagerInterface, MetadataType, WIBLMetadata, ProcessingStatus

s3 = boto3.resource('s3')


def read_local_event(event_file: str) -> Dict:
    """For local testing, you need to simulate an AWS Lambda event stucture to give the code something
       to do.  You can download the JSON for a typical event from the AWS Lambda console and store it
       locally.  This helper function can be called interactively to load this information.
    """
    with open(event_file) as f:
        event = json.load(f)
    return event


def process_item(item: ds.DataItem, controller: ds.CloudController, notifier: nt.Notifier, config: Dict[str,Any]) -> bool:
    """Implement the business logic to translate the file from WIBL binary into a GeoJSON file.  The
       file with metadata in 'item' is pulled from object store using 'controller.obtain()', run through
       the translation and time-stamping from the Timestamping module, and then converted to GeoJSON
       format.  The 'controller.transmit()' method is then used to send the file into the destination
       object store so that the file is effectively cached until it is uploaded to the end-point database.
       Note that this code does not clean up the input object, so all files being uploaded to the cloud
       might potentially stay in the input object store unless otherwise deleted.
    """

    verbose: bool = config['verbose']

    meta: WIBLMetadata = WIBLMetadata()
    lineage: Lineage = Lineage()
    meta.size = item.source_size/(1024.0*1024.0)
    meta.status = ProcessingStatus.PROCESSING_FAILED.value  # Until further notice ...
    manager: ManagerInterface = ManagerInterface(MetadataType.WIBL_METADATA, item.source_key, config['verbose'])
    if not manager.register(meta.size):
        print('error: failed to register file with REST management interface.')
    
    if verbose:
        print(f'Attempting to obtain item {item} from S3 ...')

    source_data: Dict = {}
    local_file, source_info = controller.obtain(item)
    try:
        if verbose:
            print(f'Attempting file read/time interpolation on {local_file} ...')
        source_data = ts.time_interpolation(local_file, lineage,
                                            config['elapsed_time_quantum'], verbose = config['verbose'], fault_limit = config['fault_limit'])
        meta.logger = source_data['loggername']
        meta.platform = source_data['platform']
        meta.observations = len(source_data['depth']['z'])
        meta.soundings = meta.observations
        meta.starttime = datetime.fromtimestamp(source_data['depth']['t'][0]).isoformat()
        meta.endtime = datetime.fromtimestamp(source_data['depth']['t'][-1]).isoformat()
    except lf.PacketTranscriptionError as e:
        print(f"Error reading packet from WIBL file: {str(e)}")
    except ts.NoTimeSource:
        manager.logmsg(f'error: failed to convert data({local_file}): no time source known.')
        manager.update(meta)
        return False
    except ts.NewerDataFile:
        manager.logmsg(f'error: failed to convert data({local_file}): file data format is newer than latest version known to code.')
        manager.update(meta)
        return False
    except ts.NoData:
        manager.logmsg(f'error: failed to convert data({local_file}): no bathymetric data in file.')
        manager.update(meta)
        return False
    except UnknownAlgorithm as e:
        manager.logmsg(f'error: failed to convert data({local_file}): {str(e)}')
        manager.update(meta)
        return False

    if verbose:
        print('Converting remaining data to GeoJSON format ...')
    try:
        submit_data = gj.translate(source_data, lineage, local_file, config)
    except UnknownAlgorithm as e:
        manager.logmsg(str(e))
        manager.update(meta)
        print(f"Aborting pocessing due to error: {str(e)}")
        return False

    try:
        source_id = submit_data['properties']['trustedNode']['uniqueVesselID']
    except KeyError as e:
        print(f'error: KeyError while reading uniqueVesselID, submit_data was: {submit_data}')
        raise e

    source_id = submit_data['properties']['trustedNode']['uniqueVesselID']
    if verbose:
        print('Converting GeoJSON to byte stream for transmission ...')

    encoded_data = json.dumps(submit_data).encode('utf-8')
    item.dest_size = len(encoded_data)
    if verbose:
        print('Attempting to send encoded data to S3 staging bucket ...')
    controller.transmit(item, source_id, meta.logger, meta.soundings, encoded_data)

    meta.status = ProcessingStatus.PROCESSING_SUCCESSFUL.value
    if verbose:
        print('Attempting to update status via manager...')
    manager.update(meta)
    if verbose:
        print('Attempting to notify SNS')
    notifier.notify(item)
    return True
    
    
def lambda_handler(event, context):
    try:
        # The configuration file for the algorithm should be in the same directory as the lambda function file,
        # and has a "well known" name.  We could attempt to something smarter here, but this is probably enough
        # for now.
        config = conf.read_config(get_config_file())
    except conf.BadConfiguration:
        return {
            'statusCode': 400,
            'body': 'Bad configuration'
        }
    
    # We instantiate the AWS versions of DataSource and CloudController explicitly, since we can't be using anything
    # else given the rest of the infrastructure here, which is AWS specific.
    # When using direct S3 triggers or custom WIBL lambda-generated SNS event payloads, use:
    source = ds.AWSSource(event, config)
    # When using S3->SNS triggers, use:
    # source = ds.AWSSourceSNSTrigger(event, config)
    controller = ds.AWSController(config)
    notifier = nt.SNSNotifier(getenv('NOTIFICATION_ARN'))
    
    p = source.nextSource()
    while p is not None:
        if not process_item(p, controller, notifier, config):
            print(f'Abandoning processing of {p.source_key} due to errors.')
        p = source.nextSource()

    return {
        'statusCode': 200,
        'body': json.dumps('Processing completed.')
    }
