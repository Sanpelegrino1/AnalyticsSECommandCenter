Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\salesforce\DataCloud.Common.ps1')

if (-not (Get-Variable -Name 'TableauNextDescribeCache' -Scope Script -ErrorAction SilentlyContinue)) {
    $script:TableauNextDescribeCache = @{}
}

function Get-TableauNextRegistryPath {
    return Resolve-CommandCenterPath 'notes/registries/tableau-next-targets.json'
}

function Get-TableauNextRegistry {
    $registry = Read-JsonFile -Path (Get-TableauNextRegistryPath)
    if (-not $registry) {
        $registry = [pscustomobject]@{
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

function Save-TableauNextRegistry {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Registry
    )

    Write-JsonFile -Path (Get-TableauNextRegistryPath) -Value $Registry
}

function Get-TableauNextTargetPropertyValue {
    param(
        [object]$Target,
        [Parameter(Mandatory = $true)]
        [string]$PropertyName
    )

    if ($null -eq $Target) {
        return ''
    }

    $property = $Target.PSObject.Properties[$PropertyName]
    if ($null -eq $property -or $null -eq $property.Value) {
        return ''
    }

    return [string]$property.Value
}

function Get-TableauNextTargetConfiguration {
    param(
        [string]$TargetKey
    )

    Import-CommandCenterEnv

    $registry = Get-TableauNextRegistry
    $resolvedTargetKey = $TargetKey
    if ([string]::IsNullOrWhiteSpace($resolvedTargetKey)) {
        if (-not [string]::IsNullOrWhiteSpace($env:TABLEAU_NEXT_DEFAULT_TARGET)) {
            $resolvedTargetKey = $env:TABLEAU_NEXT_DEFAULT_TARGET
        } else {
            $resolvedTargetKey = $registry.defaultTargetKey
        }
    }

    if ([string]::IsNullOrWhiteSpace($resolvedTargetKey)) {
        throw 'Provide -TargetKey, set TABLEAU_NEXT_DEFAULT_TARGET locally, or define defaultTargetKey in notes/registries/tableau-next-targets.json.'
    }

    $target = @($registry.targets | Where-Object { $_.key -eq $resolvedTargetKey } | Select-Object -First 1)
    if ($target.Count -eq 0) {
        throw "Tableau Next target '$resolvedTargetKey' was not found in notes/registries/tableau-next-targets.json."
    }

    $target = $target[0]
    if ([string]::IsNullOrWhiteSpace([string]$target.targetOrg)) {
        throw "Tableau Next target '$resolvedTargetKey' is missing targetOrg. Re-register it from live discovery output."
    }

    if ([string]::IsNullOrWhiteSpace([string]$target.workspaceId)) {
        throw "Tableau Next target '$resolvedTargetKey' is missing workspaceId. Re-register it from live discovery output."
    }

    return [pscustomobject]@{
        TargetKey = $resolvedTargetKey
        TargetOrg = Get-TableauNextTargetPropertyValue -Target $target -PropertyName 'targetOrg'
        WorkspaceId = Get-TableauNextTargetPropertyValue -Target $target -PropertyName 'workspaceId'
        WorkspaceDeveloperName = Get-TableauNextTargetPropertyValue -Target $target -PropertyName 'workspaceDeveloperName'
        WorkspaceLabel = Get-TableauNextTargetPropertyValue -Target $target -PropertyName 'workspaceLabel'
        SemanticModelId = Get-TableauNextTargetPropertyValue -Target $target -PropertyName 'semanticModelId'
        WorkspaceAssetId = Get-TableauNextTargetPropertyValue -Target $target -PropertyName 'workspaceAssetId'
        AssetUsageType = Get-TableauNextTargetPropertyValue -Target $target -PropertyName 'assetUsageType'
        Target = $target
        Registry = $registry
    }
}

function Resolve-TableauNextTargetOrg {
    param(
        [string]$TargetOrg
    )

    Import-CommandCenterEnv

    if (-not [string]::IsNullOrWhiteSpace($TargetOrg)) {
        return $TargetOrg
    }

    if (-not [string]::IsNullOrWhiteSpace($env:SF_DEFAULT_ALIAS)) {
        return $env:SF_DEFAULT_ALIAS
    }

    throw 'Provide -TargetOrg or set SF_DEFAULT_ALIAS in .env.local.'
}

function Get-TableauNextAccessContext {
    param(
        [string]$TargetOrg,
        [string]$ApiVersion = 'v66.0'
    )

    $resolvedTargetOrg = Resolve-TableauNextTargetOrg -TargetOrg $TargetOrg
    $orgContext = Get-SalesforceOrgAccessContext -Alias $resolvedTargetOrg

    return [pscustomobject]@{
        TargetOrg = $resolvedTargetOrg
        ApiVersion = $ApiVersion
        AccessToken = $orgContext.accessToken
        InstanceUrl = $orgContext.instanceUrl
        AuthSource = $orgContext.source
    }
}

function Invoke-TableauNextApi {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Context,
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    return Invoke-TableauNextApiRequest -Context $Context -Method Get -RelativePath $RelativePath
}

function Invoke-TableauNextApiRequest {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Context,
        [Parameter(Mandatory = $true)]
        [ValidateSet('Get', 'Post', 'Put', 'Patch', 'Delete')]
        [string]$Method,
        [Parameter(Mandatory = $true)]
        [string]$RelativePath,
        [object]$Body,
        [hashtable]$AdditionalHeaders
    )

    $headers = @{
        Authorization = 'Bearer {0}' -f $Context.AccessToken
    }

    if ($null -ne $AdditionalHeaders) {
        foreach ($key in @($AdditionalHeaders.Keys)) {
            $headers[$key] = $AdditionalHeaders[$key]
        }
    }

    $invokeParams = @{
        Method = $Method
        Uri = ('{0}/services/data/{1}/{2}' -f $Context.InstanceUrl, $Context.ApiVersion, $RelativePath.TrimStart('/'))
        Headers = $headers
    }

    if ($PSBoundParameters.ContainsKey('Body') -and $null -ne $Body) {
        $invokeParams.ContentType = 'application/json'
        $invokeParams.Body = ($Body | ConvertTo-Json -Depth 100)
    }

    return Invoke-RestMethod @invokeParams
}

function Get-TableauNextGeneratedXmlNodeInnerText {
    param(
        [Parameter(Mandatory = $true)]
        [xml]$XmlDocument,
        [Parameter(Mandatory = $true)]
        [string]$XPath
    )

    $node = $XmlDocument.SelectSingleNode($XPath)
    if ($null -eq $node) {
        return ''
    }

    return [string]$node.InnerText
}

function Get-TableauNextGeneratedObjectDescribe {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ObjectName
    )

    $generatedRoot = Resolve-CommandCenterPath 'salesforce/generated'
    if (-not (Test-Path -LiteralPath $generatedRoot)) {
        return $null
    }

    $candidateDirectoryNames = New-Object System.Collections.Generic.List[string]
    $candidateDirectoryNames.Add($ObjectName) | Out-Null
    if (-not $ObjectName.EndsWith('__dll')) {
        $candidateDirectoryNames.Add(('{0}__dll' -f $ObjectName)) | Out-Null
    }
    if ($ObjectName.Contains('_')) {
        $strippedObjectName = $ObjectName.Substring($ObjectName.IndexOf('_') + 1)
        if (-not [string]::IsNullOrWhiteSpace($strippedObjectName)) {
            $candidateDirectoryNames.Add($strippedObjectName) | Out-Null
            if (-not $strippedObjectName.EndsWith('__dll')) {
                $candidateDirectoryNames.Add(('{0}__dll' -f $strippedObjectName)) | Out-Null
            }
        }
    }

    foreach ($candidateDirectoryName in @($candidateDirectoryNames | Select-Object -Unique)) {
        $objectDirectory = @(
            Get-ChildItem -LiteralPath $generatedRoot -Directory -Recurse -Filter $candidateDirectoryName |
                Where-Object { $_.Parent -and $_.Parent.Name -eq 'objects' } |
                Select-Object -First 1
        )
        if ($objectDirectory.Count -eq 0) {
            continue
        }

        $fieldsDirectory = Join-Path $objectDirectory[0].FullName 'fields'
        if (-not (Test-Path -LiteralPath $fieldsDirectory)) {
            continue
        }

        $fieldFiles = @(Get-ChildItem -LiteralPath $fieldsDirectory -File -Filter '*.field-meta.xml' | Sort-Object Name)
        if ($fieldFiles.Count -eq 0) {
            continue
        }

        $fields = @(
            foreach ($fieldFile in $fieldFiles) {
                $fieldXml = [xml](Get-Content -LiteralPath $fieldFile.FullName -Raw)
                $fullName = Get-TableauNextGeneratedXmlNodeInnerText -XmlDocument $fieldXml -XPath "/*[local-name()='CustomField']/*[local-name()='fullName']"
                if ([string]::IsNullOrWhiteSpace($fullName)) {
                    continue
                }

                $label = Get-TableauNextGeneratedXmlNodeInnerText -XmlDocument $fieldXml -XPath "/*[local-name()='CustomField']/*[local-name()='label']"
                $type = Get-TableauNextGeneratedXmlNodeInnerText -XmlDocument $fieldXml -XPath "/*[local-name()='CustomField']/*[local-name()='type']"
                $scale = Get-TableauNextGeneratedXmlNodeInnerText -XmlDocument $fieldXml -XPath "/*[local-name()='CustomField']/*[local-name()='scale']"
                $primaryIndexOrder = Get-TableauNextGeneratedXmlNodeInnerText -XmlDocument $fieldXml -XPath "/*[local-name()='CustomField']/*[local-name()='mktDataLakeFieldAttributes']/*[local-name()='primaryIndexOrder']"

                [pscustomobject]@{
                    name = $fullName
                    label = $(if (-not [string]::IsNullOrWhiteSpace($label)) { $label } else { $fullName })
                    type = $type
                    scale = $(if ([string]::IsNullOrWhiteSpace($scale)) { $null } else { [int]$scale })
                    isPrimaryKey = (-not [string]::IsNullOrWhiteSpace($primaryIndexOrder) -and $primaryIndexOrder -ne '0')
                }
            }
        )
        if ($fields.Count -eq 0) {
            continue
        }

        return [pscustomobject]@{
            name = $(if ($candidateDirectoryName.EndsWith('__dll')) { $candidateDirectoryName } else { '{0}__dll' -f $candidateDirectoryName })
            fields = $fields
        }
    }

    return $null
}

