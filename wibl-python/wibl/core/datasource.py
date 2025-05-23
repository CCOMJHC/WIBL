# \file datasource.py
# \brief Provide types to encapsulate cloud-primitives like getting and sending files
#
# The WIBL data logger system uses cloud processing for the files being collected, for
# example for timestamping, duplicate depth removal, data triage, conversion to GeoJSON
# format, and so forth.  In an attempt to allow this to happen on different cloud providers
# this code defines a dataclass to provide metadata on each item being processed, an abstract
# base class to convert to this format from whatever the cloud provider gives the base
# code, and a class to encapsulate the cloud primitives of getting an object from storage,
# and putting one back in.
#   The development system for this code was AWS, so there's probably some bias in how the
# configuration, etc., is managed.  However, the idea is that other cloud providers could be
# accommodated by sub-classing DataSource to manage translating the packet of information that
# the cloud system provides to the serverless code into a DataItem list, and also sub-classing
# CloudController for the code to get a file from an object store (obtain() method) to local
# store for processing, and to write a translated and processed file to an object store
# (transmit() method).
#   Since it can be difficult to test code in the cloud, the AWS code here also has a "local" mode
# where the expectation is that compute will be done on data on a local computer.  The JSON
# configuration element { "local": "True" } will turn this on.  This is not a requirement of the
# base class, however, so it's up to other implementations whether to support this or not.  (It's
# strongly recommended, however.)
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

from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional, List
from urllib.parse import unquote_plus, urlencode
import json
import os

import boto3
import botocore
import botocore.config

from wibl.core import getenv

# Force path addressing style to allow s3 URLs to be constructed without having to resolve virtual URLs, which
# requires an internet connection, which our lambdas won't have due to running in the VPC.
# For more information, see: https://docs.aws.amazon.com/AmazonS3/latest/userguide/VirtualHosting.html
region = os.getenv('AWS_REGION', 'us-east-2')
config = botocore.config.Config(s3={'addressing_style': 'path'})
s3 = boto3.resource(service_name='s3', region_name=region, config=config)
s3_cli = s3.meta.client

## Dataclass to hold the specification for a single item of data being processed
#
# Encapsulate the specification for where to get the input file (bucket and key), what name to
# use for the local copy to work on, and where to put the output file (bucket and key).

@dataclass
class DataItem:
    # Source file's cloud store, typically the name of an S3 bucket
    source_store:   str
    # Source file's key in the cloud store, typically the key in the S3 bucket
    source_key:     str
    # Source file's size in bytes
    source_size:    Optional[int]
    # Name of the file to use in the local file system for downloading the cloud file for processing
    localname:      Optional[str]
    # Destination file's cloud store, typically the name of an S3 bucket
    dest_store:     str
    # Destination file's key in the cloud store, typically the key in the S3 bucket
    dest_key:       str
    # Destination file's size in bytes
    dest_size:      Optional[int]


@dataclass
class MultiDataItem:
    """
    A data item that has multiple inputs and produces a single output
    """
    # Source file(s)'s cloud store, typically the name of an S3 bucket
    source_store: str
    # Source file's key in the cloud store, typically the key in the S3 bucket
    source_keys: List[str]
    # Destination file's name to be written to dest_store
    dest_key: str
    # Arbitrary metadata
    meta: Dict[str, Any] = None


## Abstract base class for a collection of data items to be processed
#
# Different cloud providers specify where to find the data to be processed in different ways.  This class
# provides an interface to how to translate this information into \a DataItem objects in sequence.

class DataSource(ABC):
    ## Default constructor, adapted to the cloud provider's data information
    @abstractmethod
    def __init__(self):
        pass

    ## Abstract method to extract the next \a DataItem object from the source information
    @abstractmethod
    def nextSource(self) -> DataItem:
        pass

## Concrete implementation of the \a DataSource model for AWS Lambdas
#
# Provide translation services from AWS Lambda event dictionaries to \a DataItems for S3 bucket
# objects.

