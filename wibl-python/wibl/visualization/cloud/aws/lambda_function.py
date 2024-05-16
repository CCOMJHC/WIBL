import os
from pathlib import Path
import tempfile
from typing import List

import boto3

from wibl import config_logger_service
from wibl.core import getenv
import wibl.core.config as conf
import wibl.core.datasource as ds
from wibl.visualization.cloud.aws import get_config_file
from wibl.core.util import merge_geojson, geojson_pt_to_ln
from wibl.core.util.aws import generate_get_s3_object
from wibl.visualization.soundings import map_soundings


logger = config_logger_service()
s3 = boto3.resource('s3')


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

    if config['verbose']:
        logger.info(f"event: {event}")

    controller = ds.AWSController(config)

    source_store: str = getenv('STAGING_BUCKET')

    if 'body' not in event:
        return {
            'statusCode': 400,
            'body': 'Body not found in event.'
        }
    body: dict = event['body']

    if not isinstance(body, dict):
        return {
            'statusCode': 400,
            'body': f"Unexpected type for body: {type(body)}"
        }

    if 'observer_name' not in body:
        return {
            'statusCode': 400,
            'body': f"Property 'observer_name' not found in event body: {body}"
        }
    observer_name: str = body['observer_name']

    if 'dest_key' not in body:
        return {
            'statusCode': 400,
            'body': f"Property 'dest_key' not found in event body: {body}"
        }
    dest_key: str = body['dest_key']

    if 'source_keys' not in body:
        return {
            'statusCode': 400,
            'body': f"Property 'source_keys' not found in event body: {body}"
        }
    source_keys: List[str] = body['source_keys']

    merged_geojson_path = None
    with tempfile.TemporaryDirectory() as tempdir:
        # First convert point GeoJSON files from S3 to line GeoJSON files in tempdir
        try:
            for geojson_file in source_keys:
                with open(os.path.join(tempdir, geojson_file), mode='w', encoding='utf-8') as out_fp:
                    geojson_pt_to_ln(generate_get_s3_object(s3.meta.client),
                                     source_store, geojson_file, out_fp)
        except Exception as e:
            print(f"Unable to convert point GeoJSON from S3 to line GeoJSON in tempdir. Error was: {str(e)}")
            return {
                'statusCode': 500,
                'body': 'Unable to convert point GeoJSON from S3 to line GeoJSON in tempdir.'
            }

        try:
            # Next merge line GeoJSON files into a single GeoJSON file
            merged_geojson_fp = tempfile.NamedTemporaryFile(mode='w',
                                                            encoding='utf-8',
                                                            newline='\n',
                                                            suffix='.json',
                                                            delete=False)
            merged_geojson_path = Path(merged_geojson_fp.name)
            merge_geojson(lambda loc, f: open(os.path.join(loc, f)),
                          tempdir, source_keys, merged_geojson_fp,
                          fail_on_error=True)
        except Exception as e:
            merged_geojson_fp.close()
            merged_geojson_path.unlink()
            print(f"Unable to merge line GeoJSON files into single GeoJSON file. Error was: {str(e)}")
            return {
                'statusCode': 500,
                'body': 'Unable to merge line GeoJSON files into single GeoJSON file.'
            }
        merged_geojson_fp.close()

    # Now map soundings into local temporary file
    try:
        map_filename: Path = map_soundings(merged_geojson_path,
                                           observer_name,
                                           dest_key)
        # Upload map to S3 destination bucket
        controller.upload(str(map_filename), map_filename.name)
    except Exception as e:
        print(f"Unable to map soundings. Error was {str(e)}")
        return {
            'statusCode': 500,
            'body': 'Unable to map soundings.'
        }

    return {
        'statusCode': 200,
        'body': {
            'mesg': f"Successfully uploaded map named {map_filename.name}.",
            'upload_url': f"s3://{controller.destination}/{map_filename.name}"
        }
    }
