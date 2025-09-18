## \file interpolation.py
# \brief Simple (linear) interpolation structure for arbitrary numbers of dependent variables
#
# WIBL files have asynchronous data packets for depths, positions, and other variables, but we need
# to be able to match up positions and real-world times with the observations in order to make
# them into something useful.  Since each data packet also only has a timestamp for when it was
# received (according to the millisecond elapsed-time counter on the logger, or an equivalent),
# we need to be able to interpolate between elapsed times and real-world times available in
# certain packets.  This file provides a simple linear interpolation class that can be used to
# establish a relationship between a single independent variable, and one or more dependent
# variables, and then interpolate to points in a NumPy vector for the independent variable.
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

from typing import List

import numpy as np

## Exception to indicate that the variable requested in the InterpTable does not exist
class NoSuchVariable(Exception):
    pass

## Exception to indicate that there are insufficient number of values in an add_points() call
class NotEnoughValues(Exception):
    pass

## Simple linear interpolation table for one or more dependent variables
#
# In order to establish real-world times for the packets, and their positions, we need to
# interpolate the asynchronous packets for this information against the elapsed times for
# the variables on interest.  This class provides facilities to register one or more named
# dependent variables (and automatically adds an independent variable), which can be added
# to as data becomes available.  Interpolation can then be done at given time points against
# one or more of the dependent variables, returned as a list of NumPy arrays.

class InterpTable:
    ## Constructor, specifying the names of the dependent variables to be interpolated
    #
    # This sets up for interpolation of an independent variable (added automatically) against
    # the named dependent variables.
    #
    # \param vars   (List[str]) List of the names of the dependent variables to manage
    def __init__(self, vars: List[str]) -> None:
        # Add an independent variable tag implicitly to the lookup table
        self.vars = {}
        self.vars['ind'] = []
        for v in vars:
            self.vars[v] = []
    
    ## Add a data point to a single dependent variable
    #
    # Add a single data point to a single dependent variable.  Note that if the object is
    # tracking more than one dependent variable, this is likely to cause a problem, since
    # you'll have one more point in the independent variable array than in the dependent
    # variables that aren't updated by this call, which will fail interpolation.  This is
    # therefore only really useful for the special case where there is only a single
    # dependent variable being tracked.
    #
    # \param ind    Independent variable value to add to the array
    # \param var    Name of the dependent variable to update
    # \param value  Value to add to the dependent variable array
    def add_point(self, ind: float, var: str, value: float) -> None:
        if var not in self.vars:
            raise NoSuchVariable()
        self.vars['ind'].append(ind)
        self.vars[var].append(value)
    
    ## Add a data point to multiple dependent variables simultaneously
    #
    # Add a data point for one or more dependent variables at a common independent variable
    # point.  Since adding a data point for a common independent variable value to some, but
    # not all of the dependent variables would result in some dependent variables having arrays
    # of different lengths, it would cause problems when interpolating.  This is therefore only
    # really useful if you're updating all of the variables.
    #
    # \param ind    Independent variable value to add to the array
    # \param vars   List of names of the dependent variables to update
    # \param values List of values to update for the named dependent variables, in the same order
    def add_points(self, ind: float, vars: List[str], values: List[float]) -> None:
        for var in vars:
            if var not in self.vars:
                raise NoSuchVariable()
        if len(vars) != len(values):
            raise NotEnoughValues()
        self.vars['ind'].append(ind)
        for n in range(len(vars)):
            self.vars[vars[n]].append(values[n])

    ## Interpolate one or more dependent variables at an array of independent variable values
    #
    # Construct a linear interpolation of the named dependent variables at the given array
    # of independent variable values.
    #
    # \param yvars  List of names of the dependent variables to interpolate
    # \param x      NumPy array of the independent variable points at which to interpolate
    # \return List of NumPy arrays for the named dependent variables, in the same order
    def interpolate(self, yvars: List[str], x: np.ndarray) -> List[np.ndarray]:
        for yvar in yvars:
            if yvar not in self.vars:
                raise NoSuchVariable()
        rtn = []
        for yvar in yvars:
            rtn.append(np.interp(x, self.vars['ind'], self.vars[yvar]))
        return rtn
    
    ## Determine the number of points in the independent variable array
    #
    # This provides the count of points that have been added to the table for interpolation.  Since
    # you have to add an independent variable point for each dependent variable point(s) added, this
    # should be the total number of points in the table.
    #
    # \return Number of points in the interpolation table
    def n_points(self) -> int:
        return len(self.vars['ind'])
    
    ## Accessor for the array of points for a named variable
    #
    # This provides checked access to one of the dependent variables stored in the array.  This returns
    # all of the points stored for that variable as a NumPy array.
    #
    # \param name   Name of the dependent variable to extract
    # \return NumPy array for the dependent variable named
    def var(self, name: str) -> np.ndarray:
        if name not in self.vars:
            raise NoSuchVariable()
        return np.array(self.vars[name])
    
    ## Accessor for the array of points for the independent variable
    #
    # This provides access to the independent variable array, without exposing the specifics
    # of how this is stored.
    #
    # \return NumPy array for the independent variable
    def ind(self) -> np.ndarray:
        return np.array(self.vars['ind'])
