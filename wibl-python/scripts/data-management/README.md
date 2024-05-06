# WIBL data management scripts 
This directory contains 
[PowerShell](https://learn.microsoft.com/en-us/powershell/scripting/overview?view=powershell-7.3)
scripts that can be used to automate WIBL data management tasks.

These scripts require PowerShell 7 or later running on Windows, macOS, or Linux. 
See [here](https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell?view=powershell-7.3)
for installation instructions. After installing PowerShell 7, make sure to run `conda init` from within PowerShell 7
to enable use of conda and the `wibl-python` environment. To do so on Windows, run:
```powershell
PS C:\Users\janeuser> C:\ProgramData\miniconda\Scripts\conda.exe init
```

> If you installed `conda` in your User directory, run `C:\Users\janeuser\miniconda3\Scripts\conda.exe init` instead.

To do so on Linux or macOS, run:
```shell
PS /Users/janeuser> ./miniconda/bin/conda init powershell
```

## convertToWibl.ps1: converting non-WIBL data to WIBL format using [LogConvert](../../../LogConvert)
It is possible to use wibl-python to process non-WIBL data in the following formats: Yacht Devices YDVR-4,
TeamSurv "tab separated" (but actually plain ASCII) NMEA0183 strings. To do so, it's first necessary to
convert these data to WIBL format using the [LogConvert](../../../LogConvert) utility bundled with WIBL.

LogConvert is written in C++ and so must be compiled into an executable for your operating system and 
processor architecture. Once you have an executable, you can run LogConvert manually for each file 
needing conversion. However, if you have many files to convert, you can automate this conversion using
[convertToWibl.ps1](convertToWibl.ps1). 

> Note: If your data are already in WIBL format, you don't need to run `LogConvert` or `convertToWibl.ps1`. 

To run `convertToWibl.ps1` you'll first need to be in a Python virtual environment running within PowerShell 7 
that has [wibl-python](../../README.md) installed. When running `convertToWibl.ps1` you must supply at least two 
inputs: 
1. A zip file containing YDVR or TeamSurv files (all files in the zip file must be of the same 
format); and
2. The name of the folder to write converted WIBL files to (this folder will have the same 
structure as the source zip folder). 

In addition to those required parameters, you'll probably also have to specify the location of your LogConvert 
executable (the default is a file named 'logconvert.exe' in a sub-directory called 'logconvert') using 
the `-LogConvertPath` option. If the files to be converted are of YDVR format, you won't need to supply any 
other command line options, however, if the files are of TeamSurv format, you'll also need to use the 
`-Format TeamSurv` option.

To learn more about how to run `convertToWibl.ps1`, use the `Get-Help` command:
```
PS /Users/janeuser/wibl/wibl-python/scripts/data-management> Get-Help ./convertToWibl.ps1

NAME
    convertToWibl.ps1
    
SYNOPSIS
    Convert YDVR or TeamSurv logger files to WIBL files.
    
SYNTAX
    convertToWibl.ps1 [-Source] <String> [-OutputFolder] <String> 
        [-LogConvertPath <String>] [-Format <String>] [<CommonParameters>]
    
DESCRIPTION
    This script converts YDVR or TeamSurv logger files in a .zip file to .WIBL files in a directory that
    matches the source .zip.

RELATED LINKS

REMARKS
    To see the examples, type: "Get-Help convertToWibl.ps1 -Examples"
    For more information, type: "Get-Help convertToWibl.ps1 -Detailed"
    For technical information, type: "Get-Help convertToWibl.ps1 -Full"
```

## processWibl.ps1: Processing raw WIBL data into IHO B12 GeoJSON data
Processing raw WIBL data into IHO B12 involves two steps: 1. editing the WIBL file to include metadata; and 2. processing 
WIBL data (now with metadata) into GeoJSON data. Each of these steps can be performed separately for individual WIBL 
files using the `wibl editwibl` and `wibl procwibl` commands. To automate the running of the `editwibl` and `procwibl` 
steps for many files, use [processWibl.ps1](processWibl.ps1).

To run `processWibl.ps1` you have to supply three inputs: 
1. The path to a directory containing WIBL files for a single
vessel; 
2. A path to a JSON file containing metadata for the vessel that collected the data 
(for example, see: [b12_v3_metadata_example.json](../../tests/fixtures/b12_v3_metadata_example.json)); and 
3. A JSON configuration file for local processing (for example, see: 
[configure.local.json](../../tests/fixtures/configure.local.json)). 

The configuration file should look like the following:
```json
{
	"verbose":				true,
	"elapsed_time_width":	32,
	"fault_limit":			10,
	"local":				true,
	"provider_id": 	"SEAID",
	"management_url": ""
}
```

The only thing you'll definitely have to change in your config file is the value of the `provider_id` key, which 
should be set to the provider ID of the trusted node you plan to use to submit data to DCDB.

> Note: if your data originally came from YDVR file, make sure to set `elapsed_time_width` to 16. If you
> don't set this correctly, the WIBL processing tools won't be able to detect when the elapsed time timestamp
> wraps around.

To learn more about how to run `convertToWibl.ps1`, use the `Get-Help` command:
```
PS /Users/janeuser/wibl/wibl-python/scripts/data-management> Get-Help ./processWibl.ps1  
processWibl.ps1 [[-wiblPath] <string>] [[-metadataFile] <string>] [[-wiblConfig] <string>]
```

## validateWibl.ps1: Validate IHO B12 GeoJSON data using csbschema
Once you have converted raw WIBL data into IHO B12 GeoJSON data with vessel metadata, we strongly recommend that
you validate these GeoJSON files. This way, you can catch errors in the metadata or data before attempting to submit 
them to the DCDB. This can be done by hand for individual files using [csbschema](https://github.com/CCOMJHC/csbschema).
`csbschema` is a separate project from WIBL/wibl-python that is installed as a dependency of wibl-python. However, if
you have many files to process, this can be automated using [validateWibl.ps1](validateWibl.ps1).

To run `validateWibl.ps1` you have to provide at least one input: The path to a directory containing GeoJSON files to
validate. Optionally, you can specify the file extension of GeoJSON files to validate using the `-extension` option
(the default is `json`). Lastly, `validateWibl.ps1` allows you to specify the schema version to validate the
GeoJSON against. The schema versions are described in the 
[csbschema documentation](https://github.com/CCOMJHC/csbschema#usage), and are defined 
[here](https://github.com/CCOMJHC/csbschema/blob/main/csbschema/__init__.py#L9). The default schema is currently
"3.1.0-2023-08", other valid current schemas include: "3.0.0-2023-08", "XYZ-3.1.0-2023-08", "XYZ-3.0.0-2023-08". 
You can find examples of IHO and NOAA B12 JSON encodings in the 
[csbschema repository](https://github.com/CCOMJHC/csbschema/tree/main/docs).

## submitDCDB.ps1: Submit IHO B12 GeoJSON data to DCDB
Often, the last step of processing WIBL data will be submission to [DCDB](https://www.ngdc.noaa.gov/iho/). This can
be done for individual files using the `wibl dcdbupload` command. For uploading files in batch, you can use the
[submitDCDB.ps1](submitDCDB.ps1).

To use `submitDCDB.ps1` you need to specify three parameters: 
1. The path to a directory containing (hopefully 
validated) GeoJSON files to submit to DCDB; 
2. A text file containing authentication credentials for submitting data
to DCDB; and 
3. A JSON configuration file for local processing (the same file as used with `processWibl.ps1`). 
Optionally, you can specify the file extension of GeoJSON files to submit using the `-extension` option
(the default is `json`).

To learn more about how to run `submitDCDB.ps1`, use the `Get-Help` command:
```
PS /Users/janeuser/wibl/wibl-python/scripts/data-management> Get-Help ./submitDCDB.ps1 
submitDCDB.ps1 [-inPath] <string> -authFile <string> -configFile <string> [-extension <string>] [<CommonParameters>]
```
