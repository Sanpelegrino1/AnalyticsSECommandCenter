Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '_Tableau.Common.ps1')

$snapshotDirectory = Resolve-CommandCenterPath 'tmp/snapshots'
Ensure-Directory -Path $snapshotDirectory

$snapshotPath = Join-Path $snapshotDirectory ("tableau-targets-{0}.json" -f ([DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')))
$registry = Get-TableauRegistry
$registry | ConvertTo-Json -Depth 20 | Set-Content -Path $snapshotPath -Encoding UTF8

Write-Host "Wrote Tableau target snapshot to '$snapshotPath'."