from abc import ABC
from typing import BinaryIO
import io

from wibl.core.logger_file import DataPacket, Metadata, SerialiserVersion

# Major version number for the serialiser
SERIALISER_VERSION_MAJOR = 1
# Minor version number for the serialiser
SERIALISER_VERSION_MINOR = 0
# NMEA2000 version
SERIALISER_VERSION_NMEA2000 = (1, 0, 0)
# NMEA0183 version
SERIALISER_VERSION_NMEA0183 = (1, 0, 0)


class Writer(ABC):
    def __init__(self, logger_name: str, logger_id: str):
        # Write serialiser version to underlying data stream
        version: DataPacket = SerialiserVersion(major=SERIALISER_VERSION_MAJOR,
                                                minor=SERIALISER_VERSION_MINOR,
                                                n2000=SERIALISER_VERSION_NMEA2000,
                                                n0183=SERIALISER_VERSION_NMEA0183)
        self.record(version)
        # Write metadata to underlying data stream
        meta: DataPacket = Metadata(logger=logger_name,
                                    uniqid=logger_id)
        self.record(meta)

    def record(self, data: DataPacket):
        """
        Write a packet into the underlying data stream
        :param data:
        :return:
        """
        pass


class FileWriter(Writer):
    def __init__(self, filename: str, logger_name: str, logger_id: str):
        # Keep the filename for logging purposes
        self.filename: str = filename
        self._file: BinaryIO = open(filename, 'wb')
        # Current output log file on the SD card
        self._m_output_log: io.BufferedWriter = io.BufferedWriter(self._file)
        # Call super-class constructor to write metadata to underlying stream
        super().__init__(logger_name, logger_id)

    def __del__(self):
        self._m_output_log.close()
        self._file.close()

    def record(self, data: DataPacket):
        """
        Write a packet into the current log file
        :param data: Data packet to be written
        :return:
        """
        data.serialise(self._m_output_log)


class MemoryWriter(Writer):
    def __init__(self, logger_name: str, logger_id: str):
        self.bio = io.BytesIO()
        self.writer = io.BufferedWriter(self.bio)
        # Call super-class constructor to write metadata to underlying stream
        super().__init__(logger_name, logger_id)

    def __del__(self):
        self.writer.close()
        self.bio.close()

    def record(self, data: DataPacket):
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
