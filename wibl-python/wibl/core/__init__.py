##\file __init__.py
# \brief WIBL core library.
#
# Copyright 2022 Center for Coastal and Ocean Mapping & NOAA-UNH Joint
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
from datetime import datetime
from typing import List, Dict
from copy import deepcopy


class EnvVarUndefinedException(Exception):
    def __init__(self, var_name: str):
        super().__init__(f"{var_name} is not a defined environment variable.")


def getenv(var_name: str) -> str:
    if var_name not in os.environ:
        raise EnvVarUndefinedException(var_name)
    return os.environ[var_name]


## \brief Algorithm support for lineage metadata manipulation
# As we apply algorithms to the data, we need to make sure that we provide some record
# that we did.  This code provides a "lineage" section in the JSON metadata associated
# with the data, adding elements as required.
class Lineage:
    def __init__(self) -> None:
        self.lineage: List[Dict] = []

    @staticmethod
    def create_algorithm_element(name: str, **kwargs) -> Dict:
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        element = {
            "type": "Algorithm",
            "timestamp": timestamp,
            "name": name
        }
        for key in kwargs:
            element[key] = kwargs[key]
        return element

    def add_element(self, element: Dict):
        self.lineage.append(element)

    def add_algorithm_element(self, name: str, **kwargs) -> None:
        self.lineage.append(Lineage.create_algorithm_element(name, **kwargs))

    def export(self) -> List[Dict]:
        lin_exp: List[Dict] = deepcopy(self.lineage)
        for e in lin_exp:
            if 'parameters' in e:
                # Convert parameters from a string of comma-separated key-value pairs to a dict
                # for export to JSON
                if e['parameters'] != '':
                    e['parameters'] = dict([kvp.split('=') for kvp in e['parameters'].split(',')])
        return lin_exp

    def empty(self) -> bool:
        return len(self.lineage) == 0