function Get-TableauNextObjectDescribe {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Context,
        [Parameter(Mandatory = $true)]
        [string]$ObjectName
    )

    $cacheKey = '{0}:{1}:{2}' -f $Context.InstanceUrl, $Context.ApiVersion, $ObjectName
    if ($script:TableauNextDescribeCache.ContainsKey($cacheKey)) {
        return $script:TableauNextDescribeCache[$cacheKey]
    }

    $candidateNames = New-Object System.Collections.Generic.List[string]
    $candidateNames.Add($ObjectName) | Out-Null
    if (-not $ObjectName.EndsWith('__dll')) {
        $candidateNames.Add(('{0}__dll' -f $ObjectName)) | Out-Null
    }
    if (-not $ObjectName.EndsWith('__dlm')) {
        $candidateNames.Add(('{0}__dlm' -f $ObjectName)) | Out-Null
    }

    $lastError = $null
    foreach ($candidateName in @($candidateNames | Select-Object -Unique)) {
        try {
            $describe = Invoke-TableauNextApi -Context $Context -RelativePath ('sobjects/{0}/describe' -f $candidateName)
            $script:TableauNextDescribeCache[$cacheKey] = $describe
            return $describe
        } catch {
            $lastError = $_
        }
    }

    $generatedDescribe = Get-TableauNextGeneratedObjectDescribe -ObjectName $ObjectName
    if ($null -ne $generatedDescribe) {
        $script:TableauNextDescribeCache[$cacheKey] = $generatedDescribe
        return $generatedDescribe
    }

    if ($null -ne $lastError) {
        throw $lastError
    }

    $script:TableauNextDescribeCache[$cacheKey] = $describe
    return $describe
}

