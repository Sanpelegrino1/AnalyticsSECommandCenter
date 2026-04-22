[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ManifestPath,
    [string]$TargetKeyPrefix,
    [string]$TargetKeySeparator = '-',
    [ValidateSet('upsert', 'delete')]
    [string]$Operation = 'upsert',
    [bool]$WaitForCompletion = $true,
    [int]$PollSeconds = 15,
    [int]$TimeoutSeconds = 900,
    [switch]$ContinueOnError
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'DataCloud.Common.ps1')

$manifestInfo = Get-DataCloudManifestInfo -ManifestPath $ManifestPath
$manifest = $manifestInfo.Content
$registry = Get-DataCloudRegistry
$rootTable = if ($null -ne $manifest.publishContract -and -not [string]::IsNullOrWhiteSpace($manifest.publishContract.rootTable)) { [string]$manifest.publishContract.rootTable } else { [string]$manifest.files[0].tableName }
$registrationHints = Get-DataCloudManifestRegistrationHints -ManifestInfo $manifestInfo -Registry $registry -RootTableName $rootTable -TargetKeySeparator $TargetKeySeparator
$datasetDefaults = Get-DataCloudManifestDefaults -ManifestInfo $manifestInfo
$uploadScriptPath = Join-Path $PSScriptRoot 'data-cloud-upload-csv.ps1'

$resolvedTargetKeyPrefix = if ([string]::IsNullOrWhiteSpace($TargetKeyPrefix)) {
    if (-not [string]::IsNullOrWhiteSpace($registrationHints.TargetKeyPrefix)) { $registrationHints.TargetKeyPrefix } else { $datasetDefaults.TargetKeyPrefix }
} else {
    $TargetKeyPrefix
}

$resolvedObjectNamePrefix = if (-not [string]::IsNullOrWhiteSpace($registrationHints.ObjectNamePrefix)) { $registrationHints.ObjectNamePrefix } else { $datasetDefaults.ObjectNamePrefix }
$resolvedSourceName = if (-not [string]::IsNullOrWhiteSpace($registrationHints.SourceName)) { $registrationHints.SourceName } else { $datasetDefaults.SourceName }
$resolvedCategory = if (-not [string]::IsNullOrWhiteSpace($registrationHints.Category)) { $registrationHints.Category } else { $datasetDefaults.DatasetLabel }

$uploadPlan = foreach ($file in @($manifest.files)) {
    $tableName = [string]$file.tableName
    $targetKey = Resolve-DataCloudManifestTargetKey -TableName $tableName -TargetKeyPrefix $resolvedTargetKeyPrefix -TargetKeySeparator $TargetKeySeparator
    $csvPath = Resolve-DataCloudManifestCsvPath -ManifestInfo $manifestInfo -FileDefinition $file
    $target = @($registry.targets | Where-Object { $_.key -eq $targetKey } | Select-Object -First 1)
    $targetConfig = $null
    $validationIssues = @()
    if ($target.Count -gt 0) {
        $targetConfig = Get-DataCloudTargetConfiguration -TargetKey $targetKey
        $expectedTarget = New-DataCloudManifestTargetDefinition -ManifestInfo $manifestInfo -TableName $tableName -TargetKeyPrefix $resolvedTargetKeyPrefix -TargetKeySeparator $TargetKeySeparator -ObjectNamePrefix $resolvedObjectNamePrefix -SourceName $resolvedSourceName -Category $resolvedCategory -Notes $datasetDefaults.NotesPrefix
        $mismatches = Compare-DataCloudManifestTargetDefinition -ExistingTarget $target[0] -ExpectedTarget $expectedTarget
        foreach ($mismatch in $mismatches) {
            $validationIssues += '{0}: actual="{1}" expected="{2}"' -f $mismatch.field, $mismatch.actual, $mismatch.expected
        }

        if ([string]::IsNullOrWhiteSpace($targetConfig.TenantEndpoint)) {
            $validationIssues += 'tenantEndpoint is missing from the registry and local env'
        }
    }

    [pscustomobject]@{
        tableName = $tableName
        csvPath = $csvPath
        targetKey = $targetKey
        targetExists = ($target.Count -gt 0)
        sourceName = if ($null -eq $targetConfig) { '' } else { $targetConfig.SourceName }
        objectName = if ($null -eq $targetConfig) { '' } else { $targetConfig.ObjectName }
        objectEndpoint = if ($null -eq $targetConfig) { '' } else { $targetConfig.ObjectEndpoint }
        validationIssues = $validationIssues
    }
}

