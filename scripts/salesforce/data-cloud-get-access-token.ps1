[CmdletBinding()]
param(
    [string]$TargetKey,
    [switch]$ShowToken,
    [switch]$AsJson
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'DataCloud.Common.ps1')

$context = Get-DataCloudAccessContext -TargetKey $TargetKey
$result = [ordered]@{
    targetKey = $context.Config.TargetKey
    tokenSource = $context.TokenSource
    salesforceAlias = $context.Config.SalesforceAlias
    tenantEndpoint = $context.TenantEndpoint
    sourceName = $context.Config.SourceName
    objectName = $context.Config.ObjectName
}

if ($ShowToken) {
    $result.accessToken = $context.AccessToken
}

$output = [pscustomobject]$result
if ($AsJson) {
    $output | ConvertTo-Json -Depth 10
} else {
    Write-Output $output
}
