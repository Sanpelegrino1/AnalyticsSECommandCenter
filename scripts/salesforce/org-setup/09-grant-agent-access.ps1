# OrgSetup step (l) -- grant Access_Analytics_Agent permission set access to the
# Analytics_and_Visualization agent.
#
# Uses SetupEntityAccess insert (Tooling API). This is the safer route than
# editing the PermissionSet metadata XML because the bot-access element name
# varies across API versions.
#
# Idempotent: checks for existing SetupEntityAccess first.
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
Write-Host '--- [l] Grant agent access to Access_Analytics_Agent permset ---'

$auth = Get-OrgSetupAuth -Alias $Alias
$api = Get-OrgSetupApiVersion

Write-Host '  Looking up Access_Analytics_Agent permission set...'
$ps = Invoke-OrgSetupSoql -Auth $auth -Soql `
    "SELECT Id FROM PermissionSet WHERE Name = 'Access_Analytics_Agent'"
if (-not $ps.records -or $ps.records.Count -lt 1) {
    Add-OrgSetupWarning -Alias $Alias -Step 'l-grant-agent-access' `
        -Message "Permission set Access_Analytics_Agent not found. Run step 03 (deploy permsets) first, then rerun."
    Add-OrgSetupLogEntry -Alias $Alias -Step 'l-grant-agent-access' -Outcome 'skipped' `
        -Message 'Access_Analytics_Agent missing.'
    return
}
$psId = $ps.records[0].Id

Write-Host '  Looking up Analytics_and_Visualization agent...'
$bot = $null
try {
    $bot = Invoke-OrgSetupSoql -Auth $auth -Soql `
        "SELECT Id FROM BotDefinition WHERE DeveloperName = 'Analytics_and_Visualization'"
} catch {
    Add-OrgSetupWarning -Alias $Alias -Step 'l-grant-agent-access' `
        -Message "BotDefinition sObject not available ($($_.Exception.Message)). Create the agent first (step 08), then rerun."
    Add-OrgSetupLogEntry -Alias $Alias -Step 'l-grant-agent-access' -Outcome 'skipped' `
        -Message 'BotDefinition query failed.'
    return
}
if (-not $bot.records -or $bot.records.Count -lt 1) {
    $warnMsg = "BotDefinition Analytics_and_Visualization not found. Create it first via step 08 or in Setup > Agentforce Agents."
    Add-OrgSetupWarning -Alias $Alias -Step 'l-grant-agent-access' -Message $warnMsg
    Add-OrgSetupLogEntry -Alias $Alias -Step 'l-grant-agent-access' -Outcome 'skipped' `
        -Message 'Analytics_and_Visualization agent missing.'
    return
}
$botId = $bot.records[0].Id

$existing = $null
try {
    $existing = Invoke-OrgSetupSoql -Auth $auth -Soql `
        "SELECT Id FROM SetupEntityAccess WHERE ParentId = '$psId' AND SetupEntityId = '$botId'"
} catch {
    # SOQL against SetupEntityAccess can 400 on some entity types. If so we just
    # skip the pre-check and attempt the insert; duplicate inserts will also fail.
}
if ($existing -and $existing.records -and $existing.records.Count -gt 0) {
    Write-Host '  Agent access already granted — skipping.' -ForegroundColor Cyan
    Add-OrgSetupLogEntry -Alias $Alias -Step 'l-grant-agent-access' -Outcome 'noop' `
        -Message 'Agent access already granted to permission set.'
    return
}

Write-Host '  Granting Access_Analytics_Agent -> Analytics_and_Visualization...'

# SetupEntityAccess is a data sObject. SetupEntityType is NOT writable on insert
# (INVALID_FIELD_FOR_INSERT_UPDATE); the platform infers it from the SetupEntityId
# key prefix. Just POST ParentId + SetupEntityId.
$body = @{
    ParentId      = $psId
    SetupEntityId = $botId
}
$result = Invoke-OrgSetupRest -Auth $auth -Method POST `
    -Path "/services/data/$api/sobjects/SetupEntityAccess" -Body $body `
    -AllowErrorStatus

$isErr = $false
try { $isErr = [bool]$result._error } catch {}
if ($isErr) {
    $warnMsg2 = "SetupEntityAccess insert failed. Grant manually: Setup > Permission Sets > Access Analytics Agent > Agent Access > Edit > select Analytics and Visualization > Save."
    Add-OrgSetupWarning -Alias $Alias -Step 'l-grant-agent-access' -Message $warnMsg2
    Add-OrgSetupLogEntry -Alias $Alias -Step 'l-grant-agent-access' -Outcome 'skipped' `
        -Message 'Grant via SetupEntityAccess failed; see warning for manual step.'
    return
}

Add-OrgSetupLogEntry -Alias $Alias -Step 'l-grant-agent-access' -Outcome 'completed' `
    -Message "Granted Access_Analytics_Agent -> Analytics_and_Visualization."
Write-Host '  Agent access granted.' -ForegroundColor Green
Write-Host '  [l] Done.' -ForegroundColor Green
