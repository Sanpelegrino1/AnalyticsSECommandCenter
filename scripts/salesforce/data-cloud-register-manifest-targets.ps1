[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ManifestPath,
    [string]$SourceName,
    [string]$TenantEndpoint,
    [string]$TargetKeyPrefix,
    [string]$TargetKeySeparator = '-',
    [string]$ObjectNamePrefix,
    [string]$ObjectNameSeparator = '_',
    [string]$SalesforceAlias,
    [string]$Category,
    [string]$Notes,
    [switch]$SetDefault
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'DataCloud.Common.ps1')

function New-CompactTargetRecord {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Values
    )

    $record = [ordered]@{}
    foreach ($key in $Values.Keys) {
        $value = $Values[$key]
        if ($null -eq $value) {
            continue
        }

        if ($value -is [string] -and [string]::IsNullOrWhiteSpace($value)) {
            continue
        }

        $record[$key] = $value
    }

    return [pscustomobject]$record
}

$manifestInfo = Get-DataCloudManifestInfo -ManifestPath $ManifestPath
$manifest = $manifestInfo.Content
$datasetDefaults = Get-DataCloudManifestDefaults -ManifestInfo $manifestInfo
$rootTable = [string](Get-OptionalObjectPropertyValue -InputObject $manifest.publishContract -PropertyName 'rootTable')
if ([string]::IsNullOrWhiteSpace($rootTable)) {
    $rootTable = [string](Get-OptionalObjectPropertyValue -InputObject $manifest.publishContract -PropertyName 'rootTableId')
}
if ([string]::IsNullOrWhiteSpace($rootTable)) {
    $rootTable = [string]$manifest.files[0].tableName
}

$registry = Get-DataCloudRegistry
$registrationHints = Get-DataCloudManifestRegistrationHints -ManifestInfo $manifestInfo -Registry $registry -RootTableName $rootTable -TargetKeySeparator $TargetKeySeparator -ObjectNameSeparator $ObjectNameSeparator
$existingTargets = @($registry.targets)
$updatedTargets = @($existingTargets)
$registeredTargets = @()

$resolvedTargetKeyPrefix = if ([string]::IsNullOrWhiteSpace($TargetKeyPrefix)) {
    if (-not [string]::IsNullOrWhiteSpace($registrationHints.TargetKeyPrefix)) { $registrationHints.TargetKeyPrefix } else { $datasetDefaults.TargetKeyPrefix }
} else {
    $TargetKeyPrefix
}

$sourceNameResolution = Resolve-DataCloudSourceNamePreference -PreferredSourceName $SourceName -SalesforceAlias $SalesforceAlias -RegistrationHints $registrationHints -DatasetDefaults $datasetDefaults
$resolvedSourceName = [string]$sourceNameResolution.SourceName

$resolvedObjectNamePrefix = if ([string]::IsNullOrWhiteSpace($ObjectNamePrefix)) {
    if (-not [string]::IsNullOrWhiteSpace($registrationHints.ObjectNamePrefix)) { $registrationHints.ObjectNamePrefix } else { $datasetDefaults.ObjectNamePrefix }
} else {
    $ObjectNamePrefix
}

$resolvedCategory = if ([string]::IsNullOrWhiteSpace($Category)) {
    if (-not [string]::IsNullOrWhiteSpace($registrationHints.Category)) { $registrationHints.Category } else { $datasetDefaults.DatasetLabel }
} else {
    $Category
}

$resolvedNotes = if ([string]::IsNullOrWhiteSpace($Notes)) { $datasetDefaults.NotesPrefix } else { $Notes }

