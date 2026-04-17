[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ManifestPath,
    [Parameter(Mandatory = $true)]
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
$datasetName = if ([string]::IsNullOrWhiteSpace($manifest.datasetName)) { 'Manifest Dataset' } else { [string]$manifest.datasetName }
$resolvedCategory = if ([string]::IsNullOrWhiteSpace($Category)) { $datasetName } else { $Category }

$registry = Get-DataCloudRegistry
$existingTargets = @($registry.targets)
$updatedTargets = @($existingTargets)
$registeredTargets = @()

foreach ($file in @($manifest.files)) {
    $tableName = [string]$file.tableName
    $targetKey = Resolve-DataCloudManifestTargetKey -TableName $tableName -TargetKeyPrefix $TargetKeyPrefix -TargetKeySeparator $TargetKeySeparator
    $objectName = Resolve-DataCloudManifestObjectName -TableName $tableName -ObjectNamePrefix $ObjectNamePrefix -ObjectNameSeparator $ObjectNameSeparator
    $existingTarget = @($updatedTargets | Where-Object { $_.key -eq $targetKey } | Select-Object -First 1)
    $createdAt = if ($existingTarget.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace($existingTarget[0].createdAt)) { $existingTarget[0].createdAt } else { Get-UtcTimestamp }
    $primaryKey = Get-DataCloudManifestPrimaryKey -Manifest $manifest -TableName $tableName
    $csvPath = Resolve-DataCloudManifestCsvPath -ManifestInfo $manifestInfo -FileDefinition $file

    $targetRecord = New-CompactTargetRecord -Values @{
        key = $targetKey
        salesforceAlias = $SalesforceAlias
        tenantEndpoint = if ([string]::IsNullOrWhiteSpace($TenantEndpoint)) { '' } else { Normalize-DataCloudUrl -Value $TenantEndpoint }
        sourceName = $SourceName
        objectName = $objectName
        dataStreamLabel = '{0} - {1}' -f $datasetName, $tableName
        category = $resolvedCategory
        primaryKey = $primaryKey
        schemaPath = $manifestInfo.Path
        notes = if ([string]::IsNullOrWhiteSpace($Notes)) { 'Manifest table {0}; csv={1}' -f $tableName, $csvPath } else { '{0}; table={1}; csv={2}' -f $Notes, $tableName, $csvPath }
        createdAt = $createdAt
        updatedAt = Get-UtcTimestamp
    }

    $updatedTargets = @($updatedTargets | Where-Object { $_.key -ne $targetKey }) + $targetRecord
    $registeredTargets += $targetRecord
}

$defaultTargetKey = $registry.defaultTargetKey
if ($SetDefault) {
    $rootTable = if ($null -ne $manifest.publishContract -and -not [string]::IsNullOrWhiteSpace($manifest.publishContract.rootTable)) { [string]$manifest.publishContract.rootTable } else { [string]$manifest.files[0].tableName }
    $defaultTargetKey = Resolve-DataCloudManifestTargetKey -TableName $rootTable -TargetKeyPrefix $TargetKeyPrefix -TargetKeySeparator $TargetKeySeparator
}

$updatedRegistry = [pscustomobject]@{
    defaultTargetKey = if ([string]::IsNullOrWhiteSpace($defaultTargetKey)) { '' } else { $defaultTargetKey }
    targets = @($updatedTargets | Sort-Object key)
}

Save-DataCloudRegistry -Registry $updatedRegistry
Write-Output $registeredTargets