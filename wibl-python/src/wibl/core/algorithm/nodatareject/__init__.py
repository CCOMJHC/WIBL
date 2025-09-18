##\module nodatareject
# \brief Algorithm for rejecting no-data values (for position, depth, or time) in the provided data
#
# Currently no-data filtering is only performed on NMEA 2000 packets.
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
from typing import List
from datetime import datetime, timezone
from itertools import filterfalse
from collections import Counter
from functools import partial

import wibl.core.logger_file as LoggerFile
from wibl.core.algorithm import SOURCE, AlgorithmPhase, WiblAlgorithm
from wibl.core import Lineage

__version__ = '1.0.0'

ALG_NAME = 'nodatareject'
NA_DATA_DOUBLE: float = -1e9
EPOCH_START = datetime(1970, 1, 1).replace(tzinfo=timezone.utc)
SECONDS_PER_DAY = 86_400


def get_days_since_epoch() -> int:
    return (datetime.utcnow().replace(tzinfo=timezone.utc) - EPOCH_START).days


def reject_predicate(pkt: LoggerFile.DataPacket, *,
                     counters: Counter,
                     days_since_epoch: int,
                     verbose: bool = False) -> bool:
    counters['num_packets'] += 1
    if isinstance(pkt, LoggerFile.GNSS):
        counters['num_packets_gnss'] += 1
        if pkt.longitude == NA_DATA_DOUBLE or pkt.latitude == NA_DATA_DOUBLE:
            if verbose:
                print(f"Filtering out packet {str(pkt)}")
            counters['num_filtered_gnss'] += 1
            return True

    if isinstance(pkt, LoggerFile.Depth):
        counters['num_packets_depth'] += 1
        if pkt.depth == NA_DATA_DOUBLE:
            if verbose:
                print(f"Filtering out packet {str(pkt)}")
            counters['num_filtered_depth'] += 1
            return True

    if isinstance(pkt, LoggerFile.SystemTime):
        counters['num_packets_systime'] += 1
        if pkt.date > days_since_epoch or pkt.timestamp > SECONDS_PER_DAY:
            if verbose:
                print(f"Filtering out packet {str(pkt)}")
            counters['num_filtered_systime'] += 1
            return True

    # Don't filter out this packet
    return False


def reject_nodata(data: List[LoggerFile.DataPacket],
                  params: str,
                  lineage: Lineage,
                  verbose: bool) -> List[LoggerFile.DataPacket]:
    days_since_epoch: int = get_days_since_epoch()
    c: Counter = Counter()
    predicate = partial(reject_predicate, counters=c, days_since_epoch=days_since_epoch, verbose=verbose)
    data = [pkt for pkt in filterfalse(predicate, data)]

    num_filtered: int = c['num_filtered_gnss'] + c['num_filtered_depth'] + c['num_filtered_systime']
    lineage.add_algorithm_element(name=ALG_NAME, parameters=params, source=SOURCE, version=__version__,
                                  comment=
                                  (f"Filtered {num_filtered} packets of {c['num_packets']} total. "
                                   f"Filtered {c['num_filtered_gnss']} of {c['num_packets_gnss']} GNSS packets. "
                                   f"Filtered {c['num_filtered_depth']} of {c['num_packets_depth']} Depth packets. "
                                   f"Filtered {c['num_filtered_systime']} of {c['num_packets_systime']} SystemTime packets."
                                   )
                                  )
    return data


class NoDataReject(WiblAlgorithm):
    name: str = ALG_NAME
    phases: AlgorithmPhase = AlgorithmPhase.ON_LOAD

    @classmethod
    def run_on_load(cls,
                    data: List[LoggerFile.DataPacket],
                    params: str,
                    lineage: Lineage,
                    verbose: bool) -> List[LoggerFile.DataPacket]:
        return reject_nodata(data, params, lineage, verbose)
