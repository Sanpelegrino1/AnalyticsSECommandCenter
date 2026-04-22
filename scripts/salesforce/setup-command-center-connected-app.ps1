[CmdletBinding()]
param(
    [string]$TargetOrg = $env:SF_DEFAULT_ALIAS,
    [string]$DataCloudAlias = $env:DATACLOUD_SALESFORCE_ALIAS,
    [switch]$LaunchLogin,
    [switch]$SetDefault
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\CommandCenter.Common.ps1')

function New-CommandCenterAuthClientId {
    param(
        [Parameter(Mandatory = $true)]
        [string]$OrgId
    )

    $safeOrgId = ($OrgId -replace '[^A-Za-z0-9]', '')
    return ('CommandCenterAuth{0}' -f $safeOrgId)
}

function Set-RegisteredDataCloudClientId {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Alias,
        [Parameter(Mandatory = $true)]
        [string]$ClientId
    )

    $registryPath = Resolve-CommandCenterPath 'notes/registries/salesforce-orgs.json'
    $registry = Read-JsonFile -Path $registryPath
    if (-not $registry) {
        return
    }

    $existing = @($registry.orgs | Where-Object { $_.alias -eq $Alias } | Select-Object -First 1)
    if ($existing.Count -eq 0) {
        return
    }

    $existing[0] | Add-Member -NotePropertyName 'dataCloudClientId' -NotePropertyValue $ClientId -Force
    Write-JsonFile -Path $registryPath -Value $registry
}

function New-StagedCommandCenterAuthDeployment {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SalesforceRoot,
        [Parameter(Mandatory = $true)]
        [string]$ClientId
    )

    $stageRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('commandcenterauth-{0}' -f ([guid]::NewGuid().ToString('N')))
    $stageAppRoot = Join-Path $stageRoot 'force-app\main\default'
    $filesToStage = @(
        'externalClientApps\CommandCenterAuth.eca-meta.xml',
        'extlClntAppGlobalOauthSets\CommandCenterAuth_glbloauth.ecaGlblOauth-meta.xml',
        'extlClntAppOauthSettings\CommandCenterAuth_oauth.ecaOauth-meta.xml',
        'extlClntAppOauthPolicies\CommandCenterAuth_oauthPlcy.ecaOauthPlcy-meta.xml'
    )

    foreach ($relativePath in $filesToStage) {
        $sourcePath = Join-Path $SalesforceRoot ('force-app\main\default\' + $relativePath)
        $destinationPath = Join-Path $stageAppRoot $relativePath
        $destinationDirectory = Split-Path -Parent $destinationPath
        New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
        Copy-Item -Path $sourcePath -Destination $destinationPath -Force
    }

    $oauthSettingsPath = Join-Path $stageAppRoot 'extlClntAppGlobalOauthSets\CommandCenterAuth_glbloauth.ecaGlblOauth-meta.xml'
    $oauthSettingsContent = Get-Content -Path $oauthSettingsPath -Raw
    $oauthSettingsContent = $oauthSettingsContent -replace '<consumerKey>.*?</consumerKey>', ('<consumerKey>{0}</consumerKey>' -f $ClientId)
    Set-Content -Path $oauthSettingsPath -Value $oauthSettingsContent -Encoding UTF8

    return (Join-Path $stageRoot 'force-app')
}

Import-CommandCenterEnv
$sfCommand = Get-RequiredCommandPath -Name 'sf' -Hint 'Install Salesforce CLI or run the bootstrap script.'

if ([string]::IsNullOrWhiteSpace($TargetOrg)) {
    throw 'Provide -TargetOrg or set SF_DEFAULT_ALIAS in .env.local.'
}

if ($LaunchLogin -and [string]::IsNullOrWhiteSpace($DataCloudAlias)) {
    throw 'LaunchLogin requires a separate Data Cloud alias. Provide -DataCloudAlias or set DATACLOUD_SALESFORCE_ALIAS in .env.local.'
}

if ($LaunchLogin -and $DataCloudAlias -eq $TargetOrg) {
    throw "LaunchLogin requires a separate Data Cloud alias. '$TargetOrg' is already the normal org alias. Use a dedicated alias such as '${TargetOrg}_DC'."
}

$externalClientApplicationName = 'CommandCenterAuth'
$salesforceRoot = Resolve-CommandCenterPath 'salesforce'
$deployJobId = ''
$metadataMembers = @(
    ("ExternalClientApplication:{0}" -f $externalClientApplicationName),
    'ExtlClntAppGlobalOauthSettings:CommandCenterAuth_glbloauth',
    'ExtlClntAppOauthSettings:CommandCenterAuth_oauth',
    'ExtlClntAppOauthConfigurablePolicies:CommandCenterAuth_oauthPlcy'
)
$metadataPaths = @(
    'force-app/main/default/externalClientApps/CommandCenterAuth.eca-meta.xml',
    'force-app/main/default/extlClntAppGlobalOauthSets/CommandCenterAuth_glbloauth.ecaGlblOauth-meta.xml',
    'force-app/main/default/extlClntAppOauthSettings/CommandCenterAuth_oauth.ecaOauth-meta.xml',
    'force-app/main/default/extlClntAppOauthPolicies/CommandCenterAuth_oauthPlcy.ecaOauthPlcy-meta.xml'
)

