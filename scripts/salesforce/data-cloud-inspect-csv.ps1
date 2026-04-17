[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$CsvPath,
    [int]$SampleRows = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$resolvedCsvPath = (Resolve-Path $CsvPath).Path
$fileInfo = Get-Item -Path $resolvedCsvPath
$rows = @(Import-Csv -Path $resolvedCsvPath | Select-Object -First $SampleRows)

$headers = @()
if ($rows.Count -gt 0) {
    $headers = @($rows[0].PSObject.Properties.Name)
} else {
    $headerLine = Get-Content -Path $resolvedCsvPath -TotalCount 1
    if (-not [string]::IsNullOrWhiteSpace($headerLine)) {
        $headers = @($headerLine.Split(',') | ForEach-Object { $_.Trim('"') })
    }
}

$lineCount = (Get-Content -Path $resolvedCsvPath | Measure-Object -Line).Lines

$result = [pscustomobject]@{
    csvPath = $resolvedCsvPath
    sizeBytes = $fileInfo.Length
    lineCount = $lineCount
    estimatedDataRows = [Math]::Max($lineCount - 1, 0)
    headers = $headers
    sampleRows = $rows
}

Write-Output $result
