[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetKey,
    [ValidateSet('Auto', 'Create', 'Update')]
    [string]$Action = 'Auto',
    [string]$SpecPath,
    [string]$ModelApiName,
    [string]$ModelLabel,
    [string]$Description = '',
    [string]$DataSpace = '',
    [string[]]$ObjectApiName,
    [string]$PrimaryObjectApiName,
    [string]$OutputPath,
    [switch]$Json,
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '_TableauNext.Common.ps1')

function Get-DefinitionValue {
    param(
        [object]$Definition,
        [string]$PropertyName
    )

    if ($null -eq $Definition) {
        return $null
    }

    $property = $Definition.PSObject.Properties[$PropertyName]
    if ($null -eq $property) {
        return $null
    }

    return $property.Value
}

function Get-DefinitionArrayValue {
    param(
        [object]$Definition,
        [string]$PropertyName
    )

    $value = Get-DefinitionValue -Definition $Definition -PropertyName $PropertyName
    if ($null -eq $value) {
        return @()
    }

    return @($value | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } | ForEach-Object { [string]$_ } | ForEach-Object { $_ -split '\s*[,;]\s*' } | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
}

function Get-DefinitionObjectArrayValue {
    param(
        [object]$Definition,
        [string]$PropertyName
    )

    $value = Get-DefinitionValue -Definition $Definition -PropertyName $PropertyName
    if ($null -eq $value) {
        return @()
    }

    return @($value)
}

function Get-OptionalStringValue {
    param(
        [object]$InputObject,
        [string]$PropertyName,
        [string]$DefaultValue = ''
    )

    if ($null -eq $InputObject) {
        return $DefaultValue
    }

    $property = $InputObject.PSObject.Properties[$PropertyName]
    if ($null -eq $property -or $null -eq $property.Value) {
        return $DefaultValue
    }

    return [string]$property.Value
}

function ConvertTo-SemanticObjectLabel {
    param(
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ''
    }

    $textInfo = [System.Globalization.CultureInfo]::InvariantCulture.TextInfo
    return ($Value -split '[_\s]+' | Where-Object { $_ } | ForEach-Object { $textInfo.ToTitleCase($_.ToLowerInvariant()) }) -join ' '
}

function ConvertTo-SemanticDataType {
    param(
        [object]$Field
    )

    $typeName = if ($Field.PSObject.Properties['type'] -and -not [string]::IsNullOrWhiteSpace([string]$Field.type)) {
        [string]$Field.type
    } elseif ($Field.PSObject.Properties['customFieldType'] -and -not [string]::IsNullOrWhiteSpace([string]$Field.customFieldType)) {
        [string]$Field.customFieldType
    } else {
        [string](Get-OptionalStringValue -InputObject $Field -PropertyName 'dataType')
    }

    switch ($typeName.ToLowerInvariant()) {
        'boolean' { return 'Boolean' }
        'checkbox' { return 'Boolean' }
        'date' { return 'Date' }
        'datetime' { return 'DateTime' }
        'currency' { return 'Currency' }
        'percent' { return 'Percentage' }
        'double' { return 'Number' }
        'int' { return 'Number' }
        'integer' { return 'Number' }
        'long' { return 'Number' }
        'decimal' { return 'Number' }
        'number' { return 'Number' }
        'email' { return 'Email' }
        'phone' { return 'PhoneNumber' }
        'url' { return 'Url' }
        'string' { return 'Text' }
        'textarea' { return 'Text' }
        'text' { return 'Text' }
        'picklist' { return 'Text' }
        'multipicklist' { return 'Text' }
        'reference' { return 'Text' }
        'id' { return 'Text' }
        'encryptedstring' { return 'Text' }
        default { return '' }
    }
}

function Test-IsSemanticMeasurementType {
    param(
        [string]$SemanticDataType
    )

    return $SemanticDataType -in @('Number', 'Currency', 'Percentage')
}

function New-SemanticFieldDefinition {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Field,
        [Parameter(Mandatory = $true)]
        [bool]$IsMeasurement,
        [string[]]$PrimaryKeyFields = @()
    )

    $semanticDataType = ConvertTo-SemanticDataType -Field $Field
    if ([string]::IsNullOrWhiteSpace($semanticDataType)) {
        return $null
    }

    $dataObjectFieldName = Get-OptionalStringValue -InputObject $Field -PropertyName 'dataObjectFieldName'
    if ([string]::IsNullOrWhiteSpace($dataObjectFieldName)) {
        $dataObjectFieldName = Get-OptionalStringValue -InputObject $Field -PropertyName 'name'
    }

    $fieldLabel = Get-OptionalStringValue -InputObject $Field -PropertyName 'label'
    if ([string]::IsNullOrWhiteSpace($fieldLabel)) {
        $fieldLabel = Get-OptionalStringValue -InputObject $Field -PropertyName 'sourceFieldName'
    }
    if ([string]::IsNullOrWhiteSpace($fieldLabel)) {
        $fieldLabel = Get-OptionalStringValue -InputObject $Field -PropertyName 'name'
    }
    if ([string]::IsNullOrWhiteSpace($fieldLabel)) {
        $fieldLabel = $dataObjectFieldName
    }

    $definition = [ordered]@{
        dataObjectFieldName = $dataObjectFieldName
        label = $fieldLabel
        description = Get-OptionalStringValue -InputObject $Field -PropertyName 'inlineHelpText'
        dataType = $semanticDataType
        sortOrder = 'Ascending'
        isVisible = $true
    }

    if ($semanticDataType -in @('Date', 'DateTime') -or $IsMeasurement) {
        $definition.displayCategory = 'Continuous'
    } else {
        $definition.displayCategory = 'Discrete'
    }

    if ($PrimaryKeyFields -contains $dataObjectFieldName) {
        $definition.isPrimaryKey = $true
    }

    if ($IsMeasurement) {
        $definition.aggregationType = 'None'
        $definition.directionality = 'Up'
        $definition.shouldTreatNullsAsZeros = $false
        if ($Field.PSObject.Properties['scale'] -and $null -ne $Field.scale) {
            $definition.decimalPlace = [int]$Field.scale
        }
    }

    return [pscustomobject]$definition
}

