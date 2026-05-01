# OrgSetup step (d) -- deploy the Access_Analytics_Agent permission set.
#
# Only deploys the permset here. Tableau_Next_Admin_PSG is deployed separately
# in 03b-deploy-psg.ps1 during the RESUME phase, after Data Cloud is confirmed
# ready (the PSG references CDP/Tableau permsets that don't exist until then).
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
Write-Host '--- [d] Deploy Access_Analytics_Agent permset ---'

$sf = Get-RequiredCommandPath -Name 'sf' -Hint 'Install Salesforce CLI.'
$salesforceRoot = Resolve-CommandCenterPath 'salesforce'

Push-Location $salesforceRoot
try {
    Write-Host '  Deploying PermissionSet:Access_Analytics_Agent...'
    $exit = Invoke-OrgSetupNative -FilePath $sf -Arguments @(
        'project','deploy','start',
        '--target-org',$Alias,
        '--metadata','PermissionSet:Access_Analytics_Agent',
        '--ignore-conflicts'
    )
    if ($exit -ne 0) {
        Add-OrgSetupLogEntry -Alias $Alias -Step 'd-deploy-permset' -Outcome 'failed' `
            -Message "sf project deploy start exited $exit"
        throw "Permset deploy failed."
    }
} finally {
    Pop-Location
}

Add-OrgSetupLogEntry -Alias $Alias -Step 'd-deploy-permset' -Outcome 'completed' `
    -Message 'Deployed Access_Analytics_Agent.'
Write-Host '  [d] Done.' -ForegroundColor Green
