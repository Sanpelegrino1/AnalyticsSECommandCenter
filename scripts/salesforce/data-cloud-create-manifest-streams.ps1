[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ManifestPath,
    [Parameter(Mandatory = $true)]
    [string]$TargetOrg,
    [Parameter(Mandatory = $true)]
    [string]$SourceName,
    [string]$ObjectNamePrefix,
    [string]$ObjectNameSeparator = '_',
    [string[]]$Tables,
    [string]$OutputRoot,
    [int]$SampleRows = 200,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'DataCloud.Common.ps1')

function Get-SsotFieldDataType {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Field
    )

    switch ([string]$Field.customFieldType) {
        'Checkbox' { return 'Boolean' }
        'Date' { return 'Date' }
        'DateTime' { return 'DateTime' }
        'Number' { return 'Number' }
        default { return 'Text' }
    }
}

function New-QueryString {
    param(
        [hashtable]$Values
    )

    if ($null -eq $Values -or $Values.Count -eq 0) {
        return ''
    }

    $pairs = foreach ($key in $Values.Keys) {
        $value = $Values[$key]
        if ($null -eq $value -or [string]::IsNullOrWhiteSpace([string]$value)) {
            continue
        }

        '{0}={1}' -f [Uri]::EscapeDataString([string]$key), [Uri]::EscapeDataString([string]$value)
    }

    if (@($pairs).Count -eq 0) {
        return ''
    }

    return '?' + ($pairs -join '&')
}

function Invoke-SalesforceJsonRequest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InstanceUrl,
        [Parameter(Mandatory = $true)]
        [string]$AccessToken,
        [Parameter(Mandatory = $true)]
        [ValidateSet('Get', 'Post', 'Put', 'Patch', 'Delete')]
        [string]$Method,
        [Parameter(Mandatory = $true)]
        [string]$RelativePath,
        [hashtable]$Query,
        $Body
    )

    $uri = '{0}{1}{2}' -f $InstanceUrl.TrimEnd('/'), $RelativePath, (New-QueryString -Values $Query)
    $headers = @{ Authorization = 'Bearer {0}' -f $AccessToken }

    try {
        if ($null -ne $Body) {
            $payload = $Body | ConvertTo-Json -Depth 30
            return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -ContentType 'application/json' -Body $payload
        }

        return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers
    } catch {
        throw (Get-DataCloudErrorMessage -ErrorRecord $_)
    }
}

function Get-IngestConnector {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InstanceUrl,
        [Parameter(Mandatory = $true)]
        [string]$AccessToken,
        [Parameter(Mandatory = $true)]
        [string]$SourceName
    )

    $response = Invoke-SalesforceJsonRequest -InstanceUrl $InstanceUrl -AccessToken $AccessToken -Method Get -RelativePath '/services/data/v62.0/ssot/connections' -Query @{ connectorType = 'IngestApi'; limit = 200 }
    $connections = @($response.connections)
    $connector = @($connections | Where-Object { $_.name -eq $SourceName -or $_.label -eq $SourceName } | Select-Object -First 1)
    if ($connector.Count -eq 0) {
        $connector = @($connections | Where-Object { $_.name -like ($SourceName + '*') } | Select-Object -First 1)
    }

    if ($connector.Count -eq 0) {
        throw "Unable to find Ingest API connector '$SourceName' via /ssot/connections."
    }

    return $connector[0]
}

function Get-NormalizedAbsolutePath {
    param(
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ''
    }

    if ([System.IO.Path]::IsPathRooted($Value)) {
        return [System.IO.Path]::GetFullPath($Value)
    }

    return [System.IO.Path]::GetFullPath((Resolve-CommandCenterPath $Value))
}

function Get-StreamEventNames {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Stream
    )

    $connectorInfoProperty = $Stream.PSObject.Properties['connectorInfo']
    if ($null -eq $connectorInfoProperty -or $null -eq $connectorInfoProperty.Value) {
        return @()
    }

    $connectorDetailsProperty = $connectorInfoProperty.Value.PSObject.Properties['connectorDetails']
    if ($null -eq $connectorDetailsProperty -or $null -eq $connectorDetailsProperty.Value) {
        return @()
    }

    $eventsProperty = $connectorDetailsProperty.Value.PSObject.Properties['events']
    if ($null -eq $eventsProperty -or $null -eq $eventsProperty.Value) {
        return @()
    }

    return @(
        @($eventsProperty.Value) |
            Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } |
            ForEach-Object { [string]$_ }
    )
}

