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
from typing import Optional

from sqlalchemy import select, Delete
# noinspection PyInterpreter
from src.wibl_manager import ReturnCodes, WIBLStatus
from .database import Base, get_async_db
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends
from src.wibl_manager.schemas import WIBLDataModel


class WIBLPostParse(BaseModel):
    size: float


class WIBLPutParse(BaseModel):
    logger: str = None
    platform: str = None
    size: float = None
    observations: int = None
    soundings: int = None
    notifytime: str = None
    starttime: str = None
    endtime: str = None
    status: int = None
    messages: str = None


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
    @WIBLDataRouter.get(url, response_model=WIBLMarshModel)
    async def get(fileid: str, db=Depends(get_async_db)):
        """
        Lookup for a single file's metadata, or all files if :param: `fileid` is "all".

        :param fileid:  Filename to look up (typically a UUID)
        :type fileid:   str
        :return:        Metadata instance for the file or list of all file, or NOT_FOUND if the record doesn't exist
        :rtype:         tuple  The marshalling decorator should convert to JSON-serialisable form.
        """

        stmt = (
            select(WIBLDataModel)
            .where(WIBLDataModel.fileid == fileid)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    @WIBLDataRouter.get("/wibl/", response_model=list[WIBLMarshModel])
    async def getAll(db=Depends(get_async_db)):
        """
        Lookup for a single file's metadata, or all files if :param: `fileid` is "all".

        :param fileid:  Filename to look up (typically a UUID)
        :type fileid:   str
        :return:        Metadata instance for the file or list of all file, or NOT_FOUND if the record doesn't exist
        :rtype:         tuple  The marshalling decorator should convert to JSON-serialisable form.
        """
        result = await db.execute(select(WIBLDataModel))
        return result.scalars().all()

    @staticmethod
    @WIBLDataRouter.post(url, response_model=WIBLMarshModel, status_code=ReturnCodes.RECORD_CREATED.value)
    async def post(fileid: str, data: WIBLPostParse, db=Depends(get_async_db)):
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
        test_file = result.scalars().first()
        if test_file:
            raise HTTPException(status_code=ReturnCodes.RECORD_CONFLICT.value,
                                detail='That WIBL file already exists in the database; use PUT to update.')

        timestamp = datetime.now(timezone.utc).isoformat()
        wibl_file = WIBLDataModel(fileid=fileid, processtime=timestamp, updatetime='Unknown', notifytime='Unknown',
                                  logger='Unknown', platform='Unknown', size=data.size,
                                  observations=-1, soundings=-1, starttime='Unknown', endtime='Unknown',
                                  status=WIBLStatus.PROCESSING_STARTED.value, messages='')

        db.add(wibl_file)
        await db.commit()
        return wibl_file

    @staticmethod
    @WIBLDataRouter.put(url, response_model=WIBLMarshModel, status_code=ReturnCodes.RECORD_CREATED.value)
    async def put(fileid: str, data: WIBLPutParse, db=Depends(get_async_db)):
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
            wibl_file.platform = data.platform
        if data.size:
            wibl_file.size = data.size
        if data.observations:
            wibl_file.observations = data.observations
        if data.soundings:
            wibl_file.soundings = data.soundings
        if data.starttime:
            wibl_file.starttime = data.starttime
        if data.endtime:
            wibl_file.endtime = data.endtime
        if data.status:
            wibl_file.status = data.status
        if data.messages:
            wibl_file.messages = data.messages[:1024]
        await db.commit()
        return wibl_file

    @staticmethod
    @WIBLDataRouter.delete(url, status_code=ReturnCodes.RECORD_DELETED.value)
    async def delete(fileid: str, db=Depends(get_async_db)):
        """
        Remove a metadata record from the database for a single file.

        :param fileid:  Filename to look up (typically a UUID)
        :type fileid:   str
        :return:        RECORD_DELETED or NOT_FOUHD if the record doesn't exist.
        :rtype:         int   The marshalling decorator should convert to JSON-serliasable form.

        """
        if fileid == "all":
            await db.execute(Delete(WIBLDataModel))
            await db.commit()
            return
        else:
            result = await db.execute(select(WIBLDataModel).where(WIBLDataModel.fileid == fileid))
            wibl_file = result.scalars().first()
            if not wibl_file:
                raise HTTPException(status_code=ReturnCodes.FILE_NOT_FOUND.value,
                                    detail='That WIBL file does not exist in the database, and therefore cannot be deleted.')

            await db.execute(Delete(WIBLDataModel).where(WIBLDataModel.fileid == fileid))
            await db.commit()
            return