function Get-XmlNodeInnerText {
    param(
        [Parameter(Mandatory = $true)]
        [xml]$XmlDocument,
        [Parameter(Mandatory = $true)]
        [string]$XPath
    )

    $node = $XmlDocument.SelectSingleNode($XPath)
    if ($null -eq $node) {
        return ''
    }

    return [string]$node.InnerText
}

function Get-GeneratedDataObjectFieldDefinitions {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ObjectApiName
    )

    $generatedRoot = Resolve-CommandCenterPath 'salesforce/generated'
    if (-not (Test-Path -LiteralPath $generatedRoot)) {
        return @()
    }

    $candidateDirectoryNames = New-Object System.Collections.Generic.List[string]
    $candidateDirectoryNames.Add($ObjectApiName) | Out-Null
    if (-not $ObjectApiName.EndsWith('__dll')) {
        $candidateDirectoryNames.Add(('{0}__dll' -f $ObjectApiName)) | Out-Null
    }
    if ($ObjectApiName.Contains('_')) {
        $strippedObjectApiName = $ObjectApiName.Substring($ObjectApiName.IndexOf('_') + 1)
        if (-not [string]::IsNullOrWhiteSpace($strippedObjectApiName)) {
            $candidateDirectoryNames.Add($strippedObjectApiName) | Out-Null
            if (-not $strippedObjectApiName.EndsWith('__dll')) {
                $candidateDirectoryNames.Add(('{0}__dll' -f $strippedObjectApiName)) | Out-Null
            }
        }
    }

    foreach ($candidateDirectoryName in @($candidateDirectoryNames | Select-Object -Unique)) {
        $objectDirectory = @(
            Get-ChildItem -LiteralPath $generatedRoot -Directory -Recurse -Filter $candidateDirectoryName |
                Where-Object { $_.Parent -and $_.Parent.Name -eq 'objects' } |
                Select-Object -First 1
        )
        if ($objectDirectory.Count -eq 0) {
            continue
        }

        $fieldsDirectory = Join-Path $objectDirectory[0].FullName 'fields'
        if (-not (Test-Path -LiteralPath $fieldsDirectory)) {
            continue
        }

        $fieldFiles = @(Get-ChildItem -LiteralPath $fieldsDirectory -File -Filter '*.field-meta.xml' | Sort-Object Name)
        if ($fieldFiles.Count -eq 0) {
            continue
        }

        return @(
            foreach ($fieldFile in $fieldFiles) {
                $fieldXml = [xml](Get-Content -LiteralPath $fieldFile.FullName -Raw)
                $fullName = Get-XmlNodeInnerText -XmlDocument $fieldXml -XPath "/*[local-name()='CustomField']/*[local-name()='fullName']"
                if ([string]::IsNullOrWhiteSpace($fullName)) {
                    continue
                }

                $label = Get-XmlNodeInnerText -XmlDocument $fieldXml -XPath "/*[local-name()='CustomField']/*[local-name()='label']"
                $type = Get-XmlNodeInnerText -XmlDocument $fieldXml -XPath "/*[local-name()='CustomField']/*[local-name()='type']"
                $scale = Get-XmlNodeInnerText -XmlDocument $fieldXml -XPath "/*[local-name()='CustomField']/*[local-name()='scale']"
                $primaryIndexOrder = Get-XmlNodeInnerText -XmlDocument $fieldXml -XPath "/*[local-name()='CustomField']/*[local-name()='mktDataLakeFieldAttributes']/*[local-name()='primaryIndexOrder']"

                [pscustomobject]@{
                    dataObjectFieldName = $fullName
                    name = $fullName
                    label = $(if (-not [string]::IsNullOrWhiteSpace($label)) { $label } else { $fullName })
                    type = $type
                    scale = $(if ([string]::IsNullOrWhiteSpace($scale)) { $null } else { [int]$scale })
                    isPrimaryKey = (-not [string]::IsNullOrWhiteSpace($primaryIndexOrder) -and $primaryIndexOrder -ne '0')
                }
            }
        )
    }

    return @()
}

