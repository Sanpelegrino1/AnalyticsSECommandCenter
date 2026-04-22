[CmdletBinding()]
param(
    [string]$TargetKey,
    [string]$TargetOrg = $env:SF_DEFAULT_ALIAS,
    [string]$WorkspaceId,
    [string]$SemanticModelId,
    [string]$WorkspaceAssetId,
    [string]$OutputPath,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '_TableauNext.Common.ps1')

function Get-OptionalSemanticModelPropertyValue {
    param(
        [object]$Model,
        [Parameter(Mandatory = $true)]
        [string]$PropertyName
    )

    if ($null -eq $Model) {
        return ''
    }

    $property = $Model.PSObject.Properties[$PropertyName]
    if ($null -eq $property -or $null -eq $property.Value) {
        return ''
    }

    return [string]$property.Value
}

$config = $null
if (-not [string]::IsNullOrWhiteSpace($TargetKey)) {
    $config = Get-TableauNextTargetConfiguration -TargetKey $TargetKey

    if ([string]::IsNullOrWhiteSpace($TargetOrg)) {
        $TargetOrg = $config.TargetOrg
    }
    if ([string]::IsNullOrWhiteSpace($WorkspaceId)) {
        $WorkspaceId = $config.WorkspaceId
    }
    if ([string]::IsNullOrWhiteSpace($SemanticModelId)) {
        $SemanticModelId = $config.SemanticModelId
    }
    if ([string]::IsNullOrWhiteSpace($WorkspaceAssetId)) {
        $WorkspaceAssetId = $config.WorkspaceAssetId
    }
}

$resolvedTargetOrg = Resolve-TableauNextTargetOrg -TargetOrg $TargetOrg
if ([string]::IsNullOrWhiteSpace($SemanticModelId) -and [string]::IsNullOrWhiteSpace($WorkspaceAssetId)) {
    throw 'Provide -SemanticModelId or -WorkspaceAssetId, or use a target that already pins one of them.'
}

$detail = Get-TableauNextSemanticModelDetail -TargetOrg $resolvedTargetOrg -WorkspaceId $WorkspaceId -SemanticModelId $SemanticModelId -WorkspaceAssetId $WorkspaceAssetId
$record = if ($null -eq $detail) {
    [pscustomobject]@{
        TargetKey = $(if ($null -ne $config) { $config.TargetKey } else { '' })
        TargetOrg = $resolvedTargetOrg
        InspectionStatus = 'SemanticModelMissing'
        WorkspaceId = $WorkspaceId
        WorkspaceDeveloperName = $(if ($null -ne $config) { $config.WorkspaceDeveloperName } else { '' })
        WorkspaceLabel = $(if ($null -ne $config) { $config.WorkspaceLabel } else { '' })
        SemanticModelId = $SemanticModelId
        WorkspaceAssetId = $WorkspaceAssetId
        AssetType = ''
        AssetUsageType = ''
        HistoricalPromotionStatus = ''
        CreatedDate = ''
        LastModifiedDate = ''
    }
} else {
    $semanticModelDefinition = Get-TableauNextSemanticModelDefinition -TargetOrg $resolvedTargetOrg -SemanticModelIdOrApiName $detail.SemanticModelId
    $semanticDataObjects = @($semanticModelDefinition.semanticDataObjects)
    $semanticRelationships = @($semanticModelDefinition.semanticRelationships)
    [pscustomobject]@{
        TargetKey = $(if ($null -ne $config) { $config.TargetKey } else { '' })
        TargetOrg = $resolvedTargetOrg
        InspectionStatus = 'SemanticModelValidated'
        WorkspaceId = $detail.WorkspaceId
        WorkspaceDeveloperName = $detail.WorkspaceDeveloperName
        WorkspaceLabel = $detail.WorkspaceLabel
        SemanticModelId = $detail.SemanticModelId
        WorkspaceAssetId = $detail.WorkspaceAssetId
        AssetType = $detail.AssetType
        AssetUsageType = $detail.AssetUsageType
        HistoricalPromotionStatus = $detail.HistoricalPromotionStatus
        ModelApiName = Get-OptionalSemanticModelPropertyValue -Model $semanticModelDefinition -PropertyName 'apiName'
        ModelLabel = Get-OptionalSemanticModelPropertyValue -Model $semanticModelDefinition -PropertyName 'label'
        DataSpace = Get-OptionalSemanticModelPropertyValue -Model $semanticModelDefinition -PropertyName 'dataspace'
        VersionState = Get-OptionalSemanticModelPropertyValue -Model $semanticModelDefinition -PropertyName 'versionState'
        SemanticDataObjectCount = $semanticDataObjects.Count
        SemanticRelationshipCount = $semanticRelationships.Count
        CreatedDate = $detail.CreatedDate
        LastModifiedDate = $detail.LastModifiedDate
    }
}

Write-TableauNextOutput -Records @($record) -OutputPath $OutputPath -Json:$Json -DefaultTableFields @(
    'InspectionStatus',
    'ModelApiName',
    'WorkspaceLabel',
    'WorkspaceDeveloperName',
    'SemanticModelId',
    'AssetUsageType',
    'LastModifiedDate'
)
