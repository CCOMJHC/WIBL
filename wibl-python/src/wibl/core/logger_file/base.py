##\file base.py
# \brief Library objects for reading Seabed 2030 data logger files
#
# The Seabed 2030 low-cost logger generates files from NMEA2000 onto the SD card in
# fairly efficient binary format, with a timestamp from the local machine.  The code
# here unpacks this format and makes the data available.
#
# Copyright 2026 Center for Coastal and Ocean Mapping & NOAA-UNH Joint
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

import struct
from abc import ABC, abstractmethod
import io
from enum import Enum
from typing import TypeVar, Type, Generic


## Exception used to report bad keyword parameters when setting up a packet from scratch in code
class SpecificationError(Exception):
    pass

## Exception used to report a bad translation of a packet (rather than passing up a raw struct exception)
class PacketTranscriptionError(Exception):
    pass


# HEY YOU! YEAH, YOU THERE AT THE KEYBOARD!  Did you remember to update LogConvert/src/serialisation.h/cpp
# with the specification for that cool packet you just addded?

## Enumeration of the identification numbers associated with the various packets in a WIBL file
class PacketTypes(Enum):
    ## Version information for the logger's file construction code, and the NMEA2000 and NMEA0183 loggers
    SerialiserVersion = 0
    ## NMEA2000 SystemTime information
    SystemTime = 1
    ## NMEA2000 Attitude (roll, pitch, yaw) information
    Attitude = 2
    ## NMEA2000 Depth information
    Depth = 3
    ## NMEA2000 Course-over-ground information
    COG = 4
    ## NMEA2000 GNSS report information
    GNSS = 5
    ## NMEA2000 Environmental (temperature, pressure, and humidity) information
    Environment = 6
    ## NMEA2000 Temperature information
    Temperature = 7
    ## NMEA2000 Humidity information
    Humidity = 8
    ## NMEA2000 Pressure information
    Pressure = 9
    ## Encapsulated NMEA0183 serial sentence
    SerialString = 10
    ## Local motion sensor (three-axis acceleration, three-axis gyro) information
    Motion = 11
    ## Logger and ship identification information used for construction GeoJSON metadata on output
    Metadata = 12
    ## Requests for algorithms to be run on the data in post-processing
    AlgorithmRequest = 13
    ## Arbitrary JSON metadata string used to fill in platform-specific items in the GeoJSON metadata on output
    JSONMetadata = 14
    ## Specification for a NMEA0183 packet to be recorded at the logger
    NMEA0183Filter = 15
    ## JSON-formatted list of sensor scale factors to convert packed binary data to float
    SensorScales = 16
    ## Raw local IMU data (i.e., integer values) to be converted into floats
    RawIMU = 17
    ## Setup information JSON string for the current logger configuration
    Setup = 18
    ## PGNs being written to file in binary format (JSON list)
    NMEA2000PGNs = 19
    ## NMEA2000 binary data packets (for auxiliary data)
    NMEA2000Binary = 20


## Convert from Kelvin to degrees Celsius
#
# Temperature is stored in the NMEA2000 packets as Kelvin, but that isn't terribly useful for end users.  This converts
# into degrees Celsius so that output is more useable.
#
# \param temp   Temperature in Kelvin
# \return Temperature in degrees Celsius
def temp_to_celsius(temp):
    return temp - 273.15


## Convert from Pascals to millibars
#
# Pressure is stored in the NMEA2000 packets as Pascals, but that isn't terribly useful for end users.  This converts
# into millibars so that output is more useable.
#
# \param pressure   Pressure in Pascals
# \return Pressure in millibars
def pressure_to_mbar(pressure):
    return pressure / 100.0


## Convert from radians to degrees
#
# Angles are stored in the NMEA2000 packets as radians, but that isn't terribly useful for end users (at least for
# display).  This converts into degrees so that output is more useable.
#
# \param rads   Angle in radians
# \return Angle in degrees
def angle_to_degs(rads):
    return rads*180.0/3.1415926535897932384626433832795



