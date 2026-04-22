[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [string]$ManifestPath,
    [string]$TargetOrg = $env:SF_DEFAULT_ALIAS,
    [string]$DataCloudAlias = $env:DATACLOUD_SALESFORCE_ALIAS,
    [string]$LoginUrl = $env:DATACLOUD_LOGIN_URL,
    [string]$TargetKeyPrefix,
    [string]$SourceName,
    [string]$ObjectNamePrefix,
    [string[]]$Tables,
    [string]$TableauNextTargetKey,
    [string]$WorkspaceId,
    [string]$WorkspaceDeveloperName,
    [string]$WorkspaceLabel,
    [switch]$AutoSelectSingleWorkspace,
    [string]$SemanticModelId,
    [string]$ModelApiName,
    [string]$ModelLabel,
    [string[]]$ObjectApiName,
    [string]$PrimaryObjectApiName,
    [string]$OutputPath,
    [switch]$SkipAuthAppDeploy,
    [switch]$SkipUpload,
    [switch]$SkipTableauNext,
    [switch]$ApplySemanticModel,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'DataCloud.Common.ps1')
. (Join-Path $PSScriptRoot '..\tableau\_TableauNext.Common.ps1')

function New-StateSection {
    param(
        [string]$Status = 'pending'
    )

    return [ordered]@{ status = $Status }
}

function Add-ReadinessBlocker {
    param(
        [AllowEmptyCollection()]
        [Parameter(Mandatory = $true)]
        [System.Collections.Generic.List[object]]$Collection,
        [Parameter(Mandatory = $true)]
        [string]$Classification,
        [Parameter(Mandatory = $true)]
        [string]$Surface,
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [string]$SuggestedAction = '',
        [bool]$PlatformBound = $false
    )

    $Collection.Add([pscustomobject]@{
        classification = $Classification
        surface = $Surface
        message = $Message
        suggestedAction = $SuggestedAction
        platformBound = $PlatformBound
    }) | Out-Null
}

function Add-ReadinessNote {
    param(
        [AllowEmptyCollection()]
        [System.Collections.Generic.List[string]]$Collection,
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    if (-not [string]::IsNullOrWhiteSpace($Message)) {
        $Collection.Add($Message) | Out-Null
    }
}

function Get-HighestBlockerClassification {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$Blockers
    )

    $priority = @{
        BlockedByExternalApiLimitation = 4
        BlockedByPermission = 3
        BlockedByOrgConfiguration = 2
    }

    $selected = 'ReadyForFullAutomation'
    $selectedPriority = -1
    foreach ($blocker in @($Blockers)) {
        $classification = [string]$blocker.classification
        if (-not $priority.ContainsKey($classification)) {
            continue
        }

        if ($priority[$classification] -gt $selectedPriority) {
            $selectedPriority = $priority[$classification]
            $selected = $classification
        }
    }

    return $selected
}

function Resolve-ManifestTargetRows {
    param(
        [Parameter(Mandatory = $true)]
        [object]$ManifestInfo,
        [Parameter(Mandatory = $true)]
        [string]$TargetKeyPrefix,
        [string]$TargetKeySeparator = '-',
        [string[]]$SelectedTables
    )

    $manifest = $ManifestInfo.Content
    $selectedTableSet = @{}
    foreach ($tableName in @($SelectedTables)) {
        if (-not [string]::IsNullOrWhiteSpace($tableName)) {
            $selectedTableSet[[string]$tableName] = $true
        }
    }

    $registry = Get-DataCloudRegistry
    $rows = New-Object System.Collections.Generic.List[object]
    foreach ($file in @($manifest.files)) {
        $tableName = [string]$file.tableName
        if ($selectedTableSet.Count -gt 0 -and -not $selectedTableSet.ContainsKey($tableName)) {
            continue
        }

        $targetKey = Resolve-DataCloudManifestTargetKey -TableName $tableName -TargetKeyPrefix $TargetKeyPrefix -TargetKeySeparator $TargetKeySeparator
        $target = @($registry.targets | Where-Object { $_.key -eq $targetKey } | Select-Object -First 1)
        if ($target.Count -eq 0) {
            continue
        }

        $rows.Add([pscustomobject]@{
            tableName = $tableName
            targetKey = $targetKey
            target = $target[0]
            csvPath = Resolve-DataCloudManifestCsvPath -ManifestInfo $ManifestInfo -FileDefinition $file
        }) | Out-Null
    }

    return $rows.ToArray()
}

function Get-ObjectApiNamesFromTargets {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$TargetRows,
        [Parameter(Mandatory = $true)]
        [string]$RootTableName
    )

    $objectNames = New-Object System.Collections.Generic.List[string]
    $primaryObjectName = ''
    foreach ($row in @($TargetRows)) {
        $objectName = [string](Get-OptionalObjectPropertyValue -InputObject $row.target -PropertyName 'objectName')
        if ([string]::IsNullOrWhiteSpace($objectName)) {
            continue
        }

        if ($row.tableName -eq $RootTableName) {
            $primaryObjectName = $objectName
        }

        $objectNames.Add($objectName) | Out-Null
    }

    return [pscustomobject]@{
        objectApiNames = @($objectNames | Select-Object -Unique)
        primaryObjectApiName = $primaryObjectName
    }
}

