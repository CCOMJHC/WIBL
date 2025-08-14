##\file prase_wibl_file.py
# \brief Parse a WIBL file and report the contents (for debugging, mainly)
#
# This is a simple command-line utility that will read the contents of a WIBL binary
# file using the same code that the cloud-based processing uses, thereby confirming that
# the file will be parseable in the cloud.  This also allows for various debugging and
# investigation actions.
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

import sys

import click

import wibl.core.logger_file as LoggerFile


@click.command()
@click.argument('input', type=str)
@click.option('-s', '--stats', is_flag=True, default=False,
              help='Provide summary statistics on packets seen')
@click.option('-d', '--dump', type=click.Path(exists=True),
              help='Dump ASCII representation of NMEA0183 data to file')
@click.option('--strict-mode', is_flag=True, default=False,
              help='Strict mode: fail if any packet is not successfully translated')
def parsewibl(input: str, stats: bool, dump: str, strict_mode: bool):
    """Parse binary WIBL logger file INPUT and report contents in human-readable format to the console."""
    filename = str(input)
    
    if dump:
        dump_file = open(dump, 'w')
    else:
        dump_file = None

    file = open(filename, 'rb')

    packet_count: int = 0
    packet_stats: dict = {}
    source = LoggerFile.PacketFactory(file, strict_mode=strict_mode)
    while source.has_more():
        try:
            pkt = source.next_packet()
            if pkt:
                packet_count += 1
                click.echo(pkt)
                if dump_file:
                    if pkt.name() == 'SerialString':
                        dump_file.write(f'{pkt.elapsed} {pkt.data.decode("utf-8").strip()}\n')
                if stats:
                    if pkt.name() not in packet_stats:
                        packet_stats[pkt.name()] = 0
                    packet_stats[pkt.name()] += 1
        except LoggerFile.PacketTranscriptionError as e:
            sys.exit(f"Failed to translate packet {packet_count}: {str(e)}.")

    click.echo(f"Found {packet_count} packets total")
    if stats:
        click.echo("Packet statistics:")
        for name in packet_stats:
            click.echo(f"\t{packet_stats[name]:8d} {name}")
