# Public interface to the REST API for management
#
# This provides the public interface for the REST endpoints that manage the
# database of files being processed.
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
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from enum import Enum
from typing import Tuple, List
import requests


__version__ = '1.0.0'

class ReturnCodes(Enum):
    OK = 200
    RECORD_CREATED = 201
    RECORD_DELETED = 204
    FAILED = 400
    FILE_NOT_FOUND = 404
    RECORD_CONFLICT = 409

class ProcessingStatus(Enum):
    PROCESSING_STARTED = 0
    PROCESSING_SUCCESSFUL = 1
    PROCESSING_FAILED = 2

class UploadStatus(Enum):
    UPLOAD_STARTED = 0
    UPLOAD_SUCCESSFUL = 1
    UPLOAD_FAILED = 2

@dataclass_json
@dataclass
class FileMetadata:
    pass

@dataclass_json
@dataclass
class WIBLMetadata(FileMetadata):
    logger: str = 'Unknown'
    platform: str = 'Unknown'
    size: float = -1.0
    observations: int = -1
    soundings: int = -1
    starttime: str = 'Unknown'
    endtime: str = 'Unknown'
    status: int = ProcessingStatus.PROCESSING_STARTED.value

@dataclass_json
@dataclass
class GeoJSONMetadata(FileMetadata):
    logger: str = 'Unknown'
    size: float = -1.0
    soundings: int = -1
    status: int = UploadStatus.UPLOAD_STARTED.value


class MessageStore:
    messages: List[str] = []

    def write(self, message: str, verbose: bool) -> None:
        self.messages.append(message)
        if verbose:
            print(message)
    
    def extract(self) -> str:
        rtn = '\n'.join(self.messages)
        return rtn

    def empty(self) -> bool:
        return not self.messages


class MetadataType(Enum):
    WIBL_METADATA = 0
    GEOJSON_METADATA = 1


class ManagerInterface:
    metatype:   MetadataType
    logmsgs:    MessageStore
    verbose:    bool
    rest_url:   str

    def __init__(self, metatype: MetadataType, fileid: str, verbose: bool) -> None:
        self.metatype = metatype
        self.verbose = verbose
        self.logmsgs = MessageStore()
        if metatype == MetadataType.WIBL_METADATA:
            endpoint = 'wibl'
        elif metatype == MetadataType.GEOJSON_METADATA:
            endpoint = 'geojson'
        else:
            if verbose:
                self.logmsgs.write('error: endpoint type unknown', verbose)
            endpoint = ''

        if endpoint and 'MANAGEMENT_URL' in os.environ and os.environ['MANAGEMENT_URL']:
            self.rest_url = os.environ['MANAGEMENT_URL'] + endpoint + '/' + fileid
        else:
            self.rest_url = None

    def register(self, filesize: float) -> bool:
        if not self.rest_url:
            return True
        response = requests.post(self.rest_url, json={'size': filesize})
        if response.status_code != ReturnCodes.RECORD_CREATED.value:
            self.logmsg(f'error: metadata REST returned {response.status_code} for POST({self.rest_url}).')
            return False
        return True

    def logmsg(self, message: str) -> None:
        self.logmsgs.write(message, self.verbose)

    def update(self, meta: FileMetadata) -> bool:
        if not self.rest_url:
            return True
        meta_json = meta.to_dict()
        if not self.logmsgs.empty():
            meta_json['messages'] = self.logmsgs.extract()
        response = requests.put(self.rest_url, json=meta_json)
        if response.status_code != ReturnCodes.RECORD_CREATED.value:
            self.logmsgs.write(f'error: metadata REST returned {response.status_code} for PUT({self.rest_url}).', self.verbose)
            return False
        return True

    def lookup(self) -> Tuple[bool,FileMetadata]:
        if self.metatype == MetadataType.WIBL_METADATA:
            null_rtn = WIBLMetadata()
        else:
            null_rtn = GeoJSONMetadata()
        
        if not self.rest_url:
            return False, null_rtn
        
        response = requests.get(self.rest_url)
        if response.status_code != ReturnCodes.OK.value:
            self.logmsgs.write(f'error: metadata GET returned {response.status_code} for GET({self.rest_url}).', self.verbose)
            return False, null_rtn
        if self.metatype == MetadataType.WIBL_METADATA:
            meta: WIBLMetadata = WIBLMetadata.from_dict(response.json())
        else:
            meta: GeoJSONMetadata = GeoJSONMetadata.from_dict(response.json())
        return True, meta
