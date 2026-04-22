[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ManifestPath,
    [Parameter(Mandatory = $true)]
    [string]$SourceName,
    [string]$OutputRoot,
    [string]$ObjectNamePrefix,
    [string]$ObjectNameSeparator = '_',
    [string]$ObjectNameOverridesPath,
    [string[]]$Tables,
    [int]$SampleRows = 200,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'DataCloud.Common.ps1')

function ConvertTo-XmlValue {
    param(
        [AllowNull()]
        [string]$Value
    )

    return [System.Security.SecurityElement]::Escape($(if ($null -eq $Value) { '' } else { $Value }))
}

function Get-SourcePrefix {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    $letters = ($Value -replace '[^A-Za-z0-9]', '')
    if ($letters.Length -ge 3) {
        return $letters.Substring(0, 3)
    }

    return $letters.PadRight(3, 'X')
}

function New-CompactMetadataLabel {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PreferredValue,
        [Parameter(Mandatory = $true)]
        [string]$FallbackValue,
        [int]$MaxLength = 40
    )

    if (-not [string]::IsNullOrWhiteSpace($PreferredValue) -and $PreferredValue.Length -le $MaxLength) {
        return $PreferredValue
    }

    if ($FallbackValue.Length -le $MaxLength) {
        return $FallbackValue
    }

    return $FallbackValue.Substring(0, $MaxLength)
}

function Get-ObjectNameOverrides {
    param(
        [string]$OverridesPath
    )

    $result = [ordered]@{}
    if ([string]::IsNullOrWhiteSpace($OverridesPath)) {
        return $result
    }

    $resolvedOverridesPath = (Resolve-Path $OverridesPath).Path
    $overrides = Read-JsonFile -Path $resolvedOverridesPath
    if ($null -eq $overrides) {
        return $result
    }

    foreach ($property in $overrides.PSObject.Properties) {
        if ($null -eq $property -or [string]::IsNullOrWhiteSpace([string]$property.Name) -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
            continue
        }

        $result[[string]$property.Name] = [string]$property.Value
    }

    return $result
}

function Write-Utf8File {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string[]]$Lines
    )

    $directory = Split-Path -Parent $Path
    if (-not (Test-Path $directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }

    Set-Content -Path $Path -Value $Lines -Encoding UTF8
}

function Get-TableFieldDefinitions {
    param(
        [Parameter(Mandatory = $true)]
        [object]$ManifestInfo,
        [Parameter(Mandatory = $true)]
        [object]$FileDefinition,
        [int]$SampleRows = 200
    )

    $csvPath = Resolve-DataCloudManifestCsvPath -ManifestInfo $ManifestInfo -FileDefinition $FileDefinition
    $csvFieldProfile = Get-DataCloudCsvFieldProfiles -CsvPath $csvPath -SampleRows $SampleRows -AllowHeaderOnly -ContextLabel ("Object '$([string]$FileDefinition.tableName)'")

    return [pscustomobject]@{
        csvPath = $csvPath
        lineCount = $csvFieldProfile.lineCount
        estimatedDataRows = $csvFieldProfile.estimatedDataRows
        fields = $csvFieldProfile.fields
    }
}

$manifestInfo = Get-DataCloudManifestInfo -ManifestPath $ManifestPath
$manifest = $manifestInfo.Content
$datasetName = if ([string]::IsNullOrWhiteSpace($manifest.datasetName)) { $SourceName } else { [string]$manifest.datasetName }
$selectedTables = if ($Tables -and $Tables.Count -gt 0) { @($Tables) } else { @($manifest.files | ForEach-Object { [string]$_.tableName }) }
$defaultObjectCategory = 'Salesforce_SFDCReferenceModel_0_93.Engagement'
$objectNameOverrides = Get-ObjectNameOverrides -OverridesPath $ObjectNameOverridesPath

if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $safeSourceName = New-MetadataSafeName -Value $SourceName
    $OutputRoot = Resolve-CommandCenterPath (Join-Path 'salesforce/generated' $safeSourceName)
}

