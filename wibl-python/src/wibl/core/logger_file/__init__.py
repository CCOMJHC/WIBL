import io
import struct
from typing import Literal

import wibl.core.logger_file.logger_file_ver_1_3 as _logger_file_ver_1_3
import wibl.core.logger_file.logger_file_ver_1_4 as _logger_file_ver_1_4
import wibl.core.logger_file.logger_file_ver_1_5 as _logger_file_ver_1_5

# Note that DataPacket and PacketTranscriptionError are used transitively when
# importing this (wibl.core.logger_file) from other code, rather than directly here.
from wibl.core.logger_file.base import (
    DataPacket,
    PacketTranscriptionError,
    PacketTypes,
    LoggerFileBase, PacketFactoryBase
)


class LoggerFileIOError(Exception):
    ...

class UnknownLoggerFileVersion(Exception):
    ...


LOGGER_FILE_VERSIONS = Literal['1.3', '1.4', '1.5']
DEFAULT_LOGGER_FILE_VERSION_MAJOR = 1
DEFAULT_LOGGER_FILE_VERSION_MINOR = 5

LOGGER_VERSIONS = {
    '1.5': {
        'n2000': (1, 2, 0),
        'n0183': (1, 1, 0),
        'imu': (1, 0, 0),
        'gnss': (1, 0, 0)
    },
    '1.4': {
        'n2000': (1, 2, 0),
        'n0183': (1, 1, 0),
        'imu': (1, 0, 0)
    },
    '1.3': {
        'n2000': (1, 1, 0),
        'n0183': (1, 0, 1),
        'imu': (1, 0, 0)
    }
}


def get_major_minor_version(version: LOGGER_FILE_VERSIONS) -> tuple[int, int]:
    vals = version.split('.')
    if len(vals) != 2:
        raise ValueError(f"Unable to get major, minor version from '{version}'")
    try:
        major = int(vals[0])
    except ValueError:
        raise ValueError(f"Invalid major version {vals[0]} from '{version}'")
    try:
        minor = int(vals[1])
    except ValueError:
        raise ValueError(f"Invalid minor version {vals[1]} from '{version}'")
    return major, minor


## Obtain a LoggerFile instance for use when writing and reading WIBL data
#
# Obtain a LoggerFile instance of a particular serialiser version for use when writing and reading WIBL data.
# A LoggerFile instance encapsulates a PacketFactory for a particular serialiser version, which can be used
# for instantiating data packets specific to that version.
#
# Those only needing to read a particular WIBL file can use ``PacketFactory()``, which will return a
# PacketFactory instance for the serialiser version of that file.
#
# \param version    A string literal representing the serialiser version.
def get_logger_file(version: LOGGER_FILE_VERSIONS = '1.5') -> LoggerFileBase:
    match version:
        case '1.5':
            return _logger_file_ver_1_5.LoggerFile()
        case '1.4':
            return _logger_file_ver_1_4.LoggerFile()
        case '1.3':
            return _logger_file_ver_1_3.LoggerFile()
        case _:
            raise UnknownLoggerFileVersion(f"Unknown logger file version '{version}'")


## Obtain a PacketFactory instance for use when reading a particular WIBL file
#
# Obtain a PacketFactory instance of a pariticular serialiser version for use when reading a particular
# WIBL file.
#
# Those wishing to write WIBL data, without first reading, are advised to obtain a version-specific
# LoggerFile instance using ``get_logger_file()``.
#
# \param file           Open binary file-like object for which a PacketFactory instance is to be obtained
# \param strict_mode    Strict mode: fail if any packet is not successfully translated
def PacketFactory(file: io.FileIO | io.BufferedReader, *, # noqa: N802
                  strict_mode: bool = False) -> PacketFactoryBase:
    # Attempt to read WIBL serialiser version from ``file`` and return a PacketFactory
    # appropriate to that version. Raises ``LoggerFileIOError`` if unable to read
    # serialiser version or ``UnknownLoggerFileVersion`` if an unknown version was encountered.
    file.seek(0)
    # Read partial SerialiserVersion packet (which canonically will be the first packet in a WIBL file).
    # We only need to read the packet ID, packet length (which are stored as two uint32 little-endian values)
    # as well as the serializer major and minor versions (which are stored as two uint16 little-endian values),
    # so we need only read the first twelve bytes...
    buffer = file.read(12)
    if len(buffer) < 12:
        raise LoggerFileIOError(f"Unable to read serialiser version from file {file.name}: not enough bytes")
    try:
        (pkt_id, pkt_len, major, minor) = struct.unpack_from('<IIHH', buffer)
        if pkt_id != PacketTypes.SerialiserVersion.value:
            raise LoggerFileIOError(f"Expected first packet in file {file.name} to be of type SerialiserVersion, "
                                    f"but it apparently was not; packet ID was {pkt_id}.")
        if pkt_len < 4:
            raise LoggerFileIOError(f"Expected length of first packet in file {file.name} to be greater than four, "
                                    f"but it was {pkt_len}.")
    except Exception as e:
        raise LoggerFileIOError(f"Unable to read serialiser version from file {file.name}: error was: {str(e)}")
    # Reset file descriptor position so that reads by the packet factory can proceed as normal.
    file.seek(0)
    match (major, minor):
        case (1, 5):
            return _logger_file_ver_1_5.PacketFactory(file, strict_mode=strict_mode)
        case (1, 4):
            return _logger_file_ver_1_4.PacketFactory(file, strict_mode=strict_mode)
        case (1, 3):
            return _logger_file_ver_1_3.PacketFactory(file, strict_mode=strict_mode)
        case _:
            raise UnknownLoggerFileVersion(f"Discovered unknown serialiser version {major}.{minor} "
                                           f"from file {file.name}")
