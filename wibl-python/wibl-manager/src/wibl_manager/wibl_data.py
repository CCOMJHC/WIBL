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
import os
from datetime import datetime, timezone
from http.client import HTTPException

import boto3
import requests
from sqlalchemy import Column, String, Integer, Float, select, Delete
# noinspection PyInterpreter
from src.wibl_manager.app_globals import dashData
from src.wibl_manager import ReturnCodes, ProcessingStatus
from .database import Base, get_async_db
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException


class WIBLDataModel(Base):
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

    __tablename__ = 'WIBLDataTable'

    fileid = Column(String(40), primary_key=True)
    processtime = Column(String(30))
    updatetime = Column(String(30))
    notifytime = Column(String(30))
    logger = Column(String(80))
    platform = Column(String(80))
    size = Column(Float, nullable=False)
    observations = Column(Integer)
    soundings = Column(Integer)
    starttime = Column(String(30))
    endtime = Column(String(30))
    status = Column(Integer)
    messages = Column(String(1024))

    def __repr__(self):
        """
        Generate a simple string representation of the data model for debugging purposes.
        """
        return f'file {self.fileid} at {self.processtime} for logger {self.logger} on {self.platform} size {self.size} MB, status={self.status}.'


class WIBLMarshModel(BaseModel):
    fileid: str
    processtime: str
    updatetime: str
    notifytime: str
    logger: str
    platform: str
    size: float
    observations: int
    soundings: int
    starttime: str
    endtime: str
    status: int
    messages: str


class WIBLPostParse(BaseModel):
    size: str


class WIBLPutParse(BaseModel):
    logger: str
    platform: str
    size: float
    observations: int
    soundings: int
    starttime: str
    endtime: str
    notifytime: str
    status: int
    messages: str


WIBLDataRouter = APIRouter()
url = "/wibl/{fileid}"

#TODO: Update the doc strings
class WIBLData:
    """
    RESTful end-point for manipulating the WIBL data file database component.  The design here assumes
    that the user will use POST to generate an initial metadata entry when the file is first picked up
    for processing, and then update it with PUT when the results of the processing are known.  GET is
    provided for metadata lookup (GET 'all' for everything) and DELETE for file removal.
    """

    @staticmethod
    @WIBLDataRouter.get(url)
    async def get(fileid: str, db: AsyncSession):
        """
        Lookup for a single file's metadata, or all files if :param: `fileid` is "all".

        :param fileid:  Filename to look up (typically a UUID)
        :type fileid:   str
        :return:        Metadata instance for the file or list of all file, or NOT_FOUND if the record doesn't exist
        :rtype:         tuple  The marshalling decorator should convert to JSON-serialisable form.
        """
        if fileid == 'all':
            result = await db.execute(select(WIBLDataModel))
            return result.scalars().all()
        else:
            stmt = (
                select(WIBLDataModel)
                .where(WIBLDataModel.fileid == fileid)
            )
            result = await db.execute(stmt)
            return result.scalars().first()

    @staticmethod
    @WIBLDataRouter.post(url)
    async def post(fileid: str, data: WIBLPostParse, db: AsyncSession):
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

        result = await db.execute(select(WIBLDataModel).where(WIBLDataModel.fileid == fileid))
        if result:
            raise HTTPException(status_code=ReturnCodes.RECORD_CONFLICT.value,
                                detail='That WIBL file already exists in the database; use PUT to update.')

        timestamp = datetime.now(timezone.utc).isoformat()
        wibl_file = WIBLDataModel(fileid=fileid, processtime=timestamp, updatetime='Unknown', notifytime='Unknown',
                                  logger='Unknown', platform='Unknown', size=data.size,
                                  observations=-1, soundings=-1, starttime='Unknown', endtime='Unknown',
                                  status=ProcessingStatus.PROCESSING_STARTED.value, messages='')

        db.add(wibl_file)
        await db.commit()
        return wibl_file, ReturnCodes.RECORD_CREATED.value

    @staticmethod
    @WIBLDataRouter.put(url)
    async def put(fileid: str, data: WIBLPutParse, db: AsyncSession):
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

        result = await db.execute(select(WIBLDataModel).where(WIBLDataModel.fileid == fileid))
        wibl_file = result.scalars().first()
        if not wibl_file:
            raise HTTPException(status_code=ReturnCodes.FILE_NOT_FOUND.value,
                                detail='That WIBL file does not exist in database; use POST to add.')
        timestamp = datetime.now(timezone.utc).isoformat()
        wibl_file.updatetime = timestamp

        if data.notifytime:
            wibl_file.notifytime = data.notifytime
        if data.logger:
            wibl_file.logger = data.logger
        if data.platform:
            if wibl_file.platform:
                dashData.subtractObserverStat("fileCount", 1, wibl_file.platform)
                dashData.addObserverStat("fileCount", 1, data.platform)
            else:
                dashData.addObserverStat("fileCount", 1, data.platform)

            wibl_file.platform = data.platform
        if data.size:
            # If the size of the file changes,
            # remove its old size from the total and add the new one
            dashData.subtractGeneral("SizeTotal", wibl_file.size)
            wibl_file.size = data.size
            dashData.addGeneral("SizeTotal", data.size)
        if data.observations:
            wibl_file.observations = data.observations
        if data.soundings:
            wibl_file.soundings = data.soundings
        if data.starttime:
            wibl_file.starttime = data.starttime
        if data.endtime:
            wibl_file.endtime = data.endtime
        if data.status:
            # File always starts with status 0
            # So if the status changes to 1 or 2, add it to the data.
            match data.status:
                case 1:
                    dashData.addGeneral("ConvertedTotal", 1)
                case 2:
                    dashData.addGeneral("ProcessingFailedTotal", 1)
            wibl_file.status = data.status
        if data.messages:
            wibl_file.messages = data.messages[:1024]
        await db.commit()

        return wibl_file, ReturnCodes.RECORD_CREATED.value

    @staticmethod
    @WIBLDataRouter.delete(url)
    async def delete(fileid: str, db: AsyncSession):
        """
        Remove a metadata record from the database for a single file.

        :param fileid:  Filename to look up (typically a UUID)
        :type fileid:   str
        :return:        RECORD_DELETED or NOT_FOUHD if the record doesn't exist.
        :rtype:         int   The marshalling decorator should convert to JSON-serliasable form.

        """
        if fileid == "all":
            result = await db.execute(Delete(WIBLDataModel))
            await db.commit()
            return ReturnCodes.RECORD_DELETED.value
        else:
            result = await db.execute(select(WIBLDataModel).where(WIBLDataModel.fileid == fileid))
            wibl_file = result.scalars().first()
            if not wibl_file:
                raise HTTPException(status_code=ReturnCodes.FILE_NOT_FOUND.value,
                                    detail='That WIBL file does not exist in the database, and therefore cannot be deleted.')

            await db.execute(Delete(WIBLDataModel).where(WIBLDataModel.fileid == fileid))
            await db.commit()
            return ReturnCodes.RECORD_DELETED.value