$resolvedOutputRoot = [System.IO.Path]::GetFullPath($OutputRoot)
if ((Test-Path $resolvedOutputRoot) -and -not $Force) {
    $existingGeneratedFolders = @('dataConnectorIngestApis', 'externalDataConnectors', 'mktDataSources', 'dataSourceObjects', 'mktDataTranObjects', 'objects', 'dataStreamDefinitions', 'objectSourceTargetMaps') |
        ForEach-Object { Join-Path $resolvedOutputRoot $_ } |
        Where-Object { Test-Path $_ }
    if ($existingGeneratedFolders.Count -gt 0) {
        throw "Output root '$resolvedOutputRoot' already contains Data Cloud metadata folders. Use -Force to overwrite generated files."
    }
}

$sourceComponentName = New-MetadataSafeName -Value $SourceName
$sourcePrefix = Get-SourcePrefix -Value $sourceComponentName
$externalConnectorObjects = New-Object System.Collections.Generic.List[object]
$generatedFiles = New-Object System.Collections.Generic.List[string]
$generatedTargets = New-Object System.Collections.Generic.List[object]

foreach ($tableName in $selectedTables) {
    $fileDefinition = @($manifest.files | Where-Object { $_.tableName -eq $tableName } | Select-Object -First 1)
    if ($fileDefinition.Count -eq 0) {
        throw "Table '$tableName' was not found in manifest '$($manifestInfo.Path)'."
    }

    $objectEndpointName = if ($objectNameOverrides.Contains($tableName)) {
        [string]$objectNameOverrides[$tableName]
    } else {
        Resolve-DataCloudManifestObjectName -TableName $tableName -ObjectNamePrefix $ObjectNamePrefix -ObjectNameSeparator $ObjectNameSeparator
    }
    $transportObjectName = New-MetadataSafeName -Value $objectEndpointName
    $dataSourceObjectName = '{0}_dll' -f $transportObjectName
    $dataLakeObjectName = '{0}__dll' -f $transportObjectName
    $streamComponentName = $transportObjectName
    $streamLabel = New-CompactMetadataLabel -PreferredValue ('{0} - {1}' -f $datasetName, $tableName) -FallbackValue $transportObjectName

    $tableMetadata = Get-TableFieldDefinitions -ManifestInfo $manifestInfo -FileDefinition $fileDefinition[0] -SampleRows $SampleRows
    $joinGraphEntry = @($manifest.joinGraph | Where-Object { $_.tableName -eq $tableName } | Select-Object -First 1)
    $primaryKeys = if ($joinGraphEntry.Count -gt 0 -and $null -ne $joinGraphEntry[0].primaryKey) {
        @($joinGraphEntry[0].primaryKey)
    } else {
        @()
    }

    $externalConnectorObjects.Add([pscustomobject]@{
        tableName = $tableName
        objectEndpointName = $objectEndpointName
        transportObjectName = $transportObjectName
        dataSourceObjectName = $dataSourceObjectName
        dataLakeObjectName = $dataLakeObjectName
        streamComponentName = $streamComponentName
        streamLabel = $streamLabel
        csvPath = $tableMetadata.csvPath
        fields = $tableMetadata.fields
        primaryKeys = $primaryKeys
    }) | Out-Null

    $dataSourceObjectPath = Join-Path $resolvedOutputRoot ('dataSourceObjects\{0}.dataSourceObject-meta.xml' -f $dataSourceObjectName)
    Write-Utf8File -Path $dataSourceObjectPath -Lines @(
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<DataSourceObject xmlns="http://soap.sforce.com/2006/04/metadata">',
        ('    <dataSource>{0}</dataSource>' -f (ConvertTo-XmlValue $sourceComponentName)),
        ('    <externalRecordIdentifier>{0}</externalRecordIdentifier>' -f (ConvertTo-XmlValue $objectEndpointName)),
        ('    <masterLabel>{0}</masterLabel>' -f (ConvertTo-XmlValue $objectEndpointName)),
        '    <storageType>LOCAL</storageType>',
        '    <templateVersion>1</templateVersion>',
        '</DataSourceObject>'
    )
    $generatedFiles.Add($dataSourceObjectPath) | Out-Null

    $mktDataTranObjectPath = Join-Path $resolvedOutputRoot ('mktDataTranObjects\{0}.mktDataTranObject-meta.xml' -f $transportObjectName)
    $mktDataTranObjectLines = New-Object System.Collections.Generic.List[string]
    $mktDataTranObjectLines.Add('<?xml version="1.0" encoding="UTF-8"?>') | Out-Null
    $mktDataTranObjectLines.Add('<MktDataTranObject xmlns="http://soap.sforce.com/2006/04/metadata">') | Out-Null
    $mktDataTranObjectLines.Add(('    <connector>{0}</connector>' -f (ConvertTo-XmlValue $sourceComponentName))) | Out-Null
    $mktDataTranObjectLines.Add('    <creationType>Custom</creationType>') | Out-Null
    $mktDataTranObjectLines.Add(('    <dataSource>{0}</dataSource>' -f (ConvertTo-XmlValue $sourceComponentName))) | Out-Null
    $mktDataTranObjectLines.Add(('    <dataSourceObject>{0}</dataSourceObject>' -f (ConvertTo-XmlValue $dataSourceObjectName))) | Out-Null
    $mktDataTranObjectLines.Add(('    <masterLabel>{0}</masterLabel>' -f (ConvertTo-XmlValue $streamLabel))) | Out-Null
    foreach ($field in @($tableMetadata.fields)) {
        $primaryIndexOrder = if ($primaryKeys -contains $field.name) { 1 } else { 0 }
        $mktDataTranObjectLines.Add('    <mktDataTranFields>') | Out-Null
        $mktDataTranObjectLines.Add(('        <fullName>{0}</fullName>' -f (ConvertTo-XmlValue $field.name))) | Out-Null
        $mktDataTranObjectLines.Add('        <creationType>Custom</creationType>') | Out-Null
        $mktDataTranObjectLines.Add(('        <datatype>{0}</datatype>' -f $field.dataType)) | Out-Null
        $mktDataTranObjectLines.Add(('        <externalName>{0}</externalName>' -f (ConvertTo-XmlValue $field.name))) | Out-Null
        $mktDataTranObjectLines.Add('        <isDataRequired>false</isDataRequired>') | Out-Null
        $mktDataTranObjectLines.Add('        <length>0</length>') | Out-Null
        $mktDataTranObjectLines.Add(('        <masterLabel>{0}</masterLabel>' -f (ConvertTo-XmlValue $field.name))) | Out-Null
        $mktDataTranObjectLines.Add('        <precision>0</precision>') | Out-Null
        $mktDataTranObjectLines.Add(('        <primaryIndexOrder>{0}</primaryIndexOrder>' -f $primaryIndexOrder)) | Out-Null
        $mktDataTranObjectLines.Add('        <scale>0</scale>') | Out-Null
        $mktDataTranObjectLines.Add('        <sequence>0</sequence>') | Out-Null
        $mktDataTranObjectLines.Add('    </mktDataTranFields>') | Out-Null
    }
    $mktDataTranObjectLines.Add(('    <objectCategory>{0}</objectCategory>' -f (ConvertTo-XmlValue $defaultObjectCategory))) | Out-Null
    $mktDataTranObjectLines.Add('</MktDataTranObject>') | Out-Null
    Write-Utf8File -Path $mktDataTranObjectPath -Lines @($mktDataTranObjectLines)
    $generatedFiles.Add($mktDataTranObjectPath) | Out-Null

    $dataLakeObjectPath = Join-Path $resolvedOutputRoot ('objects\{0}\{0}.object-meta.xml' -f $dataLakeObjectName)
    Write-Utf8File -Path $dataLakeObjectPath -Lines @(
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">',
        ('    <label>{0}</label>' -f (ConvertTo-XmlValue $streamLabel)),
        '    <mktDataLakeAttributes>',
        '        <creationType>Custom</creationType>',
        '        <isEnabled>true</isEnabled>',
        ('        <objectCategory>{0}</objectCategory>' -f (ConvertTo-XmlValue $defaultObjectCategory)),
        '    </mktDataLakeAttributes>',
        '</CustomObject>'
    )
    $generatedFiles.Add($dataLakeObjectPath) | Out-Null

    foreach ($field in @($tableMetadata.fields)) {
        $fieldPath = Join-Path $resolvedOutputRoot ('objects\{0}\fields\{1}__c.field-meta.xml' -f $dataLakeObjectName, $field.apiName)
        $fieldLines = New-Object System.Collections.Generic.List[string]
        $fieldLines.Add('<?xml version="1.0" encoding="UTF-8"?>') | Out-Null
        $fieldLines.Add('<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">') | Out-Null
        $fieldLines.Add(('    <fullName>{0}__c</fullName>' -f (ConvertTo-XmlValue $field.apiName))) | Out-Null
        $fieldLines.Add(('    <label>{0}</label>' -f (ConvertTo-XmlValue $field.name))) | Out-Null
        switch ($field.customFieldType) {
            'Text' {
                $fieldLines.Add('    <length>60</length>') | Out-Null
            }
            'Checkbox' {
                $fieldLines.Add('    <defaultValue>false</defaultValue>') | Out-Null
            }
            'Number' {
                $fieldLines.Add('    <precision>18</precision>') | Out-Null
                $fieldLines.Add('    <scale>6</scale>') | Out-Null
            }
        }
        $fieldLines.Add('    <mktDataLakeFieldAttributes>') | Out-Null
        $fieldLines.Add('        <definitionCreationType>Custom</definitionCreationType>') | Out-Null
        $fieldLines.Add(('        <externalName>{0}</externalName>' -f (ConvertTo-XmlValue $field.apiName))) | Out-Null
        $fieldLines.Add('        <isEventDate>false</isEventDate>') | Out-Null
        $fieldLines.Add('        <isInternalOrganization>false</isInternalOrganization>') | Out-Null
        $fieldLines.Add('        <isRecordModified>false</isRecordModified>') | Out-Null
        if ($primaryKeys -contains $field.name) {
            $fieldLines.Add('        <primaryIndexOrder>1</primaryIndexOrder>') | Out-Null
        }
        $fieldLines.Add('        <usageTag>NONE</usageTag>') | Out-Null
        $fieldLines.Add('    </mktDataLakeFieldAttributes>') | Out-Null
        if ($field.customFieldType -ne 'Checkbox') {
            $fieldLines.Add('    <required>false</required>') | Out-Null
        }
        $fieldLines.Add(('    <type>{0}</type>' -f $field.customFieldType)) | Out-Null
        $fieldLines.Add('</CustomField>') | Out-Null
        Write-Utf8File -Path $fieldPath -Lines @($fieldLines)
        $generatedFiles.Add($fieldPath) | Out-Null
    }

    foreach ($primaryKey in @($tableMetadata.fields | Where-Object { $primaryKeys -contains $_.name })) {
        $keyQualifierApiName = New-MetadataSafeName -Value ('KQ_{0}' -f $primaryKey.apiName) -MaxLength 37
        $keyQualifierPath = Join-Path $resolvedOutputRoot ('objects\{0}\fields\{1}__c.field-meta.xml' -f $dataLakeObjectName, $keyQualifierApiName)
        Write-Utf8File -Path $keyQualifierPath -Lines @(
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">',
            ('    <fullName>{0}__c</fullName>' -f (ConvertTo-XmlValue $keyQualifierApiName)),
            ('    <label>{0}</label>' -f (ConvertTo-XmlValue $keyQualifierApiName)),
            '    <length>60</length>',
            '    <mktDataLakeFieldAttributes>',
            '        <definitionCreationType>System</definitionCreationType>',
            ('        <externalName>{0}</externalName>' -f (ConvertTo-XmlValue $keyQualifierApiName)),
            '        <isEventDate>false</isEventDate>',
            '        <isInternalOrganization>false</isInternalOrganization>',
            '        <isRecordModified>false</isRecordModified>',
            '        <usageTag>KEY_QUALIFIER</usageTag>',
            '    </mktDataLakeFieldAttributes>',
            '    <required>false</required>',
            '    <type>Text</type>',
            '</CustomField>'
        )
        $generatedFiles.Add($keyQualifierPath) | Out-Null
    }

    foreach ($systemField in @(
        [pscustomobject]@{ apiName = 'DataSourceObject'; label = 'Data Source Object'; externalName = 'DataSourceObject' },
        [pscustomobject]@{ apiName = 'DataSource'; label = 'Data Source'; externalName = 'DataSource' },
        [pscustomobject]@{ apiName = 'InternalOrganization'; label = 'Internal Organization'; externalName = 'InternalOrganization' },
        [pscustomobject]@{ apiName = 'cdp_sys_SourceVersion'; label = 'cdp_sys_SourceVersion'; externalName = 'cdp_sys_SourceVersion' }
    )) {
        $systemFieldPath = Join-Path $resolvedOutputRoot ('objects\{0}\fields\{1}__c.field-meta.xml' -f $dataLakeObjectName, $systemField.apiName)
        Write-Utf8File -Path $systemFieldPath -Lines @(
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">',
            ('    <fullName>{0}__c</fullName>' -f (ConvertTo-XmlValue $systemField.apiName)),
            ('    <label>{0}</label>' -f (ConvertTo-XmlValue $systemField.label)),
            '    <length>60</length>',
            '    <mktDataLakeFieldAttributes>',
            '        <definitionCreationType>System</definitionCreationType>',
            ('        <externalName>{0}</externalName>' -f (ConvertTo-XmlValue $systemField.externalName)),
            '        <isEventDate>false</isEventDate>',
            '        <isInternalOrganization>false</isInternalOrganization>',
            '        <isRecordModified>false</isRecordModified>',
            '        <usageTag>NONE</usageTag>',
            '    </mktDataLakeFieldAttributes>',
            '    <required>false</required>',
            '    <type>Text</type>',
            '</CustomField>'
        )
        $generatedFiles.Add($systemFieldPath) | Out-Null
    }

    $dataStreamDefinitionPath = Join-Path $resolvedOutputRoot ('dataStreamDefinitions\{0}.dataStreamDefinition-meta.xml' -f $streamComponentName)
    Write-Utf8File -Path $dataStreamDefinitionPath -Lines @(
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<DataStreamDefinition xmlns="http://soap.sforce.com/2006/04/metadata">',
        '    <areHeadersIncludedInFile>false</areHeadersIncludedInFile>',
        '    <bulkIngest>false</bulkIngest>',
        '    <creationType>Custom</creationType>',
        ('    <dataConnector>{0}</dataConnector>' -f (ConvertTo-XmlValue $sourceComponentName)),
        '    <dataConnectorType>IngestApi</dataConnectorType>',
        '    <dataExtractMethods>FULL_REFRESH</dataExtractMethods>',
        '    <dataPlatformDataSetItemName>INGESTAPI</dataPlatformDataSetItemName>',
        ('    <dataSource>{0}</dataSource>' -f (ConvertTo-XmlValue $sourceComponentName)),
        '    <isLimitedToNewFiles>false</isLimitedToNewFiles>',
        '    <isMissingFileFailure>false</isMissingFileFailure>',
        ('    <masterLabel>{0}</masterLabel>' -f (ConvertTo-XmlValue $streamLabel)),
        ('    <mktDataLakeObject>{0}</mktDataLakeObject>' -f (ConvertTo-XmlValue $dataLakeObjectName)),
        ('    <mktDataTranObject>{0}</mktDataTranObject>' -f (ConvertTo-XmlValue $transportObjectName)),
        '</DataStreamDefinition>'
    )
    $generatedFiles.Add($dataStreamDefinitionPath) | Out-Null

    $objectSourceTargetMapPath = Join-Path $resolvedOutputRoot ('objectSourceTargetMaps\{0}_map_{1}.objectSourceTargetMap-meta.xml' -f $transportObjectName, $transportObjectName)
    $objectSourceTargetMapLines = New-Object System.Collections.Generic.List[string]
    $objectSourceTargetMapLines.Add('<?xml version="1.0" encoding="UTF-8"?>') | Out-Null
    $objectSourceTargetMapLines.Add('<ObjectSourceTargetMap xmlns="http://soap.sforce.com/2006/04/metadata" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">') | Out-Null
    $objectSourceTargetMapLines.Add('    <creationType>Custom</creationType>') | Out-Null
    foreach ($field in @($tableMetadata.fields)) {
        $objectSourceTargetMapLines.Add('    <fieldSourceTargetMaps>') | Out-Null
        $objectSourceTargetMapLines.Add('        <creationType>Custom</creationType>') | Out-Null
        $objectSourceTargetMapLines.Add('        <filterApplied>false</filterApplied>') | Out-Null
        $objectSourceTargetMapLines.Add('        <isSourceFormula>false</isSourceFormula>') | Out-Null
        $objectSourceTargetMapLines.Add(('        <sourceField>{0}.{1}__c</sourceField>' -f (ConvertTo-XmlValue $transportObjectName), (ConvertTo-XmlValue $field.apiName))) | Out-Null
        $objectSourceTargetMapLines.Add(('        <sourceFormula>{0}</sourceFormula>' -f (ConvertTo-XmlValue $field.name))) | Out-Null
        $objectSourceTargetMapLines.Add(('        <targetField>{0}.{1}__c</targetField>' -f (ConvertTo-XmlValue $dataLakeObjectName), (ConvertTo-XmlValue $field.apiName))) | Out-Null
        $objectSourceTargetMapLines.Add('    </fieldSourceTargetMaps>') | Out-Null
    }
    foreach ($systemMap in @(
        [pscustomobject]@{ formula = ('&quot;{0}&quot;' -f (ConvertTo-XmlValue $streamComponentName)); targetField = ('{0}.DataSourceObject__c' -f $dataLakeObjectName) },
        [pscustomobject]@{ formula = ('&quot;{0}&quot;' -f (ConvertTo-XmlValue $sourceComponentName)); targetField = ('{0}.DataSource__c' -f $dataLakeObjectName) }
    )) {
        $objectSourceTargetMapLines.Add('    <fieldSourceTargetMaps>') | Out-Null
        $objectSourceTargetMapLines.Add('        <creationType>System</creationType>') | Out-Null
        $objectSourceTargetMapLines.Add('        <filterApplied>false</filterApplied>') | Out-Null
        $objectSourceTargetMapLines.Add('        <isSourceFormula>true</isSourceFormula>') | Out-Null
        $objectSourceTargetMapLines.Add('        <sourceField xsi:nil="true"/>') | Out-Null
        $objectSourceTargetMapLines.Add(('        <sourceFormula>{0}</sourceFormula>' -f $systemMap.formula)) | Out-Null
        $objectSourceTargetMapLines.Add(('        <targetField>{0}</targetField>' -f $systemMap.targetField)) | Out-Null
        $objectSourceTargetMapLines.Add('    </fieldSourceTargetMaps>') | Out-Null
    }
    $objectSourceTargetMapLines.Add(('    <masterLabel>{0}_map_{1}</masterLabel>' -f (ConvertTo-XmlValue $transportObjectName), (ConvertTo-XmlValue $transportObjectName))) | Out-Null
    $objectSourceTargetMapLines.Add(('    <sourceObjectName>{0}</sourceObjectName>' -f (ConvertTo-XmlValue $transportObjectName))) | Out-Null
    $objectSourceTargetMapLines.Add(('    <targetObjectName>{0}</targetObjectName>' -f (ConvertTo-XmlValue $dataLakeObjectName))) | Out-Null
    $objectSourceTargetMapLines.Add('</ObjectSourceTargetMap>') | Out-Null
    Write-Utf8File -Path $objectSourceTargetMapPath -Lines @($objectSourceTargetMapLines)
    $generatedFiles.Add($objectSourceTargetMapPath) | Out-Null

    $generatedTargets.Add([pscustomobject]@{
        tableName = $tableName
        objectName = $objectEndpointName
        objectNameOverridden = $objectNameOverrides.Contains($tableName)
        transportObjectName = $transportObjectName
        dataSourceObjectName = $dataSourceObjectName
        dataLakeObjectName = $dataLakeObjectName
        streamLabel = $streamLabel
        csvPath = $tableMetadata.csvPath
        lineCount = $tableMetadata.lineCount
        estimatedDataRows = $tableMetadata.estimatedDataRows
        fields = $tableMetadata.fields
        primaryKeys = $primaryKeys
        dataStreamDefinition = $streamComponentName
    }) | Out-Null
}

