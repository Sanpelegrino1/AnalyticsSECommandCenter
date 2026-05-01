# OrgSetup step (k) -- create + activate the Analytics and Visualization agent.
#
# Uses `sf agent create` with a hand-authored spec YAML matching the guide's
# four fields (Name, API, Role, Company) and three topics (Data Analysis,
# Data Alert Management, Data Pro).
#
# Idempotent: checks for existing BotDefinition first.
# Requires: step (b) completed (Einstein on).
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
Write-Host '--- [k] Create + activate Analytics and Visualization agent ---'

$auth = Get-OrgSetupAuth -Alias $Alias

# BotDefinition only becomes a valid sObject after Agentforce (step f/i master
# toggle = enableBots) is enabled. If that hasn't happened, the pre-check query
# 400s -- emit a warning and bail gracefully.
Write-Host '  Checking for existing Analytics_and_Visualization agent...'
$existing = $null
try {
    $existing = Invoke-OrgSetupSoql -Auth $auth -Soql `
        "SELECT Id, DeveloperName FROM BotDefinition WHERE DeveloperName = 'Analytics_and_Visualization'"
} catch {
    $warnMsg = "BotDefinition is not yet a valid sObject ($($_.Exception.Message)). Run step 06 first (enableBots) or create the agent manually in Agentforce Agents > New Agent > Analytics and Visualization template."
    Add-OrgSetupWarning -Alias $Alias -Step 'k-create-agent' -Message $warnMsg
    Add-OrgSetupLogEntry -Alias $Alias -Step 'k-create-agent' -Outcome 'skipped' `
        -Message 'BotDefinition unavailable; Agentforce likely not enabled.'
    Write-Host '  SKIPPED: BotDefinition unavailable — Agentforce not yet enabled (see warning).' -ForegroundColor Yellow
    return
}

if ($existing -and $existing.records -and $existing.records.Count -gt 0) {
    Write-Host '  Already exists — skipping create.' -ForegroundColor Cyan
    Add-OrgSetupLogEntry -Alias $Alias -Step 'k-create-agent' -Outcome 'noop' `
        -Message 'BotDefinition Analytics_and_Visualization already exists.'
    return
}

$sf = Get-RequiredCommandPath -Name 'sf' -Hint 'Install Salesforce CLI.'
$specDir = Resolve-CommandCenterPath 'salesforce/specs'
Ensure-Directory -Path $specDir
$specPath = Join-Path $specDir 'analytics-and-visualization-agent.yaml'

# Hand-author the spec per guide: Analytics and Visualization template, 3 topics.
# Exact field schema for `sf agent create --spec` is CLI-version-dependent; this
# mirrors what the Analytics and Visualization template produces in the UI.
$spec = @"
agentType: internal
role: Analytic Agent
companyName: Salesforce
companyDescription: Salesforce, the Customer Company, helps organizations of every size and industry put the customer at the center of everything they do.
companyWebsite: https://www.salesforce.com
maxNumOfTopics: 3
enrichLogs: false
tone: casual
topics:
  - name: Data Analysis
    description: Analyze data using Tableau Next and answer user questions about metrics, trends, and dashboards.
  - name: Data Alert Management
    description: Create and manage proactive data alerts for key metrics.
  - name: Data Pro
    description: Help users create calculated fields by describing them in natural language.
"@
Set-Content -Path $specPath -Value $spec -Encoding UTF8

$salesforceRoot = Resolve-CommandCenterPath 'salesforce'
Push-Location $salesforceRoot
try {
    Write-Host "  Creating agent from spec..."
    $exit = Invoke-OrgSetupNative -FilePath $sf -Arguments @(
        'agent','create','--target-org',$Alias,'--spec',$specPath,
        '--name','Analytics and Visualization','--api-name','Analytics_and_Visualization'
    )
    if ($exit -ne 0) {
        $warnMsg2 = "sf agent create exited $exit. Create the agent manually: Setup > Agentforce Agents > + New Agent > Analytics and Visualization template."
        Add-OrgSetupWarning -Alias $Alias -Step 'k-create-agent' -Message $warnMsg2
        Add-OrgSetupLogEntry -Alias $Alias -Step 'k-create-agent' -Outcome 'skipped' `
            -Message 'sf agent create failed; see warning.'
        Write-Host '  FAILED: sf agent create returned non-zero (see warning).' -ForegroundColor Red
        return
    }
    Write-Host '  Agent created.' -ForegroundColor Green

    # --version is required to avoid an interactive prompt when only one version exists.
    # A brand-new agent created by sf agent create always starts at version 1.
    Write-Host '  Activating agent (version 1)...'
    $exit = Invoke-OrgSetupNative -FilePath $sf -Arguments @(
        'agent','activate','--target-org',$Alias,'--api-name','Analytics_and_Visualization','--version','1'
    )
    if ($exit -ne 0) {
        Write-Host '  First activation attempt failed; retrying via deactivate+activate...' -ForegroundColor Yellow
        Invoke-OrgSetupNative -FilePath $sf -Arguments @(
            'agent','deactivate','--target-org',$Alias,'--api-name','Analytics_and_Visualization','--version','1'
        ) | Out-Null
        $exit = Invoke-OrgSetupNative -FilePath $sf -Arguments @(
            'agent','activate','--target-org',$Alias,'--api-name','Analytics_and_Visualization','--version','1'
        )
        if ($exit -ne 0) {
            Add-OrgSetupWarning -Alias $Alias -Step 'k-create-agent' `
                -Message 'Agent created but activation failed after deactivate+activate retry. Activate manually: Setup > Agentforce Agents > Analytics and Visualization > Activate.'
            Add-OrgSetupLogEntry -Alias $Alias -Step 'k-create-agent' -Outcome 'completed' `
                -Message 'Agent created; activation needs manual follow-up.'
            Write-Host '  WARNING: Agent created but activation failed (see warning).' -ForegroundColor Yellow
            return
        }
    }
    Write-Host '  Agent activated.' -ForegroundColor Green
} finally {
    Pop-Location
}

Add-OrgSetupLogEntry -Alias $Alias -Step 'k-create-agent' -Outcome 'completed' `
    -Message 'Created and activated Analytics_and_Visualization agent.'
Write-Host '  [k] Done.' -ForegroundColor Green
