# validate.py
#
# Sub-command to validate the metadata of a GeoJSON object.
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

from wibl.command import get_subcommand_prog
from wibl.validation.cloud.aws import get_config_file
import wibl.core.config as conf
from wibl.validation.cloud.aws.lambda_function import validate_metadata


def geojson_validate():
    parser = arg.ArgumentParser(description="Validate GeoJSON file metadata.",
                prog=get_subcommand_prog())
    parser.add_argument('-c', '--config', type=str, help='Specify configuration file for installation')
    parser.add_argument('input', help='GeoJSON format file to validate.')
    
    optargs = parser.parse_args(sys.argv[2:])

    infilename = optargs.input

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
    if config['management_url']:
        os.environ['MANAGEMENT_URL'] = config['management_url']

    if not validate_metadata(infilename, config):
        print(f'error: failed to validate {infilename} metadata.')
    else:
        print(f'info: completed successful validate of {infilename} metadata.')
