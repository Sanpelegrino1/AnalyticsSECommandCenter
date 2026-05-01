# OrgSetup step (e) completion -- self-assign Tableau_Next_Admin_PSG to the current user.
#
# Idempotent: checks for existing PermissionSetAssignment first.
# Requires: 03-deploy-permsets-and-psg.ps1 to have succeeded.
#
# The PSG is async-calculated after deploy; this script polls for Status='Updated'
# before assigning (assignments against a pending group can fail).
#
# Inputs:
#   -Alias              (required)
#   -TimeoutSeconds     (optional, default 300) -- max wait for PSG recalculation

param(
    [Parameter(Mandatory = $true)]
    [string]$Alias,
    [int]$TimeoutSeconds = 300
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'lib\OrgSetup.Common.ps1')

Write-Host ''
Write-Host '--- [e] Assign Tableau_Next_Admin_PSG to self ---'

$auth = Get-OrgSetupAuth -Alias $Alias
$userId = Get-OrgSetupUserId -Auth $auth

Write-Host "  Waiting for PSG to reach Status='Updated' (max ${TimeoutSeconds}s)..."

# Resolve PSG id + wait for Status='Updated'
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$psgId = $null
while ((Get-Date) -lt $deadline) {
    $result = Invoke-OrgSetupSoql -Auth $auth -Soql `
        "SELECT Id, Status FROM PermissionSetGroup WHERE DeveloperName = 'Tableau_Next_Admin_PSG'"
    if ($result.records -and $result.records.Count -gt 0) {
        $record = $result.records[0]
        if ($record.Status -eq 'Updated') {
            $psgId = $record.Id
            break
        }
        Write-Host "  PSG status = $($record.Status); waiting..."
    } else {
        Write-Host '  PSG not visible yet; waiting...'
    }
    Start-Sleep -Seconds 10
}
if (-not $psgId) {
    Add-OrgSetupLogEntry -Alias $Alias -Step 'e-assign-psg' -Outcome 'failed' `
        -Message 'PSG did not reach Status=Updated in time.'
    throw "Tableau_Next_Admin_PSG did not finish recalculating within $TimeoutSeconds s."
}

# Check for existing assignment
Write-Host '  Checking for existing PSG assignment...'
$existing = Invoke-OrgSetupSoql -Auth $auth -Soql `
    "SELECT Id FROM PermissionSetAssignment WHERE AssigneeId = '$userId' AND PermissionSetGroupId = '$psgId'"
if ($existing.records -and $existing.records.Count -gt 0) {
    Write-Host '  Already assigned — skipping.' -ForegroundColor Cyan
    Add-OrgSetupLogEntry -Alias $Alias -Step 'e-assign-psg' -Outcome 'noop' `
        -Message 'PSG already assigned to self.'
    return
}

Write-Host "  Assigning Tableau_Next_Admin_PSG to $($auth.Username)..."
# Create assignment
$api = Get-OrgSetupApiVersion
$body = @{ AssigneeId = $userId; PermissionSetGroupId = $psgId }
$result = Invoke-OrgSetupRest -Auth $auth -Method POST `
    -Path "/services/data/$api/sobjects/PermissionSetAssignment" -Body $body
if (-not $result.success) {
    Add-OrgSetupLogEntry -Alias $Alias -Step 'e-assign-psg' -Outcome 'failed' `
        -Message "PSA insert failed: $($result | ConvertTo-Json -Depth 5 -Compress)"
    throw "Failed to assign PSG."
}

Add-OrgSetupLogEntry -Alias $Alias -Step 'e-assign-psg' -Outcome 'completed' `
    -Message "Assigned Tableau_Next_Admin_PSG (id=$psgId) to $($auth.Username)."
Write-Host "  Tableau_Next_Admin_PSG assigned." -ForegroundColor Green
Write-Host '  [e] Done.' -ForegroundColor Green
