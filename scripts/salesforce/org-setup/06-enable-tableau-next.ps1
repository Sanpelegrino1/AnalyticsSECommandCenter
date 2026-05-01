# OrgSetup steps (f) + (i) -- enable Tableau Next toggles + Agentforce master toggle.
#
# Strategy: dynamic "flip every enable* boolean to true" across an allowlist of
# Settings records. Tableau Next's 7 sub-toggles live in settings records that
# only materialize after Data Cloud provisioning (step c), and new toggles land
# all the time -- rather than hardcode a list, we retrieve the records and turn
# on whatever enable* fields we find currently set to false.
#
# Settings record allowlist:
#   - Bot                (step i: enableBots = Agentforce Agents master toggle)
#   - EinsteinCopilot    (Agentforce Copilot)
#   - EinsteinAgent      (proactive recs, summarization)
#   - AgentPlatform      (agent platform)
#   - Analytics          (Tableau CRM / Tableau Next UI toggles)
#   - Any Settings record whose fullName contains "Tableau" or "Concierge"
#     and didn't exist before DC provisioning (auto-discovered).
#
# Safety:
#   - Only flips fields named `enable*` from false -> true. `disable*`, other
#     boolean names, and non-boolean fields are left untouched.
#   - On per-record deploy failure: warning + continue (no hard failure).
#   - No-op if everything in the allowlist is already enabled.
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
Write-Host '--- [f/i] Enable Tableau Next + Agentforce toggles ---'

$state = Read-OrgSetupState -Alias $Alias
if (@($state.completed) -contains 'f-i-tableau-next-enable') {
    Write-Host '  Already completed — skipping.' -ForegroundColor Cyan
    return
}

$sf = Get-RequiredCommandPath -Name 'sf' -Hint 'Install Salesforce CLI.'

# Static allowlist -- these records always exist in orgs with Einstein on.
$seedRecords = @('Bot','EinsteinCopilot','EinsteinAgent','AgentPlatform','Analytics')

