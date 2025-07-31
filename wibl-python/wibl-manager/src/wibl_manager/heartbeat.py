# Health check endpoint to allow service managers to ensure that the system is up
#
# Once cloud-deployed, most systems will want to know whether the local REST endpoint
# is still up and running.  This provides a simple GET interface that allows for a quick
# check that the service is still responding.
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
from src.wibl_manager import ReturnCodes

from fastapi import APIRouter, Depends, HTTPException
from .database import get_async_db
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

HeartbeatRouter = APIRouter()

@HeartbeatRouter.get("/heartbeat")
async def getHeartbeat(db=Depends(get_async_db)):
    """
    A simple check on whether the service and database is still running.  This returns a status code
    for the service, but no other information.

    """
    try:
        result = await db.execute(select(1))
        if not result:
            raise HTTPException(status_code=500, detail="Failed database connection")
        else:
            return ReturnCodes.OK.value

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail="Failed database connection")