function ConvertTo-SemanticModelFieldApiName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FieldName
    )

    return '{0}__c' -f (New-MetadataSafeName -Value $FieldName -MaxLength 37)
}

function ConvertTo-SemanticModelLabel {
    param(
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ''
    }

    $textInfo = [System.Globalization.CultureInfo]::InvariantCulture.TextInfo
    return ($Value -split '[_\s]+' | Where-Object { $_ } | ForEach-Object { $textInfo.ToTitleCase($_.ToLowerInvariant()) }) -join ' '
}

function New-ManifestSemanticModelSpec {
    param(
        [Parameter(Mandatory = $true)]
        [object]$ManifestInfo,
        [Parameter(Mandatory = $true)]
        [object]$Manifest,
        [Parameter(Mandatory = $true)]
        [object[]]$TargetRows,
        [Parameter(Mandatory = $true)]
        [object[]]$ProvisionedStreams,
        [Parameter(Mandatory = $true)]
        [object]$WorkspaceTarget,
        [Parameter(Mandatory = $true)]
        [string]$ModelApiName,
        [Parameter(Mandatory = $true)]
        [string]$ModelLabel,
        [Parameter(Mandatory = $true)]
        [string]$RootTableName
    )

    $tableNames = @($TargetRows | ForEach-Object { [string]$_.tableName } | Select-Object -Unique)
    $joinGraphByTable = @{}
    foreach ($joinGraphEntry in @($Manifest.joinGraph)) {
        $joinGraphByTable[[string]$joinGraphEntry.tableName] = $joinGraphEntry
    }

    $provisionedStreamsByTable = @{}
    foreach ($stream in @($ProvisionedStreams)) {
        $provisionedStreamsByTable[[string]$stream.tableName] = $stream
    }

    $objectMappings = New-Object System.Collections.Generic.List[object]
    $resolvedObjectApiNames = New-Object System.Collections.Generic.List[string]
    $resolvedPrimaryObjectApiName = ''
    foreach ($row in @($TargetRows)) {
        $provisionedStream = $provisionedStreamsByTable[[string]$row.tableName]
        $objectApiName = ''
        if ($null -ne $provisionedStream -and -not [string]::IsNullOrWhiteSpace([string]$provisionedStream.dataLakeObjectName)) {
            $objectApiName = [string]$provisionedStream.dataLakeObjectName
        }
        if ([string]::IsNullOrWhiteSpace($objectApiName)) {
            $objectApiName = [string](Get-OptionalObjectPropertyValue -InputObject $row.target -PropertyName 'objectName')
        }
        if ([string]::IsNullOrWhiteSpace($objectApiName)) {
            throw "Target row '$([string]$row.tableName)' is missing a resolved dataLakeObjectName and registered objectName."
        }

        $csvProfile = Get-DataCloudCsvFieldProfiles -CsvPath ([string]$row.csvPath) -AllowHeaderOnly -ContextLabel ("Table '$([string]$row.tableName)'")
        $joinGraphEntry = $joinGraphByTable[[string]$row.tableName]
        $primaryKeys = if ($null -ne $joinGraphEntry) { @($joinGraphEntry.primaryKey) } else { @() }
        $fieldDefinitions = @(
            foreach ($field in @($csvProfile.fields)) {
                [ordered]@{
                    dataObjectFieldName = ConvertTo-SemanticModelFieldApiName -FieldName ([string]$field.apiName)
                    sourceFieldName = [string]$field.name
                    label = [string]$field.name
                    customFieldType = [string]$field.customFieldType
                    dataType = [string]$field.dataType
                }
            }
        )

        $primaryKeyFields = @(
            foreach ($primaryKey in @($primaryKeys)) {
                $matchingField = @($csvProfile.fields | Where-Object { [string]$_.name -eq [string]$primaryKey } | Select-Object -First 1)
                if ($matchingField.Count -gt 0) {
                    ConvertTo-SemanticModelFieldApiName -FieldName ([string]$matchingField[0].apiName)
                }
            }
        )

        if ($row.tableName -eq $RootTableName) {
            $resolvedPrimaryObjectApiName = $objectApiName
        }

        $resolvedObjectApiNames.Add($objectApiName) | Out-Null
        $objectMappings.Add([ordered]@{
            tableName = [string]$row.tableName
            objectApiName = $objectApiName
            label = ConvertTo-SemanticModelLabel -Value ([string]$row.tableName)
            primaryKeyFields = @($primaryKeyFields)
            fields = @($fieldDefinitions)
        }) | Out-Null
    }

    $relationshipDefinitions = @(
        foreach ($relationship in @($Manifest.publishContract.relationships)) {
            if ($tableNames -notcontains [string]$relationship.sourceTable -or $tableNames -notcontains [string]$relationship.targetTable) {
                continue
            }

            [ordered]@{
                sourceTable = [string]$relationship.sourceTable
                sourceField = ConvertTo-SemanticModelFieldApiName -FieldName ([string]$relationship.sourceField)
                targetTable = [string]$relationship.targetTable
                targetField = ConvertTo-SemanticModelFieldApiName -FieldName ([string]$relationship.targetField)
                direction = [string]$relationship.direction
                required = [bool]$relationship.required
            }
        }
    )

    return [ordered]@{
        SemanticModelSpec = [ordered]@{
            targetKey = [string]$WorkspaceTarget.key
            targetOrg = [string]$WorkspaceTarget.targetOrg
            workspace = [ordered]@{
                workspaceId = [string]$WorkspaceTarget.workspaceId
                workspaceDeveloperName = [string]$WorkspaceTarget.workspaceDeveloperName
                workspaceLabel = [string]$WorkspaceTarget.workspaceLabel
            }
            model = [ordered]@{
                apiName = $ModelApiName
                label = $ModelLabel
                description = ''
                dataSpace = 'default'
                primaryObjectApiName = $resolvedPrimaryObjectApiName
                objectApiNames = @($resolvedObjectApiNames | Select-Object -Unique)
                objectMappings = @($objectMappings.ToArray())
                relationshipDefinitions = @($relationshipDefinitions)
            }
        }
    }
}

