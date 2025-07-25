##\file __main__.py
# \brief WIBL main command line tool.
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

from wibl import __version__ as version
from wibl.command.edit_wibl_file import editwibl
from wibl.command.datasim import datasim
from wibl.command.upload_wibl_file import uploadwibl
from wibl.command.parse_wibl_file import parsewibl
from wibl.command.dcdb_upload import dcdb_upload
from wibl.command.wibl_proc import wibl_proc
from wibl.command.validate import geojson_validate

class WIBL:
    def __init__(self):
        parser = argparse.ArgumentParser(
            description='Python tools for WIBL low-cost data logger system',
            usage='''wibl <command> [<arguments>]

    Commands include:
        datasim     Generate test data using Python-native data simulator.
        editwibl    Edit WIBL logger files, e.g., add platform metadata.
        uploadwibl  Upload WIBL logger files to an S3 bucket.
        parsewibl   Read and report contents of a WIBL file.
        dcdbupload  Upload a GeoJSON file to DCDB direct.
        procwibl    Local processing from WIBL file to GeoJSON.
        validate    Validate the metadata in a GeoJSON file.
        '''
        )
        parser.add_argument('--version', help='print version and exit',
                            action='version', version=f"%(prog)s {version}")
        parser.add_argument('command', help='Subcommand to run')

        # Only consume the command argument here, let sub-commands consume the rest
        args = parser.parse_args(sys.argv[1:2])

        if not hasattr(self, args.command):
            print(f"Unrecognized command: {args.command}")
            parser.print_help()
            sys.exit(1)
        # Call the subcommand
        getattr(self, args.command)()

    def datasim(self):
        datasim()

    def editwibl(self):
        editwibl()

    def uploadwibl(self):
        uploadwibl()

    def parsewibl(self):
        parsewibl()

    def dcdbupload(self):
        dcdb_upload()

    def procwibl(self):
        wibl_proc()

    def validate(self):
        geojson_validate()


def main():
    WIBL()


if __name__ == '__main__':
    main()