function Get-TableauNextSelectableFields {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Context,
        [Parameter(Mandatory = $true)]
        [string]$ObjectName,
        [Parameter(Mandatory = $true)]
        [string[]]$PreferredFields,
        [string[]]$RequiredFields = @('Id')
    )

    $describe = Get-TableauNextObjectDescribe -Context $Context -ObjectName $ObjectName
    $availableFields = @{}
    foreach ($field in $describe.fields) {
        $availableFields[$field.name] = $true
    }

    $selectedFields = New-Object System.Collections.Generic.List[string]
    foreach ($fieldName in $PreferredFields) {
        if ($availableFields.ContainsKey($fieldName)) {
            $selectedFields.Add($fieldName)
        }
    }

    foreach ($fieldName in $RequiredFields) {
        if ($availableFields.ContainsKey($fieldName) -and -not $selectedFields.Contains($fieldName)) {
            $selectedFields.Insert(0, $fieldName)
        }
    }

    if ($selectedFields.Count -eq 0) {
        throw "No requested fields were available on '$ObjectName'."
    }

    return @($selectedFields)
}

function Get-TableauNextSemanticModelDefinition {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetOrg,
        [Parameter(Mandatory = $true)]
        [string]$SemanticModelIdOrApiName,
        [string]$ApiVersion = 'v66.0'
    )

    $context = Get-TableauNextAccessContext -TargetOrg $TargetOrg -ApiVersion $ApiVersion
    return Invoke-TableauNextApi -Context $context -RelativePath ('ssot/semantic/models/{0}' -f $SemanticModelIdOrApiName)
}