function Get-DataCloudConnectorSummary {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InstanceUrl,
        [Parameter(Mandatory = $true)]
        [string]$AccessToken,
        [Parameter(Mandatory = $true)]
        [string]$SourceName
    )

    $uri = '{0}/services/data/v62.0/ssot/connections?connectorType=IngestApi&limit=200' -f $InstanceUrl.TrimEnd('/')
    $headers = @{ Authorization = 'Bearer {0}' -f $AccessToken }
    try {
        $response = Invoke-RestMethod -Method Get -Uri $uri -Headers $headers
    } catch {
        throw (Get-DataCloudErrorMessage -ErrorRecord $_)
    }

    $connections = @($response.connections)
    $connector = @($connections | Where-Object { [string]$_.name -eq $SourceName -or [string]$_.label -eq $SourceName } | Select-Object -First 1)
    if ($connector.Count -eq 0) {
        return $null
    }

    return [pscustomobject]@{
        id = $connector[0].id
        name = $connector[0].name
        label = $connector[0].label
        connectorType = $connector[0].connectorType
    }
}

Import-CommandCenterEnv

$setupAuthScriptPath = Join-Path $PSScriptRoot 'setup-command-center-connected-app.ps1'
$dataCloudLoginScriptPath = Join-Path $PSScriptRoot 'data-cloud-login-web.ps1'
$registerTargetsScriptPath = Join-Path $PSScriptRoot 'data-cloud-register-manifest-targets.ps1'
$dataCloudAccessScriptPath = Join-Path $PSScriptRoot 'data-cloud-get-access-token.ps1'
$streamBootstrapScriptPath = Join-Path $PSScriptRoot 'data-cloud-create-manifest-streams.ps1'
$uploadManifestScriptPath = Join-Path $PSScriptRoot 'data-cloud-upload-manifest.ps1'
$uploadCsvScriptPath = Join-Path $PSScriptRoot 'data-cloud-upload-csv.ps1'
$registerNextTargetScriptPath = Join-Path $PSScriptRoot '..\tableau\register-next-target.ps1'
$inspectNextTargetScriptPath = Join-Path $PSScriptRoot '..\tableau\inspect-next-target.ps1'
$inspectNextSemanticModelScriptPath = Join-Path $PSScriptRoot '..\tableau\inspect-next-semantic-model.ps1'
$upsertNextSemanticModelScriptPath = Join-Path $PSScriptRoot '..\tableau\upsert-next-semantic-model.ps1'

$manifestInfo = Get-DataCloudManifestInfo -ManifestPath $ManifestPath
$manifest = $manifestInfo.Content
$datasetDefaults = Get-DataCloudManifestDefaults -ManifestInfo $manifestInfo
$rootTableName = if ($null -ne $manifest.publishContract -and -not [string]::IsNullOrWhiteSpace([string]$manifest.publishContract.rootTable)) { [string]$manifest.publishContract.rootTable } else { [string]$manifest.files[0].tableName }
$registrationHints = Get-DataCloudManifestRegistrationHints -ManifestInfo $manifestInfo -Registry (Get-DataCloudRegistry) -RootTableName $rootTableName

