# \file wibl_to_ascii.py
# \brief Read a binary data file from the WIBL data logger, and generate ASCII data
#
# The WIBL data logger, and any loggers for which converters exist in the LogConvert sub-project,
# generate binary data for compactness on the logger's SD card.  Although the wibl python tool can
# be used to convert this data into GeoJSON for output into the DCDB database, this isn't always
# the simplest format to work with.  The code here reads the WIBL file using the standard file parser
# and timestamps the data using the standard algorithm used for the conventional processing, but then
# converts to ASCII.  For files that have heading, temperature, or wind speed/direction information,
# the code can also generate separate output files with timestamped renderings of the data sources.
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
import argparse as arg
from datetime import datetime

import wibl.core.timestamping as ts
from wibl.core import Lineage

def main():
    parser = arg.ArgumentParser(description = 'Convert WIBL logger data to timestamped ASCII')
    parser.add_argument('-b', '--bitsize', help = 'Set bit-length of elapsed times')
    parser.add_argument('-i', '--input', help = 'WIBL format input file')
    parser.add_argument('-o', '--output', help = 'ASCII format output file')
    parser.add_argument('-q', '--heading', help = 'ASCII format output for true heading')
    parser.add_argument('-t', '--temp', help = 'ASCII format output for water temperature')
    parser.add_argument('-w', '--wind', help = 'ASCII format output for wind speed/direction')
    parser.add_argument('input', help = 'WIBL format input file')
    parser.add_argument('output', help = 'ASCII format output file')

    optargs = parser.parse_args()
    
    if optargs.bitsize:
        elapsed_time_quantum = 1 << int(optargs.bitsize)
    else:
        elapsed_time_quantum = 1 << 32
        
    if optargs.input:
        in_filename = optargs.input
        
    if optargs.output:
        out_filename = optargs.output
    
    try:
        lineage = Lineage()
        tsdata = ts.time_interpolation(in_filename, lineage, elapsed_time_quantum)
        
    except ts.NoTimeSource:
        print('Error: failed to find a time source to timestamp file.')
        sys.exit(1)
        
    except ts.NoData:
        print('Warning: no data to interpolate.')
        sys.exit(1)
    
    print('Converting Data For:');
    print('Logger Name:\t', tsdata['loggername'])
    print('Platform Name:\t', tsdata['platform'])
    
    with open(out_filename, 'w') as f:
        f.write('Time,Epoch,Longitude,Latitude,Depth\n')
        for i in range(len(tsdata['depth']['t'])):
            dt = datetime.utcfromtimestamp(tsdata['depth']['t'][i])
            f.write('%sZ,%.3f,%.8f,%.8f,%.2f\n' % (dt.isoformat(), tsdata['depth']['t'][i], tsdata['depth']['lon'][i], tsdata['depth']['lat'][i], tsdata['depth']['z'][i]))
    
    if optargs.heading:
        with open(optargs.heading, 'w') as f:
            f.write('Time,Epoch,Longitude,Latitude,Heading\n')
            for i in range(len(tsdata['heading']['t'])):
                dt = datetime.utcfromtimestamp(tsdata['heading']['t'][i])
                f.write('%sZ,%.3f,%.8f,%.8f,%.1f\n' % (dt.isoformat(), tsdata['heading']['t'][i], tsdata['heading']['lon'][i], tsdata['heading']['lat'][i], tsdata['heading']['heading'][i]))
    
    if optargs.temp:
        with open(optargs.temp, 'w') as f:
            f.write('Time,Epoch,Longitude,Latitude,Temperature\n')
            for i in range(len(tsdata['watertemp']['t'])):
                dt = datetime.utcfromtimestamp(tsdata['watertemp']['t'][i])
                f.write('%sZ,%.3f,%.8f,%.8f,%.1f\n' % (dt.isoformat(), tsdata['watertemp']['t'][i], tsdata['watertemp']['lon'][i], tsdata['watertemp']['lat'][i], tsdata['watertemp']['temperature'][i]))
                
    if optargs.wind:
        with open(optargs.wind, 'w') as f:
            f.write('Time,Epoch,Longitude,Latitude,Direction,Speed\n')
            for i in range(len(tsdata['wind']['t'])):
                dt = datetime.utcfromtimestamp(tsdata['wind']['t'][i])
                f.write('%sZ,%.3f,%.8f,%.8f,%.2f,%.2f\n' % (dt.isoformat(), tsdata['wind']['t'][i], tsdata['wind']['lon'][i], tsdata['wind']['lat'][i], tsdata['wind']['direction'][i], tsdata['wind']['speed'][i]))

if __name__ == "__main__":
    main()