## Base class for all data packets that can be read from the binary file
#
# This provides a common base class for all of the data packets, and stores the information on the date and time at
# which the packet was received.
class DataPacket(ABC):
    ## Initialise the base packet with date and timestamp for the packet reception time
    #
    # This simply stores the date and time for the packet reception
    #
    # \param self       Pointer to the object
    # \param date       Days elapsed since 1970-01-01
    # \param timestamp  Seconds since midnight on the day
    def __init__(self, date, timestamp, elapsed):
        ## Date in days since 1970-01-01
        self.date = date
        ## Time in seconds since midnight on the day in question
        self.timestamp = timestamp
        ## Time in milliseconds since boot (reference time)
        self.elapsed = elapsed

    ## Abstract method for constructing the payload of the packet for serialisation
    #
    # This builds a buffer of the data required for the data packet so that the code can then serialise
    # it in new files.
    @abstractmethod
    def payload(self) -> bytes:
        pass

    ## Abstact method for a class to report its ID number
    #
    # Each packet written into the file has to have an ID number; the sub-class should know what this is.
    #
    @abstractmethod
    def id(self) -> int:
        pass

    ## Provide the fixed-text string name for this data packet
    #
    # This simply reports the human-readable name for the class so that reporting is possible
    #
    # \param self   Pointer to the object
    # \return String with the human-readable name of the packet
    @abstractmethod
    def name(self) -> str:
        pass

    ## Serialise the data in the current packet into the given file
    #
    # This wraps up the requirements to write a packet into a streamable binary output file.
    #
    # \param f  Binary output file
    def serialise(self, f: io.BufferedWriter) -> None:
        buffer = self.payload()
        id = self.id()
        #print(f'Writing packet with ID {id} and buffer length {len(buffer)}.')
        f.write(id.to_bytes(4, 'little'))
        f.write(len(buffer).to_bytes(4, 'little'))
        f.write(buffer)

    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data packet for the standard streaming output interface.
    #
    # \param self   Pointer to the object
    # \return String representation of the object
    def __str__(self):
        rtn = f'[{self.date} days, {self.timestamp} s., {self.elapsed} ms elapsed]'
        return rtn


class PacketFactoryBase(ABC):
    ## Initialise the packet factory
    #
    # This simply copies the file reference information for the binary data, and resets EOF indicator.
    #
    # \param self   Pointer to the object
    # \param file   Open file object, which must be opened for binary reads
    # \param strict_mode If True, raise exception if an error is encountered loading a packet. If False, print a warning message about the packet loading error.
    def __init__(self, file, *,
                 strict_mode: bool = False):
        ## File reference from which to read packets
        self.file = file
        ## Flag for end-of-file detection
        self.end_of_file = False
        self.strict_mode = strict_mode
        self.packets_read: int = 0

    def _generate_packet(self, pkt_id: int, buffer: bytes, last_pos: int) -> DataPacket | None:
        ...

    ## Extract the next packet from the binary data file
    #
    # This pulls the next packet header from the binary file, interprets the type and size, reads the bytes
    # corresponding to the packet payload, and the converts to an instantiation of the appropriate class object.
    #
    # \param self   Pointer to the object
    # \return DataPacket-derived object corresponding to the packet, or None if end-of-file or error
    def next_packet(self) -> DataPacket | None:
        if self.end_of_file:
            return None

        buffer = self.file.read(8)  # Header for each packet is U32 (ID) U32 (length in bytes)

        if len(buffer) < 8:
            self.end_of_file = True
            return None

        (pkt_id, pkt_len) = struct.unpack('<II', buffer)
        last_pos: int = self.file.tell()
        buffer = self.file.read(pkt_len)
        self.packets_read += 1
        return self._generate_packet(pkt_id, buffer, last_pos)

    ## Check for more data being available
    #
    # This checks for whether there is more data available in the file.
    #
    # \param self   Pointer to the object
    # \return True if there is more data to read, otherwise False
    def has_more(self):
        return not self.end_of_file


class LoggerFileBase(ABC):
    packet_factory: Type[PacketFactoryBase]

    def __init__(self, version_major: int, version_minor: int):
        self.version_major = version_major
        self.version_minor = version_minor

    def wibl_file_version(self) -> str:
        return f"{self.version_major}.{self.version_minor}"
