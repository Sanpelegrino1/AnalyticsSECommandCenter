[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DatasetPath,
    [string]$OrgAlias,
    [switch]$SkipUpload,
    [switch]$NonInteractive
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$env:SF_SKIP_NEW_VERSION_CHECK = 'true'

. (Join-Path $PSScriptRoot 'common\CommandCenter.Common.ps1')
. (Join-Path $PSScriptRoot 'salesforce\DataCloud.Common.ps1')

$script:PhaseLog = New-Object System.Collections.Generic.List[object]
$script:Blockers = New-Object System.Collections.Generic.List[object]
$script:OverallStart = [DateTime]::UtcNow

function Write-Phase {
    param([string]$Name, [string]$Message)
    Write-Host ("[{0}] {1}" -f $Name, $Message) -ForegroundColor Cyan
}

function Write-PhaseOk {
    param([string]$Name, [string]$Message, [double]$ElapsedSec)
    Write-Host ("[{0}] OK ({1:N1}s) {2}" -f $Name, $ElapsedSec, $Message) -ForegroundColor Green
    $script:PhaseLog.Add([ordered]@{ name = $Name; status = 'ok'; message = $Message; elapsedSec = [math]::Round($ElapsedSec, 2) }) | Out-Null
}

function Write-PhaseSkip {
    param([string]$Name, [string]$Message)
    Write-Host ("[{0}] skip {1}" -f $Name, $Message) -ForegroundColor DarkGray
    $script:PhaseLog.Add([ordered]@{ name = $Name; status = 'skipped'; message = $Message; elapsedSec = 0 }) | Out-Null
}

function Add-Blocker {
    param([string]$Name, [string]$Message, [string]$Action)
    $script:Blockers.Add([ordered]@{ phase = $Name; message = $Message; suggestedAction = $Action }) | Out-Null
    Write-Host ("[{0}] BLOCKED: {1}" -f $Name, $Message) -ForegroundColor Red
    if ($Action) { Write-Host ("           next: {0}" -f $Action) -ForegroundColor Yellow }
}

function Measure-Phase {
    param([string]$Name, [scriptblock]$Block)
    Write-Phase -Name $Name -Message 'start'
    $start = [DateTime]::UtcNow
    try {
        $result = & $Block
        $elapsed = ([DateTime]::UtcNow - $start).TotalSeconds
        $message = if ($result -is [string]) { $result } else { 'done' }
        Write-PhaseOk -Name $Name -Message $message -ElapsedSec $elapsed
        return $result
    } catch {
        $elapsed = ([DateTime]::UtcNow - $start).TotalSeconds
        $script:PhaseLog.Add([ordered]@{ name = $Name; status = 'failed'; message = $_.Exception.Message; elapsedSec = [math]::Round($elapsed, 2) }) | Out-Null
        throw
    }
}

function New-KebabSlug {
    param([string]$Value, [int]$MaxLength = 60)
    $normalized = ($Value -replace '[^A-Za-z0-9]+', '-').Trim('-').ToLowerInvariant()
    if ($normalized.Length -gt $MaxLength) { $normalized = $normalized.Substring(0, $MaxLength).TrimEnd('-') }
    return $normalized
}

function New-ShortSlug {
    param([string]$Value, [int]$MaxLength = 12)
    $words = ($Value -split '[^A-Za-z0-9]+') | Where-Object { $_ }
    if ($words.Count -ge 2) {
        $initials = (($words | ForEach-Object { $_.Substring(0, 1) }) -join '').ToLowerInvariant()
        if ($initials.Length -le $MaxLength -and $initials.Length -ge 2) { return $initials }
    }
    $compact = ($Value -replace '[^A-Za-z0-9]+', '_').Trim('_').ToLowerInvariant()
    if ($compact.Length -gt $MaxLength) { $compact = $compact.Substring(0, $MaxLength).TrimEnd('_') }
    return $compact
}

function New-PascalName {
    param([string]$Value, [string]$Separator = '')
    $words = ($Value -split '[^A-Za-z0-9]+') | Where-Object { $_ }
    $parts = foreach ($w in $words) {
        if ($w.Length -eq 1) { $w.ToUpperInvariant() } else { $w.Substring(0, 1).ToUpperInvariant() + $w.Substring(1) }
    }
    return ($parts -join $Separator)
}

function Read-ManifestFromPath {
    param([string]$Path)
    if (-not (Test-Path $Path)) { throw "Manifest not found at '$Path'." }
    return Get-Content -Path $Path -Raw | ConvertFrom-Json
}

function Resolve-DatasetInputs {
    param([string]$DirPath)

    $resolved = (Resolve-Path $DirPath).Path
    if (-not (Test-Path $resolved -PathType Container)) { throw "Dataset path '$resolved' is not a directory." }

    $manifestPath = Join-Path $resolved 'manifest.json'
    if (-not (Test-Path $manifestPath)) { throw "No manifest.json in '$resolved'." }
    $manifest = Read-ManifestFromPath -Path $manifestPath

    $datasetName = $manifest.datasetName
    if ([string]::IsNullOrWhiteSpace($datasetName)) { $datasetName = Split-Path -Leaf $resolved }

    $tables = @()
    if ($manifest.PSObject.Properties.Name -contains 'tables' -and $null -ne $manifest.tables) {
        foreach ($t in @($manifest.tables)) {
            $tableName = [string]$t.tableName
            $fileName = if ($t.PSObject.Properties.Name -contains 'fileName' -and $t.fileName) { [string]$t.fileName } else { "$tableName.csv" }
            $csvPath = Join-Path $resolved $fileName
            if (-not (Test-Path $csvPath)) { throw "Manifest table '$tableName' references '$fileName' but it was not found in '$resolved'." }
            $tables += [pscustomobject]@{ tableName = $tableName; fileName = $fileName; csvPath = $csvPath }
        }
    }

    if ($tables.Count -eq 0) { throw "Manifest has no tables. Older-schema manifests are not supported by this script." }

    return [pscustomobject]@{
        DirPath = $resolved
        ManifestPath = $manifestPath
        Manifest = $manifest
        DatasetName = $datasetName
        Tables = $tables
    }
}

function Get-DerivedNames {
    param([string]$DatasetName)
    $pascal = New-PascalName -Value $DatasetName
    $pascalUnder = New-PascalName -Value $DatasetName -Separator '_'
    $short = New-ShortSlug -Value $DatasetName -MaxLength 12
    $kebab = New-KebabSlug -Value $DatasetName -MaxLength 60
    return [pscustomobject]@{
        DatasetKey = $kebab
        SourceName = ($short + '_ingest_api')
        TargetKeyPrefix = $short
        ObjectNamePrefix = $short
        ModelApiName = ($pascal + '_Semantic')
        ModelLabel = $DatasetName
        WorkspaceDeveloperName = $pascalUnder
        WorkspaceLabel = $DatasetName
        TableauNextTargetKey = ($short + '-sdm')
    }
}

function Read-OrgRegistry {
    $path = Resolve-CommandCenterPath 'notes/registries/salesforce-orgs.json'
    return Read-JsonFile -Path $path
}

function Select-Org {
    param([string]$ExplicitAlias, [bool]$NonInteractive)
    if (-not [string]::IsNullOrWhiteSpace($ExplicitAlias)) { return $ExplicitAlias }
    if ($NonInteractive) { throw 'Provide -OrgAlias when running -NonInteractive.' }

    $registry = Read-OrgRegistry
    $aliases = @()
    if ($null -ne $registry -and $registry.orgs) {
        $aliases = @($registry.orgs | ForEach-Object { [string]$_.alias } | Where-Object { $_ } | Sort-Object -Unique)
    }

    Write-Host ''
    Write-Host 'Select a Salesforce org:' -ForegroundColor Cyan
    for ($i = 0; $i -lt $aliases.Count; $i++) {
        $row = $registry.orgs | Where-Object { [string]$_.alias -eq $aliases[$i] } | Select-Object -First 1
        $loginUrl = if ($row -and $row.PSObject.Properties.Name -contains 'loginUrl') { [string]$row.loginUrl } else { '' }
        Write-Host (' {0,2}. {1}  {2}' -f ($i + 1), $aliases[$i], $loginUrl)
    }
    Write-Host (' {0,2}. Add a new org (opens browser login)' -f ($aliases.Count + 1))

    $choice = Read-Host 'Pick a number'
    $index = 0
    if (-not [int]::TryParse($choice, [ref]$index)) { throw 'Invalid selection.' }
    if ($index -lt 1 -or $index -gt ($aliases.Count + 1)) { throw 'Selection out of range.' }

    if ($index -le $aliases.Count) { return $aliases[$index - 1] }

    $newAlias = (Read-Host 'New org alias (e.g. MY_ORG)').Trim()
    if ([string]::IsNullOrWhiteSpace($newAlias)) { throw 'Alias cannot be empty.' }
    $newInstance = (Read-Host 'Org instance URL (e.g. https://yourdomain.my.salesforce.com)').Trim()
    if ([string]::IsNullOrWhiteSpace($newInstance)) { throw 'Instance URL cannot be empty.' }

    $loginScript = Join-Path $PSScriptRoot 'salesforce\login-web.ps1'
    & $loginScript -Alias $newAlias -InstanceUrl $newInstance -SetDefault
    if ($LASTEXITCODE -ne 0) { throw "Browser login failed for alias '$newAlias'." }
    return $newAlias
}

function Get-SfOrgInfo {
    param([string]$Alias)
    $raw = & sf org display --target-org $Alias --json 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($raw)) {
        throw "Salesforce CLI has no session for alias '$Alias'. Run scripts\salesforce\login-web.ps1 -Alias $Alias -InstanceUrl <url>."
    }
    return ($raw | ConvertFrom-Json).result
}

