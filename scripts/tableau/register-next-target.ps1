[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetKey,
    [string]$TargetOrg = $env:SF_DEFAULT_ALIAS,
    [string]$WorkspaceId,
    [string]$WorkspaceDeveloperName,
    [string]$WorkspaceLabel,
    [string]$SemanticModelId,
    [string]$Purpose = '',
    [string]$Notes = '',
    [switch]$AutoSelectSingleWorkspace,
    [switch]$SetDefault
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '_TableauNext.Common.ps1')

$resolvedTargetOrg = Resolve-TableauNextTargetOrg -TargetOrg $TargetOrg
$workspace = Resolve-TableauNextWorkspaceSelection -TargetOrg $resolvedTargetOrg -WorkspaceId $WorkspaceId -WorkspaceDeveloperName $WorkspaceDeveloperName -WorkspaceLabel $WorkspaceLabel -AutoSelectSingleWorkspace:$AutoSelectSingleWorkspace
$semanticModel = $null
if (-not [string]::IsNullOrWhiteSpace($SemanticModelId)) {
    $semanticModelRows = Get-TableauNextSemanticModelRows -TargetOrg $resolvedTargetOrg -Limit 2000 -WorkspaceId $workspace.WorkspaceId
    $semanticModelMatch = @($semanticModelRows | Where-Object { $_.SemanticModelId -eq $SemanticModelId } | Select-Object -First 1)
    if ($semanticModelMatch.Count -eq 0) {
        throw "Semantic model '$SemanticModelId' was not found in workspace '$($workspace.WorkspaceId)'. Discover semantic models first with scripts/tableau/list-next-semantic-models.ps1 -WorkspaceId $($workspace.WorkspaceId)."
    }

    $semanticModel = $semanticModelMatch[0]
}

$registry = Get-TableauNextRegistry
$existingTargets = @($registry.targets)
$existingTarget = @($existingTargets | Where-Object { $_.key -eq $TargetKey } | Select-Object -First 1)
$createdAt = if ($existingTarget.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace([string]$existingTarget[0].createdAt)) { $existingTarget[0].createdAt } else { Get-UtcTimestamp }

$targetRecord = [ordered]@{
    key = $TargetKey
    targetOrg = $resolvedTargetOrg
    workspaceId = $workspace.WorkspaceId
    workspaceDeveloperName = $workspace.DeveloperName
    workspaceLabel = $workspace.Label
    purpose = $Purpose
    notes = $Notes
    createdAt = $createdAt
    updatedAt = Get-UtcTimestamp
    lastValidatedUtc = Get-UtcTimestamp
}

if ($null -ne $semanticModel) {
    $targetRecord.semanticModelId = $semanticModel.SemanticModelId
    $targetRecord.workspaceAssetId = $semanticModel.WorkspaceAssetId
    $targetRecord.assetUsageType = $semanticModel.AssetUsageType
}

$updatedTargets = @($existingTargets | Where-Object { $_.key -ne $TargetKey }) + [pscustomobject]$targetRecord
$updatedRegistry = [pscustomobject]@{
    defaultTargetKey = if ($SetDefault) { $TargetKey } elseif (-not [string]::IsNullOrWhiteSpace($registry.defaultTargetKey)) { $registry.defaultTargetKey } else { '' }
    targets = @($updatedTargets | Sort-Object key)
}

Save-TableauNextRegistry -Registry $updatedRegistry
Write-Output ([pscustomobject]$targetRecord)