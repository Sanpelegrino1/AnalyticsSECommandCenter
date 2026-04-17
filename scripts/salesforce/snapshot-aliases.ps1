Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\CommandCenter.Common.ps1')

Assert-CommandAvailable -Name 'sf' -Hint 'Install Salesforce CLI or run the bootstrap script.'

$snapshotDirectory = Resolve-CommandCenterPath 'tmp/snapshots'
Ensure-Directory -Path $snapshotDirectory

$snapshotPath = Join-Path $snapshotDirectory ("salesforce-orgs-{0}.json" -f ([DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')))
& sf org list --json | Set-Content -Path $snapshotPath -Encoding UTF8

Write-Host "Wrote Salesforce org snapshot to '$snapshotPath'."
