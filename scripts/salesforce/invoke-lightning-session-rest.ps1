[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Alias,

    [Parameter(Mandatory = $true)]
    [string]$RelativePath,

    [string]$Method = 'GET',
    [string]$BodyPath = '',
    [string]$BodyJson = '',
    [string]$ContentType = 'application/json; charset=UTF-8',
    [string]$OutputPath = 'tmp/rest-response.json'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'DataCloud.Common.ps1')

function Get-LightningUrl {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InstanceUrl
    )

    $normalized = $InstanceUrl.TrimEnd('/')
    if ($normalized -match '\.my\.salesforce\.com$') {
        return ($normalized -replace '\.my\.salesforce\.com$', '.lightning.force.com')
    }

    return $normalized
}

function Get-EricCookieValue {
    param(
        [Parameter(Mandatory = $true)]
        [Microsoft.PowerShell.Commands.WebRequestSession]$WebSession,

        [Parameter(Mandatory = $true)]
        [string[]]$BaseUrls
    )

    foreach ($baseUrl in $BaseUrls) {
        $cookieCollection = $WebSession.Cookies.GetCookies($baseUrl)
        $cookie = $cookieCollection | Where-Object { $_.Name -like '__Host-ERIC_*' } | Select-Object -First 1
        if ($null -ne $cookie -and -not [string]::IsNullOrWhiteSpace($cookie.Value)) {
            return $cookie.Value
        }
    }

    throw 'ERIC cookie not found after frontdoor bootstrap.'
}

$orgSession = Get-SalesforceCliOrgSession -Alias $Alias
$lightningUrl = Get-LightningUrl -InstanceUrl $orgSession.instanceUrl
$resolvedOutputPath = Resolve-CommandCenterPath $OutputPath
$outputDirectory = Split-Path -Parent $resolvedOutputPath
if (-not (Test-Path $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory | Out-Null
}

$body = if (-not [string]::IsNullOrWhiteSpace($BodyPath)) {
    Get-Content -Path (Resolve-Path $BodyPath).Path -Raw
} else {
    $BodyJson
}

$requestSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$frontdoorUrl = "$($orgSession.instanceUrl)/secur/frontdoor.jsp?sid=$($orgSession.accessToken)&retURL=%2Fone%2Fone.app"
Invoke-WebRequest -Uri $frontdoorUrl -WebSession $requestSession -UseBasicParsing | Out-Null
Invoke-WebRequest -Uri "$lightningUrl/one/one.app" -WebSession $requestSession -UseBasicParsing | Out-Null
$null = Get-EricCookieValue -WebSession $requestSession -BaseUrls @($orgSession.instanceUrl, $lightningUrl)

$requestUri = if ($RelativePath.StartsWith('http://') -or $RelativePath.StartsWith('https://')) {
    $RelativePath
} elseif ($RelativePath.StartsWith('/services/data/')) {
    '{0}{1}' -f $orgSession.instanceUrl.TrimEnd('/'), $RelativePath
} else {
    '{0}{1}' -f $lightningUrl.TrimEnd('/'), $RelativePath
}

$diagnosticPrefix = [System.IO.Path]::Combine($outputDirectory, [System.IO.Path]::GetFileNameWithoutExtension($resolvedOutputPath))
$requestLine = '{0} {1}' -f $Method.ToUpperInvariant(), $requestUri
[System.IO.File]::WriteAllText("$diagnosticPrefix.request.txt", $requestLine)
if (-not [string]::IsNullOrWhiteSpace($body)) {
    [System.IO.File]::WriteAllText("$diagnosticPrefix.body.json", $body)
}

$requestParameters = @{
    Method = $Method
    Uri = $requestUri
    WebSession = $requestSession
    UseBasicParsing = $true
    Headers = @{
        Accept = 'application/json'
        Authorization = 'Bearer {0}' -f $orgSession.accessToken
    }
}

if (-not [string]::IsNullOrWhiteSpace($body)) {
    $requestParameters['Body'] = $body
    $requestParameters['ContentType'] = $ContentType
}

try {
    $response = Invoke-WebRequest @requestParameters
    [System.IO.File]::WriteAllText($resolvedOutputPath, [string]$response.Content)
    Write-Output $response.Content
} catch [System.Net.WebException] {
    $exception = $_.Exception
    if ($null -ne $exception.Response) {
        $reader = New-Object System.IO.StreamReader($exception.Response.GetResponseStream())
        $errorBody = $reader.ReadToEnd()
        $reader.Dispose()
        [System.IO.File]::WriteAllText($resolvedOutputPath, $errorBody)
        Write-Output $errorBody
        exit 1
    }

    throw
}