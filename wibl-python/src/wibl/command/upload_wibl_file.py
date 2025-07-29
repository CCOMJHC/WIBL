##\file upload_wibl_file.py
# \brief Send a WIBL binary file into AWS S3 for processing
#
# This is a simple command-line utility to send a given WIBL binary file to
# the configured AWS S3 bucket that triggers the Lambda functions for processing.
# Note that this does not deal with credentials: you have to have the appropriate
# credentials set up in your local environment to allow the upload.
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

import uuid
from pathlib import Path

import boto3
import click


@click.command()
@click.argument('input', type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
@click.option('-b', '--bucket', type=str,
              help='The upload bucket name')
@click.option('-j', '--json', is_flag=True, default=False,
              help='Add .json extension to UUID for upload key')
@click.option('-s', '--source', type=str,
              help='Set SourceID tag for the S3 object')
def uploadwibl(input: Path, bucket: str, json: bool, source: str):
    """Upload a WIBL file INPUT to an S3 bucket for processing."""
    filename = input

    if bucket:
        bucket = bucket
    else:
        bucket = 'csb-upload-ingest-bucket'
    
    if json:
        file_extension = '.json'
    else:
        file_extension = '.wibl'
        
    sourceID = None
    if source:
        sourceID = source

    s3 = boto3.resource('s3')
    dest_bucket = s3.Bucket(bucket)
    try:
        obj_key = f"{str(uuid.uuid4())}file_extension"
        dest_bucket.upload_file(Filename=filename, Key=obj_key)
        if sourceID is not None:
            tagset = {
                'TagSet': [
                    {
                        'Key':  'SourceID',
                        'Value':    sourceID
                    },
                ]
            }
            boto3.client('s3').put_object_tagging(Bucket=bucket, Key=obj_key, Tagging=tagset)
            
        click.echo(f"Successfully uploaded {filename} to bucket {bucket} for object {obj_key}.")
    except Exception as e:
        click(f"Failed to upload file to CSB ingest bucket due to error: {str(e)}")
