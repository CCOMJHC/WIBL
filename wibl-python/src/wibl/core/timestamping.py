##\file Timestamping.py
# \brief Read a binary data file from the SB2030 data logger, and generate timestamped data
#
# The SB2030 data logger reports, for each packet received, the elapsed time with respect
# to the logger's time ticker, and the data.  It also estimates the real time for the packet's
# reception time using whatever time information it has available, in real-time, using a forward
# extrapolation of the last time reference.  Of course, this isn't great, because it has to be
# causal.  This code is designed to get around that by reading all of the data to find the best
# time reference information, and then going back through again to provide timestamps for the
# packets based on all of the time reference data.
#    The code is pretty simple, just doing linear interpolation between timestamps of the reference
# time in order to generate the real-world times.  Reference time is, by preference, NMEA2000 SystemTime,
# then the timestamps from NMEA2000 GNSS packets, and then finally from NMEA0183 ZDA or RMC packets if
# there's nothing else available.
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

from typing import Dict, Any
import datetime as dt
import pynmea2 as nmea

import wibl.core.logger_file as LoggerFile
from wibl.core.fileloader import TimeSource, load_file
from wibl.core.fileloader import NoTimeSource as flNoTimeSource
from wibl.core.algorithm import AlgorithmPhase, UnknownAlgorithm
from wibl.core.algorithm.runner import run_algorithms
from wibl.core import Lineage
from wibl.core.interpolation import InterpTable
from wibl.core.statistics import PktStats, PktFaults


## Exception to indicate that there is no data to interpolate from the WIBL file
class NoData(Exception):
    pass

## Exception to indicate that the WIBL file is newer than the latest version understood by the code
class NewerDataFile(Exception):
    pass

## Exception to indicate that no time source was foundß
class NoTimeSource(Exception):
    pass

## Construct an encoded integer representing a protocol version
#
# Create an encoded integer that represents a combined major/minor version
# number for a protocol.  This allows for simple integer comparison to determine
# newer/earlier/equivalent versions.
#
# \param major  Major version for the protocol implementation
# \param minor  Minor version for the protocol implementation
# \return Encoded integer for protocol version

def protocol_version(major: int, minor: int) -> int:
    """Convert the version information for the serialiser protocol to an integer so that we can do simple
       comparisons against what we find in the file being processed.

        Inputs:
            major   (int) Major verion number for a protocol implementaiton
            minor   (int) Minor version number for a protocol implementation
        Output:
            (int) Combined (encoded) version indicator
    """
    return major * 1000 + minor

# We need to make sure that we aren't asked to process a version of the data format newer than we know
# (although we should accept anything older).  These define the latest version of the protocol that's
# understood by the code.

## Latest major protocol version understood by the code
protocol_version_major = 1
## Latest minor protocol version understood by the code
protocol_version_minor = 3
 
## Maximum protocol version understood by the code
maximum_version = protocol_version(protocol_version_major, protocol_version_minor)

