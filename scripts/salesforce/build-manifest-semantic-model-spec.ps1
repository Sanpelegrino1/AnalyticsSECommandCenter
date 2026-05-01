[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ManifestPath,
    [Parameter(Mandatory = $true)]
    [string]$ProvisioningReportPath,
    [Parameter(Mandatory = $true)]
    [string]$TargetKey,
    [string]$TargetKeyPrefix,
    [string[]]$Tables,
    [string]$ModelApiName,
    [string]$ModelLabel,
    [string]$OutputPath,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'DataCloud.Common.ps1')
. (Join-Path $PSScriptRoot '..\tableau\_TableauNext.Common.ps1')

function Resolve-ManifestTargetRows {
    param(
        [Parameter(Mandatory = $true)]
        [object]$ManifestInfo,
        [Parameter(Mandatory = $true)]
        [string]$ResolvedTargetKeyPrefix,
        [string[]]$SelectedTables
    )

    $manifest = $ManifestInfo.Content
    $selectedTableSet = @{}
    foreach ($tableName in @($SelectedTables)) {
        if (-not [string]::IsNullOrWhiteSpace($tableName)) {
            $selectedTableSet[[string]$tableName] = $true
        }
    }

    $registry = Get-DataCloudRegistry
    $rows = New-Object System.Collections.Generic.List[object]
    foreach ($file in @($manifest.files)) {
        $tableName = [string]$file.tableName
        if (@($selectedTableSet.Keys).Count -gt 0 -and -not $selectedTableSet.ContainsKey($tableName)) {
            continue
        }

        $targetKeyForTable = Resolve-DataCloudManifestTargetKey -TableName $tableName -TargetKeyPrefix $ResolvedTargetKeyPrefix
        $target = @($registry.targets | Where-Object { $_.key -eq $targetKeyForTable } | Select-Object -First 1)
        if (@($target).Count -eq 0) {
            throw "Manifest table '$tableName' is missing registry target '$targetKeyForTable'. Register manifest targets before building the semantic-model spec."
        }

        $rows.Add([pscustomobject]@{
            tableName = $tableName
            targetKey = $targetKeyForTable
            target = $target[0]
            csvPath = Resolve-DataCloudManifestCsvPath -ManifestInfo $ManifestInfo -FileDefinition $file
        }) | Out-Null
    }

    return $rows.ToArray()
}

function ConvertTo-SemanticModelFieldApiName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FieldName
    )

    return '{0}__c' -f (New-MetadataSafeName -Value $FieldName -MaxLength 37)
}

function ConvertTo-SemanticModelLabel {
    param(
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ''
    }

    $textInfo = [System.Globalization.CultureInfo]::InvariantCulture.TextInfo
    return ($Value -split '[_\s]+' | Where-Object { $_ } | ForEach-Object { $textInfo.ToTitleCase($_.ToLowerInvariant()) }) -join ' '
}

function Get-PrimaryKeysForTable {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Manifest,
        [Parameter(Mandatory = $true)]
        [object]$TargetRow
    )

    $joinGraphEntry = @($Manifest.joinGraph | Where-Object { [string]$_.tableName -eq [string]$TargetRow.tableName } | Select-Object -First 1)
    if (@($joinGraphEntry).Count -gt 0) {
        return @($joinGraphEntry[0].primaryKey | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } | ForEach-Object { [string]$_ })
    }

    $registeredPrimaryKey = [string](Get-OptionalObjectPropertyValue -InputObject $TargetRow.target -PropertyName 'primaryKey')
    if ([string]::IsNullOrWhiteSpace($registeredPrimaryKey)) {
        return @()
    }

    return @($registeredPrimaryKey -split '\s*[,;]\s*' | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
}

