Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\CommandCenter.Common.ps1')

function ConvertTo-FormUrlEncoded {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Values
    )

    $pairs = foreach ($key in $Values.Keys) {
        $value = $Values[$key]
        if ($null -eq $value -or [string]::IsNullOrWhiteSpace([string]$value)) {
            continue
        }

        '{0}={1}' -f [Uri]::EscapeDataString([string]$key), [Uri]::EscapeDataString([string]$value)
    }

    return ($pairs -join '&')
}

function Normalize-DataCloudUrl {
    param(
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ''
    }

    $trimmed = $Value.Trim()
    if ($trimmed -match '^https?://') {
        return $trimmed.TrimEnd('/')
    }

    return ('https://{0}' -f $trimmed.Trim('/')).TrimEnd('/')
}

function Resolve-DataCloudTokenExchangeUrl {
    param(
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ''
    }

    $normalized = Normalize-DataCloudUrl -Value $Value
    if ($normalized -match '/services/a360/token$') {
        return $normalized
    }

    return '{0}/services/a360/token' -f $normalized
}

function Get-SalesforceCliOrgSession {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Alias
    )

    Assert-CommandAvailable -Name 'sf' -Hint 'Install Salesforce CLI or run the bootstrap script.'

    $output = & sf org display --target-org $Alias --json 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($output)) {
        throw "Unable to resolve Salesforce CLI auth for alias '$Alias'. Log in again or set DATACLOUD_SF_ACCESS_TOKEN explicitly."
    }

    $payload = $output | ConvertFrom-Json
    if ($null -eq $payload.result -or [string]::IsNullOrWhiteSpace($payload.result.accessToken) -or [string]::IsNullOrWhiteSpace($payload.result.instanceUrl)) {
        throw "Salesforce CLI auth for alias '$Alias' did not include an access token and instance URL."
    }

    return [pscustomobject]@{
        alias = $Alias
        accessToken = $payload.result.accessToken
        instanceUrl = Normalize-DataCloudUrl -Value $payload.result.instanceUrl
    }
}

function Get-DataCloudRegistryPath {
    return Resolve-CommandCenterPath 'notes/registries/data-cloud-targets.json'
}

function Get-DataCloudRegistry {
    $registryPath = Get-DataCloudRegistryPath
    $registry = Read-JsonFile -Path $registryPath

    if ($null -eq $registry) {
        return [pscustomobject]@{
            defaultTargetKey = ''
            targets = @()
        }
    }

    if ($null -eq $registry.targets) {
        $registry | Add-Member -NotePropertyName 'targets' -NotePropertyValue @() -Force
    }

    if ($null -eq $registry.defaultTargetKey) {
        $registry | Add-Member -NotePropertyName 'defaultTargetKey' -NotePropertyValue '' -Force
    }

    return $registry
}

function Save-DataCloudRegistry {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Registry
    )

    Write-JsonFile -Path (Get-DataCloudRegistryPath) -Value $Registry
}

function Get-DataCloudManifestInfo {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ManifestPath
    )

    $resolvedManifestPath = (Resolve-Path $ManifestPath).Path
    $manifest = Get-Content -Path $resolvedManifestPath -Raw | ConvertFrom-Json

    if ($null -eq $manifest.files -or @($manifest.files).Count -eq 0) {
        throw "Manifest '$resolvedManifestPath' does not define any files."
    }

    return [pscustomobject]@{
        Path = $resolvedManifestPath
        Directory = Split-Path -Parent $resolvedManifestPath
        Content = $manifest
    }
}

function Resolve-DataCloudManifestTargetKey {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TableName,
        [string]$TargetKeyPrefix,
        [string]$TargetKeySeparator = '-'
    )

    if ([string]::IsNullOrWhiteSpace($TargetKeyPrefix)) {
        return $TableName
    }

    if ([string]::IsNullOrWhiteSpace($TargetKeySeparator)) {
        return '{0}{1}' -f $TargetKeyPrefix, $TableName
    }

    return '{0}{1}{2}' -f $TargetKeyPrefix, $TargetKeySeparator, $TableName
}

function Resolve-DataCloudManifestObjectName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TableName,
        [string]$ObjectNamePrefix,
        [string]$ObjectNameSeparator = '_'
    )

    if ([string]::IsNullOrWhiteSpace($ObjectNamePrefix)) {
        return $TableName
    }

    if ([string]::IsNullOrWhiteSpace($ObjectNameSeparator)) {
        return '{0}{1}' -f $ObjectNamePrefix, $TableName
    }

    return '{0}{1}{2}' -f $ObjectNamePrefix, $ObjectNameSeparator, $TableName
}