function Get-StreamAcceptedObjectNames {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Stream
    )

    $names = New-Object System.Collections.Generic.List[string]
    foreach ($eventName in @(Get-StreamEventNames -Stream $Stream)) {
        if (-not [string]::IsNullOrWhiteSpace($eventName)) {
            $names.Add([string]$eventName) | Out-Null
        }
    }

    $dataLakeObjectInfoProperty = $Stream.PSObject.Properties['dataLakeObjectInfo']
    if ($null -ne $dataLakeObjectInfoProperty -and $null -ne $dataLakeObjectInfoProperty.Value) {
        foreach ($propertyName in @('label', 'name')) {
            $property = $dataLakeObjectInfoProperty.Value.PSObject.Properties[$propertyName]
            if ($null -eq $property -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
                continue
            }

            $candidateName = [string]$property.Value
            if ($propertyName -eq 'name' -and $candidateName.EndsWith('__dll')) {
                $candidateName = $candidateName.Substring(0, $candidateName.Length - 5)
            }

            if (-not [string]::IsNullOrWhiteSpace($candidateName)) {
                $names.Add($candidateName) | Out-Null
            }
        }
    }

    return @($names | Select-Object -Unique)
}

function Get-ExistingStreams {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InstanceUrl,
        [Parameter(Mandatory = $true)]
        [string]$AccessToken,
        [Parameter(Mandatory = $true)]
        [string]$ConnectorId
    )

    $response = Invoke-SalesforceJsonRequest -InstanceUrl $InstanceUrl -AccessToken $AccessToken -Method Get -RelativePath '/services/data/v62.0/ssot/data-streams' -Query @{ connectorId = $ConnectorId; limit = 200 }
    return @($response.dataStreams)
}

function Compare-SchemaDefinition {
    param(
        [Parameter(Mandatory = $true)]
        [object]$ExistingSchema,
        [Parameter(Mandatory = $true)]
        [object]$ExpectedSchema
    )

    $existingFieldsByName = [ordered]@{}
    foreach ($field in @($ExistingSchema.fields)) {
        $existingFieldsByName[[string]$field.name] = [string]$field.dataType
    }

    $missingFields = New-Object System.Collections.Generic.List[string]
    $mismatchedFields = New-Object System.Collections.Generic.List[string]
    foreach ($field in @($ExpectedSchema.fields)) {
        $fieldName = [string]$field.name
        $expectedType = [string]$field.dataType
        if (-not $existingFieldsByName.Contains($fieldName)) {
            $missingFields.Add($fieldName) | Out-Null
            continue
        }

        $existingType = [string]$existingFieldsByName[$fieldName]
        if ($existingType -ne $expectedType) {
            $mismatchedFields.Add(('{0} ({1} != {2})' -f $fieldName, $existingType, $expectedType)) | Out-Null
        }
    }

    return [pscustomobject]@{
        isCompatible = ($missingFields.Count -eq 0 -and $mismatchedFields.Count -eq 0)
        missingFields = $missingFields.ToArray()
        mismatchedFields = $mismatchedFields.ToArray()
    }
}

function Resolve-ExistingStream {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$ExistingStreams,
        [Parameter(Mandatory = $true)]
        [string]$DesiredStreamName,
        [Parameter(Mandatory = $true)]
        [string]$DesiredLabel,
        [Parameter(Mandatory = $true)]
        [string]$DesiredObjectName
    )

    $candidates = @($ExistingStreams | Where-Object { (Get-StreamAcceptedObjectNames -Stream $_) -contains $DesiredObjectName })
    if ($candidates.Count -eq 0) {
        $candidates = @($ExistingStreams | Where-Object { [string]$_.name -eq $DesiredStreamName })
    }

    if ($candidates.Count -eq 0) {
        $candidates = @($ExistingStreams | Where-Object { [string]$_.label -eq $DesiredLabel })
    }

    if ($candidates.Count -gt 1) {
        $candidateNames = @($candidates | ForEach-Object { [string]$_.name }) -join ', '
        throw "Multiple existing streams matched table '$DesiredStreamName': $candidateNames"
    }

    if ($candidates.Count -eq 0) {
        return $null
    }

    return $candidates[0]
}

