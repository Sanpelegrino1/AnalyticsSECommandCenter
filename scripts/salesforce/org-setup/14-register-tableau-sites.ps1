# OrgSetup step (o) -- register Tableau Cloud sites via TableauHostMapping.
#
# Registers the two shared PACE Tableau Cloud sites (URL + LUID) in Salesforce
# so Tableau Next can resolve them. Salesforce-side only -- Tableau-side trust
# setup is manual (see warning emitted at end of step).
#
# Idempotent: checks for existing UrlMatch before inserting.
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
Write-Host '--- [o] Register Tableau Cloud sites (TableauHostMapping) ---'

$auth = Get-OrgSetupAuth -Alias $Alias
$api  = Get-OrgSetupApiVersion

$sites = @(
    @{
        Label    = 'PACE'
        UrlMatch = 'prod-uswest-c.online.tableau.com/pace'
        SiteLuid = '5a81db69-14f1-42c7-b6a5-65ec087bf57d'
    },
    @{
        Label    = 'PACE-NEXUS'
        UrlMatch = 'prod-uswest-c.online.tableau.com/pace-nexus'
        SiteLuid = '6901a397-fe8d-4795-83a0-7a6e7685434f'
    }
)

$anyFailure = $false

foreach ($site in $sites) {
    Write-Host "  Checking TableauHostMapping for $($site.Label)..."

    $existing = $null
    try {
        $existing = Invoke-OrgSetupSoql -Auth $auth -Soql `
            "SELECT Id FROM TableauHostMapping WHERE UrlMatch = '$($site.UrlMatch)'"
    } catch {
        $warnMsg = "TableauHostMapping query failed for $($site.Label): $($_.Exception.Message). Register manually in Setup under Tableau Organization Setup."
        Add-OrgSetupWarning -Alias $Alias -Step 'o-tableau-sites' -Message $warnMsg
        $anyFailure = $true
        continue
    }

    if ($existing -and $existing.records -and $existing.records.Count -gt 0) {
        Write-Host "    $($site.Label) already registered -- skipping." -ForegroundColor Cyan
        Add-OrgSetupLogEntry -Alias $Alias -Step 'o-tableau-sites' -Outcome 'noop' `
            -Message "$($site.Label): TableauHostMapping already present."
        continue
    }

    Write-Host "    Registering $($site.Label)..."
    $result = Invoke-OrgSetupRest -Auth $auth -Method POST `
        -Path "/services/data/$api/sobjects/TableauHostMapping" `
        -Body @{
            SiteLuid = $site.SiteLuid
            UrlMatch = $site.UrlMatch
            HostType = 'Tableau Cloud'
        } `
        -AllowErrorStatus

    $isErr = $false
    try { $isErr = [bool]$result._error } catch {}
    if ($isErr) {
        $warnMsg = "TableauHostMapping insert failed for $($site.Label). Register manually in Setup under Tableau Organization Setup. URL=$($site.UrlMatch) LUID=$($site.SiteLuid)."
        Add-OrgSetupWarning -Alias $Alias -Step 'o-tableau-sites' -Message $warnMsg
        Add-OrgSetupLogEntry -Alias $Alias -Step 'o-tableau-sites' -Outcome 'skipped' `
            -Message "$($site.Label): REST insert failed."
        $anyFailure = $true
    } else {
        Write-Host "    $($site.Label) registered (Id=$($result.id))." -ForegroundColor Green
        Add-OrgSetupLogEntry -Alias $Alias -Step 'o-tableau-sites' -Outcome 'completed' `
            -Message "$($site.Label): TableauHostMapping created (Id=$($result.id))."
    }
}

if (-not $anyFailure) {
    Write-Host '  Tableau Cloud site URLs registered on the Salesforce side.' -ForegroundColor Green
}

Write-Host '  [o] Done.' -ForegroundColor Green
