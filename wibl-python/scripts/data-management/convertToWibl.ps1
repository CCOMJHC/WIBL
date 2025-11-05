<#
.SYNOPSIS
Convert YDVR or TeamSurv logger files to WIBL files.

.DESCRIPTION
This script converts YDVR or TeamSurv logger files in a .zip file to .WIBL files in a directory that
matches the source .zip.

.OUTPUTS
A directory structure containing .WIBL files matching the input .zip file

.INPUTS
A .zip file containing subdirectories of .DAT files

.NOTES
The -verbose flag will show you some more information of what's happening behind the scenes.
The -debug flag will tell you about each file as they're getting converted

This script is multithreaded, and therefore requires at least Powershell 7.0.0
This was developed using Powershell 7.3.4

Developed by Chris Schwartz at The Center for Coastal and Ocean Mapping, 7-19-2023.
cschwartz@ccom.unh.edu / christopher.schwartz@unh.edu

.PARAMETER Source
The source .ZIP file to extract the .DAT files from

.PARAMETER LogConvertPath
The location of logconvert.exe, if it isn't in a folder next to the script called "logconvert"

.PARAMETER Format
The format to convert from, either YDVR or TeamSurv.

.PARAMETER OutputFolder
A folder to output all of the processed files to. This folder will have the same structure as the
source zip folder

.EXAMPLE
PS > ./Convert-DATToWIBL.ps1 input.zip output

.EXAMPLE
PS > ./Convert-DATToWIBL.ps1 -Source input.zip -OutputFolder C:\foo\bar\baz

.EXAMPLE
PS > ./Convert-DATToWIBL -Source input.zip -OutputFolder C:\foo\bar\baz -LogConvertPath C:\foo\bar\logconvert.exe

.EXAMPLE
PS > ./Convert-DATToWIBL -Source input.zip -OutputFolder C:\foo\bar\baz -LogConvertPath C:\foo\bar\logconvert.exe

#>

#Requires -Version 7

[CmdletBinding()]

param (
    # The input ZIP file    
    [Parameter( Mandatory = $True, Position = 0, ValueFromPipeline )]
    [string]$Source,
    
    # The output to send the resulting .WIBL files
    [Parameter( Mandatory = $True, Position = 1  )]
    [string]$OutputFolder,

    # The logconvert program can be anywhere, but we can assume it
    # to be in the local directory if the user doesn't specifiy it.
    [string]$LogConvertPath = ".\logconvert\logconvert.exe",

    # The format to convert from, either YDVR or TeamSurv.
    [string]$Format = "YDVR"
)

# Before starting, verify that we have access to our logconvert program.
# This should be in a folder on the same level as the script
if ( -not ( Test-Path -Path $LogConvertPath ) ) {
    Write-Error "Could not find logconvert. Make sure it's in a folder in the same directory as this script."
    return -1
}

# Otherwise we may be good to go. We're going to assume logconvert has all of it's dependencies
# in the directory with it. 

# Make sure the input zip exists. This is more of a sanity check.
if ( -not ( Test-Path "$Source" ) ) {
    Write-Error "Source ZIP file does not exist. Check your path and try again."
    return -2
}
elseif ( -not ( $Source.ToLower().EndsWith( ".zip" ) ) ) {
    Write-Error "Source is not a ZIP file!"
    return -3
}

# And now we should make sure the output directory exists.
if ( -not ( Test-Path -Path $OutputFolder ) ) {
    Write-Verbose "Output directory not found. Creating a new directory."
    New-Item -Path $OutputFolder -Name $OutputFolderName -ItemType Directory | Out-Null
}
else {
    # TODO ask if they want to overwrite the already existing directory
    $OverwriteOutputResponse = Read-Host -Prompt "Output directory exists. Do you want to overwrite it? ( y\n )"
    if ( $OverwriteOutputResponse.ToLower() -ne "y" ) {
        return 0
    }
    else {
        Remove-Item -Recurse -Force -Path $OutputFolder
    }
}

# And now, lettuce begin.
# Copy everything to the output folder
Expand-Archive -Path $Source -DestinationPath $OutputFolder -Force | Out-Null

# Get all of the files in the output directory
$AllFiles = Get-ChildItem -Path $OutputFolder -recurse | where {$_.extension -in ".DAT",".tsv"}

# Get the full path to log convert since we move directories quite often
$FullLogConvertPath = Resolve-Path $LogConvertPath
Write-Debug "Full logconvert path: $( $FullLogConvertPath )"

# And then for each .dat file, use logconvert to make it a .wibl
$AllFiles | ForEach-Object -ThrottleLimit 20 -Parallel {
    $WIBLFileName = $PSItem.BaseName + ".wibl"
    $CurrentItemDirectory = $PSItem.Directory.FullName

    Write-Verbose "Processing file $( $PSItem.Name ) ---> $( $WIBLFileName )" -Verbose

    # Go to the directory that the .dat file lives in and then 
    # use log convert in that directory.
    Push-Location -Path $CurrentItemDirectory -StackName "Wibl"
    & $using:FullLogConvertPath -f $using:Format -i $PSItem.FullName -o $WIBLFileName | Out-Null
    Pop-Location -StackName "Wibl"

    Remove-Item $PSItem
}