[CmdletBinding()]
param(
    [string]$Alias = $(if (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_SALESFORCE_ALIAS)) { $env:DATACLOUD_SALESFORCE_ALIAS } elseif (-not [string]::IsNullOrWhiteSpace($env:SF_DEFAULT_ALIAS)) { $env:SF_DEFAULT_ALIAS } else { '' }),
    [string]$InstanceUrl = $env:SF_LOGIN_URL,
    [string]$ClientId = $(if (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_CLIENT_ID)) { $env:DATACLOUD_CLIENT_ID } else { 'CommandCenterAuthClient20260417A9F3D7K2M8Q4R6T1V5X' }),
    [string]$Scopes = 'api refresh_token offline_access cdp_ingest_api',
    [string]$Purpose = 'Data Cloud ingestion auth',
    [string]$Notes = '',
    [string]$ValidationTargetKey,
    [switch]$ValidateAfterLogin,
    [switch]$SetDefault
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\CommandCenter.Common.ps1')

Import-CommandCenterEnv
Assert-CommandAvailable -Name 'sf' -Hint 'Install Salesforce CLI or run the bootstrap script.'

if ([string]::IsNullOrWhiteSpace($Alias)) {
    throw 'Provide -Alias or set DATACLOUD_SALESFORCE_ALIAS in .env.local.'
}

if ([string]::IsNullOrWhiteSpace($ClientId)) {
    throw 'Provide -ClientId or set DATACLOUD_CLIENT_ID in .env.local.'
}

if ([string]::IsNullOrWhiteSpace($InstanceUrl)) {
    $InstanceUrl = 'https://login.salesforce.com'
}

$args = @(
    'org', 'login', 'web',
    '--alias', $Alias,
    '--instance-url', $InstanceUrl,
    '--client-id', $ClientId,
    '--scopes', $Scopes
)

if ($SetDefault) {
    $args += '--set-default'
}

Write-Host ("Opening Data Cloud browser login for alias '{0}' against '{1}'." -f $Alias, $InstanceUrl) -ForegroundColor Cyan
& sf @args
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& (Join-Path $PSScriptRoot 'register-org.ps1') -Alias $Alias -LoginUrl $InstanceUrl -Purpose $Purpose -Notes $Notes -SetPreferred:$SetDefault

if (-not $ValidateAfterLogin) {
    return
}

$validationScriptPath = Join-Path $PSScriptRoot 'data-cloud-get-access-token.ps1'
$previousAlias = $env:DATACLOUD_SALESFORCE_ALIAS
$env:DATACLOUD_SALESFORCE_ALIAS = $Alias

try {
    $validationArgs = @{
        AsJson = $true
    }

    if (-not [string]::IsNullOrWhiteSpace($ValidationTargetKey)) {
        $validationArgs.TargetKey = $ValidationTargetKey
    }

    Write-Host 'Validating Data Cloud token exchange...' -ForegroundColor Cyan
    $validationResult = & $validationScriptPath @validationArgs | ConvertFrom-Json
    $validationResult | Select-Object targetKey, tokenSource, tenantEndpoint, sourceName, objectName | Format-List
} catch {
    throw "Browser login succeeded, but Data Cloud validation failed. Check the connected app scopes, client ID, and Data Cloud setup. $($_.Exception.Message)"
} finally {
    if ([string]::IsNullOrWhiteSpace($previousAlias)) {
        Remove-Item Env:DATACLOUD_SALESFORCE_ALIAS -ErrorAction SilentlyContinue
    } else {
        $env:DATACLOUD_SALESFORCE_ALIAS = $previousAlias
    }
}