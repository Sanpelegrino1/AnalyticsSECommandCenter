[CmdletBinding()]
param(
    [string]$TargetKey,
    [Parameter(Mandatory = $true)]
    [string]$CsvPath,
    [ValidateSet('upsert', 'delete')]
    [string]$Operation = 'upsert',
    [bool]$WaitForCompletion = $false,
    [int]$PollSeconds = 15,
    [int]$TimeoutSeconds = 900
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'DataCloud.Common.ps1')

function Test-DataCloudNotFoundMessage {
    param(
        [string]$Message
    )

    return (-not [string]::IsNullOrWhiteSpace($Message) -and $Message -match '\(404\)|NOT_FOUND|not found')
}

function Test-DataCloudConfiguredEndpointFallbackMessage {
    param(
        [string]$Message
    )

    return (
        -not [string]::IsNullOrWhiteSpace($Message) -and
        ($Message -match '\(404\)|NOT_FOUND|not found|\(400\)|BAD_REQUEST|bad request')
    )
}

function New-DataCloudStaleTargetMessage {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [string]$Reason
    )

    $targetLabel = if ([string]::IsNullOrWhiteSpace($Config.TargetKey)) { '<env>' } else { $Config.TargetKey }
    $message = 'Target {0} could not create a Data Cloud bulk job for source {1} and object {2}.' -f $targetLabel, $Config.SourceName, $Config.ObjectName
    if (-not [string]::IsNullOrWhiteSpace($Reason)) {
        $message = '{0} {1}' -f $message, $Reason
    }

    if (-not [string]::IsNullOrWhiteSpace($Config.ObjectEndpoint)) {
        $message = '{0} The configured objectEndpoint ''{1}'' was not accepted by the current connector route and may be stale or incompatible with the current ingest API contract. This script will fall back to generic object lookup using sourceName ''{2}'' and object ''{3}''. If upload still fails, re-register the target with the live connector-specific object endpoint and confirm sourceName and objectName match the intended stream in the current org.' -f $message, $Config.ObjectEndpoint, $Config.SourceName, $Config.ObjectName
    } else {
        $message = '{0} The target does not have an objectEndpoint override. This script will use generic object lookup with sourceName ''{1}'' and object ''{2}''. Confirm the data stream exists and that sourceName and objectName match the intended stream in the current org if generic lookup keeps returning 404.' -f $message, $Config.SourceName, $Config.ObjectName
    }

    return $message
}

function Stop-CurrentUploadJobSafely {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Context,
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$Job,
        [Parameter(Mandatory = $true)]
        [string]$OriginalMessage
    )

    $jobId = [string]$Job.id
    if ([string]::IsNullOrWhiteSpace($jobId)) {
        return $OriginalMessage
    }

    try {
        $abortedJob = Stop-DataCloudJob -Context $Context -JobId $jobId
        $abortedJob = Add-DataCloudJobOperatorMetadata -TargetKey $Config.TargetKey -Job $abortedJob
        return '{0} Cleanup aborted unfinished job {1}. Inspect with: {2}' -f $OriginalMessage, $jobId, $abortedJob.inspectCommand
    } catch {
        $abortCommand = Get-DataCloudJobAbortCommand -TargetKey $Config.TargetKey -JobId $jobId
        return '{0} Cleanup could not abort unfinished job {1}. Abort it manually with: {2} Error: {3}' -f $OriginalMessage, $jobId, $abortCommand, $_.Exception.Message
    }
}

function New-BulkIngestJob {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Context,
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string]$Operation,
        [int]$MaxRetries = 3,
        [int]$RetryDelaySeconds = 15
    )

    $createAttempts = @()
    if (-not [string]::IsNullOrWhiteSpace($Config.ObjectEndpoint)) {
        $createAttempts += [pscustomobject]@{
            Name = 'configured-object-endpoint'
            RelativePath = '/api/v1/ingest/sources/{0}/{1}' -f $Config.SourceName, $Config.ObjectEndpoint
            Body = @{ operation = $Operation }
        }
    }

    $createAttempts += [pscustomobject]@{
        Name = 'generic-object-lookup'
        RelativePath = '/api/v1/ingest/jobs'
        Body = @{
            object = $Config.ObjectName
            sourceName = $Config.SourceName
            operation = $Operation
        }
    }

    $attemptMessages = @()
    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        foreach ($createAttempt in $createAttempts) {
            try {
                return Invoke-DataCloudJsonRequest -Context $Context -Method Post -RelativePath $createAttempt.RelativePath -Body $createAttempt.Body
            } catch {
                $message = $_.Exception.Message
                $attemptMessages += ('{0}: {1}' -f $createAttempt.Name, $message)

                if ($createAttempt.Name -eq 'configured-object-endpoint' -and (Test-DataCloudConfiguredEndpointFallbackMessage -Message $message)) {
                    Write-Warning (New-DataCloudStaleTargetMessage -Config $Config -Reason ('Configured object endpoint create failed on attempt {0}/{1}; falling back to generic object lookup.' -f $attempt, $MaxRetries))
                    continue
                }

                $shouldRetry = $createAttempt.Name -eq 'generic-object-lookup' -and $attempt -lt $MaxRetries -and (Test-DataCloudNotFoundMessage -Message $message)
                if ($shouldRetry) {
                    Write-Warning ('Bulk job create returned 404 for source {0} object {1}. Waiting {2}s for fresh stream propagation before retry {3}/{4}.' -f $Config.SourceName, $Config.ObjectName, $RetryDelaySeconds, ($attempt + 1), $MaxRetries)
                    Start-Sleep -Seconds $RetryDelaySeconds
                    break
                }

                if ($createAttempt.Name -eq 'generic-object-lookup' -and (Test-DataCloudNotFoundMessage -Message $message)) {
                    throw (New-DataCloudStaleTargetMessage -Config $Config -Reason 'Generic object lookup also returned 404.')
                }

                $targetLabel = if ([string]::IsNullOrWhiteSpace($Config.TargetKey)) { '<env>' } else { $Config.TargetKey }
                throw ('Unable to create a Data Cloud bulk job for target {0}. Attempt {1}/{2} using {3} failed. {4}' -f $targetLabel, $attempt, $MaxRetries, $createAttempt.Name, $message)
            }
        }
    }

    $attemptSummary = if ($attemptMessages.Count -gt 0) { ' Attempts: {0}' -f ($attemptMessages -join ' | ') } else { '' }
    throw ('Unable to create a Data Cloud bulk job for object {0} after {1} attempts.{2}' -f $Config.ObjectName, $MaxRetries, $attemptSummary)
}

