param(
    [string]$TargetOrg = $env:SF_DEFAULT_ALIAS,
    [int]$Limit = 200,
    [string]$OutputPath,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '_TableauNext.Common.ps1')

$workspaceRows = Get-TableauNextWorkspaceRows -TargetOrg $TargetOrg -Limit $Limit

Write-TableauNextOutput -Records $workspaceRows -OutputPath $OutputPath -Json:$Json -DefaultTableFields @(
    'WorkspaceId',
    'DeveloperName',
    'Label',
    'Language',
    'LastModifiedDate'
)