function New-ManifestSemanticModelSpec {
    param(
        [Parameter(Mandatory = $true)]
        [object]$ManifestInfo,
        [Parameter(Mandatory = $true)]
        [object]$Manifest,
        [Parameter(Mandatory = $true)]
        [object[]]$TargetRows,
        [Parameter(Mandatory = $true)]
        [object[]]$ProvisionedStreams,
        [Parameter(Mandatory = $true)]
        [object]$WorkspaceTarget,
        [Parameter(Mandatory = $true)]
        [string]$ResolvedModelApiName,
        [Parameter(Mandatory = $true)]
        [string]$ResolvedModelLabel,
        [Parameter(Mandatory = $true)]
        [string]$RootTableName
    )

    $tableNames = @($TargetRows | ForEach-Object { [string]$_.tableName } | Select-Object -Unique)
    $provisionedStreamsByTable = @{}
    foreach ($stream in @($ProvisionedStreams)) {
        $provisionedStreamsByTable[[string]$stream.tableName] = $stream
    }

    $objectMappings = New-Object System.Collections.Generic.List[object]
    $resolvedObjectApiNames = New-Object System.Collections.Generic.List[string]
    $resolvedPrimaryObjectApiName = ''
    foreach ($row in @($TargetRows)) {
        $provisionedStream = $provisionedStreamsByTable[[string]$row.tableName]
        $objectApiName = ''
        if ($null -ne $provisionedStream -and -not [string]::IsNullOrWhiteSpace([string]$provisionedStream.dataLakeObjectName)) {
            $objectApiName = [string]$provisionedStream.dataLakeObjectName
        }
        if ([string]::IsNullOrWhiteSpace($objectApiName)) {
            $objectApiName = [string](Get-OptionalObjectPropertyValue -InputObject $row.target -PropertyName 'objectName')
        }
        if ([string]::IsNullOrWhiteSpace($objectApiName)) {
            throw "Target row '$([string]$row.tableName)' is missing a resolved dataLakeObjectName and registered objectName."
        }

        $csvProfile = Get-DataCloudCsvFieldProfiles -CsvPath ([string]$row.csvPath) -AllowHeaderOnly -ContextLabel ("Table '$([string]$row.tableName)'")
        $fieldDefinitions = @(
            foreach ($field in @($csvProfile.fields)) {
                [ordered]@{
                    dataObjectFieldName = ConvertTo-SemanticModelFieldApiName -FieldName ([string]$field.apiName)
                    sourceFieldName = [string]$field.name
                    label = [string]$field.name
                    customFieldType = [string]$field.customFieldType
                    dataType = [string]$field.dataType
                }
            }
        )

        $primaryKeyFields = @(
            foreach ($primaryKey in @(Get-PrimaryKeysForTable -Manifest $Manifest -TargetRow $row)) {
                $matchingField = @($csvProfile.fields | Where-Object { [string]$_.name -eq [string]$primaryKey } | Select-Object -First 1)
                if (@($matchingField).Count -gt 0) {
                    ConvertTo-SemanticModelFieldApiName -FieldName ([string]$matchingField[0].apiName)
                }
            }
        )

        if ($row.tableName -eq $RootTableName) {
            $resolvedPrimaryObjectApiName = $objectApiName
        }

        $resolvedObjectApiNames.Add($objectApiName) | Out-Null
        $objectMappings.Add([ordered]@{
            tableName = [string]$row.tableName
            objectApiName = $objectApiName
            label = ConvertTo-SemanticModelLabel -Value ([string]$row.tableName)
            primaryKeyFields = @($primaryKeyFields)
            fields = @($fieldDefinitions)
        }) | Out-Null
    }

    $relationshipDefinitions = @(
        foreach ($relationship in @($Manifest.publishContract.relationships)) {
            if ($tableNames -notcontains [string]$relationship.sourceTable -or $tableNames -notcontains [string]$relationship.targetTable) {
                continue
            }

            [ordered]@{
                sourceTable = [string]$relationship.sourceTable
                sourceField = ConvertTo-SemanticModelFieldApiName -FieldName ([string]$relationship.sourceField)
                targetTable = [string]$relationship.targetTable
                targetField = ConvertTo-SemanticModelFieldApiName -FieldName ([string]$relationship.targetField)
                direction = [string]$relationship.direction
                required = [bool]$relationship.required
            }
        }
    )

    return [ordered]@{
        SemanticModelSpec = [ordered]@{
            targetKey = [string]$WorkspaceTarget.TargetKey
            targetOrg = [string]$WorkspaceTarget.TargetOrg
            workspace = [ordered]@{
                workspaceId = [string]$WorkspaceTarget.WorkspaceId
                workspaceDeveloperName = [string]$WorkspaceTarget.WorkspaceDeveloperName
                workspaceLabel = [string]$WorkspaceTarget.WorkspaceLabel
            }
            model = [ordered]@{
                apiName = $ResolvedModelApiName
                label = $ResolvedModelLabel
                description = ''
                dataSpace = 'default'
                primaryObjectApiName = $resolvedPrimaryObjectApiName
                objectApiNames = @($resolvedObjectApiNames | Select-Object -Unique)
                objectMappings = @($objectMappings.ToArray())
                relationshipDefinitions = @($relationshipDefinitions)
            }
        }
    }
}

