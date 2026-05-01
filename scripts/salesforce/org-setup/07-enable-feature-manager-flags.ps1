# OrgSetup step (g) -- Data Cloud Feature Manager flags.
#
# Target features (per the PACE guide):
#   - Semantic Authoring AI
#   - Connectors (Beta)
#   - Accelerated Data Ingest
#   - Code Extension
#   - Content Tagging
#
# These features have no public REST API. Two paths are offered:
#   1. Headless browser (Python + Playwright) -- auto-installs if needed, flips
#      all toggles programmatically.
#   2. Manual -- opens the Feature Manager page in the browser so the user can
#      flip them in about 30 seconds.
#
# Idempotent: skips entirely if already recorded in the state file.
#
# Inputs:  -Alias  (required)

param(
    [Parameter(Mandatory = $true)]
    [string]$Alias
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'lib\OrgSetup.Common.ps1')
. (Join-Path $PSScriptRoot 'lib\OrgSetup.Playwright.ps1')

Write-Host ''
Write-Host '--- [g] Feature Manager flags ---'

$state = Read-OrgSetupState -Alias $Alias
if (@($state.completed) -contains 'g-feature-editor') {
    Write-Host '  Already completed -- skipping.' -ForegroundColor Cyan
    return
}

$targetFeatures = @(
    'Semantic Authoring AI',
    'Connectors',
    'Accelerated Data Ingest',
    'Code Extension',
    'Content Tagging',
    'Notebook AI'
)

$auth = Get-OrgSetupAuth -Alias $Alias
$featureManagerUrl = "$($auth.InstanceUrl)/lightning/setup/BetaFeaturesSetup/home"

Write-Host ''
Write-Host '  There are Data Cloud Feature Manager flags that currently have no' -ForegroundColor Cyan
Write-Host '  REST endpoint for us to turn on automatically:' -ForegroundColor Cyan
Write-Host ''
foreach ($f in $targetFeatures) { Write-Host "    - $f" }
Write-Host ''
Write-Host '  We can flip these for you using a headless browser, but it requires'
Write-Host '  Python + Playwright to be installed (we will install them if needed).'
Write-Host '  Alternatively, you can flip them yourself on a single Setup page -- takes about 30 seconds.'
Write-Host ''
Write-Host '  [1] Install Python + Playwright (if needed) and flip automatically'
Write-Host '  [2] Open the Feature Manager page so I can flip them myself'
Write-Host '  [3] Skip for now (I will do this later)'
Write-Host ''

$choice = Read-Host '  Your choice (1/2/3)'

