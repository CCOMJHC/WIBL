##\file LoggerFile.py
# \brief Library objects for reading Seabed 2030 data logger files
#
# The Seabed 2030 low-cost logger generates files from NMEA2000 onto the SD card in
# fairly efficient binary format, with a timestamp from the local machine.  The code
# here unpacks this format and makes the data available.
#
# Copyright 2020 Center for Coastal and Ocean Mapping & NOAA-UNH Joint
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
import json


## Exception used to report bad keyword parameters when setting up a packet from scratch in code
class SpecificationError(Exception):
    pass

## Exception used to report a bad translation of a packet (rather than passing up a raw struct exception)
class PacketTranscriptionError(Exception):
    pass

## Definition of major version of the file format represented by this description
wibl_file_version_major = 1
## Definition of minor version of the file format represented by this description
wibl_file_version_minor = 3

def wibl_file_version() -> str:
    return f'{wibl_file_version_major}.{wibl_file_version_minor}'

def numeric_file_version(major: int, minor: int) -> int:
    return major*1000 + minor

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
    def name(self):
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


## Implementation of the SystemTime NMEA2000 packet
#
# This retrieves the timestamp, logger elapsed time, and time source for a SystemTime packet serialised into the file.
#
class SystemTime(DataPacket):
    ## Initialise the object using the supplied buffer of data, or keywords if appropriate
    #
    # If the keywords include "buffer", the code assumes that the contents of the buffer are a serialised
    # version of the packet, and attempts to unpack it.  Otherwise, the code assumes that the keywords contain
    # information required to initialise the packet, and attempts to pull them from the dictionary.
    #
    # \param self   Reference for the object
    # \param kwargs Named arguments to initialise parameters, or "buffer" to unpack from binary data
    def __init__(self, **kwargs):
        if 'buffer' in kwargs:
            self.buffer_constructor(kwargs['buffer'])
        else:
            self.data_constructor(**kwargs)
    
    ## Initialise the SystemTime packet with date/time of reception, and logger elapsed time
    #
    # This picks out the date and timestamp for the packet (which is the indicated real time in the packet itself), and
    # then the logger elapsed time and data source (u16, double, u32, u8), total 15B.
    #
    # \param self   Pointer to the object
    # \param buffer Bytes buffer from which to unpack binary data
    def buffer_constructor(self, buffer: bytes) -> None:
        (date, timestamp, elapsed_time, data_source) = struct.unpack('<HdIB', buffer)
        ## Source of the timestamp (see documentation for decoding, but at least GNSS)
        self.data_source = data_source
        DataPacket.__init__(self, date, timestamp, elapsed_time)

    ## Generate a synthetic packet based on keywords
    #
    # This generates a synthetic packet based on keywords.  The expected keywords are:
    #   'elapsed_time':     Elapsed time (ms) since logger boot
    #   'date':             Estimated real-world date string for packet (yyyy-mm-dd)
    #   'timestamp':        Estimated real-world timestasmp for packet (seconds since midnight)
    #   'data_source':      Source for time information (see Wiki for details)
    def data_constructor(self, **kwargs) -> None:
        try:
            self.data_source = kwargs['data_source']
            super().__init__(kwargs['date'], kwargs['timestamp'], kwargs['elapsed_time'])
        except KeyError as e:
            raise SpecificationError('Bad packet parameters') from e
    
    def payload(self) -> bytes:
        buffer = struct.pack('<HdIB', self.date, self.timestamp, self.elapsed, self.data_source)
        return buffer
    
    def id(self) -> int:
        return PacketTypes.SystemTime.value

    ## Provide the fixed-text string name for this data packet
    #
    # This simply reports the human-readable name for the class so that reporting is possible
    #
    # \param self   Pointer to the object
    # \return String with the human-readable name of the packet
    def name(self):
        return 'SystemTime'

    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data packet for the standard streaming output interface.
    #
    # \param self   Pointer to the object
    # \return String representation of the object
    def __str__(self):
        rtn = super().__str__() + f' {self.name()}:  source = {self.data_source}'
        return rtn

## Implementation of the Attitude NMEA2000 packet
#
# The attitude message contains estimates of roll, pitch, and yaw of the ship, without any indication of where the data
# is coming from.  Consequently, the data is just reported directly.
class Attitude(DataPacket):
    ## Initialise the object using the supplied buffer of data, or keywords if appropriate
    #
    # If the keywords include "buffer", the code assumes that the contents of the buffer are a serialised
    # version of the packet, and attempts to unpack it.  Otherwise, the code assumes that the keywords contain
    # information required to initialise the packet, and attempts to pull them from the dictionary.
    #
    # \param self   Reference for the object
    # \param kwargs Named arguments to initialise parameters, or "buffer" to unpack from binary data
    def __init__(self, **kwargs):
        if 'buffer' in kwargs:
            self.buffer_constructor(kwargs['buffer'])
        else:
            self.data_constructor(**kwargs)

    ## Initialise the Attitude packet with reception timestamp, and raw data
    #
    # This picks out the date and time of message reception (based on the last known good real time estimate), and the
    # raw attitude data (u16, double, double, double, double), total 34B.  Attitude values are in radians.
    #
    # \param self   Pointer to the object
    # \param buffer Bytes byffer from which to unpack binary data
    def buffer_constructor(self, buffer: bytes) -> None:
        (date, timestamp, elapsed_time, yaw, pitch, roll) = struct.unpack("<HdIddd", buffer)
        ## Yaw angle of the ship, radians (+ve clockwise from north)
        self.yaw = yaw
        ## Pitch angle of the ship, radians (+ve bow up)
        self.pitch = pitch
        ## Roll angle of the ship, radians (+ve port up)
        self.roll = roll
        DataPacket.__init__(self, date, timestamp, elapsed_time)

    def payload(self) -> bytes:
        buffer = struct.pack('<HdIddd', self.date, self.timestamp, self.elapsed, self.yaw, self.pitch, self.roll)
        return buffer
    
    ## Generate a synthetic packet based on keywords
    #
    # This generates a synthetic packet based on keywords.  The expected keywords are:
    #   'elapsed_time':     Elapsed time (ms) since logger boot
    #   'date':             Estimated real-world date string for packet (yyyy-mm-dd)
    #   'timestamp':        Estimated real-world timestasmp for packet (seconds since midnight)
    #   'yaw':              Yaw angle (radians, +ve clockwise from north)
    #   'pitch':            Pitch angle (radians, +ve bow up)
    #   'roll':             Roll angle (radians, +ve port up)
    def data_constructor(self, **kwargs) -> None:
        try:
            self.yaw = kwargs['yaw']
            self.pitch = kwargs['pitch']
            self.roll = kwargs['roll']
            super().__init__(kwargs['date'], kwargs['timestamp'], kwargs['elapsed_time'])
        except KeyError as e:
            raise SpecificationError('Bad packet parameters') from e

    def id(self) -> int:
        return PacketTypes.Attitude.value

    ## Provide the fixed-text string name for this data packet
    #
    # This simply reports the human-readable name for the class so that reporting is possible
    #
    # \param self   Pointer to the object
    # \return String with the human-readable name of the packet
    def name(self):
        return "Attitude"

    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data packet for the standard streaming output interface.
    #
    # \param self   Pointer to the object
    # \return String representation of the object
    def __str__(self):
        rtn = super().__str__() + f' {self.name()}: yaw = {angle_to_degs(self.yaw)} deg, pitch = {angle_to_degs(self.pitch)} deg, roll = {angle_to_degs(self.roll)} deg'
        return rtn

## Implement the Observed Depth NMEA2000 message
#
# The depth message includes the observed depth, the offset that needs to be applied to it either for rise from the keel
# or waterline, and the maximum depth that can be observed (allowing for some filtering).
class Depth(DataPacket):
    ## Initialise the object using the supplied buffer of data, or keywords if appropriate
    #
    # If the keywords include "buffer", the code assumes that the contents of the buffer are a serialised
    # version of the packet, and attempts to unpack it.  Otherwise, the code assumes that the keywords contain
    # information required to initialise the packet, and attempts to pull them from the dictionary.
    #
    # \param self   Reference for the object
    # \param kwargs Named arguments to initialise parameters, or "buffer" to unpack from binary data
    def __init__(self, **kwargs):
        if 'buffer' in kwargs:
            self.buffer_constructor(kwargs['buffer'])
        else:
            self.data_constructor(**kwargs)

    ## Initialise the Depth packet with reception timestamp and raw data
    #
    # This picks out the date and time of message reception (based on the last known good real time estimate), and the
    # raw depth, offset, and range data (u16, double, double, double, double) for 34B total.  Depths are in metres
    #
    # \param self   Pointer to the object
    # \param buffer Bytes buffer from which to unpack binary data
    def buffer_constructor(self, buffer: bytes) -> None:
        (date, timestamp, elapsed_time, depth, offset, range) = struct.unpack('<HdIddd', buffer)
        ## Observed depth below transducer, metres
        self.depth = depth
        ## Offset for depth, metres.
        # This is an offset to apply to reference the depth to either the water surface, or the keel.  Positive
        # values imply that the correction is for water surface to transducer; negative implies transducer to keel
        self.offset = offset
        ## Maximum range of observation, metres
        self.range = range
        super().__init__(date, timestamp, elapsed_time)

    def payload(self) -> bytes:
        buffer = struct.pack('<HdIddd', self.date, self.timestamp, self.elapsed, self.depth, self.offset, self.range)
        return buffer
    
    def id(self) -> int:
        return PacketTypes.Depth.value
    
    ## Generate a synthetic packet based on keywords
    #
    # This generates a synthetic packet based on keywords.  The expected keywords are:
    #   'elapsed_time':     Elapsed time (ms) since logger boot
    #   'date':             Estimated real-world date string for packet (yyyy-mm-dd)
    #   'timestamp':        Estimated real-world timestasmp for packet (seconds since midnight)
    #   'depth':            Depth indicated (m)
    #   'offset':           Offset applied to the depth before reporting (m)
    #   'range':            Maximum range of the echosounder (m)
    def data_constructor(self, **kwargs) -> None:
        try:
            self.depth = kwargs['depth']
            self.offset = kwargs['offset']
            self.range = kwargs['range']
            super().__init__(kwargs['date'], kwargs['timestamp'], kwargs['elapsed_time'])
        except KeyError as e:
            raise SpecificationError('Bad packet parameters') from e

    ## Provide the fixed-text string name for this data packet
    #
    # This simply reports the human-readable name for the class so that reporting is possible
    #
    # \param self   Pointer to the object
    # \return String with the human-readable name of the packet
    def name(self):
        return "Depth"

    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data packet for the standard streaming output interface.
    #
    # \param self   Pointer to the object
    # \return String representation of the object
    def __str__(self):
        rtn = super().__str__() + f' {self.name()}: depth = {self.depth}m, offset = {self.offset}m, range = {self.range}m'
        return rtn

