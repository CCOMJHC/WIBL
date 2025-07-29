# wibl-python: Python tools for working with the WIBL low-cost data logger system

## Installation
You can run `wibl-python` either locally or in the cloud. For cloud instructions, see the "Packaging and Deploying 
Processing and Submission Code" section below.

For local installations there are currently two options: 
1. Python
2. Docker

The following subsections describe each installation method.

### Local installation using Python

#### Using Conda (Windows, Linux, macOS)
`wibl-python` is available as a [conda-forge package](https://anaconda.org/conda-forge/wibl-python) and can be used
on Windows, Linux, and macOS (without needing to download or clone the source code from GitHub). 

For Windows, it's probably best to install `wibl-python` using [Miniconda](https://docs.anaconda.com/free/miniconda/miniconda-install/) (Anaconda or Miniforge should also 
work). 

> Note: If you plan to run [WIBL data management scripts](scripts/data-management/README.md) to automate data processing
using `wibl-python`, make sure to follow the instructions in the [README](scripts/data-management/README.md) to
set up Miniconda using PowerShell 7 (which is required to run the data management scripts).

Linux and macOS users can also choose to use Conda, however it's not required as there are other ways to install 
the necessary dependencies in these environments (see below).

Once you've installed conda, the next step is to create a conda environment for `wibl-python`. To do so, open a 
conda shell (we recommend using PowerShell 7 so that you can easily use 
[WIBL data management scripts](scripts/data-management/README.md)) and do the following to create the `wibl` 
environment:
```
conda env create -n wibl
conda activate wibl
conda install wibl-python
```

> To update an existing environment, run `conda update -n wibl wibl-python`.

Then, each time you want to use `wibl-python` activate the environment as follows:
```
conda activate wibl
```

> Note: You can also install `wibl-python` in an existing conda environment by running `conda install wibl-python`.

Once activated, you should be able to run `wibl` commands:
```
(wibl-python) PS C:\> wibl --help
usage: wibl <command> [<arguments>]

    Commands include:
        datasim     Generate test data using Python-native data simulator.
        editwibl    Edit WIBL logger files, e.g., add platform metadata.
        uploadwibl  Upload WIBL logger files to an S3 bucket.
        parsewibl   Read and report contents of a WIBL file.
        dcdbupload  Upload a GeoJSON file to DCDB direct.
        procwibl    Local processing from WIBL file to GeoJSON.
        validate    Validate the metadata in a GeoJSON file.


Python tools for WIBL low-cost data logger system

positional arguments:
  command     Subcommand to run

options:
  -h, --help  show this help message and exit
  --version   print version and exit
(wibl-python) PS C:\>
```