$orgDisplayRaw = & $sfCommand org display --target-org $TargetOrg --json 2>$null
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($orgDisplayRaw)) {
    throw "Unable to resolve Salesforce CLI auth for target org alias '$TargetOrg'. Log in with scripts/salesforce/login-web.ps1 first."
}

$orgDisplay = $orgDisplayRaw | ConvertFrom-Json
if ($null -eq $orgDisplay.result -or [string]::IsNullOrWhiteSpace($orgDisplay.result.instanceUrl) -or [string]::IsNullOrWhiteSpace($orgDisplay.result.username)) {
    throw "Salesforce CLI auth for alias '$TargetOrg' did not include an instance URL and username. Reauthorize the alias before deploying CommandCenterAuth."
}

$commandCenterAuthClientId = New-CommandCenterAuthClientId -OrgId $orgDisplay.result.id

foreach ($relativeMetadataPath in $metadataPaths) {
    $absoluteMetadataPath = Join-Path $salesforceRoot $relativeMetadataPath
    if (-not (Test-Path $absoluteMetadataPath)) {
        throw "CommandCenterAuth deployment metadata is missing: '$relativeMetadataPath'."
    }
}

Write-Host ("Deploying '{0}' to org alias '{1}' ({2})." -f $externalClientApplicationName, $TargetOrg, $orgDisplay.result.username) -ForegroundColor Cyan
if ($LaunchLogin) {
    Write-Host ("Data Cloud login alias: {0}" -f $DataCloudAlias) -ForegroundColor DarkGray
}

Push-Location $salesforceRoot
try {
    $stagedDeploymentRoot = New-StagedCommandCenterAuthDeployment -SalesforceRoot $salesforceRoot -ClientId $commandCenterAuthClientId
    $deployArgs = @('project', 'deploy', 'start', '--target-org', $TargetOrg, '--source-dir', $stagedDeploymentRoot, '--json')

    $deployResultRaw = & $sfCommand @deployArgs
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($deployResultRaw)) {
        throw "CommandCenterAuth deployment command failed for '$TargetOrg'."
    }

    $deployResult = $deployResultRaw | ConvertFrom-Json

    if ($null -ne $deployResult.result) {
        $deployJobId = $deployResult.result.id
    }

    if ($deployResult.status -ne 0 -or $null -eq $deployResult.result -or -not $deployResult.result.success) {
        $failureMessages = @()
        $componentFailures = @($deployResult.result.details.componentFailures)
        foreach ($failure in $componentFailures) {
            if ($null -eq $failure) {
                continue
            }

            $problemType = if ([string]::IsNullOrWhiteSpace($failure.problemType)) { 'Error' } else { $failure.problemType }
            $fullName = if ([string]::IsNullOrWhiteSpace($failure.fullName)) { $failure.componentType } else { $failure.fullName }
            $failureMessages += ('{0}: {1} ({2})' -f $fullName, $failure.problem, $problemType)
        }

        if (-not [string]::IsNullOrWhiteSpace($deployJobId)) {
            Write-Host ("CommandCenterAuth deploy did not report success. Inspect deployment job {0}." -f $deployJobId) -ForegroundColor Yellow
        }

        if ($failureMessages.Count -gt 0) {
            throw (("CommandCenterAuth deployment failed for '{0}'.`n{1}" -f $TargetOrg, ($failureMessages -join "`n")))
        }

        throw "CommandCenterAuth deployment failed for '$TargetOrg'."
    }
} finally {
    if ($stagedDeploymentRoot -and (Test-Path $stagedDeploymentRoot)) {
        Remove-Item -Path $stagedDeploymentRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    Pop-Location
}

Set-RegisteredDataCloudClientId -Alias $TargetOrg -ClientId $commandCenterAuthClientId
Set-CommandCenterEnvValue -Name 'DATACLOUD_CLIENT_ID' -Value $commandCenterAuthClientId

Write-Host ("External client app '{0}' deployed to '{1}'." -f $externalClientApplicationName, $TargetOrg) -ForegroundColor Green
Write-Host ("Resolved org-specific Data Cloud client id: {0}" -f $commandCenterAuthClientId) -ForegroundColor DarkGray
if (-not [string]::IsNullOrWhiteSpace($deployJobId)) {
    Write-Host ("Deployment job ID: {0}" -f $deployJobId) -ForegroundColor DarkGray
}

Write-Host 'Manual Setup still required unless the org already has it:' -ForegroundColor Yellow
Write-Host '- Confirm the app is visible in Setup -> External Client App Manager.' -ForegroundColor Yellow
Write-Host '- Confirm the deployed OAuth policy allows the intended users to self-authorize the app.' -ForegroundColor Yellow
Write-Host '- Confirm Data Cloud is provisioned and the user can authorize cdp_ingest_api.' -ForegroundColor Yellow
Write-Host '- Create or verify the Ingestion API connector and destination data streams in Data Cloud Setup.' -ForegroundColor Yellow

if (-not $LaunchLogin) {
    return
}

$loginScriptPath = Join-Path $PSScriptRoot 'data-cloud-login-web.ps1'
Write-Host ("Launching Data Cloud auth with alias '{0}' against '{1}'." -f $DataCloudAlias, $orgDisplay.result.instanceUrl) -ForegroundColor Cyan
& $loginScriptPath -Alias $DataCloudAlias -InstanceUrl $orgDisplay.result.instanceUrl -ClientId $commandCenterAuthClientId -SetDefault:$SetDefault -ValidateAfterLogin
exit $LASTEXITCODE