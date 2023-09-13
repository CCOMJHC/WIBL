##\module algorithms
#
# Classes, flag enums, and exceptions needed to enable processing algorithms
# This file contains high-level definitions needed to implement specific
# algorithms and algorithm processing, but that need to be referenced across
# the codebase. They are housed here to avoid circular dependency problems.
# As such, this file shouldn't import anything outside of wibl.core.
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

from dataclasses import dataclass
from datetime import datetime
from enum import Flag, auto

from abc import ABC
from typing import List, Dict, Any

from wibl.core.logger_file import DataPacket



class UnknownAlgorithm(Exception):
    pass


## AlgorithmDescriptor describes an algorithm to be run on data from a WIBL file
@dataclass(eq=True, frozen=True)
class AlgorithmDescriptor:
    name: str
    params: str


class AlgorithmPhase(Flag):
    ON_LOAD = auto()
    AFTER_TIME_INTERP = auto()
    AFTER_GEOJSON_CONVERSION = auto()


class WiblAlgorithm(ABC):
    name: str
    phases: AlgorithmPhase

    @classmethod
    def run_on_load(cls, data: List[DataPacket],
                    params: str, verbose: bool) -> List[DataPacket]:
        pass

    @classmethod
    def run_after_time_interp(cls, data: Dict[str, Any],
                              params: str, verbose: bool) -> Dict[str, Any]:
        pass

    @classmethod
    def run_after_geojson_conversion(cls, data: Dict[str, Any],
                                     params: str, verbose: bool) -> Dict[str,Any]:
        pass


## \brief Algorithm support for lineage metadata manipulation
# As we apply algorithms to the data, we need to make sure that we provide some record
# that we did.  This code provides a "lineage" section in the JSON metadata associated
# with the data, adding elements as required.
class Lineage:
    def __init__(self, source: Dict[str,Any]) -> None:
        if 'lineage' in source:
            self.lineage = source['lineage']
        else:
            self.lineage = []

    def add_algorithm(self, name: str, **kwargs) -> None:
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        element = {
            "type":         "Algorithm",
            "timestamp":    timestamp,
            "name":         name
        }
        for key in kwargs:
            element[key] = kwargs[key]
        self.lineage.append(element)

    def export(self) -> List[Dict]:
        return self.lineage