## Implement the Course-over-Ground Rapid NMEA2000 message
#
# The Course-over-ground/Speed-over-ground message is sent more frequently that most, and contains estimates of the
# current course and speed.
class COG(DataPacket):
    ## Initialise the object using the supplied buffer of data, or keywords if appropriate
    #
    # If the keywords include "buffer", the code assumes that the contents of the buffer are a serialised
    # version of the packet, and attempts to unpack it.  Otherwise, the code assumes that the keywords contain
    # information required to initialise the packet, and attempts to pull them from the dictionary.
    #
    # \param self   Reference for the object
    # \param kwargs Named arguments to initialise parameters, or "buffer" to unpack from binary data
    def __init__(self, **kwargs):
        if 'buffer' in kwargs:
            self.buffer_constructor(kwargs['buffer'])
        else:
            self.data_constructor(**kwargs)

    ## Initialise the COG-SOG packet with reception timestamp and raw data
    #
    # This picks out the date and time of message reception (based on the last known good real time estimate), and the
    # course/speed over ground (u16, double, double, double) for 26B total.  Course is in radians, speed in m/s.
    #
    # \param self   Pointer to the objet
    # \param buffer Bytes buffer from which to unpack binary data
    def buffer_constructor(self, buffer: bytes) -> None:
        (date, timestamp, elapsed_time, courseOverGround, speedOverGround) = struct.unpack('<HdIdd', buffer)
        ## Course over ground (radians)
        self.courseOverGround = courseOverGround
        ## Speed over ground (m/s)
        self.speedOverGround = speedOverGround
        super().__init__(date, timestamp, elapsed_time)
    
    def payload(self) -> bytes:
        buffer = struct.pack('<HdIdd', self.date, self.timestamp, self.elapsed, self.courseOverGround, self.speedOverGround)
        return buffer

    def id(self) -> int:
        return PacketTypes.COG.value
    
    ## Generate a synthetic packet based on keywords
    #
    # This generates a synthetic packet based on keywords.  The expected keywords are:
    #   'elapsed_time':     Elapsed time (ms) since logger boot
    #   'date':             Estimated real-world date string for packet (yyyy-mm-dd)
    #   'timestamp':        Estimated real-world timestasmp for packet (seconds since midnight)
    #   'cog':              Course over ground (CW from north), radians
    #   'sog':              Speed over ground (m/s)
    def data_constructor(self, **kwargs) -> None:
        try:
            self.courseOverGround = kwargs['cog']
            self.speedOverGround = kwargs['sog']
            super().__init__(kwargs['date'], kwargs['timestamp'], kwargs['elapsed_time'])
        except KeyError as e:
            raise SpecificationError('Bad packet parameters') from e

    ## Provide the fixed-text string name for this data packet
    #
    # This simply reports the human-readable name for the class so that reporting is possible
    #
    # \param self   Pointer to the object
    # \return String with the human-readable name of the packet
    def name(self):
        return 'Course Over Ground'

    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data packet for the standard streaming output interface.
    #
    # \param self   Pointer to the object
    # \return String representation of the object
    def __str__(self):
        rtn = super().__str__() + f' {self.name()}: course over ground = {angle_to_degs(self.courseOverGround)} deg, speed over ground = {self.speedOverGround} m/s'
        return rtn

## Implement the GNSS observation NMEA2000 message
#
# The GNSS observation message contains a single GNSS observation from a receiver on the ship (multiple receivers are
# possible, of course).  This contains all of the usual suspects that would come from a GPGGA message in NMEA0183, but
# has better information on correctors, and methods of correction, which are preserved here.
class GNSS(DataPacket):
    ## Initialise the object using the supplied buffer of data, or keywords if appropriate
    #
    # If the keywords include "buffer", the code assumes that the contents of the buffer are a serialised
    # version of the packet, and attempts to unpack it.  Otherwise, the code assumes that the keywords contain
    # information required to initialise the packet, and attempts to pull them from the dictionary.
    #
    # \param self   Reference for the object
    # \param kwargs Named arguments to initialise parameters, or "buffer" to unpack from binary data
    def __init__(self, **kwargs):
        if 'buffer' in kwargs:
            self.buffer_constructor(kwargs['buffer'])
        else:
            self.data_constructor(**kwargs)

    ## Initialise the GNSS packet with real time timestamp and raw data
    #
    # This picks out the raw data, including the validity time of the original message, including the latitude,
    # longitude, altitude, receiver type, receiver method, number of SVs, horizontal DOP, position DOP, geoid sep.,
    # number of reference stations, reference station type, reference station ID, and correction age, as
    # (u16, double, double, double, double, u8, u8, u8, double, double, double, u8, u8, u16, double) for
    # 73B total.  Latitude, longitude are in degrees; altitude, separation are metres; others are integers that are
    # mapped enum values for the receiver type (GPS, GLONASS, Galileo, etc.) and so on.  See Wiki for definitions.
    #
    # \param self   Pointer to the object
    # \param buffer Bytes buffer from which to unpack binary data
    def buffer_constructor(self, buffer: bytes) -> None:
        (sys_date, sys_timestamp, sys_elapsed, date, timestamp, latitude, longitude, altitude,
         receiverType, receiverMethod, numSVs, horizontalDOP, positionDOP, separation, numRefStations, refStationType,
         refStationID, correctionAge) = struct.unpack('<HdIHddddBBBdddBBHd', buffer)
        ## In-message date (days since epoch)
        self.msg_date = date
        ## In-message timestamp (seconds since midnight)
        self.msg_timestamp = timestamp
        ## Latitude of position, degrees
        self.latitude = latitude
        ## Longitude of position, degrees
        self.longitude = longitude
        ## Altitude of position, metres
        self.altitude = altitude
        ## GNSS receiver type (e.g., GPS, GLONASS, Beidou, Galileo, and some combinations)
        self.receiverType = receiverType
        ## GNSS receiver method (e.g., C/A, Differential, Float/fixed RTK, etc.)
        self.receiverMethod = receiverMethod
        ## Number of SVs in view
        self.numSVs = numSVs
        ## Horizontal dilution of precision (unitless)
        self.horizontalDOP = horizontalDOP
        ## Position dilution of precision (unitless)
        self.positionDOP = positionDOP
        ## Geoid-ellipsoid separation, metres (modeled)
        self.separation = separation
        ## Number of reference stations used in corrections
        self.numRefStations = numRefStations
        ## Reference station receiver type (as for receiverType)
        self.refStationType = refStationType
        ## Reference station ID number
        self.refStationID = refStationID
        ## Age of corrections, seconds
        self.correctionAge = correctionAge
        super().__init__(sys_date, sys_timestamp, sys_elapsed)
    
    def payload(self) -> bytes:
        buffer = struct.pack('<HdIHddddBBBdddBBHd', self.date, self.timestamp, self.elapsed, self.msg_date, self.msg_timestamp,
                                                    self.latitude, self.longitude, self.altitude, self.receiverType, self.receiverMethod,
                                                    self.numSVs, self.horizontalDOP, self.positionDOP, self.separation,
                                                    self.numRefStations, self.refStationType, self.refStationID, self.correctionAge)
        return buffer
    
    def id(self) -> int:
        return PacketTypes.GNSS.value

    ## Generate a synthetic packet based on keywords
    #
    # This generates a synthetic packet based on keywords.  The expected keywords are:
    #   'elapsed_time':     Elapsed time (ms) since logger boot
    #   'date':             Estimated real-world date string for packet (days since epoch))
    #   'timestamp':        Estimated real-world timestasmp for packet (seconds since midnight)
    #   'msg_date':         Message's claimed date string for data (days since epoch)
    #   'msg_timestamp':    Message's claimed timestasmp for data (seconds since midnight)
    #   'latitude':         Latitude of antenna phase centre (degrees)
    #   'longitude':        Longitude of antenna phase centre (degrees)
    #   'altitude':         Altitude of antenna phase centre (m)
    #   'rx_type':          Receiver type (see Wiki for details)
    #   'rx_method':        Receiver method (see Wiki for details)
    #   'num_svs':          Number of SVs in sight for position fix
    #   'horizontal_dop':   Horizontal Dilution of Position estimate
    #   'position_dop':     Position Dilution of Position estimate
    #   'sep':              Geoidal separation at current position (m)
    #   'n_refs':           Number of reference stations in use
    #   'refs_type':        Reference station type
    #   'refs_id':          Reference station ID
    #   'correction_age':   Age of the last set of aiding corrections being used
    #
    # Note that the specification provides for there to be more than one reference station, but apparently
    # only allows for one reference station type and ID to be given.  It's not clear how you would choose
    # which one you reported, or how you'd report more than one.
    def data_constructor(self, **kwargs) -> None:
        try:
            self.msg_date = kwargs['msg_date']
            self.msg_timestamp = kwargs['msg_timestamp']
            self.latitude = kwargs['latitude']
            self.longitude = kwargs['longitude']
            self.altitude = kwargs['altitude']
            self.receiverType = kwargs['rx_type']
            self.receiverMethod = kwargs['rx_method']
            self.numSVs = kwargs['num_svs']
            self.horizontalDOP = kwargs['horizontal_dop']
            self.positionDOP = kwargs['position_dop']
            self.separation = kwargs['sep']
            self.numRefStations = kwargs['n_refs']
            self.refStationType = kwargs['refs_type']
            self.refStationID = kwargs['refs_id']
            self.correctionAge = kwargs['correction_age']
            super().__init__(kwargs['date'], kwargs['timestamp'], kwargs['elapsed_time'])
        except KeyError as e:
            raise SpecificationError('Bad packet parameters') from e

    ## Provide the fixed-text string name for this data packet
    #
    # This simply reports the human-readable name for the class so that reporting is possible
    #
    # \param self   Pointer to the object
    # \return String with the human-readable name of the packet
    def name(self):
        return "GNSS"

    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data packet for the standard streaming output interface.
    #
    # \param self   Pointer to the object
    # \return String representation of the object
    def __str__(self):
        summary = io.StringIO()
        summary.write(super().__str__())
        summary.write(f' {self.name()}: in-message date = {self.msg_date} days, in-message time = {self.msg_timestamp} s., ')
        summary.write(f'latitude = {self.latitude} deg, longitude = {self.longitude} deg, altitude = {self.altitude} m, ')
        summary.write(f'GNSS type = {self.receiverType}, GNSS method = {self.receiverMethod}, ')
        summary.write(f'num. SVs = {self.numSVs}, ')
        summary.write(f'horizontal DOP = {self.horizontalDOP}, position DOP = {self.positionDOP}, ')
        summary.write(f'Geoid separation = {self.separation}m, number of ref. stations = {self.numRefStations}, ')
        summary.write(f'ref. station type = {self.refStationType}, ref. station ID = {self.refStationID}, correction age = {self.correctionAge}')
        summary.seek(0)
        return summary.read()