function New-SemanticDataObjectRequest {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Context,
        [Parameter(Mandatory = $true)]
        [string]$ObjectApiName,
        [string]$ObjectLabel,
        [object[]]$Fields = @(),
        [string[]]$PrimaryKeyFields = @()
    )

    $dimensions = New-Object System.Collections.Generic.List[object]
    $measurements = New-Object System.Collections.Generic.List[object]

    $fieldRows = @($Fields)
    if ($fieldRows.Count -eq 0) {
        try {
            $describe = Get-TableauNextObjectDescribe -Context $Context -ObjectName $ObjectApiName
            $fieldRows = @($describe.fields)
        } catch {
            $fieldRows = @(Get-GeneratedDataObjectFieldDefinitions -ObjectApiName $ObjectApiName)
            if ($fieldRows.Count -eq 0) {
                throw
            }
        }
    }

    foreach ($field in @($fieldRows)) {
        $fieldName = Get-OptionalStringValue -InputObject $field -PropertyName 'name'
        $dataObjectFieldName = Get-OptionalStringValue -InputObject $field -PropertyName 'dataObjectFieldName'
        if ($fieldName -eq 'Id' -or $dataObjectFieldName -eq 'Id') {
            continue
        }

        $semanticDataType = ConvertTo-SemanticDataType -Field $field
        if ([string]::IsNullOrWhiteSpace($semanticDataType)) {
            continue
        }

        $isMeasurement = Test-IsSemanticMeasurementType -SemanticDataType $semanticDataType
        $fieldDefinition = New-SemanticFieldDefinition -Field $field -IsMeasurement:$isMeasurement -PrimaryKeyFields $PrimaryKeyFields
        if ($null -eq $fieldDefinition) {
            continue
        }

        if ($isMeasurement) {
            $measurements.Add($fieldDefinition) | Out-Null
        } else {
            $dimensions.Add($fieldDefinition) | Out-Null
        }
    }

    return [ordered]@{
        label = $(if (-not [string]::IsNullOrWhiteSpace($ObjectLabel)) { $ObjectLabel } else { ConvertTo-SemanticObjectLabel -Value $ObjectApiName })
        description = ''
        dataObjectName = $ObjectApiName
        dataObjectType = 'Dlo'
        shouldIncludeAllFields = $false
        semanticDimensions = $dimensions.ToArray()
        semanticMeasurements = $measurements.ToArray()
    }
}

function Resolve-ObjectMappingRows {
    param(
        [object]$DefinitionModel,
        [string[]]$ResolvedObjectApiNames,
        [string]$ResolvedPrimaryObjectApiName
    )

    $mappingRows = @(Get-DefinitionObjectArrayValue -Definition $DefinitionModel -PropertyName 'objectMappings')
    if ($mappingRows.Count -gt 0) {
        return @(
            foreach ($row in $mappingRows) {
                [pscustomobject]@{
                    tableName = Get-OptionalStringValue -InputObject $row -PropertyName 'tableName'
                    objectApiName = Get-OptionalStringValue -InputObject $row -PropertyName 'objectApiName'
                    label = Get-OptionalStringValue -InputObject $row -PropertyName 'label'
                    primaryKeyFields = @(Get-DefinitionArrayValue -Definition $row -PropertyName 'primaryKeyFields')
                    fields = @(Get-DefinitionObjectArrayValue -Definition $row -PropertyName 'fields')
                    isPrimary = ([string](Get-OptionalStringValue -InputObject $row -PropertyName 'objectApiName') -eq $ResolvedPrimaryObjectApiName)
                }
            }
        )
    }

    return @(
        foreach ($objectApiName in @($ResolvedObjectApiNames)) {
            [pscustomobject]@{
                tableName = ''
                objectApiName = $objectApiName
                label = ConvertTo-SemanticObjectLabel -Value $objectApiName
                primaryKeyFields = @()
                fields = @()
                isPrimary = ($objectApiName -eq $ResolvedPrimaryObjectApiName)
            }
        }
    )
}

function Resolve-RelationshipDefinitions {
    param(
        [object]$DefinitionModel
    )

    return @(Get-DefinitionObjectArrayValue -Definition $DefinitionModel -PropertyName 'relationshipDefinitions')
}

function New-SemanticModelRequestBody {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Context,
        [Parameter(Mandatory = $true)]
        [object]$Workspace,
        [Parameter(Mandatory = $true)]
        [string]$ModelApiName,
        [Parameter(Mandatory = $true)]
        [string]$ModelLabel,
        [string]$Description,
        [string]$DataSpace,
        [Parameter(Mandatory = $true)]
        [object[]]$ObjectMappings
    )

    $semanticDataObjects = New-Object System.Collections.Generic.List[object]
    foreach ($mapping in @($ObjectMappings)) {
        if ([string]::IsNullOrWhiteSpace([string]$mapping.objectApiName)) {
            continue
        }

        $semanticDataObjects.Add((New-SemanticDataObjectRequest -Context $Context -ObjectApiName ([string]$mapping.objectApiName) -ObjectLabel ([string]$mapping.label) -Fields @($mapping.fields) -PrimaryKeyFields @($mapping.primaryKeyFields))) | Out-Null
    }

    $requestBody = [ordered]@{
        apiName = $ModelApiName
        label = $ModelLabel
        description = $(if (-not [string]::IsNullOrWhiteSpace($Description)) { $Description } else { '' })
        categories = @()
        queryUnrelatedDataObjects = 'Union'
        dataspace = $(if (-not [string]::IsNullOrWhiteSpace($DataSpace)) { $DataSpace } else { 'default' })
        workspaceId = $Workspace.WorkspaceId
        semanticDataObjects = $semanticDataObjects.ToArray()
        semanticRelationships = @()
        semanticCalculatedMeasurements = @()
        semanticCalculatedDimensions = @()
        semanticLogicalViews = @()
        semanticMetrics = @()
        semanticParameters = @()
        semanticGroupings = @()
    }

    return $requestBody
}

