import os
import sys
from importlib import resources
from typing import Optional, TextIO
from pathlib import Path
from datetime import datetime
from random import randrange
import argparse
import logging

__version__ = '1.0.3'


LOGGER_NAME: str = 'wibl-python'

_logger: logging.Logger = logging.getLogger(LOGGER_NAME)


def get_logfile_name(prefix: str = 'wibl-python-', suffix: str = 'log') -> str:
    date_portion = datetime.utcnow().strftime("%Y-%m-%dT%H_%M_%S.%fZ")
    rand_portion = f"{randrange(1, 10000):05}"
    return f"{prefix}{date_portion}-{rand_portion}.{suffix}"


def get_logging_stream(stream_name: str) -> TextIO:
    if stream_name.capitalize() == 'STDERR':
        return sys.stderr
    return sys.stdout


def get_logger() -> logging.Logger:
    """
    Get instance of logger. Most modules that need to use logging should use
    this method rather than ``config_logger`` or ``config_logger_cmdline``.
    This is safe to call before the logger has been configured (i.e., at the
    top level of a module that needs logging). However, messages sent to the
    logger before configuration will be lost.
    :return:
    """
    return _logger


def config_logger(*,
                  level: int = logging.INFO,
                  filename: Optional[Path] = None,
                  stream: Optional[TextIO] = None) -> logging.Logger:
    """
    Configure global logger instance and return it.
    Note: This method should only be called once, usually at the entry point
        of a program.
    :param level:
    :param filename:
    :param stream:
    :return:
    """
    if filename is None and stream is None:
        raise ValueError(
            'Unable to configure log with both filename and stream set to'
            ' None; at least one must be set.')

    _logger.setLevel(level)

    log_format = os.environ.get('WIBL_PYTHON_LOG_FORMAT',
                                "%(asctime)s %(levelname)s %(name)s:%(filename)s:%(lineno)d: %(message)s")
    formatter = logging.Formatter(log_format)

    if filename is not None:
        fh = logging.FileHandler(filename)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        _logger.addHandler(fh)

    if stream is not None:
        sh = logging.StreamHandler(stream=stream)
        sh.setLevel(level)
        sh.setFormatter(formatter)
        _logger.addHandler(sh)

    return _logger


def config_logger_cmdline(args: argparse.Namespace, *,
                          log_prefix: str = None) -> logging.Logger:
    """
    Configure global logger instance and return it. For use by
    command line tools.
    Note: This method, which calls ``config_logger``, should only be called
    once, usually at the entry point of a program.
    :param args: ``argparse.Namespace`` object that defines the following
        properties: log: str, debug: bool, verbose: bool
    :param log_prefix: Prefix argument to be sent to ``get_logfile_name``.
    :return:
    """
    log_stream = None
    if args.log is None:
        logfile_name_args = {}
        if log_prefix:
            logfile_name_args['prefix'] = log_prefix
        log_filename = Path(args.outpath, get_logfile_name(**logfile_name_args))
    else:
        log_filename = Path(args.log)
    if args.debug:
        log_stream = sys.stderr
    if args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    return config_logger(level=log_level,
                         filename=log_filename,
                         stream=log_stream)


def config_logger_service(*,
                          debug: bool = False) -> logging.Logger:
    """
    Configure global logger instance and return it. For use by
    network services such as AWS lambdas, or by unit tests. This only
    configures a handler for ``sys.stdout``.
    Note: This method, which calls ``config_logger``, should only be called
    once, usually at the entry point of a program.
    :param debug: If ``True`` set logging level to DEBUG, else INFO.
    :return:
    """
    log_stream = sys.stdout
    if debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    return config_logger(level=log_level,
                         stream=log_stream)


def get_default_file(default_file_rel_path: str) -> Path:
    """
    Get path of resource file stored in ``wibl.defaults`` module from its location
    in the current installation of wibl-python.
    :param default_file_rel_path:
    :return:
    """
    if sys.version_info[0] == 3 and sys.version_info[1] < 9:
        # Python version is less than 3.9, so use older method of resolving resource files
        path_elems = default_file_rel_path.split('/')
        fname = path_elems[-1]
        sub_mod = '.'.join(path_elems[:-1])
        with resources.path(f"wibl.defaults.{sub_mod}", fname) as schema_file:
            return schema_file
    else:
        # Python version is >= 3.9, so use newer, non-deprecated resource resolution method
        return Path(str(resources.files('wibl').joinpath(f"defaults/{default_file_rel_path}")))
