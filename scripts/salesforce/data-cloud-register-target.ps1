[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetKey,
    [Parameter(Mandatory = $true)]
    [string]$SourceName,
    [Parameter(Mandatory = $true)]
    [string]$ObjectName,
    [string]$TenantEndpoint,
    [string]$ObjectEndpoint,
    [string]$SalesforceAlias,
    [string]$DataStreamLabel,
    [string]$Category,
    [string]$PrimaryKey,
    [string]$RecordModifiedField,
    [string]$SchemaPath,
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

$registry = Get-DataCloudRegistry
$existingTargets = @($registry.targets)
$existingTarget = @($existingTargets | Where-Object { $_.key -eq $TargetKey } | Select-Object -First 1)
$createdAt = if ($existingTarget.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace($existingTarget[0].createdAt)) { $existingTarget[0].createdAt } else { Get-UtcTimestamp }

$targetRecord = New-CompactTargetRecord -Values @{
    key = $TargetKey
    salesforceAlias = $SalesforceAlias
    tenantEndpoint = if ([string]::IsNullOrWhiteSpace($TenantEndpoint)) { '' } else { Normalize-DataCloudUrl -Value $TenantEndpoint }
    sourceName = $SourceName
    objectName = $ObjectName
    objectEndpoint = $ObjectEndpoint
    dataStreamLabel = $DataStreamLabel
    category = $Category
    primaryKey = $PrimaryKey
    recordModifiedField = $RecordModifiedField
    schemaPath = $SchemaPath
    notes = $Notes
    createdAt = $createdAt
    updatedAt = Get-UtcTimestamp
}

$updatedTargets = @($existingTargets | Where-Object { $_.key -ne $TargetKey }) + $targetRecord
$updatedRegistry = [pscustomobject]@{
    defaultTargetKey = if ($SetDefault) { $TargetKey } elseif (-not [string]::IsNullOrWhiteSpace($registry.defaultTargetKey)) { $registry.defaultTargetKey } else { '' }
    targets = @($updatedTargets | Sort-Object key)
}

Save-DataCloudRegistry -Registry $updatedRegistry
Write-Output $targetRecord
