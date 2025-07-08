from src.wibl_manager import ReturnCodes, WIBLStatus, GeoJSONStatus
from .database import Base, get_async_db
from pydantic import BaseModel
from datetime import datetime, timezone
from http.client import HTTPException
from typing import Optional
from sqlalchemy import select, func, cast, Date
from fastapi import APIRouter, HTTPException, Depends
from src.wibl_manager.schemas import WIBLDataModel, GeoJSONDataModel
import asyncio

class StatsMarsh(BaseModel):
    WIBLFileCount: int
    GeoJSONFileCount: int
    FileSizeTotal: int
    DepthTotal: int
    ConvertedTotal: int
    ValidatedTotal: int
    SubmittedTotal: int
    ObserverTotal: int
    ObserverStats: int


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

    ValidatedTotalStmt = (
        select(func.count())
        .select_from(GeoJSONDataModel)
        .where(GeoJSONDataModel.status.op('&')(0b000000111) == 0b000000010)
    )

    SubmittedTotalStmt = (
        select(func.count())
        .select_from(GeoJSONDataModel)
        .where(GeoJSONDataModel.status.op('&')(0b000111000) == 0b000010000)
    )

    ObserverTotalStmt = (
        select(func.count(func.distinct(WIBLDataModel.platform)))
    )

    ObserverFileTotalStmt = (
        select(WIBLDataModel.platform, func.count(func.distinct(WIBLDataModel.fileid)).label("files"),
               func.sum(WIBLDataModel.soundings).label("soundings"))
        .group_by(WIBLDataModel.platform)
    )

    results = await asyncio.gather(
        db.execute(WIBLTotalStmt),
        db.execute(GeoJSONTotalStmt),
        db.execute(SizeTotalStmt),
        db.execute(FileDateTotalStmt),
        db.execute(ConvertedTotalStmt),
        db.execute(ValidatedTotalStmt),
        db.execute(SubmittedTotalStmt),
        db.execute(ObserverTotalStmt),
        db.execute(ObserverFileTotalStmt)
    )

    WIBLTotal = results[0].scalar_one_or_none()
    GeoJSONTotal = results[1].scalar_one_or_none()
    SizeTotal = results[2].scalar_one_or_none()
    DepthTotal = 0
    FileDateTotal = results[3].all()
    ConvertedTotal = results[4].scalar_one_or_none()
    ValidatedTotal = results[5].scalar_one_or_none()
    SubmittedTotal = results[6].scalar_one_or_none()
    ObserverTotal = results[7].scalar_one_or_none()
    ObserverFileTotal = results[8].all()


    # print(f"WIBL Total SQL: {WIBLTotalStmt.compile(compile_kwargs={'literal_binds': True})}")
    # print(f"GeoJSON Total SQL: {GeoJSONTotalStmt.compile(compile_kwargs={'literal_binds': True})}")
    # print(f"File Date Total SQL: {FileDateTotalStmt.compile(compile_kwargs={'literal_binds': True})}")
    # print(f"File Size Total SQL: {SizeTotalStmt.compile(compile_kwargs={'literal_binds': True})}")
    # print(f"Converted Total SQL: {ConvertedTotalStmt.compile(compile_kwargs={'literal_binds': True})}")
    # print(f"Validated Total SQL: {ValidatedTotalStmt.compile(compile_kwargs={'literal_binds': True})}")
    # print(f"Submitted Total SQL: {SubmittedTotalStmt.compile(compile_kwargs={'literal_binds': True})}")
    # print(f"Observer Total SQL: {ObserverTotalStmt.compile(compile_kwargs={'literal_binds': True})}")
    # print(f"Converted List SQL: {ObserverListStmt.compile(compile_kwargs={'literal_binds': True})}")
    # print(f"Observer File Total SQL: {ObserverFileTotalStmt.compile(compile_kwargs={'literal_binds': True})}")

    return {
        "WiblFileCount": WIBLTotal,
        "GeojsonFileCount": GeoJSONTotal,
        "SizeTotal": SizeTotal,
        "DepthTotal": DepthTotal,
        "FileDateTotal": FileDateTotal,
        "ConvertedTotal": ConvertedTotal,
        "ValidatedTotal": ValidatedTotal,
        "SubmittedTotal": SubmittedTotal,
        "ObserverTotal": ObserverTotal,
        "ObserverFileTotal": ObserverFileTotal
    }