function Test-CommandCenterAuthInstalled {
    param([string]$Alias, [string]$ExpectedClientId)
    $query = "SELECT Id, DeveloperName FROM ExternalClientApplication WHERE DeveloperName LIKE '%CommandCenterAuth%'"
    $raw = & sf data query --target-org $Alias --query $query --use-tooling-api --json 2>$null
    if ($LASTEXITCODE -ne 0) { return $false }
    $payload = $raw | ConvertFrom-Json
    $records = @($payload.result.records)
    return ($records.Count -gt 0)
}

function Ensure-CommandCenterAuth {
    param([string]$Alias)
    $orgInfo = Get-SfOrgInfo -Alias $Alias
    $expectedClientId = ('CommandCenterAuth{0}' -f ($orgInfo.id -replace '[^A-Za-z0-9]', ''))

    if (Test-CommandCenterAuthInstalled -Alias $Alias -ExpectedClientId $expectedClientId) {
        return "CommandCenterAuth present ($expectedClientId)"
    }

    $setupScript = Join-Path $PSScriptRoot 'salesforce\setup-command-center-connected-app.ps1'
    & $setupScript -TargetOrg $Alias
    if ($LASTEXITCODE -ne 0) { throw "CommandCenterAuth deploy failed for '$Alias'." }
    return "CommandCenterAuth deployed ($expectedClientId)"
}