## Implement the Environment NMEA2000 message
#
# The Environment message was originally used to provide a combination of temperature, humidity, and pressure, but has
# since been deprecated in favour of individual messages (which also have the benefit of preserving the source information
# for the pressure data).  These are also supported, but this is provided for backwards compatibility.
class Environment(DataPacket):
    ## Initialise the object using the supplied buffer of data, or keywords if appropriate
    #
    # If the keywords include "buffer", the code assumes that the contents of the buffer are a serialised
    # version of the packet, and attempts to unpack it.  Otherwise, the code assumes that the keywords contain
    # information required to initialise the packet, and attempts to pull them from the dictionary.
    #
    # \param self   Reference for the object
    # \param kwargs Named arguments to initialise parameters, or "buffer" to unpack from binary data
    def __init__(self, **kwargs):
        if 'buffer' in kwargs:
            self.buffer_constructor(kwargs['buffer'])
        else:
            self.data_constructor(**kwargs)
        
    ## Initialise the Environment packet
    #
    # This picks out the date and time of message reception (based on the last known good real time estimate), and the
    # temperature (and source), humidity (and source), and pressure information as (u16, double, u8, double, u8, double,
    # double) for 36B total.  Temperature is Kelvin, humidity is %, pressure is Pascals.  The temperature and humidity
    # sources are enums (see Wiki for details); some filtering on allowed sources can happen at the logger, so not all
    # data might make it here from the NMEA2000 bus.
    #
    # \param self   Pointer to the object
    # \param buffer Bytes buffer from which to unpack binary data
    def buffer_constructor(self, buffer: bytes) -> None:
        (date, timestamp, elapsed_time, tempSource, temperature, humiditySource, humidity, pressure) = \
            struct.unpack('<HdIBdBdd', buffer)
        ## Source of temperature information (e.g., inside, outside)
        self.tempSource = tempSource
        ## Current temperature, Kelvin
        self.temperature = temperature
        ## Source of humidity information (e.g., inside, outside)
        self.humiditySource = humiditySource
        ## Relative humidity, percent
        self.humidity = humidity
        ## Current pressure, Pascals.
        # The source information for pressure information is not provided, so presumably this is meant to be
        # atmospheric pressure, rather than something more general.
        self.pressure = pressure
        super().__init__(date, timestamp, elapsed_time)

    def payload(self) -> bytes:
        buffer = struct.pack('<HdIBdBdd', self.date, self.timestamp, self.elapsed, self.tempSource, self.temperature, self.humiditySource, self.humidity, self.pressure)
        return buffer

    def id(self) -> int:
        return PacketTypes.Environment.value

    ## Generate a synthetic packet from keyword descriptions
    #
    # This generates a synetic packet from keywords.  Expected keywords are:
    #   'elapsed_time': Elapsed time (ms) since logger boot
    #   'date':         Real-world date associated with the data (days since epoch)
    #   'timestamp':    Real-world time associated with the data (seconds since midnight)
    #   'temp':         Temperature (C)
    #   'temp_source':  Source of temperature (see Wiki for details)
    #   'humidity':     Relative humidity (%)
    #   'humid_source': Source of humidity (see Wiki for details)
    #   'pressure':     Pressure (Pa)
    def data_constructor(self, **kwargs) -> None:
        try:
            self.tempSource = kwargs['temp_source']
            self.temperature = kwargs['temp']
            self.humiditySource = kwargs['humid_source']
            self.humidity = kwargs['humidity']
            self.pressure = kwargs['pressure']
            super().__init__(kwargs['date'], kwargs['timestamp'], kwargs['elapsed_time'])
        except KeyError as e:
            raise SpecificationError('Bad packet parameters') from e

    ## Provide the fixed-text string name for this data packet
    #
    # This simply reports the human-readable name for the class so that reporting is possible
    #
    # \param self   Pointer to the object
    # \return String with the human-readable name of the packet
    def name(self):
        return 'Environment'

    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data packet for the standard streaming output interface.
    #
    # \param self   Pointer to the object
    # \return String representation of the object
    def __str__(self):
        rtn = super().__str__() + f' {self.name()}: temperature = {temp_to_celsius(self.temperature)} ºC (source {self.tempSource}),  humidity = {self.humidity}% (source {self.humiditySource}), pressure = {pressure_to_mbar(self.pressure)} mBar'
        return rtn

## Implement the Temperature NMEA2000 message
#
# The Temperature message can serve a number of purposes, carrying temperature information for a variety of different
# sensors on the ship, including things like bait tanks and reefers.  The information is, however, always qualified
# with a source designator.  Some filtering of messages might happen at the logger, however, which means that not all
# temperature messages make it to here.
class Temperature(DataPacket):
    ## Initialise the object using the supplied buffer of data, or keywords if appropriate
    #
    # If the keywords include "buffer", the code assumes that the contents of the buffer are a serialised
    # version of the packet, and attempts to unpack it.  Otherwise, the code assumes that the keywords contain
    # information required to initialise the packet, and attempts to pull them from the dictionary.
    #
    # \param self   Reference for the object
    # \param kwargs Named arguments to initialise parameters, or "buffer" to unpack from binary data
    def __init__(self, **kwargs):
        if 'buffer' in kwargs:
            self.buffer_constructor(kwargs['buffer'])
        else:
            self.data_constructor(**kwargs)
    
    ## Initialise the Temperature message
    #
    # This picks out the date and time of message reception (based on the last known good real time estimate), and the
    # temperature source and temperature as (u16, double, u8, double) for 19B total.  Temperature source is a mapped
    # enum (see Wiki for details); temperature is Kelvin, so it's always positive.
    #
    # \param self   Pointer to the object
    # \param buffer Bytes object from which to unpack binary data
    def buffer_constructor(self, buffer: bytes) -> None:
        (date, timestamp, elapsed_time, tempSource, temperature) = struct.unpack('<HdIBd', buffer)
        ## Source of temperature information (e.g., water, air, cabin)
        self.tempSource = tempSource
        ## Temperature of source, Kelvin
        self.temperature = temperature
        super().__init__(date, timestamp, elapsed_time)

    def payload(self) -> bytes:
        buffer = struct.pack('<HdIBd', self.date, self.timestamp, self.elapsed, self.tempSource, self.tempSource)
        return buffer

    def id(self) -> int:
        return PacketTypes.Temperature.value
    
    ## Generate a synthetic packet from keyword descriptions
    #
    # This generates a synetic packet from keywords.  Expected keywords are:
    #   'elapsed_time': Elapsed time (ms) since logger boot
    #   'date':         Real-world date associated with the data
    #   'timestamp':    Real-world time associated with the data
    #   'temp':         Temperature (C)
    #   'temp_source':  Source of temperature (see Wiki for details)
    def data_constructor(self, **kwargs) -> None:
        try:
            self.tempSource = kwargs['temp_source']
            self.temperature = kwargs['temp']
            super().__init__(kwargs['date'], kwargs['timestamp'], kwargs['elapsed_time'])
        except KeyError as e:
            raise SpecificationError('Bad packet parameters') from e

    ## Provide the fixed-text string name for this data packet
    #
    # This simply reports the human-readable name for the class so that reporting is possible
    #
    # \param self   Pointer to the object
    # \return String with the human-readable name of the packet
    def name(self):
        return 'Temperature'

    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data packet for the standard streaming output interface.
    #
    # \param self   Pointer to the object
    # \return String representation of the object
    def __str__(self):
        rtn = super().__str__() + f' {self.name()}: temperature = {temp_to_celsius(self.temperature)} ºC (source {self.tempSource})'
        return rtn

