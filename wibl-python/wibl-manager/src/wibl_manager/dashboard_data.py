from flask import Flask, jsonify, request
from flask_restful import Resource
from flask_sqlalchemy import SQLAlchemy
from threading import Lock
from enum import Enum

class ObserverStatistic:
    def __init__(self):
        self.files = 0
        self.soundings = 0


class DashboardDataModel:
    def __init__(self):
        self._general_data = {
            "WiblFileCount" : 0,
            "GeojsonFileCount": 0,
            "SizeTotal" : 0,
            "DepthTotal" : 0,
            "ConvertedTotal" : 0,
            "ProcessingFailedTotal" : 0,
            "UploadFailedTotal" : 0,
            "ValidatedTotal" : 0,
            "SubmittedTotal" : 0,
            "ObserverTotal": 0,
            "SoundingTotal" : 0
        }
        self._observer_stats = {}
        self._lock = Lock()

    def add(self, value, count):
        with self._lock:
            self._general_data[value] = self._general_data[value] + count
            return self._general_data[value]

    def get(self, value):
        with self._lock:
            return self._general_data[value].get(value, 0)

    def getObservers(self):
        with self._lock:
            return self._observer_stats
    def getAll(self):
        with self._lock:
            return self._general_data

    def subtract(self, value, count):
        with self._lock:
            self._general_data[value] = self._general_data[value] - count

    def addObs(self, value, count, platform):
        with self._lock:
            if platform in self._observer_stats:
                obs_stat = self._observer_stats[platform]
                if value == 'files':
                    obs_stat.files += count
                elif value == 'soundings':
                    obs_stat.soundings += count
            else:
                self._observer_stats[platform] = ObserverStatistic()
                if value == 'files':
                    self._observer_stats[platform].files += count
                elif value == 'soundings':
                    self._observer_stats[platform].soundings += count

    def subObs(self, value, count, platform):
        with self._lock:
            if platform in self._observer_stats:
                obs_stat = self._observer_stats[platform]
                if value == 'files':
                    obs_stat.files -= count
                elif value == 'soundings':
                    obs_stat.soundings -= count

dashDataModel = DashboardDataModel()

class DashboardDataInternal:
    def addGeneral(self, value, count):
        dashDataModel.add(value, count)

    def subtractGeneral(self, value, count):
        dashDataModel.subtract(value, count)

    def addObserverStat(self, value, count, platform):
        dashDataModel.addObs(value, count, platform)

    def subtractObserverStat(self, value, count, platform):
        dashDataModel.subObs(value, count, platform)


class DashboardDataExternal(Resource):
    def get(self, value):
        if value == "allGeneral":
            return dashDataModel.getAll(), 200
        if value == "allObserver":
            return dashDataModel.getObservers(), 200
        else:
            return {value: dashDataModel.get(value)}, 200