function Ensure-DataCloudAuth {
    param([string]$Alias, [string]$InstanceUrl)

    # Process-scoped env: force refresh-token path, do not inherit conflicting CLI-session routing
    $env:DATACLOUD_SALESFORCE_ALIAS = ''

    $orgInfo = Get-SfOrgInfo -Alias $Alias
    $clientId = ('CommandCenterAuth{0}' -f ($orgInfo.id -replace '[^A-Za-z0-9]', ''))
    $env:DATACLOUD_CLIENT_ID = $clientId
    $env:DATACLOUD_LOGIN_URL = $InstanceUrl
    $env:DATACLOUD_TOKEN_EXCHANGE_URL = ($InstanceUrl.TrimEnd('/') + '/services/a360/token')

    if ([string]::IsNullOrWhiteSpace($env:DATACLOUD_REFRESH_TOKEN)) {
        $loginScript = Join-Path $PSScriptRoot 'salesforce\data-cloud-login-web.ps1'
        & $loginScript -Alias $Alias -InstanceUrl $InstanceUrl -UseManualOAuth
        if ($LASTEXITCODE -ne 0) { throw "Data Cloud browser login failed for '$Alias'." }
        # data-cloud-login-web.ps1 writes DATACLOUD_REFRESH_TOKEN to .env.local; re-hydrate it
        Import-CommandCenterEnv -Force
        $env:DATACLOUD_SALESFORCE_ALIAS = ''  # force refresh-token path again after reload
    }

    # Verify exchange works; if invalid_scope, trigger browser and retry once
    try {
        $tenantEndpoint = Get-DataCloudTenantEndpointFromExchange
        return "tenant $tenantEndpoint"
    } catch {
        if ($_.Exception.Message -notmatch 'invalid_scope') { throw }
        $loginScript = Join-Path $PSScriptRoot 'salesforce\data-cloud-login-web.ps1'
        & $loginScript -Alias $Alias -InstanceUrl $InstanceUrl -UseManualOAuth
        if ($LASTEXITCODE -ne 0) { throw "Data Cloud browser login retry failed for '$Alias'." }
        Import-CommandCenterEnv -Force
        $env:DATACLOUD_SALESFORCE_ALIAS = ''
        $tenantEndpoint = Get-DataCloudTenantEndpointFromExchange
        return "tenant $tenantEndpoint (re-auth)"
    }
}

