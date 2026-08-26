import io
import struct
from typing import Literal, Type

import wibl.core.logger_file.logger_file_ver_1_3 as _logger_file_ver_1_3
import wibl.core.logger_file.logger_file_ver_1_4 as _logger_file_ver_1_4

from wibl.core.logger_file.base import (
    PacketTranscriptionError,
    PacketTypes,
    DataPacket,
    LoggerFileBase, PacketFactoryBase
)


class LoggerFileIOError(Exception):
    ...

class UnknownLoggerFileVersion(Exception):
    ...


LOGGER_FILE_VERSIONS = Literal['1.3', '1.4']
DEFAULT_LOGGER_FILE_VERSION_MAJOR = 1
DEFAULT_LOGGER_FILE_VERSION_MINOR = 4

LOGGER_VERSIONS = {
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


def get_logger_file(version: LOGGER_FILE_VERSIONS = '1.4') -> LoggerFileBase:
    match version:
        case '1.4':
            return _logger_file_ver_1_4.LoggerFile()
        case '1.3':
            return _logger_file_ver_1_3.LoggerFile()
        case _:
            raise UnknownLoggerFileVersion(f"Unknown logger file version '{version}'")


def PacketFactory(file: io.FileIO | io.BufferedReader, *, # noqa: N802
                  strict_mode: bool = False) -> PacketFactoryBase:
    # Attempt to read WIBL serialiser version from ``file`` and return a PacketFactory
    # appropriate to that version. Raises ``LoggerFileIOError`` if unable to read
    # serialiser version or ``UnknownLoggerFileVersion`` if an unknown version was encountered.
    file.seek(0)
    buffer = file.read(12)
    if len(buffer) < 12:
        raise LoggerFileIOError(f"Unable to read serialiser version from file {file.name}: not enough bytes")
    try:
        (major, minor) = struct.unpack_from('<HH', buffer, 8)
    except Exception as e:
        raise LoggerFileIOError(f"Unable to read serialiser version from file {file.name}: error was: {str(e)}")
    file.seek(0)
    match (major, minor):
        case (1, 4):
            return _logger_file_ver_1_4.PacketFactory(file, strict_mode=strict_mode)
        case (1, 3):
            return _logger_file_ver_1_3.PacketFactory(file, strict_mode=strict_mode)
        case _:
            raise UnknownLoggerFileVersion(f"Discovered unknown serialiser version {major}.{minor} "
                                           f"from file {file.name}")
