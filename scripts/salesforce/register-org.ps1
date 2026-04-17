param(
    [Parameter(Mandatory = $true)]
    [string]$Alias,
    [Parameter(Mandatory = $true)]
    [string]$LoginUrl,
    [string]$Purpose = '',
    [string]$Notes = '',
    [switch]$SetPreferred
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\CommandCenter.Common.ps1')

$registryPath = Resolve-CommandCenterPath 'notes/registries/salesforce-orgs.json'
$registry = Read-JsonFile -Path $registryPath
if (-not $registry) {
    $registry = [pscustomobject]@{
        defaultAlias = ''
        orgs = @()
    }
}

$orgs = @($registry.orgs)
$existing = $orgs | Where-Object { $_.alias -eq $Alias } | Select-Object -First 1
if ($existing) {
    $existing.loginUrl = $LoginUrl
    $existing.purpose = $Purpose
    $existing.notes = $Notes
    $existing.lastValidatedUtc = Get-UtcTimestamp
} else {
    $orgs += [pscustomobject]@{
        alias = $Alias
        loginUrl = $LoginUrl
        purpose = $Purpose
        notes = $Notes
        lastValidatedUtc = Get-UtcTimestamp
    }
}

$registry.orgs = $orgs
if ($SetPreferred) {
    $registry.defaultAlias = $Alias
}

Write-JsonFile -Path $registryPath -Value $registry
Write-Host "Registered Salesforce alias '$Alias'."
