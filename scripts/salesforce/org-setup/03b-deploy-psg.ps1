# OrgSetup step (e) -- deploy Tableau_Next_Admin_PSG permission set group.
#
# Run during RESUME (after Data Cloud is confirmed ready) because the PSG
# references CDP/Tableau permsets (CDPAdmin, TableauEinsteinAdmin, etc.) that
# only materialize after Data Cloud finishes provisioning.
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
Write-Host '--- [e] Deploy Tableau_Next_Admin_PSG ---'

$state = Read-OrgSetupState -Alias $Alias
if (@($state.completed) -contains 'e-deploy-psg') {
    Write-Host '  Already completed — skipping.' -ForegroundColor Cyan
    return
}

$sf = Get-RequiredCommandPath -Name 'sf' -Hint 'Install Salesforce CLI.'
$salesforceRoot = Resolve-CommandCenterPath 'salesforce'

Push-Location $salesforceRoot
try {
    Write-Host '  Deploying PermissionSetGroup:Tableau_Next_Admin_PSG...'
    $exit = Invoke-OrgSetupNative -FilePath $sf -Arguments @(
        'project','deploy','start',
        '--target-org',$Alias,
        '--metadata','PermissionSetGroup:Tableau_Next_Admin_PSG',
        '--ignore-conflicts'
    )
    if ($exit -ne 0) {
        $warnMsg = "PSG deploy failed (exit $exit). Deploy manually: Setup > Permission Set Groups > New > add the standard Tableau/CDP/Agentforce permsets."
        Add-OrgSetupWarning -Alias $Alias -Step 'e-deploy-psg' -Message $warnMsg
        Add-OrgSetupLogEntry -Alias $Alias -Step 'e-deploy-psg' -Outcome 'failed' `
            -Message "sf project deploy start exited $exit"
        Write-Host '  FAILED: PSG deploy (see warning).' -ForegroundColor Red
        return
    }
} finally {
    Pop-Location
}

Add-OrgSetupLogEntry -Alias $Alias -Step 'e-deploy-psg' -Outcome 'completed' `
    -Message 'Deployed Tableau_Next_Admin_PSG.'
Write-Host '  Tableau_Next_Admin_PSG deployed.' -ForegroundColor Green
Write-Host '  [e] Done.' -ForegroundColor Green