function Invoke-TableauNextQuery {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetOrg,
        [string]$Query
    )

    $sfCommand = Get-RequiredCommandPath -Name 'sf' -Hint 'Install Salesforce CLI or run the bootstrap script.'
    $response = & $sfCommand data query --target-org $TargetOrg --query $Query --json | ConvertFrom-Json
    if ($null -eq $response) {
        throw 'Salesforce CLI returned no response for Tableau Next query.'
    }

    if ($response.PSObject.Properties.Name -contains 'status' -and [int]$response.status -ne 0) {
        $message = if ($response.PSObject.Properties.Name -contains 'message' -and -not [string]::IsNullOrWhiteSpace([string]$response.message)) {
            [string]$response.message
        } else {
            'Salesforce CLI query failed.'
        }

        throw $message
    }

    if (-not ($response.PSObject.Properties.Name -contains 'result') -or $null -eq $response.result) {
        throw 'Salesforce CLI query response did not include a result payload.'
    }

    return @($response.result.records | Select-Object -ExcludeProperty attributes)
}

function Get-TableauNextWorkspaceRows {
    param(
        [string]$TargetOrg,
        [int]$Limit = 200
    )

    $context = Get-TableauNextAccessContext -TargetOrg $TargetOrg
    $safeLimit = [Math]::Max(1, $Limit)
    $fields = Get-TableauNextSelectableFields -Context $context -ObjectName 'AnalyticsWorkspace' -PreferredFields @(
        'Id',
        'DeveloperName',
        'MasterLabel',
        'Language',
        'Description',
        'CreatedDate',
        'LastModifiedDate'
    )

    $query = 'SELECT {0} FROM AnalyticsWorkspace ORDER BY LastModifiedDate DESC LIMIT {1}' -f ($fields -join ', '), $safeLimit
    $records = Invoke-TableauNextQuery -TargetOrg $context.TargetOrg -Query $query

    return @(
        foreach ($record in $records) {
            [pscustomobject]@{
                WorkspaceId = Get-TableauNextRecordFieldValue -Record $record -FieldName 'Id'
                DeveloperName = Get-TableauNextRecordFieldValue -Record $record -FieldName 'DeveloperName'
                Label = Get-TableauNextRecordFieldValue -Record $record -FieldName 'MasterLabel'
                Language = Get-TableauNextRecordFieldValue -Record $record -FieldName 'Language'
                Description = Get-TableauNextRecordFieldValue -Record $record -FieldName 'Description'
                CreatedDate = Get-TableauNextRecordFieldValue -Record $record -FieldName 'CreatedDate'
                LastModifiedDate = Get-TableauNextRecordFieldValue -Record $record -FieldName 'LastModifiedDate'
            }
        }
    )
}

