[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Alias,

    [Parameter(Mandatory = $true)]
    [string]$Descriptor,

    [string]$ParamsJson = '{}',
    [string]$ParamsPath = '',
    [string]$CallingDescriptor = 'markup://one:one',
    [string]$ContextPath = 'tmp/aura-context.json',
    [string]$PageUri = '/one/one.app',
    [string]$OutputPath = 'tmp/aura-response.json'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'DataCloud.Common.ps1')

function ConvertTo-NativeValue {
    param(
        [Parameter(Mandatory = $false)]
        $InputObject
    )

    if ($null -eq $InputObject) {
        return $null
    }

    if ($InputObject -is [System.Collections.IDictionary]) {
        $result = [ordered]@{}
        foreach ($key in $InputObject.Keys) {
            $result[$key] = ConvertTo-NativeValue -InputObject $InputObject[$key]
        }

        return $result
    }

    if ($InputObject -is [System.Collections.IEnumerable] -and -not ($InputObject -is [string])) {
        $items = @()
        foreach ($item in $InputObject) {
            $items += ,(ConvertTo-NativeValue -InputObject $item)
        }

        return $items
    }

    if ($InputObject -is [pscustomobject]) {
        $result = [ordered]@{}
        foreach ($property in $InputObject.PSObject.Properties) {
            $result[$property.Name] = ConvertTo-NativeValue -InputObject $property.Value
        }

        return $result
    }

    return $InputObject
}

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
$resolvedContextPath = (Resolve-Path $ContextPath).Path
$resolvedOutputPath = Resolve-CommandCenterPath $OutputPath
$outputDirectory = Split-Path -Parent $resolvedOutputPath
if (-not (Test-Path $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory | Out-Null
}

$context = Get-Content -Path $resolvedContextPath -Raw
$rawParamsJson = if (-not [string]::IsNullOrWhiteSpace($ParamsPath)) {
    Get-Content -Path (Resolve-Path $ParamsPath).Path -Raw
} else {
    $ParamsJson
}

$parsedParams = if ([string]::IsNullOrWhiteSpace($rawParamsJson)) { @{} } else { ConvertFrom-Json -InputObject $rawParamsJson }
$nativeParams = ConvertTo-NativeValue -InputObject $parsedParams
if ($null -eq $nativeParams) {
    $nativeParams = [ordered]@{}
}

if (-not ($nativeParams -is [System.Collections.IDictionary]) -or -not $nativeParams.Contains('clientOptions')) {
    if ($nativeParams -is [System.Collections.IDictionary]) {
        $nativeParams['clientOptions'] = @{}
    } else {
        $nativeParams = [ordered]@{
            clientOptions = @{}
            value = $nativeParams
        }
    }
}

$action = [ordered]@{
    id = '1;a'
    descriptor = $Descriptor
    callingDescriptor = $CallingDescriptor
    params = $nativeParams
}

$message = @{ actions = @($action) } | ConvertTo-Json -Compress -Depth 20
$body = ConvertTo-FormUrlEncoded -Values @{
    message = $message
    'aura.context' = $context
    'aura.pageURI' = $PageUri
}

$requestSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$frontdoorUrl = "$($orgSession.instanceUrl)/secur/frontdoor.jsp?sid=$($orgSession.accessToken)&retURL=%2Fone%2Fone.app"
Invoke-WebRequest -Uri $frontdoorUrl -WebSession $requestSession -UseBasicParsing | Out-Null
Invoke-WebRequest -Uri "$lightningUrl/one/one.app" -WebSession $requestSession -UseBasicParsing | Out-Null
$ericCookie = Get-EricCookieValue -WebSession $requestSession -BaseUrls @($orgSession.instanceUrl, $lightningUrl)
$bodyWithToken = '{0}&aura.token={1}' -f $body, [Uri]::EscapeDataString($ericCookie)

$diagnosticPrefix = [System.IO.Path]::Combine($outputDirectory, [System.IO.Path]::GetFileNameWithoutExtension($resolvedOutputPath))
[System.IO.File]::WriteAllText("$diagnosticPrefix.message.json", $message)
[System.IO.File]::WriteAllText("$diagnosticPrefix.body.txt", $bodyWithToken)

$response = Invoke-WebRequest -Method Post -Uri "$lightningUrl/aura?r=1&other.one=1" -WebSession $requestSession -UseBasicParsing -ContentType 'application/x-www-form-urlencoded; charset=UTF-8' -Body $bodyWithToken

[System.IO.File]::WriteAllText($resolvedOutputPath, [string]$response.Content)
Write-Output $response.Content