## Implement the Humidity NMEA2000 message
#
# The Humidity message can serve a number of purposes, carrying humidity information for a variety of different sensors
# on the ship, including interior and exterior.  The information is, however, always qualified with a source designator.
# Some filtering of messages might happen at the logger, however, which means that not all humidity messages make it
# to here.
class Humidity(DataPacket):
    ## Initialise the object using the supplied buffer of data, or keywords if appropriate
    #
    # If the keywords include "buffer", the code assumes that the contents of the buffer are a serialised
    # version of the packet, and attempts to unpack it.  Otherwise, the code assumes that the keywords contain
    # information required to initialise the packet, and attempts to pull them from the dictionary.
    #
    # \param self   Reference for the object
    # \param kwargs Named arguments to initialise parameters, or "buffer" to unpack from binary data
    def __init__(self, **kwargs):
        if 'buffer' in kwargs:
            self.buffer_constructor(kwargs['buffer'])
        else:
            self.data_constructor(**kwargs)
    
    ## Initialise the Humidty message
    #
    # This picks out the date and time of message reception (based on the last known good real time estimate), and the
    # humidity source and humidity as (u16, double, u8, double) for 19B total.  Humidity source is a mapped enum (see
    # Wiki for details); humidity is a relative percentage.
    #
    # \param self   Pointer to the object
    # \param buffer Bytes object from which to unpack the binary data
    def buffer_constructor(self, buffer: bytes) -> None:
        (date, timestamp, elapsed_time, humiditySource, humidity) = struct.unpack('<HdIBd', buffer)
        ## Source of humidity (e.g., inside, outside)
        self.humiditySource = humiditySource
        ## Humidity observation, percent
        self.humidity = humidity
        super().__init__(date, timestamp, elapsed_time)
    
    def payload(self) -> bytes:
        buffer = struct.pack('<HdIBd', self.date, self.timestamp, self.elapsed, self.humiditySource, self.humidity)
        return buffer
    
    def id(self) -> int:
        return PacketTypes.Humidity.value
    
    ## Generate a synthetic packet from keyword descriptions
    #
    # This generates a synetic packet from keywords.  Expected keywords are:
    #   'elapsed_time': Elapsed time (ms) since logger boot
    #   'date':         Real-world date associated with the data
    #   'timestamp':    Real-world time associated with the data
    #   'humidity':     Relative humidity (%)
    #   'humid_source': Source of humidity (see Wiki for details)
    def data_constructor(self, **kwargs):
        try:
            self.humiditySource = kwargs['humid_source']
            self.humidity = kwargs['humidity']
            super().__init__(kwargs['date'], kwargs['timestamp'], kwargs['elapsed_time'])
        except KeyError as e:
            raise SpecificationError('Bad packet parameters') from e

    ## Provide the fixed-text string name for this data packet
    #
    # This simply reports the human-readable name for the class so that reporting is possible
    #
    # \param self   Pointer to the object
    # \return String with the human-readable name of the packet
    def name(self):
        return 'Humidity'

    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data packet for the standard streaming output interface.
    #
    # \param self   Pointer to the object
    # \return String representation of the object
    def __str__(self):
        rtn = super().__str__() + f' {self.name()}: humidity = {self.humidity} % (source {self.humiditySource})'
        return rtn

## Implement the Pressure NMEA2000 message
#
# The Pressure message can serve a number of purposes, carrying pressure information for a variety of different sensors
# on the ship, including atmospheric and compressed air systems.  The information is, however, always qualified with a
# source designator.  Some filtering of messages might happen at the logger, however, which means that not all pressure
# messages make it to here.
class Pressure(DataPacket):
    ## Initialise the object using the supplied buffer of data, or keywords if appropriate
    #
    # If the keywords include "buffer", the code assumes that the contents of the buffer are a serialised
    # version of the packet, and attempts to unpack it.  Otherwise, the code assumes that the keywords contain
    # information required to initialise the packet, and attempts to pull them from the dictionary.
    #
    # \param self   Reference for the object
    # \param kwargs Named arguments to initialise parameters, or "buffer" to unpack from binary data
    def __init__(self, **kwargs):
        if 'buffer' in kwargs:
            self.buffer_constructor(kwargs['buffer'])
        else:
            self.data_constructor(**kwargs)

    ## Initialise the Pressure message
    #
    # This picks out the date and time of message reception (based on the last known good real time estimate), and the
    # pressure source and pressure as (u16, double, u8, double) for 19B total.  Pressure source is a mapped enum (see
    # Wiki for details); pressure is in Pascals.
    #
    # \param self   Pointer to the object
    # \param buffer Bytes object from which to unpack the information
    def buffer_constructor(self, buffer: bytes) -> None:
        (date, timestamp, elapsed_time, pressureSource, pressure) = struct.unpack('<HdIBd', buffer)
        ## Source of pressure measurement (e.g., atmospheric, compressed air)
        self.pressureSource = pressureSource
        ## Pressure, Pascals
        self.pressure = pressure
        super().__init__(date, timestamp, elapsed_time)
    
    def payload(self) -> bytes:
        buffer = struct.pack('<HdIBd', self.date, self.timestamp, self.elapsed, self.pressureSource, self.pressure)
        return buffer
    
    def id(self) -> int:
        return PacketTypes.Pressure.value

    ## Generate a synthetic packet from keyword descriptions
    #
    # This generates a synetic packet from keywords.  Expected keywords are:
    #   'elapsed_time': Elapsed time (ms) since logger boot
    #   'date':         Real-world date associated with the data
    #   'timestamp':    Real-world time associated with the data
    #   'pressure':     Pressure in Pascals
    #   'press_source': Source of pressure (see Wiki for details)
    def data_constructor(self, **kwargs):
        try:
            self.pressureSource = kwargs['press_source']
            self.pressure = kwargs['pressure']
            super().__init__(kwargs['date'], kwargs['timestamp'], kwargs['elapsed_time'])
        except KeyError as e:
            raise SpecificationError('Bad packet parameters') from e
    
    ## Provide the fixed-text string name for this data packet
    #
    # This simply reports the human-readable name for the class so that reporting is possible
    #
    # \param self   Pointer to the object
    # \return String with the human-readable name of the packet
    def name(self):
        return "Pressure"

    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data packet for the standard streaming output interface.
    #
    # \param self   Pointer to the object
    # \return String representation of the object
    def __str__(self):
        rtn = super().__str__() + f' {self.name()}: pressure = {pressure_to_mbar(self.pressure)} mBar (source {self.pressureSource})'
        return rtn

## Implement the NMEA0183 serial data message
#
# As an extension, the logger can (if the hardware is populated) record data from two separate RS-422 NMEA0183
# data streams, and timestamp in the same manner as the rest of the data.  The code encapsulates the entire message
# in this packet, rather than trying to have a separate packet for each data string type (at least for now).
class SerialString(DataPacket):
    ## Initialise the object using the supplied buffer of data, or keywords if appropriate
    #
    # If the keywords include "buffer", the code assumes that the contents of the buffer are a serialised
    # version of the packet, and attempts to unpack it.  Otherwise, the code assumes that the keywords contain
    # information required to initialise the packet, and attempts to pull them from the dictionary.
    #
    # \param self   Reference for the object
    # \param kwargs Named arguments to initialise parameters, or "buffer" to unpack from binary data
    def __init__(self, **kwargs):
        if 'buffer' in kwargs:
            self.buffer_constructor(kwargs['buffer'])
        else:
            self.data_constructor(**kwargs)

    def buffer_constructor(self, buffer: bytes) -> None:
        string_length = len(buffer) - 4
        (elapsed_time, data) = struct.unpack(f'<I{string_length}s', buffer)
        ## Serial data encapsulated in the packet
        self.data = data
        super().__init__(0, 0, elapsed_time)

    def payload(self) -> bytes:
        data_len = len(self.data)
        buffer = struct.pack(f'<I{data_len}s', self.elapsed, self.data)
        return buffer

    def id(self) -> int:
        return PacketTypes.SerialString.value

    ## Generate a synthetic packet from keyword specification
    #
    # This generates a synthetic packet from keywords.  Expected keywords are:
    #   'elapsed_time': Elapsed time (ms) since logger boot
    #   'payload':      A NMEA0183-formatted sentence, complete with leading '$' and tailing CRC
    def data_constructor(self, **kwargs) -> None:
        try:
            self.data = kwargs['payload']
            super().__init__(0, 0, kwargs['elapsed_time'])
        except KeyError as e:
            raise SpecificationError('Bad packet parameters') from e

    ## Provide the fixed-text string name for this data packet
    #
    # This simply reports the human-readable name for the class so that reporting is possible
    #
    # \param self   Pointer to the object
    # \return String with the human-readable name of the packet
    def name(self):
        return 'SerialString'

    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data packet for the standard streaming output interface.
    #
    # \param self   Pointer to the object
    # \return String representation of the object
    def __str__(self):
        rtn = super().__str__() + f' {self.name()}: payload = |{self.data}|'
        return rtn