function Add-ExistingApiNamesToRequestBody {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$RequestBody,
        [Parameter(Mandatory = $true)]
        [object]$ExistingDefinition
    )

    $objectByName = @{}
    foreach ($existingObject in @($ExistingDefinition.semanticDataObjects)) {
        $objectByName[[string]$existingObject.dataObjectName] = $existingObject
    }

    function Set-DynamicPropertyValue {
        param(
            [Parameter(Mandatory = $true)]
            [object]$InputObject,
            [Parameter(Mandatory = $true)]
            [string]$PropertyName,
            $Value
        )

        if ($InputObject -is [System.Collections.IDictionary]) {
            $InputObject[$PropertyName] = $Value
            return
        }

        $property = $InputObject.PSObject.Properties[$PropertyName]
        if ($null -ne $property) {
            $property.Value = $Value
            return
        }

        Add-Member -InputObject $InputObject -NotePropertyName $PropertyName -NotePropertyValue $Value -Force
    }

    foreach ($requestObject in @($RequestBody.semanticDataObjects)) {
        $existingObject = $objectByName[[string]$requestObject.dataObjectName]
        if ($null -eq $existingObject) {
            continue
        }

        Set-DynamicPropertyValue -InputObject $requestObject -PropertyName 'apiName' -Value ([string]$existingObject.apiName)
        $dimensionByField = @{}
        foreach ($dimension in @($existingObject.semanticDimensions)) {
            $dimensionByField[[string]$dimension.dataObjectFieldName] = $dimension
        }
        foreach ($dimension in @($requestObject.semanticDimensions)) {
            $existingDimension = $dimensionByField[[string]$dimension.dataObjectFieldName]
            if ($null -ne $existingDimension) {
                Set-DynamicPropertyValue -InputObject $dimension -PropertyName 'apiName' -Value ([string]$existingDimension.apiName)
            }
        }

        $measurementByField = @{}
        foreach ($measurement in @($existingObject.semanticMeasurements)) {
            $measurementByField[[string]$measurement.dataObjectFieldName] = $measurement
        }
        foreach ($measurement in @($requestObject.semanticMeasurements)) {
            $existingMeasurement = $measurementByField[[string]$measurement.dataObjectFieldName]
            if ($null -ne $existingMeasurement) {
                Set-DynamicPropertyValue -InputObject $measurement -PropertyName 'apiName' -Value ([string]$existingMeasurement.apiName)
            }
        }
    }

    return $RequestBody
}

function Resolve-SemanticRelationshipRequests {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$RelationshipDefinitions,
        [Parameter(Mandatory = $true)]
        [object]$SemanticModelDefinition,
        [Parameter(Mandatory = $true)]
        [object[]]$ObjectMappings
    )

    if ($RelationshipDefinitions.Count -eq 0) {
        return @()
    }

    $tableToObjectName = @{}
    foreach ($mapping in @($ObjectMappings)) {
        if (-not [string]::IsNullOrWhiteSpace([string]$mapping.tableName)) {
            $tableToObjectName[[string]$mapping.tableName] = [string]$mapping.objectApiName
        }
    }

    $semanticObjectByDataObjectName = @{}
    foreach ($semanticObject in @($SemanticModelDefinition.semanticDataObjects)) {
        $semanticObjectByDataObjectName[[string]$semanticObject.dataObjectName] = $semanticObject
    }

    $requests = New-Object System.Collections.Generic.List[object]

    function Find-SemanticField {
        param(
            [Parameter(Mandatory = $true)]
            [object[]]$Fields,
            [Parameter(Mandatory = $true)]
            [string]$ReferenceName
        )

        $candidates = @(
            $ReferenceName,
            ('{0}__c' -f $ReferenceName)
        ) | Select-Object -Unique

        foreach ($candidate in $candidates) {
            $exactMatch = @($Fields | Where-Object { [string]$_.dataObjectFieldName -eq $candidate } | Select-Object -First 1)
            if ($exactMatch.Count -gt 0) {
                return $exactMatch[0]
            }
        }

        foreach ($candidate in $candidates) {
            $labelMatch = @($Fields | Where-Object { [string]$_.label -eq $candidate } | Select-Object -First 1)
            if ($labelMatch.Count -gt 0) {
                return $labelMatch[0]
            }
        }

        return $null
    }

    foreach ($relationship in @($RelationshipDefinitions)) {
        $sourceTable = Get-OptionalStringValue -InputObject $relationship -PropertyName 'sourceTable'
        $targetTable = Get-OptionalStringValue -InputObject $relationship -PropertyName 'targetTable'
        $sourceField = Get-OptionalStringValue -InputObject $relationship -PropertyName 'sourceField'
        $targetField = Get-OptionalStringValue -InputObject $relationship -PropertyName 'targetField'
        $direction = Get-OptionalStringValue -InputObject $relationship -PropertyName 'direction'

        $sourceObjectName = $(if ($tableToObjectName.ContainsKey($sourceTable)) { $tableToObjectName[$sourceTable] } else { $sourceTable })
        $targetObjectName = $(if ($tableToObjectName.ContainsKey($targetTable)) { $tableToObjectName[$targetTable] } else { $targetTable })
        $leftObject = $semanticObjectByDataObjectName[$sourceObjectName]
        $rightObject = $semanticObjectByDataObjectName[$targetObjectName]
        if ($null -eq $leftObject -or $null -eq $rightObject) {
            throw "Unable to resolve semantic relationship objects for '$sourceTable.$sourceField' -> '$targetTable.$targetField'."
        }

        $leftFields = @($leftObject.semanticDimensions) + @($leftObject.semanticMeasurements)
        $rightFields = @($rightObject.semanticDimensions) + @($rightObject.semanticMeasurements)
        $leftField = Find-SemanticField -Fields $leftFields -ReferenceName $sourceField
        $rightField = Find-SemanticField -Fields $rightFields -ReferenceName $targetField
        if ($null -eq $leftField -or $null -eq $rightField) {
            throw "Unable to resolve semantic relationship fields for '$sourceTable.$sourceField' -> '$targetTable.$targetField'."
        }

        $requests.Add([ordered]@{
            apiName = ConvertTo-TableauNextApiName -Value ('{0}_{1}_to_{2}_{3}' -f $sourceTable, $sourceField, $targetTable, $targetField)
            label = ('{0}.{1} -> {2}.{3}' -f $sourceTable, $sourceField, $targetTable, $targetField)
            leftSemanticDefinitionApiName = [string]$leftObject.apiName
            rightSemanticDefinitionApiName = [string]$rightObject.apiName
            criteria = @(
                [ordered]@{
                    leftSemanticFieldApiName = [string]$leftField.apiName
                    rightSemanticFieldApiName = [string]$rightField.apiName
                }
            )
        }) | Out-Null
    }

    return $requests.ToArray()
}

