[CmdletBinding()]
param(
    [string]$ManifestPath,
    [string]$Alias,
    [string]$LoginUrl,
    [string]$TargetKeyPrefix,
    [string]$TargetKeySeparator = '-',
    [string]$SourceName,
    [string]$ObjectNamePrefix,
    [string]$ObjectNameSeparator = '_',
    [string]$TenantEndpoint,
    [string]$Category,
    [string]$Notes,
    [switch]$SkipAuthorization,
    [switch]$SetDefault
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'DataCloud.Common.ps1')

function Read-RequiredValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Prompt,
        [string]$DefaultValue
    )

    while ($true) {
        $displayPrompt = if ([string]::IsNullOrWhiteSpace($DefaultValue)) { $Prompt } else { '{0} [{1}]' -f $Prompt, $DefaultValue }
        $answer = Read-Host $displayPrompt
        if (-not [string]::IsNullOrWhiteSpace($answer)) {
            return $answer.Trim()
        }

        if (-not [string]::IsNullOrWhiteSpace($DefaultValue)) {
            return $DefaultValue.Trim()
        }
    }
}

function Read-OptionalValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Prompt,
        [string]$DefaultValue
    )

    $displayPrompt = if ([string]::IsNullOrWhiteSpace($DefaultValue)) { $Prompt } else { '{0} [{1}]' -f $Prompt, $DefaultValue }
    $answer = Read-Host $displayPrompt
    if ([string]::IsNullOrWhiteSpace($answer)) {
        return $DefaultValue
    }

    return $answer.Trim()
}

function Test-DataCloudAuthorizationReusable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Alias,
        [Parameter(Mandatory = $true)]
        [string]$LoginUrl
    )

    try {
        $null = Get-SalesforceCliOrgSession -Alias $Alias
        return $true
    } catch {
    }

    if ([string]::IsNullOrWhiteSpace($env:DATACLOUD_REFRESH_TOKEN)) {
        return $false
    }

    if ([string]::IsNullOrWhiteSpace($env:DATACLOUD_SALESFORCE_ALIAS)) {
        return $false
    }

    if ($env:DATACLOUD_SALESFORCE_ALIAS -ne $Alias) {
        return $false
    }

    if (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_LOGIN_URL)) {
        return ((Normalize-DataCloudUrl -Value $env:DATACLOUD_LOGIN_URL) -eq (Normalize-DataCloudUrl -Value $LoginUrl))
    }

    return $true
}

Import-CommandCenterEnv

$defaultManifestPath = Join-Path (Get-Location) 'manifest.json'
if ([string]::IsNullOrWhiteSpace($ManifestPath)) {
    $ManifestPath = Read-RequiredValue -Prompt 'Manifest path' -DefaultValue $(if (Test-Path $defaultManifestPath) { $defaultManifestPath } else { '' })
}

$registry = Get-DataCloudRegistry
$manifestInfo = Get-DataCloudManifestInfo -ManifestPath $ManifestPath
$manifest = $manifestInfo.Content
$datasetDefaults = Get-DataCloudManifestDefaults -ManifestInfo $manifestInfo
$datasetName = $datasetDefaults.DatasetLabel
$datasetSlug = $datasetDefaults.DatasetKey
$rootTable = if ($null -ne $manifest.publishContract -and -not [string]::IsNullOrWhiteSpace($manifest.publishContract.rootTable)) { [string]$manifest.publishContract.rootTable } else { [string]$manifest.files[0].tableName }
$registrationHints = Get-DataCloudManifestRegistrationHints -ManifestInfo $manifestInfo -Registry $registry -RootTableName $rootTable -TargetKeySeparator $TargetKeySeparator -ObjectNameSeparator $ObjectNameSeparator

if ([string]::IsNullOrWhiteSpace($Alias)) {
    $Alias = Read-RequiredValue -Prompt 'Data Cloud auth alias label' -DefaultValue $(if (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_SALESFORCE_ALIAS)) { $env:DATACLOUD_SALESFORCE_ALIAS } elseif (-not [string]::IsNullOrWhiteSpace($registrationHints.SalesforceAlias)) { $registrationHints.SalesforceAlias } elseif (-not [string]::IsNullOrWhiteSpace($env:SF_DEFAULT_ALIAS)) { '{0}_DC' -f $env:SF_DEFAULT_ALIAS } else { '{0}-dc' -f $datasetSlug })
}

if ([string]::IsNullOrWhiteSpace($LoginUrl)) {
    $LoginUrl = Read-RequiredValue -Prompt 'Salesforce login URL or My Domain URL' -DefaultValue $(if (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_LOGIN_URL)) { $env:DATACLOUD_LOGIN_URL } elseif (-not [string]::IsNullOrWhiteSpace($env:SF_LOGIN_URL)) { $env:SF_LOGIN_URL } else { 'https://login.salesforce.com' })
}

if ([string]::IsNullOrWhiteSpace($TargetKeyPrefix)) {
    $TargetKeyPrefix = Read-RequiredValue -Prompt 'Target key prefix' -DefaultValue $(if (-not [string]::IsNullOrWhiteSpace($registrationHints.TargetKeyPrefix)) { $registrationHints.TargetKeyPrefix } else { $datasetDefaults.TargetKeyPrefix })
}

