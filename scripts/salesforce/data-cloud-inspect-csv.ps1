[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$CsvPath,
    [int]$SampleRows = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'DataCloud.Common.ps1')

$csvProfile = Get-DataCloudCsvProfile -CsvPath $CsvPath -SampleRows $SampleRows -AllowHeaderOnly -ContextLabel 'CSV inspection'

$result = [pscustomobject]@{
    csvPath = $csvProfile.csvPath
    sizeBytes = $csvProfile.sizeBytes
    lineCount = $csvProfile.lineCount
    estimatedDataRows = $csvProfile.estimatedDataRows
    headers = $csvProfile.headers
    hasDuplicateHeaders = $false
    duplicateHeaders = @()
    sampleRows = $csvProfile.sampleRows
}

Write-Output $result
