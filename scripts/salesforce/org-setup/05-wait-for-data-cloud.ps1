# OrgSetup steps (c) + (j) -- poll for Data Cloud tenant readiness.
#
# Data Cloud enablement (step a) kicks off ~30 min async provisioning. This script
# polls GET /services/data/v60.0/ssot/data-connections -- success = tenant is live
# and downstream features (Feature Manager, Tableau Next, MktDataConnection sobject)
# become available.
#
# Inputs:
#   -Alias              (required)
#   -TimeoutMinutes     (optional, default 60)
#   -IntervalSeconds    (optional, default 60)

param(
    [Parameter(Mandatory = $true)]
    [string]$Alias,
    [int]$TimeoutMinutes = 60,
    [int]$IntervalSeconds = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'lib\OrgSetup.Common.ps1')

Write-Host ''
Write-Host '--- [c/j] Wait for Data Cloud tenant provisioning ---'

$auth = Get-OrgSetupAuth -Alias $Alias
$deadline = (Get-Date).AddMinutes($TimeoutMinutes)
$startedAt = Get-Date

Write-Host "  Polling Data Cloud readiness for '$Alias' (timeout ${TimeoutMinutes}min, interval ${IntervalSeconds}s)..."
Write-Host '  (STORM orgs are usually ready immediately; fresh orgs can take ~30 min)' -ForegroundColor Yellow
while ((Get-Date) -lt $deadline) {
    if (Test-OrgSetupDataCloudReady -Auth $auth) {
        $elapsed = [int]((Get-Date) - $startedAt).TotalSeconds
        Write-Host "  Data Cloud tenant is live (${elapsed}s elapsed)." -ForegroundColor Green
        Add-OrgSetupLogEntry -Alias $Alias -Step 'c-j-data-cloud-ready' -Outcome 'completed' `
            -Message "Data Cloud tenant is live ($elapsed s)."
        Write-Host '  [c/j] Done.' -ForegroundColor Green
        return
    }
    Write-Host ("  [{0}] not ready yet; next check in {1}s..." -f (Get-Date).ToString('HH:mm:ss'), $IntervalSeconds)
    Start-Sleep -Seconds $IntervalSeconds
}

Add-OrgSetupLogEntry -Alias $Alias -Step 'c-j-data-cloud-ready' -Outcome 'failed' `
    -Message "Timed out after $TimeoutMinutes min."
throw "Data Cloud not ready after $TimeoutMinutes minutes."