$dataConnectorIngestApiPath = Join-Path $resolvedOutputRoot ('dataConnectorIngestApis\{0}.dataConnectorIngestApi-meta.xml' -f $sourceComponentName)
Write-Utf8File -Path $dataConnectorIngestApiPath -Lines @(
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<DataConnectorIngestApi xmlns="http://soap.sforce.com/2006/04/metadata">',
    ('    <masterLabel>{0}</masterLabel>' -f (ConvertTo-XmlValue $SourceName)),
    ('    <sourceName>{0}</sourceName>' -f (ConvertTo-XmlValue $SourceName)),
    '</DataConnectorIngestApi>'
)
$generatedFiles.Add($dataConnectorIngestApiPath) | Out-Null

$dataSourcePath = Join-Path $resolvedOutputRoot ('mktDataSources\{0}.dataSource-meta.xml' -f $sourceComponentName)
Write-Utf8File -Path $dataSourcePath -Lines @(
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<DataSource xmlns="http://soap.sforce.com/2006/04/metadata">',
    ('    <masterLabel>{0}</masterLabel>' -f (ConvertTo-XmlValue $sourceComponentName)),
    ('    <prefix>{0}</prefix>' -f (ConvertTo-XmlValue $sourcePrefix)),
    '</DataSource>'
)
$generatedFiles.Add($dataSourcePath) | Out-Null