$missingTargets = @($uploadPlan | Where-Object { -not $_.targetExists })
if ($missingTargets.Count -gt 0) {
    $missingTargetKeys = @($missingTargets | ForEach-Object { $_.targetKey }) -join ', '
    throw "The registry is missing Data Cloud targets for: $missingTargetKeys. Register them first with data-cloud-register-target.ps1 or data-cloud-register-manifest-targets.ps1. Suggested repair: powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-register-manifest-targets.ps1 -ManifestPath '$($manifestInfo.RelativePath)' -TargetKeyPrefix $resolvedTargetKeyPrefix"
}

$invalidTargets = @($uploadPlan | Where-Object { [string]::IsNullOrWhiteSpace($_.sourceName) -or [string]::IsNullOrWhiteSpace($_.objectName) })
if ($invalidTargets.Count -gt 0) {
    $invalidTargetKeys = @($invalidTargets | ForEach-Object { $_.targetKey }) -join ', '
    throw "The following Data Cloud targets are missing sourceName or objectName: $invalidTargetKeys. Re-register them before retrying the manifest upload."
}

$staleTargets = @($uploadPlan | Where-Object { $_.validationIssues.Count -gt 0 })
if ($staleTargets.Count -gt 0) {
    $details = @(
        $staleTargets | ForEach-Object {
            '{0}: {1}' -f $_.targetKey, ($_.validationIssues -join '; ')
        }
    ) -join [Environment]::NewLine
    throw "Data Cloud target registry preflight failed for this manifest. Re-register the dataset to refresh dataset-derived fields and then fill any remaining org-specific fields.`n$details`nSuggested repair: powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-register-manifest-targets.ps1 -ManifestPath '$($manifestInfo.RelativePath)' -TargetKeyPrefix $resolvedTargetKeyPrefix"
}

$genericLookupTargets = @($uploadPlan | Where-Object { [string]::IsNullOrWhiteSpace($_.objectEndpoint) })
foreach ($genericLookupTarget in $genericLookupTargets) {
    Write-Warning ('Target {0} does not include objectEndpoint metadata for table {1}. Upload will use generic object lookup and may need target re-registration if the org was rebuilt or the connector changed.' -f $genericLookupTarget.targetKey, $genericLookupTarget.tableName)
}

$results = @()
foreach ($item in $uploadPlan) {
    Write-Host ('Uploading table {0} from {1} using target {2}...' -f $item.tableName, $item.csvPath, $item.targetKey)

    try {
        $job = & $uploadScriptPath -TargetKey $item.targetKey -CsvPath $item.csvPath -Operation $Operation -WaitForCompletion:$WaitForCompletion -PollSeconds $PollSeconds -TimeoutSeconds $TimeoutSeconds
        $results += [pscustomobject]@{
            tableName = $item.tableName
            targetKey = $item.targetKey
            csvPath = $item.csvPath
            jobId = $job.id
            state = $job.state
            inspectCommand = $job.inspectCommand
            abortCommand = $(if ($job.PSObject.Properties['abortCommand']) { $job.abortCommand } else { '' })
        }
    } catch {
        $results += [pscustomobject]@{
            tableName = $item.tableName
            targetKey = $item.targetKey
            csvPath = $item.csvPath
            jobId = ''
            state = 'FailedToStart'
            error = $_.Exception.Message
        }

        if (-not $ContinueOnError) {
            throw
        }
    }
}

Write-Output $results