##  Unpack the serialiser version information packet, and store versions
#
# This picks apart the information on the version of the serialiser used to generate the file being read.  This should
# always be the first packet in the file, and allows the code to adjust readers if necessary in order to read what's
# coming next.
class SerialiserVersion(DataPacket):
    ## Initialise the object using the supplied buffer of data, or keywords if appropriate
    #
    # If the keywords include "buffer", the code assumes that the contents of the buffer are a serialised
    # version of the packet, and attempts to unpack it.  Otherwise, the code assumes that the keywords contain
    # information required to initialise the packet, and attempts to pull them from the dictionary.
    #
    # \param self   Reference for the object
    # \param kwargs Named arguments to initialise parameters, or "buffer" to unpack from binary data
    def __init__(self, **kwargs):
        if 'buffer' in kwargs:
            self.buffer_constructor(kwargs['buffer'])
        else:
            self.data_constructor(**kwargs)

    def buffer_constructor(self, buffer: bytes) -> None:
        base = 0
        (major, minor) = struct.unpack_from('<HH', buffer, base)
        base += 4
        if numeric_file_version(major, minor) < numeric_file_version(wibl_file_version_major, wibl_file_version_minor):
            # Dealing with an older version of the file format, which means that we have slight
            # differences in the rest of the buffer, and have to fake some of the data.
            (n2000_major, n2000_minor, n2000_patch, n0183_major, n0183_minor, n0183_patch) = \
                struct.unpack_from('<HHHHHH', buffer, base)
            imu_major = 0
            imu_minor = 0
            imu_patch = 0
        else:
            (n2000_major, n2000_minor, n2000_patch, n0183_major, n0183_minor, n0183_patch, imu_major, imu_minor, imu_patch) = \
                struct.unpack_from('<HHHHHHHHH', buffer, base)
        ## Major software version for the serialiser code
        self.major = major
        ## Minor software version for the serialiser code
        self.minor = minor
        ## A tuple of the NMEA2000 software version
        self.nmea2000 = (n2000_major, n2000_minor, n2000_patch)
        ## A tuple of the NMEA0183 software version
        self.nmea0183 = (n0183_major, n0183_minor, n0183_patch)
        ## A tuple of the MIMU software version
        self.imu = (imu_major, imu_minor, imu_patch)
        ## NMEA2000 software version information
        self.nmea2000_version = f'{n2000_major}.{n2000_minor}.{n2000_patch}'
        ## NMEA0183 software version information
        self.nmea0183_version = f'{n0183_major}.{n0183_minor}.{n0183_patch}'
        ## IMU software version information
        self.imu_version = f'{imu_major}.{imu_minor}.{imu_patch}'

        super().__init__(0, 0.0, 0)

    def payload(self) -> bytes:
        buffer = struct.pack('<HHHHHHHHHHH', self.major, self.minor, self.nmea2000[0], self.nmea2000[1], self.nmea2000[2],
                            self.nmea0183[0], self.nmea0183[1], self.nmea0183[2],
                            self.imu[0], self.imu[1], self.imu[2])
        return buffer
    
    def id(self) -> int:
        return PacketTypes.SerialiserVersion.value
    
    ## Generate a synthetic packet from a keyword specification
    #
    # This generates the packet based on keywords from the call.  Expected keywords are:
    #   'major':    Major version of the serialiser (i.e., what's generating the data)
    #   'minor':    Minor version of the serialiser
    #   'n2000':    3-tuple (major, minor, patch) for the NMEA2000 receiver
    #   'n0183':    3-tuple (major, minor, patch) for the NMEA0183 receiver
    #   'imu':      3-tuple (major, minor, patch) for the IMU receiver
    def data_constructor(self, **kwargs) -> None:
        try:
            self.major = kwargs['major']
            self.minor = kwargs['minor']
            self.nmea2000 = kwargs['n2000']
            self.nmea0183 = kwargs['n0183']
            self.imu = kwargs['imu']
            self.nmea2000_version = f'{self.nmea2000[0]}.{self.nmea2000[1]}.{self.nmea2000[2]}'
            self.nmea0183_version = f'{self.nmea0183[0]}.{self.nmea0183[1]}.{self.nmea0183[2]}'
            self.imu_version = f'{self.imu[0]}.{self.imu[1]}.{self.imu[2]}'
            super().__init__(0, 0.0, 0)
        except KeyError as e:
            raise SpecificationError('Bad packet parameters') from e

    ## Provide the fixed-text string name for this data packet
    #
    # This simply reports the human-readable name for the class so that reporting is possible
    #
    # \param self   Pointer to the object
    # \return String with the human-readable name of the packet
    def name(self):
        return 'SerialiserVersion'

    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data packet for the standard streaming output interface.
    #
    # \param self   Pointer to the object
    # \return String representation of the object
    def __str__(self):
        rtn = super().__str__() + f' {self.name()}: version = {self.major}.{self.minor}, with NMEA2000 version {self.nmea2000},  NMEA0183 version {self.nmea0183}, and IMU version {self.imu}'
        return rtn

## Implement the motion sensor data packet
#
# This picks out the information from the on-board motion sensor (if available).  This data is not processed
# (e.g., with a Kalman filter) and may need further work before being useful.
class Motion(DataPacket):
    ## Initialise the object using the supplied buffer of data, or keywords if appropriate
    #
    # If the keywords include "buffer", the code assumes that the contents of the buffer are a serialised
    # version of the packet, and attempts to unpack it.  Otherwise, the code assumes that the keywords contain
    # information required to initialise the packet, and attempts to pull them from the dictionary.
    #
    # \param self   Reference for the object
    # \param kwargs Named arguments to initialise parameters, or "buffer" to unpack from binary data
    def __init__(self, **kwargs):
        if 'buffer' in kwargs:
            self.buffer_constructor(kwargs['buffer'])
        else:
            self.data_constructor(**kwargs)

    ## Construct a version of the packet from serialised binary data
    #
    # The buffer should contain 28 bytes for 3-axis acceleration, 3-axis gyro, and internal sensor temperature.
    #
    # \param self   Reference for the object
    # \param buffer A bytes object for the previously serialised packet
    def buffer_constructor(self, buffer: bytes) -> None:
        (elapsed, ax, ay, az, gx, gy, gz, temp) = struct.unpack('<Ifffffff', buffer)
        ## The acceleration vector, 3D
        self.accel = (ax, ay, az)
        ## The gyroscope rate vector, 3D
        self.gyro = (gx, gy, gz)
        # Die temperature of the motion sensor
        self.temp = temp
        super().__init__(0, 0.0, elapsed)

    def payload(self) -> bytes:
        buffer = struct.pack('<Ifffffff', self.elapsed, self.accel[0], self.accel[1], self.accel[2], self.gyro[0], self.gyro[1], self.gyro[2], self.temp)
        return buffer
    
    def id(self) -> int:
        return PacketTypes.Motion.value

    ## Generate an example of the packet from keyword specifications.
    #
    # This generates a synthetic packet based on keyword descriptions.  Expected keywords are:
    #   'elapsed_time': Elapsed time (ms) since logger boot
    #   'accel':        3-tuple of accelerations (x,y,z)
    #   'gyro':         3-tuple of gyro rates (x,y,z)
    #   'temp':         Scalar temperature
    def data_constructor(self, **kwargs) -> None:
        try:
            self.accel = kwargs['accel']
            self.gyro = kwargs['gyro']
            self.temp = kwargs['temp']
            super().__init__(0, 0.0, kwargs['elapsed_time'])
        except KeyError as e:
            raise SpecificationError('Bad packet parameters') from e

    ## Provide the fixed-text string name for this data pakcet
    #
    # This simply reports the human-readable name for the class so that reporting is possible
    #
    # \param self   Pointer to the object
    # \return String with the human-readable name of the packet
    def name(self):
        return 'Motion'
    
    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data packet for the standard streaming output interface.
    #
    # \param self   Pointer to the object
    # \return String representation of the object
    def __str__(self):
        rtn = super().__str__() + f' {self.name()}: acc = {self.accel}, gyro = {self.gyro}, temp = {self.temp}'
        return rtn

