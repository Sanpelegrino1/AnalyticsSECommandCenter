param(
    [Parameter(Mandatory = $true)]
    [string]$TargetKey
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '_Tableau.Common.ps1')

$registry = Get-TableauRegistry
$target = @($registry.targets | Where-Object { $_.key -eq $TargetKey }) | Select-Object -First 1
if (-not $target) {
    throw "Target '$TargetKey' is not registered in notes/registries/tableau-targets.json."
}

$registry.defaultTargetKey = $TargetKey
Save-TableauRegistry -Registry $registry
Write-Host "Set default Tableau target to '$TargetKey'."