class AWSSource(DataSource):
    ## Default constructor for AWS Lambda event sources
    #
    # This parses out all of the S3 objects specified in the AWS Lambda trigger event, and prepares
    # them as \a DataItems to be returned to the user in sequence.
    #
    # \param event      AWS Lambda event to parse
    # \param config     Configuration dictionary for the algorithm

    def __init__(self, event, config):
        self.items = []
        for record in event['Records']:
            if 'Sns' not in record:
                print('error: no SNS notification in event.')
            else:
                message = json.loads(record['Sns']['Message'])
                if 'bucket' not in message or 'filename' not in message:
                    print('error: malformed SNS message packet: {message}.')
                else:
                    source_bucket = message['bucket']
                    source_object = unquote_plus(message['filename'])
                    source_size = message['size']
                    local_file = f'/tmp/{source_object}'
                    dest_bucket = getenv('DEST_BUCKET')
                    if '.wibl' in source_object:
                        dest_object = source_object.replace('.wibl', '.json')
                    else:
                        dest_object = source_object
                    dest_size = 0
                    self.items.append(DataItem(source_bucket, source_object, source_size, local_file, dest_bucket, dest_object, dest_size))
        if config['verbose']:
            n_items = len(self.items)
            print(f'Total {n_items} input items to process:')
            for item in self.items:
                print(f'Item: {item}')
    
    ## Concrete implementation of S3 object specification return from AWS Lambda events
    #
    # Since the code converts all of the information about the S3 objects to be processed in the Lambda call
    # into a list in the initialiser, this code simply pops the next item off the list and returns to the
    # caller, or None if there are none left.
    #
    # \return Specification for the next S3 object to process
    def nextSource(self) -> DataItem:
        if self.items:
            rc = self.items.pop()
        else:
            rc = None
        return rc


class AWSSourceSNSTrigger(DataSource):
    ## Default constructor for AWS SNS event sources
    #
    # This parses out all of the S3 objects specified in the AWS SNS trigger event, and prepares
    # them as \a DataItems to be returned to the user in sequence.
    #
    # \param event      AWS Lambda event to parse
    # \param config     Configuration dictionary for the algorithm

    def __init__(self, event, config):
        self.items = []
        for record in event['Records']:
            if 'Sns' not in record:
                print('error: no SNS notification in event.')
            else:
                sns_message = json.loads(record['Sns']['Message'])
                if 'Records' not in sns_message:
                    print(f'error: no records found in SNS message: {sns_message}. Event was: {event}.')
                    # Skip to next record in event
                    continue
                for sns_record in sns_message['Records']:
                    if 's3' not in sns_record:
                        print(f'error: no s3 payload in sns_record: {sns_record}.')
                        # Skip to next SNS record in SNS message
                        continue
                    s3_payload = sns_record['s3']
                    if 'bucket' not in s3_payload or 'object' not in s3_payload:
                        print(f'error: malformed S3 payload in SNS message record: {sns_record}.')
                        # Skip to next SNS record in SNS message
                        continue
                    s3_bucket = s3_payload['bucket']
                    if 'name' not in s3_bucket:
                        print(f'error: no bucket name in S3 payload: {s3_payload}.')
                        # Skip to next SNS record in SNS message
                        continue
                    s3_object = s3_payload['object']
                    if 'key' not in s3_object or 'size' not in s3_object:
                        print(f'error: malformed object definition in S3 payload: {s3_payload}.')
                        # Skip to next SNS record in SNS message
                        continue
                    source_bucket = s3_bucket['name']
                    source_object = unquote_plus(s3_object['key'])
                    source_size = s3_object['size']
                    local_file = f'/tmp/{source_object}'
                    dest_bucket = getenv('DEST_BUCKET')
                    if '.wibl' in source_object:
                        dest_object = source_object.replace('.wibl', '.json')
                    else:
                        dest_object = source_object
                    dest_size = 0
                    self.items.append(
                        DataItem(source_bucket, source_object, source_size, local_file, dest_bucket, dest_object,
                                 dest_size))
        if config['verbose']:
            n_items = len(self.items)
            print(f'Total {n_items} input items to process:')
            for item in self.items:
                print(f'Item: {item}')

    ## Concrete implementation of S3 object specification return from AWS Lambda events
    #
    # Since the code converts all of the information about the S3 objects to be processed in the Lambda call
    # into a list in the initialiser, this code simply pops the next item off the list and returns to the
    # caller, or None if there are none left.
    #
    # \return Specification for the next S3 object to process
    def nextSource(self) -> DataItem:
        if self.items:
            rc = self.items.pop()
        else:
            rc = None
        return rc

## \class Concrete implementation for the \a DataSource model for a single local file
#
# This provides a simple model for a local file conversion from WIBL to GeoJSON, typically for
# debugging purposes (but also providing a local conversion if cloud services are not available).