if ([string]::IsNullOrWhiteSpace($TargetKeyPrefix)) {
    $TargetKeyPrefix = if (-not [string]::IsNullOrWhiteSpace($registrationHints.TargetKeyPrefix)) { $registrationHints.TargetKeyPrefix } else { $datasetDefaults.TargetKeyPrefix }
}
if ([string]::IsNullOrWhiteSpace($SourceName)) {
    $SourceName = if (-not [string]::IsNullOrWhiteSpace($registrationHints.SourceName)) { $registrationHints.SourceName } else { $datasetDefaults.SourceName }
}
if ([string]::IsNullOrWhiteSpace($ObjectNamePrefix)) {
    $ObjectNamePrefix = if (-not [string]::IsNullOrWhiteSpace($registrationHints.ObjectNamePrefix)) { $registrationHints.ObjectNamePrefix } else { ($TargetKeyPrefix -replace '-', '_') }
}
if ([string]::IsNullOrWhiteSpace($DataCloudAlias)) {
    $DataCloudAlias = if (-not [string]::IsNullOrWhiteSpace($registrationHints.SalesforceAlias)) { $registrationHints.SalesforceAlias } elseif (-not [string]::IsNullOrWhiteSpace($TargetOrg)) { '{0}_DC' -f $TargetOrg } else { '' }
}
if ([string]::IsNullOrWhiteSpace($TableauNextTargetKey)) {
    $TableauNextTargetKey = '{0}-sdm' -f $datasetDefaults.DatasetKey
}
if ([string]::IsNullOrWhiteSpace($ModelLabel)) {
    $ModelLabel = '{0} Semantic Model' -f $datasetDefaults.DatasetLabel
}
if ([string]::IsNullOrWhiteSpace($ModelApiName)) {
    $ModelApiName = ConvertTo-TableauNextApiName -Value ('{0} Semantic Model' -f $datasetDefaults.DatasetLabel)
}
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Resolve-CommandCenterPath (Join-Path 'tmp' ('{0}-authenticated-to-sdm-state.json' -f $datasetDefaults.DatasetKey))
}

$resolvedOutputPath = if ([System.IO.Path]::IsPathRooted($OutputPath)) { $OutputPath } else { Resolve-CommandCenterPath $OutputPath }
Ensure-Directory -Path (Split-Path -Parent $resolvedOutputPath)

$blockers = New-Object System.Collections.Generic.List[object]
$dryRunReasons = New-Object System.Collections.Generic.List[string]
$nextSteps = New-Object System.Collections.Generic.List[string]
$targetRows = @()
$streamBootstrap = $null
$uploadResult = $null
$workspaceTarget = $null
$targetInspection = $null
$semanticModelInspection = $null
$semanticModelRequest = $null
$orgAccessContext = $null
$dataCloudAccessContext = $null
$connectorSummary = $null

$state = [ordered]@{
    generatedAt = Get-UtcTimestamp
    requestedOperation = [ordered]@{
        manifestPath = $manifestInfo.RelativePath
        datasetKey = $datasetDefaults.DatasetKey
        datasetLabel = $datasetDefaults.DatasetLabel
        targetOrg = $TargetOrg
        dataCloudAlias = $DataCloudAlias
        sourceName = $SourceName
        targetKeyPrefix = $TargetKeyPrefix
        objectNamePrefix = $ObjectNamePrefix
        tables = @($Tables)
        tableauNextTargetKey = $TableauNextTargetKey
        workspaceId = $WorkspaceId
        workspaceDeveloperName = $WorkspaceDeveloperName
        workspaceLabel = $WorkspaceLabel
        skipUpload = [bool]$SkipUpload
        skipTableauNext = [bool]$SkipTableauNext
        applySemanticModel = [bool]$ApplySemanticModel
    }
    phases = [ordered]@{
        salesforceAuth = New-StateSection
        commandCenterAuth = New-StateSection
        manifestTargets = New-StateSection
        dataCloudAuth = New-StateSection
        dataCloudConnector = New-StateSection
        streamBootstrap = New-StateSection
        upload = New-StateSection
        tableauNextTarget = New-StateSection
        tableauNextInspection = New-StateSection
        semanticModelInspection = New-StateSection
        semanticModelRequest = New-StateSection
    }
}

try {
    $orgAccessContext = Get-SalesforceOrgAccessContext -Alias $TargetOrg -LoginUrl $LoginUrl
    $state.phases.salesforceAuth.status = 'validated'
    $state.phases.salesforceAuth.authSource = $orgAccessContext.source
    $state.phases.salesforceAuth.instanceUrl = $orgAccessContext.instanceUrl
} catch {
    $message = $_.Exception.Message
    $state.phases.salesforceAuth.status = 'failed'
    $state.phases.salesforceAuth.message = $message
    Add-ReadinessBlocker -Collection $blockers -Classification 'BlockedByPermission' -Surface 'salesforce-auth' -Message $message -SuggestedAction 'Authenticate the standard Salesforce org alias first with scripts/salesforce/login-web.ps1.'
}

if ($state.phases.salesforceAuth.status -eq 'validated') {
    if ($SkipAuthAppDeploy) {
        $state.phases.commandCenterAuth.status = 'skipped'
    } else {
        try {
            & $setupAuthScriptPath -TargetOrg $TargetOrg
            $state.phases.commandCenterAuth.status = 'deployed-or-verified'
        } catch {
            $message = $_.Exception.Message
            $state.phases.commandCenterAuth.status = 'failed'
            $state.phases.commandCenterAuth.message = $message
            Add-ReadinessBlocker -Collection $blockers -Classification 'BlockedByOrgConfiguration' -Surface 'commandcenterauth' -Message $message -SuggestedAction 'Ensure External Client App metadata deployment is allowed and the current user can deploy it.'
        }
    }
}

