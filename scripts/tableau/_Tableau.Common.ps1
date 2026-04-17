Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\CommandCenter.Common.ps1')

function Get-TableauRegistry {
    $registryPath = Resolve-CommandCenterPath 'notes/registries/tableau-targets.json'
    $registry = Read-JsonFile -Path $registryPath
    if (-not $registry) {
        $registry = [pscustomobject]@{
            defaultTargetKey = ''
            targets = @()
        }
    }

    return $registry
}

function Save-TableauRegistry {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Registry
    )

    $registryPath = Resolve-CommandCenterPath 'notes/registries/tableau-targets.json'
    Write-JsonFile -Path $registryPath -Value $Registry
}

function Get-TableauTargetConfiguration {
    param(
        [string]$TargetKey
    )

    Import-CommandCenterEnv

    $registry = Get-TableauRegistry
    if (-not $TargetKey) {
        $TargetKey = if ($env:TABLEAU_DEFAULT_TARGET) { $env:TABLEAU_DEFAULT_TARGET } else { $registry.defaultTargetKey }
    }

    $target = $null
    if ($TargetKey) {
        $target = @($registry.targets | Where-Object { $_.key -eq $TargetKey }) | Select-Object -First 1
    }

    $serverUrl = if ($env:TABLEAU_SERVER_URL) { $env:TABLEAU_SERVER_URL } elseif ($target) { $target.serverUrl } else { '' }
    $siteContentUrl = if ($env:TABLEAU_SITE_CONTENT_URL) { $env:TABLEAU_SITE_CONTENT_URL } elseif ($target) { $target.siteContentUrl } else { '' }
    $defaultProjectId = if ($env:TABLEAU_DEFAULT_PROJECT_ID) { $env:TABLEAU_DEFAULT_PROJECT_ID } elseif ($target) { $target.defaultProjectId } else { '' }
    $apiVersion = if ($env:TABLEAU_API_VERSION) { $env:TABLEAU_API_VERSION } else { '3.24' }

    if (-not $serverUrl) {
        throw 'Set TABLEAU_SERVER_URL in .env.local or define a tracked target in notes/registries/tableau-targets.json.'
    }

    if (-not $siteContentUrl) {
        throw 'Set TABLEAU_SITE_CONTENT_URL in .env.local or define a tracked target in notes/registries/tableau-targets.json.'
    }

    if (-not $env:TABLEAU_PAT_NAME -or -not $env:TABLEAU_PAT_SECRET) {
        throw 'Set TABLEAU_PAT_NAME and TABLEAU_PAT_SECRET in .env.local or user environment variables.'
    }

    return [pscustomobject]@{
        TargetKey = $TargetKey
        ServerUrl = $serverUrl.TrimEnd('/')
        SiteContentUrl = $siteContentUrl
        DefaultProjectId = $defaultProjectId
        ApiVersion = $apiVersion
        PatName = $env:TABLEAU_PAT_NAME
        PatSecret = $env:TABLEAU_PAT_SECRET
        Target = $target
        Registry = $registry
    }
}

function Invoke-TableauSession {
    param(
        [string]$TargetKey,
        [Parameter(Mandatory = $true)]
        [scriptblock]$ScriptBlock
    )

    $config = Get-TableauTargetConfiguration -TargetKey $TargetKey
    $signinUri = '{0}/api/{1}/auth/signin' -f $config.ServerUrl, $config.ApiVersion
    $body = @{
        credentials = @{
            personalAccessTokenName = $config.PatName
            personalAccessTokenSecret = $config.PatSecret
            site = @{
                contentUrl = $config.SiteContentUrl
            }
        }
    } | ConvertTo-Json -Depth 10

    $signinResponse = Invoke-RestMethod -Method Post -Uri $signinUri -Headers @{ Accept = 'application/json' } -ContentType 'application/json' -Body $body
    $context = [pscustomobject]@{
        Config = $config
        AuthToken = $signinResponse.credentials.token
        SiteId = $signinResponse.credentials.site.id
        UserId = $signinResponse.credentials.user.id
    }

    try {
        & $ScriptBlock $context
    } finally {
        $signoutUri = '{0}/api/{1}/auth/signout' -f $config.ServerUrl, $config.ApiVersion
        Invoke-RestMethod -Method Post -Uri $signoutUri -Headers @{ 'X-Tableau-Auth' = $context.AuthToken } | Out-Null
    }
}

function Invoke-TableauApi {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Context,
        [Parameter(Mandatory = $true)]
        [string]$Method,
        [Parameter(Mandatory = $true)]
        [string]$RelativePath,
        [object]$Body
    )

    $uri = '{0}/api/{1}{2}' -f $Context.Config.ServerUrl, $Context.Config.ApiVersion, $RelativePath
    $parameters = @{
        Method = $Method
        Uri = $uri
        Headers = @{
            'X-Tableau-Auth' = $Context.AuthToken
            Accept = 'application/json'
        }
    }

    if ($Body) {
        $parameters.ContentType = 'application/json'
        $parameters.Body = ($Body | ConvertTo-Json -Depth 20)
    }

    return Invoke-RestMethod @parameters
}