function Get-DataCloudManifestPrimaryKey {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Manifest,
        [Parameter(Mandatory = $true)]
        [string]$TableName
    )

    $tableDefinition = @($Manifest.joinGraph | Where-Object { $_.tableName -eq $TableName } | Select-Object -First 1)
    if ($tableDefinition.Count -eq 0 -or $null -eq $tableDefinition[0].primaryKey) {
        return ''
    }

    return [string]::Join(',', @($tableDefinition[0].primaryKey))
}

function Resolve-DataCloudManifestCsvPath {
    param(
        [Parameter(Mandatory = $true)]
        [object]$ManifestInfo,
        [Parameter(Mandatory = $true)]
        [object]$FileDefinition
    )

    $csvPath = Join-Path $ManifestInfo.Directory $FileDefinition.fileName
    if (-not (Test-Path $csvPath)) {
        throw "Manifest file entry '$($FileDefinition.fileName)' for table '$($FileDefinition.tableName)' was not found at '$csvPath'."
    }

    return (Resolve-Path $csvPath).Path
}

function Get-DataCloudTargetConfiguration {
    param(
        [string]$TargetKey
    )

    Import-CommandCenterEnv
    $registry = Get-DataCloudRegistry

    $resolvedTargetKey = $TargetKey
    if ([string]::IsNullOrWhiteSpace($resolvedTargetKey)) {
        if (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_DEFAULT_TARGET)) {
            $resolvedTargetKey = $env:DATACLOUD_DEFAULT_TARGET
        } elseif (-not [string]::IsNullOrWhiteSpace($registry.defaultTargetKey)) {
            $resolvedTargetKey = $registry.defaultTargetKey
        }
    }

    $target = $null
    if (-not [string]::IsNullOrWhiteSpace($resolvedTargetKey)) {
        $target = @($registry.targets | Where-Object { $_.key -eq $resolvedTargetKey } | Select-Object -First 1)
        if ($target.Count -eq 0) {
            throw "Data Cloud target '$resolvedTargetKey' was not found in notes/registries/data-cloud-targets.json."
        }

        $target = $target[0]
    }

    return [pscustomobject]@{
        TargetKey = $resolvedTargetKey
        LoginUrl = if (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_LOGIN_URL)) { Normalize-DataCloudUrl -Value $env:DATACLOUD_LOGIN_URL } elseif ($null -ne $target -and -not [string]::IsNullOrWhiteSpace($target.loginUrl)) { Normalize-DataCloudUrl -Value $target.loginUrl } elseif (-not [string]::IsNullOrWhiteSpace($env:SF_LOGIN_URL)) { Normalize-DataCloudUrl -Value $env:SF_LOGIN_URL } else { 'https://login.salesforce.com' }
        TenantEndpoint = if (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_TENANT_ENDPOINT)) { Normalize-DataCloudUrl -Value $env:DATACLOUD_TENANT_ENDPOINT } elseif ($null -ne $target -and -not [string]::IsNullOrWhiteSpace($target.tenantEndpoint)) { Normalize-DataCloudUrl -Value $target.tenantEndpoint } else { '' }
        SourceName = if (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_SOURCE_NAME)) { $env:DATACLOUD_SOURCE_NAME } elseif ($null -ne $target) { $target.sourceName } else { '' }
        ObjectName = if (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_OBJECT_NAME)) { $env:DATACLOUD_OBJECT_NAME } elseif ($null -ne $target) { $target.objectName } else { '' }
        ObjectEndpoint = if (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_OBJECT_ENDPOINT)) { $env:DATACLOUD_OBJECT_ENDPOINT } elseif ($null -ne $target) { $target.objectEndpoint } else { '' }
        SalesforceAlias = if (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_SALESFORCE_ALIAS)) { $env:DATACLOUD_SALESFORCE_ALIAS } elseif ($null -ne $target -and -not [string]::IsNullOrWhiteSpace($target.salesforceAlias)) { $target.salesforceAlias } elseif (-not [string]::IsNullOrWhiteSpace($env:SF_DEFAULT_ALIAS)) { $env:SF_DEFAULT_ALIAS } else { '' }
        DataStreamLabel = if ($null -ne $target) { $target.dataStreamLabel } else { '' }
        Category = if ($null -ne $target) { $target.category } else { '' }
        PrimaryKey = if ($null -ne $target) { $target.primaryKey } else { '' }
        RecordModifiedField = if ($null -ne $target) { $target.recordModifiedField } else { '' }
        SchemaPath = if ($null -ne $target) { $target.schemaPath } else { '' }
        Notes = if ($null -ne $target) { $target.notes } else { '' }
        Registry = $registry
        Target = $target
    }
}