## Implement the basic metadata packet
#
# This picks out the information from the metadata packet, which gives identification
# information for the logger that created the file. Note that this is not the same as the
# JSONMetadata packet, which provides more detailled information for the post-processing code
# to generate/modify IHO B.12 style GeoJSON metadata.
class Metadata(DataPacket):
    ## Initialise the object using the supplied buffer of data, or keywords if appropriate
    #
    # If the keywords include "buffer", the code assumes that the contents of the buffer are a serialised
    # version of the packet, and attempts to unpack it.  Otherwise, the code assumes that the keywords contain
    # information required to initialise the packet, and attempts to pull them from the dictionary.
    #
    # \param self   Reference for the object
    # \param kwargs Named arguments to initialise parameters, or "buffer" to unpack from binary data
    def __init__(self, **kwargs):
        if 'buffer' in kwargs:
            self.buffer_constructor(kwargs['buffer'])
        else:
            self.data_constructor(**kwargs)

    def buffer_constructor(self, buffer: bytes) -> None:
        base = 0
        id_len, = struct.unpack_from('<I', buffer, base)
        base += 4
        unique_id, = struct.unpack_from(f'<{id_len}s', buffer, base)
        base += id_len
        name_len, = struct.unpack_from('<I', buffer, base)
        base += 4
        name, = struct.unpack_from(f'<{name_len}s', buffer, base)
        self.logger_name = unique_id.decode('UTF-8')
        self.ship_name = name.decode('UTF-8')
        super().__init__(0, 0.0, 0)

    def payload(self) -> bytes:
        logger_name_len = len(self.logger_name)
        ship_name_len = len(self.ship_name)
        buffer = struct.pack(f'<I{logger_name_len}sI{ship_name_len}s', logger_name_len, self.logger_name.encode('UTF-8'), ship_name_len, self.ship_name.encode('UTF-8'))
        return buffer
    
    def id(self) -> int:
        return PacketTypes.Metadata.value

    ## Implement a version of the packet from keywords
    #
    # This generates a synthetic packet based on keyword specifications.  Expected keywords are:
    #   'logger':   String containing the logger's unique identifier (typically a DCDB provider ID and a UUID)
    #   'shipname': String containing some human-readable description of the host platform, often a ship name.
    def data_constructor(self, **kwargs) -> None:
        try:
            self.logger_name = kwargs['logger']
            self.ship_name = kwargs['shipname']
            super().__init__(0, 0.0, 0)
        except KeyError as e:
            raise SpecificationError('Bad packet parameters') from e

    
    ## Provide the fixed-text string name for this data packet
    #
    # This simply reports the human-readable name for the class so that reporting is possible
    #
    # \param self   Pointer to the object
    # \return String with the human-readable name of the packet
    def name(self):
        return 'Metadata'
    
    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data packet for the standard streaming output interface
    #
    # \param self   Pointer to the object
    # \return String representation of the object
    def __str__(self):
        rtn = DataPacket.__str__(self) + f' {self.name()}: logger name (unique ID) = {self.logger_name}, shipname = {self.ship_name}'
        return rtn

## Implement the algorithm packet
#
# This picks out the information from the algorithm request packet, which provides an algorithm name
# and parameter set that the logger would recommend running on the data in the cloud, if available
class AlgorithmRequest(DataPacket):
    ## Initialise the object using the supplied buffer of data, or keywords if appropriate
    #
    # If the keywords include "buffer", the code assumes that the contents of the buffer are a serialised
    # version of the packet, and attempts to unpack it.  Otherwise, the code assumes that the keywords contain
    # information required to initialise the packet, and attempts to pull them from the dictionary.
    #
    # \param self   Reference for the object
    # \param kwargs Named arguments to initialise parameters, or "buffer" to unpack from binary data
    def __init__(self, **kwargs):
        if 'buffer' in kwargs:
            self.buffer_constructor(kwargs['buffer'])
        else:
            self.data_constructor(**kwargs)

    def buffer_constructor(self, buffer: bytes) -> None:
        base = 0
        algname_len, = struct.unpack_from('<I', buffer, base)
        base += 4
        algname, = struct.unpack_from(f'<{algname_len}s', buffer, base)
        base += algname_len
        param_len, = struct.unpack_from('<I', buffer, base)
        base += 4
        algparams, = struct.unpack_from(f'<{param_len}s', buffer, base)
        self.algorithm = algname
        self.parameters = algparams
        super().__init__(0, 0.0, 0)
    
    def payload(self) -> bytes:
        name_len = len(self.algorithm)
        param_len = len(self.parameters)
        buffer = struct.pack(f'<I{name_len}sI{param_len}s', name_len, self.algorithm, param_len, self.parameters)
        return buffer
    
    def id(self) -> int:
        return PacketTypes.AlgorithmRequest.value

    def data_constructor(self, **kwargs) -> None:
        try:
            self.algorithm = kwargs['name'].encode('UTF-8')
            self.parameters = kwargs['params'].encode('UTF-8')
            super().__init__(0, 0.0, 0)
        except KeyError as e:
            raise SerialiserVersion('Bad packet parameters') from e
    
    ## Provide the fixed-text string name for this data packet
    #
    # This simply report the human-readable name for the class so that reporting is possible
    #
    # \param self   Pointer to the object
    # \return String with the human-readable name of the packet
    def name(self):
        return 'AlgorithmRequest'
        
    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data pacet for the standard streaming output interface
    #
    # \param self   Pointer to the object
    # \return String representation of the obect
    def __str__(self):
        rtn = DataPacket.__str__(self) + f' {self.name()}: algorithm = {self.algorithm}, parameters = {self.parameters}'
        return rtn

## Implement the JSON metadata packet
#
# This picks out information on metadata elements that the logger would like to send into the JSON
# file being constructed for each data file being transmitted to the database.  This is provided by
# the user and cached on the logger, and then transmitted as is, without interpretation.
class JSONMetadata(DataPacket):
    ## Initialise the object using the supplied buffer of data, or keywords if appropriate
    #
    # If the keywords include "buffer", the code assumes that the contents of the buffer are a serialised
    # version of the packet, and attempts to unpack it.  Otherwise, the code assumes that the keywords contain
    # information required to initialise the packet, and attempts to pull them from the dictionary.
    #
    # \param self   Reference for the object
    # \param kwargs Named arguments to initialise parameters, or "buffer" to unpack from binary data
    def __init__(self, **kwargs):
        if 'buffer' in kwargs:
            self.buffer_constructor(kwargs['buffer'])
        else:
            self.data_constructor(**kwargs)

    def buffer_constructor(self, buffer: bytes) -> None:
        base = 0
        meta_len, = struct.unpack_from('<I', buffer, base)
        base += 4
        meta, = struct.unpack_from(f'<{meta_len}s', buffer, base)
        self.metadata_element = meta
        super().__init__(0, 0.0, 0)

    def payload(self) -> bytes:
        meta_len = len(self.metadata_element)
        buffer = struct.pack(f'<I{meta_len}s', meta_len, self.metadata_element)
        return buffer
    
    def id(self) -> int:
        return PacketTypes.JSONMetadata.value

    ## Construct the packet representation from keywords
    #
    # This constructs a representation of the packet from keywords.  Expected keywords are:
    #   'meta': String representation of a JSON-style dictionary containing any (IHO B.12 style) metadata
    #
    # Although the Python implementation doesn't mind, the logger implementation of the serialiser
    # requires that there be no CR/LF in the string; readers of the packet might have the same assumption.
    def data_constructor(self, **kwargs) -> None:
        try:
            if type(kwargs['meta']) != 'bytes':
                self.metadata_element = kwargs['meta'].encode('UTF-8')
            else:
                self.metadata_element = kwargs['meta']
            super().__init__(0, 0.0, 0)
        except KeyError as e:
            raise SpecificationError('Bad packet parameters') from e
        
    ## Provide the fixed-text string name for this data packet
    #
    # This simply reports the human-readable name for the class so that reporting is possible
    def name(self):
        return 'JSONMetadata'
    
    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data packet for the standard streaming output interface
    #
    # \param self
    # \return String representation of the object
    def __str__(self):
        rtn = DataPacket.__str__(self) + f' {self.name()}: metadata element = |{self.metadata_element.decode("UTF-8")}|'
        return rtn

