[CmdletBinding()]
param(
    [string]$TargetKey,
    [Parameter(Mandatory = $true)]
    [string]$JobId,
    [bool]$WaitForTerminalState = $true,
    [int]$PollSeconds = 10,
    [int]$TimeoutSeconds = 300
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'DataCloud.Common.ps1')

$context = Get-DataCloudAccessContext -TargetKey $TargetKey
$job = Invoke-DataCloudJsonRequest -Context $context -Method Get -RelativePath ('/api/v1/ingest/jobs/{0}' -f $JobId)

if ($job.state -in @('JobComplete', 'Failed', 'Aborted')) {
    Write-Warning ('Data Cloud job {0} is already in terminal state {1}. No abort request was sent.' -f $JobId, $job.state)
    $job = Add-DataCloudJobOperatorMetadata -TargetKey $context.Config.TargetKey -Job $job
    Write-Output $job
    return
}

Write-Host ('Aborting Data Cloud job {0} from state {1}...' -f $JobId, $job.state)
$job = Stop-DataCloudJob -Context $context -JobId $JobId

if ($WaitForTerminalState) {
    $job = Wait-DataCloudJobState -Context $context -JobId $JobId -PollSeconds $PollSeconds -TimeoutSeconds $TimeoutSeconds
}

$job = Add-DataCloudJobOperatorMetadata -TargetKey $context.Config.TargetKey -Job $job
Write-Output $job