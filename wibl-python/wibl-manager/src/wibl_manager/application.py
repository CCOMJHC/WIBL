# Main application code for a Flask-based RESTful interface to a metadata database
#
# Once data is being uploaded into the WIBL cloud segment, the Trusted node (and potentially
# data collectors) will want to know that the files have been correctly processed, and then
# uploaded.  This code builds a Flask-based application that exposes a REST API for update
# and management of the metadata in a SQLite database, so that the processing and upload code
# can provide information on the files being manipulated, and another website can be used to
# front this information for the Trusted Node, and provide manipulation tools.  This is
# intentionally very minimal, since we want it to run on as limited a resource as possible.
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
from fastapi import FastAPI
from src.wibl_manager.wibl_data import WIBLDataRouter
from src.wibl_manager.geojson_data import GeoJSONRouter
from src.wibl_manager.heartbeat import HeartbeatRouter
from src.wibl_manager.download import DownloadRouter

app = FastAPI()

# /wibl/{fileid}
app.include_router(WIBLDataRouter)

# /heartbeat
app.include_router(HeartbeatRouter)

# /geojson/{fileid}
app.include_router(GeoJSONRouter)

# /wibl/download/{fileid}
# /geojson/download/{fileid}
# /geojson/save/{fileid}
app.include_router(DownloadRouter)

