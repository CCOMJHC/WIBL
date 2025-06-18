from flask import Flask, jsonify, request
from flask_restful import Resource
from flask_sqlalchemy import SQLAlchemy
from threading import Lock
from enum import Enum
from app_globals import dashData

class DashboardDataModel:
    def __init__(self):
        self._data = {
            "WiblFileCount" : 0,
            "GeojsonFileCount": 0,
            "SizeTotal" : 0,
            "DepthTotal" : 0,
            "ConvertedTotal" : 0,
            "ProcessingFailedTotal" : 0,
            "UploadFailedTotal" : 0,
            "ValidatedTotal" : 0,
            "SubmittedTotal" : 0,
            "ObserverTotal": 0
        }
        self._lock = Lock()

    def add(self, value, count):
        with self._lock:
            self._data[value] = self._data[value] + count
            return self._data[value]

    def get(self, value):
        with self._lock:
            return self._data[value].get(value, 0)

    def getAll(self):
        with self._lock:
            return self._data

    def subtract(self, value, count):
        with self._lock:
            self._data[value] = self._data[value] - count


class DashboardData(Resource):
    def get(self, value):
        if value == "all":
            return dashData.getAll(), 200
        else:
            return {value: dashData.get(value)}, 200

    def post(self, value):
        data = request.get_json(silent=True) or {}
        count = data.get("count", 1)
        return {value: dashData.add(value, count)}, 200

    def delete(self, value):
        data = request.get_json(silent=True) or {}
        count = data.get("count", 1)
        return {value: dashData.subtract(value, count)}, 204