$externalDataConnectorPath = Join-Path $resolvedOutputRoot ('externalDataConnectors\{0}.externalDataConnector-meta.xml' -f $sourceComponentName)
$externalDataConnectorLines = New-Object System.Collections.Generic.List[string]
$externalDataConnectorLines.Add('<?xml version="1.0" encoding="UTF-8"?>') | Out-Null
$externalDataConnectorLines.Add('<ExternalDataConnector xmlns="http://soap.sforce.com/2006/04/metadata">') | Out-Null
$externalDataConnectorLines.Add('    <dataConnectionStatus>Connected</dataConnectionStatus>') | Out-Null
$externalDataConnectorLines.Add(('    <dataConnectorConfiguration>{0}</dataConnectorConfiguration>' -f (ConvertTo-XmlValue $sourceComponentName))) | Out-Null
$externalDataConnectorLines.Add('    <dataConnectorType>IngestApi</dataConnectorType>') | Out-Null
$externalDataConnectorLines.Add('    <dataPlatform>Ingest_Api</dataPlatform>') | Out-Null
foreach ($objectDefinition in $externalConnectorObjects.ToArray()) {
    $externalDataConnectorLines.Add('    <externalDataTranObjects>') | Out-Null
    $externalDataConnectorLines.Add(('        <fullName>{0}</fullName>' -f (ConvertTo-XmlValue $objectDefinition.objectEndpointName))) | Out-Null
    $externalDataConnectorLines.Add('        <availabilityStatus>In_Use</availabilityStatus>') | Out-Null
    $externalDataConnectorLines.Add('        <creationType>Custom</creationType>') | Out-Null
    foreach ($field in @($objectDefinition.fields)) {
        $primaryIndexOrder = if ($objectDefinition.primaryKeys -contains $field.name) { 1 } else { 0 }
        $externalDataConnectorLines.Add('        <externalDataTranFields>') | Out-Null
        $externalDataConnectorLines.Add(('            <fullName>{0}</fullName>' -f (ConvertTo-XmlValue $field.apiName))) | Out-Null
        $externalDataConnectorLines.Add('            <creationType>Custom</creationType>') | Out-Null
        $externalDataConnectorLines.Add(('            <datatype>{0}</datatype>' -f $field.dataType)) | Out-Null
        $externalDataConnectorLines.Add(('            <externalName>{0}</externalName>' -f (ConvertTo-XmlValue $field.apiName))) | Out-Null
        $externalDataConnectorLines.Add('            <isCurrencyIsoCode>false</isCurrencyIsoCode>') | Out-Null
        $externalDataConnectorLines.Add('            <isDataRequired>false</isDataRequired>') | Out-Null
        $externalDataConnectorLines.Add('            <length>0</length>') | Out-Null
        $externalDataConnectorLines.Add(('            <masterLabel>{0}</masterLabel>' -f (ConvertTo-XmlValue $field.name))) | Out-Null
        $externalDataConnectorLines.Add(('            <mktDataTranField>{0}.{1}__c</mktDataTranField>' -f (ConvertTo-XmlValue $objectDefinition.transportObjectName), (ConvertTo-XmlValue $field.apiName))) | Out-Null
        $externalDataConnectorLines.Add('            <precision>0</precision>') | Out-Null
        $externalDataConnectorLines.Add(('            <primaryIndexOrder>{0}</primaryIndexOrder>' -f $primaryIndexOrder)) | Out-Null
        $externalDataConnectorLines.Add('            <scale>0</scale>') | Out-Null
        $externalDataConnectorLines.Add('            <sequence>0</sequence>') | Out-Null
        $externalDataConnectorLines.Add('        </externalDataTranFields>') | Out-Null
    }
    $externalDataConnectorLines.Add(('        <masterLabel>{0}</masterLabel>' -f (ConvertTo-XmlValue $objectDefinition.streamLabel))) | Out-Null
    $externalDataConnectorLines.Add(('        <mktDataTranObject>{0}</mktDataTranObject>' -f (ConvertTo-XmlValue $objectDefinition.transportObjectName))) | Out-Null
    $externalDataConnectorLines.Add(('        <objectCategory>{0}</objectCategory>' -f (ConvertTo-XmlValue $defaultObjectCategory))) | Out-Null
    $externalDataConnectorLines.Add('    </externalDataTranObjects>') | Out-Null
}
$externalDataConnectorLines.Add(('    <masterLabel>{0}</masterLabel>' -f (ConvertTo-XmlValue $SourceName))) | Out-Null
$externalDataConnectorLines.Add('</ExternalDataConnector>') | Out-Null
Write-Utf8File -Path $externalDataConnectorPath -Lines @($externalDataConnectorLines)
$generatedFiles.Add($externalDataConnectorPath) | Out-Null

Write-Output ([pscustomobject]@{
    manifestPath = $manifestInfo.Path
    sourceName = $SourceName
    outputRoot = $resolvedOutputRoot
    reviewPath = $resolvedOutputRoot
    generatedFileCount = $generatedFiles.Count
    generatedFiles = $generatedFiles.ToArray()
    tables = $generatedTargets.ToArray()
})