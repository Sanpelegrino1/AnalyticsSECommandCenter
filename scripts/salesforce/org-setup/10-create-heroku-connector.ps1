# OrgSetup step (m) -- OPTIONAL Heroku PostgreSQL connector.
#
# Creates a Data Cloud external data connector pointing at the shared Heroku
# PostgreSQL used by the ICE curriculum (creds from the PACE guide).
#
# BEST-EFFORT: the /ssot/external-data-connectors POST schema is not officially
# documented. If the POST fails, the script logs a manual fallback instruction.
#
# Inputs:
#   -Alias            (required)
#   -ConnectionName   (optional, default 'Heroku_PostgreSQL')

param(
    [Parameter(Mandatory = $true)]
    [string]$Alias,
    [string]$ConnectionName = 'Heroku_PostgreSQL'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'lib\OrgSetup.Common.ps1')

Write-Host ''
Write-Host '--- [m] Create Heroku PostgreSQL connector ---'

$auth = Get-OrgSetupAuth -Alias $Alias
$api = Get-OrgSetupApiVersion

Write-Host "  Checking for existing '$ConnectionName' connector..."
$existingList = Invoke-OrgSetupRest -Auth $auth -Method GET `
    -Path "/services/data/$api/ssot/external-data-connectors" -AllowErrorStatus

if (-not $existingList._error) {
    $connectors = @()
    if ($existingList.externalDataConnectors) {
        $connectors = @($existingList.externalDataConnectors)
    } elseif ($existingList.PSObject.Properties['data']) {
        $connectors = @($existingList.data)
    }
    $match = $connectors | Where-Object { $_.name -eq $ConnectionName -or $_.developerName -eq $ConnectionName }
    if (@($match).Count -gt 0) {
        Write-Host "  '$ConnectionName' already exists -- skipping." -ForegroundColor Cyan
        Add-OrgSetupLogEntry -Alias $Alias -Step 'm-heroku-connector' -Outcome 'noop' `
            -Message "Connection '$ConnectionName' already exists."
        return
    }
}

Write-Host "  Creating Heroku PostgreSQL connector '$ConnectionName'..."

$body = @{
    connectorType = 'POSTGRESQL'
    name          = $ConnectionName
    apiName       = $ConnectionName
    host          = 'ec2-34-239-63-69.compute-1.amazonaws.com'
    port          = 5432
    database      = 'd2pbagf1jq37ti'
    schema        = 'public'
    username      = 'u92dhi1ajn88fj'
    password      = 'p4c90c4b2e14564db61447051bc670c4e0ade9e63af8905557975968ad7d9a567'
}

$result = Invoke-OrgSetupRest -Auth $auth -Method POST `
    -Path "/services/data/$api/ssot/external-data-connectors" -Body $body -AllowErrorStatus

if ($result._error) {
    $warnMsg = "SSOT connector POST failed (status=$($result.statusCode)). Create manually in Data Cloud Setup under Other Connectors, type PostgreSQL. Creds are in Org Setup/Tableau Next PACE Setup.txt lines 177-192."
    Add-OrgSetupWarning -Alias $Alias -Step 'm-heroku-connector' -Message $warnMsg
    Add-OrgSetupLogEntry -Alias $Alias -Step 'm-heroku-connector' -Outcome 'skipped' `
        -Message 'SSOT POST failed.'
    Write-Host '  Connector POST failed -- see warning.' -ForegroundColor Yellow
    return
}

Add-OrgSetupLogEntry -Alias $Alias -Step 'm-heroku-connector' -Outcome 'completed' `
    -Message "Created Heroku PostgreSQL connector '$ConnectionName'."
Write-Host "  Heroku PostgreSQL connector created." -ForegroundColor Green
Write-Host '  [m] Done.' -ForegroundColor Green