#### Linux or macOS
To install `wibl-python` in a local Python environment, first install Python 3 for your operating system; version 
3.11 or greater is recommended, but 3.8 or later will work (though Python 3.8 will reach 
[end-of-life](https://devguide.python.org/versions/) status in October 2024).

Next, we'll need to install non-Python dependencies required by `wibl-python`. Currently, the only such dependency
is [GDAL](https://gdal.org/download.html). If you are using Linux, your distribution likely has a recent-enough
version of the GDAL that you can install via the package manager for that distribution (e.g., `apt` for Debian
or Ubuntu derivatives, `yum` or `dnf` for RedHat or CentOS derivatives). For macOS, you can use the version of 
GDAL provided by the [Homebrew](https://brew.sh) or [MacPorts](https://www.macports.org) package managers. 

Once you have installed Python 3, [create a virtual environment](https://docs.python.org/3/library/venv.html#creating-virtual-environments)
in which to install and run `wibl-python`. For example, on Linux or macOS
this would look like:
```shell
$ python3 -m venv wibl-env
```

> Note: If using a `miniconda` version of Python, see [here](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html)
> to learn how to create and activate a Python virtual environment.

Once created, each time you want to use `wibl-python` (or before you install `wibl-python`) you will need to activate 
the environment, which again on Linux or macOS would look like:
```shell
$ ./wibl-env/bin/activate
```

> Note: this assumes the current working directory of your shell is the same directory where `wibl-env` resides.

Once you've activated the `wibl-env` Python virtual environment, you can install `wibl-python` as follows:
```
pip install ./wibl-manager
pip install .
```

### Local installation using Docker
Please refer to the instructions [here](https://github.com/CCOMJHC/WIBL/blob/main/DataManagement/containers/README.md)
to learn how to install and use `wibl-python` and [data management scripts](scripts/data-management/README.md) via 
Docker.

## Testing
To run unit tests, including detailed verification of packet data output by the data simulator, run:
```
pip install -r requirements-build.txt
pytest -n 4 --cov=wibl --cov-branch --cov-report=xml --junitxml=test-results.xml tests/unit/*.py
```

To run integration tests exercising much of the functionality of the `wibl` command line tool 
(except for file upload to S3 and submission DCDB):
```
bash ./tests/integration/test_wibl.bash
```

## Usage
Once you've activated the `wibl-env` Python virtual environment where you installed `wibl-python`, you can run the
`wibl` command, which has several sub-commands that you can discover using the `--help` option:
```
$ wibl --help  
Usage: wibl [OPTIONS] COMMAND [ARGS]...

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  datasim     Write simulated WIBL data to FILENAME.
  dcdbupload  Upload GeoJSON files to DCDB for archival.
  editwibl    Edit INPUT WIBL logger file, writing edited WIBL file to...
  parsewibl   Parse binary WIBL logger file INPUT and report contents in...
  procwibl    Process a WIBL file INPUT into GeoJSON file OUTPUT locally.
  uploadwibl  Upload a WIBL file INPUT to an S3 bucket for processing.
  validate    Validate GeoJSON metadata stored in INPUT.

```

### Run WIBL data simulator
Run data simulator to generate test data and store it in a binary WIBL file:
```
$ wibl datasim -f test.bin -d 360 -s
```

For more information on simulator, use the `-h` option:
```
$ wibl datasim -h
usage: wibl datasim [-h] [-f FILENAME] [-d DURATION] [-s] [-b] [--use_buffer_constructor] [--duplicate_depth_prob DUPLICATE_DEPTH_PROB]
                    [--no_data_prob NO_DATA_PROB] [-v]

Command line user interface for the NMEA data simulator.

options:
  -h, --help            show this help message and exit
  -f, --filename FILENAME
                        Simulated data output filename
  -d, --duration DURATION
                        Duration (seconds) of the simulated data
  -s, --emit_serial     Write NMEA0183 simulated strings
  -b, --emit_binary     Write NMEA2000 simulated data packets
  --use_buffer_constructor
                        Use buffer constructor, rather than data constructor, for data packets. If not specified, data constructor will
                        be used.
  --duplicate_depth_prob DUPLICATE_DEPTH_PROB
                        Probability of generating duplicate depth values. Default: 0.0
  --no_data_prob NO_DATA_PROB
                        Probability of generating no-data values for system time, position, and depth packets. Default: 0.0
  -v, --verbose         Produce verbose output.
```

### Edit WIBL file
Add platform metadata to existing binary WIBL file (e.g., from data simulator or from a real datalogger):
```
$ wibl editwibl -m examples/ship-metadata-simple.json test.bin test-inject.bin
```

#### Note on metadata format
In versions of `wibl-python` previous to 1.1.0 (run `wibl --version` to find out what version you have), B-12 metadata 
elements embedded in WIBL files (whether included by a WIBL logger or added later using `editwibl`) were stored at the 
root, so:
```json
{
    "trustedNode": {
        "providerOrganizationName": "",
        "providerEmail": "",
        "uniqueVesselID": "",
        "providerLogger": "",
        "providerLoggerVersion": ""
    },
    "platform": {
        "length":   0,
        "IDType":   "",
        "IDNumber": "",
        "soundSpeedDocumented":     false,
        "postionOffsetsDocumented": false,
        "dataProcessed":            false
    }
}
```

However, this is not compatible with how metadata are handled by OpenVBI, which expects B-12 metadata 
that are to be included in GeoJSON representations to be nested in the "properties" object at the root 
of the GeoJSON object. Further, OpenVBI allows non-B-12 GeoJSON metadata (namely "crs") stored at the 
root of the GeoJSON object to be specified and copied into B-12 GeoJSON encoding. For example:
```json
{
    "crs": {
        "type": "name",
        "properties": {
          "name": "EPSG:4269"
        }
    },
    "properties": {
        "trustedNode": {
            "providerOrganizationName": "",
            "providerEmail": "",
            "uniqueVesselID": "",
            "providerLogger": "",
            "providerLoggerVersion": ""
        },
        "platform": {
            "length": 0,
            "IDType": "",
            "IDNumber": "",
            "soundSpeedDocumented": false,
            "postionOffsetsDocumented": false,
            "dataProcessed": false
        }
    }
}
```

> Note: The `"crs"` object in the above metadata example is optional. If not supplied, the GeoJSON default
> CRS of EPSG:4326 (WGS84) will be used.

Starting with `wibl-python` 1.1.0, the OpenVBI-compatible format must be used; using the old `wibl-python` 1.0.4
format will result in the creation of GeoJSON files that are not valid. See 
[convert-md-openvbi.py](scripts/convert-md-openvbi.py) to perform automated conversion of existing metadata
JSON templates into the new format, for example:
```shell
$ python3 scripts/convert-md-openvbi.py --help
usage: convert-md-openvbi.py [-h] input_dir output_dir

Convert JSON files in a directory to OpenVBI B-12 metadata format

positional arguments:
  input_dir   Input directory containing B-12 JSON metadata in WIBL 1.0.4 format
  output_dir  Name of directory to write B-12 JSON metadata in OpenVBI/WIBL 1.1.0 format. If directory does not exist it will be created.

options:
  -h, --help  show this help message and exit
```

Assuming you have B-12 metadata JSON files to be converted in a directory called 'my_metadata' in the current 
directory and want to store converted files in a directory called 'my_new_metadata':
```shell
$ python3 scripts/convert-md-openvbi.py my_metadata my_new_metadata
```

### Process WIBL file into GeoJSON
Convert a binary WIBL file into GeoJSON:
```
$ wibl procwibl -c tests/data/configure.local.json test-inject.bin test-inject.geojson
```

> Note: It is necessary to supply a configuration JSON file with the `local` attribute
> set to `true`, such as `tests/data/configure.local.json`, because `procwibl` uses
> the same code as the conversion processing lambda code run in the cloud.

### Upload WIBL files into AWS S3 Buckets for processing
Instead of using the mobile app (and for testing), WIBL binary files can be uploaded into a given S3 bucket to trigger processing.  If the file is being uploaded into the staging bucket (i.e., to test transfer to DCDB), a '.json' extension must be added (``-j|--json``), and the SourceID tag must be set (``-s|--source``) so that the submission Lambda can find this information.
```
$ wibl uploadwibl -h
usage: wibl uploadwibl [-h] [-b BUCKET] [-j] [-s SOURCE] input

Upload WIBL logger files to an S3 bucket (in a limited capacity)

positional arguments:
  input                 WIBL format input file

options:
  -h, --help            show this help message and exit
  -b BUCKET, --bucket BUCKET
                        Set the upload bucket name (string)
  -j, --json            Add .json extension to UUID for upload key
  -s SOURCE, --source SOURCE
                        Set SourceID tag for the S3 object (string)
```

### Parse WIBL binary files
Raw WIBL binary files can be read and transcribed in ASCII format for debug.  Statistics on which NMEA2000 talkers, and which packets, are observed can be dumped at the end of the read (``-s|--stats``).
```
$ wibl parsewibl -h
usage: wibl parsewibl [-h] [-s] input

Parse WIBL logger files locally and report contents.

positional arguments:
  input        Specify the file to parse

options:
  -h, --help   show this help message and exit
  -s, --stats  Provide summary statistics on packets seen
```

### Uploading GeoJSON files to DCDB directly
Instead of using the cloud-based submission process (and for debugging), pre-formatted GeoJSON files can be uploaded directly to DCDB for archival.  Note that the file containing the provider authorisation token (provided by DCDB for each Trusted Node) has to be set on the command line (``-a|--auth``), although the rest of the information (provider ID, upload point) can be specified through the JSON configuration file (``-c|--config``); the provider ID (specified by DCDB for each Trusted Node) can be over-ridden on the command line (``-p|--provider``).  The source ID is read from the GeoJSON file, unless it is set on the command line (``-s|--source``).

```
wibl dcdbupload -h
usage: wibl dcdbupload [-h] [-s SOURCEID] [-p PROVIDER] [-a AUTH] [-c CONFIG] input

Upload GeoJSON files to DCDB for archival.

positional arguments:
  input                 GeoJSON file to upload to DCDB

optional arguments:
  -h, --help            show this help message and exit
  -s SOURCEID, --sourceid SOURCEID
                        Set SourceID as in the GeoJSON metadata.
  -p PROVIDER, --provider PROVIDER
                        Provider ID as generated by DCDB
  -a AUTH, --auth AUTH  File containing the Provider authorisation token generated by DCDB
  -c CONFIG, --config CONFIG
                        Specify configuration file for installation
```

Configuration files suitable for uploading to both the test and production DCDB endpoints are available in the
[examples](examples) directory; For test uploads, use [configure-submission-test.json](examples/configure-submission-test.json),
and for production uploads use [configure-submission.json](examples/configure-submission.json).

## Batch processing scripts
In addition to running the above-documented `wibl` commands on individual WIBL files, it is also possible to batch 
process many WIBL files using the provided [data management PowerShell scripts](scripts/data-management/README.md). 
These scripts can also be run in [Docker](https://www.docker.com/) (or other container runtimes) using the 
[wibl-base container image](https://github.com/CCOMJHC/WIBL/blob/main/DataManagement/containers/README.md).

## Packaging and Deploying Processing and Submission Code
Packaging up the software for the cloud segment, and deploying it, can be a little involved due to security concerns with the various cloud providers.  Detailed setup instructions, and automation scripts, are provided as described below.

### AWS
There are a number of steps required to set up the AWS Lambdas, the S3 buckets, and associated triggers and permissions in order to make processing work in the cloud.  The steps are covered in detail in the [Setup Instructions](scripts/cloud/AWS/README.md), and a corresponding set of scripts are available in the [scripts](scripts/cloud/AWS) directory in the repository.  These scripts should *mostly* work, but will likely need some modification for a local configuration before being fully executable.  Consider the `configuration-parameters.sh` file first for this.

## Configuration for Local Use
The ``wibl`` tool can be installed locally as above, but needs a configuration JSON file for some of the sub-commands (e.g., to send data to DCDB) rather than using environment variables as with the cloud-based processing.  Scripts in `wibl-python/scripts/desktop` will generate the `configure/json` required (configure `configuration-parameters.sh` and then run `configure-desktop.sh`).