try {
    $registerArgs = @{
        ManifestPath = $manifestInfo.Path
        SourceName = $SourceName
        TargetKeyPrefix = $TargetKeyPrefix
        ObjectNamePrefix = $ObjectNamePrefix
        SalesforceAlias = $DataCloudAlias
    }
    $registeredTargets = & $registerTargetsScriptPath @registerArgs
    $targetRows = @(Resolve-ManifestTargetRows -ManifestInfo $manifestInfo -TargetKeyPrefix $TargetKeyPrefix -SelectedTables $Tables)
    $state.phases.manifestTargets.status = 'registered'
    $state.phases.manifestTargets.targetCount = @($targetRows).Count
    $state.phases.manifestTargets.defaultTargetKey = Resolve-DataCloudManifestTargetKey -TableName $rootTableName -TargetKeyPrefix $TargetKeyPrefix
} catch {
    $message = $_.Exception.Message
    $state.phases.manifestTargets.status = 'failed'
    $state.phases.manifestTargets.message = $message
    Add-ReadinessBlocker -Collection $blockers -Classification 'BlockedByOrgConfiguration' -Surface 'manifest-target-registration' -Message $message -SuggestedAction 'Fix the manifest inputs or registry write permissions, then rerun the orchestration.'
}

$rootTargetKey = Resolve-DataCloudManifestTargetKey -TableName $rootTableName -TargetKeyPrefix $TargetKeyPrefix
if ($state.phases.manifestTargets.status -eq 'registered') {
    try {
        $dataCloudAccessContext = & $dataCloudAccessScriptPath -TargetKey $rootTargetKey -AsJson | ConvertFrom-Json
        $state.phases.dataCloudAuth.status = 'validated'
        $state.phases.dataCloudAuth.targetKey = $rootTargetKey
        $state.phases.dataCloudAuth.tokenSource = $dataCloudAccessContext.tokenSource
        $state.phases.dataCloudAuth.salesforceAlias = $dataCloudAccessContext.salesforceAlias
        $state.phases.dataCloudAuth.tenantEndpoint = $dataCloudAccessContext.tenantEndpoint
    } catch {
        $firstFailure = $_.Exception.Message
        if ($state.phases.salesforceAuth.status -eq 'validated' -and -not [string]::IsNullOrWhiteSpace($DataCloudAlias)) {
            try {
                & $dataCloudLoginScriptPath -Alias $DataCloudAlias -InstanceUrl $orgAccessContext.instanceUrl -SetDefault -ValidateAfterLogin
                $dataCloudAccessContext = & $dataCloudAccessScriptPath -TargetKey $rootTargetKey -AsJson | ConvertFrom-Json
                $state.phases.dataCloudAuth.status = 'validated-after-login-bootstrap'
                $state.phases.dataCloudAuth.targetKey = $rootTargetKey
                $state.phases.dataCloudAuth.tokenSource = $dataCloudAccessContext.tokenSource
                $state.phases.dataCloudAuth.salesforceAlias = $dataCloudAccessContext.salesforceAlias
                $state.phases.dataCloudAuth.tenantEndpoint = $dataCloudAccessContext.tenantEndpoint
            } catch {
                $message = $_.Exception.Message
                $state.phases.dataCloudAuth.status = 'failed'
                $state.phases.dataCloudAuth.message = $message
                Add-ReadinessBlocker -Collection $blockers -Classification 'BlockedByPermission' -Surface 'data-cloud-auth' -Message $message -SuggestedAction 'Authorize the dedicated Data Cloud alias with CommandCenterAuth and cdp_ingest_api scope.'
                $state.phases.dataCloudAuth.initialFailure = $firstFailure
            }
        } else {
            $state.phases.dataCloudAuth.status = 'failed'
            $state.phases.dataCloudAuth.message = $firstFailure
            Add-ReadinessBlocker -Collection $blockers -Classification 'BlockedByPermission' -Surface 'data-cloud-auth' -Message $firstFailure -SuggestedAction 'Authorize the dedicated Data Cloud alias with CommandCenterAuth and cdp_ingest_api scope.'
        }
    }
}