function Get-DataCloudTenantEndpointFromExchange {
    $tokenBody = @{
        grant_type = 'refresh_token'
        client_id = $env:DATACLOUD_CLIENT_ID
        refresh_token = $env:DATACLOUD_REFRESH_TOKEN
    }
    $tokenUrl = ('{0}/services/oauth2/token' -f $env:DATACLOUD_LOGIN_URL.TrimEnd('/'))
    $sfResp = Invoke-RestMethod -Method Post -Uri $tokenUrl -ContentType 'application/x-www-form-urlencoded' -Body (ConvertTo-FormUrlEncoded -Values $tokenBody)

    $exchangeBody = @{
        grant_type = 'urn:salesforce:grant-type:external:cdp'
        subject_token = $sfResp.access_token
        subject_token_type = 'urn:ietf:params:oauth:token-type:access_token'
    }
    $dcResp = Invoke-RestMethod -Method Post -Uri $env:DATACLOUD_TOKEN_EXCHANGE_URL -ContentType 'application/x-www-form-urlencoded' -Body (ConvertTo-FormUrlEncoded -Values $exchangeBody)
    $tenant = 'https://' + $dcResp.instance_url.TrimStart('h').TrimStart('t').TrimStart('t').TrimStart('p').TrimStart('s').TrimStart(':').TrimStart('/')
    if ($dcResp.instance_url -match '^https?://') { $tenant = $dcResp.instance_url } else { $tenant = 'https://' + $dcResp.instance_url }
    $env:DATACLOUD_TENANT_ENDPOINT = $tenant
    return $tenant
}

function Get-DataCloudConnector {
    param([string]$Alias, [string]$SourceName)
    $orgInfo = Get-SfOrgInfo -Alias $Alias
    $uri = ('{0}/services/data/v62.0/ssot/connections?connectorType=IngestApi&limit=200' -f $orgInfo.instanceUrl.TrimEnd('/'))
    $headers = @{ Authorization = 'Bearer ' + $orgInfo.accessToken }
    try {
        $resp = Invoke-RestMethod -Method Get -Uri $uri -Headers $headers
    } catch {
        return $null
    }
    if ($null -eq $resp) { return $null }
    $items = @()
    foreach ($key in 'connections', 'items', 'data') {
        if ($resp.PSObject.Properties.Name -contains $key) {
            $val = $resp.PSObject.Properties[$key].Value
            if ($null -ne $val) { $items = @($val); break }
        }
    }
    foreach ($item in $items) {
        foreach ($prop in 'name', 'connectorName', 'sourceName', 'developerName') {
            if ($item.PSObject.Properties.Name -contains $prop) {
                $v = $item.PSObject.Properties[$prop].Value
                if ([string]$v -eq $SourceName) { return $item }
            }
        }
    }
    return $null
}

