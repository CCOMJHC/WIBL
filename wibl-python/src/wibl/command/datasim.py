##\file datasim.py
# \brief WIBL data simulator.
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

import sys
import argparse
import logging

from wibl.command import get_subcommand_prog, type_probability_float
from wibl.simulator.data import DataGenerator, Engine, CLOCKS_PER_SEC
from wibl.simulator.data.writer import Writer, FileWriter


logger = logging.getLogger(__name__)


def datasim():
    """
    Provides a very simple interface to the simulator for NMEA data so that files of a given
    size can be readily generated for testing data loggers and transfer software.
    :return:
    """
    parser = argparse.ArgumentParser(
        description='Command line user interface for the NMEA data simulator.',
        prog=get_subcommand_prog()
    )
    parser.add_argument('-f', '--filename', help='Simulated data output filename')
    parser.add_argument('-d', '--duration', help='Duration (seconds) of the simulated data',
                        type=int)
    parser.add_argument('-s', '--emit_serial', help='Write NMEA0183 simulated strings',
                        action='store_true', default=True)
    parser.add_argument('-b', '--emit_binary', help='Write NMEA2000 simulated data packets',
                        action='store_true', default=False)
    parser.add_argument('--use_buffer_constructor',
                        help=('Use buffer constructor, rather than data constructor, for data packets. '
                              'If not specified, data constructor will be used.'),
                        action='store_true', default=False)
    parser.add_argument('--duplicate_depth_prob',
                        help='Probability of generating duplicate depth values. Default: 0.0',
                        type=type_probability_float, default=0.0)
    parser.add_argument('--no_data_prob',
                        help=('Probability of generating no-data values for system time, position, and depth packets. '
                              'Default: 0.0'),
                        type=type_probability_float, default=0.0)
    parser.add_argument('-v', '--verbose', help='Produce verbose output.',
                        action='store_true', default=False)
    args = parser.parse_args(sys.argv[2:])

    if args.verbose:
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    else:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    duration: int = args.duration * CLOCKS_PER_SEC
    use_data_constructor = not args.use_buffer_constructor

    gen: DataGenerator = DataGenerator(emit_nmea0183=args.emit_serial,
                                       emit_nmea2000=args.emit_binary,
                                       use_data_constructor=use_data_constructor,
                                       duplicate_depth_prob=args.duplicate_depth_prob,
                                       no_data_prob=args.no_data_prob)
    writer: Writer = FileWriter(args.filename, 'Gulf Surveyor', 'WIBL-Simulator')
    engine: Engine = Engine(gen)

    first_time: int
    current_time: int

    current_time = first_time = engine.step_engine(writer)
    num_itr: int = 0
    while current_time - first_time < duration:
        current_time = engine.step_engine(writer)
        logger.info(f"Step to time: {current_time}")
        num_itr += 1

    logger.info(f"Total iterations: {num_itr}")