## Implement a packet to hold information on NMEA0183 packets being recorded
#
# The logger has the ability to filter the NMEA0183 sentences that are received so that it only  records to
# SD card those that are of interest.  Getting the filtering right can be important to let the capture run
# for as long as possible. 
class NMEA0183Filter(DataPacket):
    ## Initialise the object using the supplied buffer of data, or keywords if appropriate
    #
    # If the keywords include "buffer", the code assumes that the contents of the buffer are a serialised
    # version of the packet, and attempts to unpack it.  Otherwise, the code assumes that the keywords contain
    # information required to initialise the packet, and attempts to pull them from the dictionary.
    #
    # \param self   Reference for the object
    # \param kwargs Named arguments to initialise parameters, or "buffer" to unpack from binary data
    def __init__(self, **kwargs):
        if 'buffer' in kwargs:
            self.buffer_constructor(kwargs['buffer'])
        else:
            self.data_constructor(**kwargs)
    
    ## Initialise the packet from a binary buffer
    #
    # This takes the binary buffer presented and unpacks into an instance of the packet.
    #
    # \param self   Reference for the object
    # \param buffer Binary buffer with serialised information for the packet
    def buffer_constructor(self, buffer: bytes) -> None:
        base = 0
        id_len, = struct.unpack_from('<I', buffer, base)
        base += 4
        recog_string, = struct.unpack_from(f'<{id_len}s', buffer, base)
        self.recog_string = recog_string
        super().__init__(0, 0.0, 0)
    
    ## Initialise the packet from keyword arguments
    #
    # This takes the keywords provided and attempts to initialise the packet.  For this packet, valid
    # keywords are:
    #   'sentence': String containing the three-letter sentence name(s) to be accepted for recording
    #
    # Note that you have to have comma-separated sentence names if more than one is provided.
    #
    # \param self       Reference for the object
    # \param **kwargs   Keyword dictionary with parameters for the packet
    def data_constructor(self, **kwargs) -> None:
        try:
            self.recog_string = kwargs['sentence'].encode('UTF-8')
            super().__init__(0, 0.0, 0)
        except KeyError as e:
            raise SpecificationError('Bad packet parameters') from e
    
    ## Encode the current packet for serialisation
    #
    # From the parameters set in the packet, convert to a stream of bytes that can be used to serialise
    # the packet to an output stream.  Note that this returns only the contents of the packet; the
    # packet length, recognition ID, etc., must be added separately.
    #
    # \param self   Reference for the object
    # \return Bytes array with the binary representation of the packet-specific parameters
    def payload(self) -> bytes:
        recog_len = len(self.recog_string)
        buffer = struct.pack(f'<I{recog_len}s', recog_len, self.recog_string)
        return buffer
    
    ## Provide the recognition ID for the packet, as used in the binary file
    #
    # Each packet has a reference number that's used as an ID; this routine provides that number
    #
    # \param self   Reference for the object
    # \returns Integer identification number for the packet
    def id(self) ->int:
        return PacketTypes.NMEA0183Filter.value

    ## Provide the fixed-text string name for this data packet
    #
    # This simply reports the human-readable name for the class so that reporting is possible
    #
    # \param self   Reference for the object
    # \return String with th ename of the object
    def name(self) -> str:
        return 'NMEA0183Filter'

    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data packet for standard streaming output interface
    #
    # \param self   Reference for the object
    # \return String representation of the object
    def __str__(self) -> str:
        rtn = DataPacket.__str__(self) + f' {self.name()}: sentence recognition string = |{self.recog_string.decode("UTF-8")}|'
        return rtn

## Implement a packet to store a JSON description of the sensor scales used by on-board sensors
#
# The WIBL logger has at least an on-board IMU, which generates integer readings for the accelerations
# and gyro rates; these need to be converted by known scale factors (depending on the maximum range
# configured) to give SI units (m/s and rad/s).  This packet contains a JSON-format string to provide
# these scales.  Of course, since it's just a JSON string, it can also be readily extended for other
# sensors that might be embedded in other implementations.
class SensorScales(DataPacket):
    ## Initialise the packet using either a bytes buffer from a file, or keywords ab initio
    #
    # If the keywords include "buffer", the code assumes that the contents of the buffer are a serialised
    # version of the packet, and attempts to unpack it.  Otherwise, the code assumes that the keywords contain
    # information required to initialise the packet, and attempts to pull them from the dictionary.
    #
    # \param self   Reference for the object
    # \param kwargs Named arguments to initialise parameters, or "buffer" to unpack from binary data 
    def __init__(self, **kwargs):
        if 'buffer' in kwargs:
            self.buffer_constructor(kwargs['buffer'])
        else:
            self.data_constructor(**kwargs)
    
    ## Construct for a serialised buffer of bytes
    #
    # This attempts to construct the packet from a previously serialised version, typically from a WIBL
    # logger.  The serialisation assumes a length word followed by a serialised JSON dictionary as a
    # simple C-style string.
    #
    # \param self   Reference for the object
    # \param buffer Binary buffer with serialised information for the packet
    def buffer_constructor(self, buffer: bytes) -> None:
        base = 0
        config_len, = struct.unpack_from('<I', buffer, base)
        base += 4
        convert_string = f'<{config_len}s'
        config, = struct.unpack_from(convert_string, buffer, base)
        self.config = json.loads(config)
        super().__init__(0, 0.0, 0)

    ## Initialise the packet from keyword arguments
    #
    # This takes the keywords provided and attempts to initialise the packet.  For this packet, valid
    # keywords are:
    #   'scales': Dict containing the parameters scales required for the packet
    #
    # \param self       Reference for the object
    # \param **kwargs   Keyword dictionary with parameters for the packet
    def data_constructor(self, **kwargs) -> None:
        try:
            if type(kwargs['scales']) != 'Dict':
                if type(kwargs['scales']) == 'bytes':
                    self.config = json.loads(kwargs['scales'].decode('UTF-8'))
                else:
                    self.config = json.load(kwargs['scales'])
            else:
                self.config = kwargs['scales']
            super().__init__(0, 0.0, 0)
        except KeyError as e:
            raise SpecificationError('Bad packet parameters') from e

    ## Encode the current packet for serialisation
    #
    # From the parameters set in the packet, convert to a stream of bytes that can be used to serialise
    # the packet to an output stream.  Note that this returns only the contents of the packet; the
    # packet length, recognition ID, etc., must be added separately.
    #
    # \param self   Reference for the object
    # \return Bytes array with the binary representation of the packet-specific parameters
    def payload(self) -> bytes:
        config = json.dumps(self.config, separators=(',', ':')).encode('UTF-8')
        config_len = len(config)
        buffer = struct.pack(f'<I{config_len}s', config_len, config)
        return buffer

    ## Provide the recognition ID for the packet, as used in the binary file
    #
    # Each packet has a reference number that's used as an ID; this routine provides that number
    #
    # \param self   Reference for the object
    # \returns Integer identification number for the packet
    def id(self) -> int:
        return PacketTypes.SensorScales.value
    
    ## Provide the fixed-text string name for this data packet
    #
    # This simply reports the human-readable name for the class so that reporting is possible
    #
    # \param self   Reference for the object
    # \return String with th ename of the object
    def name(self) -> str:
        return 'SensorScales'
    
    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data packet for standard streaming output interface
    #
    # \param self   Reference for the object
    # \return String representation of the object
    def __str__(self) -> str:
        rtn = DataPacket.__str__(self) + f' {self.name()}: sensor scales =|{self.config}|'
        return rtn

## Implement a packet to hold IMU information from a WIBL logger
#
# The IMU on the standard WIBL logger is a 6-dof device, and therefore provides a 3-axis acceleration and 3-axis
# gyro rate estimate.  The particular device used also provides a die temperature estimate (needed to calibrate
# internally) which is also serialised.
class RawIMU(DataPacket):
    ## Initialise the packet using either a bytes buffer from a file, or keywords ab initio
    #
    # If the keywords include "buffer", the code assumes that the contents of the buffer are a serialised
    # version of the packet, and attempts to unpack it.  Otherwise, the code assumes that the keywords contain
    # information required to initialise the packet, and attempts to pull them from the dictionary.
    #
    # \param self   Reference for the object
    # \param kwargs Named arguments to initialise parameters, or "buffer" to unpack from binary data 
    def __init__(self, **kwargs):
        if 'buffer' in kwargs:
            self.buffer_constructor(kwargs['buffer'])
        else:
            self.data_constructor(**kwargs)
    
    ## Construct for a serialised buffer of bytes
    #
    # This attempts to construct the packet from a previously serialised version, typically from a WIBL
    # logger.  The serialisation assumes a length word followed by a serialised JSON dictionary as a
    # simple C-style string.
    #
    # \param self   Reference for the object
    # \param buffer Binary buffer with serialised information for the packet
    def buffer_constructor(self, buffer: bytes) -> None:
        (elapsed, t, gx, gy, gz, ax, ay, az) = struct.unpack('<Ihhhhhhh', buffer)
        self.accel = (ax, ay, az)
        self.gyro = (gx, gy, gz)
        self.temp = t
        super().__init__(0, 0.0, elapsed)

    ## Initialise the packet from keyword arguments
    #
    # This takes the keywords provided and attempts to initialise the packet.  For this packet, valid
    # keywords are:
    #   'accel': 3-tuple of int16s for accelerations (using appropriate scale factors)
    #   'gyro': 3-tuple of int16s for gyro rates (using appropriate scale factors)
    #   'temp': int16 for temperature (using appropriate scale factors)
    #   'elapsed_time': uint32 for elapsed time of the packet
    #
    # \param self       Reference for the object
    # \param **kwargs   Keyword dictionary with parameters for the packet
    def data_constructor(self, **kwargs) -> None:
        try:
            self.accel = kwargs['accel']
            self.gyro = kwargs['gyro']
            self.temp = kwargs['temp']
            super().__init__(0, 0.0, kwargs['elapsed_time'])
        except KeyError as e:
            raise SpecificationError('Bad packet parameters') from e

    ## Encode the current packet for serialisation
    #
    # From the parameters set in the packet, convert to a stream of bytes that can be used to serialise
    # the packet to an output stream.  Note that this returns only the contents of the packet; the
    # packet length, recognition ID, etc., must be added separately.
    #
    # \param self   Reference for the object
    # \return Bytes array with the binary representation of the packet-specific parameters
    def payload(self) -> bytes:
        buffer = struct.pack('<Ihhhhhhh', self.elapsed, self.temp, self.gyro[0], self.gyro[1], self.gyro[2], self.accel[0], self.accel[1], self.accel[2])
        return buffer

    ## Provide the recognition ID for the packet, as used in the binary file
    #
    # Each packet has a reference number that's used as an ID; this routine provides that number
    #
    # \param self   Reference for the object
    # \returns Integer identification number for the packet
    def id(self) -> int:
        return PacketTypes.RawIMU.value
    
    ## Provide the fixed-text string name for this data packet
    #
    # This simply reports the human-readable name for the class so that reporting is possible
    #
    # \param self   Reference for the object
    # \return String with th ename of the object
    def name(self) -> str:
        return 'RawIMU'
    
    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data packet for standard streaming output interface
    #
    # \param self   Reference for the object
    # \return String representation of the object
    def __str__(self) -> str:
        rtn = super().__str__() + f' {self.name()}: acc = {self.accel}, gyro = {self.gyro}, temp = {self.temp}'
        return rtn

