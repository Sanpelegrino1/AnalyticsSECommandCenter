param(
    [string]$TargetOrg = $env:SF_DEFAULT_ALIAS,
    [int]$Limit = 200,
    [string]$WorkspaceId,
    [string]$OutputPath,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '_TableauNext.Common.ps1')

$semanticModelRows = Get-TableauNextSemanticModelRows -TargetOrg $TargetOrg -Limit $Limit -WorkspaceId $WorkspaceId

Write-TableauNextOutput -Records $semanticModelRows -OutputPath $OutputPath -Json:$Json -DefaultTableFields @(
    'WorkspaceLabel',
    'WorkspaceDeveloperName',
    'SemanticModelId',
    'AssetUsageType',
    'LastModifiedDate'
)