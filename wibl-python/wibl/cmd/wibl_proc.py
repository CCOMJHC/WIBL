##\file wibl_proc.py
# \brief Process a WIBL file locally
#
# This is a simple command-line utility to take a WIBL file through the standard
# processing chain (by invoking the processing lambda locally), without having to
# send it out through the cloud-based chain.  This is primarily for testing, but
# could be used as an alternate scheme for processing if required.
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

import argparse as arg
import sys
import os

from wibl.cmd import get_subcommand_prog
import wibl.core.config as conf
from wibl.core import getenv
from wibl.processing.cloud.aws import get_config_file
from wibl.processing.cloud.aws.lambda_function import process_item
from wibl.core.datasource import LocalSource, LocalController

def wibl_proc():
    parser = arg.ArgumentParser(description="Process WIBL files into GeoJSON locally.",
                prog=get_subcommand_prog())
    parser.add_argument('-c', '--config', type=str, help='Specify configuration file for installation')
    parser.add_argument('input', help='WIBL format file to convert to GeoJSON.')
    parser.add_argument('output', help='Specify output GeoJSON file location')

    optargs = parser.parse_args(sys.argv[2:])

    infilename = optargs.input
    outfilename = optargs.output

    try:
        if hasattr(optargs, 'config'):
            config_filename = optargs.config
        else:
            config_filename = get_config_file()
        config = conf.read_config(config_filename)
    except conf.BadConfiguration:
        sys.exit('Error: bad configuration file.')
    
    # The cloud-based code uses environment variables to provide some of the configuration,
    # so we need to add this to the local environment to compensate.
    os.environ['PROVIDER_ID'] = config['provider_id']

    source = LocalSource(infilename, outfilename, config)
    data_item = source.nextSource()
    controller = LocalController(config)

    if not process_item(data_item, controller, config):
        sys.exit('Error: failed to process data (try with verbose option for more information).')