function Resolve-TableauNextWorkspaceSelection {
    param(
        [string]$TargetOrg,
        [string]$WorkspaceId,
        [string]$WorkspaceDeveloperName,
        [string]$WorkspaceLabel,
        [switch]$AutoSelectSingleWorkspace
    )

    $workspaceRows = @(Get-TableauNextWorkspaceRows -TargetOrg $TargetOrg -Limit 2000)
    $candidates = @($workspaceRows)

    if (-not [string]::IsNullOrWhiteSpace($WorkspaceId)) {
        $candidates = @($candidates | Where-Object { [string]$_.WorkspaceId -eq $WorkspaceId })
    }

    if (-not [string]::IsNullOrWhiteSpace($WorkspaceDeveloperName)) {
        $candidates = @($candidates | Where-Object { [string]$_.DeveloperName -eq $WorkspaceDeveloperName })
    }

    if (-not [string]::IsNullOrWhiteSpace($WorkspaceLabel)) {
        $candidates = @($candidates | Where-Object { [string]$_.Label -eq $WorkspaceLabel })
    }

    if ($candidates.Count -eq 1) {
        return $candidates[0]
    }

    $selectionWasRequested = (
        -not [string]::IsNullOrWhiteSpace($WorkspaceId) -or
        -not [string]::IsNullOrWhiteSpace($WorkspaceDeveloperName) -or
        -not [string]::IsNullOrWhiteSpace($WorkspaceLabel)
    )

    if ($candidates.Count -eq 0 -and $selectionWasRequested) {
        $requestedParts = @()
        if (-not [string]::IsNullOrWhiteSpace($WorkspaceId)) {
            $requestedParts += "WorkspaceId='$WorkspaceId'"
        }
        if (-not [string]::IsNullOrWhiteSpace($WorkspaceDeveloperName)) {
            $requestedParts += "WorkspaceDeveloperName='$WorkspaceDeveloperName'"
        }
        if (-not [string]::IsNullOrWhiteSpace($WorkspaceLabel)) {
            $requestedParts += "WorkspaceLabel='$WorkspaceLabel'"
        }

        throw ("No Tableau Next workspace matched {0} in org alias '{1}'. Discover workspaces first with scripts/tableau/list-next-workspaces.ps1." -f ($requestedParts -join ', '), (Resolve-TableauNextTargetOrg -TargetOrg $TargetOrg))
    }

    if ($candidates.Count -gt 1) {
        $candidateList = @($candidates | ForEach-Object { '{0} ({1})' -f $_.Label, $_.WorkspaceId }) -join ', '
        throw "Multiple Tableau Next workspaces matched the requested selection: $candidateList"
    }

    if ($AutoSelectSingleWorkspace -and $workspaceRows.Count -eq 1) {
        return $workspaceRows[0]
    }

    if ($workspaceRows.Count -eq 0) {
        throw ("No Tableau Next workspaces were returned for org alias '{0}'." -f (Resolve-TableauNextTargetOrg -TargetOrg $TargetOrg))
    }

    $workspaceSummary = @($workspaceRows | Select-Object -First 10 | ForEach-Object { '{0} ({1})' -f $_.Label, $_.WorkspaceId }) -join ', '
    throw ("Workspace selection is still required. Provide -WorkspaceId, -WorkspaceDeveloperName, or -WorkspaceLabel, or use -AutoSelectSingleWorkspace when exactly one workspace should be visible. Visible workspaces: {0}" -f $workspaceSummary)
}

