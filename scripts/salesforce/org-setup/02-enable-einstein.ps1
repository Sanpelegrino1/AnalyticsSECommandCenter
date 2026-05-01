# OrgSetup step (b) -- Enable Einstein (Einstein Generative AI platform).
#
# Deploys Settings:EinsteinGpt via Metadata API with three flags:
#   - enableEinsteinGptPlatform=true                   (master "Turn on Einstein" toggle)
#   - enableAIModelBeta=true                           (Beta Generative AI Models)
#   - enableEinsteinGptAllowUnsafePTInputChanges=true  (Allow Unsafe Changes to prompt templates)
#
# Tooling API PATCH on settings sobjects returns 500; Metadata API deploy is the public path.
# Also covers step (i) indirectly -- Einstein is a prerequisite for Agentforce bots in step (k).
# Idempotent: deploy is a no-op if already in desired state.
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
Write-Host '--- [b] Enable Einstein ---'

$auth = Get-OrgSetupAuth -Alias $Alias
Write-Host '  Checking current Einstein status...'
$current = Invoke-OrgSetupSoql -Auth $auth -Tooling `
    -Soql 'SELECT IsEinsteinGptPlatformEnabled FROM EinsteinGptSettings'
if ($current.records -and $current.records.Count -gt 0 -and [bool]$current.records[0].IsEinsteinGptPlatformEnabled) {
    Write-Host '  Already enabled — skipping.' -ForegroundColor Cyan
    Add-OrgSetupLogEntry -Alias $Alias -Step 'b-enable-einstein' -Outcome 'noop' `
        -Message 'Einstein already enabled.'
    return
}

$sf = Get-RequiredCommandPath -Name 'sf' -Hint 'Install Salesforce CLI.'
$salesforceRoot = Resolve-CommandCenterPath 'salesforce'
Push-Location $salesforceRoot
try {
    Write-Host '  Deploying Settings:EinsteinGpt (platform + beta models + allow unsafe PT changes)...'
    $exit = Invoke-OrgSetupNative -FilePath $sf -Arguments @(
        'project','deploy','start',
        '--target-org',$Alias,
        '--metadata','Settings:EinsteinGpt',
        '--ignore-conflicts'
    )
    if ($exit -ne 0) {
        Add-OrgSetupLogEntry -Alias $Alias -Step 'b-enable-einstein' -Outcome 'failed' `
            -Message "sf project deploy start exited $exit"
        throw 'Einstein enable deploy failed.'
    }
} finally {
    Pop-Location
}

Add-OrgSetupLogEntry -Alias $Alias -Step 'b-enable-einstein' -Outcome 'completed' `
    -Message 'Deployed enableEinsteinGptPlatform + enableAIModelBeta + enableEinsteinGptAllowUnsafePTInputChanges.'
Write-Host '  [b] Done.' -ForegroundColor Green