# Dynamic discovery -- anything Tableau Next / Concierge / Semantic that appeared.
Write-Host '  Discovering Settings records (Tableau/Concierge/Semantic)...'
$discovered = @()
try {
    $listResult = Invoke-OrgSetupSfJson -Args @(
        'org','list','metadata','--target-org',$Alias,'--metadata-type','Settings'
    )
    foreach ($r in @($listResult)) {
        $fn = $r.fullName
        if ($fn -match '(?i)(tableau|concierge|semantic)') {
            $discovered += $fn
        }
    }
} catch {
    Add-OrgSetupWarning -Alias $Alias -Step 'f-i-tableau-next-enable' `
        -Message "Could not enumerate Settings metadata for dynamic discovery: $($_.Exception.Message)"
}

$allRecords = @($seedRecords + $discovered) | Sort-Object -Unique
Write-Host ("  Target Settings records: {0}" -f ($allRecords -join ', '))

# Prepare working dirs
$salesforceRoot = Resolve-CommandCenterPath 'salesforce'
$stageRoot = Join-Path (Resolve-CommandCenterPath 'tmp') ("org-setup-{0}-toggle" -f $Alias)
if (Test-Path $stageRoot) { Remove-Item -Recurse -Force $stageRoot }
Ensure-Directory -Path $stageRoot
$retrieveDir = Join-Path $stageRoot 'retrieved'
$deployDir   = Join-Path $stageRoot 'deploy'
Ensure-Directory -Path $retrieveDir
Ensure-Directory -Path $deployDir

# Retrieve current state
$manifestPath = Join-Path $stageRoot 'package.xml'
$membersXml = ($allRecords | ForEach-Object { "        <members>$_</members>" }) -join "`n"
@"
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
$membersXml
        <name>Settings</name>
    </types>
    <version>66.0</version>
</Package>
"@ | Set-Content -Path $manifestPath -Encoding UTF8

Push-Location $salesforceRoot
try {
    Write-Host '  Retrieving current Settings records to inspect...'
    $exit = Invoke-OrgSetupNative -FilePath $sf -Arguments @(
        'project','retrieve','start',
        '--target-org',$Alias,
        '--manifest',$manifestPath,
        '--target-metadata-dir',$retrieveDir,
        '--unzip'
    )
    if ($exit -ne 0) {
        $warnMsg = "sf project retrieve start exited $exit -- cannot flip toggles. Enable manually in Setup > Tableau Next Setup and Agentforce Agents."
        Add-OrgSetupWarning -Alias $Alias -Step 'f-i-tableau-next-enable' -Message $warnMsg
        Add-OrgSetupLogEntry -Alias $Alias -Step 'f-i-tableau-next-enable' -Outcome 'skipped' `
            -Message 'Retrieve failed; see warning for manual fallback.'
        return
    }
} finally {
    Pop-Location
}

$retrievedSettingsDir = Join-Path $retrieveDir 'unpackaged/unpackaged/settings'
if (-not (Test-Path $retrievedSettingsDir)) {
    Add-OrgSetupWarning -Alias $Alias -Step 'f-i-tableau-next-enable' `
        -Message "No Settings files retrieved (expected at $retrievedSettingsDir). Data Cloud may not be fully provisioned."
    Add-OrgSetupLogEntry -Alias $Alias -Step 'f-i-tableau-next-enable' -Outcome 'skipped' `
        -Message 'No Settings files retrieved.'
    return
}

# Stage the deploy: copy each .settings file, flipping enable*=false -> true.
$deploySettingsDir = Join-Path $deployDir 'settings'
Ensure-Directory -Path $deploySettingsDir

$flipCount = 0
$recordsWithChanges = @()
$changedFieldsByRecord = @{}

foreach ($sourceFile in (Get-ChildItem $retrievedSettingsDir -Filter '*.settings')) {
    $recordName = [System.IO.Path]::GetFileNameWithoutExtension($sourceFile.Name)
    $text = Get-Content -Path $sourceFile.FullName -Raw

    # Regex match enable*>false</enable*> -- careful: tag name inside > and </>
    # must be identical. Capture the tag name so we can emit it in the warning
    # list.
    $pattern = '(?ms)<(enable[A-Za-z0-9_]+)>\s*false\s*</\1>'
    $falseMatches = [regex]::Matches($text, $pattern)

    if ($falseMatches.Count -eq 0) {
        continue
    }

    # First pass: build the list of tags we'll flip (regex scriptblock closures
    # don't mutate outer scope, so we enumerate matches directly).
    # Skip fields that require paid add-ons or are known to fail on STORM/demo orgs.
    # Extend this list as new license-gated toggles are discovered.
    $skipPatterns = @(
        '(?i)disable','(?i)deprecat','(?i)optOut','(?i)legacy',
        '^enableAmazonRedshiftOutputConnector$',
        '^enableAzureDLGen2OutputConnector$',
        '^enableCrmaDataCloudIntegration$',   # requires CRM Analytics license
        '^enableSnowflakeOutputConnector$',
        '^enableSalesforceOutputConnector$',
        '^enableLotusNotesImages$',
        '^enableLightningReportBuilder$',     # gated
        '^enableIncludeDisclaimerMessage$',
        '^enableOrgCanViewTableau$',          # Tableau Server integration, gated
        '^enableWriteToDataCloud$'
    )
    $flippedFields = @()
    foreach ($fm in $falseMatches) {
        $tag = $fm.Groups[1].Value
        $skip = $false
        foreach ($sp in $skipPatterns) { if ($tag -match $sp) { $skip = $true; break } }
        if (-not $skip -and ($flippedFields -notcontains $tag)) { $flippedFields += $tag }
    }

    # Second pass: do the actual text replacement for every tag we chose.
    $newText = $text
    foreach ($tag in $flippedFields) {
        $tagPattern = "(?ms)<$tag>\s*false\s*</$tag>"
        $newText = [regex]::Replace($newText, $tagPattern, "<$tag>true</$tag>")
    }

    # Strip tags whose NAME matches an explicit-name skip pattern (anchored
    # ^name$ entries above). These are fields the org's license doesn't cover;
    # leaving them in the deploy causes "invalid field" failures even when
    # value is false, so we must remove the element entirely.
    foreach ($sp in $skipPatterns) {
        # Only process patterns that look like an exact field-name anchor.
        if ($sp -match '^\^enable') {
            $bareName = $sp.Trim('^$')
            # Remove the single-line element <bareName>value</bareName>.
            $removalPattern = "(?ms)[\r\n]?\s*<$bareName>[^<]*</$bareName>"
            $newText = [regex]::Replace($newText, $removalPattern, '')
        }
    }

    if ($flippedFields.Count -gt 0) {
        $targetFile = Join-Path $deploySettingsDir ($recordName + '.settings-meta.xml')
        Set-Content -Path $targetFile -Value $newText -Encoding UTF8
        $flipCount += $flippedFields.Count
        $recordsWithChanges += $recordName
        $changedFieldsByRecord[$recordName] = $flippedFields
    }
}

if ($flipCount -eq 0) {
    Write-Host '  All target enable* fields already true — nothing to deploy.' -ForegroundColor Cyan
    Add-OrgSetupLogEntry -Alias $Alias -Step 'f-i-tableau-next-enable' -Outcome 'noop' `
        -Message "All target enable* fields already true across: $($allRecords -join ', ')."
    Write-Host '  [f/i] Done (noop).' -ForegroundColor Cyan
    return
}

Write-Host ("  Staging deploy: {0} enable* field(s) to flip across {1} record(s):" -f `
    $flipCount, $recordsWithChanges.Count)
foreach ($rec in $recordsWithChanges) {
    Write-Host ("    {0}: {1}" -f $rec, ($changedFieldsByRecord[$rec] -join ', '))
}

# Deploy each record individually -- if one settings record fails, others
# should still succeed (e.g. if Tableau Next isn't fully provisioned but
# Bot + EinsteinCopilot are ready). sf project deploy requires the DX project
# root as cwd, so Push-Location around the loop.
$failedRecords = @()
Push-Location $salesforceRoot
try {
    foreach ($rec in $recordsWithChanges) {
        Write-Host ("  Deploying Settings:{0}..." -f $rec)
        $singleFile = Join-Path $deploySettingsDir ($rec + '.settings-meta.xml')
        $exit = Invoke-OrgSetupNative -FilePath $sf -Arguments @(
            'project','deploy','start',
            '--target-org',$Alias,
            '--source-dir',$singleFile,
            '--ignore-conflicts','--ignore-warnings'
        )
        if ($exit -ne 0) {
            Add-OrgSetupWarning -Alias $Alias -Step 'f-i-tableau-next-enable' `
                -Feature $rec `
                -Message ("Settings:{0} deploy failed (exit {1}). Fields that would have flipped: {2}. Enable manually in Setup." -f `
                    $rec, $exit, ($changedFieldsByRecord[$rec] -join ', '))
            $failedRecords += $rec
            Write-Host ("  Settings:{0} deploy FAILED (see warning)." -f $rec) -ForegroundColor Yellow
        } else {
            Write-Host ("  Settings:{0} deployed." -f $rec) -ForegroundColor Green
        }
    }
} finally {
    Pop-Location
}

$succeeded = @($recordsWithChanges | Where-Object { $_ -notin $failedRecords })
if ($succeeded.Count -gt 0) {
    $msg = ("Enabled {0} toggle(s) across {1} record(s): {2}." -f $flipCount, $succeeded.Count, ($succeeded -join ', '))
    if ($failedRecords.Count -gt 0) {
        $msg += " Failed: $($failedRecords -join ', ') -- see warnings."
        Write-Host ("  Done with partial failures: {0} succeeded, {1} failed (see warnings above)." -f $succeeded.Count, $failedRecords.Count) -ForegroundColor Yellow
    } else {
        Write-Host ("  All {0} Settings record(s) deployed successfully." -f $succeeded.Count) -ForegroundColor Green
    }
    Add-OrgSetupLogEntry -Alias $Alias -Step 'f-i-tableau-next-enable' -Outcome 'completed' -Message $msg
} else {
    Write-Host '  All Settings deploys failed — check warnings.' -ForegroundColor Red
    Add-OrgSetupLogEntry -Alias $Alias -Step 'f-i-tableau-next-enable' -Outcome 'failed' `
        -Message "All record deploys failed: $($failedRecords -join ', ')."
}
Write-Host '  [f/i] Done.' -ForegroundColor Green
