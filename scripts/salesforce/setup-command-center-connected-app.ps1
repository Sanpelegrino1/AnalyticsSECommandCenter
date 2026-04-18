[CmdletBinding()]
param(
    [string]$TargetOrg = $env:SF_DEFAULT_ALIAS,
    [switch]$LaunchLogin,
    [switch]$SetDefault
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\CommandCenter.Common.ps1')

Import-CommandCenterEnv
Assert-CommandAvailable -Name 'sf' -Hint 'Install Salesforce CLI or run the bootstrap script.'

if ([string]::IsNullOrWhiteSpace($TargetOrg)) {
    throw 'Provide -TargetOrg or set SF_DEFAULT_ALIAS in .env.local.'
}

$externalClientApplicationName = 'CommandCenterAuth'
$salesforceRoot = Resolve-CommandCenterPath 'salesforce'

Push-Location $salesforceRoot
try {
    & sf project deploy start --target-org $TargetOrg --metadata ("ExternalClientApplication:{0}" -f $externalClientApplicationName) --metadata 'ExtlClntAppGlobalOauthSettings:CommandCenterAuth_glbloauth' --metadata 'ExtlClntAppOauthSettings:CommandCenterAuth_oauth' --metadata 'ExtlClntAppOauthConfigurablePolicies:CommandCenterAuth_oauthPlcy'
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}

Write-Host ("External client app '{0}' deployed to '{1}'." -f $externalClientApplicationName, $TargetOrg) -ForegroundColor Green

if (-not $LaunchLogin) {
    return
}

$orgDisplay = & sf org display --target-org $TargetOrg --json 2>$null | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $null -eq $orgDisplay.result -or [string]::IsNullOrWhiteSpace($orgDisplay.result.instanceUrl)) {
    throw "Connected app deployed, but the org instance URL could not be resolved for alias '$TargetOrg'."
}

$loginScriptPath = Join-Path $PSScriptRoot 'data-cloud-login-web.ps1'
& $loginScriptPath -Alias $TargetOrg -InstanceUrl $orgDisplay.result.instanceUrl -SetDefault:$SetDefault -ValidateAfterLogin
exit $LASTEXITCODE