function Ensure-IngestConnector {
    param([string]$Alias, [object]$DatasetInputs, [object]$Derived)

    $existing = Get-DataCloudConnector -Alias $Alias -SourceName $Derived.SourceName
    if ($null -ne $existing) { return "connector '$($Derived.SourceName)' already present" }

    $genScript = Join-Path $PSScriptRoot 'salesforce\data-cloud-generate-ingest-metadata.ps1'
    & $genScript -ManifestPath $DatasetInputs.ManifestPath -SourceName $Derived.SourceName -ObjectNamePrefix $Derived.ObjectNamePrefix -Force | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Ingest metadata generation failed.' }

    $genDir = Resolve-CommandCenterPath (Join-Path 'salesforce/generated' (New-MetadataSafeName -Value $Derived.SourceName))
    # Deploy only the DataConnectorIngestApi (empty connector shell). Schema is created later by
    # stream bootstrap via REST, which avoids the metadata-API taxonomy constraint on MktDataTranObject.
    $connectorDir = Join-Path $genDir 'dataConnectorIngestApis'
    if (-not (Test-Path $connectorDir)) { throw "Expected connector metadata at '$connectorDir' was not generated." }
    $salesforceRoot = Resolve-CommandCenterPath 'salesforce'
    Push-Location $salesforceRoot
    try {
        & sf project deploy start --target-org $Alias --source-dir $connectorDir --ignore-conflicts --wait 10 | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "Ingest connector metadata deploy failed against '$Alias'." }
    } finally { Pop-Location }

    # Poll for connector visibility (up to 90s)
    $deadline = [DateTime]::UtcNow.AddSeconds(90)
    while ([DateTime]::UtcNow -lt $deadline) {
        Start-Sleep -Seconds 5
        if ($null -ne (Get-DataCloudConnector -Alias $Alias -SourceName $Derived.SourceName)) {
            return "connector '$($Derived.SourceName)' deployed"
        }
    }
    throw "Connector '$($Derived.SourceName)' did not appear within 90s after deploy."
}