function Get-ResolvedStreamObjectName {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Stream,
        [Parameter(Mandatory = $true)]
        [string]$FallbackObjectName
    )

    $acceptedObjectNames = Get-StreamAcceptedObjectNames -Stream $Stream
    if ($acceptedObjectNames.Count -gt 0) {
        return [string]$acceptedObjectNames[0]
    }

    return $FallbackObjectName
}

function Update-RegistryTargetsFromProvisioning {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ManifestPath,
        [Parameter(Mandatory = $true)]
        [string]$SourceName,
        [Parameter(Mandatory = $true)]
        [object[]]$ProvisionedStreams
    )

    $resolvedManifestPath = Get-NormalizedAbsolutePath -Value $ManifestPath
    $registry = Get-DataCloudRegistry
    $updatedTargets = @($registry.targets)
    $updatedKeys = New-Object System.Collections.Generic.List[string]

    foreach ($stream in @($ProvisionedStreams)) {
        $matchingTargets = @(
            $updatedTargets | Where-Object {
                [string]$_.sourceName -eq $SourceName -and
                [string]$_.manifestTableName -eq $stream.tableName -and
                (Get-NormalizedAbsolutePath -Value ([string]$_.schemaPath)) -eq $resolvedManifestPath
            }
        )

        if ($matchingTargets.Count -eq 0) {
            $matchingTargets = @(
                $updatedTargets | Where-Object {
                    [string]$_.sourceName -eq $SourceName -and
                    [string]$_.dataStreamLabel -eq $stream.streamLabel -and
                    (Get-NormalizedAbsolutePath -Value ([string]$_.schemaPath)) -eq $resolvedManifestPath
                }
            )
        }

        if ($matchingTargets.Count -gt 1) {
            $targetKeys = @($matchingTargets | ForEach-Object { [string]$_.key }) -join ', '
            throw "Multiple registry targets matched stream label '$($stream.streamLabel)': $targetKeys"
        }

        if ($matchingTargets.Count -eq 0) {
            continue
        }

        $target = $matchingTargets[0]
        $updatedTarget = [ordered]@{}
        foreach ($property in $target.PSObject.Properties) {
            $updatedTarget[$property.Name] = $property.Value
        }

        $changed = $false
        foreach ($propertyName in @('objectName', 'objectEndpoint')) {
            if ([string]$updatedTarget[$propertyName] -ne $stream.resolvedObjectName) {
                $updatedTarget[$propertyName] = $stream.resolvedObjectName
                $changed = $true
            }
        }

        if ($changed) {
            $updatedTarget.updatedAt = Get-UtcTimestamp
            $updatedTargets = @($updatedTargets | Where-Object { $_.key -ne $target.key }) + [pscustomobject]$updatedTarget
            $updatedKeys.Add([string]$target.key) | Out-Null
        }
    }

    if ($updatedKeys.Count -gt 0) {
        Save-DataCloudRegistry -Registry ([pscustomobject]@{
            defaultTargetKey = $registry.defaultTargetKey
            targets = @($updatedTargets | Sort-Object key)
        })
    }

    return [pscustomobject]@{
        updatedCount = $updatedKeys.Count
        updatedKeys = $updatedKeys.ToArray()
    }
}

function Write-ProvisioningReport {
    param(
        [Parameter(Mandatory = $true)]
        [string]$OutputRoot,
        [Parameter(Mandatory = $true)]
        [object]$Report
    )

    $reportPath = Join-Path $OutputRoot 'provisioning-state.json'
    Write-JsonFile -Path $reportPath -Value $Report
    return $reportPath
}

function Get-CleanExistingSchemas {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InstanceUrl,
        [Parameter(Mandatory = $true)]
        [string]$AccessToken,
        [Parameter(Mandatory = $true)]
        [string]$ConnectorId
    )

    $response = Invoke-SalesforceJsonRequest -InstanceUrl $InstanceUrl -AccessToken $AccessToken -Method Get -RelativePath ('/services/data/v62.0/ssot/connections/{0}/schema' -f $ConnectorId)
    $schemas = @($response.schemas)

    $cleaned = foreach ($schema in $schemas) {
        $result = [ordered]@{}
        foreach ($property in @('name', 'label', 'schemaType')) {
            if ($null -ne $schema.PSObject.Properties[$property]) {
                $result[$property] = $schema.$property
            }
        }

        $result.fields = @(
            foreach ($field in @($schema.fields)) {
                $cleanField = [ordered]@{}
                foreach ($property in @('name', 'label', 'dataType')) {
                    if ($null -ne $field.PSObject.Properties[$property]) {
                        $cleanField[$property] = $field.$property
                    }
                }
                [pscustomobject]$cleanField
            }
        )

        [pscustomobject]$result
    }

    return @($cleaned)
}

