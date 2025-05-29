##\file statistics.py
# \brief Track packet statistics for the loader/processor
#
# As packets are loaded from the WIBL file, it is often important to keep track of which
# packets have been seen, how often, and how many times each type of packet causes a range
# of potential faults when being processed.  This file provides a couple of classes that
# can be used to track arbitrarily named packets, and provide composite statistics on demand.
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

from dataclasses import dataclass
from enum import Enum


## Exception indicating that the caller asked for a packet type that is not being tracked
class NoSuchPacket(Exception):
    pass

## Encapsulate the different types of faults that can be reported
#
# Enumeration for the different types of faults that can be tracked by the PktStats class
class PktFaults(Enum):
    ## A fault in parsing the packet for its individual components
    ParseFault = 0
    ## A packet that does not have enough data to adequately interpret
    ShortMessage = 1
    ## A fault when attempting to decode a packet (typically from bytes to str)
    DecodeFault = 2
    ## A fault in attributes when attempting to use a packet (usually a coding problem)
    AttributeFault = 3
    ## A fault in data types when attempting to use a packet (usually a coding problem)
    TypeFault = 4
    ## A fault in checksum verification for a packet
    ChecksumFault = 5

## Exception indicating that the code attempted to register an unknown fault type
class NoSuchFault(Exception):
    pass

## \class StatCounters
#
# Provide a data object to count the number of times that a packet is observed in the data stream, and
# the count of faults observed when manipulating the packet (broken into a number of categories).  The
# object provides methods to count the total number of faults, and to serialise the contents for reporting.

@dataclass
class StatCounters:
    observed:       int = 0
    parse_fault:    int = 0
    short_msg:      int = 0
    decode_fault:   int = 0
    attrib_fault:   int = 0
    type_fault:     int = 0
    chksum_fault:   int = 0

    ## Count the number of times that the object has been observed in the datastream
    def Observed(self) -> None:
        self.observed += 1
    
    ## Count the number of times an object has failed to parse correctly
    def ParseFault(self) -> None:
        self.parse_fault += 1
    
    ## Count the number of times an object has come up short on the data expected
    def ShortMessage(self) -> None:
        self.short_msg += 1

    ## Count the number of times an object has failed to decode a bytes object into a string
    def DecodeFault(self) -> None:
        self.decode_fault += 1
    
    ## Count the number of times an object has thrown attribute errors during manipulation (usually a coding error)
    def AttributeFault(self) -> None:
        self.attrib_fault += 1
    
    ## Count the number of times an object has thrown type errors during manipulation (usually a coding error)
    def TypeFault(self) -> None:
        self.type_fault += 1
    
    ## Count the number of times an object has failed a checksum verification
    def ChecksumFault(self) -> None:
        self.chksum_fault += 1

    ## Count the total number of faults that have been seen on the object
    #
    # For reporting purposes, it's often a requirement to know how many faults have been
    # seen on the object (e.g., to determine whether to keep reporting errors).  This provides
    # the total number of faults recorded so far.
    #
    # \return Total number of faults recorded for this object
    def FaultCount(self) -> int:
        return self.parse_fault + self.short_msg + self.decode_fault + self.attrib_fault + self.type_fault + self.chksum_fault

    ## Generate a printable representation of the current object's information
    def __str__(self) -> str:
        total_fault = self.FaultCount()
        rtn = f'{self.observed:6} Obs.; Errors ({total_fault:6} total): {self.parse_fault:6} Parse / {self.short_msg:6} Short / {self.decode_fault:6} Decode / {self.attrib_fault:6} Attrib / {self.type_fault:6} Type / {self.chksum_fault:6} Checksum'
        return rtn