function Get-DataCloudErrorMessage {
    param(
        [Parameter(Mandatory = $true)]
        [System.Management.Automation.ErrorRecord]$ErrorRecord
    )

    $message = $ErrorRecord.Exception.Message
    $response = $ErrorRecord.Exception.Response
    if ($null -eq $response) {
        return $message
    }

    try {
        $stream = $response.GetResponseStream()
        if ($null -eq $stream) {
            return $message
        }

        $reader = New-Object System.IO.StreamReader($stream)
        $body = $reader.ReadToEnd()
        if ([string]::IsNullOrWhiteSpace($body)) {
            return $message
        }

        return "$message`n$body"
    } catch {
        return $message
    }
}

function Get-DataCloudAccessContext {
    param(
        [string]$TargetKey
    )

    $config = Get-DataCloudTargetConfiguration -TargetKey $TargetKey

    if (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_ACCESS_TOKEN)) {
        if ([string]::IsNullOrWhiteSpace($config.TenantEndpoint)) {
            throw 'DATACLOUD_ACCESS_TOKEN is set, but no tenant endpoint is available. Set DATACLOUD_TENANT_ENDPOINT or register the target with tenantEndpoint.'
        }

        return [pscustomobject]@{
            AccessToken = $env:DATACLOUD_ACCESS_TOKEN
            TenantEndpoint = $config.TenantEndpoint
            Config = $config
            TokenSource = 'direct-datacloud-token'
        }
    }

    $salesforceAccessToken = $env:DATACLOUD_SF_ACCESS_TOKEN
    $tokenExchangeUrl = Resolve-DataCloudTokenExchangeUrl -Value $env:DATACLOUD_TOKEN_EXCHANGE_URL
    $tokenSource = 'salesforce-token-exchange'

    if ([string]::IsNullOrWhiteSpace($salesforceAccessToken)) {
        if (-not [string]::IsNullOrWhiteSpace($config.SalesforceAlias)) {
            $cliSession = Get-SalesforceCliOrgSession -Alias $config.SalesforceAlias
            $salesforceAccessToken = $cliSession.accessToken
            if ([string]::IsNullOrWhiteSpace($tokenExchangeUrl)) {
                $tokenExchangeUrl = Resolve-DataCloudTokenExchangeUrl -Value $cliSession.instanceUrl
            }

            $tokenSource = 'salesforce-cli-session'
        } elseif ([string]::IsNullOrWhiteSpace($env:DATACLOUD_CLIENT_ID) -or [string]::IsNullOrWhiteSpace($env:DATACLOUD_REFRESH_TOKEN)) {
            throw 'No usable Data Cloud auth configuration was found. Set DATACLOUD_ACCESS_TOKEN and DATACLOUD_TENANT_ENDPOINT, log into Salesforce CLI with a Data Cloud-scoped connected app, or set DATACLOUD_CLIENT_ID and DATACLOUD_REFRESH_TOKEN for token exchange.'
        }
    }

    if ([string]::IsNullOrWhiteSpace($salesforceAccessToken)) {
        throw 'A Salesforce access token was not available for Data Cloud token exchange.'
    }

    if ($tokenSource -ne 'salesforce-cli-session') {

        $tokenRequestBody = @{
            grant_type = 'refresh_token'
            client_id = $env:DATACLOUD_CLIENT_ID
            refresh_token = $env:DATACLOUD_REFRESH_TOKEN
        }

        if (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_CLIENT_SECRET)) {
            $tokenRequestBody.client_secret = $env:DATACLOUD_CLIENT_SECRET
        }

        $salesforceTokenUrl = '{0}/services/oauth2/token' -f $config.LoginUrl

        try {
            $salesforceResponse = Invoke-RestMethod -Method Post -Uri $salesforceTokenUrl -ContentType 'application/x-www-form-urlencoded' -Body (ConvertTo-FormUrlEncoded -Values $tokenRequestBody)
        } catch {
            throw (Get-DataCloudErrorMessage -ErrorRecord $_)
        }

        $salesforceAccessToken = $salesforceResponse.access_token
        if ([string]::IsNullOrWhiteSpace($tokenExchangeUrl)) {
            $tokenExchangeUrl = Resolve-DataCloudTokenExchangeUrl -Value $salesforceResponse.instance_url
        }
    }

    if ([string]::IsNullOrWhiteSpace($tokenExchangeUrl)) {
        throw 'A token exchange URL was not available. Set DATACLOUD_TOKEN_EXCHANGE_URL, log into Salesforce CLI with a Data Cloud-scoped connected app, or use the refresh-token flow so the exchange URL comes back from Salesforce OAuth.'
    }

    $exchangeBody = @{
        grant_type = 'urn:salesforce:grant-type:external:cdp'
        subject_token = $salesforceAccessToken
        subject_token_type = 'urn:ietf:params:oauth:token-type:access_token'
    }

    try {
        $exchangeResponse = Invoke-RestMethod -Method Post -Uri $tokenExchangeUrl -ContentType 'application/x-www-form-urlencoded' -Body (ConvertTo-FormUrlEncoded -Values $exchangeBody)
    } catch {
        throw (Get-DataCloudErrorMessage -ErrorRecord $_)
    }

    $tenantEndpoint = if (-not [string]::IsNullOrWhiteSpace($config.TenantEndpoint)) {
        $config.TenantEndpoint
    } else {
        Normalize-DataCloudUrl -Value $exchangeResponse.instance_url
    }

    if ([string]::IsNullOrWhiteSpace($tenantEndpoint)) {
        throw 'Unable to determine the Data Cloud tenant endpoint. Register the target with tenantEndpoint or set DATACLOUD_TENANT_ENDPOINT.'
    }

    $resolvedConfig = [pscustomobject]@{
        TargetKey = $config.TargetKey
        LoginUrl = $config.LoginUrl
        TenantEndpoint = $tenantEndpoint
        SourceName = $config.SourceName
        ObjectName = $config.ObjectName
        ObjectEndpoint = $config.ObjectEndpoint
        SalesforceAlias = $config.SalesforceAlias
        DataStreamLabel = $config.DataStreamLabel
        Category = $config.Category
        PrimaryKey = $config.PrimaryKey
        RecordModifiedField = $config.RecordModifiedField
        SchemaPath = $config.SchemaPath
        Notes = $config.Notes
        Registry = $config.Registry
        Target = $config.Target
    }

    return [pscustomobject]@{
        AccessToken = $exchangeResponse.access_token
        TenantEndpoint = $tenantEndpoint
        Config = $resolvedConfig
        TokenSource = $tokenSource
    }
}