function Get-TableauNextSemanticModelRows {
    param(
        [string]$TargetOrg,
        [int]$Limit = 200,
        [string]$WorkspaceId,
        [string]$SemanticModelId,
        [string]$WorkspaceAssetId
    )

    $context = Get-TableauNextAccessContext -TargetOrg $TargetOrg
    $safeLimit = [Math]::Max(1, $Limit)
    $workspaceRows = Get-TableauNextWorkspaceRows -TargetOrg $context.TargetOrg -Limit 2000
    $workspaceMap = @{}
    foreach ($workspaceRow in $workspaceRows) {
        if ([string]::IsNullOrWhiteSpace($workspaceRow.WorkspaceId)) {
            continue
        }

        $workspaceMap[$workspaceRow.WorkspaceId] = $workspaceRow
    }

    $assetFields = Get-TableauNextSelectableFields -Context $context -ObjectName 'AnalyticsWorkspaceAsset' -PreferredFields @(
        'Id',
        'AnalyticsWorkspaceId',
        'AssetId',
        'AssetUsageType',
        'AssetType',
        'HistoricalPromotionStatus',
        'CreatedDate',
        'LastModifiedDate'
    )

    $whereClauses = @("AssetType = 'SemanticModel'")
    if (-not [string]::IsNullOrWhiteSpace($WorkspaceId)) {
        $whereClauses += "AnalyticsWorkspaceId = '$WorkspaceId'"
    }
    if (-not [string]::IsNullOrWhiteSpace($SemanticModelId)) {
        $whereClauses += "AssetId = '$SemanticModelId'"
    }
    if (-not [string]::IsNullOrWhiteSpace($WorkspaceAssetId)) {
        $whereClauses += "Id = '$WorkspaceAssetId'"
    }

    $assetQuery = 'SELECT {0} FROM AnalyticsWorkspaceAsset WHERE {1} ORDER BY LastModifiedDate DESC LIMIT {2}' -f ($assetFields -join ', '), ($whereClauses -join ' AND '), $safeLimit
    $assetRecords = Invoke-TableauNextQuery -TargetOrg $context.TargetOrg -Query $assetQuery

    return @(
        foreach ($assetRecord in $assetRecords) {
            $assetWorkspaceId = Get-TableauNextRecordFieldValue -Record $assetRecord -FieldName 'AnalyticsWorkspaceId'
            $workspace = if ($assetWorkspaceId -and $workspaceMap.ContainsKey($assetWorkspaceId)) { $workspaceMap[$assetWorkspaceId] } else { $null }

            [pscustomobject]@{
                WorkspaceId = $assetWorkspaceId
                WorkspaceDeveloperName = if ($null -ne $workspace) { $workspace.DeveloperName } else { $null }
                WorkspaceLabel = if ($null -ne $workspace) { $workspace.Label } else { $null }
                SemanticModelId = Get-TableauNextRecordFieldValue -Record $assetRecord -FieldName 'AssetId'
                WorkspaceAssetId = Get-TableauNextRecordFieldValue -Record $assetRecord -FieldName 'Id'
                AssetType = Get-TableauNextRecordFieldValue -Record $assetRecord -FieldName 'AssetType'
                AssetUsageType = Get-TableauNextRecordFieldValue -Record $assetRecord -FieldName 'AssetUsageType'
                HistoricalPromotionStatus = Get-TableauNextRecordFieldValue -Record $assetRecord -FieldName 'HistoricalPromotionStatus'
                CreatedDate = Get-TableauNextRecordFieldValue -Record $assetRecord -FieldName 'CreatedDate'
                LastModifiedDate = Get-TableauNextRecordFieldValue -Record $assetRecord -FieldName 'LastModifiedDate'
            }
        }
    )
}

function Get-TableauNextSemanticModelDetail {
    param(
        [string]$TargetOrg,
        [string]$WorkspaceId,
        [string]$SemanticModelId,
        [string]$WorkspaceAssetId
    )

    if ([string]::IsNullOrWhiteSpace($SemanticModelId) -and [string]::IsNullOrWhiteSpace($WorkspaceAssetId)) {
        throw 'Provide -SemanticModelId or -WorkspaceAssetId when requesting semantic-model detail.'
    }

    $rows = @(Get-TableauNextSemanticModelRows -TargetOrg $TargetOrg -Limit 2000 -WorkspaceId $WorkspaceId)
    if (-not [string]::IsNullOrWhiteSpace($SemanticModelId)) {
        $rows = @($rows | Where-Object { [string]$_.SemanticModelId -eq $SemanticModelId })
    }
    if (-not [string]::IsNullOrWhiteSpace($WorkspaceAssetId)) {
        $rows = @($rows | Where-Object { [string]$_.WorkspaceAssetId -eq $WorkspaceAssetId })
    }

    if ($rows.Count -eq 0) {
        return $null
    }

    if ($rows.Count -gt 1) {
        throw 'Semantic-model detail query returned multiple rows. Narrow the query by workspace or ID.'
    }

    return $rows[0]
}

