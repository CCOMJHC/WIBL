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

import sys
import os
from pathlib import Path

import click

from wibl.validation.cloud.aws import get_config_file
import wibl.core.config as conf
from wibl.validation.cloud.aws.lambda_function import validate_metadata


@click.command(name='validate')
@click.argument('input')
@click.option('-c', '--config',
              type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True),
              help='Specify configuration file for installation')
def geojson_validate(input: str, config_path: Path=None):
    """Validate GeoJSON metadata stored in INPUT."""
    infilename = input

    try:
        if config_path:
            config_filename = config_path
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
        click.echo(f"error: failed to validate {infilename} metadata.")
    else:
        click.echo(f"info: completed successful validate of {infilename} metadata.")
