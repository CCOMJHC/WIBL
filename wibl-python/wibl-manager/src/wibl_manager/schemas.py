from datetime import datetime, timezone
from http.client import HTTPException

import boto3
import requests
from pydantic.v1.schema import schema
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

    fileid = Column(String(60), primary_key=True)
    processtime = Column(String(40))
    updatetime = Column(String(40))
    notifytime = Column(String(40))
    logger = Column(String(80))
    platform = Column(String(80))
    size = Column(Float, nullable=False)
    observations = Column(Integer)
    soundings = Column(Integer)
    starttime = Column(String(40))
    endtime = Column(String(40))
    status = Column(Integer)
    messages = Column(String(1024))

    def __repr__(self):
        """
        Generate a simple string representation of the data model for debugging purposes.
        """
        return f'file {self.fileid} at {self.processtime} for logger {self.logger} on {self.platform} size {self.size} MB, status={self.status}.'

class GeoJSONDataModel(Base):
    """
    Data model for GeoJSON file metadata in the database.

    :param fileid:      Primary key, usually the file's name (assuming that it's a UUID)
    :type fileid:       str
    :param uploadtime:  String representation (ISO format) for when the file was first picked up for upload.  Added
                        automatically by the REST server on POST.
    :type uploadtime:   str
    :param updatetime:  String representation (ISO format) for when the PUT update to the metadata is received. Added
                        automatically by the REST server.
    :type updatetime:   str, optional
    :param notifytime:  String representation (ISO format) for when a notification about any processing failure is sent out.
    :type notifytime:   str, optional
    :param logger:      Unique identifier used for the logger generating the data.
    :type logger:       str, optional
    :param size:        Size of the file in MB.
    :type size:         float
    :param soundings:   Number of processed (output) soundings in the converted file.
    :type soundings:    int, optional
    :param status:      Status indicator for upload of the file to the archive.  Set to 'started' on POST, but can then be
                        updated through PUT to reflect the results of processing.
    :type status:       :enum: `return_codes.UploadStatus`
    :param messages:    Messages returned during processing (usually error/warnings)
    :type messages:     str, optional
    """

    __tablename__ = 'GeoJSONDataTable'

    fileid = Column(String(60), primary_key=True)
    uploadtime = Column(String(40))
    updatetime = Column(String(40))
    notifytime = Column(String(40))
    logger = Column(String(80))
    size = Column(Float, nullable=False)
    soundings = Column(Integer)
    status = Column(Integer)
    messages = Column(String(1024))

    def __repr__(self):
        """
        Generate a simple text version of the data model for debugging.
        """
        return f'file {self.fileid}, size {self.size} MB at {self.uploadtime} for logger {self.logger} with {self.soundings} observations, status={self.status}'
