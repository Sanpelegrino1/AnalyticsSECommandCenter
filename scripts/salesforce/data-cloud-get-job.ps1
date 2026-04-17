[CmdletBinding()]
param(
    [string]$TargetKey,
    [Parameter(Mandatory = $true)]
    [string]$JobId,
    [bool]$WaitForTerminalState = $false,
    [int]$PollSeconds = 15,
    [int]$TimeoutSeconds = 900
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'DataCloud.Common.ps1')

$context = Get-DataCloudAccessContext -TargetKey $TargetKey

if ($WaitForTerminalState) {
    Write-Host ('Waiting for Data Cloud job {0} to reach a terminal state...' -f $JobId)
    $job = Wait-DataCloudJobState -Context $context -JobId $JobId -PollSeconds $PollSeconds -TimeoutSeconds $TimeoutSeconds
} else {
    $job = Invoke-DataCloudJsonRequest -Context $context -Method Get -RelativePath ('/api/v1/ingest/jobs/{0}' -f $JobId)
}

Write-Output $job