function Wait-DataLakeObjectActive {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InstanceUrl,
        [Parameter(Mandatory = $true)]
        [string]$AccessToken,
        [Parameter(Mandatory = $true)]
        [string]$StreamName,
        [int]$TimeoutSeconds = 300,
        [int]$PollSeconds = 10
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $stream = Invoke-SalesforceJsonRequest -InstanceUrl $InstanceUrl -AccessToken $AccessToken -Method Get -RelativePath ('/services/data/v62.0/ssot/data-streams/{0}' -f $StreamName)
        if ($null -ne $stream.dataLakeObjectInfo -and $stream.dataLakeObjectInfo.status -eq 'ACTIVE') {
            return $stream
        }

        Start-Sleep -Seconds $PollSeconds
    }

    throw "Timed out waiting for data stream '$StreamName' to reach ACTIVE status."
}

if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $safeSourceName = ($SourceName -replace '[^A-Za-z0-9_]', '_').Trim('_')
    $OutputRoot = Resolve-CommandCenterPath (Join-Path 'salesforce/generated' $safeSourceName)
}

$resolvedOutputRoot = [System.IO.Path]::GetFullPath($OutputRoot)
if ((Test-Path $resolvedOutputRoot) -and $Force) {
    Remove-Item $resolvedOutputRoot -Recurse -Force
}

$generatorScriptPath = Join-Path $PSScriptRoot 'data-cloud-generate-ingest-metadata.ps1'
$generatorArguments = @{
    ManifestPath = $ManifestPath
    SourceName = $SourceName
    OutputRoot = $resolvedOutputRoot
    ObjectNamePrefix = $ObjectNamePrefix
    ObjectNameSeparator = $ObjectNameSeparator
    SampleRows = $SampleRows
    Force = $true
}

if ($Tables -and $Tables.Count -gt 0) {
    $generatorArguments.Tables = $Tables
}

$generation = & $generatorScriptPath @generatorArguments
if (-not $? -or $null -eq $generation) {
    throw 'Failed to generate Data Cloud ingest metadata.'
}

$generation = $generation | ConvertTo-Json -Depth 20 | ConvertFrom-Json

$orgSession = Get-SalesforceOrgAccessContext -Alias $TargetOrg -LoginUrl $env:DATACLOUD_LOGIN_URL
$connector = Get-IngestConnector -InstanceUrl $orgSession.instanceUrl -AccessToken $orgSession.accessToken -SourceName $SourceName
$existingSchemas = Get-CleanExistingSchemas -InstanceUrl $orgSession.instanceUrl -AccessToken $orgSession.accessToken -ConnectorId $connector.id
$existingStreams = Get-ExistingStreams -InstanceUrl $orgSession.instanceUrl -AccessToken $orgSession.accessToken -ConnectorId $connector.id

$existingSchemasByName = [ordered]@{}
foreach ($schema in @($existingSchemas)) {
    $existingSchemasByName[[string]$schema.name] = $schema
}

$newSchemas = foreach ($table in @($generation.tables)) {
    [pscustomobject]@{
        name = $table.objectName
        label = $table.objectName
        schemaType = 'IngestApi'
        fields = @(
            foreach ($field in @($table.fields)) {
                [pscustomobject]@{
                    name = $field.name
                    label = $field.name
                    dataType = Get-SsotFieldDataType -Field $field
                }
            }
        )
    }
}