switch ($choice.Trim()) {
    '1' {
        Write-Host ''
        Write-Host '  Checking Python + Playwright...' -ForegroundColor Cyan
        $python = Assert-PythonAndPlaywright
        if (-not $python) {
            Write-Host '  Could not set up Python/Playwright. Falling back to manual path.' -ForegroundColor Yellow
            Write-Host "  Opening Feature Manager: $featureManagerUrl" -ForegroundColor Cyan
            Start-Process $featureManagerUrl
            Add-OrgSetupWarning -Alias $Alias -Step 'g-feature-editor' `
                -Message "Python/Playwright unavailable. Feature Manager opened in browser. Enable manually: $($targetFeatures -join ', ')."
            Add-OrgSetupLogEntry -Alias $Alias -Step 'g-feature-editor' -Outcome 'skipped' `
                -Message 'Python/Playwright setup failed; browser opened for manual completion.'
            Write-Host '  [g] Done (manual fallback).' -ForegroundColor Yellow
            return
        }

        $flipResult = Invoke-FeatureManagerHeadless -Auth $auth -Features $targetFeatures -Python $python

        if (-not $flipResult) {
            Write-Host '  Headless flip failed -- no result returned. Opening browser as fallback.' -ForegroundColor Yellow
            Start-Process $featureManagerUrl
            Add-OrgSetupWarning -Alias $Alias -Step 'g-feature-editor' `
                -Message "Headless flip returned no result. Feature Manager opened in browser. Enable manually: $($targetFeatures -join ', ')."
            Add-OrgSetupLogEntry -Alias $Alias -Step 'g-feature-editor' -Outcome 'skipped' `
                -Message 'Headless flip failed; browser opened for manual completion.'
            Write-Host '  [g] Done (manual fallback).' -ForegroundColor Yellow
            return
        }

        # Special case: Feature Manager page rendered no feature cards (fresh org, DC still settling)
        $reasonProp = $flipResult.PSObject.Properties['reason']
        if ($reasonProp -and $reasonProp.Value -eq 'page_not_ready') {
            Write-Host ''
            Write-Host '  Data Cloud Feature Manager page had no features rendered yet.' -ForegroundColor Yellow
            Write-Host '  This is common on fresh orgs -- the feature list takes a few minutes to populate' -ForegroundColor Yellow
            Write-Host '  after Data Cloud provisioning completes. Rerun the setup script in 5-10 minutes' -ForegroundColor Yellow
            Write-Host '  and this step will pick up where it left off.' -ForegroundColor Yellow
            Write-Host ''
            Add-OrgSetupLogEntry -Alias $Alias -Step 'g-feature-editor' -Outcome 'skipped' `
                -Message 'Feature Manager page had no features rendered yet; rerun setup in a few minutes.'
            Write-Host '  [g] Deferred -- rerun setup shortly.' -ForegroundColor Yellow
            return
        }

        $succeeded = @()
        $failed    = @()
        foreach ($r in $flipResult.results) {
            if ($r.status -in @('enabled','already_enabled')) {
                Write-Host "    $($r.feature): $($r.message)" -ForegroundColor Green
                $succeeded += $r.feature
            } else {
                Write-Host "    $($r.feature): $($r.message)" -ForegroundColor Yellow
                $failed += $r.feature
                $warnMsg = "Headless flip failed ($($r.status)): $($r.message). Enable manually in Setup > Data Cloud > Feature Editor."
                Add-OrgSetupWarning -Alias $Alias -Step 'g-feature-editor' -Feature $r.feature -Message $warnMsg
            }
        }

        if ($failed.Count -eq 0) {
            Add-OrgSetupLogEntry -Alias $Alias -Step 'g-feature-editor' -Outcome 'completed' `
                -Message "Headless browser enabled: $($succeeded -join ', ')."
            Write-Host '  All features enabled via headless browser.' -ForegroundColor Green
        } else {
            Add-OrgSetupLogEntry -Alias $Alias -Step 'g-feature-editor' -Outcome 'completed' `
                -Message "Headless enabled: $($succeeded -join ', '). Failed: $($failed -join ', ')."
            Write-Host "  $($failed.Count) feature(s) need manual follow-up (see warnings)." -ForegroundColor Yellow
        }
    }

    '2' {
        Write-Host ''
        Write-Host "  Opening Feature Manager in your browser..." -ForegroundColor Cyan
        Write-Host "  URL: $featureManagerUrl"
        Start-Process $featureManagerUrl
        Write-Host ''
        Write-Host '  Please enable the following features, then press Enter to continue:' -ForegroundColor Yellow
        foreach ($f in $targetFeatures) { Write-Host "    - $f" -ForegroundColor Yellow }
        Read-Host '  Press Enter once you have enabled the features'

        Add-OrgSetupLogEntry -Alias $Alias -Step 'g-feature-editor' -Outcome 'completed' `
            -Message "User manually enabled features via browser: $($targetFeatures -join ', ')."
        Write-Host '  Marked as complete.' -ForegroundColor Green
    }

    default {
        Write-Host '  Skipping -- adding to manual follow-up list.' -ForegroundColor Yellow
        foreach ($f in $targetFeatures) {
            $warnMsg2 = "Enable manually: Setup > Data Cloud > Feature Editor. No public API exists for this toggle."
            Add-OrgSetupWarning -Alias $Alias -Step 'g-feature-editor' -Feature $f -Message $warnMsg2
        }
        Add-OrgSetupLogEntry -Alias $Alias -Step 'g-feature-editor' -Outcome 'skipped' `
            -Message "User chose to skip. $($targetFeatures.Count) feature(s) need manual enablement."
    }
}

Write-Host '  [g] Done.' -ForegroundColor Green
