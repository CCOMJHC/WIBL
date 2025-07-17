# Data model and REST endpoint to manipulate GeoJSON metadata in the database
#
# When data is being converted into GeoJSON format, it is then uploaded to the archive;
# this data model and associated REST endpoint maintains in the database a list of all
# the files that have been picked up for upload, and their statistics.  The REST API is
# to generate an instance in the database with POST with minimal data when the file is
# first opened, and then update with PUT when the upload is complete.  Timestamps are
# applied at the server for the current time when the initial entry is made, and when
# it is updated (so that we can also get performance metrics out of the database).
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

from datetime import datetime, timezone
from http.client import HTTPException

from sqlalchemy import select, Delete
# noinspection PyInterpreter
from src.wibl_manager import ReturnCodes, GeoJSONStatus
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, HTTPException, Depends
from .database import Base, get_async_db
from src.wibl_manager.schemas import WIBLDataModel
from src.wibl_manager.schemas import GeoJSONDataModel
from pydantic import BaseModel, ConfigDict

# # Arguments passable to the GeoJSON end-point to POST a new record's metadata
class GeoJSONPostParse(BaseModel):
    size: float

# Arguments passable to the GeoJSON end-point for PUT updates to an existing file's metadata
class GeoJSONPutParse(BaseModel):
    logger: str = None
    size: float = None
    soundings: int = None
    notifytime: str = None
    status: int = None
    messages: str = None

# Data mapping for marshalling GeoJSONDataModel for transfer
class GeoJSONMarshModel(BaseModel):
    fileid: str
    uploadtime: str
    updatetime: str
    notifytime: str
    logger: str
    size: float
    soundings: int
    status: int
    messages: str




url = "/geojson/{fileid}"
GeoJSONRouter = APIRouter()

#TODO: Update the doc strings
class GeoJSONData:
    """
     A RESTful endpoint for manipulating metadata on GeoJSON files in a local database.  The design here
     expects that the client will generate a POST when the file is first picked up for upload to the archive,
     and then update with PUT when the upload is complete (and update the status indicator).  GET is provided
     for individual file extraction (or "all" for an index of all files currently in the database), and
     DELETE is provided to remove metadata entries.
     """

    @staticmethod
    @GeoJSONRouter.get(url, response_model=GeoJSONMarshModel)
    async def get(fileid: str, db = Depends(get_async_db)):
        """
         Lookup for a single file's metadata, or all files if :param: `fileid` is "all"

         :param fileid:  Filename to look up (typically a UUID)
         :type fileid:   str
         :return:        Metadata instance for the file or list of all file, or NOT_FOUND if the record doesn't exist
         :rtype:         tuple   The marshalling decorator should convert to JSON-serialisable form.
         """

        stmt = (
            select(GeoJSONDataModel)
            .where(GeoJSONDataModel.fileid == fileid)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    @GeoJSONRouter.get("/geojson/", response_model=list[GeoJSONMarshModel])
    async def getall(db=Depends(get_async_db)):

        result = await db.execute(select(GeoJSONDataModel))
        return result.scalars().all()

    @staticmethod
    @GeoJSONRouter.post(url, response_model=GeoJSONMarshModel, status_code=ReturnCodes.RECORD_CREATED.value)
    async def post(fileid: str, data: GeoJSONPostParse, db = Depends(get_async_db)):
        """
         Initial creation of a metadata entry for a GeoJSON file being uploaded.  Only the 'size' parameter is
         required at creation time; the server automatically sets the 'uploadtime' element to the current time
         and defaults the other values in the metadata to "unknown" states that are recognisable.

         :param fileid:  Filename to look up (typically a UUID)
         :type fileid:   str
         :return:        The initial state of the metadata for the file and RECORD_CREATED, or RECORD_CONFLICT if
                         the record already exists.
         :rtype:         tuple   The marchalling decorator should convert to JSON-serliasable form.
         """

        result = await db.execute(select(GeoJSONDataModel).where(GeoJSONDataModel.fileid == fileid))
        test_file = result.scalars().first()
        if test_file:
            raise HTTPException(status_code=ReturnCodes.RECORD_CONFLICT.value,
                                detail='That GeoJSON file already exists in the database; use PUT to update.')

        timestamp = datetime.now(timezone.utc).isoformat()
        geojson_file = GeoJSONDataModel(fileid=fileid, uploadtime=timestamp, updatetime='Unknown', notifytime='Unknown',
                                        logger='Unknown', size=data.size,
                                        soundings=-1, status=GeoJSONStatus.UPLOAD_STARTED.value, messages='')

        db.add(geojson_file)
        await db.commit()
        return geojson_file


    @staticmethod
    @GeoJSONRouter.put(url, response_model=GeoJSONMarshModel, status_code=ReturnCodes.RECORD_CREATED.value)
    async def put(fileid: str, data: GeoJSONPutParse, db = Depends(get_async_db)):
        """
         Update of the metadata for a single GeoJSON file after upload.  All variables can be set through the data
         parameters in the request, although the server automatically sets the 'updatetime' component to the current
         UTC time for the call. All the metadata elements are optional.

         :param fileid:  Filename to look up (typically a UUID)
         :type fileid:   str
         :return:        The updated state of the metadata for the file and RECORD_CREATED, or NOT_FOUND if the
                         record doesn't exist.
         :rtype:         tuple   The marshalling decorator should convert to JSON-serliasable form.
         """

        result = await db.execute(select(GeoJSONDataModel).where(GeoJSONDataModel.fileid == fileid))
        geojson_file = result.scalars().first()
        if not geojson_file:
            raise HTTPException(status_code=ReturnCodes.FILE_NOT_FOUND.value,
                                detail='That GeoJSON file does not exist in database; use POST to add.')
        timestamp = datetime.now(timezone.utc).isoformat()
        geojson_file.updatetime = timestamp

        if data.notifytime:
            geojson_file.notifytime = data.notifytime
        if data.logger:
            geojson_file.logger = data.logger
        if data.size:
            geojson_file.size = data.size
        if data.soundings:
            geojson_file.soundings = data.soundings
        if data.status:
            geojson_file.status = data.status
        if data.messages:
            geojson_file.messages = data.messages[:1024]
        await db.commit()
        return geojson_file

    @staticmethod
    @GeoJSONRouter.delete(url, status_code=ReturnCodes.RECORD_DELETED.value)
    async def delete(fileid: str, db = Depends(get_async_db)):
        """
         Remove a metadata record from the database for a single file.

         :param fileid:  Filename to look up (typically a UUID)
         :type fileid:   str
         :return:        RECORD_DELETED or NOT_FOUHD if the record doesn't exist.
         :rtype:         int   The marshalling decorator should convert to JSON-serliasable form.

         """
        if fileid == "all":
            await db.execute(Delete(GeoJSONDataModel))
            await db.commit()
            return
        else:
            result = await db.execute(select(GeoJSONDataModel).where(GeoJSONDataModel.fileid == fileid))
            geojson_file = result.scalars().first()
            if not geojson_file:
                raise HTTPException(status_code=ReturnCodes.FILE_NOT_FOUND.value,
                                    detail='That GeoJSON file does not exist in the database, and therefore cannot be deleted.')

            await db.execute(Delete(GeoJSONDataModel).where(GeoJSONDataModel.fileid == fileid))
            await db.commit()
            return
