param(
    [string]$TargetOrg = $env:SF_DEFAULT_ALIAS,
    [string]$ManifestPath = 'manifest/package.xml',
    [string[]]$Metadata
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\CommandCenter.Common.ps1')

Import-CommandCenterEnv
Assert-CommandAvailable -Name 'sf' -Hint 'Install Salesforce CLI or run the bootstrap script.'

if (-not $TargetOrg) {
    throw 'Provide -TargetOrg or set SF_DEFAULT_ALIAS in .env.local.'
}

$salesforceRoot = Resolve-CommandCenterPath 'salesforce'
Push-Location $salesforceRoot
try {
    if ($Metadata -and $Metadata.Count -gt 0) {
        & sf project retrieve start --target-org $TargetOrg --metadata $Metadata
        exit $LASTEXITCODE
    }

    & (Join-Path $PSScriptRoot '..\..\salesforce\scripts\retrieve-manifest.ps1') -TargetOrg $TargetOrg -ManifestPath $ManifestPath
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