$sourceNameResolution = Resolve-DataCloudSourceNamePreference -PreferredSourceName $SourceName -SalesforceAlias $Alias -LoginUrl $LoginUrl -RegistrationHints $registrationHints -DatasetDefaults $datasetDefaults -AllowDatasetFallback:$false
if ([string]::IsNullOrWhiteSpace($SourceName)) {
    $SourceName = if (-not [string]::IsNullOrWhiteSpace([string]$sourceNameResolution.SourceName)) { [string]$sourceNameResolution.SourceName } else { [string]$datasetDefaults.SourceName }
}

if ([string]::IsNullOrWhiteSpace($ObjectNamePrefix)) {
    $ObjectNamePrefix = Read-RequiredValue -Prompt 'Object name prefix for generated Data Cloud objects' -DefaultValue $(if (-not [string]::IsNullOrWhiteSpace($registrationHints.ObjectNamePrefix)) { $registrationHints.ObjectNamePrefix } else { ($TargetKeyPrefix -replace '-', '_') })
}

if ([string]::IsNullOrWhiteSpace($Category)) {
    $Category = Read-OptionalValue -Prompt 'Category label for registered targets' -DefaultValue $(if (-not [string]::IsNullOrWhiteSpace($registrationHints.Category)) { $registrationHints.Category } else { $datasetDefaults.DatasetLabel })
}

if ([string]::IsNullOrWhiteSpace($Notes)) {
    $Notes = Read-OptionalValue -Prompt 'Notes to attach to registered targets' -DefaultValue $datasetDefaults.NotesPrefix
}

if (-not $SkipAuthorization -and -not (Test-DataCloudAuthorizationReusable -Alias $Alias -LoginUrl $LoginUrl)) {
    $loginScriptPath = Join-Path $PSScriptRoot 'data-cloud-login-web.ps1'
    & $loginScriptPath -Alias $Alias -InstanceUrl $LoginUrl -SetDefault -Purpose 'Data Cloud manifest publishing auth' -Notes ('Guided setup for {0}' -f $datasetName)
    if (-not $?) {
        exit 1
    }
    Import-CommandCenterEnv -Force
}

$registerScriptPath = Join-Path $PSScriptRoot 'data-cloud-register-manifest-targets.ps1'
$registeredTargets = & $registerScriptPath -ManifestPath $manifestInfo.Path -SourceName $SourceName -TenantEndpoint $TenantEndpoint -TargetKeyPrefix $TargetKeyPrefix -TargetKeySeparator $TargetKeySeparator -ObjectNamePrefix $ObjectNamePrefix -ObjectNameSeparator $ObjectNameSeparator -SalesforceAlias $Alias -Category $Category -Notes $Notes -SetDefault:$SetDefault
if (-not $?) {
    exit 1
}

$defaultTargetKey = Resolve-DataCloudManifestTargetKey -TableName $rootTable -TargetKeyPrefix $TargetKeyPrefix -TargetKeySeparator $TargetKeySeparator
Set-CommandCenterEnvValue -Name 'DATACLOUD_DEFAULT_TARGET' -Value $defaultTargetKey
if (-not [string]::IsNullOrWhiteSpace($TenantEndpoint)) {
    Set-CommandCenterEnvValue -Name 'DATACLOUD_TENANT_ENDPOINT' -Value (Normalize-DataCloudUrl -Value $TenantEndpoint)
}

$validationScriptPath = Join-Path $PSScriptRoot 'data-cloud-get-access-token.ps1'
$validationResult = & $validationScriptPath -TargetKey $defaultTargetKey -AsJson | ConvertFrom-Json

$tableCount = @($manifest.files).Count
Write-Host ('Registered {0} manifest targets for dataset "{1}".' -f $tableCount, $datasetName) -ForegroundColor Green
Write-Host ('Default target key: {0}' -f $defaultTargetKey) -ForegroundColor Green
Write-Host ('Token source: {0}' -f $validationResult.tokenSource) -ForegroundColor Green
Write-Host ('Resolved tenant endpoint: {0}' -f $validationResult.tenantEndpoint) -ForegroundColor Green
$missingObjectEndpointTargets = @(
    $registeredTargets | Where-Object {
        $objectEndpointProperty = $_.PSObject.Properties['objectEndpoint']
        $objectEndpoint = if ($null -ne $objectEndpointProperty) { [string]$objectEndpointProperty.Value } else { '' }
        [string]::IsNullOrWhiteSpace($objectEndpoint)
    }
)
if ($missingObjectEndpointTargets.Count -gt 0) {
    $missingKeys = @($missingObjectEndpointTargets | ForEach-Object { $_.key }) -join ', '
    Write-Warning ("Dataset registration is automatic, but Data Cloud Setup still has to create and validate the live streams/object endpoints for: {0}. After that, update notes/registries/data-cloud-targets.json with the connector-specific objectEndpoint values or rerun per-target registration." -f $missingKeys)
}
Write-Host ('Next upload command: powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-upload-manifest.ps1 -ManifestPath "{0}" -TargetKeyPrefix {1}' -f $manifestInfo.Path, $TargetKeyPrefix) -ForegroundColor Cyan