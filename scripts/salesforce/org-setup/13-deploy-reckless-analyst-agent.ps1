# OrgSetup step (n) -- deploy and activate the Reckless Analyst (Employee) agent.
#
# Opt-in only. Run via run-setup.ps1 -MakeAgent, or standalone.
#
# Uses the authoring-bundle publish path (sf agent generate authoring-bundle ->
# sf agent publish authoring-bundle) which is the only CLI path that produces
# an InternalCopilot / Employee Agent visible in the Concierge sidebar dropdown.
#
# Deploys:
#   - AiAuthoringBundle:  Reckless_Analyst_Employee  (from repo source)
#   - PermissionSet:      Reckless_Analyst_Access     (from repo source)
#   - SetupEntityAccess:  Reckless_Analyst_Access -> Reckless_Analyst_Employee
#   - PermSetAssignment:  Reckless_Analyst_Access -> running user
#
# Idempotent: checks for existing BotDefinition and SetupEntityAccess before acting.
# Safe to rerun -- already-present resources are logged as noop.
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
Write-Host '--- [n] Deploy Reckless Analyst Employee agent ---'

$sf  = Get-RequiredCommandPath -Name 'sf' -Hint 'Install Salesforce CLI.'
$auth = Get-OrgSetupAuth -Alias $Alias
$api  = Get-OrgSetupApiVersion

$salesforceRoot = Resolve-CommandCenterPath 'salesforce'

# ── 1. Publish authoring bundle ──────────────────────────────────────────────
Write-Host '  Checking for existing Reckless_Analyst_Employee agent...'

$existing = $null
try {
    $existing = Invoke-OrgSetupSoql -Auth $auth -Soql `
        "SELECT Id, DeveloperName, Type FROM BotDefinition WHERE DeveloperName = 'Reckless_Analyst_Employee'"
} catch {
    $warnBot = 'BotDefinition sObject not available (' + $_.Exception.Message + '). Ensure Agentforce is enabled (step 06) then rerun.'
    Add-OrgSetupWarning -Alias $Alias -Step 'n-reckless-analyst' -Message $warnBot
    Add-OrgSetupLogEntry -Alias $Alias -Step 'n-reckless-analyst' -Outcome 'skipped' `
        -Message 'BotDefinition unavailable; Agentforce likely not enabled.'
    return
}

if ($existing -and $existing.records -and $existing.records.Count -gt 0) {
    Write-Host '  Reckless_Analyst_Employee already exists -- skipping publish.' -ForegroundColor Cyan
    Add-OrgSetupLogEntry -Alias $Alias -Step 'n-reckless-analyst' -Outcome 'noop' `
        -Message 'BotDefinition Reckless_Analyst_Employee already exists.'
} else {
    Write-Host '  Publishing Reckless_Analyst_Employee authoring bundle (max 10 min)...'
    Push-Location $salesforceRoot
    try {
        $exit = Invoke-OrgSetupNativeWithTimeout -FilePath $sf -TimeoutSeconds 600 -Arguments @(
            'agent','publish','authoring-bundle',
            '--target-org', $Alias,
            '--api-name',   'Reckless_Analyst_Employee',
            '--skip-retrieve'
        )
    } finally {
        Pop-Location
    }
    if ($exit -ne 0) {
        $warnPub = 'sf agent publish authoring-bundle exited ' + $exit + '. Publish manually: cd salesforce; sf agent publish authoring-bundle --target-org ' + $Alias + ' --api-name Reckless_Analyst_Employee --skip-retrieve'
        Add-OrgSetupWarning -Alias $Alias -Step 'n-reckless-analyst' -Message $warnPub
        Add-OrgSetupLogEntry -Alias $Alias -Step 'n-reckless-analyst' -Outcome 'skipped' `
            -Message 'Authoring-bundle publish failed or timed out; see warning.'
        return
    }

    Write-Host '  Agent published.' -ForegroundColor Green
    Write-Host '  Activating Reckless_Analyst_Employee (version 1, max 5 min)...'
    Push-Location $salesforceRoot
    try {
        $exit = Invoke-OrgSetupNativeWithTimeout -FilePath $sf -TimeoutSeconds 300 -Arguments @(
            'agent','activate',
            '--target-org', $Alias,
            '--api-name',   'Reckless_Analyst_Employee',
            '--version',    '1'
        )
    } finally {
        Pop-Location
    }
    if ($exit -ne 0) {
        $warnAct = 'Agent published but activation failed. Activate manually: sf agent activate --target-org ' + $Alias + ' --api-name Reckless_Analyst_Employee'
        Add-OrgSetupWarning -Alias $Alias -Step 'n-reckless-analyst' -Message $warnAct
        Add-OrgSetupLogEntry -Alias $Alias -Step 'n-reckless-analyst' -Outcome 'completed' `
            -Message 'Agent published; activation needs manual follow-up.'
        return
    }

    Write-Host '  Agent activated.' -ForegroundColor Green
    Add-OrgSetupLogEntry -Alias $Alias -Step 'n-reckless-analyst' -Outcome 'completed' `
        -Message 'Published and activated Reckless_Analyst_Employee.'
}

# ── 2. Deploy permission set ──────────────────────────────────────────────────

