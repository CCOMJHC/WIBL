param(
  [Parameter(Mandatory=$True, Position=0)]
  [string]$inPath,

  [Parameter(Mandatory=$True)]
  [string]$authFile,

  [Parameter(Mandatory=$True)]
  [string]$configFile,

  [Parameter(Mandatory=$False)]
  [string]$extension = "json"
)

Get-ChildItem -Path $inPath -Filter "*.$extension" -File -Recurse |
  ForEach-Object -Process {
    # Run wibl dcdbupload to submit to DCDB
    Write-Output "Submitting file $_ to DCDB..."
    wibl dcdbupload $_ -a $authFile -c $configFile
    if ( -not ($LASTEXITCODE -eq 0) ) {
      Write-Error "Error submitting $_, exiting..."
      exit -1
    }
  }
