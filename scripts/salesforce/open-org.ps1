param(
    [string]$TargetOrg = $env:SF_DEFAULT_ALIAS,
    [string]$Path,
    [string]$SourceFile,
    [switch]$UrlOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\CommandCenter.Common.ps1')

Import-CommandCenterEnv
if (-not $TargetOrg) {
    throw 'Provide -TargetOrg or set SF_DEFAULT_ALIAS in .env.local.'
}

$scriptPath = Resolve-CommandCenterPath 'salesforce/scripts/org-open.ps1'
& $scriptPath -TargetOrg $TargetOrg -Path $Path -SourceFile $SourceFile -UrlOnly:$UrlOnly
exit $LASTEXITCODE