$manifestInfo = Get-DataCloudManifestInfo -ManifestPath $ManifestPath
$manifest = $manifestInfo.Content
$datasetDefaults = Get-DataCloudManifestDefaults -ManifestInfo $manifestInfo
$rootTableName = [string](Get-OptionalObjectPropertyValue -InputObject $manifest.publishContract -PropertyName 'rootTable')
if ([string]::IsNullOrWhiteSpace($rootTableName)) {
    $rootTableName = [string](Get-OptionalObjectPropertyValue -InputObject $manifest.publishContract -PropertyName 'rootTableId')
}
if ([string]::IsNullOrWhiteSpace($rootTableName)) {
    $rootTableName = [string]$manifest.files[0].tableName
}

$registrationHints = Get-DataCloudManifestRegistrationHints -ManifestInfo $manifestInfo -Registry (Get-DataCloudRegistry) -RootTableName $rootTableName
$resolvedTargetKeyPrefix = if ([string]::IsNullOrWhiteSpace($TargetKeyPrefix)) {
    if (-not [string]::IsNullOrWhiteSpace($registrationHints.TargetKeyPrefix)) { $registrationHints.TargetKeyPrefix } else { $datasetDefaults.TargetKeyPrefix }
} else {
    $TargetKeyPrefix
}

$resolvedModelLabel = if ([string]::IsNullOrWhiteSpace($ModelLabel)) { '{0} Semantic Model' -f $datasetDefaults.DatasetLabel } else { $ModelLabel }
$resolvedModelApiName = if ([string]::IsNullOrWhiteSpace($ModelApiName)) { ConvertTo-TableauNextApiName -Value $resolvedModelLabel } else { ConvertTo-TableauNextApiName -Value $ModelApiName }
$resolvedOutputPath = if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    Resolve-CommandCenterPath (Join-Path 'tmp' ('{0}.semantic-model.spec.json' -f $datasetDefaults.DatasetKey))
} elseif ([System.IO.Path]::IsPathRooted($OutputPath)) {
    $OutputPath
} else {
    Resolve-CommandCenterPath $OutputPath
}

$workspaceTarget = Get-TableauNextTargetConfiguration -TargetKey $TargetKey
$targetRows = @(Resolve-ManifestTargetRows -ManifestInfo $manifestInfo -ResolvedTargetKeyPrefix $resolvedTargetKeyPrefix -SelectedTables $Tables)
if (@($targetRows).Count -eq 0) {
    throw 'No manifest target rows were resolved. Register the manifest targets before building a semantic-model spec.'
}

$provisioningState = Read-JsonFile -Path $ProvisioningReportPath
if ($null -eq $provisioningState) {
    throw "Provisioning report '$ProvisioningReportPath' could not be read."
}

$provisionedStreamsProperty = $provisioningState.PSObject.Properties['provisionedStreams']
$provisionedStreams = if ($null -ne $provisionedStreamsProperty -and $null -ne $provisionedStreamsProperty.Value) { @($provisionedStreamsProperty.Value) } else { @() }
if (@($provisionedStreams).Count -eq 0) {
    $streamProvisioning = Get-OptionalObjectPropertyValue -InputObject $provisioningState -PropertyName 'streamProvisioning'
    if ($null -ne $streamProvisioning) {
        $provisionedStreams = @($streamProvisioning.streams)
    }
}
if (@($provisionedStreams).Count -eq 0) {
    throw "Provisioning report '$ProvisioningReportPath' did not include any provisionedStreams."
}

$semanticModelSpec = New-ManifestSemanticModelSpec -ManifestInfo $manifestInfo -Manifest $manifest -TargetRows $targetRows -ProvisionedStreams $provisionedStreams -WorkspaceTarget $workspaceTarget -ResolvedModelApiName $resolvedModelApiName -ResolvedModelLabel $resolvedModelLabel -RootTableName $rootTableName
Ensure-Directory -Path (Split-Path -Parent $resolvedOutputPath)
Write-JsonFile -Path $resolvedOutputPath -Value ([pscustomobject]$semanticModelSpec)

$result = [pscustomobject]@{
    TargetKey = $workspaceTarget.TargetKey
    TargetOrg = $workspaceTarget.TargetOrg
    WorkspaceId = $workspaceTarget.WorkspaceId
    WorkspaceLabel = $workspaceTarget.WorkspaceLabel
    ModelApiName = $resolvedModelApiName
    ModelLabel = $resolvedModelLabel
    RootTableName = $rootTableName
    ObjectApiNames = @($semanticModelSpec.SemanticModelSpec.model.objectApiNames)
    OutputPath = $resolvedOutputPath
}

if ($Json) {
    $result | ConvertTo-Json -Depth 30
} else {
    Write-Output $result
}