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
    Write-Host "Validating: $($_.Name)..." -ForegroundColor Cyan -NoNewline
    
    # Run validation and capture both standard output and errors into $results
    if ( $PSBoundParameters.ContainsKey('schema') ) {
        $results = csbschema validate -f $_.FullName --version $schema 2>&1
    } else {
        $results = csbschema validate -f $_.FullName 2>&1
    }

    if ($LASTEXITCODE -eq 0) {
        Write-Host " [PASS]" -ForegroundColor Green
    } else {
        Write-Host " [FAIL]" -ForegroundColor Red
        
        # Extract just the first few lines of the error to see why it failed 
        # without printing every single coordinate.
        $summaryError = $results | Where-Object { $_ -like "*error:*" } | Select-Object -First 3
        
        Write-Host "  Partial error output: Data is missing required properties (depth/time)." -ForegroundColor Yellow
        if ($summaryError) {
            Write-Host "  Details: $summaryError" -ForegroundColor Gray
        }
        Write-Host "  ----------------------------------------------------" -ForegroundColor Red
    }
  }
