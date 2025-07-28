from calendar import month

from src.wibl_manager import ReturnCodes, WIBLStatus, GeoJSONStatus
from .database import Base, get_async_db
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from http.client import HTTPException
from typing import Optional
from sqlalchemy import select, func, cast, Date
from fastapi import APIRouter, HTTPException, Depends
from src.wibl_manager import GeoJSONStatus
from src.wibl_manager.schemas import WIBLDataModel, GeoJSONDataModel
import asyncio
from geoalchemy2 import functions

StatsRouter = APIRouter()


@StatsRouter.get("/statistics")
async def getStats(db=Depends(get_async_db)):
    WIBLTotalStmt = (
        select(func.count())
        .select_from(WIBLDataModel)
    )

    GeoJSONTotalStmt = (
        select(func.count())
        .select_from(GeoJSONDataModel)
    )

    SizeTotalStmt = (
        select(func.sum(WIBLDataModel.size))
    )

    FileDateTotalStmt = (
        select(
            cast(WIBLDataModel.processtime, Date).label("date"),
            func.count().label("submissions")
        )
        .group_by(cast(WIBLDataModel.processtime, Date))
    )

    ConvertedTotalStmt = (
        select(func.count())
        .select_from(WIBLDataModel)
        .where(WIBLDataModel.status == 2)
    )

    ObservationTotalStmt = (
        select(func.sum(WIBLDataModel.observations))
    )

    validatedBitmask = 0b000000111

    ValidatedTotalStmt = (
        select(func.count())
        .select_from(GeoJSONDataModel)
        .where(GeoJSONDataModel.status.op('&')(validatedBitmask) == GeoJSONStatus.VALIDATION_SUCCESSFUL)
    )

    submitBitmask = 0b000111000

    SubmittedTotalStmt = (
        select(func.count())
        .select_from(GeoJSONDataModel)
        .where(GeoJSONDataModel.status.op('&')(submitBitmask) == GeoJSONStatus.UPLOAD_SUCCESSFUL)
    )

    ObserverTotalStmt = (
        select(func.count(func.distinct(WIBLDataModel.platform)))
    )

    previousMonthData = datetime.now(timezone.utc) - timedelta(days=30)
    mostRecentUpload = (
        select(WIBLDataModel.platform,
               func.max(cast(WIBLDataModel.processtime, Date)).label('latest_upload'))
        .group_by(WIBLDataModel.platform)
        .subquery()
    )

    ObserverZeroReportsStmt = (
        select(func.count())
        .select_from(mostRecentUpload)
        .where(
            mostRecentUpload.c.latest_upload < previousMonthData
        )
    )

    ObserverFileTotalStmt = (
        select(WIBLDataModel.platform.label("observer"), func.count(func.distinct(WIBLDataModel.fileid)).label("files"),
               func.sum(WIBLDataModel.soundings).label("soundings"))
        .group_by(WIBLDataModel.platform)
    )

    LocationDataStmt = (
        select(WIBLDataModel.fileid, func.ST_ASGeoJSON(WIBLDataModel.boundingbox).label("GeoJSON"))
    )

    SoundingsTotalStmt = (
        select(func.sum(WIBLDataModel.soundings))
    )

    WIBLTotal = (await db.execute(WIBLTotalStmt)).scalar()
    GeoJSONTotal = (await db.execute(GeoJSONTotalStmt)).scalar()
    SizeTotal = (await db.execute(SizeTotalStmt)).scalar()
    ObservationsTotal = (await db.execute(ObservationTotalStmt)).scalar()
    SoundingsTotal = (await db.execute(SoundingsTotalStmt)).scalar()
    LocationData = (await db.execute(LocationDataStmt)).mappings().all()
    FileDateTotal = (await db.execute(FileDateTotalStmt)).mappings().all()
    ConvertedTotal = (await db.execute(ConvertedTotalStmt)).scalar()
    ValidatedTotal = (await db.execute(ValidatedTotalStmt)).scalar()
    SubmittedTotal = (await db.execute(SubmittedTotalStmt)).scalar()
    ObserverZeroReports = (await db.execute(ObserverZeroReportsStmt)).scalar()
    ObserverTotal = (await db.execute(ObserverTotalStmt)).scalar()
    ObserverFileTotal = (await db.execute(ObserverFileTotalStmt)).mappings().all()

    return {
        "WIBLFileCount": WIBLTotal,
        "GeoJSONFileCount": GeoJSONTotal,
        "SizeTotal": SizeTotal,
        "FileDateTotal": FileDateTotal,
        "ConvertedTotal": ConvertedTotal,
        "ValidatedTotal": ValidatedTotal,
        "SubmittedTotal": SubmittedTotal,
        "ObserverZeroReportsTotal": ObserverZeroReports,
        "ObserverTotal": ObserverTotal,
        "ObservationsTotal": ObservationsTotal,
        "SoundingsTotal": SoundingsTotal,
        "ObserverFileTotal": ObserverFileTotal,
        "LocationData": LocationData
    }
