##\module deduplicate
# \brief Algorithm for deplicating depth values in the provided data
#
# On some systems, it's possible to get duplicated depths from the echosounder or control
# system (typically because the system is generating positions every second, and the depths
# aren't being updated that fast).  This algorithm does an exhaustive check through all
# of the depths provided in sequence, and provides a boolean NumPy vector that provides an
# indication whether the depth is valid (True) or can be dropped (False).  The original data
# is not modified.
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
from typing import Dict, Any

import numpy as np

from wibl.core.algorithm import SOURCE, AlgorithmPhase, WiblAlgorithm
from wibl.core import Lineage

__version__ = '1.0.0'

ALG_NAME = 'deduplicate'


def find_duplicates(source: Dict, verbose: bool) -> np.ndarray:
    current_depth = 0
    d = []
    for n in range(len(source['depth']['z'])):
        if source['depth']['z'][n] != current_depth:
            d.append(n)
            current_depth = source['depth']['z'][n]
    rtn = np.array(d)
    if verbose:
        n_ip_points = len(source['depth']['z'])
        n_op_points = len(rtn)
        print(f'After deduplication, total {n_op_points} points selected from {n_ip_points}')
    return rtn


def deduplicate_depth(source: Dict[str,Any], params: str,  lineage: Lineage, verbose: bool) -> Dict[str,Any]:
    n_ip_points = len(source['depth']['z'])
    index = find_duplicates(source, verbose)
    source['depth']['t'] = source['depth']['t'][index]
    source['depth']['lat'] = source['depth']['lat'][index]
    source['depth']['lon'] = source['depth']['lon'][index]
    source['depth']['z'] = source['depth']['z'][index]
    
    # To memorialise that we did something, we add an entry to the lineage segment of
    # the metadata headers in the data.
    n_op_points = len(source['depth']['z'])
    lineage.add_algorithm_element(name=ALG_NAME, parameters=params, source=SOURCE, version=__version__,
                                  comment=f'Selected {n_op_points} non-duplicate depths from {n_ip_points} in input.')

    return source


class Deduplicate(WiblAlgorithm):
    name: str = ALG_NAME
    phases: AlgorithmPhase = AlgorithmPhase.AFTER_TIME_INTERP

    @classmethod
    def run_after_time_interp(cls,
                              data: Dict[str, Any],
                              params: str,
                              lineage: Lineage,
                              verbose: bool) -> Dict[str, Any]:
        return deduplicate_depth(data, params, lineage, verbose)