foreach ($file in @($manifest.files)) {
    $tableName = [string]$file.tableName
    $expectedTarget = New-DataCloudManifestTargetDefinition -ManifestInfo $manifestInfo -TableName $tableName -TargetKeyPrefix $resolvedTargetKeyPrefix -TargetKeySeparator $TargetKeySeparator -ObjectNamePrefix $resolvedObjectNamePrefix -ObjectNameSeparator $ObjectNameSeparator -SourceName $resolvedSourceName -Category $resolvedCategory -Notes $resolvedNotes
    $targetKey = $expectedTarget.key
    $existingTarget = @($updatedTargets | Where-Object { $_.key -eq $targetKey } | Select-Object -First 1)
    $createdAt = if ($existingTarget.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace($existingTarget[0].createdAt)) { $existingTarget[0].createdAt } else { Get-UtcTimestamp }
    $existingTargetRecord = if ($existingTarget.Count -gt 0) { $existingTarget[0] } else { $null }
    $resolvedSalesforceAlias = if ([string]::IsNullOrWhiteSpace($SalesforceAlias)) { Get-OptionalObjectPropertyValue -InputObject $existingTargetRecord -PropertyName 'salesforceAlias' } else { $SalesforceAlias }
    $existingSalesforceAlias = Get-OptionalObjectPropertyValue -InputObject $existingTargetRecord -PropertyName 'salesforceAlias'
    $aliasChanged = (-not [string]::IsNullOrWhiteSpace($resolvedSalesforceAlias) -and -not [string]::IsNullOrWhiteSpace($existingSalesforceAlias) -and $resolvedSalesforceAlias -ne $existingSalesforceAlias)
    $resolvedTenantEndpoint = if ([string]::IsNullOrWhiteSpace($TenantEndpoint)) {
        if ($aliasChanged) { '' } else { Get-OptionalObjectPropertyValue -InputObject $existingTargetRecord -PropertyName 'tenantEndpoint' }
    } else {
        Normalize-DataCloudUrl -Value $TenantEndpoint
    }
    $resolvedObjectEndpoint = if ([string]::IsNullOrWhiteSpace((Get-OptionalObjectPropertyValue -InputObject $existingTargetRecord -PropertyName 'objectEndpoint'))) {
        ''
    } elseif ($aliasChanged) {
        ''
    } else {
        Get-OptionalObjectPropertyValue -InputObject $existingTargetRecord -PropertyName 'objectEndpoint'
    }

    $targetRecord = New-CompactTargetRecord -Values @{
        key = $targetKey
        salesforceAlias = $resolvedSalesforceAlias
        tenantEndpoint = $resolvedTenantEndpoint
        sourceName = $expectedTarget.sourceName
        objectName = $expectedTarget.objectName
        objectEndpoint = $resolvedObjectEndpoint
        dataStreamLabel = $expectedTarget.dataStreamLabel
        category = $expectedTarget.category
        primaryKey = $expectedTarget.primaryKey
        schemaPath = $expectedTarget.schemaPath
        manifestPath = $expectedTarget.manifestPath
        csvPath = $expectedTarget.csvPath
        datasetKey = $expectedTarget.datasetKey
        datasetLabel = $expectedTarget.datasetLabel
        manifestTableName = $expectedTarget.manifestTableName
        targetKeyPrefix = $expectedTarget.targetKeyPrefix
        objectNamePrefix = $expectedTarget.objectNamePrefix
        notes = $expectedTarget.notes
        createdAt = $createdAt
        updatedAt = Get-UtcTimestamp
    }

    $updatedTargets = @($updatedTargets | Where-Object { $_.key -ne $targetKey }) + $targetRecord
    $registeredTargets += $targetRecord
}

$defaultTargetKey = $registry.defaultTargetKey
if ($SetDefault) {
    $defaultTargetKey = Resolve-DataCloudManifestTargetKey -TableName $rootTable -TargetKeyPrefix $resolvedTargetKeyPrefix -TargetKeySeparator $TargetKeySeparator
}

$updatedRegistry = [pscustomobject]@{
    defaultTargetKey = if ([string]::IsNullOrWhiteSpace($defaultTargetKey)) { '' } else { $defaultTargetKey }
    targets = @($updatedTargets | Sort-Object key)
}

Save-DataCloudRegistry -Registry $updatedRegistry
Write-Output $registeredTargets