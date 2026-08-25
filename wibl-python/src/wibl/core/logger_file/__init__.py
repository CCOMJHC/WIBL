from typing import Literal, Type

import wibl.core.logger_file.logger_file_ver_1_3 as _logger_file_ver_1_3
import wibl.core.logger_file.logger_file_ver_1_4 as _logger_file_ver_1_4

from wibl.core.logger_file.base import (
    PacketTranscriptionError,
    PacketTypes,
    DataPacket,
    LoggerFileBase
)


class UnknownLoggerFileVersion(Exception):
    ...


LOGGER_FILE_VERSIONS = Literal['1.3', '1.4']
DEFAULT_LOGGER_FILE_VERSION_MAJOR = 1
DEFAULT_LOGGER_FILE_VERSION_MINOR = 4


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
    if version == '1.4':
        return _logger_file_ver_1_4.LoggerFile()
    elif version == '1.3':
        return _logger_file_ver_1_3.LoggerFile()
    else:
        raise UnknownLoggerFileVersion(f"Unknown logger file version '{version}'")