## \class PktStats
#
# Provide a dictionary for statistics for an arbitrary set of packets to be tracked.  The object
# automatically adds new entries to the dictionary as any of the counting methods are called,
# although EnsureName() can be called to explicitly add the entry if required.  The Seen()
# method can be used to determine whether a particular packet has been observed in the data
# stream.  A constant can be specified at instantiation to provide a limit to the number of faults
# that can be seen and still report them (i.e., to avoid too many error messages from being
# issued on the output in verbose mode).  The object here does not mandate this: it just stores
# the constant on behalf of the user so that it doesn't need to get passed around the code.

class PktStats:
    ## Constructor for an empty dictionary
    #
    # This sets up the statistics tracker with a blank dictionary, and stores the reporting limit
    # on faults for later.
    #
    # \param fault_limit    Number of faults to report before suppressing output
    def __init__(self, fault_limit: int) -> None:
        self.fault_limit = fault_limit
        self.packets = {}
    
    ## Ensure that the packet specified is in the dictionary of objects being tracked
    #
    # Add the name object to the tracking list, with zeroed counters.  This is typically
    # not something that user-level code should call; rely on the code automatically adding
    # the packet name to the dictionary when you tell it either that you've seen it, or that
    # it caused a fault (Observed() or Fault() respectively).
    #
    # \param name   Name of the object to track
    def EnsureName(self, name: str) -> None:
        if name not in self.packets:
            self.packets[name] = StatCounters()

    ## Increment the count for how many times the named packet has been seen
    #
    # As a basic statistic, we count the number of times that each packet has been seen
    # in the data stream.  By default, this adds the packet name to the dictionary if
    # if has not been done before.
    #
    # \param name   Name of the object to track
    def Observed(self, name: str) -> None:
        self.EnsureName(name)
        self.packets[name].Observed()

    ## Increment the count for how many times a particular fault has been seen on the packet
    #
    # This allows the user to indicate that a fault has occurred in using the packet, and the
    # type of fault.  The statistics object tracks the count of each fault type separately.
    #
    # \param name   Name of the object that caused the fault
    # \param fault  (PktFaults) Fault that the packet caused
    def Fault(self, name: str, fault: PktFaults) -> None:
        self.EnsureName(name)
        if fault == PktFaults.ParseFault:
            self.packets[name].ParseFault()
        elif fault == PktFaults.ShortMessage:
            self.packets[name].ShortMessage()
        elif fault == PktFaults.DecodeFault:
            self.packets[name].DecodeFault()
        elif fault == PktFaults.AttributeFault:
            self.packets[name].AttributeFault()
        elif fault == PktFaults.TypeFault:
            self.packets[name].TypeFault()
        elif fault == PktFaults.ChecksumFault:
            self.packets[name].ChecksumFault()
        else:
            raise NoSuchFault()

    ## Determine whether the named packet has been seen in the data stream
    #
    # This checks whether the give name appears in the dictionary or not.  By proxy, this means
    # that the packet either was Observed(), or caused a Fault(), and therefore must have existed
    # in the data stream.
    #
    # \param name   Name of the object to check for
    # \return True if the name appears in the dictionary, otherwise False
    def Seen(self, name: str) -> bool:
        return name in self.packets

    ## Determine the total count of all packets that have been observed
    #
    # This computes the sum of all packets that have been Observed() in the dictionary.
    #
    # \return Count of all packets registered as seen in the data stream
    def TotalCount(self) -> int:
        rtn = 0
        for p in self.packets:
            rtn += self.packets[p].observed
        return rtn
    
    ## Determine the total count of faults registered for a given packet
    #
    # This computes the total number of faults of any kind registered for the particular
    # packet.
    #
    # \param name   Name of the object to report on
    # \return Total number of faults registered for the given packet
    def FaultCount(self, name: str) -> int:
        if name not in self.packets:
            raise NoSuchPacket()
        return self.packets[name].FaultCount()
    
    ## Generate a printable representation of the statistics for all of the packets observed
    def __str__(self) -> str:
        n_sentences = len(self.packets)
        rtn = f'Packet Statistics ({n_sentences} unique seen):\n'
        for p in self.packets:
            rtn += f'\t{p:>17}: {self.packets[p]}\n'
        return rtn