## Implement a packet to store the configuration specification for a logger
#
# The WIBL logger can serialise a JSON-formatted dictionary containing all of the configuration parameters for
# the current setup of the logger.  This packet encapsulates that string so that it can be used to determine the
# configuration during processing, if required (or for general monitoring, etc.)
class Setup(DataPacket):
    ## Initialise the packet using either a bytes buffer from a file, or keywords ab initio
    #
    # If the keywords include "buffer", the code assumes that the contents of the buffer are a serialised
    # version of the packet, and attempts to unpack it.  Otherwise, the code assumes that the keywords contain
    # information required to initialise the packet, and attempts to pull them from the dictionary.
    #
    # \param self   Reference for the object
    # \param kwargs Named arguments to initialise parameters, or "buffer" to unpack from binary data 
    def __init__(self, **kwargs):
        if 'buffer' in kwargs:
            self.buffer_constructor(kwargs['buffer'])
        else:
            self.data_constructor(**kwargs)
    
    ## Construct for a serialised buffer of bytes
    #
    # This attempts to construct the packet from a previously serialised version, typically from a WIBL
    # logger.  The serialisation assumes a length word followed by a serialised JSON dictionary as a
    # simple C-style string.
    #
    # \param self   Reference for the object
    # \param buffer Binary buffer with serialised information for the packet
    def buffer_constructor(self, buffer: bytes) -> None:
        base = 0
        setup_len, = struct.unpack_from('<I', buffer, base)
        base += 4
        convert_string = f'<{setup_len}s'
        setup, = struct.unpack_from(convert_string, buffer, base)
        self.setup = json.loads(setup)
        super().__init__(0, 0.0, 0)

    ## Initialise the packet from keyword arguments
    #
    # This takes the keywords provided and attempts to initialise the packet.  The JSON-serialisable
    # dictionary must contain at least { 'version': { 'commandproc': 'M.m.p' }} to be recognised by
    # the logger, which is validated before the packet is constructed.
    # For this packet, valid keywords are:
    #   'setup':    Dict containing JSON-serialisable configuration information, or a bytes array or string
    #               containing JSON-serialised dictionary information that can be reconstructed.
    #
    # \param self       Reference for the object
    # \param **kwargs   Keyword dictionary with parameters for the packet
    def data_constructor(self, **kwargs) -> None:
        try:
            if type(kwargs['setup']) != 'Dict':
                if type(kwargs['setup']) == 'bytes':
                    self.setup = json.loads(kwargs['setup'].decode('UTF-8'))
                else:
                    self.setup = json.load(kwargs['setup'])
            else:
                self.setup = kwargs['setup']
            if 'version' not in self.setup or 'commandproc' not in self.setup['version']:
                raise SpecificationError('JSON specification does not contain version information.')
        except KeyError as e:
            raise SpecificationError('Bad packet parameters') from e

    ## Encode the current packet for serialisation
    #
    # From the parameters set in the packet, convert to a stream of bytes that can be used to serialise
    # the packet to an output stream.  Note that this returns only the contents of the packet; the
    # packet length, recognition ID, etc., must be added separately.
    #
    # \param self   Reference for the object
    # \return Bytes array with the binary representation of the packet-specific parameters
    def payload(self) -> bytes:
        stringified = json.dumps(self.setup).encode('UTF-8')
        stringified_len = len(stringified)
        buffer = struct.pack(f'<I{stringified_len}s', stringified_len, stringified)
        return buffer

    ## Provide the recognition ID for the packet, as used in the binary file
    #
    # Each packet has a reference number that's used as an ID; this routine provides that number
    #
    # \param self   Reference for the object
    # \returns Integer identification number for the packet
    def id(self) -> int:
        return PacketTypes.Setup.value
    
    ## Provide the fixed-text string name for this data packet
    #
    # This simply reports the human-readable name for the class so that reporting is possible
    #
    # \param self   Reference for the object
    # \return String with the name of the object
    def name(self) -> str:
        return 'Setup'
    
    ## Implement the printable interface for this class, allowing it to be streamed
    #
    # This converts to human-readable version of the data packet for standard streaming output interface
    #
    # \param self   Reference for the object
    # \return String representation of the object
    def __str__(self) -> str:
        rtn = super().__str__() + f' {self.name()}: json = |{self.setup}|'
        return rtn

## Translate packets out of the binary file, reconstituing as an appropriate class
#
# This provides the primary interface for the user to the binary data generated by the logger.  Calling the next_packet
# method pulls the next packet header, checks for type and size, and then reads the following byte sequence to the
# required length before translating to an instantiation of the appropriate class.  Unknown packets generate a warning.
class PacketFactory:
    ## Initialise the packet factory
    #
    # This simple copies the file reference information for the binary data, and resets EOF indicator.
    #
    # \param self   Pointer to the object
    # \param file   Open file object, which must be opened for binary reads
    def __init__(self, file):
        ## File reference from which to read packets
        self.file = file
        ## Flag for end-of-file detection
        self.end_of_file = False

    ## Extract the next packet from the binary data file
    #
    # This pulls the next packet header from the binary file, interprets the type and size, reads the bytes
    # corresponding to the packet payload, and the converts to an instantiation of the appropriate class object.
    #
    # \param self   Pointer to the object
    # \return DataPacket-derived object corresponding to the packet, or None if end-of-file or error
    def next_packet(self):
        if self.end_of_file:
            return None

        buffer = self.file.read(8)   # Header for each packet is U32 (ID) U32 (length in bytes)

        if len(buffer) < 8:
            self.end_of_file = True
            return None

        (pkt_id, pkt_len) = struct.unpack('<II', buffer)
        buffer = self.file.read(pkt_len)
        try:
            if pkt_id == PacketTypes.SerialiserVersion.value:
                rtn = SerialiserVersion(buffer=buffer)
            elif pkt_id == PacketTypes.SystemTime.value:
                rtn = SystemTime(buffer=buffer)
            elif pkt_id == PacketTypes.Attitude.value:
                rtn = Attitude(buffer=buffer)
            elif pkt_id == PacketTypes.Depth.value:
                rtn = Depth(buffer=buffer)
            elif pkt_id == PacketTypes.COG.value:
                rtn = COG(buffer=buffer)
            elif pkt_id == PacketTypes.GNSS.value:
                rtn = GNSS(buffer=buffer)
            elif pkt_id == PacketTypes.Environment.value:
                rtn = Environment(buffer=buffer)
            elif pkt_id == PacketTypes.Temperature.value:
                rtn = Temperature(buffer=buffer)
            elif pkt_id == PacketTypes.Humidity.value:
                rtn = Humidity(buffer=buffer)
            elif pkt_id == PacketTypes.Pressure.value:
                rtn = Pressure(buffer=buffer)
            elif pkt_id == PacketTypes.SerialString.value:
                rtn = SerialString(buffer=buffer)
            elif pkt_id == PacketTypes.Motion.value:
                rtn = Motion(buffer=buffer)
            elif pkt_id == PacketTypes.Metadata.value:
                rtn = Metadata(buffer=buffer)
            elif pkt_id == PacketTypes.AlgorithmRequest.value:
                rtn = AlgorithmRequest(buffer=buffer)
            elif pkt_id == PacketTypes.JSONMetadata.value:
                rtn = JSONMetadata(buffer=buffer)
            elif pkt_id == PacketTypes.NMEA0183Filter.value:
                rtn = NMEA0183Filter(buffer=buffer)
            elif pkt_id == PacketTypes.SensorScales.value:
                rtn = SensorScales(buffer=buffer)
            elif pkt_id == PacketTypes.RawIMU.value:
                rtn = RawIMU(buffer=buffer)
            elif pkt_id == PacketTypes.Setup.value:
                rtn = Setup(buffer=buffer)
            else:
                print(f'Unknown packet with ID {pkt_id} in input stream; ignored.')
                rtn = None
        except struct.error as e:
            raise PacketTranscriptionError(str(e))

        return rtn

    ## Check for more data being available
    #
    # This checks for whether there is more data available in the file.
    #
    # \param self   Pointer to the object
    # \return True if there is more data to read, otherwise False
    def has_more(self):
        return not self.end_of_file