if ($state.phases.dataCloudAuth.status -like 'validated*') {
    try {
        $orgContextForConnector = Get-SalesforceOrgAccessContext -Alias $(if (-not [string]::IsNullOrWhiteSpace($DataCloudAlias)) { $DataCloudAlias } else { $TargetOrg }) -LoginUrl $LoginUrl
        $connectorSummary = Get-DataCloudConnectorSummary -InstanceUrl $orgContextForConnector.instanceUrl -AccessToken $orgContextForConnector.accessToken -SourceName $SourceName
        if ($null -eq $connectorSummary) {
            $state.phases.dataCloudConnector.status = 'missing'
            Add-ReadinessBlocker -Collection $blockers -Classification 'BlockedByOrgConfiguration' -Surface 'data-cloud-connector' -Message ("Ingestion API connector '{0}' was not found in the target org." -f $SourceName) -SuggestedAction 'Create or expose the Ingestion API connector in Data Cloud Setup. This repo still cannot create the connector automatically.' -PlatformBound:$true
        } else {
            $state.phases.dataCloudConnector.status = 'resolved-existing'
            $state.phases.dataCloudConnector.connectorId = $connectorSummary.id
            $state.phases.dataCloudConnector.connectorName = $connectorSummary.name
        }
    } catch {
        $message = $_.Exception.Message
        $state.phases.dataCloudConnector.status = 'failed'
        $state.phases.dataCloudConnector.message = $message
        Add-ReadinessBlocker -Collection $blockers -Classification 'BlockedByOrgConfiguration' -Surface 'data-cloud-connector' -Message $message -SuggestedAction 'Confirm Data Cloud is provisioned and the connector is accessible to the current user.' -PlatformBound:$true
    }
}

if ($state.phases.dataCloudConnector.status -eq 'resolved-existing') {
    try {
        $streamOutputRoot = Join-Path (Split-Path -Parent $resolvedOutputPath) 'stream-bootstrap'
        $streamArgs = @{
            ManifestPath = $manifestInfo.Path
            TargetOrg = $(if (-not [string]::IsNullOrWhiteSpace($DataCloudAlias)) { $DataCloudAlias } else { $TargetOrg })
            SourceName = $SourceName
            ObjectNamePrefix = $ObjectNamePrefix
            OutputRoot = $streamOutputRoot
            Force = $Force
        }
        if ($Tables -and $Tables.Count -gt 0) {
            $streamArgs.Tables = $Tables
        }

        $streamBootstrap = & $streamBootstrapScriptPath @streamArgs
        $streamBootstrap = $streamBootstrap | ConvertTo-Json -Depth 20 | ConvertFrom-Json
        $targetRows = @(Resolve-ManifestTargetRows -ManifestInfo $manifestInfo -TargetKeyPrefix $TargetKeyPrefix -SelectedTables $Tables)
        $state.phases.streamBootstrap.status = 'completed'
        $state.phases.streamBootstrap.reportPath = $streamBootstrap.reportPath
        $state.phases.streamBootstrap.provisionedStreams = $streamBootstrap.provisionedStreams
        $state.phases.streamBootstrap.registrySync = $streamBootstrap.registrySync
    } catch {
        $message = $_.Exception.Message
        $state.phases.streamBootstrap.status = 'failed'
        $state.phases.streamBootstrap.message = $message
        Add-ReadinessBlocker -Collection $blockers -Classification 'BlockedByOrgConfiguration' -Surface 'data-cloud-stream-bootstrap' -Message $message -SuggestedAction 'Resolve the live connector or stream state in Data Cloud, then rerun stream bootstrap.' -PlatformBound:$true
    }
}

if ($state.phases.streamBootstrap.status -eq 'completed') {
    if ($SkipUpload) {
        $state.phases.upload.status = 'skipped'
    } else {
        try {
            if ($Tables -and $Tables.Count -gt 0) {
                $jobs = New-Object System.Collections.Generic.List[object]
                foreach ($row in @($targetRows)) {
                    $job = & $uploadCsvScriptPath -TargetKey $row.targetKey -CsvPath $row.csvPath
                    $jobs.Add($job) | Out-Null
                }
                $uploadResult = $jobs.ToArray()
            } else {
                $uploadResult = & $uploadManifestScriptPath -ManifestPath $manifestInfo.Path -TargetKeyPrefix $TargetKeyPrefix
            }

            $state.phases.upload.status = 'completed'
            $state.phases.upload.jobs = @($uploadResult)
        } catch {
            $message = $_.Exception.Message
            $state.phases.upload.status = 'failed'
            $state.phases.upload.message = $message
            Add-ReadinessBlocker -Collection $blockers -Classification 'BlockedByOrgConfiguration' -Surface 'data-cloud-upload' -Message $message -SuggestedAction 'Inspect or abort the conflicting job, or confirm the live object route contract for this connector.' -PlatformBound:$true
        }
    }
}

