# OrgSetup -- full org setup in one script.
#
# Run once. If Data Cloud is still provisioning, the script exits cleanly and
# tells you to rerun -- all completed steps are saved and skipped on rerun.
#
# Optional features are offered interactively at the start of each run
# (only when they haven't already been completed for this org).
#
# Steps (in order):
#   (a)   Enable Data Cloud
#   (b)   Enable Einstein / Generative AI
#   (d)   Deploy Access_Analytics_Agent permission set
#   (11)  Deploy CommandCenterAuth connected app  [-NoConnectedApp to skip]
#   [DC gate]
#   (e)   Deploy + assign Tableau_Next_Admin_PSG
#   (f/i) Enable Tableau Next + Agentforce toggles
#   (g)   Feature Manager flags (headless browser or manual)
#   (h)   Enable SLDS v2 dark mode
#   (k)   Create + activate Analytics and Visualization agent
#   (l)   Grant Access_Analytics_Agent -> agent access
#   (o)   Register Tableau Cloud sites (Salesforce side)
#   [opt] Heroku PostgreSQL connector (interactive)
#   [opt] Reckless Analyst Employee agent (interactive)
#   [opt] PACE / PACE-NEXUS Tableau trust + user (interactive, PAT-prompted)
#
# Inputs:
#   -Alias            (optional) -- SF CLI alias; prompts to pick/login if omitted
#   -NoConnectedApp   (optional) -- skip CommandCenterAuth connected app deploy