function Invoke-DataCloudJsonRequest {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Context,
        [Parameter(Mandatory = $true)]
        [ValidateSet('Get', 'Post', 'Patch', 'Delete')]
        [string]$Method,
        [Parameter(Mandatory = $true)]
        [string]$RelativePath,
        [hashtable]$Query,
        [object]$Body
    )

    $uri = '{0}{1}' -f $Context.TenantEndpoint, $RelativePath
    if ($null -ne $Query -and $Query.Count -gt 0) {
        $queryString = ConvertTo-FormUrlEncoded -Values $Query
        if (-not [string]::IsNullOrWhiteSpace($queryString)) {
            $uri = '{0}?{1}' -f $uri, $queryString
        }
    }

    $headers = @{ Authorization = 'Bearer {0}' -f $Context.AccessToken }

    try {
        if ($PSBoundParameters.ContainsKey('Body')) {
            return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -ContentType 'application/json' -Body ($Body | ConvertTo-Json -Depth 10)
        }

        return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers
    } catch {
        throw (Get-DataCloudErrorMessage -ErrorRecord $_)
    }
}

function Wait-DataCloudJobState {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Context,
        [Parameter(Mandatory = $true)]
        [string]$JobId,
        [int]$PollSeconds = 15,
        [int]$TimeoutSeconds = 900
    )

    $deadline = (Get-Date).ToUniversalTime().AddSeconds($TimeoutSeconds)
    do {
        $job = Invoke-DataCloudJsonRequest -Context $Context -Method Get -RelativePath ('/api/v1/ingest/jobs/{0}' -f $JobId)
        if (@('JobComplete', 'Failed', 'Aborted') -contains $job.state) {
            return $job
        }

        Start-Sleep -Seconds $PollSeconds
    } while ((Get-Date).ToUniversalTime() -lt $deadline)

    throw "Timed out waiting for Data Cloud job '$JobId' to reach a terminal state."
}