function Invoke-RegisterTargets {
    param([object]$DatasetInputs, [object]$Derived, [string]$TenantEndpoint)
    $script = Join-Path $PSScriptRoot 'salesforce\data-cloud-register-manifest-targets.ps1'
    & $script `
        -ManifestPath $DatasetInputs.ManifestPath `
        -SourceName $Derived.SourceName `
        -TargetKeyPrefix $Derived.TargetKeyPrefix `
        -ObjectNamePrefix $Derived.ObjectNamePrefix `
        -TenantEndpoint $TenantEndpoint | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Target registration failed.' }
}

function Invoke-StreamBootstrap {
    param([string]$DataCloudAlias, [object]$DatasetInputs, [object]$Derived)
    $script = Join-Path $PSScriptRoot 'salesforce\data-cloud-create-manifest-streams.ps1'
    & $script `
        -ManifestPath $DatasetInputs.ManifestPath `
        -TargetOrg $DataCloudAlias `
        -SourceName $Derived.SourceName `
        -ObjectNamePrefix $Derived.ObjectNamePrefix | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Stream bootstrap failed.' }
}

function Invoke-UploadManifest {
    param([object]$DatasetInputs, [object]$Derived)
    $script = Join-Path $PSScriptRoot 'salesforce\data-cloud-upload-manifest.ps1'
    & $script -ManifestPath $DatasetInputs.ManifestPath -TargetKeyPrefix $Derived.TargetKeyPrefix | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Upload failed.' }
}

function Ensure-TableauNextWorkspace {
    param([string]$Alias, [object]$Derived)
    $commonScript = Join-Path $PSScriptRoot 'tableau\_TableauNext.Common.ps1'
    . $commonScript
    $existing = @(Get-TableauNextWorkspaceRows -TargetOrg $Alias -Limit 2000 |
        Where-Object { [string]$_.DeveloperName -eq $Derived.WorkspaceDeveloperName } | Select-Object -First 1)
    if ($existing.Count -gt 0) { return "workspace '$($Derived.WorkspaceDeveloperName)' already present ($($existing[0].WorkspaceId))" }

    $createScript = Join-Path $PSScriptRoot 'tableau\create-next-workspace.ps1'
    & $createScript -TargetOrg $Alias -WorkspaceDeveloperName $Derived.WorkspaceDeveloperName -WorkspaceLabel $Derived.WorkspaceLabel | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Workspace creation failed. If Tableau Next is not yet provisioned on this org, run the 'org-setup-tableau-next-pace' skill first."
    }
    return "workspace '$($Derived.WorkspaceDeveloperName)' created"
}

function Upsert-TableauNextTarget {
    param([string]$Alias, [object]$Derived)
    $regPath = Resolve-CommandCenterPath 'notes/registries/tableau-next-targets.json'
    $reg = Read-JsonFile -Path $regPath
    if (-not $reg) { $reg = [pscustomobject]@{ defaultTargetKey = ''; targets = @() } }

    $commonScript = Join-Path $PSScriptRoot 'tableau\_TableauNext.Common.ps1'
    . $commonScript
    $workspace = @(Get-TableauNextWorkspaceRows -TargetOrg $Alias -Limit 2000 |
        Where-Object { [string]$_.DeveloperName -eq $Derived.WorkspaceDeveloperName } | Select-Object -First 1)
    if ($workspace.Count -eq 0) { throw "Workspace '$($Derived.WorkspaceDeveloperName)' missing after ensure-workspace phase." }

    $existing = @($reg.targets | Where-Object { [string]$_.key -eq $Derived.TableauNextTargetKey })
    $now = (Get-UtcTimestamp)

    if ($existing.Count -gt 0) {
        $existing[0] | Add-Member -NotePropertyName 'targetOrg' -NotePropertyValue $Alias -Force
        $existing[0] | Add-Member -NotePropertyName 'workspaceId' -NotePropertyValue $workspace[0].WorkspaceId -Force
        $existing[0] | Add-Member -NotePropertyName 'workspaceDeveloperName' -NotePropertyValue $workspace[0].DeveloperName -Force
        $existing[0] | Add-Member -NotePropertyName 'workspaceLabel' -NotePropertyValue $workspace[0].Label -Force
        $existing[0] | Add-Member -NotePropertyName 'updatedAt' -NotePropertyValue $now -Force
        $existing[0] | Add-Member -NotePropertyName 'lastValidatedUtc' -NotePropertyValue $now -Force
    } else {
        $newTarget = [ordered]@{
            key = $Derived.TableauNextTargetKey
            targetOrg = $Alias
            workspaceId = $workspace[0].WorkspaceId
            workspaceDeveloperName = $workspace[0].DeveloperName
            workspaceLabel = $workspace[0].Label
            purpose = "$($Derived.ModelLabel) semantic model"
            notes = ''
            createdAt = $now
            updatedAt = $now
            lastValidatedUtc = $now
        }
        $reg.targets = @($reg.targets) + [pscustomobject]$newTarget
    }

    Write-JsonFile -Path $regPath -Value $reg
    return "target '$($Derived.TableauNextTargetKey)' upserted"
}

function Invoke-BuildSpec {
    param([object]$DatasetInputs, [object]$Derived)
    $script = Join-Path $PSScriptRoot 'salesforce\build-manifest-semantic-model-spec.ps1'
    $provReport = Resolve-CommandCenterPath ('salesforce/generated/{0}/provisioning-state.json' -f (New-MetadataSafeName -Value $Derived.SourceName))
    & $script `
        -ManifestPath $DatasetInputs.ManifestPath `
        -ProvisioningReportPath $provReport `
        -TargetKey $Derived.TableauNextTargetKey `
        -TargetKeyPrefix $Derived.TargetKeyPrefix `
        -ModelApiName $Derived.ModelApiName `
        -ModelLabel $Derived.ModelLabel | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Semantic model spec build failed.' }

    $specPath = Resolve-CommandCenterPath ('tmp/{0}.semantic-model.spec.json' -f $Derived.DatasetKey)
    if (-not (Test-Path $specPath)) { throw "Spec file not found at '$specPath'." }
    return $specPath
}

function Invoke-ApplyModel {
    param([string]$Alias, [string]$SpecPath, [object]$Derived)
    # Query existing model by apiName to choose Create vs Update (sidesteps registry state drift).
    . (Join-Path $PSScriptRoot 'tableau\_TableauNext.Common.ps1')
    $ctx = Get-TableauNextAccessContext -TargetOrg $Alias
    $action = 'Create'
    $existingId = ''
    try {
        $existing = Invoke-TableauNextApi -Context $ctx -RelativePath ('ssot/semantic/models/{0}' -f $Derived.ModelApiName)
        if ($existing -and $existing.PSObject.Properties.Name -contains 'id' -and $existing.id) {
            $action = 'Update'
            $existingId = [string]$existing.id
        }
    } catch { $action = 'Create' }

    if ($action -eq 'Update' -and $existingId) {
        $regPath = Resolve-CommandCenterPath 'notes/registries/tableau-next-targets.json'
        $reg = Read-JsonFile -Path $regPath
        $target = @($reg.targets | Where-Object { [string]$_.key -eq $Derived.TableauNextTargetKey }) | Select-Object -First 1
        if ($target) {
            $target | Add-Member -NotePropertyName 'semanticModelId' -NotePropertyValue $existingId -Force
            Write-JsonFile -Path $regPath -Value $reg
        }
    }

    $script = Join-Path $PSScriptRoot 'tableau\upsert-next-semantic-model.ps1'
    # Invoke via & to avoid WhatIf propagation from any ancestor scope.
    $result = & $script -SpecPath $SpecPath -TargetKey $Derived.TableauNextTargetKey -Action $action -Apply -Json
    if ($LASTEXITCODE -ne 0) { throw 'Semantic model apply failed.' }
    return "$action $($Derived.ModelApiName)"
}

function Test-ModelValidity {
    param([string]$Alias, [object]$Derived)
    . (Join-Path $PSScriptRoot 'tableau\_TableauNext.Common.ps1')
    $ctx = Get-TableauNextAccessContext -TargetOrg $Alias
    $resp = Invoke-TableauNextApi -Context $ctx -RelativePath ('ssot/semantic/models/{0}/validate' -f $Derived.ModelApiName)
    return [bool]$resp.isValid
}

function Write-StateJson {
    param([object]$DatasetInputs, [string]$Alias, [object]$Derived, [bool]$IsValid, [string]$ModelApiName)
    $total = ([DateTime]::UtcNow - $script:OverallStart).TotalSeconds
    $state = [ordered]@{
        generatedAt = (Get-UtcTimestamp)
        datasetPath = $DatasetInputs.DirPath
        datasetName = $DatasetInputs.DatasetName
        orgAlias = $Alias
        derived = $Derived
        phases = $script:PhaseLog.ToArray()
        semanticModel = [ordered]@{ apiName = $ModelApiName; isValid = $IsValid }
        totalElapsedSec = [math]::Round($total, 2)
        blockers = $script:Blockers.ToArray()
    }
    $statePath = Resolve-CommandCenterPath ('tmp/{0}-publish-state.json' -f $Derived.DatasetKey)
    Write-JsonFile -Path $statePath -Value ([pscustomobject]$state)
    Write-Host ''
    Write-Host ('State: {0}' -f $statePath) -ForegroundColor DarkGray
}

# --- main orchestration ---

try {
    Import-CommandCenterEnv
} catch {
    # .env.local missing or empty is fine; we only need the refresh token if one is stored
}
$env:SF_SKIP_NEW_VERSION_CHECK = 'true'
$env:DATACLOUD_SALESFORCE_ALIAS = ''

$script:DatasetPathArg = $DatasetPath
Measure-Phase -Name 'loadDataset' -Block {
    $script:DatasetInputs = Resolve-DatasetInputs -DirPath $script:DatasetPathArg
    "'$($script:DatasetInputs.DatasetName)' ($($script:DatasetInputs.Tables.Count) tables)"
} | Out-Null
$datasetInputs = $script:DatasetInputs

Measure-Phase -Name 'deriveNames' -Block {
    $script:Derived = Get-DerivedNames -DatasetName $script:DatasetInputs.DatasetName
    "prefix=$($script:Derived.TargetKeyPrefix) source=$($script:Derived.SourceName) model=$($script:Derived.ModelApiName) workspace=$($script:Derived.WorkspaceDeveloperName)"
} | Out-Null
$derived = $script:Derived

Write-Host ''
Write-Host 'Publishing plan:' -ForegroundColor Cyan
Write-Host ("  dataset        : {0}" -f $datasetInputs.DatasetName)
Write-Host ("  tables         : {0}" -f (($datasetInputs.Tables | ForEach-Object { $_.tableName }) -join ', '))
Write-Host ("  source         : {0}" -f $derived.SourceName)
Write-Host ("  target prefix  : {0}" -f $derived.TargetKeyPrefix)
Write-Host ("  model          : {0}  [{1}]" -f $derived.ModelApiName, $derived.ModelLabel)
Write-Host ("  workspace      : {0}" -f $derived.WorkspaceDeveloperName)
Write-Host ''

if (-not $NonInteractive) {
    $confirm = Read-Host 'Proceed? [Y/n]'
    if (-not [string]::IsNullOrWhiteSpace($confirm) -and $confirm -notmatch '^(y|Y)') {
        Write-Host 'Aborted.' -ForegroundColor Yellow
        exit 2
    }
}

$script:OrgAliasArg = $OrgAlias
$script:NonInteractiveArg = $NonInteractive.IsPresent
Measure-Phase -Name 'selectOrg' -Block {
    $script:Alias = Select-Org -ExplicitAlias $script:OrgAliasArg -NonInteractive $script:NonInteractiveArg
    "alias=$($script:Alias)"
} | Out-Null
$alias = $script:Alias

Measure-Phase -Name 'verifyCliSession' -Block {
    $script:OrgInfo = Get-SfOrgInfo -Alias $script:Alias
    "instance=$($script:OrgInfo.instanceUrl)"
} | Out-Null
$orgInfo = $script:OrgInfo

Measure-Phase -Name 'commandCenterAuth' -Block { Ensure-CommandCenterAuth -Alias $script:Alias } | Out-Null

Measure-Phase -Name 'dataCloudAuth' -Block {
    $t = Ensure-DataCloudAuth -Alias $script:Alias -InstanceUrl $script:OrgInfo.instanceUrl
    $script:TenantEndpoint = $env:DATACLOUD_TENANT_ENDPOINT
    $t
} | Out-Null
$tenantEndpoint = $script:TenantEndpoint

Measure-Phase -Name 'ingestConnector' -Block {
    Ensure-IngestConnector -Alias $script:Alias -DatasetInputs $script:DatasetInputs -Derived $script:Derived
} | Out-Null

Measure-Phase -Name 'registerTargets' -Block {
    Invoke-RegisterTargets -DatasetInputs $script:DatasetInputs -Derived $script:Derived -TenantEndpoint $script:TenantEndpoint
    'targets registered'
} | Out-Null

Measure-Phase -Name 'streamBootstrap' -Block {
    Invoke-StreamBootstrap -DataCloudAlias $script:Alias -DatasetInputs $script:DatasetInputs -Derived $script:Derived
    'streams active'
} | Out-Null

Measure-Phase -Name 'reregisterTargets' -Block {
    Invoke-RegisterTargets -DatasetInputs $script:DatasetInputs -Derived $script:Derived -TenantEndpoint $script:TenantEndpoint
    'targets aligned with live streams'
} | Out-Null

if ($SkipUpload) {
    Write-PhaseSkip -Name 'upload' -Message 'skipped (-SkipUpload)'
} else {
    Measure-Phase -Name 'upload' -Block {
        Invoke-UploadManifest -DatasetInputs $script:DatasetInputs -Derived $script:Derived
        'uploaded'
    } | Out-Null
}

Measure-Phase -Name 'workspace' -Block { Ensure-TableauNextWorkspace -Alias $script:Alias -Derived $script:Derived } | Out-Null

Measure-Phase -Name 'tableauNextTarget' -Block { Upsert-TableauNextTarget -Alias $script:Alias -Derived $script:Derived } | Out-Null

Measure-Phase -Name 'buildSpec' -Block {
    $script:SpecPath = Invoke-BuildSpec -DatasetInputs $script:DatasetInputs -Derived $script:Derived
    "spec=$($script:SpecPath)"
} | Out-Null
$specPath = $script:SpecPath

Measure-Phase -Name 'applyModel' -Block { Invoke-ApplyModel -Alias $script:Alias -SpecPath $script:SpecPath -Derived $script:Derived } | Out-Null

Measure-Phase -Name 'validate' -Block {
    $script:IsValid = Test-ModelValidity -Alias $script:Alias -Derived $script:Derived
    "isValid=$($script:IsValid)"
} | Out-Null
$isValid = $script:IsValid

Write-StateJson -DatasetInputs $datasetInputs -Alias $alias -Derived $derived -IsValid $isValid -ModelApiName $derived.ModelApiName

$totalSec = ([DateTime]::UtcNow - $script:OverallStart).TotalSeconds
if ($isValid) {
    Write-Host ''
    Write-Host ("Done. Model '{0}' is valid. ({1:N1}s total)" -f $derived.ModelApiName, $totalSec) -ForegroundColor Green
    exit 0
} else {
    Write-Host ''
    Write-Host ("Model '{0}' applied but failed validation. See state JSON." -f $derived.ModelApiName) -ForegroundColor Yellow
    exit 3
}
