param(
  [Parameter(Mandatory=$True, Position=0)]
  [string]$inPath,

  [Parameter(Mandatory=$False)]
  [string]$extension = "json",

  [Parameter(Mandatory=$False)]
  [string]$schema
)

Get-ChildItem -Path $inPath -Filter "*.$extension" -File -Recurse |
  ForEach-Object -Process {
    Write-Output "Validating file $($_.FullName)..."
        if ( $PSBoundParameters.ContainsKey('schema') ) {
        csbschema validate -f $_.FullName --version $schema
    } else {
        csbschema validate -f $_.FullName
    }

    if ($LASTEXITCODE -eq 0) {
        Write-Host "Successfully validated against CSB schema" -ForegroundColor Green
    } else {
        Write-Host "Failed to validate against CSB schema" -ForegroundColor Red
    }
    
    # Add a small gap between files for readability
    Write-Output "" 
  }