function Sync-SemanticRelationships {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Context,
        [Parameter(Mandatory = $true)]
        [string]$SemanticModelIdOrApiName,
        [Parameter(Mandatory = $true)]
        [object[]]$SemanticRelationships,
        [object[]]$ExistingRelationships = @()
    )

    $existingRelationshipByApiName = @{}
    foreach ($relationship in @($ExistingRelationships)) {
        $existingRelationshipByApiName[[string]$relationship.apiName] = $relationship
    }

    $responses = New-Object System.Collections.Generic.List[object]
    foreach ($relationship in @($SemanticRelationships)) {
        $relationshipApiName = [string]$relationship.apiName
        if ([string]::IsNullOrWhiteSpace($relationshipApiName)) {
            continue
        }

        $relativePath = if ($existingRelationshipByApiName.ContainsKey($relationshipApiName)) {
            'ssot/semantic/models/{0}/relationships/{1}' -f $SemanticModelIdOrApiName, $relationshipApiName
        } else {
            'ssot/semantic/models/{0}/relationships' -f $SemanticModelIdOrApiName
        }
        $method = if ($existingRelationshipByApiName.ContainsKey($relationshipApiName)) { 'Put' } else { 'Post' }
        try {
            $responses.Add((Invoke-TableauNextApiRequest -Context $Context -Method $method -RelativePath $relativePath -Body $relationship)) | Out-Null
        } catch {
            $message = Get-DataCloudErrorMessage -ErrorRecord $_
            throw "Failed to $($method.ToUpperInvariant()) semantic relationship '$relationshipApiName' on model '$SemanticModelIdOrApiName'. $message"
        }
    }

    return $responses.ToArray()
}

function Get-ExistingCollectionValue {
    param(
        [object]$Definition,
        [string]$PropertyName
    )

    $value = Get-DefinitionValue -Definition $Definition -PropertyName $PropertyName
    if ($null -eq $value) {
        return @()
    }

    return @($value)
}

function New-UpdateRequestBody {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$RequestBody,
        [Parameter(Mandatory = $true)]
        [object]$ExistingDefinition,
        [object[]]$SemanticRelationships = @()
    )

    return [ordered]@{
        apiName = $RequestBody.apiName
        label = $RequestBody.label
        description = $RequestBody.description
        app = Get-OptionalStringValue -InputObject $ExistingDefinition -PropertyName 'app'
        categories = @(Get-ExistingCollectionValue -Definition $ExistingDefinition -PropertyName 'categories')
        queryUnrelatedDataObjects = $(if (-not [string]::IsNullOrWhiteSpace([string](Get-DefinitionValue -Definition $ExistingDefinition -PropertyName 'queryUnrelatedDataObjects'))) { [string](Get-DefinitionValue -Definition $ExistingDefinition -PropertyName 'queryUnrelatedDataObjects') } else { $RequestBody.queryUnrelatedDataObjects })
        dataspace = $RequestBody.dataspace
        workspaceId = $(if (-not [string]::IsNullOrWhiteSpace([string](Get-DefinitionValue -Definition $ExistingDefinition -PropertyName 'workspaceId'))) { [string](Get-DefinitionValue -Definition $ExistingDefinition -PropertyName 'workspaceId') } else { $RequestBody.workspaceId })
        externalConnections = @(Get-ExistingCollectionValue -Definition $ExistingDefinition -PropertyName 'externalConnections')
        fieldsOverrides = @(Get-ExistingCollectionValue -Definition $ExistingDefinition -PropertyName 'fieldsOverrides')
        semanticDataObjects = @($RequestBody.semanticDataObjects)
        semanticRelationships = @($SemanticRelationships)
        semanticCalculatedMeasurements = @(Get-ExistingCollectionValue -Definition $ExistingDefinition -PropertyName 'semanticCalculatedMeasurements')
        semanticCalculatedDimensions = @(Get-ExistingCollectionValue -Definition $ExistingDefinition -PropertyName 'semanticCalculatedDimensions')
        semanticLogicalViews = @(Get-ExistingCollectionValue -Definition $ExistingDefinition -PropertyName 'semanticLogicalViews')
        semanticMetrics = @(Get-ExistingCollectionValue -Definition $ExistingDefinition -PropertyName 'semanticMetrics')
        semanticParameters = @(Get-ExistingCollectionValue -Definition $ExistingDefinition -PropertyName 'semanticParameters')
        semanticGroupings = @(Get-ExistingCollectionValue -Definition $ExistingDefinition -PropertyName 'semanticGroupings')
    }
}

