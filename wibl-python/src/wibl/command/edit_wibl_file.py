##\file edit_wibl_file.py
# \brief Limited editing/modification of WIBL raw binary files
#
# Although the goal is to have all of the data points required for the WIBL binary
# file embedded into the logger before data capture starts, it's occasionally
# necessary to edit one or more of the metadata elements of the files to correct issues
# that might not have been obvious at startup.  This code allows for some editing
# in batch (i.e., non-interactive) mode.
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

import argparse as arg
import sys
import json

from wibl.command import get_subcommand_prog
from wibl.core import logger_file as lf


def editwibl():
    parser = arg.ArgumentParser(description = 'Edit WIBL logger files (in a limited capacity)',
                                prog=get_subcommand_prog())
    parser.add_argument('-u', '--uniqueid', type=str, help = 'Set the logger name (string), which should be a unique identifier')
    parser.add_argument('-s', '--shipname', type=str, help = 'Set the ship name for the logger (string)')
    parser.add_argument('-m', '--meta', type=str, help = 'Specify a JSON file for additional metadata elements (filename)')
    parser.add_argument('-a', '--algo', type=str, action='append', help = 'Add a processing algorithm request (name: str,params: str)')
    parser.add_argument('-v', '--version', type=str, help = 'Specify the serialiser version for the output file (major: int, minor: int)')
    parser.add_argument('-f', '--filter', type=str, action='append', help='Specify a NMEA0183 sentence filter name')
    parser.add_argument('input', type=str, help = 'WIBL format input file')
    parser.add_argument('output', type=str, help = 'WIBL format output file')

    optargs = parser.parse_args(sys.argv[2:])

    if not optargs.input:
        sys.exit('Error: must have an input file!')
    
    if not optargs.output:
        sys.exit('Error: must have an output file!')

    if optargs.uniqueid:
        logger_name = optargs.uniqueid
    else:
        logger_name = None
    if optargs.shipname:
        shipname = optargs.shipname
    else:
        shipname = None
    if optargs.meta:
        with open(optargs.meta) as f:
            json_meta = json.load(f)
        metadata = json.dumps(json_meta)
    else:
        metadata = None

    algorithms = []
    if optargs.algo:
        for alg in optargs.algo:
            name,params = alg.split(',')
            algorithms.append({ 'name': name, 'params': params})
    
    filters = []
    if optargs.filter:
        filters = optargs.filter

    if optargs.version:
        file_major, file_minor = optargs.version.split(',')
        file_major = int(file_major)
        file_minor = int(file_minor)
    else:
        file_major = None
        file_minor = None

    # Next step is to loop through the data file, copying packets by default
    # unless there's something that we have to add.  Note that we edit the
    # Metadata packet to change the logger name and/or unique ID, if it exists
    # (it should on most systems), but add it later if there isn't one; with the
    # JSON metadata, the same thing is true: if the packet exists, we replace it
    # at the same location in the file, but otherwise append it at the end.
    op = open(optargs.output, 'wb')
    metadata_out = False
    json_metadata_out = False
    with open(optargs.input, 'rb') as ip:
        source = lf.PacketFactory(ip)
        while source.has_more():
            packet = source.next_packet()
            if packet:
                if isinstance(packet, lf.Metadata):
                    if logger_name or shipname:
                        out_name = packet.logger_name
                        out_id = packet.ship_name
                        if logger_name:
                            out_name = logger_name
                        if shipname:
                            out_id = shipname
                        packet = lf.Metadata(logger = out_name, shipname = out_id)
                        metadata_out = True
                elif isinstance(packet, lf.JSONMetadata):
                    if metadata:
                        packet = lf.JSONMetadata(meta = metadata)
                        json_metadata_out = True
                elif isinstance(packet, lf.SerialiserVersion):
                    if file_major:
                        packet = lf.SerialiserVersion(major=file_major, minor=file_minor,
                                                      n2000=packet.nmea2000, n0183=packet.nmea0183, imu=packet.imu)
                packet.serialise(op)
        # At the end of the file, if we haven't yet sent out any of the edited packets,
        # we just append.  Note that we don't do this for the SerialiserVersion packet,
        # since all versions of the file format have this, so we are certain that it
        # must have occurred during the read-through.
        if not metadata_out:
            if logger_name or shipname:
                out_name = 'Unknown'
                if logger_name:
                    out_name = logger_name
                out_id = 'Unknown'
                if shipname:
                    out_id = shipname
                packet = lf.Metadata(logger = out_name, shipname = out_id)
                packet.serialise(op)
        if not json_metadata_out and metadata:
            packet = lf.JSONMetadata(meta = metadata)
            packet.serialise(op)
        if algorithms:
            for alg in algorithms:
                packet = lf.AlgorithmRequest(name = alg['name'], params = alg['params'])
                packet.serialise(op)
        if filters:
            for filt in filters:
                packet = lf.NMEA0183Filter(sentence = filt)
                packet.serialise(op)
    
    op.flush()
    op.close()
