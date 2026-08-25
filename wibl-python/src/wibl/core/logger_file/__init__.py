from typing import Literal

from wibl.core.logger_file import (
    base,
    logger_file_ver_1_3 as _logger_file_ver_1_3,
    logger_file_ver_1_4 as _logger_file_ver_1_4
)


class UnknownLoggerFileVersion(Exception):
    ...


def get_logger_file(version: Literal['1.3', '1.4'] = '1.4') -> base.LoggerFileT:
    if version == '1.4':
        return _logger_file_ver_1_4.LoggerFile()
    elif version == '1.3':
        return _logger_file_ver_1_3.LoggerFile()
    else:
        raise UnknownLoggerFileVersion(f"Unknown logger file version '{version}'")
