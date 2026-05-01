# Thin shim -- forwards to run-setup.ps1.
# Kept so existing docs / muscle memory pointing at "run-resume.ps1" still work.

param(
    [string]$Alias = '',
    [switch]$NoConnectedApp,
    [switch]$NoWait   # accepted but ignored -- DC is always checked live now
)

$forward = @{ Alias = $Alias }
if ($NoConnectedApp) { $forward['NoConnectedApp'] = $true }

& (Join-Path $PSScriptRoot 'run-setup.ps1') @forward
