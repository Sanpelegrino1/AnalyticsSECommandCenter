[CmdletBinding()]
param(
    [string]$Alias = $env:DATACLOUD_SALESFORCE_ALIAS,
    [string]$InstanceUrl = $env:SF_LOGIN_URL,
    [string]$ClientId = $env:DATACLOUD_CLIENT_ID,
    [string]$ClientSecret = $env:DATACLOUD_CLIENT_SECRET,
    [string]$Scopes = 'api refresh_token offline_access cdp_ingest_api',
    [string]$Purpose = 'Data Cloud ingestion auth',
    [string]$Notes = '',
    [string]$ValidationTargetKey,
    [string]$RedirectUri = 'http://localhost:1718/OauthRedirect',
    [int]$TimeoutSeconds = 300,
    [string]$AuthorizationCode,
    [string]$CallbackUrl,
    [switch]$UseManualOAuth,
    [switch]$ValidateAfterLogin,
    [switch]$SetDefault
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'DataCloud.Common.ps1')

function Complete-DataCloudCliLogin {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Alias,
        [Parameter(Mandatory = $true)]
        [string]$InstanceUrl,
        [Parameter(Mandatory = $true)]
        [string]$ClientId,
        [Parameter(Mandatory = $true)]
        [string]$Scopes,
        [switch]$SetDefault
    )

    $authScriptPath = Resolve-CommandCenterPath 'salesforce/scripts/auth-web.ps1'
    & $authScriptPath -Alias $Alias -InstanceUrl $InstanceUrl -ClientId $ClientId -Scopes $Scopes -SetDefault:$SetDefault
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    try {
        [void](Get-SalesforceCliOrgSession -Alias $Alias)
    } catch {
        throw "Salesforce CLI login did not produce a usable alias '$Alias'. $($_.Exception.Message)"
    }
}

function Get-RegisteredDataCloudClientId {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Alias
    )

    $registryPath = Resolve-CommandCenterPath 'notes/registries/salesforce-orgs.json'
    $registry = Read-JsonFile -Path $registryPath
    if (-not $registry) {
        return ''
    }

    $orgRecord = @($registry.orgs | Where-Object { $_.alias -eq $Alias } | Select-Object -First 1)
    if ($orgRecord.Count -eq 0) {
        return ''
    }

    $clientIdProperty = $orgRecord[0].PSObject.Properties['dataCloudClientId']
    if ($null -eq $clientIdProperty -or [string]::IsNullOrWhiteSpace([string]$clientIdProperty.Value)) {
        return ''
    }

    return [string]$clientIdProperty.Value
}

function Get-PendingDataCloudLoginStatePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Alias
    )

    $safeAlias = ($Alias -replace '[^A-Za-z0-9._-]', '_')
    return (Resolve-CommandCenterPath ('tmp/data-cloud-oauth/{0}.json' -f $safeAlias))
}

function Get-PendingDataCloudLoginState {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Alias
    )

    $statePath = Get-PendingDataCloudLoginStatePath -Alias $Alias
    if (-not (Test-Path $statePath)) {
        return $null
    }

    return Read-JsonFile -Path $statePath
}

function Save-PendingDataCloudLoginState {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Alias,
        [Parameter(Mandatory = $true)]
        [hashtable]$State
    )

    $statePath = Get-PendingDataCloudLoginStatePath -Alias $Alias
    $stateDirectory = Split-Path -Parent $statePath
    if (-not (Test-Path $stateDirectory)) {
        New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null
    }

    Write-JsonFile -Path $statePath -Value ([pscustomobject]$State)
}

function Clear-PendingDataCloudLoginState {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Alias
    )

    $statePath = Get-PendingDataCloudLoginStatePath -Alias $Alias
    if (Test-Path $statePath) {
        Remove-Item -Path $statePath -Force -ErrorAction SilentlyContinue
    }
}

function ConvertTo-Base64Url {
    param(
        [Parameter(Mandatory = $true)]
        [byte[]]$Bytes
    )

    return [Convert]::ToBase64String($Bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

function New-PkceVerifier {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return ConvertTo-Base64Url -Bytes $bytes
}

function Get-PkceChallenge {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Verifier
    )

    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hashBytes = $sha256.ComputeHash([System.Text.Encoding]::ASCII.GetBytes($Verifier))
        return ConvertTo-Base64Url -Bytes $hashBytes
    } finally {
        $sha256.Dispose()
    }
}

