param(
    [string]$TargetKey = 'default',
    [string]$ServerUrl,
    [string]$SiteContentUrl,
    [string]$DefaultProjectId,
    [string]$Purpose = '',
    [string]$Notes = '',
    [switch]$SetDefault
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '_Tableau.Common.ps1')

$registry = Get-TableauRegistry
$targets = @($registry.targets)
$existing = @($targets | Where-Object { $_.key -eq $TargetKey }) | Select-Object -First 1

if ($existing) {
    if ($ServerUrl) { $existing.serverUrl = $ServerUrl }
    if ($SiteContentUrl) { $existing.siteContentUrl = $SiteContentUrl }
    if ($DefaultProjectId) { $existing.defaultProjectId = $DefaultProjectId }
    $existing.purpose = $Purpose
    $existing.notes = $Notes
    $existing.lastValidatedUtc = Get-UtcTimestamp
} else {
    $targets += [pscustomobject]@{
        key = $TargetKey
        serverUrl = $ServerUrl
        siteContentUrl = $SiteContentUrl
        defaultProjectId = $DefaultProjectId
        purpose = $Purpose
        notes = $Notes
        lastValidatedUtc = Get-UtcTimestamp
    }
}

$registry.targets = $targets
if ($SetDefault) {
    $registry.defaultTargetKey = $TargetKey
}

Save-TableauRegistry -Registry $registry
& (Join-Path $PSScriptRoot 'auth-status.ps1') -TargetKey $TargetKey | Out-Null
