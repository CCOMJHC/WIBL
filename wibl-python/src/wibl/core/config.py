## \file config.py
# \brief Handle configuration files
#
# The cloud processing code needs a number of external parameters to work out where to find the data,
# where to store intermediate files, and so on.  These are summarised in a JSON configuration file that
# should be installed in the same directory as the serverless handler.  The code here handles reading
# this configuration into a dictionary, and then doing any preliminary processing required to get the
# configuration ready for use (e.g., converting strings to actual values, pre-computing values from
# raw inputs, etc.).
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
import os
from pathlib import Path
from typing import Union
import json
from typing import Dict, Any

from wibl import get_default_file

RSRC_KEY = 'wibl'
DEFAULT_CONFIG_FILE_ENV_KEY = 'WIBL_CONFIG_FILE'

## Read a JSON-format configuration file for the algorithm
#
# In order to allow the user to specify arbitrary configuration parameters, the configuration file
# is a simple JSON structure that can contain any key-value pairs.  Although most of these are
# specific to the algorithm being run, there are a few that control the algorithm:
#   elapsed_time_width  Width (bits) of the elapsed time data in the WIBL file (usu. 32)
#   verbose             Boolean for verbose reporting of processing (usu. False)
#   local               Boolean for local testing (usu. False for cloud deployment)
#   fault_limit         Limit on number of fault messages that are reported before starting to summarise
#
# \param config_file
# \return JSON-file converted into a dictionary (per JSON library)


class BadConfiguration(Exception):
    pass


def get_config_resource_filename(resource_rel_path: str) -> str:
    """
    Get name of default configuration file packaged with wibl.
    :param resource_rel_path: String representing path of resource file relative to ``wibl.defaults``.
    :return:
    """
    return str(get_default_file(resource_rel_path))


def get_config_path(default_config_file: str, env_key: str = DEFAULT_CONFIG_FILE_ENV_KEY) -> Path:
    """
    Get configuration file as a Path instance, guaranteeing that the file exists.
    Will attempt to first use the configuration file specified by the environment variable `env_key`, if this is not
    set in the environment, then the file denoted by `default_config_file` will be used instead.
    :param default_config_file: name of file to use if config file environment variable is not defined.
    :param env_key: name of the environment variable that optionally indicates the config file path to use.
    :return: configuration file as a Path instance, guaranteeing that the file exists.
    """
    config_file_name: str = os.getenv(env_key, default_config_file)
    if not os.path.exists(config_file_name):
        raise BadConfiguration(f"Config file {config_file_name} does not exist.")
    return Path(config_file_name)


def get_config_file(resource_name, env_key: str = DEFAULT_CONFIG_FILE_ENV_KEY) -> Path:
    """
    Convenience function combining get_config_resource_filename() and get_config_path().
    :param resource_name:
    :param env_key:
    :return:
    """
    return get_config_path(get_config_resource_filename(resource_name), env_key)


def read_config(config_file: Union[Path, str] = None) -> Dict[str, Any]:
    """There are a number of configuration parameters for the algorithm, such as the provider ID name
       to write into the metadata, and use for filenames; where to stage the intermediate GeoJSON files
       before they're uploaded to the database; and where to send the files.  There are also parameters
       to control the local algorithm, including:
    
            elapsed_time_width:     Width (bits) of the elapsed time data in the WIBL file (default: 32)
            verbose:                Boolean for verbose reporting of processing (usu. False)
            local:                  Boolean for local testing (usu. False for cloud deployment)
            fault_limit             Limit on number of fault messages that are reported before starting to summarise
       
       This code reads the JSON file with these parameters, and does appropriate translations to them so
       that the rest of the code can just read from the resulting dictionary.
    """
    try:
        with open(config_file) as f:
            config = json.load(f)
        
        # We need to tell the timestamping code what the roll-over size is for the elapsed times
        # stored in the WIBL file.  This allows it to determine when to add a day to the count
        # so that we don't wrap the interpolation.
        if 'elapsed_time_width' in config:
            config['elapsed_time_quantum'] = 1 << config['elapsed_time_width']
        else:
            config['elapsed_time_quantum'] = 1 << 32

        return config

    except Exception as e:
        raise BadConfiguration(e)
