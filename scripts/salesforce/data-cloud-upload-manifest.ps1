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
$uploadScriptPath = Join-Path $PSScriptRoot 'data-cloud-upload-csv.ps1'

$uploadPlan = foreach ($file in @($manifest.files)) {
    $tableName = [string]$file.tableName
    $targetKey = Resolve-DataCloudManifestTargetKey -TableName $tableName -TargetKeyPrefix $TargetKeyPrefix -TargetKeySeparator $TargetKeySeparator
    $csvPath = Resolve-DataCloudManifestCsvPath -ManifestInfo $manifestInfo -FileDefinition $file
    $target = @($registry.targets | Where-Object { $_.key -eq $targetKey } | Select-Object -First 1)

    [pscustomobject]@{
        tableName = $tableName
        csvPath = $csvPath
        targetKey = $targetKey
        targetExists = ($target.Count -gt 0)
    }
}

$missingTargets = @($uploadPlan | Where-Object { -not $_.targetExists })
if ($missingTargets.Count -gt 0) {
    $missingTargetKeys = @($missingTargets | ForEach-Object { $_.targetKey }) -join ', '
    throw "The registry is missing Data Cloud targets for: $missingTargetKeys. Register them first with data-cloud-register-target.ps1 or data-cloud-register-manifest-targets.ps1."
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