function Send-OAuthBrowserResponse {
    param(
        [Parameter(Mandatory = $true)]
        [System.Net.HttpListenerContext]$Context,
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [bool]$IsSuccess = $true
    )

    $statusText = if ($IsSuccess) { 'Authorization complete' } else { 'Authorization failed' }
    $html = @"
<html>
  <head><title>$statusText</title></head>
  <body style="font-family: Segoe UI, sans-serif; margin: 2rem;">
    <h1>$statusText</h1>
    <p>$Message</p>
    <p>You can close this window and return to VS Code.</p>
  </body>
</html>
"@

    $buffer = [System.Text.Encoding]::UTF8.GetBytes($html)
    $Context.Response.ContentType = 'text/html; charset=utf-8'
    $Context.Response.ContentLength64 = $buffer.Length
    $Context.Response.OutputStream.Write($buffer, 0, $buffer.Length)
    $Context.Response.OutputStream.Close()
}

Import-CommandCenterEnv
Add-Type -AssemblyName System.Web

$pendingLoginState = $null
if (-not [string]::IsNullOrWhiteSpace($CallbackUrl) -or -not [string]::IsNullOrWhiteSpace($AuthorizationCode)) {
    $pendingLoginState = Get-PendingDataCloudLoginState -Alias $Alias
}

if (-not [string]::IsNullOrWhiteSpace($CallbackUrl) -and [string]::IsNullOrWhiteSpace($AuthorizationCode)) {
    $callbackUri = [Uri]$CallbackUrl
    $callbackQuery = [System.Web.HttpUtility]::ParseQueryString($callbackUri.Query)
    $AuthorizationCode = $callbackQuery['code']
}

if ([string]::IsNullOrWhiteSpace($Alias)) {
    throw 'Provide -Alias or set DATACLOUD_SALESFORCE_ALIAS in .env.local. Do not reuse the standard Salesforce org alias for Data Cloud auth.'
}

if ([string]::IsNullOrWhiteSpace($ClientId)) {
    $registeredClientId = Get-RegisteredDataCloudClientId -Alias $Alias
    if (-not [string]::IsNullOrWhiteSpace($registeredClientId)) {
        $ClientId = $registeredClientId
    }
}

if ([string]::IsNullOrWhiteSpace($ClientId) -and -not [string]::IsNullOrWhiteSpace($env:DATACLOUD_CLIENT_ID)) {
    $ClientId = $env:DATACLOUD_CLIENT_ID
}

if ([string]::IsNullOrWhiteSpace($ClientId) -and $null -ne $pendingLoginState -and -not [string]::IsNullOrWhiteSpace([string]$pendingLoginState.clientId)) {
    $ClientId = [string]$pendingLoginState.clientId
}

if ([string]::IsNullOrWhiteSpace($ClientId)) {
    $ClientId = 'CommandCenterAuthClient20260417A9F3D7K2M8Q4R6T1V5X'
}

if ([string]::IsNullOrWhiteSpace($ClientId)) {
    throw 'Provide -ClientId or set DATACLOUD_CLIENT_ID in .env.local.'
}

if ([string]::IsNullOrWhiteSpace($InstanceUrl)) {
    $InstanceUrl = 'https://login.salesforce.com'
}

if (($InstanceUrl -eq 'https://login.salesforce.com') -and $null -ne $pendingLoginState -and -not [string]::IsNullOrWhiteSpace([string]$pendingLoginState.instanceUrl)) {
    $InstanceUrl = [string]$pendingLoginState.instanceUrl
}

$normalizedInstanceUrl = Normalize-DataCloudUrl -Value $InstanceUrl
$shouldUseManualOAuth = $UseManualOAuth -or -not [string]::IsNullOrWhiteSpace($AuthorizationCode) -or -not [string]::IsNullOrWhiteSpace($CallbackUrl)

