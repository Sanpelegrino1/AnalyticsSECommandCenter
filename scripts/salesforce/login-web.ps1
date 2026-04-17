param(
    [string]$Alias = $env:SF_DEFAULT_ALIAS,
    [string]$InstanceUrl = $env:SF_LOGIN_URL,
    [string]$Purpose = '',
    [string]$Notes = '',
    [switch]$SetDefault
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\CommandCenter.Common.ps1')

Import-CommandCenterEnv
Assert-CommandAvailable -Name 'sf' -Hint 'Install Salesforce CLI or run the bootstrap script.'

if (-not $Alias) {
    throw 'Provide -Alias or set SF_DEFAULT_ALIAS in .env.local.'
}

if (-not $InstanceUrl) {
    $InstanceUrl = 'https://login.salesforce.com'
}

$scriptPath = Resolve-CommandCenterPath 'salesforce/scripts/auth-web.ps1'
& $scriptPath -Alias $Alias -InstanceUrl $InstanceUrl -SetDefault:$SetDefault
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& (Join-Path $PSScriptRoot 'register-org.ps1') -Alias $Alias -LoginUrl $InstanceUrl -Purpose $Purpose -Notes $Notes -SetPreferred:$SetDefault
