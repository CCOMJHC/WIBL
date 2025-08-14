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

import json
from pathlib import Path

import click

from wibl.core import logger_file as lf
from wibl.core.logger_file import PacketTranscriptionError


@click.command()
@click.argument('input', type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
@click.argument('output', type=click.Path())
@click.option('-u', '--uniqueid', type=str,
              help='Set the logger name, which should be a unique identifier')
@click.option('-s', '--shipname', type=str,
              help ='Set the ship name for the logger')
@click.option('-m', '--meta', type=click.Path(exists=True),
              help='Specify a JSON file for additional metadata elements')
@click.option('-a', '--algo', type=str, multiple=True,
              help='Add a processing algorithm request (name;params, e.g. -a uncertainty;0.25,IHO_S44_6_Order1)')
@click.option('-v', '--version', type=str,
              help='Specify the serialiser version for the output file (major: int, minor: int)')
@click.option('-f', '--filter', type=str, multiple=True,
              help='Specify a NMEA0183 sentence filter name')
@click.option('--strict-mode', is_flag=True, default=False,
              help='Strict mode: fail if any packet is not successfully translated')
def editwibl(input: Path, output: Path, uniqueid: str, shipname: str,
             meta: Path, algo: tuple[str], version: str, filter: tuple[str], strict_mode: bool):
    """Edit INPUT WIBL logger file, writing edited WIBL file to OUTPUT."""

    if uniqueid:
        logger_name = uniqueid
    else:
        logger_name = None
    if shipname:
        shipname = shipname
    else:
        shipname = None
    if meta:
        with open(meta) as f:
            json_meta = json.load(f)
        metadata = json.dumps(json_meta)
    else:
        metadata = None

    algorithms = []
    if algo:
        for alg in algo:
            name, params = alg.split(';')
            algorithms.append({ 'name': name, 'params': params})
    
    filters = []
    if filter:
        filters = filter

    if version:
        file_major, file_minor = version.split(',')
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
    op = open(output, 'wb')
    metadata_out = False
    json_metadata_out = False
    packet_count: int = 0
    with open(input, 'rb') as ip:
        source = lf.PacketFactory(ip, strict_mode=strict_mode)
        while source.has_more():
            packet_count += 1
            try:
                packet = source.next_packet()
            except PacketTranscriptionError as e:
                raise PacketTranscriptionError(f'Error reading packet {packet_count}: {str(e)}') from e
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
