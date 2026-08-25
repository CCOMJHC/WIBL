##\file writer.py
# \brief IO support for Python-based data simulator.
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

from abc import ABC
from typing import BinaryIO
import io

import wibl.core.logger_file as lf


# NMEA2000 version
SERIALISER_VERSION_NMEA2000 = (1, 0, 0)
# NMEA0183 version
SERIALISER_VERSION_NMEA0183 = (1, 0, 0)
# IMU version
SERIALISER_VERSION_IMU = (1, 0, 0)


class Writer(ABC):
    def __init__(self, logger_name: str, shipname: str, *,
                 logger_file_version: lf.LOGGER_FILE_VERSIONS = '1.4'):
        major, minor = lf.get_major_minor_version(logger_file_version)
        self._lf = self._lf = lf.get_logger_file(logger_file_version)
        self._pf = self._lf.packet_factory
        # Write serialiser version to underlying data stream
        version: lf.DataPacket = self._pf.SerialiserVersion(major=major,
                                                            minor=minor,
                                                            n2000=SERIALISER_VERSION_NMEA2000,
                                                            n0183=SERIALISER_VERSION_NMEA0183,
                                                            imu=SERIALISER_VERSION_IMU)
        self.record(version)
        # Write metadata to underlying data stream
        meta: lf.DataPacket = self._pf.Metadata(logger=logger_name,
                                                shipname=shipname)
        self.record(meta)

    def record(self, data: lf.DataPacket):
        """
        Write a packet into the underlying data stream
        :param data:
        :return:
        """
        pass


class FileWriter(Writer):
    def __init__(self, filename: str, logger_name: str, shipname: str, *,
                 logger_file_version: lf.LOGGER_FILE_VERSIONS = '1.4'):
        # Keep the filename for logging purposes
        self.filename: str = filename
        self._file: BinaryIO = open(filename, 'wb')
        # Current output log file on the SD card
        self._m_output_log: io.BufferedWriter = io.BufferedWriter(self._file)
        # Call super-class constructor to write metadata to underlying stream
        super().__init__(logger_name, shipname, logger_file_version=logger_file_version)

    def __del__(self):
        self._m_output_log.close()
        self._file.close()

    def record(self, data: lf.DataPacket):
        """
        Write a packet into the current log file
        :param data: Data packet to be written
        :return:
        """
        data.serialise(self._m_output_log)


class MemoryWriter(Writer):
    def __init__(self, logger_name: str, shipname: str, *,
                 logger_file_version: lf.LOGGER_FILE_VERSIONS = '1.4'):
        self.bio = io.BytesIO()
        self.writer = io.BufferedWriter(self.bio)
        # Call super-class constructor to write metadata to underlying stream
        super().__init__(logger_name, shipname, logger_file_version=logger_file_version)

    def __del__(self):
        self.writer.close()
        self.bio.close()

    def record(self, data: lf.DataPacket):
        """
        Write a packet into the underlying byte array
        :param data: Data packet to be written
        :return:
        """
        data.serialise(self.writer)

    def getvalue(self) -> bytes:
        """
        Get contents of the underlying ByteIO byffer
        :return:
        """
        self.writer.flush()
        return self.bio.getvalue()
