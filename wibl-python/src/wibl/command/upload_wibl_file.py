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
import argparse as arg
import sys

import boto3

from wibl.command import get_subcommand_prog


def uploadwibl():
    parser = arg.ArgumentParser(description='Upload WIBL logger files to an S3 bucket (in a limited capacity)',
                                prog=get_subcommand_prog())
    parser.add_argument('-b', '--bucket', type=str, help = 'Set the upload bucket name (string)')
    parser.add_argument('-j', '--json', action='store_true', help = 'Add .json extension to UUID for upload key')
    parser.add_argument('-s', '--source', type=str, help='Set SourceID tag for the S3 object (string)')
    parser.add_argument('input', type=str, help = 'WIBL format input file')

    optargs = parser.parse_args(sys.argv[2:])

    if not optargs.input:
        sys.exit('Error: must have an input file!')
    else:
        filename = optargs.input
  
    if optargs.bucket:
        bucket = optargs.bucket
    else:
        bucket = 'csb-upload-ingest-bucket'
    
    if optargs.json:
        file_extension = '.json'
    else:
        file_extension = '.wibl'
        
    sourceID = None
    if optargs.source:
        sourceID = optargs.source

    s3 = boto3.resource('s3')
    dest_bucket = s3.Bucket(bucket)
    try:
        obj_key = str(uuid.uuid4()) + file_extension
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
            
        print(f'Successfully uploaded {filename} to bucket {bucket} for object {obj_key}.')
    except:
        print(f"Failed to upload file to CSB ingest bucket")