if (-not $shouldUseManualOAuth) {
    Complete-DataCloudCliLogin -Alias $Alias -InstanceUrl $normalizedInstanceUrl -ClientId $ClientId -Scopes $Scopes -SetDefault:$SetDefault

    Set-CommandCenterEnvValue -Name 'DATACLOUD_LOGIN_URL' -Value $normalizedInstanceUrl
    Set-CommandCenterEnvValue -Name 'DATACLOUD_SALESFORCE_ALIAS' -Value $Alias
    Set-CommandCenterEnvValue -Name 'DATACLOUD_CLIENT_ID' -Value $ClientId
    Set-CommandCenterEnvValue -Name 'DATACLOUD_CLIENT_SECRET' -Value ''
    Set-CommandCenterEnvValue -Name 'DATACLOUD_REFRESH_TOKEN' -Value ''
    Set-CommandCenterEnvValue -Name 'DATACLOUD_TOKEN_EXCHANGE_URL' -Value ''
    Set-CommandCenterEnvValue -Name 'DATACLOUD_SF_ACCESS_TOKEN' -Value ''
    Set-CommandCenterEnvValue -Name 'DATACLOUD_ACCESS_TOKEN' -Value ''
    Clear-PendingDataCloudLoginState -Alias $Alias

    Write-Host ("Registered dedicated Data Cloud Salesforce CLI session for alias '{0}'." -f $Alias) -ForegroundColor Green
    Write-Host 'Expected Data Cloud auth source order: Salesforce CLI session for DATACLOUD_SALESFORCE_ALIAS, then refresh-token fallback if configured.' -ForegroundColor DarkGray

    & (Join-Path $PSScriptRoot 'register-org.ps1') -Alias $Alias -LoginUrl $normalizedInstanceUrl -Purpose $Purpose -Notes $Notes -SetPreferred:$SetDefault

    if (-not $ValidateAfterLogin) {
        return
    }

    $validationScriptPath = Join-Path $PSScriptRoot 'data-cloud-get-access-token.ps1'
    $previousAlias = $env:DATACLOUD_SALESFORCE_ALIAS
    $env:DATACLOUD_SALESFORCE_ALIAS = $Alias

    try {
        $validationArgs = @{ AsJson = $true }
        if (-not [string]::IsNullOrWhiteSpace($ValidationTargetKey)) {
            $validationArgs.TargetKey = $ValidationTargetKey
        }

        Write-Host 'Validating Data Cloud token exchange...' -ForegroundColor Cyan
        $validationResult = & $validationScriptPath @validationArgs | ConvertFrom-Json
        $validationResult | Select-Object targetKey, tokenSource, salesforceAlias, tenantEndpoint, sourceName, objectName | Format-List
    } catch {
        throw "CLI login succeeded, but Data Cloud validation failed. Check the connected app scopes, dedicated alias, client ID, and Data Cloud setup. $($_.Exception.Message)"
    } finally {
        if ([string]::IsNullOrWhiteSpace($previousAlias)) {
            Remove-Item Env:DATACLOUD_SALESFORCE_ALIAS -ErrorAction SilentlyContinue
        } else {
            $env:DATACLOUD_SALESFORCE_ALIAS = $previousAlias
        }
    }

    return
}

$redirectUriObject = [Uri]$RedirectUri
$listenerPrefix = '{0}://{1}:{2}/' -f $redirectUriObject.Scheme, $redirectUriObject.Host, $redirectUriObject.Port
$expectedPath = $redirectUriObject.AbsolutePath.TrimEnd('/')
if ([string]::IsNullOrWhiteSpace($expectedPath)) {
    $expectedPath = '/'
}

$codeVerifier = ''
$codeChallenge = ''
$state = ''

if ($null -ne $pendingLoginState -and -not [string]::IsNullOrWhiteSpace($AuthorizationCode)) {
    if (-not [string]::IsNullOrWhiteSpace([string]$pendingLoginState.redirectUri)) {
        $RedirectUri = [string]$pendingLoginState.redirectUri
        $redirectUriObject = [Uri]$RedirectUri
        $listenerPrefix = '{0}://{1}:{2}/' -f $redirectUriObject.Scheme, $redirectUriObject.Host, $redirectUriObject.Port
        $expectedPath = $redirectUriObject.AbsolutePath.TrimEnd('/')
        if ([string]::IsNullOrWhiteSpace($expectedPath)) {
            $expectedPath = '/'
        }
    }

    $codeVerifier = [string]$pendingLoginState.codeVerifier
    $state = [string]$pendingLoginState.state
} else {
    $codeVerifier = New-PkceVerifier
    $state = [guid]::NewGuid().ToString('N')
}