Write-Host '  Deploying Reckless_Analyst_Access permission set...'
Push-Location $salesforceRoot
try {
    $exit = Invoke-OrgSetupNative -FilePath $sf -Arguments @(
        'project','deploy','start',
        '--target-org',  $Alias,
        '--metadata',    'PermissionSet:Reckless_Analyst_Access',
        '--api-version', '66.0'
    )
} finally {
    Pop-Location
}
if ($exit -ne 0) {
    $warnDeploy = 'Permission set deploy failed (exit ' + $exit + '). Deploy manually: cd salesforce; sf project deploy start --target-org ' + $Alias + ' --metadata PermissionSet:Reckless_Analyst_Access --api-version 66.0'
    Add-OrgSetupWarning -Alias $Alias -Step 'n-reckless-analyst' -Message $warnDeploy
    Add-OrgSetupLogEntry -Alias $Alias -Step 'n-reckless-analyst' -Outcome 'skipped' `
        -Message 'Reckless_Analyst_Access permset deploy failed.'
    Write-Host '  FAILED: permission set deploy (see warning).' -ForegroundColor Red
    return
}
Write-Host '  Reckless_Analyst_Access permission set deployed.' -ForegroundColor Green

# ── 3. Grant agent access via SetupEntityAccess ───────────────────────────────
Write-Host '  Granting Reckless_Analyst_Access -> Reckless_Analyst_Employee...'

$ps = Invoke-OrgSetupSoql -Auth $auth -Soql `
    "SELECT Id FROM PermissionSet WHERE Name = 'Reckless_Analyst_Access'"
if (-not $ps.records -or $ps.records.Count -lt 1) {
    $warnPs = 'Reckless_Analyst_Access permset not found after deploy. Grant agent access manually in Setup > Permission Sets.'
    Add-OrgSetupWarning -Alias $Alias -Step 'n-reckless-analyst' -Message $warnPs
    Add-OrgSetupLogEntry -Alias $Alias -Step 'n-reckless-analyst' -Outcome 'skipped' `
        -Message 'Reckless_Analyst_Access not found post-deploy.'
    return
}
$psId = $ps.records[0].Id

$bot = Invoke-OrgSetupSoql -Auth $auth -Soql `
    "SELECT Id FROM BotDefinition WHERE DeveloperName = 'Reckless_Analyst_Employee'"
if (-not $bot.records -or $bot.records.Count -lt 1) {
    Add-OrgSetupWarning -Alias $Alias -Step 'n-reckless-analyst' `
        -Message 'BotDefinition Reckless_Analyst_Employee not found after publish. Grant agent access manually.'
    Add-OrgSetupLogEntry -Alias $Alias -Step 'n-reckless-analyst' -Outcome 'skipped' `
        -Message 'BotDefinition missing post-publish.'
    return
}
$botId = $bot.records[0].Id

$existingAccess = $null
try {
    $existingAccess = Invoke-OrgSetupSoql -Auth $auth -Soql `
        "SELECT Id FROM SetupEntityAccess WHERE ParentId = '$psId' AND SetupEntityId = '$botId'"
} catch {}

if ($existingAccess -and $existingAccess.records -and $existingAccess.records.Count -gt 0) {
    Write-Host '  Agent access already granted -- skipping.' -ForegroundColor Cyan
} else {
    $result = Invoke-OrgSetupRest -Auth $auth -Method POST `
        -Path "/services/data/$api/sobjects/SetupEntityAccess" `
        -Body @{ ParentId = $psId; SetupEntityId = $botId } `
        -AllowErrorStatus

    $isErr = $false
    try { $isErr = [bool]$result._error } catch {}
    if ($isErr) {
        $warnAccess = 'SetupEntityAccess insert failed. Grant manually: Setup > Permission Sets > Reckless_Analyst_Access > Agent Access > Edit > select Reckless Analyst > Save.'
        Add-OrgSetupWarning -Alias $Alias -Step 'n-reckless-analyst' -Message $warnAccess
        Add-OrgSetupLogEntry -Alias $Alias -Step 'n-reckless-analyst' -Outcome 'skipped' `
            -Message 'SetupEntityAccess insert failed; see warning.'
        return
    }
}

# ── 4. Assign permission set to running user ──────────────────────────────────

$existingPsAssign = $null
try {
    $existingPsAssign = Invoke-OrgSetupSoql -Auth $auth -Soql `
        "SELECT Id FROM PermissionSetAssignment WHERE Assignee.Username = '$($auth.Username)' AND PermissionSet.Name = 'Reckless_Analyst_Access'"
} catch {}

if ($existingPsAssign -and $existingPsAssign.records -and $existingPsAssign.records.Count -gt 0) {
    Write-Host '  Reckless_Analyst_Access already assigned to running user -- skipping.' -ForegroundColor Cyan
} else {
    Write-Host '  Assigning Reckless_Analyst_Access to running user...'
    Push-Location $salesforceRoot
    try {
        $exit = Invoke-OrgSetupNative -FilePath $sf -Arguments @(
            'org','assign','permset',
            '--target-org', $Alias,
            '--name',       'Reckless_Analyst_Access'
        )
    } finally {
        Pop-Location
    }
    if ($exit -ne 0) {
        $warnAssign = 'Permission set assignment failed (exit ' + $exit + '). Assign manually: Setup > Users > [your user] > Permission Set Assignments > Edit > add Reckless_Analyst_Access.'
        Add-OrgSetupWarning -Alias $Alias -Step 'n-reckless-analyst' -Message $warnAssign
    }
}

Add-OrgSetupLogEntry -Alias $Alias -Step 'n-reckless-analyst' -Outcome 'completed' `
    -Message 'Reckless Analyst agent deployed, activated, access granted, and permset assigned.'
Write-Host '  Reckless Analyst agent ready. It will appear in the Concierge sidebar dropdown.' -ForegroundColor Green
Write-Host '  [n] Done.' -ForegroundColor Green