$schemasToRegister = New-Object System.Collections.Generic.List[object]
$reusedSchemas = New-Object System.Collections.Generic.List[object]
foreach ($schema in @($newSchemas)) {
    if ($existingSchemasByName.Contains([string]$schema.name)) {
        $schemaComparison = Compare-SchemaDefinition -ExistingSchema $existingSchemasByName[[string]$schema.name] -ExpectedSchema $schema
        if (-not $schemaComparison.isCompatible) {
            $details = @()
            if ($schemaComparison.missingFields.Count -gt 0) {
                $details += ('missing fields: {0}' -f ($schemaComparison.missingFields -join ', '))
            }
            if ($schemaComparison.mismatchedFields.Count -gt 0) {
                $details += ('type mismatches: {0}' -f ($schemaComparison.mismatchedFields -join ', '))
            }

            throw ("Existing schema object '{0}' on connector '{1}' is incompatible with the manifest-derived schema: {2}" -f $schema.name, $connector.name, ($details -join '; '))
        }

        Write-Host ("Schema object '{0}' already exists on connector '{1}' and matches the manifest schema." -f $schema.name, $connector.name) -ForegroundColor DarkYellow
        $reusedSchemas.Add([pscustomobject]@{
            name = $schema.name
            status = 'reused'
        }) | Out-Null
        continue
    }

    $schemasToRegister.Add($schema) | Out-Null
}

if ($schemasToRegister.Count -gt 0) {
    Write-Host ('Registering schema objects with connector {0}...' -f $connector.name) -ForegroundColor Cyan
    $null = Invoke-SalesforceJsonRequest -InstanceUrl $orgSession.instanceUrl -AccessToken $orgSession.accessToken -Method Put -RelativePath ('/services/data/v62.0/ssot/connections/{0}/schema' -f $connector.id) -Body @{ schemas = $schemasToRegister.ToArray() }
} else {
    Write-Host ('No new schema objects needed for connector {0}.' -f $connector.name) -ForegroundColor Cyan
}

$provisionedStreams = New-Object System.Collections.Generic.List[object]
foreach ($table in @($generation.tables)) {
    $primaryKeys = @($table.primaryKeys)
    if ($primaryKeys.Count -eq 0) {
        throw "Table '$($table.tableName)' does not define a primary key in the manifest joinGraph."
    }

    $pkField = @($table.fields | Where-Object { $primaryKeys -contains $_.name } | Select-Object -First 1)
    if ($pkField.Count -eq 0) {
        throw "Unable to resolve a primary key field for table '$($table.tableName)'."
    }

    $payload = [ordered]@{
        name = $table.dataStreamDefinition
        label = $table.streamLabel
        datasource = $SourceName
        datastreamType = 'INGESTAPI'
        connectorInfo = [ordered]@{
            connectorType = 'IngestApi'
            connectorDetails = [ordered]@{
                name = $connector.name
                events = @($table.objectName)
            }
        }
        dataLakeObjectInfo = [ordered]@{
            label = $table.streamLabel
            category = 'Other'
            dataspaceInfo = @(@{ name = 'default' })
            dataLakeFieldInputRepresentations = @(
                [ordered]@{
                    name = $pkField[0].name
                    label = $pkField[0].name
                    dataType = Get-SsotFieldDataType -Field $pkField[0]
                    isPrimaryKey = $true
                }
            )
            eventDateTimeFieldName = ''
            recordModifiedFieldName = ''
        }
        mappings = @()
    }

    Write-Host ('Creating or resolving stream for table {0}...' -f $table.tableName) -ForegroundColor Cyan
    $existingStream = Resolve-ExistingStream -ExistingStreams $existingStreams -DesiredStreamName ([string]$table.dataStreamDefinition) -DesiredLabel ([string]$table.streamLabel) -DesiredObjectName ([string]$table.objectName)
    $streamAction = 'reused'
    $streamName = ''
    if ($null -eq $existingStream) {
        try {
            $streamResult = Invoke-SalesforceJsonRequest -InstanceUrl $orgSession.instanceUrl -AccessToken $orgSession.accessToken -Method Post -RelativePath '/services/data/v62.0/ssot/data-streams' -Body $payload
            $streamName = [string]$streamResult.name
            $streamAction = 'created'
        } catch {
            $message = $_.Exception.Message
            if ($message -notmatch 'already in use|duplicate|exists') {
                throw
            }

            $existingStreams = Get-ExistingStreams -InstanceUrl $orgSession.instanceUrl -AccessToken $orgSession.accessToken -ConnectorId $connector.id
            $existingStream = Resolve-ExistingStream -ExistingStreams $existingStreams -DesiredStreamName ([string]$table.dataStreamDefinition) -DesiredLabel ([string]$table.streamLabel) -DesiredObjectName ([string]$table.objectName)
            if ($null -eq $existingStream) {
                throw
            }
        }
    }

    if ($null -ne $existingStream) {
        $streamName = [string]$existingStream.name
    }

    $activeStream = Wait-DataLakeObjectActive -InstanceUrl $orgSession.instanceUrl -AccessToken $orgSession.accessToken -StreamName $streamName
    $resolvedObjectName = Get-ResolvedStreamObjectName -Stream $activeStream -FallbackObjectName ([string]$table.objectName)
    $provisionedStreams.Add([pscustomobject]@{
        tableName = $table.tableName
        desiredObjectName = $table.objectName
        resolvedObjectName = $resolvedObjectName
        streamLabel = $table.streamLabel
        streamName = $streamName
        action = $streamAction
        csvPath = $table.csvPath
        dataLakeObjectName = $activeStream.dataLakeObjectInfo.name
        dataLakeObjectStatus = $activeStream.dataLakeObjectInfo.status
    }) | Out-Null

    if ($null -eq $existingStream) {
        $existingStreams += $activeStream
    }
}

