# Application global variables needed to bring up the whole app, and the database
#
# In the Flask environment, it is expected that the app variable is a global, and the
# SQLAlchemy instance variable has to be constructed before the data models can be
# specified (since they need an embedded type from the instance of the database).  This
# file provides these two variables so that they can be imported into other modules.
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
import boto3
from src.wibl_manager.dashboard_data import DashboardDataInternal
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

MANAGER_DATABASE_URI = os.environ.get('MANAGER_DATABASE_URI', 'postgresql://postgres:postgres@localhost:6432/db')
S3_WIBL_BUCKET_NAME = "wibl-test"
S3_GEOJSON_BUCKET_NAME = "geojson-test"

app = Flask('WIBL-Manager')
app.config['SQLALCHEMY_DATABASE_URI'] = MANAGER_DATABASE_URI

db = SQLAlchemy(app)

dashData = DashboardDataInternal()
