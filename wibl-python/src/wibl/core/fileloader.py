## \file fileloader.py
# \brief Read a binary data file from the SB2030 data logger
#
# The WIBL data file contains binary data packets that can encapsulate either specific
# NMEA2000 data packets (translated into a simpler format), or wrap a NMEA0183 sentence
# for later intepretation; some metadata and auxiliary packets are also allowed.  In order
# to do something useful, however, we need to read those packets into memory, and then
# fix up the timestamps associated with the packets in the case where they have not been
# added automatically by the logger (this doesn't happen with WIBL loggers, but can be the
# case where other loggers have their data translated into WIBL format for processing and
# submission to DCDB).
#
# Copyright 2021 Center for Coastal and Ocean Mapping & NOAA-UNH Joint
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

from enum import Enum
from typing import List, Tuple
import datetime as dt

import pynmea2 as nmea

from wibl.core import Lineage
from wibl.core.statistics import PktStats, PktFaults
import wibl.core.logger_file as LoggerFile
from wibl.core.algorithm import AlgorithmPhase, AlgorithmDescriptor
from wibl.core.algorithm.runner import run_algorithms


## Exception to report that no adequate source of real-world time information is available
class NoTimeSource(Exception):
    pass


## Encapsulate the types of real-world time information that can be used
#
# In order to establish the relationship between the elapsed time (i.e., time of reception) of
# each packet and the real-world time, we need to use the encoded timestamps in one of the
# packets in the file.  There are a number of choices for this, depending on what type of
# data we have in there; this enumeration provides a controlled list of the options.
class TimeSource(Enum):
    ## Use NMEA2000 packet for SystemTime
    Time_SysTime = 0
    ## Use NMEA2000 packet from GNSS observations
    Time_GNSS = 1
    ## Use NMEA0183 ZDA timestamp packets
    Time_ZDA = 2
    ## Use NMEA0183 RMC minimum data with timestamps
    Time_RMC = 3

## Work out which time source in the WIBL file should be used for real time associations
#
# WIBL files have an elapsed time associated with each packet that tags the time of reception
# of the packet according to the local oscillator (which might not be reliable, but at least
# is monotonic).  There are multiple potential ways to assign a correspondence between these
# timestamps and a real-world time, which depend on the types of packets that we have in the
# file.  This code selects which of several sources is likely to be best.
#
# \param stats  (PktStats) Statistics on which packets have been seen in the data
# \return TImeSource enum for the source of real-world time to use for referencing

def determine_time_source(stats: PktStats) -> TimeSource:
    """Work out which source of time can be used to provide the translation between
       elapsed time (local time-stamps that indicate a monotonic clock tick at the
       logger when the packet is received) to a real world time.  The preference is
       to use NMEA2000 system time packets, but then to attempt to use GNSS packets,
       and then finally to drop back to NMEA0183 ZDA or RMC packets (in that order)
       if required.

        Inputs:
            stats   (PktStats) Statistics on which packets have been seen in the data
        
        Outputs:
            TimeSource enum for which source should be used for timestamping
    """
    if stats.Seen('SystemTime'):
        rtn = TimeSource.Time_SysTime
    elif stats.Seen('GNSS'):
        rtn = TimeSource.Time_GNSS
    elif stats.Seen('ZDA'):
        rtn = TimeSource.Time_ZDA
    elif stats.Seen('RMC'):
        rtn = TimeSource.Time_RMC
    else:
        raise NoTimeSource()
    return rtn