class LocalSource(DataSource):
    ## Default constructor for local file conversion
    #
    # This simply stores the provided in and out filenames so that they can be converted to a DataTtem
    # when required.  Only a single filename is allowed currently.
    #
    # \param input  Local filename for the WIBL file to convert
    # \param output Local filename to write converted GeoJSON into
    # \param config Configuration dictionary for the algorithm

    def __init__(self, input: str, output: str, config: Dict[str,Any]):
        self.inname = input
        self.outname = output
        self.filesize = os.path.getsize(input)
        if config['verbose']:
            print(f'Configured for input file {self.inname} converting to {self.outname}.')
    
    ## Concrete implementation of local object specification
    #
    # Since we only have a single filename for local conversion, the code here simply converts
    # to a DataItem and then invalidates the local name so that we don't attempt to return it
    # more than once.
    #
    # \return Specification for the next local file to process
    def nextSource(self) -> DataItem:
        if self.inname is None:
            rc = None
        else:
            rc: DataItem = DataItem(None, self.inname, self.filesize, self.inname, None, self.outname, 0)
            self.inname = None
            self.outname = None
        return rc


class MultiDataSource(ABC):
    ## Default constructor, adapted to the cloud provider's data information
    @abstractmethod
    def __init__(self):
        pass

    ## Abstract method to extract the next \a DataItem object from the source information
    @abstractmethod
    def nextSource(self) -> MultiDataItem:
        pass


class AWSMultiSource(MultiDataSource):
    ## Default constructor for AWS Lambda event sources where multiple data items are sent to a single
    # lambda, such as when visualizing one or more GeoJSON files.

    # This parses out all of the S3 objects specified in each AWS Lambda trigger record, and prepares
    # them as \a MultiDataItems to be returned to the user in sequence.
    #
    # \param event      AWS Lambda event to parse
    # \param config     Configuration dictionary for the algorithm
    def __init__(self, event, config):
        self.items: List[MultiDataItem] = []
        for record in event['Records']:
            if 'Sns' not in record:
                print('error: no SNS notification in event.')
            else:
                message = json.loads(record['Sns']['Message'])
                if 'bucket' not in message or 'filename' not in message:
                    print('error: malformed SNS message packet: {message}.')
                else:
                    source_bucket = message['bucket']
                    source_keys = [unquote_plus(fname) for fname in message['source_keys']]
                    dest_key = message['dest_key']
                    if 'meta' in message:
                        meta = message['meta']
                    else:
                        meta = None

                    self.items.append(
                        MultiDataItem(source_bucket, source_keys, dest_key, meta=meta)
                    )
        if config['verbose']:
            n_items = len(self.items)
            print(f'Total {n_items} input items to process:')
            for item in self.items:
                print(f'Item: {item}')

    ## Concrete implementation of S3 object specification return from AWS Lambda events
    #
    # Since the code converts all of the information about the S3 objects to be processed in the Lambda call
    # into a list in the initialiser, this code simply pops the next item off the list and returns to the
    # caller, or None if there are none left.
    #
    # \return Specification for the next S3 object to process
    def nextSource(self) -> Optional[MultiDataItem]:
        if self.items:
            rc = self.items.pop()
        else:
            rc = None
        return rc


## Abstract base class for an encapsulation of how to interact with a specific cloud provider
#
# Each cloud provider acts a little differently with respect to how you extract objects from their
# store, and add them back in.  This provides an interface for the core operations required by the
# processing algorithm so that you can swap out providers more easily.

class CloudController(ABC):
    ## Default constructor, configuring the algorithm
    #
    # Construct a controller configuration for the cloud provider.
    #
    # \param config Dictionary (typically from JSON file) with parameters
    @abstractmethod
    def __init__(self, config: Dict[str,Any]):
        pass

    ## Test whether a specified object exists in the provider's cloud store
    #
    # Test whether a local copy of the specified cloud object can be obtained.
    #
    # \param meta   Specification for the object to pull from the cloud object store
    # \return Tuple[bool, Optional[int]] (True, size in bytes) if the specified object exists,
    #   (False, None) if the specified object doesn't exist.
    def exists(self, meta: DataItem) -> Tuple[bool, Optional[int]]:
        pass

    ## Extract a specified object from the provider's cloud store
    #
    # Get a local copy of the specified cloud object so that it can be processed.
    #
    # \param meta   Specification for the object to pull from the cloud object store
    # \return Tuple of a string and dictionary specifying the local filename at which
    # the object was stored, and the tags used for the object
    @abstractmethod
    def obtain(self, meta: DataItem) -> Tuple[str, Dict[str,Any]]:
        pass
        
    ## Send a local object to the cloud provider's object store
    #
    # Send a local data object (str) to the cloud provider's object store, setting an object metadata key-value
    # pair for the uniqueID associated with the object.
    #
    # \param meta       Specification for the object destination
    # \param SourceID   UniqueID for the source data, to set on the object store
    # \param Logger     Logger name for the source file
    # \param Soundings  Number of soundings in the transmitted file
    # \param data       Data string to transmit to the cloud object store
    @abstractmethod
    def transmit(self, meta: DataItem, SourceID: str, Logger: str, Soundings: int, data: str) -> None:
        pass

    ## Upload local (temp) file to cloud provider's object store
    #
    # \param localname      Name of local file to uplaod
    # \param dest_key       Key of object to store file in within bucket defined by self.destination.
    def upload(self, localname: str, dest_key: str) -> None:
        pass