$codeChallenge = Get-PkceChallenge -Verifier $codeVerifier

$listener = [System.Net.HttpListener]::new()
$listener.Prefixes.Add($listenerPrefix)

if ([string]::IsNullOrWhiteSpace($AuthorizationCode)) {
    try {
        Save-PendingDataCloudLoginState -Alias $Alias -State @{
            alias = $Alias
            clientId = $ClientId
            instanceUrl = $normalizedInstanceUrl
            redirectUri = $RedirectUri
            codeVerifier = $codeVerifier
            state = $state
            createdUtc = [DateTime]::UtcNow.ToString('o')
        }

        $listener.Start()
        $authorizeUri = '{0}/services/oauth2/authorize?{1}' -f $normalizedInstanceUrl, (ConvertTo-FormUrlEncoded -Values @{
            response_type = 'code'
            client_id = $ClientId
            redirect_uri = $RedirectUri
            scope = $Scopes
            code_challenge = $codeChallenge
            code_challenge_method = 'S256'
            state = $state
            prompt = 'login'
        })

        Write-Host ("Opening Data Cloud browser login for alias '{0}' against '{1}'." -f $Alias, $normalizedInstanceUrl) -ForegroundColor Cyan
        Write-Host ("Authorization URL: {0}" -f $authorizeUri) -ForegroundColor DarkGray
        Start-Process $authorizeUri | Out-Null

        $pendingContext = $listener.BeginGetContext($null, $null)
        if (-not $pendingContext.AsyncWaitHandle.WaitOne($TimeoutSeconds * 1000)) {
            Write-Warning 'Timed out waiting for the browser OAuth callback.'
            Write-Host ('Pending OAuth session saved to {0}.' -f (Get-PendingDataCloudLoginStatePath -Alias $Alias)) -ForegroundColor DarkGray
            Write-Host 'Fallback: rerun this script with -Alias and -CallbackUrl "<redirected URL>" after the browser redirects. The original PKCE verifier and state will be reused automatically.' -ForegroundColor Yellow
            return
        }

        $callbackContext = $listener.EndGetContext($pendingContext)
        $callbackPath = $callbackContext.Request.Url.AbsolutePath.TrimEnd('/')
        if ([string]::IsNullOrWhiteSpace($callbackPath)) {
            $callbackPath = '/'
        }

        if ($callbackPath -ne $expectedPath) {
            Send-OAuthBrowserResponse -Context $callbackContext -Message 'Unexpected callback path.' -IsSuccess:$false
            throw "Unexpected callback path '$callbackPath'."
        }

        $query = [System.Web.HttpUtility]::ParseQueryString($callbackContext.Request.Url.Query)
        if (-not [string]::IsNullOrWhiteSpace($query['error'])) {
            $errorMessage = if ([string]::IsNullOrWhiteSpace($query['error_description'])) { $query['error'] } else { '{0}: {1}' -f $query['error'], $query['error_description'] }
            Clear-PendingDataCloudLoginState -Alias $Alias
            Send-OAuthBrowserResponse -Context $callbackContext -Message $errorMessage -IsSuccess:$false
            throw "Browser authorization failed. $errorMessage"
        }

        if ($query['state'] -ne $state) {
            Clear-PendingDataCloudLoginState -Alias $Alias
            Send-OAuthBrowserResponse -Context $callbackContext -Message 'State validation failed.' -IsSuccess:$false
            throw 'Browser authorization failed because the returned state did not match.'
        }

        $authorizationCode = $query['code']
        if ([string]::IsNullOrWhiteSpace($authorizationCode)) {
            Clear-PendingDataCloudLoginState -Alias $Alias
            Send-OAuthBrowserResponse -Context $callbackContext -Message 'No authorization code was returned.' -IsSuccess:$false
            throw 'Browser authorization did not return an authorization code.'
        }

        Send-OAuthBrowserResponse -Context $callbackContext -Message 'The Data Cloud authorization succeeded.'
    } finally {
        if ($listener.IsListening) {
            $listener.Stop()
        }
        $listener.Close()
    }
} else {
    $authorizationCode = $AuthorizationCode

    if (-not [string]::IsNullOrWhiteSpace($CallbackUrl)) {
        $callbackUri = [Uri]$CallbackUrl
        $callbackQuery = [System.Web.HttpUtility]::ParseQueryString($callbackUri.Query)
        if (-not [string]::IsNullOrWhiteSpace($callbackQuery['state']) -and -not [string]::IsNullOrWhiteSpace($state) -and $callbackQuery['state'] -ne $state) {
            throw 'The callback URL state did not match the pending OAuth session for this alias.'
        }
    }
}

