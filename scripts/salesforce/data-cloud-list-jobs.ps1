[CmdletBinding()]
param(
    [string]$TargetKey,
    [string]$States,
    [int]$Limit = 20,
    [int]$Offset = 0,
    [string]$OrderBy = 'systemModstamp'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'DataCloud.Common.ps1')

$context = Get-DataCloudAccessContext -TargetKey $TargetKey
$query = @{
    limit = $Limit
    offset = $Offset
    orderBy = $OrderBy
}

if (-not [string]::IsNullOrWhiteSpace($States)) {
    $query.states = $States
}

$response = Invoke-DataCloudJsonRequest -Context $context -Method Get -RelativePath '/api/v1/ingest/jobs' -Query $query
if ($null -eq $response.data) {
    Write-Output @()
} else {
    $jobs = @($response.data | ForEach-Object { Add-DataCloudJobOperatorMetadata -TargetKey $context.Config.TargetKey -Job $_ })
    Write-Output $jobs
}