$config = Get-TableauNextTargetConfiguration -TargetKey $TargetKey
$workspaceRows = Get-TableauNextWorkspaceRows -TargetOrg $config.TargetOrg -Limit 2000
$workspace = @($workspaceRows | Where-Object { $_.WorkspaceId -eq $config.WorkspaceId } | Select-Object -First 1)
if ($workspace.Count -eq 0) {
    throw "Workspace '$($config.WorkspaceId)' was not found for target '$TargetKey'. Re-run scripts/tableau/inspect-next-target.ps1 before attempting semantic-model work."
}

$workspace = $workspace[0]

$definition = $null
if (-not [string]::IsNullOrWhiteSpace($SpecPath)) {
    $resolvedSpecPath = if ([System.IO.Path]::IsPathRooted($SpecPath)) { $SpecPath } else { Resolve-CommandCenterPath $SpecPath }
    if (-not (Test-Path -LiteralPath $resolvedSpecPath)) {
        throw "Spec file '$resolvedSpecPath' was not found."
    }

    $definition = Read-JsonFile -Path $resolvedSpecPath
    $nestedSemanticModelSpec = Get-DefinitionValue -Definition $definition -PropertyName 'SemanticModelSpec'
    if ($null -ne $nestedSemanticModelSpec) {
        $definition = $nestedSemanticModelSpec
    }
}

$definitionModel = Get-DefinitionValue -Definition $definition -PropertyName 'model'
$definitionObjects = @(Get-DefinitionArrayValue -Definition $definitionModel -PropertyName 'objectApiNames')
if ($definitionObjects.Count -eq 0) {
    $definitionObjects = @(Get-DefinitionArrayValue -Definition $definition -PropertyName 'objectApiNames')
}

$requestedAction = switch ($Action) {
    'Create' { 'Create' }
    'Update' {
        if ([string]::IsNullOrWhiteSpace($config.SemanticModelId)) {
            throw "Target '$TargetKey' does not pin an existing semantic model, so -Action Update is not valid yet."
        }

        'Update'
    }
    default {
        if (-not [string]::IsNullOrWhiteSpace($config.SemanticModelId)) { 'Update' } else { 'Create' }
    }
}

$candidateApiName = $ModelApiName
if ([string]::IsNullOrWhiteSpace($candidateApiName)) {
    $candidateApiName = [string](Get-DefinitionValue -Definition $definitionModel -PropertyName 'apiName')
}
if ([string]::IsNullOrWhiteSpace($candidateApiName)) {
    $candidateApiName = [string](Get-DefinitionValue -Definition $definitionModel -PropertyName 'label')
}
if ([string]::IsNullOrWhiteSpace($candidateApiName)) {
    $candidateApiName = $ModelLabel
}
if ([string]::IsNullOrWhiteSpace($candidateApiName)) {
    throw 'Provide -ModelApiName or -ModelLabel, or include model.apiName or model.label in -SpecPath.'
}

$resolvedModelApiName = ConvertTo-TableauNextApiName -Value $candidateApiName
$resolvedModelLabel = $ModelLabel
if ([string]::IsNullOrWhiteSpace($resolvedModelLabel)) {
    $resolvedModelLabel = [string](Get-DefinitionValue -Definition $definitionModel -PropertyName 'label')
}
if ([string]::IsNullOrWhiteSpace($resolvedModelLabel)) {
    $resolvedModelLabel = $resolvedModelApiName
}

$resolvedDescription = $Description
if ([string]::IsNullOrWhiteSpace($resolvedDescription)) {
    $resolvedDescription = [string](Get-DefinitionValue -Definition $definitionModel -PropertyName 'description')
}

$resolvedDataSpace = $DataSpace
if ([string]::IsNullOrWhiteSpace($resolvedDataSpace)) {
    $resolvedDataSpace = [string](Get-DefinitionValue -Definition $definitionModel -PropertyName 'dataSpace')
}
if ([string]::IsNullOrWhiteSpace($resolvedDataSpace)) {
    $resolvedDataSpace = [string](Get-DefinitionValue -Definition $definitionModel -PropertyName 'dataspace')
}

$resolvedObjectApiNames = @($ObjectApiName | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } | ForEach-Object { [string]$_ } | ForEach-Object { $_ -split '\s*[,;]\s*' } | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
if ($resolvedObjectApiNames.Count -eq 0) {
    $resolvedObjectApiNames = $definitionObjects
}
if ($resolvedObjectApiNames.Count -eq 0) {
    throw 'Provide at least one -ObjectApiName, or include model.objectApiNames in -SpecPath.'
}

$resolvedObjectApiNames = @($resolvedObjectApiNames | Select-Object -Unique)
$resolvedPrimaryObjectApiName = $PrimaryObjectApiName
if ([string]::IsNullOrWhiteSpace($resolvedPrimaryObjectApiName)) {
    $resolvedPrimaryObjectApiName = [string](Get-DefinitionValue -Definition $definitionModel -PropertyName 'primaryObjectApiName')
}
if ([string]::IsNullOrWhiteSpace($resolvedPrimaryObjectApiName)) {
    $resolvedPrimaryObjectApiName = [string](Get-DefinitionValue -Definition $definitionModel -PropertyName 'primaryDataObjectApiName')
}
if ([string]::IsNullOrWhiteSpace($resolvedPrimaryObjectApiName)) {
    $resolvedPrimaryObjectApiName = $resolvedObjectApiNames[0]
}

