##\file __init__.py
# \brief WIBL command line tools.
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

import click

from wibl import __version__ as version
from wibl.command.datasim import datasim
from wibl.command.dcdb_upload import dcdb_upload
from wibl.command.edit_wibl_file import editwibl
from wibl.command.parse_wibl_file import parsewibl
from wibl.command.validate import geojson_validate
from wibl.command.upload_wibl_file import uploadwibl
from wibl.command.wibl_proc import wibl_proc


@click.version_option(version=version)
@click.group()
def cli():
    """Python tools for WIBL low-cost data logger system."""
    pass

cli.add_command(datasim)
cli.add_command(dcdb_upload)
cli.add_command(editwibl)
cli.add_command(parsewibl)
cli.add_command(geojson_validate)
cli.add_command(uploadwibl)
cli.add_command(wibl_proc)

# To Run a command in a debugger in your IDE, invoke as follows:
# if __name__ == '__main__':
#     from click.testing import CliRunner
#     runner = CliRunner(catch_exceptions=False)
#     result = runner.invoke(cli,
#                            ['editwibl',
#                                  '-m', 'examples/ship-metadata-simple.json',
#                                  'path/to/wibl/file/foo.wibl',
#                                  'path/to/wibl/file/foo-edited.wibl'])
#     print(result.output)