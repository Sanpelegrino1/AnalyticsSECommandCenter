[CmdletBinding()]
param(
    [string]$TargetKey,
    [string]$OutputPath,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '_TableauNext.Common.ps1')

$config = Get-TableauNextTargetConfiguration -TargetKey $TargetKey
$workspaceRows = Get-TableauNextWorkspaceRows -TargetOrg $config.TargetOrg -Limit 2000
$workspace = @($workspaceRows | Where-Object { $_.WorkspaceId -eq $config.WorkspaceId } | Select-Object -First 1)

$workspaceValidated = ($workspace.Count -gt 0)
$workspaceDeveloperNameMatches = $false
$workspaceLabelMatches = $false
if ($workspaceValidated) {
    $workspaceDeveloperNameMatches = ([string]$workspace[0].DeveloperName -eq [string]$config.WorkspaceDeveloperName)
    $workspaceLabelMatches = ([string]$workspace[0].Label -eq [string]$config.WorkspaceLabel)
}

$semanticModelPinned = -not [string]::IsNullOrWhiteSpace($config.SemanticModelId)
$semanticModel = $null
$semanticModelValidated = $false
if ($semanticModelPinned -and $workspaceValidated) {
    $semanticModelRows = Get-TableauNextSemanticModelRows -TargetOrg $config.TargetOrg -Limit 2000 -WorkspaceId $config.WorkspaceId
    $semanticModelMatch = @($semanticModelRows | Where-Object { $_.SemanticModelId -eq $config.SemanticModelId } | Select-Object -First 1)
    if ($semanticModelMatch.Count -gt 0) {
        $semanticModel = $semanticModelMatch[0]
        $semanticModelValidated = $true
    }
}

$inspectionStatus = if (-not $workspaceValidated) {
    'WorkspaceMissing'
} elseif ($semanticModelPinned -and -not $semanticModelValidated) {
    'SemanticModelMissing'
} elseif ($semanticModelPinned) {
    'ExistingSemanticModelValidated'
} else {
    'ReadyForCreation'
}

$record = [pscustomobject]@{
    TargetKey = $config.TargetKey
    TargetOrg = $config.TargetOrg
    InspectionStatus = $inspectionStatus
    WorkspaceValidated = $workspaceValidated
    WorkspaceId = $config.WorkspaceId
    WorkspaceDeveloperName = $(if ($workspaceValidated) { $workspace[0].DeveloperName } else { $config.WorkspaceDeveloperName })
    WorkspaceLabel = $(if ($workspaceValidated) { $workspace[0].Label } else { $config.WorkspaceLabel })
    WorkspaceDeveloperNameMatches = $workspaceDeveloperNameMatches
    WorkspaceLabelMatches = $workspaceLabelMatches
    SemanticModelPinned = $semanticModelPinned
    SemanticModelValidated = $semanticModelValidated
    SemanticModelId = $(if ($semanticModelValidated) { $semanticModel.SemanticModelId } else { $config.SemanticModelId })
    WorkspaceAssetId = $(if ($semanticModelValidated) { $semanticModel.WorkspaceAssetId } else { $config.WorkspaceAssetId })
    AssetUsageType = $(if ($semanticModelValidated) { $semanticModel.AssetUsageType } else { $config.AssetUsageType })
    HistoricalPromotionStatus = $(if ($semanticModelValidated) { $semanticModel.HistoricalPromotionStatus } else { '' })
    LastValidatedUtc = Get-TableauNextTargetPropertyValue -Target $config.Target -PropertyName 'lastValidatedUtc'
    WorkspaceInventoryCommand = ('powershell -ExecutionPolicy Bypass -File .\scripts\tableau\list-next-workspaces.ps1 -TargetOrg {0}' -f $config.TargetOrg)
    SemanticModelInventoryCommand = ('powershell -ExecutionPolicy Bypass -File .\scripts\tableau\list-next-semantic-models.ps1 -TargetOrg {0} -WorkspaceId {1}' -f $config.TargetOrg, $config.WorkspaceId)
}

Write-TableauNextOutput -Records @($record) -OutputPath $OutputPath -Json:$Json -DefaultTableFields @(
    'TargetKey',
    'InspectionStatus',
    'WorkspaceLabel',
    'WorkspaceDeveloperName',
    'SemanticModelId',
    'AssetUsageType'
)