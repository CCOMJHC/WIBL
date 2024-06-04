param(
  [string]$datFile,
  [string]$metadataFile,
  [string]$wiblConfig,
  [string]$LogConvertPath = ".\logconvert\logconvert.exe",
  [string]$Format = "YDVR"
)

Write-Output "Input DAT file to convert is: $datFile"
$statsName = $datFile -replace '\.dat', '-stats.txt'
Write-Output "Writing logconvert stats to file: $statsName"
$wiblFile = $datFile -replace '\.dat', '.wibl'
Write-Output "Writing logconvert wibl file to: $wiblFile"
$editedName = $wiblFile -replace '\.wibl', '-edited.wibl'
Write-Output "Writing edited wibl file to: $editedName"
$processedName = $editedName -replace '-edited.wibl', '.geojson'
Write-Output "Writing to GeoJSON file: $processedName"

Write-Output "Using metadata file: $metadataFile"
Write-Output "Using WIBL config file: $wiblConfig"
Write-Output "Using logconvert at: $LogConvertPath"
Write-Output "Input logger file format is: $Format"

$res = Read-Host "Do you want to continue?"
if ($res -ne 'y') {
    exit
}


Write-Output "Running 'logconvert'..."
& $LogConvertPath --stats -f $Format -i $datFile -o $wiblFile > $statsName
if ( -not ($LASTEXITCODE -eq 0) ) {
  Write-Error "Error running 'logconvert', exiting..."
  exit -1
}

Write-Output "Running 'wibl editwibl'..."
wibl editwibl -m $metadataFile $wiblFile $editedName
if ( -not ($LASTEXITCODE -eq 0) ) {
  Write-Error "Error running 'wibl editwibl', exiting..."
  exit -1
}

Write-Output "Running 'wibl procwibl'..."
wibl procwibl -c $wiblConfig $editedName $processedName
if ( -not ($LASTEXITCODE -eq 0) ) {
  Write-Error "Error running 'wibl procwibl', exiting..."
  exit -1
}

Write-Output "Running 'csbschema validate'..."
csbschema validate -f $processedName
