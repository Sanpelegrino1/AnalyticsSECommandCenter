# OrgSetup step (extra) -- deploy the CommandCenterAuth external client app.
#
# Self-contained: uses only OrgSetup.Common.ps1 -- no dependency on
# CommandCenter.Common.ps1 or setup-command-center-connected-app.ps1.
#
# What it does:
#   1. Derives a unique client ID from the org ID
#   2. Stages a temp deploy with that client ID written into the OAuth settings XML
#   3. Deploys via sf project deploy start
#   4. Records the client ID in notes/registries/salesforce-orgs.json (if the org
#      is already registered there)
#
# Idempotent: skips if extra-connected-app already completed in state file.
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
Write-Host '--- [extra] Deploy CommandCenterAuth Connected App ---'

$state = Read-OrgSetupState -Alias $Alias
if (@($state.completed) -contains 'extra-connected-app') {
    Write-Host '  Already completed -- skipping.' -ForegroundColor Cyan
    return
}

$sf           = Get-RequiredCommandPath -Name 'sf' -Hint 'Install Salesforce CLI.'
$auth         = Get-OrgSetupAuth -Alias $Alias
$salesforceRoot = Resolve-CommandCenterPath 'salesforce'

# ── 1. Derive client ID from org ID ──────────────────────────────────────────
if (-not $auth.OrgId) {
    Add-OrgSetupWarning -Alias $Alias -Step 'extra-connected-app' `
        -Message 'Could not read OrgId from sf org display -- cannot derive client ID. Deploy CommandCenterAuth manually.'
    Add-OrgSetupLogEntry -Alias $Alias -Step 'extra-connected-app' -Outcome 'skipped' `
        -Message 'OrgId unavailable; skipped.'
    return
}
$safeOrgId = $auth.OrgId -replace '[^A-Za-z0-9]', ''
$clientId  = "CommandCenterAuth$safeOrgId"
Write-Host "  Client ID: $clientId" -ForegroundColor DarkGray

# ── 2. Stage deploy with client ID written into OAuth settings XML ────────────
$filesToStage = @(
    'force-app\main\default\externalClientApps\CommandCenterAuth.eca-meta.xml',
    'force-app\main\default\extlClntAppGlobalOauthSets\CommandCenterAuth_glbloauth.ecaGlblOauth-meta.xml',
    'force-app\main\default\extlClntAppOauthSettings\CommandCenterAuth_oauth.ecaOauth-meta.xml',
    'force-app\main\default\extlClntAppOauthPolicies\CommandCenterAuth_oauthPlcy.ecaOauthPlcy-meta.xml'
)