## Concrete implementation of the CloudController model for AWS S3 buckets
#
# Implement methods to transfer data files between a local environment and an AWS S3 bucket store.

class AWSController(CloudController):
    ## Construct and configure the AWS S3 bucket interface
    #
    # This sets up for transfer of objects to an AWS S3 bucket, as specified in the configuration dictionary.
    # Parameters are:
    #   "local"             Flag: True => do operations (approximately) locally, rather than in the cloud (debugging)
    #   "staging_bucket"    S3 bucket name where output files are transmitted
    #   "verbose"           Flag: True => provide more information on what's going on
    #
    # \param config Configuration dictionary for the algorithm
    def __init__(self, config: Dict[str,Any]):
        self.destination = getenv('DEST_BUCKET')
        self.verbose = config['verbose']

    ## Test whether a specified object exists in the provider's cloud store
    #
    # Test whether a local copy of the specified cloud object can be obtained.
    #
    # \param meta   Specification for the object to pull from the cloud object store
    # \return Tuple[bool, Optional[int]] (True, size in bytes) if the specified object exists,
    #   (False, None) if the specified object doesn't exist.
    def exists(self, meta: DataItem) -> Tuple[bool, Optional[int]]:
        if self.verbose:
            print(f'Testing existence of object {meta.source_key} from bucket {meta.source_store}')
        try:
            response = s3_cli.head_object(Bucket=meta.source_store,
                                       Key=meta.source_key)
            return True, response['ContentLength']
        except botocore.exceptions.ClientError as e:
            if e.response['ResponseMetadata']['HTTPStatusCode'] == 404:
                return False, None
            else:
                raise e

    ## Get an S3 object from a specified bucket
    #
    # This reads the specified S3 object from the given bucket, and then reads the associated tags to see whether there
    # is a "SourceID" key-value pair specified (which contains the UniqueID for the file).  Using the object key-value
    # tags allows us to pass on the UniqueID without having to re-read the GeoJSON on transmission to DCDB.
    #
    # \param meta   Specification for the object being transferred into the local environment
    # \return Tuple[str,str]: local filename, dictionary of tags on the data
    def obtain(self, meta: DataItem) -> Tuple[str, Dict[str,Any]]:
        if self.verbose:
            print(f'Downloading from bucket {meta.source_store} object {meta.source_key} to local file {meta.localname}')
        s3.Bucket(meta.source_store).download_file(meta.source_key, meta.localname)
        tags = s3_cli.get_object_tagging(Bucket=meta.source_store, Key=meta.source_key)
        info: Dict[str,Any] = {'sourceID': '', 'logger': '', 'soundings': -1}
        for tag in tags['TagSet']:
            if tag['Key'] == 'SourceID':
                info['sourceID'] = tag['Value']
            if tag['Key'] == 'Logger':
                info['logger'] = tag['Value']
            if tag['Key'] == 'Soundings':
                info['soundings'] = int(tag['Value'])

        return meta.localname, info
    
    ## Transmit a local data object to an AWS S3 bucket/key with key-value metadata tags
    #
    # Upload a local data string to the specified AWS S2 bucket/key, and set the "SourceID" key-value metadata tag
    # on the resulting object to store the uniqueID used for the data.  This allows us to re-read it later without
    # having to read in and parse the whole GeoJSON file.  In local mode, the code generates a formatted JSON object
    # to the output file specified, stored in the current working directory, and reports the first 1000 characters of
    # the object (or the whole object if smaller).
    #
    # \param meta       Specification for the object being transferred into the cloud environment
    # \param sourceID   UniqueID associated with the data (for key-value metadata tag)
    # \param logger     Logger name for the source file
    # \param soundings  Number of soundings in the transmitted file
    # \param data       Data to transfer into the cloud store
    def transmit(self, meta: DataItem, sourceID: str, logger: str, soundings: int, data: str) -> None:
        if self.verbose:
            print(f'Transmitting {meta.localname} to bucket {self.destination}, key {meta.dest_key}, source ID {sourceID}')
        tags = urlencode({
            'SourceID': sourceID,
            'Logger': logger,
            'Soundings': soundings
        })
        s3.Bucket(self.destination).put_object(Key=meta.dest_key, Body=data,
                                               Tagging=tags)

    ## Upload local (temp) file to an AWS S3 bucket/key
    #
    # \param localname      Name of local file to uplaod
    # \param dest_key       Key of object to store file in within bucket defined by self.destination.
    def upload(self, localname: str, dest_key: str) -> None:
        if self.verbose:
            print(f'Uploading {localname} to bucket {self.destination}, key {dest_key}.')
        s3.Bucket(self.destination).upload_file(localname, dest_key)


