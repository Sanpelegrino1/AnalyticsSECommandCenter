[CmdletBinding()]
param(
    [string]$TargetKey,
    [Parameter(Mandatory = $true)]
    [string]$CsvPath,
    [ValidateSet('upsert', 'delete')]
    [string]$Operation = 'upsert',
    [bool]$WaitForCompletion = $true,
    [int]$PollSeconds = 15,
    [int]$TimeoutSeconds = 900
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'DataCloud.Common.ps1')

$context = Get-DataCloudAccessContext -TargetKey $TargetKey
$config = $context.Config

if ([string]::IsNullOrWhiteSpace($config.SourceName)) {
    throw 'A Data Cloud sourceName is required. Register the target or set DATACLOUD_SOURCE_NAME.'
}

if ([string]::IsNullOrWhiteSpace($config.ObjectName)) {
    throw 'A Data Cloud objectName is required. Register the target or set DATACLOUD_OBJECT_NAME.'
}

$resolvedCsvPath = (Resolve-Path $CsvPath).Path
$fileInfo = Get-Item -Path $resolvedCsvPath
if ($fileInfo.Length -gt 150MB) {
    throw 'Data Cloud bulk uploads require each CSV file to be 150 MB or smaller.'
}

Write-Host ('Creating Data Cloud bulk job for target {0}...' -f $(if ([string]::IsNullOrWhiteSpace($config.TargetKey)) { '<env>' } else { $config.TargetKey }))
$job = Invoke-DataCloudJsonRequest -Context $context -Method Post -RelativePath '/api/v1/ingest/jobs' -Body @{
    object = $config.ObjectName
    sourceName = $config.SourceName
    operation = $Operation
}

$uploadUri = '{0}/api/v1/ingest/jobs/{1}/batches' -f $context.TenantEndpoint, $job.id
Write-Host ('Uploading {0} ({1} bytes) to job {2}...' -f $resolvedCsvPath, $fileInfo.Length, $job.id)
try {
    Invoke-WebRequest -UseBasicParsing -Method Put -Uri $uploadUri -Headers @{ Authorization = 'Bearer {0}' -f $context.AccessToken } -ContentType 'text/csv' -InFile $resolvedCsvPath | Out-Null
} catch {
    throw (Get-DataCloudErrorMessage -ErrorRecord $_)
}

Write-Host ('Closing job {0} for processing...' -f $job.id)
$closeResponse = Invoke-DataCloudJsonRequest -Context $context -Method Patch -RelativePath ('/api/v1/ingest/jobs/{0}' -f $job.id) -Body @{ state = 'UploadComplete' }

$finalJob = $closeResponse
if ($WaitForCompletion) {
    Write-Host ('Waiting for job {0} to complete...' -f $job.id)
    $finalJob = Wait-DataCloudJobState -Context $context -JobId $job.id -PollSeconds $PollSeconds -TimeoutSeconds $TimeoutSeconds
}

if ($finalJob.state -eq 'Failed') {
    throw ('Data Cloud ingestion job {0} failed. Inspect the job with data-cloud-get-job.ps1.' -f $job.id)
}

Write-Output $finalJob