foreach ($rel in $filesToStage) {
    $abs = Join-Path $salesforceRoot $rel
    if (-not (Test-Path $abs)) {
        $warnMsg = "Missing deployment file: $rel. Ensure CommandCenterAuth metadata is present in the salesforce/ directory."
        Add-OrgSetupWarning -Alias $Alias -Step 'extra-connected-app' -Message $warnMsg
        Add-OrgSetupLogEntry -Alias $Alias -Step 'extra-connected-app' -Outcome 'skipped' `
            -Message "Missing file: $rel"
        Write-Host "  FAILED: missing file $rel" -ForegroundColor Red
        return
    }
}

$stageRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ccauth-$([guid]::NewGuid().ToString('N'))")

foreach ($rel in $filesToStage) {
    $src  = Join-Path $salesforceRoot $rel
    $dst  = Join-Path $stageRoot $rel
    $dstDir = Split-Path -Parent $dst
    New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
    Copy-Item -Path $src -Destination $dst -Force
}

# Patch the client ID into the OAuth global settings file
$oauthSetFile = Join-Path $stageRoot 'force-app\main\default\extlClntAppGlobalOauthSets\CommandCenterAuth_glbloauth.ecaGlblOauth-meta.xml'
$oauthXml = Get-Content -Path $oauthSetFile -Raw
$oauthXml = $oauthXml -replace '<consumerKey>.*?</consumerKey>', "<consumerKey>$clientId</consumerKey>"
Set-Content -Path $oauthSetFile -Value $oauthXml -Encoding UTF8

# ── 3. Deploy ─────────────────────────────────────────────────────────────────
Write-Host '  Deploying CommandCenterAuth external client app...'
$stageAppDir = Join-Path $stageRoot 'force-app'
Push-Location $salesforceRoot
try {
    $prevEap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $deployRaw = & $sf project deploy start `
        --target-org $Alias `
        --source-dir $stageAppDir `
        --json 2>&1
    $deployExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
} finally {
    Pop-Location
    Remove-Item -Path $stageRoot -Recurse -Force -ErrorAction SilentlyContinue
}

if ($deployExit -ne 0) {
    $warnMsg2 = "CommandCenterAuth deploy failed (exit $deployExit). Deploy manually: cd salesforce && sf project deploy start --target-org $Alias --source-dir force-app/main/default/externalClientApps"
    Add-OrgSetupWarning -Alias $Alias -Step 'extra-connected-app' -Message $warnMsg2
    Add-OrgSetupLogEntry -Alias $Alias -Step 'extra-connected-app' -Outcome 'failed' `
        -Message "Deploy exited $deployExit"
    Write-Host '  FAILED: deploy exited non-zero (see warning).' -ForegroundColor Red
    return
}

# Parse JSON to check for component failures
$deployText = ($deployRaw | ForEach-Object { $_.ToString() }) -join "`n"
$jsonStart  = $deployText.IndexOf('{')
if ($jsonStart -ge 0) {
    try {
        $deployResult = $deployText.Substring($jsonStart) | ConvertFrom-Json
        if ($deployResult.status -ne 0 -or ($deployResult.result -and -not $deployResult.result.success)) {
            $failures = @($deployResult.result.details.componentFailures) |
                Where-Object { $_ } |
                ForEach-Object { "$($_.fullName): $($_.problem)" }
            $warnMsg3 = "CommandCenterAuth deploy reported failures: $($failures -join '; ')"
            Add-OrgSetupWarning -Alias $Alias -Step 'extra-connected-app' -Message $warnMsg3
            Add-OrgSetupLogEntry -Alias $Alias -Step 'extra-connected-app' -Outcome 'failed' `
                -Message "Component failures: $($failures -join '; ')"
            Write-Host '  FAILED: component failures (see warning).' -ForegroundColor Red
            return
        }
    } catch {}
}

Write-Host '  CommandCenterAuth deployed.' -ForegroundColor Green

# ── 4. Record client ID in org registry if org is registered ─────────────────
try {
    $registryPath = Resolve-CommandCenterPath 'notes/registries/salesforce-orgs.json'
    if (Test-Path $registryPath) {
        $registry = Get-Content $registryPath -Raw | ConvertFrom-Json
        $entry = @($registry.orgs | Where-Object { $_.alias -eq $Alias }) | Select-Object -First 1
        if ($entry) {
            $entry | Add-Member -NotePropertyName 'dataCloudClientId' -NotePropertyValue $clientId -Force
            if (-not $entry.PSObject.Properties['dataCloudSourceName'] -or
                [string]::IsNullOrWhiteSpace($entry.dataCloudSourceName)) {
                $entry | Add-Member -NotePropertyName 'dataCloudSourceName' -NotePropertyValue 'command_center_ingest_api' -Force
            }
            $registry | ConvertTo-Json -Depth 10 | Set-Content $registryPath -Encoding UTF8
            Write-Host "  Org registry updated with client ID." -ForegroundColor DarkGray
        }
    }
} catch {
    Write-Host "  Could not update org registry: $($_.Exception.Message)" -ForegroundColor Yellow
}

Add-OrgSetupLogEntry -Alias $Alias -Step 'extra-connected-app' -Outcome 'completed' `
    -Message "Deployed CommandCenterAuth with client ID $clientId."

Write-Host ''
Write-Host '  Manual steps still required:' -ForegroundColor Yellow
Write-Host '    - Confirm app is visible in Setup > External Client App Manager' -ForegroundColor Yellow
Write-Host '    - Create the Ingestion API connector and destination data streams in Data Cloud Setup' -ForegroundColor Yellow
Write-Host '    - See playbooks/set-up-command-center-connected-app.md for the full flow' -ForegroundColor Yellow
Write-Host '  [extra] Done.' -ForegroundColor Green