## Construct a dictionary of interpolated observation data from a given WIBL file
#
# This carries out the basic read-convert-preprocess operations for a WIBL binary file, loading in all
# of the packets, fixing up any missing elapsed timestamps on the packets using real-world indicators
# in the packets, and then assigning real-world times to all of the recorded observable data packets,
# interpolating the positioning information at those points to give a (time, position, observation) set
# for each observation data set.  The data are encoded into a dictionary with auxiliary information
# such as metadata identifying the logger, required processing algorithms, etc. If kwarg 'process_algorithms'
# is set to True, execution of any algorithms defined in WIBL file `filename` will be enabled for phases
# `AlgorithmPhase.ON_LOAD` and `AlgorithmPhase.AFTER_TIME_INTERP`.
#
# \param filename               Local filename for the source WIBL file
# \param elapsed_time_quantum   Maximum value that can be represented by the elapsed times in the packets
# \param lineage                `wibl.core.Lineage` instance used to track any processing done on data from `filename`
# \param kwargs                 Keyword dictionary for 'verbose' (bool), 'fault_limit' (int),
#   and 'process_algorithms' (bool).
# \return Dictionary mapping identification names for the various datasets to the interpolated data arrays
def time_interpolation(filename: str, lineage: Lineage, elapsed_time_quantum: int, **kwargs) -> Dict[str, Any]:
    verbose = False
    fault_limit = 10
    if 'verbose' in kwargs:
        verbose = kwargs['verbose']
    if 'fault_limit' in kwargs:
        fault_limit = kwargs['fault_limit']
    process_algorithms: bool = True
    if 'process_algorithms' in kwargs:
        process_algorithms = kwargs['process_algorithms']
    
    # Pull all of the packets out of the file, and fix up any preliminary problems
    try:
        stats, time_source, packets, algorithms = load_file(filename, lineage, verbose, fault_limit,
                                                            process_algorithms=process_algorithms)
    except flNoTimeSource as e:
        if verbose:
            print(f'Failed to determine a valid time source from file: {e}')
        raise NoTimeSource()
    except UnknownAlgorithm as e:
        if verbose:
            print(f'Unable to load file due to unknown algorithm encountered: {str(e)}')
        raise e
    
    if verbose:
        print(stats)

    time_table = InterpTable(['ref',])              # Mapping of elapsed time to real-world time
    position_table = InterpTable(['lon', 'lat'])    # Mapping of elapsed time to position information
    depth_table = InterpTable(['z',])               # Mapping of elapsed time to depth
    hdg_table = InterpTable(['h',])                 # Mapping of elapsed time to heading information
    wattemp_table = InterpTable(['temp',])          # Mapping of elapsed time to water temperature
    wind_table = InterpTable(['dir', 'spd'])        # Mapping of elapsed time to wind direction and speed

    logger_name = None      # Name of the logger (usually the identification)
    platform_name = None    # Name of the platform doing the logging
    metadata = None         # Any JSON metadata string provided in the WIBL file

    seconds_per_day = 24.0 * 60.0 * 60.0

    elapsed_offset = 0  # Estimate of the offset in milliseconds to add to elapsed times recorded (if we lap the counter)
    last_elapsed = 0    # Marker for the last observed elapsed time (to check for lapping the counter)

    stats = PktStats(fault_limit) # Reset statistics so that we don't double count on the second pass
    
    for pkt in packets:
        # There are some informational packets in the file that we can handle even if they
        # don't have assigned elapsed times; we deal with these first so that we can then
        # safely ignore any packets that are not time-enabled.
        if isinstance(pkt, LoggerFile.SerialiserVersion):
            stats.Observed(pkt.name())
            if protocol_version(pkt.major, pkt.minor) > maximum_version:
                raise NewerDataFile()
            logger_version = f'{pkt.major}.{pkt.minor}/{pkt.nmea2000_version}/{pkt.nmea0183_version}'
        if isinstance(pkt, LoggerFile.Metadata):
            stats.Observed(pkt.name())
            logger_name = pkt.logger_name
            platform_name = pkt.ship_name
        if isinstance(pkt, LoggerFile.JSONMetadata):
            stats.Observed(pkt.name())
            metadata = pkt.metadata_element.decode('UTF-8')
        
        # After this point, any packet that we're interested in has to have an elapsed time assigned
        if pkt.elapsed is None:
            continue

        # We need to check that the elapsed ms counter hasn't wrapped around since
        # the last packet.  If so, we need to increment the elapsed time base stamp.
        # This method is very simple, and will fail mightily if the elapsed times in
        # the log file are not sequential and monotonic (modulo the elapsed_time_quantum).
        if pkt.elapsed < last_elapsed:
            elapsed_offset = elapsed_offset + elapsed_time_quantum
        last_elapsed = pkt.elapsed

        if isinstance(pkt, LoggerFile.SystemTime):
            stats.Observed(pkt.name())
            if time_source == TimeSource.Time_SysTime:
                time_table.add_point(pkt.elapsed + elapsed_offset, 'ref', pkt.date * seconds_per_day + pkt.timestamp)
        if isinstance(pkt, LoggerFile.Depth):
            stats.Observed(pkt.name())
            depth_table.add_point(pkt.elapsed + elapsed_offset, 'z', pkt.depth)
        if isinstance(pkt, LoggerFile.GNSS):
            stats.Observed(pkt.name())
            if time_source == TimeSource.Time_GNSS:
                time_table.add_point(pkt.elapsed + elapsed_offset, 'ref', pkt.msg_date * seconds_per_day + pkt.msg_timestamp)
            position_table.add_points(pkt.elapsed + elapsed_offset, ('lat', 'lon'), (pkt.latitude, pkt.longitude))
        if isinstance(pkt, LoggerFile.SerialString):
            try:
                pkt_name = pkt.data[3:6].decode('UTF-8')
                stats.Observed(pkt_name)
                data = pkt.data.decode('UTF-8')
                if stats.FaultCount(pkt_name) == stats.fault_limit:
                    print(f'Warning: too many errors on packet {pkt_name}; supressing further reporting.')
                if len(data) > 11:
                    try:
                        msg = nmea.parse(data)
                        if isinstance(msg, nmea.ZDA) and time_source == TimeSource.Time_ZDA:
                            if msg.datestamp is not None and msg.timestamp is not None:
                                reftime = dt.datetime.combine(msg.datestamp, msg.timestamp)
                                time_table.add_point(pkt.elapsed + elapsed_offset, 'ref', reftime.timestamp())
                        if isinstance(msg, nmea.RMC) and time_source == TimeSource.Time_RMC:
                            if msg.datestamp is not None and msg.timestamp is not None:
                                reftime = dt.datetime.combine(msg.datestamp, msg.timestamp)
                                time_table.add_point(pkt.elapsed + elapsed_offset, 'ref', reftime.timestamp())
                        if isinstance(msg, nmea.GGA) or isinstance(msg, nmea.GLL):
                            if msg.latitude is not None and msg.longitude is not None:
                                position_table.add_points(pkt.elapsed + elapsed_offset, ('lat', 'lon'), (msg.latitude, msg.longitude))
                        if isinstance(msg, nmea.DBT):
                            if msg.depth_meters is not None:
                                depth = float(msg.depth_meters)
                                depth_table.add_point(pkt.elapsed + elapsed_offset, 'z', depth)
                        if isinstance(msg, nmea.DPT):
                            if msg.depth is not None:
                                depth = float(msg.depth)
                                depth_table.add_point(pkt.elapsed + elapsed_offset, 'z', depth)
                        if isinstance(msg, nmea.HDT):
                            if msg.heading is not None:
                                heading = float(msg.heading)
                                hdg_table.add_point(pkt.elapsed + elapsed_offset, 'h', heading)
                        if isinstance(msg, nmea.MWD):
                            if msg.direction_true is not None and msg.wind_speed_meters is not None:
                                direction = float(msg.direction_true)
                                speed = float(msg.wind_speed_meters)
                                wind_table.add_points(pkt.elapsed + elapsed_offset, ('dir', 'spd'), (direction, speed))
                        if isinstance(msg, nmea.MTW):
                            if msg.temperature is not None:
                                temp = float(msg.temperature)
                                wattemp_table.add_point(pkt.elapsed + elapsed_offset, 'temp', temp)
                    except nmea.ParseError as e:
                        if verbose and stats.FaultCount(pkt_name) < stats.fault_limit:
                            print(f'Parse error: {e}')
                        stats.Fault(pkt_name, PktFaults.ParseFault)
                        continue
                    except AttributeError as e:
                        if verbose and stats.FaultCount(pkt_name) < stats.fault_limit:
                            print(f'Attribute error: {e}')
                        stats.Fault(pkt_name, PktFaults.AttributeFault)
                        continue
                    except TypeError as e:
                        if verbose and stats.FaultCount(pkt_name) < stats.fault_limit:
                            print(f'Type error: {e}')
                        stats.Fault(pkt_name, PktFaults.TypeFault)
                        continue
                    except nmea.ChecksumError as e:
                        if verbose and stats.FaultCount(pkt_name) < stats.fault_limit:
                            print(f'Checksum error: {e}')
                        stats.Fault(pkt_name, PktFaults.ChecksumFault)
                        continue
                else:
                    # Packets have to be at least 11 characters to contain all of the mandatory elements.
                    # Usually a short packet is broken in some fashion, and should be ignored.
                    if verbose and stats.FaultCount(pkt_name) < stats.fault_limit:
                        print(f'Error: short message: {data}; ignoring.')
                    stats.Fault(pkt_name, PktFaults.ShortMessage)
            except UnicodeDecodeError as e:
                if verbose and stats.FaultCount(pkt_name) < stats.fault_limit:
                    print(f'Decode error: {e}')
                stats.Fault(pkt_name, PktFaults.DecodeFault)
                continue
    if verbose:
        print('Reference time table length = ', time_table.n_points())
        print('Position table length = ', position_table.n_points())
        print('Depth observations = ', depth_table.n_points())
        print(stats)

    if depth_table.n_points() < 1:
        raise NoData()
        
    # Finally, do the interpolations to generate the output data, and package it up as a dictionary for return
    depth_timepoints = depth_table.ind()
    z_times = time_table.interpolate(['ref'], depth_timepoints)[0]
    z_lat, z_lon = position_table.interpolate(['lat', 'lon'], depth_timepoints)
    
    hdg_timepoints = hdg_table.ind()
    hdg_times = time_table.interpolate(['ref'], hdg_timepoints)[0]
    hdg_lat, hdg_lon = position_table.interpolate(['lat', 'lon'], hdg_timepoints)
    
    wt_timepoints = wattemp_table.ind()
    wt_times = time_table.interpolate(['ref'], wt_timepoints)[0]
    wt_lat, wt_lon = position_table.interpolate(['lat', 'lon'], wt_timepoints)
    
    wind_timepoints = wind_table.ind()
    wind_times = time_table.interpolate(['ref'], wind_timepoints)[0]
    wind_lat, wind_lon  = position_table.interpolate(['lat', 'lon'], wind_timepoints)

    source_data = {
        'loggername': logger_name,
        'platform': platform_name,
        'loggerversion': logger_version,
        'metadata': metadata,
        'algorithms': algorithms,
        'depth' : {
            't': z_times,
            'lat': z_lat,
            'lon': z_lon,
            'z': depth_table.var('z')
        },
        'heading' : {
            't': hdg_times,
            'lat': hdg_lat,
            'lon': hdg_lon,
            'heading': hdg_table.var('h')
        },
        'watertemp' : {
            't': wt_times,
            'lat': wt_lat,
            'lon': wt_lon,
            'temperature': wattemp_table.var('temp')
        },
        'wind' : {
            't': wind_times,
            'lat': wind_lat,
            'lon': wind_lon,
            'direction': wind_table.var('dir'),
            'speed': wind_table.var('spd')
        }
    }

    if process_algorithms:
        source_data = run_algorithms(source_data,
                                     source_data['algorithms'],
                                     AlgorithmPhase.AFTER_TIME_INTERP,
                                     filename,
                                     lineage,
                                     verbose)

    return source_data
