##\file countGeojsons.py
# \brief Count GeoJSON files in a specified directory
#
# This file was contributed to the WIBL project by Haley Davis of the International Seakeepers Society.
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

import pathlib
import argparse

def main():
    # 1. Set up the argument parser
    parser = argparse.ArgumentParser(description="Count GeoJSON files in a directory recursively.")
    
    # 2. Define the -path argument
    parser.add_argument("-path", type=str, required=True, help="The directory path to search.")
    
    # 3. Parse the arguments from the command line
    args = parser.parse_args()
    
    # 4. Perform the search
    folder_to_search = args.path
    path_obj = pathlib.Path(folder_to_search)
    
    # Check if path exists to avoid errors
    if not path_obj.exists():
        print(f"Error: The path '{folder_to_search}' does not exist.")
        return

    # Count the files (case-insensitive for reliability)
    total = sum(1 for f in path_obj.rglob('*') if f.suffix.lower() == '.geojson')
    
    # 5. Print the output in your requested format
    print(f"Found {total} files ending in 'GeoJSON' in {folder_to_search}")

if __name__ == "__main__":
    main()