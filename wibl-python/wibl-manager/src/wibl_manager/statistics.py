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
        select(WIBLDataModel.platform.label("observer"), func.count(func.distinct(WIBLDataModel.fileid)).label("files"),
               func.sum(WIBLDataModel.soundings).label("soundings"))
        .group_by(WIBLDataModel.platform)
    )

    WIBLTotal = (await db.execute(WIBLTotalStmt)).scalar()
    GeoJSONTotal = (await db.execute(GeoJSONTotalStmt)).scalar()
    SizeTotal = (await db.execute(SizeTotalStmt)).scalar()
    DepthTotal = 0
    FileDateTotal = (await db.execute(FileDateTotalStmt)).mappings().all()
    ConvertedTotal = (await db.execute(ConvertedTotalStmt)).scalar()
    ValidatedTotal = (await db.execute(ValidatedTotalStmt)).scalar()
    SubmittedTotal =(await db.execute(SubmittedTotalStmt)).scalar()
    ObserverTotal = (await db.execute(ObserverTotalStmt)).scalar()
    ObserverFileTotal = (await db.execute(ObserverFileTotalStmt)).mappings().all()

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
        "WIBLFileCount": WIBLTotal,
        "GeoJSONFileCount": GeoJSONTotal,
        "SizeTotal": SizeTotal,
        "DepthTotal": DepthTotal,
        "FileDateTotal": FileDateTotal,
        "ConvertedTotal": ConvertedTotal,
        "ValidatedTotal": ValidatedTotal,
        "SubmittedTotal": SubmittedTotal,
        "ObserverTotal": ObserverTotal,
        "ObserverFileTotal": ObserverFileTotal
    }