$tokenBody = @{
    grant_type = 'authorization_code'
    client_id = $ClientId
    code = $authorizationCode
    redirect_uri = $RedirectUri
    code_verifier = $codeVerifier
}

if (-not [string]::IsNullOrWhiteSpace($ClientSecret)) {
    $tokenBody.client_secret = $ClientSecret
}

try {
    $tokenResponse = Invoke-RestMethod -Method Post -Uri ('{0}/services/oauth2/token' -f $normalizedInstanceUrl) -ContentType 'application/x-www-form-urlencoded' -Body (ConvertTo-FormUrlEncoded -Values $tokenBody)
} catch {
    throw (Get-DataCloudErrorMessage -ErrorRecord $_)
}

if ([string]::IsNullOrWhiteSpace($tokenResponse.refresh_token)) {
    throw 'Browser authorization succeeded, but Salesforce did not return a refresh token. Confirm the connected app includes refresh_token and offline_access scopes.'
}

Set-CommandCenterEnvValue -Name 'DATACLOUD_LOGIN_URL' -Value $normalizedInstanceUrl
Set-CommandCenterEnvValue -Name 'DATACLOUD_SALESFORCE_ALIAS' -Value $Alias
Set-CommandCenterEnvValue -Name 'DATACLOUD_CLIENT_ID' -Value $ClientId
Set-CommandCenterEnvValue -Name 'DATACLOUD_CLIENT_SECRET' -Value $ClientSecret
Set-CommandCenterEnvValue -Name 'DATACLOUD_REFRESH_TOKEN' -Value $tokenResponse.refresh_token
Set-CommandCenterEnvValue -Name 'DATACLOUD_TOKEN_EXCHANGE_URL' -Value (Resolve-DataCloudTokenExchangeUrl -Value $tokenResponse.instance_url)
Set-CommandCenterEnvValue -Name 'DATACLOUD_SF_ACCESS_TOKEN' -Value ''
Set-CommandCenterEnvValue -Name 'DATACLOUD_ACCESS_TOKEN' -Value ''
Clear-PendingDataCloudLoginState -Alias $Alias

Write-Host ("Stored local-only Data Cloud auth settings for alias '{0}'." -f $Alias) -ForegroundColor Green
Write-Host 'Expected Data Cloud auth source order: Salesforce CLI session for DATACLOUD_SALESFORCE_ALIAS, then refresh-token fallback if configured.' -ForegroundColor DarkGray

& (Join-Path $PSScriptRoot 'register-org.ps1') -Alias $Alias -LoginUrl $normalizedInstanceUrl -Purpose $Purpose -Notes $Notes -SetPreferred:$SetDefault

if (-not $ValidateAfterLogin) {
    return
}

$validationScriptPath = Join-Path $PSScriptRoot 'data-cloud-get-access-token.ps1'
$previousAlias = $env:DATACLOUD_SALESFORCE_ALIAS
$env:DATACLOUD_SALESFORCE_ALIAS = $Alias

try {
    $validationArgs = @{
        AsJson = $true
    }

    if (-not [string]::IsNullOrWhiteSpace($ValidationTargetKey)) {
        $validationArgs.TargetKey = $ValidationTargetKey
    }

    Write-Host 'Validating Data Cloud token exchange...' -ForegroundColor Cyan
    $validationResult = & $validationScriptPath @validationArgs | ConvertFrom-Json
    $validationResult | Select-Object targetKey, tokenSource, tenantEndpoint, sourceName, objectName | Format-List
} catch {
    throw "Browser login succeeded, but Data Cloud validation failed. Check the connected app scopes, client ID, and Data Cloud setup. $($_.Exception.Message)"
} finally {
    if ([string]::IsNullOrWhiteSpace($previousAlias)) {
        Remove-Item Env:DATACLOUD_SALESFORCE_ALIAS -ErrorAction SilentlyContinue
    } else {
        $env:DATACLOUD_SALESFORCE_ALIAS = $previousAlias
    }
}