## \class LocalController
#
# This provides a concrete implementation for a pseudo-controller than works with local
# files (i.e., doing direct conversion on the local machine).

class LocalController(CloudController):
    ## Configure the local controller
    #
    # Since the local controller just operates on files in the local system, the
    # only configuration is whether to report what's going on (verbose mode)
    #
    # \param config Dictionary of algorithm configuration parameters
    def __init__(self, config: Dict[str, Any]):
        self.verbose = config['verbose']

    ## Test whether a specified object exists as a local file
    #
    # \param meta   Specification for the object to pull from the local environment
    # \return Tuple[bool, Optional[int]] (True, size in bytes) if the specified object exists,
    #   (False, None) if the specified object doesn't exist.
    def exists(self, meta: DataItem) -> Tuple[bool, Optional[int]]:
        try:
            stat = os.stat(meta.localname)
            return True, stat.st_size
        except FileNotFoundError:
            return False, None

    ## Concrete implementation of the code to provide a local file
    #
    # Since the file is in the local filesystem and can be opened directly, there's
    # no need to copy it to a given location; the code therefore simply returns the
    # local filename of the input file.
    #
    # \param meta   Specification for the object being transferred into the local environment
    # \return Tuple[str,str]: local filename, dictionary of tags
    def obtain(self, meta: DataItem) -> Tuple[str, Dict[str,Any]]:
        info: Dict[str,Any] = {'sourceID': '', 'logger': '', 'soundings': -1}
        # To get the tagging information on a local file, we can't rely on the sort of key,value
        # pairs that we have in S3, so we read the file, and find them directly (if the file is JSON)
        if 'json' in meta.localname:
            with open(meta.localname, 'r') as f:
                data = json.load(f)
                # We need to make sure that we get the source ID from the right location in the
                # metadata --- it varies between V2 and V3 metadata (and possibly from others)
                sourceID: str = ''
                if 'trustedNode' in data['properties']:
                    # This was added in V3.1 of the metadata specification
                    if data['properties']['trustedNode']['convention'] == 'GeoJSON CSB 3.1':
                        sourceID = data['properties']['trustedNode']['uniqueVesselID']
                    else:
                        # If we don't get a convention that we recognise, we can at least check to see
                        # whether the vessel ID is still in the same place
                        if 'uniqueVesselID' in data['properties']['trustedNode']:
                            sourceID = data['properties']['trustedNode']['uniqueVesselID']
                        else:
                            if self.verbose:
                                print('error: failed to find a unique vessel ID in metadata.')
                else:
                    if 'convention' in data['properties']:
                        # This was the case in V2 and V3.0 metadata, but we should check that it's a version
                        # that we understand.  This is more a nicety than anything else: there was
                        # only one version, so this should always pass!
                        if data['properties']['convention'] in ('CSB 2.0', 'GeoJSON CSB 3.0'):
                            sourceID = data['properties']['platform']['uniqueID']
                        else:
                            if self.verbose:
                                print('error: unrecognised CSB metadata convention.')
                info['sourceID'] = sourceID
                if 'platform' in data['properties'] and 'IDNumber' in data['properties']['platform']:
                    info['logger'] = data['properties']['platform']['IDNumber']
                else:
                    info['logger'] = 'wibl-logger'
                info['soundings'] = len(data['features'])
        return meta.localname, info

    ## Concrete implementation of code to save converted GeoJSON data
    #
    # Since the file output is in the local filesystem, the code here just formats
    # the GeoJSON and writes it to the indicated file.
    #
    # \param meta       Specification for the object being transferred into the cloud environment
    # \param sourceID   UniqueID associated with the data (for key-value metadata tag)
    # \param data       Data to transfer into the cloud store
    def transmit(self, meta: DataItem, sourceID: str, logger: str, soundings: int, data: str) -> None:
        if self.verbose:
            if len(data) > 1000:
                prdata = str(data[0:1000]) + '...'
            else:
                prdata = str(data)
            print(f'Local conversion: saving to {meta.dest_key} with data {prdata}.')
        with open(meta.dest_key, 'w') as f:
            json.dump(json.loads(data.decode('utf-8')), f, indent=4)

