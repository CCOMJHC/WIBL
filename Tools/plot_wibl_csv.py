# \file plot_wibl_csv.py
# \brief Make some basic plots from WIBL converted CSV files
#
# This code attempts to make a few quick plots of the data that is generated by
# a WIBL logger, giving a rough guide to the contents of the file and what we
# might expect from the data.
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
import matplotlib.pyplot as plt
import pandas
import argparse as arg

def plot_timestrip(data, file_prefix):
    basetime = data['Epoch'][0]
    endtime = data['Epoch'][len(data)-1]
    duration = endtime - basetime
    if duration > 24*60*60:
        # Plot in days
        divisor = 24*60*60
        time_label = 'Days'
    elif duration > 60*60:
        # Plot in hours
        divisor = 60*60
        time_label = 'Hours'
    else:
        # Plot in seconds
        divisor = 1
        time_label = 'Seconds'
        
    timebase = (data['Epoch'] - basetime)/divisor
    
    plt.figure(figsize=(14,9))
    plt.subplot(3,1,1)
    plt.plot(timebase, data['Longitude'])
    plt.grid()
    plt.ylabel('Longitude (deg)')
    plt.subplot(3,1,2)
    plt.plot(timebase, data['Latitude'])
    plt.grid()
    plt.ylabel('Latitude (deg)')
    plt.subplot(3,1,3)
    plt.plot(timebase, data['Depth'], '.')
    plt.grid()
    plt.ylabel('Depth (m)')
    plt.xlabel('Elapsed Time (' + time_label + ')')
    
    if file_prefix is not None:
        plt.savefig(file_prefix + '-Timestrip.png', format='png')

def plot_geographic(data, file_prefix):
    plt.figure(figsize=(14,9))
    plt.plot(data['Longitude'], data['Latitude'])
    plt.xlabel('Longitude (deg)')
    plt.ylabel('Latitude (deg)')
    plt.grid()
    
    if file_prefix is not None:
        plt.savefig(file_prefix + '-Geographic.png', format = 'png')
    
def main():
    parser = arg.ArgumentParser(description = 'Plot WIBL logger data in CSV format')
    parser.add_argument('-s', '--save', help = 'Prefix for output of PNG version of plots')
    parser.add_argument('input', help = 'CSV format input file')
    
    optargs = parser.parse_args()
    
    if optargs.input:
        data = pandas.read_csv(optargs.input)
    else:
        print('Error: must have at least an input file.');
        sys.exit(1)
        
    if optargs.save:
        fig_file_prefix = optargs.save
    else:
        fig_file_prefix = None
    
    plot_timestrip(data, fig_file_prefix)
    plot_geographic(data, fig_file_prefix)
    plt.show()
    
if __name__ == "__main__":
    main()