if ($resolvedObjectApiNames -notcontains $resolvedPrimaryObjectApiName) {
    throw "Primary object '$resolvedPrimaryObjectApiName' must also appear in the semantic-model object list."
}

$workspaceReference = [ordered]@{
    workspaceId = $workspace.WorkspaceId
    workspaceDeveloperName = $workspace.DeveloperName
    workspaceLabel = $workspace.Label
}

$semanticModelSpec = [ordered]@{
    requestedAction = $requestedAction
    targetKey = $config.TargetKey
    targetOrg = $config.TargetOrg
    workspace = $workspaceReference
    model = [ordered]@{
        apiName = $resolvedModelApiName
        label = $resolvedModelLabel
        description = $resolvedDescription
        dataSpace = $resolvedDataSpace
        primaryObjectApiName = $resolvedPrimaryObjectApiName
        objectApiNames = @($resolvedObjectApiNames)
    }
    generatedFieldSource = [ordered]@{
        notes = @(
            'When live DLO describe is available, this helper derives semantic fields directly from the org.',
            'When live DLO describe returns 404, this helper falls back to repo-generated Data Cloud field metadata under salesforce/generated/.'
        )
    }
}

if ($requestedAction -eq 'Update') {
    $semanticModelSpec.existingSemanticModelId = $config.SemanticModelId
    $semanticModelSpec.existingWorkspaceAssetId = $config.WorkspaceAssetId
}

$objectMappings = @(Resolve-ObjectMappingRows -DefinitionModel $definitionModel -ResolvedObjectApiNames $resolvedObjectApiNames -ResolvedPrimaryObjectApiName $resolvedPrimaryObjectApiName)
$relationshipDefinitions = @(Resolve-RelationshipDefinitions -DefinitionModel $definitionModel)
$semanticModelSpec.model.objectMappings = @($objectMappings)
$semanticModelSpec.model.relationshipDefinitions = @($relationshipDefinitions)

$context = Get-TableauNextAccessContext -TargetOrg $config.TargetOrg
$semanticModelRequest = New-SemanticModelRequestBody -Context $context -Workspace $workspace -ModelApiName $resolvedModelApiName -ModelLabel $resolvedModelLabel -Description $resolvedDescription -DataSpace $resolvedDataSpace -ObjectMappings $objectMappings

$semanticModelSpec.supportedContract = [ordered]@{
    endpointBase = '/services/data/v66.0/ssot/semantic/models'
    notes = @(
        'This helper owns a supported semantic-layer REST request body generated from live DLO describes or repo-generated Data Cloud field metadata, plus optional manifest relationship metadata.',
        'Create uses POST /ssot/semantic/models, then resolves semanticRelationships from the created model definition and applies a full PUT update when relationshipDefinitions are present.'
    )
}

$result = [ordered]@{
    TargetKey = $config.TargetKey
    TargetOrg = $config.TargetOrg
    RequestedAction = $requestedAction
    WorkspaceValidated = $true
    WorkspaceId = $workspace.WorkspaceId
    WorkspaceDeveloperName = $workspace.DeveloperName
    WorkspaceLabel = $workspace.Label
    ExistingSemanticModelId = $config.SemanticModelId
    SemanticModelSpec = $semanticModelSpec
    SemanticModelRequest = $semanticModelRequest
    ApplyAttempted = $false
    ApplyStatus = 'DryRun'
}

