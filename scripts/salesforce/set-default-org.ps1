param(
    [Parameter(Mandatory = $true)]
    [string]$Alias
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\CommandCenter.Common.ps1')

Assert-CommandAvailable -Name 'sf' -Hint 'Install Salesforce CLI or run the bootstrap script.'

& sf config set target-org=$Alias
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$registryPath = Resolve-CommandCenterPath 'notes/registries/salesforce-orgs.json'
$registry = Read-JsonFile -Path $registryPath
if ($registry) {
    $registry.defaultAlias = $Alias
    Write-JsonFile -Path $registryPath -Value $registry
}

Write-Host "Set default Salesforce org to '$Alias'."
