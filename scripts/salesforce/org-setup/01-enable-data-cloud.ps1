# OrgSetup step (a) -- Enable Data Cloud.
#
# Deploys the CustomerDataPlatformSettings.enableCustomerDataPlatform=true flag
# via Metadata API. Tooling API PATCH on the settings sobject is NOT supported
# (returns 500); deployment is the only headless path.
#
# This begins ~30 min tenant provisioning. Use 05-wait-for-data-cloud.ps1 to poll completion.
# Idempotent: metadata deploy is a no-op if the flag is already true.
#
# Inputs:  -Alias  (required)

param(
    [Parameter(Mandatory = $true)]
    [string]$Alias
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'lib\OrgSetup.Common.ps1')

Write-Host ''
Write-Host '--- [a] Enable Data Cloud ---'

$auth = Get-OrgSetupAuth -Alias $Alias
Write-Host '  Checking current Data Cloud status...'
$current = Invoke-OrgSetupSoql -Auth $auth -Tooling `
    -Soql 'SELECT IsCustomerDataPlatformEnabled FROM CustomerDataPlatformSettings'
if ($current.records -and $current.records.Count -gt 0 -and [bool]$current.records[0].IsCustomerDataPlatformEnabled) {
    Write-Host '  Already enabled — skipping.' -ForegroundColor Cyan
    Add-OrgSetupLogEntry -Alias $Alias -Step 'a-enable-data-cloud' -Outcome 'noop' `
        -Message 'Data Cloud already enabled.'
    return
}

$sf = Get-RequiredCommandPath -Name 'sf' -Hint 'Install Salesforce CLI.'
$salesforceRoot = Resolve-CommandCenterPath 'salesforce'
Push-Location $salesforceRoot
try {
    Write-Host '  Deploying Settings:CustomerDataPlatform...'
    $exit = Invoke-OrgSetupNative -FilePath $sf -Arguments @(
        'project','deploy','start',
        '--target-org',$Alias,
        '--metadata','Settings:CustomerDataPlatform',
        '--ignore-conflicts'
    )
    if ($exit -ne 0) {
        Add-OrgSetupLogEntry -Alias $Alias -Step 'a-enable-data-cloud' -Outcome 'failed' `
            -Message "sf project deploy start exited $exit"
        throw 'Data Cloud enable deploy failed.'
    }
} finally {
    Pop-Location
}

Add-OrgSetupLogEntry -Alias $Alias -Step 'a-enable-data-cloud' -Outcome 'completed' `
    -Message 'Deployed enableCustomerDataPlatform=true; tenant provisioning started (~30 min).'
Write-Host '  Data Cloud enabled. Async provisioning started (~30 min).' -ForegroundColor Green
Write-Host '  [a] Done.' -ForegroundColor Green
