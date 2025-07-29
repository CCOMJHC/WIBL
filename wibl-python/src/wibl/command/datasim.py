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

import logging
import sys

import click

from wibl.command.support import PROBABILITY
from wibl.simulator.data import DataGenerator, Engine, CLOCKS_PER_SEC
from wibl.simulator.data.writer import Writer, FileWriter

logger = logging.getLogger(__name__)

@click.command()
@click.argument('-f',  '--filename',
              help='Simulated data output filename', required=True)
@click.option('-d', '--duration',
              help='Duration (seconds) of the simulated data', type=int, required=True)
@click.option('-s', '--emit-serial',
              help='Write NMEA0183 simulated strings', is_flag=True, default=True)
@click.option('-b', '--emit-binary',
              help='Write NMEA2000 simulated data packets', is_flag=True, default=False)
@click.option('--use-buffer-constructor',
              is_flag=True, default=False,
              help='Use buffer constructor, rather than data constructor, for data packets. If not specified, data constructor will be used.')
@click.option('--duplicate-depth-prob',
              type=PROBABILITY, default=0.0,
              help='Probability of generating duplicate depth values. Default: 0.0')
@click.option('--no-data-prob',
              type=PROBABILITY, default=0.0,
              help='Probability of generating no-data values for system time, position, and depth packets. Default: 0.0',)
@click.option('-v', '--verbose',
              help='Produce verbose output.', is_flag=True, default=False)
def datasim(filename:str , duration: int, emit_serial: bool, emit_binary: bool, use_buffer_constructor: bool,
            duplicate_depth_prob: float, no_data_prob: float, verbose: bool):
    """
    Write simulated WIBL data to FILENAME. Provides a very simple interface to the simulator for NMEA data so that
    files of a given size can be readily generated for testing data loggers and transfer software.
    """
    if not

    if verbose:
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    else:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    duration_ticks: int = duration * CLOCKS_PER_SEC
    use_data_constructor = not use_buffer_constructor

    gen: DataGenerator = DataGenerator(emit_nmea0183=emit_serial,
                                       emit_nmea2000=emit_binary,
                                       use_data_constructor=use_data_constructor,
                                       duplicate_depth_prob=duplicate_depth_prob,
                                       no_data_prob=no_data_prob)
    writer: Writer = FileWriter(filename, 'Gulf Surveyor', 'WIBL-Simulator')
    engine: Engine = Engine(gen)

    first_time: int
    current_time: int

    current_time = first_time = engine.step_engine(writer)
    num_itr: int = 0
    while current_time - first_time < duration_ticks:
        current_time = engine.step_engine(writer)
        logger.info(f"Step to time: {current_time}")
        num_itr += 1

    logger.info(f"Total iterations: {num_itr}")