function Get-TableauNextRecordFieldValue {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Record,
        [Parameter(Mandatory = $true)]
        [string]$FieldName
    )

    $property = $Record.PSObject.Properties[$FieldName]
    if ($null -eq $property) {
        return $null
    }

    return $property.Value
}

function ConvertTo-TableauNextApiName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    $trimmed = $Value.Trim()
    if ([string]::IsNullOrWhiteSpace($trimmed)) {
        throw 'Provide a non-empty semantic-model API name or label.'
    }

    $normalized = $trimmed -replace '[^A-Za-z0-9_]+', '_'
    $normalized = $normalized -replace '_{2,}', '_'
    $normalized = $normalized.Trim('_')
    if ([string]::IsNullOrWhiteSpace($normalized)) {
        throw "Unable to derive a valid API name from '$Value'."
    }

    if ($normalized -match '^[0-9]') {
        $normalized = 'M_{0}' -f $normalized
    }

    return $normalized
}

function ConvertTo-TableauNextCookieHeader {
    param(
        [string]$CookieHeader,
        [string]$CookiePath
    )

    if (-not [string]::IsNullOrWhiteSpace($CookieHeader)) {
        return $CookieHeader.Trim()
    }

    if ([string]::IsNullOrWhiteSpace($CookiePath)) {
        return ''
    }

    $resolvedCookiePath = if ([System.IO.Path]::IsPathRooted($CookiePath)) { $CookiePath } else { Resolve-CommandCenterPath $CookiePath }
    if (-not (Test-Path -LiteralPath $resolvedCookiePath)) {
        throw "Aura cookie file '$resolvedCookiePath' was not found."
    }

    $cookiePairs = New-Object System.Collections.Generic.List[string]
    foreach ($line in (Get-Content -LiteralPath $resolvedCookiePath)) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith('#')) {
            continue
        }

        $columns = $line -split "`t"
        if ($columns.Count -lt 7) {
            continue
        }

        $cookieName = [string]$columns[5]
        throw
    }

    $parsedResponse = $response.Content | ConvertFrom-Json
    $errorMessage = Get-TableauNextAuraActionErrorMessage -Response $parsedResponse
    if (-not [string]::IsNullOrWhiteSpace($errorMessage)) {
        throw $errorMessage
    }

    return $parsedResponse
}

function Write-TableauNextOutput {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$Records,
        [string]$OutputPath,
        [switch]$Json,
        [string[]]$DefaultTableFields
    )

    if ($OutputPath) {
        $resolvedOutputPath = $OutputPath
        if (-not [System.IO.Path]::IsPathRooted($resolvedOutputPath)) {
            $resolvedOutputPath = Resolve-CommandCenterPath $OutputPath
        }

        Ensure-Directory -Path (Split-Path -Parent $resolvedOutputPath)
        $extension = [System.IO.Path]::GetExtension($resolvedOutputPath)
        if ($Json -or $extension -ieq '.json') {
            $Records | ConvertTo-Json -Depth 10 | Set-Content -Path $resolvedOutputPath -Encoding UTF8
        } else {
            $Records | Export-Csv -Path $resolvedOutputPath -NoTypeInformation -Encoding UTF8
        }

        Write-Host "Exported $($Records.Count) rows to '$resolvedOutputPath'."
        return
    }

    if ($Json) {
        $Records | ConvertTo-Json -Depth 10
        return
    }

    if ($DefaultTableFields -and $DefaultTableFields.Count -gt 0) {
        $Records | Select-Object -Property $DefaultTableFields | Format-Table -AutoSize
        return
    }

    $Records | Format-Table -AutoSize
}