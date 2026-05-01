# OrgSetup step (h+) -- enable SLDS v2 dark mode at the org level.
#
# Deploys UserInterface settings with enableSldsV2 + enableSldsV2DarkModeInCosmos.
# This unlocks dark mode as an option; each user must still pick "Dark" from
# their avatar menu > Appearance. Salesforce does not currently expose a
# public CRUD surface for the per-user selection (not a UserPreferences*
# boolean, not a sobject), so the script always emits a warning reminding
# the user to complete the per-user step manually.
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
Write-Host '--- [h] Enable dark mode (SLDS v2) ---'

$state = Read-OrgSetupState -Alias $Alias
if (@($state.completed) -contains 'h-dark-mode') {
    Write-Host '  Already completed — skipping.' -ForegroundColor Cyan
    return
}

# Check live state via Tooling API before deploying -- gracefully skip if unavailable
$auth = Get-OrgSetupAuth -Alias $Alias
Write-Host '  Checking current dark mode status...'
try {
    $current = Invoke-OrgSetupSoql -Auth $auth -Tooling `
        -Soql 'SELECT IsSldsV2Enabled, IsSldsV2DarkModeInCosmosEnabled FROM UserInterfaceSettings'
    if ($current.records -and $current.records.Count -gt 0) {
        $rec = $current.records[0]
        if ([bool]$rec.IsSldsV2Enabled -and [bool]$rec.IsSldsV2DarkModeInCosmosEnabled) {
            Write-Host '  Already enabled — skipping.' -ForegroundColor Cyan
            Add-OrgSetupLogEntry -Alias $Alias -Step 'h-dark-mode' -Outcome 'noop' `
                -Message 'SLDS v2 + dark mode already enabled.'
            $warnMsg = 'Dark Mode is enabled at the org level. Click your profile avatar > Appearance > Dark to switch your own user.'
            Add-OrgSetupWarning -Alias $Alias -Step 'h-dark-mode' -Feature 'User dark mode' -Message $warnMsg
            Write-Host '  [h] Done (noop).' -ForegroundColor Cyan
            return
        }
    }
} catch {
    Write-Host '  Could not query dark mode state -- proceeding with deploy.' -ForegroundColor Yellow
}

$sf = Get-RequiredCommandPath -Name 'sf' -Hint 'Install Salesforce CLI.'
$salesforceRoot = Resolve-CommandCenterPath 'salesforce'

Push-Location $salesforceRoot
try {
    Write-Host '  Deploying Settings:UserInterface (enableSldsV2 + enableSldsV2DarkModeInCosmos)...'
    $exit = Invoke-OrgSetupNative -FilePath $sf -Arguments @(
        'project','deploy','start',
        '--target-org',$Alias,
        '--metadata','Settings:UserInterface',
        '--ignore-conflicts','--ignore-warnings',
        '--async'
    )
} finally {
    Pop-Location
}

if ($exit -ne 0) {
    $warnMsg2 = "Settings:UserInterface deploy failed (exit $exit). Enable dark mode manually in Setup > Themes and Branding."
    Add-OrgSetupWarning -Alias $Alias -Step 'h-dark-mode' -Message $warnMsg2
    Add-OrgSetupLogEntry -Alias $Alias -Step 'h-dark-mode' -Outcome 'failed' `
        -Message 'UserInterface settings deploy failed.'
    return
}

Add-OrgSetupLogEntry -Alias $Alias -Step 'h-dark-mode' -Outcome 'completed' `
    -Message 'Deployed enableSldsV2 + enableSldsV2DarkModeInCosmos (org-level).'
Write-Host '  SLDS v2 dark mode enabled at org level.' -ForegroundColor Green

# Per-user selection has no public API -- always remind the user.
$warnMsg3 = 'Dark Mode Enabled at the org level. Click your profile avatar > Appearance > Dark to switch your own user.'
Add-OrgSetupWarning -Alias $Alias -Step 'h-dark-mode' -Feature 'User dark mode' -Message $warnMsg3
Write-Host '  [h] Done.' -ForegroundColor Green