param(
    [string]$Alias = '',
    [switch]$NoConnectedApp,
    [string]$PacePatName   = '',
    [string]$PacePatSecret = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

. (Join-Path $PSScriptRoot 'lib\OrgSetup.Common.ps1')
. (Join-Path $PSScriptRoot 'lib\OrgSetup.HtmlReport.ps1')

Write-Host ''
Write-Host '========================================='
Write-Host '=== Salesforce Org Setup ==='
Write-Host '========================================='
Write-Host ''

Assert-SalesforceCli

# ── Org selection ─────────────────────────────────────────────────────────────
if (-not $Alias) {
    Write-Host 'Checking for authenticated Salesforce orgs...'
    $previousEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $orgListRaw = & sf org list --json 2>&1
    $ErrorActionPreference = $previousEap

    $orgList = $null
    try {
        $jsonText = ($orgListRaw | ForEach-Object { $_.ToString() }) -join "`n"
        $startIdx = $jsonText.IndexOf('{')
        if ($startIdx -ge 0) {
            $orgList = ($jsonText.Substring($startIdx) | ConvertFrom-Json).result
        }
    } catch {}

    $nonScratch = @()
    if ($orgList) {
        $nonScratch += @($orgList.nonScratchOrgs) | Where-Object { $_ -and $_.connectedStatus -eq 'Connected' }
    }

    if ($nonScratch.Count -gt 0) {
        Write-Host ''
        Write-Host 'Authenticated orgs:' -ForegroundColor Cyan
        for ($i = 0; $i -lt $nonScratch.Count; $i++) {
            $org = $nonScratch[$i]
            $aliasLabel = if ($org.alias) { $org.alias } else { '(no alias)' }
            Write-Host ("  [{0}] {1}  ({2})" -f ($i + 1), $aliasLabel, $org.username)
        }
        Write-Host ("  [{0}] Log in to a new org" -f ($nonScratch.Count + 1))
        Write-Host ''
        $choice = Read-Host "Select an org (1-$($nonScratch.Count + 1))"
        $choiceInt = 0
        [int]::TryParse($choice, [ref]$choiceInt) | Out-Null

        if ($choiceInt -ge 1 -and $choiceInt -le $nonScratch.Count) {
            $selected = $nonScratch[$choiceInt - 1]
            $Alias = if ($selected.alias) { $selected.alias } else { $selected.username }
            Write-Host "Using org: $Alias" -ForegroundColor Green
        } else {
            $Alias = ''
        }
    }

    if (-not $Alias) {
        Write-Host ''
        Write-Host 'No org selected. Opening browser login...' -ForegroundColor Cyan
        $loginAlias = Read-Host "Enter a short alias for this org (e.g. MY-DEMO-ORG)"
        if (-not $loginAlias) { throw 'An alias is required to continue.' }
        $previousEap2 = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        & sf org login web --alias $loginAlias 2>&1 | ForEach-Object { Write-Host $_ }
        $loginExit = $LASTEXITCODE
        $ErrorActionPreference = $previousEap2
        if ($loginExit -ne 0) { throw "Login failed (exit $loginExit). Rerun the script and try again." }
        $Alias = $loginAlias
        Write-Host "Logged in as: $Alias" -ForegroundColor Green
    }
}

Write-Host ''
Write-Host "Setting up org: $Alias"
Write-Host "State file:     $(Get-OrgSetupStatePath -Alias $Alias)"
Write-Host ''

# ── Optional feature prompts (skipped if already completed for this org) ──────

$existingState = Read-OrgSetupState -Alias $Alias
$alreadyDone   = @($existingState.completed)

Write-Host '-----------------------------------------'
Write-Host '  Optional features'
Write-Host '-----------------------------------------'
Write-Host ''

# Heroku
$doHeroku = $false
if ($alreadyDone -contains 'm-heroku-connector') {
    Write-Host '  [Heroku connector]  Already set up.' -ForegroundColor Cyan
} else {
    Write-Host '  Heroku Connector: Adds a shared PostgreSQL data source from the PACE ICE'
    Write-Host '  curriculum into Data Cloud as an external connector.' -ForegroundColor DarkGray
    $ans = Read-Host '  Set up Heroku connector? (y/N)'
    $doHeroku = $ans -match '^[Yy]'
    Write-Host ''
}

# Reckless Analyst agent
$doAgent = $false
if ($alreadyDone -contains 'n-reckless-analyst') {
    Write-Host '  [Reckless Analyst]  Already deployed.' -ForegroundColor Cyan
} else {
    Write-Host '  Reckless Analyst Agent: A custom analytics sidebar agent with faster'
    Write-Host '  responses, fewer guardrails, and no inline chart generation -- runs'
    Write-Host '  alongside the default Analytics and Visualization agent.' -ForegroundColor DarkGray
    $ans = Read-Host '  Deploy Reckless Analyst agent? (y/N)'
    $doAgent = $ans -match '^[Yy]'
    Write-Host ''
}

# PACE / PACE-NEXUS Tableau trust
$doTrust  = $false
$patName   = ''
$patSecret = $null
if ($alreadyDone -contains 'p-pace-trust') {
    Write-Host '  [PACE trust]  Already configured.' -ForegroundColor Cyan
} else {
    Write-Host '  PACE & PACE-NEXUS Tableau Embedding: Registers this Salesforce org as a'
    Write-Host '  trusted identity provider on both Tableau sites so embedded dashboards'
    Write-Host '  can authenticate using Salesforce-signed tokens. Also adds your Salesforce'
    Write-Host '  user to both sites (Explorer role, Tableau ID + MFA auth).' -ForegroundColor DarkGray
    if ($PacePatName -and $PacePatSecret) {
        $patName   = $PacePatName
        $patSecret = $PacePatSecret
        $doTrust   = $true
        Write-Host '  Using PAT provided on command line.' -ForegroundColor DarkGray
    } else {
        $ans = Read-Host '  Set up Tableau embedding for PACE and PACE-NEXUS? (y/N)'
        if ($ans -match '^[Yy]') {
            Write-Host ''
            Write-Host '  Provide a Personal Access Token from your Tableau account.'
            Write-Host '  You can create one at: Profile menu > My Account Settings > Personal Access Tokens' -ForegroundColor DarkGray
            Write-Host '  Tip: right-click to paste in this terminal.' -ForegroundColor DarkGray
            Write-Host ''
            $patName = Read-Host '  PAT Name'
            Write-Host -NoNewline '  PAT Secret: '
            $patSecret = ''
            while ($true) {
                $key = [Console]::ReadKey($true)
                if ($key.Key -eq 'Enter') { Write-Host ''; break }
                if ($key.Key -eq 'Backspace') {
                    if ($patSecret.Length -gt 0) {
                        $patSecret = $patSecret.Substring(0, $patSecret.Length - 1)
                        Write-Host -NoNewline "`b `b"
                    }
                } else {
                    $patSecret += $key.KeyChar
                    Write-Host -NoNewline '*'
                }
            }
            if ($patName -and $patSecret) {
                $doTrust = $true
            } else {
                Write-Host '  PAT name or secret was empty -- skipping Tableau trust setup.' -ForegroundColor Yellow
            }
        }
    }
    Write-Host ''
}

Write-Host '-----------------------------------------'
Write-Host ''

$runStart = Get-UtcTimestamp
$stepsDir = $PSScriptRoot

# ── Pre-DC steps (no DC dependency) ──────────────────────────────────────────
& (Join-Path $stepsDir '01-enable-data-cloud.ps1')       -Alias $Alias
& (Join-Path $stepsDir '02-enable-einstein.ps1')         -Alias $Alias
& (Join-Path $stepsDir '03-deploy-permsets-and-psg.ps1') -Alias $Alias

if (-not $NoConnectedApp) {
    & (Join-Path $stepsDir '11-deploy-connected-app.ps1') -Alias $Alias
}

# ── Data Cloud gate ───────────────────────────────────────────────────────────
Write-Host ''
Write-Host '--- [c/j] Checking Data Cloud readiness ---'

$auth = Get-OrgSetupAuth -Alias $Alias

$dcState = Read-OrgSetupState -Alias $Alias
$dcReady = @($dcState.completed) -contains 'c-j-data-cloud-ready'

if ($dcReady) {
    Write-Host '  Already confirmed in a previous run -- skipping check.' -ForegroundColor Cyan
} else {
    try {
        $dcReady = Test-OrgSetupDataCloudReady -Auth $auth
    } catch {
        Write-Host "  Could not check DC status: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

if (-not $dcReady) {
    Write-Host ''
    Write-Host '  Data Cloud is not ready yet.' -ForegroundColor Yellow
    Write-Host '  This is normal for new orgs -- provisioning typically takes 5-30 minutes.' -ForegroundColor Yellow
    Write-Host ''
    Write-Host '  Steps completed so far have been saved. When Data Cloud is ready,' -ForegroundColor Cyan
    Write-Host '  rerun this same script and it will pick up from here:' -ForegroundColor Cyan
    Write-Host ''

    $rerunCmd = 'powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/run-setup.ps1 -Alias ' + $Alias
    if ($NoConnectedApp) { $rerunCmd += ' -NoConnectedApp' }
    Write-Host "    $rerunCmd" -ForegroundColor White
    Write-Host ''
    Write-Host '  You can check Data Cloud status in Setup > Data Cloud Setup > Home.' -ForegroundColor Yellow
    Write-Host ''

    Add-OrgSetupLogEntry -Alias $Alias -Step 'c-j-data-cloud-ready' -Outcome 'skipped' `
        -Message 'Data Cloud not yet provisioned; user must rerun run-setup.ps1 when ready.'
    Write-OrgSetupRunSummary -Alias $Alias -Since $runStart
    exit 0
}

Write-Host '  Data Cloud is live.' -ForegroundColor Green
Add-OrgSetupLogEntry -Alias $Alias -Step 'c-j-data-cloud-ready' -Outcome 'completed' `
    -Message 'Data Cloud tenant is live.'

# ── Post-DC steps ─────────────────────────────────────────────────────────────
& (Join-Path $stepsDir '03b-deploy-psg.ps1')                  -Alias $Alias
& (Join-Path $stepsDir '04-assign-psg-to-self.ps1')           -Alias $Alias

& (Join-Path $stepsDir '06-enable-tableau-next.ps1')          -Alias $Alias
& (Join-Path $stepsDir '07-enable-feature-manager-flags.ps1') -Alias $Alias

& (Join-Path $stepsDir '12-enable-dark-mode.ps1')             -Alias $Alias

& (Join-Path $stepsDir '08-create-analytics-agent.ps1')       -Alias $Alias
& (Join-Path $stepsDir '09-grant-agent-access.ps1')           -Alias $Alias

& (Join-Path $stepsDir '14-register-tableau-sites.ps1')       -Alias $Alias

if ($doHeroku) {
    & (Join-Path $stepsDir '10-create-heroku-connector.ps1') -Alias $Alias
}

if ($doAgent) {
    & (Join-Path $stepsDir '13-deploy-reckless-analyst-agent.ps1') -Alias $Alias
}

if ($doTrust) {
    & (Join-Path $stepsDir '15-register-tableau-trust.ps1') `
        -Alias $Alias -PatName $patName -PatSecret $patSecret
}

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ''
Write-Host '========================================='
Write-Host '=== Setup complete ==='
Write-Host '========================================='
Write-OrgSetupRunSummary -Alias $Alias -Since $runStart
Write-Host ''
Write-Host '  Opening setup report in browser...' -ForegroundColor Cyan
Write-OrgSetupHtmlReport -Alias $Alias -Since $runStart -Open