$objectNameOverrides = [ordered]@{}
foreach ($stream in $provisionedStreams.ToArray()) {
    if ([string]$stream.desiredObjectName -ne [string]$stream.resolvedObjectName) {
        $objectNameOverrides[[string]$stream.tableName] = [string]$stream.resolvedObjectName
    }
}

if ($objectNameOverrides.Count -gt 0) {
    $overridePath = Join-Path ([System.IO.Path]::GetTempPath()) ('command-center-datacloud-overrides-{0}.json' -f ([guid]::NewGuid().ToString('N')))
    try {
        Set-Content -Path $overridePath -Value ($objectNameOverrides | ConvertTo-Json -Depth 5) -Encoding UTF8
        $generatorArguments.ObjectNameOverridesPath = $overridePath
        $generation = & $generatorScriptPath @generatorArguments
        if (-not $? -or $null -eq $generation) {
            throw 'Failed to regenerate Data Cloud ingest metadata with live object-name overrides.'
        }

        $generation = $generation | ConvertTo-Json -Depth 20 | ConvertFrom-Json
    } finally {
        if (Test-Path $overridePath) {
            Remove-Item $overridePath -Force
        }
    }
}

$registrySync = Update-RegistryTargetsFromProvisioning -ManifestPath $ManifestPath -SourceName $SourceName -ProvisionedStreams $provisionedStreams.ToArray()
$manualStepsRemaining = @(
    'The Ingest API connector itself must already exist in Data Cloud. This script resolves and uses an existing connector; it does not create one from scratch.',
    'The generated metadata under salesforce/generated remains local source until you deploy it separately with the Salesforce metadata workflow.'
)
$report = [pscustomobject]@{
    generatedAt = Get-UtcTimestamp
    manifestPath = (Resolve-Path $ManifestPath).Path
    targetOrg = $TargetOrg
    sourceName = $SourceName
    connector = [pscustomobject]@{
        id = $connector.id
        name = $connector.name
        status = 'resolved-existing'
    }
    localMetadata = [pscustomobject]@{
        status = 'generated'
        outputRoot = $resolvedOutputRoot
        deployedByThisScript = $false
        generatedTables = @($generation.tables)
    }
    schemaRegistration = [pscustomobject]@{
        created = @($schemasToRegister | ForEach-Object { $_.name })
        reused = @($reusedSchemas | ForEach-Object { $_.name })
    }
    streamProvisioning = [pscustomobject]@{
        allActive = (@($provisionedStreams | Where-Object { $_.dataLakeObjectStatus -ne 'ACTIVE' }).Count -eq 0)
        streams = $provisionedStreams.ToArray()
    }
    registrySync = $registrySync
    manualStepsRemaining = $manualStepsRemaining
}
$reportPath = Write-ProvisioningReport -OutputRoot $resolvedOutputRoot -Report $report

Write-Output ([pscustomobject]@{
    manifestPath = (Resolve-Path $ManifestPath).Path
    targetOrg = $TargetOrg
    sourceName = $SourceName
    connectorId = $connector.id
    connectorName = $connector.name
    outputRoot = $resolvedOutputRoot
    reportPath = $reportPath
    generatedTables = @($generation.tables)
    schemaRegistration = $report.schemaRegistration
    provisionedStreams = $provisionedStreams.ToArray()
    registrySync = $registrySync
    manualStepsRemaining = $manualStepsRemaining
})