if ($SkipTableauNext) {
    $state.phases.tableauNextTarget.status = 'skipped'
    $state.phases.tableauNextInspection.status = 'skipped'
    $state.phases.semanticModelInspection.status = 'skipped'
    $state.phases.semanticModelRequest.status = 'skipped'
} else {
    try {
        $existingTarget = $null
        try {
            $existingTarget = Get-TableauNextTargetConfiguration -TargetKey $TableauNextTargetKey
        } catch {
            $existingTarget = $null
        }

        if ($null -ne $existingTarget -and [string]::IsNullOrWhiteSpace($WorkspaceId) -and [string]::IsNullOrWhiteSpace($WorkspaceDeveloperName) -and [string]::IsNullOrWhiteSpace($WorkspaceLabel) -and [string]::IsNullOrWhiteSpace($SemanticModelId)) {
            $workspaceTarget = [pscustomobject]@{ key = $existingTarget.TargetKey; targetOrg = $existingTarget.TargetOrg; workspaceId = $existingTarget.WorkspaceId; workspaceDeveloperName = $existingTarget.WorkspaceDeveloperName; workspaceLabel = $existingTarget.WorkspaceLabel; semanticModelId = $existingTarget.SemanticModelId; workspaceAssetId = $existingTarget.WorkspaceAssetId }
            $state.phases.tableauNextTarget.status = 'reused-existing'
        } else {
            $workspaceTarget = & $registerNextTargetScriptPath -TargetKey $TableauNextTargetKey -TargetOrg $TargetOrg -WorkspaceId $WorkspaceId -WorkspaceDeveloperName $WorkspaceDeveloperName -WorkspaceLabel $WorkspaceLabel -SemanticModelId $SemanticModelId -AutoSelectSingleWorkspace:$AutoSelectSingleWorkspace
            $state.phases.tableauNextTarget.status = 'registered-or-updated'
        }

        $state.phases.tableauNextTarget.targetKey = $workspaceTarget.key
        $state.phases.tableauNextTarget.workspaceId = $workspaceTarget.workspaceId
        $state.phases.tableauNextTarget.workspaceDeveloperName = $workspaceTarget.workspaceDeveloperName
        $state.phases.tableauNextTarget.workspaceLabel = $workspaceTarget.workspaceLabel
    } catch {
        $message = $_.Exception.Message
        $state.phases.tableauNextTarget.status = 'failed'
        $state.phases.tableauNextTarget.message = $message
        Add-ReadinessBlocker -Collection $blockers -Classification 'BlockedByOrgConfiguration' -Surface 'tableau-next-target' -Message $message -SuggestedAction 'Provide workspace selection criteria or use a target that already pins the workspace.'
    }

    if ($state.phases.tableauNextTarget.status -in @('reused-existing', 'registered-or-updated')) {
        try {
            $targetInspection = & $inspectNextTargetScriptPath -TargetKey $workspaceTarget.key -Json | ConvertFrom-Json
            $state.phases.tableauNextInspection.status = [string]$targetInspection.InspectionStatus
            $state.phases.tableauNextInspection.result = $targetInspection
        } catch {
            $message = $_.Exception.Message
            $state.phases.tableauNextInspection.status = 'failed'
            $state.phases.tableauNextInspection.message = $message
            Add-ReadinessBlocker -Collection $blockers -Classification 'BlockedByOrgConfiguration' -Surface 'tableau-next-inspection' -Message $message -SuggestedAction 'Revalidate the saved target against live workspace discovery.'
        }
    }

    if ($state.phases.tableauNextInspection.status -in @('ExistingSemanticModelValidated', 'ReadyForCreation')) {
        $semanticModelInspectionStatus = 'skipped'
        $resolvedPinnedSemanticModelId = Get-TableauNextTargetPropertyValue -Target $workspaceTarget -PropertyName 'semanticModelId'
        if (-not [string]::IsNullOrWhiteSpace($SemanticModelId) -or (-not [string]::IsNullOrWhiteSpace($resolvedPinnedSemanticModelId))) {
            try {
                $inspectSemanticArgs = @{
                    TargetKey = $workspaceTarget.key
                    Json = $true
                }
                if (-not [string]::IsNullOrWhiteSpace($SemanticModelId)) {
                    $inspectSemanticArgs.SemanticModelId = $SemanticModelId
                }
                $semanticModelInspection = & $inspectNextSemanticModelScriptPath @inspectSemanticArgs | ConvertFrom-Json
                $semanticModelInspectionStatus = [string]$semanticModelInspection.InspectionStatus
                $state.phases.semanticModelInspection.status = $semanticModelInspectionStatus
                $state.phases.semanticModelInspection.result = $semanticModelInspection
            } catch {
                $message = $_.Exception.Message
                $state.phases.semanticModelInspection.status = 'failed'
                $state.phases.semanticModelInspection.message = $message
                Add-ReadinessBlocker -Collection $blockers -Classification 'BlockedByOrgConfiguration' -Surface 'semantic-model-inspection' -Message $message -SuggestedAction 'Inspect semantic-model inventory again and confirm the pinned model still exists.'
            }
        } else {
            $state.phases.semanticModelInspection.status = $semanticModelInspectionStatus
        }

        try {
            $objectApiResolution = if ($ObjectApiName -and $ObjectApiName.Count -gt 0) {
                [pscustomobject]@{
                    objectApiNames = @($ObjectApiName)
                    primaryObjectApiName = $PrimaryObjectApiName
                }
            } else {
                Get-ObjectApiNamesFromTargets -TargetRows $targetRows -RootTableName $rootTableName
            }

            $resolvedObjectApiNames = @($objectApiResolution.objectApiNames | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } | Select-Object -Unique)
            $resolvedPrimaryObjectApiName = if (-not [string]::IsNullOrWhiteSpace($PrimaryObjectApiName)) { $PrimaryObjectApiName } else { [string]$objectApiResolution.primaryObjectApiName }
            if ([string]::IsNullOrWhiteSpace($resolvedPrimaryObjectApiName) -and $resolvedObjectApiNames.Count -gt 0) {
                $resolvedPrimaryObjectApiName = $resolvedObjectApiNames[0]
            }
            if ($resolvedObjectApiNames.Count -eq 0) {
                throw 'No stable Data Cloud object API names were available for semantic-model request generation.'
            }

            $requestOutputPath = Join-Path (Split-Path -Parent $resolvedOutputPath) ('{0}.semantic-model.request.json' -f $datasetDefaults.DatasetKey)
            $specOutputPath = Join-Path (Split-Path -Parent $resolvedOutputPath) ('{0}.semantic-model.spec.json' -f $datasetDefaults.DatasetKey)
            $semanticModelSpec = New-ManifestSemanticModelSpec -ManifestInfo $manifestInfo -Manifest $manifest -TargetRows $targetRows -ProvisionedStreams @($streamBootstrap.provisionedStreams) -WorkspaceTarget $workspaceTarget -ModelApiName $ModelApiName -ModelLabel $ModelLabel -RootTableName $rootTableName
            Write-JsonFile -Path $specOutputPath -Value ([pscustomobject]$semanticModelSpec)
            $upsertArgs = @{
                TargetKey = $workspaceTarget.key
                SpecPath = $specOutputPath
                OutputPath = $requestOutputPath
                Json = $true
            }
            if ($ApplySemanticModel) {
                $upsertArgs.Apply = $true
            }

            $semanticModelRequest = & $upsertNextSemanticModelScriptPath @upsertArgs | ConvertFrom-Json
            $state.phases.semanticModelRequest.status = [string]$semanticModelRequest.ApplyStatus
            $state.phases.semanticModelRequest.outputPath = $requestOutputPath
            $state.phases.semanticModelRequest.specPath = $specOutputPath
            $state.phases.semanticModelRequest.result = $semanticModelRequest
        } catch {
            $message = $_.Exception.Message
            $state.phases.semanticModelRequest.status = 'failed'
            $state.phases.semanticModelRequest.message = $message
            Add-ReadinessBlocker -Collection $blockers -Classification 'BlockedByOrgConfiguration' -Surface 'semantic-model-request' -Message $message -SuggestedAction 'Confirm the workspace target, manifest relationship fields, and registered Data Cloud object names are correct.'
        }
    }
}