$context = Get-DataCloudAccessContext -TargetKey $TargetKey
$config = $context.Config

if ([string]::IsNullOrWhiteSpace($config.SourceName)) {
    throw 'A Data Cloud sourceName is required. Register the target or set DATACLOUD_SOURCE_NAME.'
}

if ([string]::IsNullOrWhiteSpace($config.ObjectName)) {
    throw 'A Data Cloud objectName is required. Register the target or set DATACLOUD_OBJECT_NAME.'
}

if ([string]::IsNullOrWhiteSpace($config.ObjectEndpoint)) {
    Write-Warning ('Target {0} does not include objectEndpoint metadata. Upload will fall back to generic object lookup. If job creation returns 404, re-register the target with the live connector-specific object endpoint.' -f $(if ([string]::IsNullOrWhiteSpace($config.TargetKey)) { '<env>' } else { $config.TargetKey }))
}

$resolvedCsvPath = (Resolve-Path $CsvPath).Path
$fileInfo = Get-Item -Path $resolvedCsvPath
if ($fileInfo.Length -gt 150MB) {
    throw 'Data Cloud bulk uploads require each CSV file to be 150 MB or smaller.'
}

Write-Host ('Creating Data Cloud bulk job for target {0}...' -f $(if ([string]::IsNullOrWhiteSpace($config.TargetKey)) { '<env>' } else { $config.TargetKey }))
$job = $null
$jobClosed = $false

try {
    $job = New-BulkIngestJob -Context $context -Config $config -Operation $Operation

    $uploadUri = '{0}/api/v1/ingest/jobs/{1}/batches' -f $context.TenantEndpoint, $job.id
    Write-Host ('Uploading {0} ({1} bytes) to job {2}...' -f $resolvedCsvPath, $fileInfo.Length, $job.id)
    try {
        Invoke-WebRequest -UseBasicParsing -Method Put -Uri $uploadUri -Headers @{ Authorization = 'Bearer {0}' -f $context.AccessToken } -ContentType 'text/csv' -InFile $resolvedCsvPath | Out-Null
    } catch {
        throw (Get-DataCloudErrorMessage -ErrorRecord $_)
    }

    Write-Host ('Closing job {0} for processing...' -f $job.id)
    $closeResponse = Invoke-DataCloudJsonRequest -Context $context -Method Patch -RelativePath ('/api/v1/ingest/jobs/{0}' -f $job.id) -Body @{ state = 'UploadComplete' }
    $jobClosed = $true

    $finalJob = $closeResponse
    if ($WaitForCompletion) {
        Write-Host ('Waiting for job {0} to complete...' -f $job.id)
        $finalJob = Wait-DataCloudJobState -Context $context -JobId $job.id -PollSeconds $PollSeconds -TimeoutSeconds $TimeoutSeconds
    }

    $finalJob = Add-DataCloudJobOperatorMetadata -TargetKey $config.TargetKey -Job $finalJob
    if ($finalJob.state -in @('Failed', 'Aborted')) {
        throw (Format-DataCloudJobFailureMessage -TargetKey $config.TargetKey -Job $finalJob)
    }

    Write-Output $finalJob
} catch {
    $message = $_.Exception.Message

    if ($null -ne $job -and -not $jobClosed) {
        $message = Stop-CurrentUploadJobSafely -Context $context -Config $config -Job $job -OriginalMessage $message
    } elseif ($null -ne $job -and $message -match '^Timed out waiting for Data Cloud job') {
        $inspectionCommand = Get-DataCloudJobInspectionCommand -TargetKey $config.TargetKey -JobId $job.id
        $abortCommand = Get-DataCloudJobAbortCommand -TargetKey $config.TargetKey -JobId $job.id
        $message = '{0} Inspect the current state with: {1} If the job is stuck in Open or UploadComplete and you do not want it to continue, abort it with: {2}' -f $message, $inspectionCommand, $abortCommand
    }

    throw $message
}