## Load the contents of a WIBL file and patch up any missing elapsed time entries
#
# We need to work over the data in a number of stages, so to avoid having to read the file
# more than once, we load all of the packets into memory first.  This allows the code to
# estimate statistics on how many packets have been read, and of what types (and if they have
# faults in their interpretation), and also to patch up any missing elapsed time entries on
# the packets (which can happen if another logger's data is translated into WIBL format for
# processing).
#
# \param filename       Filename to load for WIBL data
# \param verbose        Flag: set True to report more information on parsing.
# \param maxreports     Limit on how many errors should be reported before suppressing and summarising
# \param process_algorithms Flag: set to True to enable execution of algorithms for phase `AlgorithmPhase.ON_LOAD`
# \return Tuple of PktStats, TimeSource, a list of DataPacket, and a list of AlgorithmDescriptor entries from the file
def load_file(filename: str, lineage: Lineage, verbose: bool, maxreports: int, *,
              process_algorithms: bool = True) -> \
        Tuple[PktStats, TimeSource, List[LoggerFile.DataPacket], List[AlgorithmDescriptor]]:
    """Load the entirety of a WIBL binary file into memory, in the process determining the type of time
       source that can be used to add timestamps to the data, and fixing up any messages that don't have
       any elapsed time (i.e., time of reception) stamps.  This provides a set of data where it should
       be possible to continue processing without having to worry about missing information, although it
       does not guarantee that all of the data in the packets will be valid.

       Inputs:
            filename        Local filesystem name of the WIBL file to open and read
            lineage         `wibl.core.Lineage` instance used to track any processing done on data from `filename`
            verbose         Flag: set True to extra information on the process
            maxreports      Maximum number of errors per packet to report before summarising
            process_algorithms Flag: set to True to enable execution of algorithms for phase `AlgorithmPhaseON_LOAD`

        Outputs:
            stats           (PktStats) Statistics on which packets have been seen, and any problems
            time-source     (TimeSource) Indicator of which source of time should be used for real-time information
            packets         List[LoggerFile.DataPacket] List if packets derived from the WIBL file
            alg_desc        List[AlgorithmDescriptor] List of algorithms derived from the WIBL file
    """
    stats: PktStats = PktStats(maxreports)
    packets: List[LoggerFile.DataPacket] = []
    alg_desc: List[AlgorithmDescriptor]

    # First read all packets into packets_raw so that we can find algorithm packets
    packets_raw: List[LoggerFile.DataPacket] = []
    algorithms_raw = []
    with open(filename, 'rb') as file:
        source = LoggerFile.PacketFactory(file)
        while source.has_more():
            pkt = source.next_packet()
            if pkt is not None:
                packets_raw.append(pkt)
                # Check for algorithm packet
                if isinstance(pkt, LoggerFile.AlgorithmRequest):
                    stats.Observed(pkt.name())
                    algorithms_raw.append(AlgorithmDescriptor(name=pkt.algorithm.decode('UTF-8'),
                                                              params=pkt.parameters.decode('UTF-8'))
                    )
    # Store algorithm descriptors in a list using value-less dict, which are ordered by key,
    # to filter duplicates without using a set, which does not preserve order
    alg_desc = list(dict.fromkeys(algorithms_raw))
    del algorithms_raw

    if process_algorithms:
        packets_raw = run_algorithms(packets_raw,
                                     alg_desc,
                                     AlgorithmPhase.ON_LOAD,
                                     filename,
                                     lineage,
                                     verbose)

    # Now iterate over stored packets to record stats needed for timestamp interpolation
    needs_elapsed_time_fixup = False
    packet_count = 0
    for pkt in packets_raw:
        if isinstance(pkt, LoggerFile.SerialString):
            # We need to pull out the NMEA0183 recognition string
            try:
                name = pkt.data[3:6].decode('UTF-8')
                stats.Observed(name)
            except UnicodeDecodeError:
                stats.Fault(str(pkt), PktFaults.DecodeFault)
                continue
        else:
            stats.Observed(pkt.name())
        packet_count += 1
        if pkt.elapsed == 0:
            needs_elapsed_time_fixup = True
        if verbose and packet_count % 50000 == 0:
            print(f'Reading file: passing {packet_count} packets ...')
        packets.append(pkt)
    del packets_raw

    # We need some form of connection from elapsed time stamps (i.e., when the packet is received
    # at the logger) and a real time, so that we can interpolate to real-time information for all
    # of the data.  There are a number of potential sources, including (in descending order of
    # preference), NMEA2000 SystemTime or GNSS, or NMEA0183 ZDA or RMC messages.  This code determines
    # which to use.
    timesource = determine_time_source(stats)

    # Under some circumstances, it is possible that packets will have no elapsed time in them
    # and therefore cannot be time-interpolated to a real time.  This generally is because the
    # source (i.e., from a non-WIBL logger) doesn't record elapsed times.  The best we can do in
    # this case is to fabricate an elapsed time based on whatever times we have, and then assign
    # an elapsed time to what's left based on the assumption that they had to have appeared at
    # some point between bordering timestamped data.  It's messy, but it's the best you're going
    # to get from loggers that don't record decent data ...
    if needs_elapsed_time_fixup:
        if timesource == TimeSource.Time_ZDA or timesource == TimeSource.Time_RMC:
            # If we're using NMEA0183 strings for timing, then we have the possibility of there being
            # packets where there's no elapsed time stamp, and we need to unpack the NMEA string
            # for its real-time stamp, and then assign an elapsed time based on this.  This sets us up for
            # generating intermediate elapsed time estimates subsequently.
            realtime_elapsed_zero = None
            for n in range(len(packets)):
                if isinstance(packets[n], LoggerFile.SerialString) and packets[n].elapsed == 0:
                    # Decode the packet string to identify ZDA/RMC
                    msg_id = packets[n].data[3:6].decode('UTF-8')
                    if (msg_id == 'ZDA' and timesource == TimeSource.Time_ZDA) or (msg_id == 'RMC' and timesource == TimeSource.Time_RMC):
                        if len(packets[n].data) < 11:
                            if verbose and stats.FaultCount(msg_id) < stats.fault_limit:
                                print(f'Error: short message {packets[n].data}; ignoring.')
                            stats.Fault(msg_id, PktFaults.ShortMessage)
                        else:
                            try:
                                msg = nmea.parse(packets[n].data.decode('UTF-8'))
                                if msg.datestamp is not None and msg.timestamp is not None:
                                    pkt_real_time = dt.datetime.combine(msg.datestamp, msg.timestamp)
                                    if realtime_elapsed_zero is None:
                                        realtime_elapsed_zero = pkt_real_time
                                        packets[n].elapsed = 0
                                    else:
                                        packets[n].elapsed = 1000.0*(pkt_real_time.timestamp() - realtime_elapsed_zero.timestamp())
                            except UnicodeDecodeError:
                                if verbose and stats.FaultCount(msg_id) < stats.fault_limit:
                                    print(f'Error: unicode decode failure on NMEA string; ignoring.')
                                stats.Fault(msg_id, PktFaults.DecodeFault)
                                continue
                            except nmea.ParseError:
                                if verbose and stats.FaultCount(msg_id) < stats.fault_limit:
                                    print(f'Error: parse error in NMEA string {packets[n].data}; ignoring.')
                                stats.Fault(msg_id, PktFaults.ParseFault)
                                continue
                            except TypeError:
                                if verbose and stats.FaultCount(msg_id) < stats.fault_limit:
                                    print(f'Error: type error unpacking NMEA string; ignoring.')
                                stats.Fault(msg_id, PktFaults.TypeFault)
                                continue
                    if stats.FaultCount(msg_id) >= stats.fault_limit:
                        print(f'Warning: too many errors on NMEA0183 packet {msg_id}; suppressing further reporting.')
        
        # We now need to patch up any packets that don't have an elapsed time using the mean of the
        # two nearest (ahead and behind) packets with known elapsed times.  The algorithm here finds
        # pairs of elapsed times, and then fills in all of the packets with no elapsed times between
        # them.
        oldest_position = None
        for n in range(len(packets)):
            if packets[n].elapsed == 0:
                if n > 0 and packets[n-1].elapsed > 0:
                    oldest_position = n - 1
            else:
                if oldest_position is not None:
                    if n - oldest_position > 1:
                        # This means we hit the end of a potential bracket, so we need to process the elapsed times
                        target_elapsed_time = (packets[oldest_position].elapsed + packets[n].elapsed)/2.0
                        for i in range(n - oldest_position - 1):
                            packets[oldest_position + 1 + i].elapsed = target_elapsed_time
                        oldest_position = None
        
        # Finally, we replace any timestamps that weren't interpolated to make sure that there's no question
        # that they're not valid.
        for n in range(len(packets)):
            #print(f'{n}: {packets[n].elapsed}')
            if packets[n].elapsed == 0:
               packets[n].elapsed = None

    return stats, timesource, packets, alg_desc