if ($Apply) {
    if ($PSCmdlet.ShouldProcess(($workspace.Label), ('{0} semantic model {1}' -f $requestedAction.ToLowerInvariant(), $resolvedModelApiName))) {
        try {
            $result.ApplyAttempted = $true
            $appliedModelDefinition = $null
            $appliedModelKey = ''
            if ($requestedAction -eq 'Create') {
                $createBody = $semanticModelRequest
                try {
                    $createdModel = Invoke-TableauNextApiRequest -Context $context -Method Post -RelativePath 'ssot/semantic/models' -Body $createBody
                } catch {
                    $message = Get-DataCloudErrorMessage -ErrorRecord $_
                    if ($message -match 'workspaceId') {
                        $fallbackCreateBody = [ordered]@{}
                        foreach ($property in $createBody.Keys) {
                            if ($property -eq 'workspaceId') {
                                continue
                            }

                            $fallbackCreateBody[$property] = $createBody[$property]
                        }

                        $createdModel = Invoke-TableauNextApiRequest -Context $context -Method Post -RelativePath 'ssot/semantic/models' -Body $fallbackCreateBody
                        $result.RequestFallback = 'Retried create without workspaceId after the API rejected that property.'
                    } else {
                        throw
                    }
                }

                $appliedModelKey = $(if (-not [string]::IsNullOrWhiteSpace([string]$createdModel.id)) { [string]$createdModel.id } else { [string]$createdModel.apiName })
                $appliedModelDefinition = Get-TableauNextSemanticModelDefinition -TargetOrg $config.TargetOrg -SemanticModelIdOrApiName $appliedModelKey
                $relationshipModelKey = $(if (-not [string]::IsNullOrWhiteSpace([string]$appliedModelDefinition.apiName)) { [string]$appliedModelDefinition.apiName } else { $appliedModelKey })
                $resolvedSemanticRelationships = Resolve-SemanticRelationshipRequests -RelationshipDefinitions $relationshipDefinitions -SemanticModelDefinition $appliedModelDefinition -ObjectMappings $objectMappings
                if ($resolvedSemanticRelationships.Count -gt 0) {
                    $relationshipResponses = Sync-SemanticRelationships -Context $context -SemanticModelIdOrApiName $relationshipModelKey -SemanticRelationships $resolvedSemanticRelationships -ExistingRelationships @($appliedModelDefinition.semanticRelationships)
                    $appliedModelDefinition = Get-TableauNextSemanticModelDefinition -TargetOrg $config.TargetOrg -SemanticModelIdOrApiName $appliedModelKey
                    $result.RelationshipPatch = $relationshipResponses
                }

                $result.CreateResponse = $createdModel
            } else {
                $existingDefinition = Get-TableauNextSemanticModelDefinition -TargetOrg $config.TargetOrg -SemanticModelIdOrApiName $config.SemanticModelId
                $requestWithExistingApiNames = Add-ExistingApiNamesToRequestBody -RequestBody $semanticModelRequest -ExistingDefinition $existingDefinition
                $resolvedSemanticRelationships = Resolve-SemanticRelationshipRequests -RelationshipDefinitions $relationshipDefinitions -SemanticModelDefinition $existingDefinition -ObjectMappings $objectMappings
                $updateBody = New-UpdateRequestBody -RequestBody $requestWithExistingApiNames -ExistingDefinition $existingDefinition -SemanticRelationships @(Get-ExistingCollectionValue -Definition $existingDefinition -PropertyName 'semanticRelationships')
                $updatedModel = Invoke-TableauNextApiRequest -Context $context -Method Put -RelativePath ('ssot/semantic/models/{0}' -f $config.SemanticModelId) -Body $updateBody
                $appliedModelKey = $(if (-not [string]::IsNullOrWhiteSpace([string]$updatedModel.id)) { [string]$updatedModel.id } else { [string]$updatedModel.apiName })
                $appliedModelDefinition = Get-TableauNextSemanticModelDefinition -TargetOrg $config.TargetOrg -SemanticModelIdOrApiName $appliedModelKey
                if ($resolvedSemanticRelationships.Count -gt 0) {
                    $relationshipModelKey = $(if (-not [string]::IsNullOrWhiteSpace([string]$appliedModelDefinition.apiName)) { [string]$appliedModelDefinition.apiName } else { $appliedModelKey })
                    $relationshipResponses = Sync-SemanticRelationships -Context $context -SemanticModelIdOrApiName $relationshipModelKey -SemanticRelationships $resolvedSemanticRelationships -ExistingRelationships @($appliedModelDefinition.semanticRelationships)
                    $appliedModelDefinition = Get-TableauNextSemanticModelDefinition -TargetOrg $config.TargetOrg -SemanticModelIdOrApiName $appliedModelKey
                    $result.RelationshipPatch = $relationshipResponses
                }
                $result.UpdateResponse = $updatedModel
            }

            $validationResponse = Invoke-TableauNextApiRequest -Context $context -Method Get -RelativePath ('ssot/semantic/models/{0}/validate' -f $appliedModelKey)
            $result.ApplyStatus = $(if ($validationResponse.isValid) { 'Applied' } else { 'AppliedWithValidationIssues' })
            $result.AppliedModelId = Get-OptionalStringValue -InputObject $appliedModelDefinition -PropertyName 'id'
            $result.AppliedModelApiName = Get-OptionalStringValue -InputObject $appliedModelDefinition -PropertyName 'apiName'
            $result.Validation = $validationResponse
            $result.Response = $appliedModelDefinition
        } catch {
            $result.ApplyStatus = 'Failed'
            $result.Error = Get-DataCloudErrorMessage -ErrorRecord $_
            throw
        }
    }
}

if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
    $resolvedOutputPath = if ([System.IO.Path]::IsPathRooted($OutputPath)) { $OutputPath } else { Resolve-CommandCenterPath $OutputPath }
    Ensure-Directory -Path (Split-Path -Parent $resolvedOutputPath)
    ([pscustomobject]$result | ConvertTo-Json -Depth 20) | Set-Content -LiteralPath $resolvedOutputPath -Encoding UTF8
    Write-Host "Exported semantic-model helper output to '$resolvedOutputPath'."
}

if ($Json -or -not [string]::IsNullOrWhiteSpace($OutputPath)) {
    [pscustomobject]$result | ConvertTo-Json -Depth 20
    return
}

$summaryRecord = [pscustomobject]@{
    TargetKey = $config.TargetKey
    RequestedAction = $requestedAction
    WorkspaceLabel = $workspace.Label
    ExistingSemanticModelId = $config.SemanticModelId
    ModelApiName = $resolvedModelApiName
    ModelLabel = $resolvedModelLabel
    PrimaryObjectApiName = $resolvedPrimaryObjectApiName
    DataObjectCount = $resolvedObjectApiNames.Count
    RelationshipCount = $relationshipDefinitions.Count
    ApplyStatus = $result.ApplyStatus
}

Write-TableauNextOutput -Records @($summaryRecord) -DefaultTableFields @(
    'TargetKey',
    'RequestedAction',
    'WorkspaceLabel',
    'ExistingSemanticModelId',
    'ModelApiName',
    'PrimaryObjectApiName',
    'DataObjectCount',
    'RelationshipCount',
    'ApplyStatus'
)