$classification = if ($blockers.Count -gt 0) {
    Get-HighestBlockerClassification -Blockers $blockers.ToArray()
} elseif ($dryRunReasons.Count -gt 0) {
    'ReadyThroughDryRunOnly'
} else {
    'ReadyForFullAutomation'
}

if ($state.phases.dataCloudConnector.status -ne 'resolved-existing') {
    Add-ReadinessNote -Collection $nextSteps -Message 'Create or expose the Ingestion API connector in Data Cloud Setup.'
}
if ($state.phases.tableauNextTarget.status -eq 'failed') {
    Add-ReadinessNote -Collection $nextSteps -Message 'Provide a stable workspace selector such as WorkspaceDeveloperName or WorkspaceId.'
}

$state.readiness = [ordered]@{
    classification = $classification
    blockers = $blockers.ToArray()
    dryRunReasons = $dryRunReasons.ToArray()
    nextSteps = @($nextSteps | Select-Object -Unique)
}

$state.zeroTouchDefinition = [ordered]@{
    nowAutomatedAfterAuthentication = @(
        'CommandCenterAuth deployment or verification',
        'Manifest-derived Data Cloud target registration and refresh',
        'Data Cloud connector preflight and stream reconciliation',
        'Accepted object-name and objectEndpoint capture through stream bootstrap',
        'Manifest or per-table upload execution using registered targets',
        'Tableau Next workspace discovery and target registration when the workspace is uniquely discoverable or explicitly identified',
        'Direct semantic-model inventory inspection',
        'Semantic-model request generation and supported semantic-layer REST apply from manifest relationship logic plus registered Data Cloud objects'
    )
    stillSemiAutomated = @(
        'Workspace selection still needs an explicit selector when multiple workspaces are visible and no stable routing criteria are saved.'
    )
    blockedByOrgSetupOrPermissions = @(
        'Data Cloud connector creation still depends on org setup and permissions outside this repo.',
        'Dedicated Data Cloud alias authorization still has to succeed with cdp_ingest_api scope.'
    )
    blockedByExternalPlatformLimitations = @(
        'Connector-specific ingest route semantics are still connector and org dependent, so generic object lookup fallback remains part of the resilient upload path.'
    )
}

Write-JsonFile -Path $resolvedOutputPath -Value ([pscustomobject]$state)
Write-Host ("Wrote authenticated-to-SDM readiness state to '{0}'." -f $resolvedOutputPath) -ForegroundColor Green

[pscustomobject]$state | ConvertTo-Json -Depth 20
