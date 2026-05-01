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

function ConvertTo-DataCloudSlug {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    $slug = $Value.ToLowerInvariant() -replace '[^a-z0-9]+', '-'
    return $slug.Trim('-')
}

function Get-CommandCenterRelativePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $resolvedPath = [System.IO.Path]::GetFullPath($Path)
    $root = (Get-CommandCenterRoot).TrimEnd('\')
    if ($resolvedPath.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $resolvedPath.Substring($root.Length).TrimStart('\') -replace '\\', '/'
    }

    return $resolvedPath
}

function Resolve-DataCloudRegistryPathValue {
    param(
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ''
    }

    return Get-CommandCenterRelativePath -Path $Value
}

function Resolve-DataCloudRegistryPathForComparison {
    param(
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ''
    }

    try {
        if ([System.IO.Path]::IsPathRooted($Value)) {
            return [System.IO.Path]::GetFullPath($Value)
        }

        return [System.IO.Path]::GetFullPath((Resolve-CommandCenterPath $Value))
    } catch {
        return $Value
    }
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

    $sfCommand = Get-RequiredCommandPath -Name 'sf' -Hint 'Install Salesforce CLI or run the bootstrap script.'

    $output = & $sfCommand org display --target-org $Alias --json 2>$null
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

function Get-SalesforceOrgAccessContext {
    param(
        [string]$Alias,
        [string]$LoginUrl
    )

    Import-CommandCenterEnv

    if (-not [string]::IsNullOrWhiteSpace($Alias)) {
        try {
            $cliSession = Get-SalesforceCliOrgSession -Alias $Alias
            return [pscustomobject]@{
                accessToken = $cliSession.accessToken
                instanceUrl = $cliSession.instanceUrl
                source = 'salesforce-cli-session'
            }
        } catch {
            $hasRefreshTokenFlow = (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_CLIENT_ID) -and -not [string]::IsNullOrWhiteSpace($env:DATACLOUD_REFRESH_TOKEN))
            if (-not $hasRefreshTokenFlow) {
                throw
            }
        }
    }

    if ([string]::IsNullOrWhiteSpace($env:DATACLOUD_CLIENT_ID) -or [string]::IsNullOrWhiteSpace($env:DATACLOUD_REFRESH_TOKEN)) {
        throw 'No usable Salesforce org auth configuration was found. Log into Salesforce CLI with the target alias or set DATACLOUD_CLIENT_ID and DATACLOUD_REFRESH_TOKEN for refresh-token auth.'
    }

    $normalizedLoginUrl = if ([string]::IsNullOrWhiteSpace($LoginUrl)) { 'https://login.salesforce.com' } else { Normalize-DataCloudUrl -Value $LoginUrl }
    $tokenRequestBody = @{
        grant_type = 'refresh_token'
        client_id = $env:DATACLOUD_CLIENT_ID
        refresh_token = $env:DATACLOUD_REFRESH_TOKEN
    }

    if (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_CLIENT_SECRET)) {
        $tokenRequestBody.client_secret = $env:DATACLOUD_CLIENT_SECRET
    }

    try {
        $salesforceResponse = Invoke-RestMethod -Method Post -Uri ('{0}/services/oauth2/token' -f $normalizedLoginUrl) -ContentType 'application/x-www-form-urlencoded' -Body (ConvertTo-FormUrlEncoded -Values $tokenRequestBody)
    } catch {
        throw (Get-DataCloudErrorMessage -ErrorRecord $_)
    }

    if ($null -eq $salesforceResponse -or [string]::IsNullOrWhiteSpace([string](Get-OptionalObjectPropertyValue -InputObject $salesforceResponse -PropertyName 'access_token')) -or [string]::IsNullOrWhiteSpace([string](Get-OptionalObjectPropertyValue -InputObject $salesforceResponse -PropertyName 'instance_url'))) {
        throw (Get-DataCloudUnexpectedResponseMessage -Operation 'Salesforce OAuth refresh-token exchange' -Response $salesforceResponse)
    }

    return [pscustomobject]@{
        accessToken = Get-OptionalObjectPropertyValue -InputObject $salesforceResponse -PropertyName 'access_token'
        instanceUrl = Normalize-DataCloudUrl -Value (Get-OptionalObjectPropertyValue -InputObject $salesforceResponse -PropertyName 'instance_url')
        source = 'salesforce-refresh-token'
    }
}

function Get-SalesforceOrgRegistryPath {
    return Resolve-CommandCenterPath 'notes/registries/salesforce-orgs.json'
}

function Get-SalesforceOrgRegistry {
    $registry = Read-JsonFile -Path (Get-SalesforceOrgRegistryPath)
    if ($null -eq $registry) {
        return [pscustomobject]@{
            defaultAlias = ''
            orgs = @()
        }
    }

    if ($null -eq $registry.orgs) {
        $registry | Add-Member -NotePropertyName 'orgs' -NotePropertyValue @() -Force
    }

    if ($null -eq $registry.defaultAlias) {
        $registry | Add-Member -NotePropertyName 'defaultAlias' -NotePropertyValue '' -Force
    }

    return $registry
}

function Get-SalesforceOrgRegistryRecord {
    param(
        [string]$Alias,
        [string]$LoginUrl,
        [string]$InstanceUrl
    )

    $registry = Get-SalesforceOrgRegistry
    $orgs = @($registry.orgs)
    if ($orgs.Count -eq 0) {
        return $null
    }

    if (-not [string]::IsNullOrWhiteSpace($Alias)) {
        $aliasMatch = @($orgs | Where-Object { [string]$_.alias -eq $Alias } | Select-Object -First 1)
        if ($aliasMatch.Count -gt 0) {
            return $aliasMatch[0]
        }
    }

    $candidateUrls = @()
    foreach ($url in @($LoginUrl, $InstanceUrl)) {
        if (-not [string]::IsNullOrWhiteSpace($url)) {
            $candidateUrls += (Normalize-DataCloudUrl -Value $url)
        }
    }

    foreach ($candidateUrl in @($candidateUrls | Select-Object -Unique)) {
        $urlMatch = @($orgs | Where-Object { (Normalize-DataCloudUrl -Value ([string]$_.loginUrl)) -eq $candidateUrl } | Select-Object -First 1)
        if ($urlMatch.Count -gt 0) {
            return $urlMatch[0]
        }
    }

    return $null
}

function Get-DataCloudRegistryPath {
    return Resolve-CommandCenterPath 'notes/registries/data-cloud-targets.json'
}

function Get-DataCloudIngestApiConnectors {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InstanceUrl,
        [Parameter(Mandatory = $true)]
        [string]$AccessToken
    )

    $uri = '{0}/services/data/v62.0/ssot/connections?connectorType=IngestApi&limit=200' -f $InstanceUrl.TrimEnd('/')
    $headers = @{ Authorization = 'Bearer {0}' -f $AccessToken }

    try {
        $response = Invoke-RestMethod -Method Get -Uri $uri -Headers $headers
    } catch {
        throw (Get-DataCloudErrorMessage -ErrorRecord $_)
    }

    return @($response.connections)
}

function Resolve-DataCloudSourceNamePreference {
    param(
        [string]$PreferredSourceName,
        [string]$SalesforceAlias,
        [string]$LoginUrl,
        [string]$InstanceUrl,
        [string]$AccessToken,
        [object]$RegistrationHints,
        [object]$DatasetDefaults,
        [switch]$AllowConnectorDiscovery,
        [switch]$AllowDatasetFallback = $true
    )

    if (-not [string]::IsNullOrWhiteSpace($PreferredSourceName)) {
        return [pscustomobject]@{
            SourceName = $PreferredSourceName
            ResolutionSource = 'explicit'
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_SOURCE_NAME)) {
        return [pscustomobject]@{
            SourceName = [string]$env:DATACLOUD_SOURCE_NAME
            ResolutionSource = 'env:DATACLOUD_SOURCE_NAME'
        }
    }

    $orgRecord = Get-SalesforceOrgRegistryRecord -Alias $SalesforceAlias -LoginUrl $LoginUrl -InstanceUrl $InstanceUrl
    if ($null -ne $orgRecord) {
        $orgSourceName = [string](Get-OptionalObjectPropertyValue -InputObject $orgRecord -PropertyName 'dataCloudSourceName')
        if (-not [string]::IsNullOrWhiteSpace($orgSourceName)) {
            return [pscustomobject]@{
                SourceName = $orgSourceName
                ResolutionSource = 'salesforce-org-registry'
            }
        }
    }

    $hintSourceName = [string](Get-OptionalObjectPropertyValue -InputObject $RegistrationHints -PropertyName 'SourceName')
    if (-not [string]::IsNullOrWhiteSpace($hintSourceName)) {
        return [pscustomobject]@{
            SourceName = $hintSourceName
            ResolutionSource = 'manifest-registration-hints'
        }
    }

    if ($AllowConnectorDiscovery -and -not [string]::IsNullOrWhiteSpace($InstanceUrl) -and -not [string]::IsNullOrWhiteSpace($AccessToken)) {
        $connectors = @(Get-DataCloudIngestApiConnectors -InstanceUrl $InstanceUrl -AccessToken $AccessToken)
        $connectedConnectors = @($connectors | Where-Object { [string]$_.status -eq 'CONNECTED' })
        if ($connectedConnectors.Count -eq 1) {
            return [pscustomobject]@{
                SourceName = [string]$connectedConnectors[0].name
                ResolutionSource = 'org-connector-discovery'
                ConnectorNames = @($connectors | ForEach-Object { [string]$_.name })
            }
        }

        if ($connectors.Count -eq 1) {
            return [pscustomobject]@{
                SourceName = [string]$connectors[0].name
                ResolutionSource = 'org-connector-discovery'
                ConnectorNames = @($connectors | ForEach-Object { [string]$_.name })
            }
        }

        if ($connectedConnectors.Count -gt 1 -or $connectors.Count -gt 1) {
            return [pscustomobject]@{
                SourceName = ''
                ResolutionSource = 'ambiguous-org-connectors'
                ConnectorNames = @($(if ($connectedConnectors.Count -gt 0) { $connectedConnectors } else { $connectors }) | ForEach-Object { [string]$_.name })
            }
        }
    }

    if ($AllowDatasetFallback) {
        $datasetSourceName = [string](Get-OptionalObjectPropertyValue -InputObject $DatasetDefaults -PropertyName 'SourceName')
        if (-not [string]::IsNullOrWhiteSpace($datasetSourceName)) {
            return [pscustomobject]@{
                SourceName = $datasetSourceName
                ResolutionSource = 'dataset-derived-fallback'
            }
        }
    }

    return [pscustomobject]@{
        SourceName = ''
        ResolutionSource = 'unresolved'
    }
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

$script:DataCloudReservedFieldNames = @(
    'date_id',
    'location_id',
    'dat_account_currency',
    'dat_exchange_rate',
    'pacing_period',
    'pacing_end_date',
    'row_count',
    'version'
)

function Test-IsInvariantNumber {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    $parsedValue = 0.0
    return [double]::TryParse($Value, [System.Globalization.NumberStyles]::Float, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$parsedValue)
}

function Test-IsIsoDate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    $parsedValue = [datetime]::MinValue
    return [datetime]::TryParseExact($Value, 'yyyy-MM-dd', [System.Globalization.CultureInfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::None, [ref]$parsedValue)
}

function Test-IsIsoDateTime {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    $formats = @(
        'yyyy-MM-ddTHH:mm:ssZ',
        'yyyy-MM-ddTHH:mm:ss.fffZ',
        'yyyy-MM-ddTHH:mm:ss.fffffffZ'
    )

    $parsedValue = [datetimeoffset]::MinValue
    return [datetimeoffset]::TryParseExact($Value, $formats, [System.Globalization.CultureInfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::AssumeUniversal, [ref]$parsedValue)
}

function Test-IsPhoneLike {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    if ($Value -notmatch '^[+()0-9 .-]+$') {
        return $false
    }

    $digitsOnly = ($Value -replace '[^0-9]', '')
    return $digitsOnly.Length -ge 7
}

function Get-NonEmptyValues {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$Values
    )

    return @(
        $Values |
            Where-Object { $null -ne $_ -and -not [string]::IsNullOrWhiteSpace([string]$_) } |
            ForEach-Object { ([string]$_).Trim() }
    )
}

function Assert-ValidDataCloudName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$Kind
    )

    if ([string]::IsNullOrWhiteSpace($Name)) {
        throw "$Kind name cannot be empty."
    }

    if ($Name.Length -gt 80) {
        throw "$Kind name '$Name' exceeds the 80 character limit."
    }

    if ($Name -notmatch '^[A-Za-z0-9_.-]+$') {
        throw "$Kind name '$Name' contains unsupported characters."
    }
}

function Assert-ValidFieldName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FieldName,
        [string]$ContextLabel = 'Field'
    )

    Assert-ValidDataCloudName -Name $FieldName -Kind $ContextLabel

    if ($FieldName -match '__') {
        throw "$ContextLabel name '$FieldName' cannot contain '__'."
    }

    if ($script:DataCloudReservedFieldNames -contains $FieldName.ToLowerInvariant()) {
        throw "$ContextLabel name '$FieldName' is a reserved Data Cloud field name."
    }
}

function Assert-NoCaseInsensitiveDuplicates {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Values,
        [Parameter(Mandatory = $true)]
        [string]$Kind
    )

    $duplicates = @(
        $Values |
            Group-Object { $_.ToLowerInvariant() } |
            Where-Object { $_.Count -gt 1 }
    )

    if ($duplicates.Count -gt 0) {
        $duplicateNames = @($duplicates | ForEach-Object { $_.Group[0] }) -join ', '
        throw "Duplicate $Kind names are not allowed: $duplicateNames"
    }
}

function New-MetadataSafeName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value,
        [int]$MaxLength = 80
    )

    $normalized = ($Value -replace '[^A-Za-z0-9_]', '_').Trim('_')
    if ([string]::IsNullOrWhiteSpace($normalized)) {
        throw "Unable to derive a metadata-safe name from '$Value'."
    }

    if ($normalized.Length -gt $MaxLength) {
        return $normalized.Substring(0, $MaxLength)
    }

    return $normalized
}

function Get-InferredSchemaType {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$Values
    )

    $nonEmptyValues = Get-NonEmptyValues -Values $Values
    if ($nonEmptyValues.Count -eq 0) {
        return [ordered]@{ type = 'string' }
    }

    if (@($nonEmptyValues | Where-Object { $_ -notmatch '^(?i:true|false)$' }).Count -eq 0) {
        return [ordered]@{ type = 'boolean' }
    }

    if (@($nonEmptyValues | Where-Object { -not (Test-IsIsoDateTime -Value $_) }).Count -eq 0) {
        return [ordered]@{ type = 'string'; format = 'date-time' }
    }

    if (@($nonEmptyValues | Where-Object { -not (Test-IsIsoDate -Value $_) }).Count -eq 0) {
        return [ordered]@{ type = 'string'; format = 'date' }
    }

    if (@($nonEmptyValues | Where-Object { $_ -notmatch '^[^\s@]+@[^\s@]+\.[^\s@]+$' }).Count -eq 0) {
        return [ordered]@{ type = 'string'; format = 'email' }
    }

    if (@($nonEmptyValues | Where-Object { -not (Test-IsPhoneLike -Value $_) }).Count -eq 0) {
        return [ordered]@{ type = 'string'; format = 'phone' }
    }

    if (@($nonEmptyValues | Where-Object { $_ -notmatch '^(?i)https?://\S+$' }).Count -eq 0) {
        return [ordered]@{ type = 'string'; format = 'url' }
    }

    if (@($nonEmptyValues | Where-Object { $_ -notmatch '^-?[0-9]+(?:\.[0-9]+)?%$' }).Count -eq 0) {
        return [ordered]@{ type = 'string'; format = 'percent' }
    }

    if (@($nonEmptyValues | Where-Object { -not (Test-IsInvariantNumber -Value $_) }).Count -eq 0) {
        return [ordered]@{ type = 'number' }
    }

    return [ordered]@{ type = 'string' }
}

function Get-FieldDataTypeCode {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$Values
    )

    $nonEmptyValues = Get-NonEmptyValues -Values $Values
    if ($nonEmptyValues.Count -eq 0) {
        return 'S'
    }

    if (@($nonEmptyValues | Where-Object { $_ -notmatch '^(?i:true|false)$' }).Count -eq 0) {
        return 'B'
    }

    if (@($nonEmptyValues | Where-Object { -not (Test-IsIsoDateTime -Value $_) }).Count -eq 0) {
        return 'F'
    }

    if (@($nonEmptyValues | Where-Object { -not (Test-IsIsoDate -Value $_) }).Count -eq 0) {
        return 'F'
    }

    if (@($nonEmptyValues | Where-Object { -not (Test-IsInvariantNumber -Value $_) }).Count -eq 0) {
        return 'N'
    }

    return 'S'
}

function Get-CustomFieldMetadataType {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$Values
    )

    $nonEmptyValues = Get-NonEmptyValues -Values $Values
    if ($nonEmptyValues.Count -eq 0) {
        return 'Text'
    }

    if (@($nonEmptyValues | Where-Object { $_ -notmatch '^(?i:true|false)$' }).Count -eq 0) {
        return 'Checkbox'
    }

    if (@($nonEmptyValues | Where-Object { -not (Test-IsIsoDateTime -Value $_) }).Count -eq 0) {
        return 'DateTime'
    }

    if (@($nonEmptyValues | Where-Object { -not (Test-IsIsoDate -Value $_) }).Count -eq 0) {
        return 'Date'
    }

    if (@($nonEmptyValues | Where-Object { -not (Test-IsInvariantNumber -Value $_) }).Count -eq 0) {
        return 'Number'
    }

    return 'Text'
}

function Get-DataCloudCsvProfile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CsvPath,
        [int]$SampleRows = 200,
        [switch]$AllowHeaderOnly,
        [string]$ContextLabel = 'CSV'
    )

    $resolvedCsvPath = (Resolve-Path $CsvPath).Path
    $fileInfo = Get-Item -Path $resolvedCsvPath
    if ($fileInfo.Length -eq 0) {
        throw "$ContextLabel '$resolvedCsvPath' is empty."
    }

    $headerLine = Get-Content -Path $resolvedCsvPath -TotalCount 1
    if ([string]::IsNullOrWhiteSpace($headerLine)) {
        throw "$ContextLabel '$resolvedCsvPath' does not contain a header row."
    }

    $headers = @($headerLine.Split(',') | ForEach-Object { $_.Trim().Trim('"') })
    if ($headers.Count -eq 0) {
        throw "$ContextLabel '$resolvedCsvPath' does not contain any headers."
    }

    $blankHeaders = New-Object System.Collections.Generic.List[string]
    $sanitizedHeaders = New-Object System.Collections.Generic.List[string]
    for ($index = 0; $index -lt $headers.Count; $index++) {
        if ([string]::IsNullOrWhiteSpace($headers[$index])) {
            $blankHeaders.Add([string]($index + 1)) | Out-Null
            continue
        }

        $safeHeaderName = New-MetadataSafeName -Value $headers[$index] -MaxLength 37
        Assert-ValidFieldName -FieldName $safeHeaderName -ContextLabel 'Header API'
        $sanitizedHeaders.Add($safeHeaderName) | Out-Null
    }

    if ($blankHeaders.Count -gt 0) {
        throw "$ContextLabel '$resolvedCsvPath' contains blank headers at positions $($blankHeaders -join ', ')."
    }

    Assert-NoCaseInsensitiveDuplicates -Values $headers -Kind 'header'
    Assert-NoCaseInsensitiveDuplicates -Values $sanitizedHeaders.ToArray() -Kind 'header API'

    $sampleRowsData = @(Import-Csv -Path $resolvedCsvPath | Select-Object -First $SampleRows)
    if ($sampleRowsData.Count -eq 0 -and -not $AllowHeaderOnly) {
        throw "$ContextLabel '$resolvedCsvPath' does not contain any data rows."
    }

    if ($sampleRowsData.Count -gt 0) {
        $importHeaders = @($sampleRowsData[0].PSObject.Properties.Name)
        if ($importHeaders.Count -ne $headers.Count) {
            throw "$ContextLabel '$resolvedCsvPath' header parsing is inconsistent between the raw header row and Import-Csv."
        }

        for ($index = 0; $index -lt $headers.Count; $index++) {
            if ($importHeaders[$index] -cne $headers[$index]) {
                throw "$ContextLabel '$resolvedCsvPath' header parsing is inconsistent for column '$($headers[$index])'."
            }
        }
    }

    $lineCount = (Get-Content -Path $resolvedCsvPath | Measure-Object -Line).Lines

    return [pscustomobject]@{
        csvPath = $resolvedCsvPath
        sizeBytes = $fileInfo.Length
        lineCount = $lineCount
        estimatedDataRows = [Math]::Max($lineCount - 1, 0)
        headers = $headers
        sampleRows = $sampleRowsData
    }
}

function Get-DataCloudCsvFieldProfiles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CsvPath,
        [int]$SampleRows = 200,
        [switch]$AllowHeaderOnly,
        [string]$ContextLabel = 'CSV'
    )

    $csvProfile = Get-DataCloudCsvProfile -CsvPath $CsvPath -SampleRows $SampleRows -AllowHeaderOnly:$AllowHeaderOnly -ContextLabel $ContextLabel
    $fieldDefinitions = New-Object System.Collections.Generic.List[object]
    $fieldApiNames = New-Object System.Collections.Generic.List[string]

    foreach ($fieldName in @($csvProfile.headers)) {
        $fieldApiName = New-MetadataSafeName -Value $fieldName -MaxLength 37
        $fieldValues = @($csvProfile.sampleRows | ForEach-Object { $_.$fieldName })

        $fieldDefinitions.Add([pscustomobject]@{
            name = $fieldName
            apiName = $fieldApiName
            schema = Get-InferredSchemaType -Values $fieldValues
            dataType = Get-FieldDataTypeCode -Values $fieldValues
            customFieldType = Get-CustomFieldMetadataType -Values $fieldValues
        }) | Out-Null
        $fieldApiNames.Add($fieldApiName) | Out-Null
    }

    Assert-NoCaseInsensitiveDuplicates -Values $fieldApiNames.ToArray() -Kind 'field API'

    return [pscustomobject]@{
        csvPath = $csvProfile.csvPath
        sizeBytes = $csvProfile.sizeBytes
        lineCount = $csvProfile.lineCount
        estimatedDataRows = $csvProfile.estimatedDataRows
        headers = $csvProfile.headers
        sampleRows = $csvProfile.sampleRows
        fieldCount = $fieldDefinitions.Count
        fields = $fieldDefinitions.ToArray()
    }
}
function ConvertTo-DataCloudCompatibleManifest {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Manifest
    )

    function Get-ManifestJoinGraphEntries {
        param(
            [Parameter(Mandatory = $true)]
            [object]$JoinGraphValue
        )

        $entries = New-Object System.Collections.Generic.List[object]
        foreach ($property in @($JoinGraphValue.PSObject.Properties)) {
            if ($null -eq $property -or [string]::IsNullOrWhiteSpace([string]$property.Name) -or $null -eq $property.Value) {
                continue
            }

            $primaryKeyValue = Get-OptionalObjectPropertyValue -InputObject $property.Value -PropertyName 'primaryKey'
            $foreignKeysValue = Get-OptionalObjectPropertyValue -InputObject $property.Value -PropertyName 'foreignKeys'
            $entries.Add([pscustomobject]@{
                tableName = [string]$property.Name
                primaryKey = @($primaryKeyValue)
                foreignKeys = @($foreignKeysValue)
            }) | Out-Null
        }

        return @($entries.ToArray())
    }

    function Get-ManifestRootTableName {
        param(
            [Parameter(Mandatory = $true)]
            [object[]]$JoinGraphEntries,
            [object]$PublishContract
        )

        if ($null -ne $PublishContract) {
            $rootTableProperty = $PublishContract.PSObject.Properties['rootTable']
            if ($null -ne $rootTableProperty -and -not [string]::IsNullOrWhiteSpace([string]$rootTableProperty.Value)) {
                return [string]$rootTableProperty.Value
            }
        }

        $factTable = @($JoinGraphEntries | Where-Object { [string]$_.tableName -like 'fact_*' } | Select-Object -First 1)
        if ($factTable.Count -gt 0) {
            return [string]$factTable[0].tableName
        }

        $rankedByForeignKeys = @(
            $JoinGraphEntries |
                Sort-Object -Property @{ Expression = { @($_.foreignKeys).Count } ; Descending = $true }, @{ Expression = { [string]$_.tableName } }
        )
        if ($rankedByForeignKeys.Count -gt 0) {
            return [string]$rankedByForeignKeys[0].tableName
        }

        return ''
    }

    $filesProperty = $Manifest.PSObject.Properties['files']
    if ($null -ne $filesProperty -and $null -ne $filesProperty.Value -and @($filesProperty.Value).Count -gt 0) {
        $firstFileEntry = @($filesProperty.Value | Select-Object -First 1)
        if ($firstFileEntry.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace([string](Get-OptionalObjectPropertyValue -InputObject $firstFileEntry[0] -PropertyName 'tableName')) -and -not [string]::IsNullOrWhiteSpace([string](Get-OptionalObjectPropertyValue -InputObject $firstFileEntry[0] -PropertyName 'fileName'))) {
            return $Manifest
        }
    }

    $publishContract = Get-OptionalObjectPropertyValue -InputObject $Manifest -PropertyName 'publishContract'
    if ($publishContract -is [string] -and [string]::IsNullOrWhiteSpace([string]$publishContract)) {
        $publishContract = $null
    }

    $topLevelTables = @(
        foreach ($table in @(Get-OptionalObjectPropertyValue -InputObject $Manifest -PropertyName 'tables')) {
            if ($null -ne $table -and -not ($table -is [string] -and [string]::IsNullOrWhiteSpace($table))) {
                $table
            }
        }
    )

    $publishContractTables = if ($null -ne $publishContract) {
        @(Get-OptionalObjectPropertyValue -InputObject $publishContract -PropertyName 'tables')
    } else {
        @()
    }

    $tables = @(
        foreach ($table in $publishContractTables) {
            if ($null -ne $table -and -not ($table -is [string] -and [string]::IsNullOrWhiteSpace($table))) {
                $table
            }
        }
    )
    if ($tables.Count -eq 0 -and $topLevelTables.Count -gt 0) {
        $tables = @($topLevelTables)
    }
    if ($tables.Count -eq 0) {
        $joinGraphProperty = $Manifest.PSObject.Properties['joinGraph']
        $joinGraphEntries = if ($null -ne $joinGraphProperty -and $null -ne $joinGraphProperty.Value) { @(Get-ManifestJoinGraphEntries -JoinGraphValue $joinGraphProperty.Value) } else { @() }
        if ($joinGraphEntries.Count -eq 0) {
            return $Manifest
        }

        $files = @(
            foreach ($entry in $joinGraphEntries) {
                [pscustomobject]@{
                    tableName = [string]$entry.tableName
                    fileName = '{0}.csv' -f [string]$entry.tableName
                }
            }
        )

        $relationships = @(
            foreach ($entry in $joinGraphEntries) {
                foreach ($foreignKey in @($entry.foreignKeys)) {
                    $referenceValue = [string](Get-OptionalObjectPropertyValue -InputObject $foreignKey -PropertyName 'references')
                    if ([string]::IsNullOrWhiteSpace($referenceValue) -or -not $referenceValue.Contains('.')) {
                        continue
                    }

                    $referenceParts = $referenceValue.Split('.', 2)
                    if ($referenceParts.Count -ne 2 -or [string]::IsNullOrWhiteSpace($referenceParts[0]) -or [string]::IsNullOrWhiteSpace($referenceParts[1])) {
                        continue
                    }

                    [pscustomobject]@{
                        sourceTable = [string]$entry.tableName
                        sourceField = [string](Get-OptionalObjectPropertyValue -InputObject $foreignKey -PropertyName 'field')
                        targetTable = [string]$referenceParts[0]
                        targetField = [string]$referenceParts[1]
                        direction = 'many_to_one'
                        required = $true
                    }
                }
            }
        )

        $rootTableName = Get-ManifestRootTableName -JoinGraphEntries $joinGraphEntries -PublishContract $publishContract
        $datasetNameProperty = $Manifest.PSObject.Properties['datasetName']
        $datasetIdentityProperty = $Manifest.PSObject.Properties['datasetIdentity']
        if (($null -eq $datasetNameProperty -or [string]::IsNullOrWhiteSpace([string]$datasetNameProperty.Value)) -and $null -ne $datasetIdentityProperty -and -not [string]::IsNullOrWhiteSpace([string]$datasetIdentityProperty.Value)) {
            $Manifest | Add-Member -NotePropertyName 'datasetName' -NotePropertyValue ([string]$datasetIdentityProperty.Value) -Force
        }

        $Manifest | Add-Member -NotePropertyName 'files' -NotePropertyValue $files -Force
        $Manifest | Add-Member -NotePropertyName 'joinGraph' -NotePropertyValue $joinGraphEntries -Force

        if ($null -eq $publishContract) {
            $publishContract = [pscustomobject]@{}
            $Manifest | Add-Member -NotePropertyName 'publishContract' -NotePropertyValue $publishContract -Force
        }

        if (-not [string]::IsNullOrWhiteSpace($rootTableName)) {
            $publishContract | Add-Member -NotePropertyName 'rootTable' -NotePropertyValue $rootTableName -Force
        }

        $relationshipsProperty = $publishContract.PSObject.Properties['relationships']
        if (($null -eq $relationshipsProperty -or $null -eq $relationshipsProperty.Value -or @($relationshipsProperty.Value).Count -eq 0) -and $relationships.Count -gt 0) {
            $publishContract | Add-Member -NotePropertyName 'relationships' -NotePropertyValue $relationships -Force
        }

        return $Manifest
    }

    $tableNameById = @{}
    foreach ($table in $tables) {
        $tableId = [string](Get-OptionalObjectPropertyValue -InputObject $table -PropertyName 'id')
        $tableName = [string](Get-OptionalObjectPropertyValue -InputObject $table -PropertyName 'tableName')
        if (-not [string]::IsNullOrWhiteSpace($tableId) -and -not [string]::IsNullOrWhiteSpace($tableName)) {
            $tableNameById[$tableId] = $tableName
        }
        if (-not [string]::IsNullOrWhiteSpace($tableName)) {
            $tableNameById[$tableName] = $tableName
        }
    }

    $files = @(
        foreach ($table in $tables) {
            $tableName = [string](Get-OptionalObjectPropertyValue -InputObject $table -PropertyName 'tableName')
            $fileName = [string](Get-OptionalObjectPropertyValue -InputObject $table -PropertyName 'fileName')
            if ([string]::IsNullOrWhiteSpace($fileName) -and -not [string]::IsNullOrWhiteSpace($tableName)) {
                $fileName = '{0}.csv' -f $tableName
            }

            [pscustomobject]@{
                tableName = $tableName
                fileName = $fileName
            }
        }
    )

    $joinGraph = @(
        foreach ($table in $tables) {
            [pscustomobject]@{
                tableName = [string](Get-OptionalObjectPropertyValue -InputObject $table -PropertyName 'tableName')
                primaryKey = @((Get-OptionalObjectPropertyValue -InputObject $table -PropertyName 'primaryKey'))
            }
        }
    )

    $publishContractJoinPaths = if ($null -ne $publishContract) {
        @(Get-OptionalObjectPropertyValue -InputObject $publishContract -PropertyName 'joinPaths')
    } else {
        @()
    }

    $joinPaths = @(
        foreach ($joinPath in $publishContractJoinPaths) {
            if ($null -ne $joinPath -and -not ($joinPath -is [string] -and [string]::IsNullOrWhiteSpace($joinPath))) {
                $joinPath
            }
        }
    )
    if ($joinPaths.Count -eq 0) {
        $joinPaths = @(
            foreach ($joinPath in @(Get-OptionalObjectPropertyValue -InputObject $Manifest -PropertyName 'joinPaths')) {
                if ($null -ne $joinPath -and -not ($joinPath -is [string] -and [string]::IsNullOrWhiteSpace($joinPath))) {
                    $joinPath
                }
            }
        )
    }

    $relationships = @(
        foreach ($joinPath in $joinPaths) {
            $sourceTableKey = [string](Get-OptionalObjectPropertyValue -InputObject $joinPath -PropertyName 'sourceTableId')
            if ([string]::IsNullOrWhiteSpace($sourceTableKey)) {
                $sourceTableKey = [string](Get-OptionalObjectPropertyValue -InputObject $joinPath -PropertyName 'fromTable')
            }

            $targetTableKey = [string](Get-OptionalObjectPropertyValue -InputObject $joinPath -PropertyName 'targetTableId')
            if ([string]::IsNullOrWhiteSpace($targetTableKey)) {
                $targetTableKey = [string](Get-OptionalObjectPropertyValue -InputObject $joinPath -PropertyName 'toTable')
            }

            $sourceTableName = if ($tableNameById.ContainsKey($sourceTableKey)) { $tableNameById[$sourceTableKey] } else { $sourceTableKey }
            $targetTableName = if ($tableNameById.ContainsKey($targetTableKey)) { $tableNameById[$targetTableKey] } else { $targetTableKey }
            if ([string]::IsNullOrWhiteSpace($sourceTableName) -or [string]::IsNullOrWhiteSpace($targetTableName)) {
                continue
            }

            $sourceFieldValue = [string](Get-OptionalObjectPropertyValue -InputObject $joinPath -PropertyName 'sourceField')
            if ([string]::IsNullOrWhiteSpace($sourceFieldValue)) {
                $sourceFieldValue = [string](Get-OptionalObjectPropertyValue -InputObject $joinPath -PropertyName 'fromField')
            }

            $targetFieldValue = [string](Get-OptionalObjectPropertyValue -InputObject $joinPath -PropertyName 'targetField')
            if ([string]::IsNullOrWhiteSpace($targetFieldValue)) {
                $targetFieldValue = [string](Get-OptionalObjectPropertyValue -InputObject $joinPath -PropertyName 'toField')
            }

            [pscustomobject]@{
                sourceTable = $sourceTableName
                sourceField = $sourceFieldValue
                targetTable = $targetTableName
                targetField = $targetFieldValue
                direction = 'many_to_one'
                required = $true
            }
        }
    )

    $rootTableName = ''
    if ($null -ne $publishContract) {
        $rootTableValue = [string](Get-OptionalObjectPropertyValue -InputObject $publishContract -PropertyName 'rootTable')
        $rootTableIdValue = [string](Get-OptionalObjectPropertyValue -InputObject $publishContract -PropertyName 'rootTableId')
        if (-not [string]::IsNullOrWhiteSpace($rootTableValue)) {
            $rootTableName = $rootTableValue
        } elseif (-not [string]::IsNullOrWhiteSpace($rootTableIdValue)) {
            $rootTableKey = $rootTableIdValue
            $rootTableName = if ($tableNameById.ContainsKey($rootTableKey)) { $tableNameById[$rootTableKey] } else { $rootTableKey }
        }
    }
    if ([string]::IsNullOrWhiteSpace($rootTableName)) {
        $factTable = @($tables | Where-Object { [string](Get-OptionalObjectPropertyValue -InputObject $_ -PropertyName 'tableRole') -eq 'fact' } | Select-Object -First 1)
        if ($factTable.Count -gt 0) {
            $rootTableName = [string](Get-OptionalObjectPropertyValue -InputObject $factTable[0] -PropertyName 'tableName')
        }
    }
    if ([string]::IsNullOrWhiteSpace($rootTableName) -and $files.Count -gt 0) {
        $rootTableName = [string]$files[0].tableName
    }

    $datasetNameProperty = $Manifest.PSObject.Properties['datasetName']
    $datasetIdentityProperty = $Manifest.PSObject.Properties['datasetIdentity']
    if (($null -eq $datasetNameProperty -or [string]::IsNullOrWhiteSpace([string]$datasetNameProperty.Value)) -and $null -ne $datasetIdentityProperty -and -not [string]::IsNullOrWhiteSpace([string]$datasetIdentityProperty.Value)) {
        $Manifest | Add-Member -NotePropertyName 'datasetName' -NotePropertyValue ([string]$datasetIdentityProperty.Value) -Force
    }

    $Manifest | Add-Member -NotePropertyName 'files' -NotePropertyValue $files -Force
    $Manifest | Add-Member -NotePropertyName 'joinGraph' -NotePropertyValue $joinGraph -Force

    if ($null -eq $publishContract) {
        $publishContract = [pscustomobject]@{}
        $Manifest | Add-Member -NotePropertyName 'publishContract' -NotePropertyValue $publishContract -Force
    }

    if (-not [string]::IsNullOrWhiteSpace($rootTableName)) {
        $publishContract | Add-Member -NotePropertyName 'rootTable' -NotePropertyValue $rootTableName -Force
    }

    $relationshipsProperty = if ($null -ne $publishContract) { $publishContract.PSObject.Properties['relationships'] } else { $null }
    if (($null -eq $relationshipsProperty -or $null -eq $relationshipsProperty.Value -or @($relationshipsProperty.Value).Count -eq 0) -and $relationships.Count -gt 0) {
        $publishContract | Add-Member -NotePropertyName 'relationships' -NotePropertyValue $relationships -Force
    }

    return $Manifest
}

function Get-DataCloudManifestInfo {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ManifestPath
    )

    $resolvedManifestPath = (Resolve-Path $ManifestPath).Path
    $manifest = Get-Content -Path $resolvedManifestPath -Raw | ConvertFrom-Json
    $manifest = ConvertTo-DataCloudCompatibleManifest -Manifest $manifest

    if ($null -eq $manifest.files -or @($manifest.files).Count -eq 0) {
        throw "Manifest '$resolvedManifestPath' does not define any files."
    }

    return [pscustomobject]@{
        Path = $resolvedManifestPath
        RelativePath = Resolve-DataCloudRegistryPathValue -Value $resolvedManifestPath
        Directory = Split-Path -Parent $resolvedManifestPath
        Content = $manifest
    }
}

function Get-DataCloudManifestDefaults {
    param(
        [Parameter(Mandatory = $true)]
        [object]$ManifestInfo
    )

    $manifest = $ManifestInfo.Content
    $manifestFileStem = [System.IO.Path]::GetFileNameWithoutExtension($ManifestInfo.Path)
    $manifestDirectoryName = Split-Path -Path $ManifestInfo.Directory -Leaf
    $datasetName = [string](Get-OptionalObjectPropertyValue -InputObject $manifest -PropertyName 'datasetName')
    $datasetIdentity = [string](Get-OptionalObjectPropertyValue -InputObject $manifest -PropertyName 'datasetIdentity')

    $datasetLabel = if (-not [string]::IsNullOrWhiteSpace($datasetName)) {
        $datasetName
    } elseif (-not [string]::IsNullOrWhiteSpace($datasetIdentity)) {
        $datasetIdentity
    } elseif (-not [string]::IsNullOrWhiteSpace($manifestDirectoryName)) {
        $manifestDirectoryName
    } else {
        $manifestFileStem
    }

    $slugSeed = if (-not [string]::IsNullOrWhiteSpace($manifestFileStem) -and $manifestFileStem -ne 'manifest') {
        $manifestFileStem
    } elseif (-not [string]::IsNullOrWhiteSpace($manifestDirectoryName)) {
        $manifestDirectoryName
    } else {
        $datasetLabel
    }

    $datasetKey = ConvertTo-DataCloudSlug -Value $slugSeed
    if ([string]::IsNullOrWhiteSpace($datasetKey)) {
        $datasetKey = 'manifest-dataset'
    }

    return [pscustomobject]@{
        DatasetLabel = $datasetLabel
        DatasetKey = $datasetKey
        TargetKeyPrefix = $datasetKey
        ObjectNamePrefix = ($datasetKey -replace '-', '_')
        SourceName = 'command_center_ingest_api'
        ManifestPath = $ManifestInfo.RelativePath
        NotesPrefix = 'Dataset config from {0}' -f $ManifestInfo.RelativePath
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

function Get-DataCloudManifestRegistrationHints {
    param(
        [Parameter(Mandatory = $true)]
        [object]$ManifestInfo,
        [Parameter(Mandatory = $true)]
        [object]$Registry,
        [Parameter(Mandatory = $true)]
        [string]$RootTableName,
        [string]$TargetKeySeparator = '-',
        [string]$ObjectNameSeparator = '_'
    )

    $manifestPath = Resolve-DataCloudRegistryPathForComparison -Value $ManifestInfo.Path
    $matchingTargets = @(
        @($Registry.targets) | Where-Object {
            $candidateSchemaPath = Resolve-DataCloudRegistryPathForComparison -Value ([string](Get-OptionalObjectPropertyValue -InputObject $_ -PropertyName 'schemaPath'))
            $candidateManifestPath = Resolve-DataCloudRegistryPathForComparison -Value ([string](Get-OptionalObjectPropertyValue -InputObject $_ -PropertyName 'manifestPath'))
            ($candidateSchemaPath -eq $manifestPath) -or ($candidateManifestPath -eq $manifestPath)
        }
    )

    if ($matchingTargets.Count -eq 0) {
        return [pscustomobject]@{
            TargetKeyPrefix = ''
            SourceName = ''
            ObjectNamePrefix = ''
            Category = ''
            Notes = ''
            SalesforceAlias = ''
            TenantEndpoint = ''
        }
    }

    $rootTarget = @($matchingTargets | Where-Object { ([string](Get-OptionalObjectPropertyValue -InputObject $_ -PropertyName 'manifestTableName')) -eq $RootTableName } | Select-Object -First 1)
    if ($rootTarget.Count -eq 0) {
        $rootTarget = @(
            $matchingTargets | Where-Object {
                $candidateKey = [string](Get-OptionalObjectPropertyValue -InputObject $_ -PropertyName 'key')
                $candidateObjectName = [string](Get-OptionalObjectPropertyValue -InputObject $_ -PropertyName 'objectName')
                $candidateLabel = [string](Get-OptionalObjectPropertyValue -InputObject $_ -PropertyName 'dataStreamLabel')
                $candidateKey.EndsWith(('{0}{1}' -f $TargetKeySeparator, $RootTableName)) -or
                $candidateObjectName.EndsWith(('{0}{1}' -f $ObjectNameSeparator, $RootTableName)) -or
                $candidateLabel.EndsWith((' - {0}' -f $RootTableName))
            } | Select-Object -First 1
        )
    }

    if ($rootTarget.Count -eq 0) {
        $rootTarget = @($matchingTargets | Select-Object -First 1)
    }

    $rootTarget = $rootTarget[0]
    $explicitTargetKeyPrefix = [string](Get-OptionalObjectPropertyValue -InputObject $rootTarget -PropertyName 'targetKeyPrefix')
    $explicitObjectNamePrefix = [string](Get-OptionalObjectPropertyValue -InputObject $rootTarget -PropertyName 'objectNamePrefix')

    $inferredTargetKeyPrefix = ''
    if ([string]::IsNullOrWhiteSpace($explicitTargetKeyPrefix)) {
        $rootKey = [string](Get-OptionalObjectPropertyValue -InputObject $rootTarget -PropertyName 'key')
        $targetSuffix = '{0}{1}' -f $TargetKeySeparator, $RootTableName
        if ($rootKey.EndsWith($targetSuffix)) {
            $inferredTargetKeyPrefix = $rootKey.Substring(0, $rootKey.Length - $targetSuffix.Length)
        }
    }

    $inferredObjectNamePrefix = ''
    if ([string]::IsNullOrWhiteSpace($explicitObjectNamePrefix)) {
        $rootObjectName = [string](Get-OptionalObjectPropertyValue -InputObject $rootTarget -PropertyName 'objectName')
        $objectSuffix = '{0}{1}' -f $ObjectNameSeparator, $RootTableName
        if ($rootObjectName.EndsWith($objectSuffix)) {
            $inferredObjectNamePrefix = $rootObjectName.Substring(0, $rootObjectName.Length - $objectSuffix.Length)
        }
    }

    return [pscustomobject]@{
        TargetKeyPrefix = if (-not [string]::IsNullOrWhiteSpace($explicitTargetKeyPrefix)) { $explicitTargetKeyPrefix } else { $inferredTargetKeyPrefix }
        SourceName = [string](Get-OptionalObjectPropertyValue -InputObject $rootTarget -PropertyName 'sourceName')
        ObjectNamePrefix = if (-not [string]::IsNullOrWhiteSpace($explicitObjectNamePrefix)) { $explicitObjectNamePrefix } else { $inferredObjectNamePrefix }
        Category = [string](Get-OptionalObjectPropertyValue -InputObject $rootTarget -PropertyName 'category')
        Notes = [string](Get-OptionalObjectPropertyValue -InputObject $rootTarget -PropertyName 'notes')
        SalesforceAlias = [string](Get-OptionalObjectPropertyValue -InputObject $rootTarget -PropertyName 'salesforceAlias')
        TenantEndpoint = [string](Get-OptionalObjectPropertyValue -InputObject $rootTarget -PropertyName 'tenantEndpoint')
    }
}

function New-DataCloudManifestTargetDefinition {
    param(
        [Parameter(Mandatory = $true)]
        [object]$ManifestInfo,
        [Parameter(Mandatory = $true)]
        [string]$TableName,
        [Parameter(Mandatory = $true)]
        [string]$TargetKeyPrefix,
        [string]$TargetKeySeparator = '-',
        [Parameter(Mandatory = $true)]
        [string]$ObjectNamePrefix,
        [string]$ObjectNameSeparator = '_',
        [Parameter(Mandatory = $true)]
        [string]$SourceName,
        [string]$Category,
        [string]$Notes
    )

    $manifest = $ManifestInfo.Content
    $datasetDefaults = Get-DataCloudManifestDefaults -ManifestInfo $ManifestInfo
    $fileDefinition = @($manifest.files | Where-Object { [string]$_.tableName -eq $TableName } | Select-Object -First 1)
    if ($fileDefinition.Count -eq 0) {
        throw "Manifest '$($ManifestInfo.Path)' does not define a file for table '$TableName'."
    }

    $csvPath = Resolve-DataCloudManifestCsvPath -ManifestInfo $ManifestInfo -FileDefinition $fileDefinition[0]
    $relativeCsvPath = Resolve-DataCloudRegistryPathValue -Value $csvPath
    $resolvedCategory = if ([string]::IsNullOrWhiteSpace($Category)) { $datasetDefaults.DatasetLabel } else { $Category }
    $notesPrefix = if ([string]::IsNullOrWhiteSpace($Notes)) { $datasetDefaults.NotesPrefix } else { $Notes }

    return [pscustomobject]@{
        key = Resolve-DataCloudManifestTargetKey -TableName $TableName -TargetKeyPrefix $TargetKeyPrefix -TargetKeySeparator $TargetKeySeparator
        sourceName = $SourceName
        objectName = Resolve-DataCloudManifestObjectName -TableName $TableName -ObjectNamePrefix $ObjectNamePrefix -ObjectNameSeparator $ObjectNameSeparator
        dataStreamLabel = '{0} - {1}' -f $datasetDefaults.DatasetLabel, $TableName
        category = $resolvedCategory
        primaryKey = Get-DataCloudManifestPrimaryKey -Manifest $manifest -TableName $TableName
        schemaPath = $datasetDefaults.ManifestPath
        manifestPath = $datasetDefaults.ManifestPath
        csvPath = $relativeCsvPath
        datasetKey = $datasetDefaults.DatasetKey
        datasetLabel = $datasetDefaults.DatasetLabel
        manifestTableName = $TableName
        targetKeyPrefix = $TargetKeyPrefix
        objectNamePrefix = $ObjectNamePrefix
        notes = '{0}; table={1}; csv={2}' -f $notesPrefix, $TableName, $relativeCsvPath
    }
}

function Compare-DataCloudManifestTargetDefinition {
    param(
        [Parameter(Mandatory = $true)]
        [object]$ExistingTarget,
        [Parameter(Mandatory = $true)]
        [object]$ExpectedTarget
    )

    $fieldsToCompare = @(
        'sourceName',
        'objectName',
        'primaryKey',
        'schemaPath',
        'manifestPath',
        'csvPath',
        'datasetKey',
        'datasetLabel',
        'manifestTableName',
        'targetKeyPrefix',
        'objectNamePrefix'
    )

    $mismatches = @()
    foreach ($fieldName in $fieldsToCompare) {
        $actualValue = [string](Get-OptionalObjectPropertyValue -InputObject $ExistingTarget -PropertyName $fieldName)
        $expectedValue = [string](Get-OptionalObjectPropertyValue -InputObject $ExpectedTarget -PropertyName $fieldName)

        if ($fieldName -in @('schemaPath', 'manifestPath', 'csvPath')) {
            $actualValue = Resolve-DataCloudRegistryPathForComparison -Value $actualValue
            $expectedValue = Resolve-DataCloudRegistryPathForComparison -Value $expectedValue
        }

        if ($actualValue -ne $expectedValue) {
            $mismatches += [pscustomobject]@{
                field = $fieldName
                actual = [string](Get-OptionalObjectPropertyValue -InputObject $ExistingTarget -PropertyName $fieldName)
                expected = [string](Get-OptionalObjectPropertyValue -InputObject $ExpectedTarget -PropertyName $fieldName)
            }
        }
    }

    return $mismatches
}

function Get-OptionalObjectPropertyValue {
    param(
        [object]$InputObject,
        [Parameter(Mandatory = $true)]
        [string]$PropertyName
    )

    if ($null -eq $InputObject) {
        return ''
    }

    $property = $InputObject.PSObject.Properties[$PropertyName]
    if ($null -eq $property -or $null -eq $property.Value) {
        return ''
    }

    return $property.Value
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
        } elseif (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_SALESFORCE_ALIAS)) {
            $aliasMatchedTarget = @(
                $registry.targets |
                    Where-Object { [string](Get-OptionalObjectPropertyValue -InputObject $_ -PropertyName 'salesforceAlias') -eq $env:DATACLOUD_SALESFORCE_ALIAS } |
                    Select-Object -First 1
            )
            if ($aliasMatchedTarget.Count -gt 0) {
                $resolvedTargetKey = [string](Get-OptionalObjectPropertyValue -InputObject $aliasMatchedTarget[0] -PropertyName 'key')
            }
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

    $preferTargetValues = (-not [string]::IsNullOrWhiteSpace($resolvedTargetKey) -and $null -ne $target)

    return [pscustomobject]@{
        TargetKey = $resolvedTargetKey
        LoginUrl = if (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_LOGIN_URL)) { Normalize-DataCloudUrl -Value $env:DATACLOUD_LOGIN_URL } elseif (-not [string]::IsNullOrWhiteSpace((Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'loginUrl'))) { Normalize-DataCloudUrl -Value (Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'loginUrl') } elseif (-not [string]::IsNullOrWhiteSpace($env:SF_LOGIN_URL)) { Normalize-DataCloudUrl -Value $env:SF_LOGIN_URL } else { 'https://login.salesforce.com' }
        TenantEndpoint = if ($preferTargetValues -and -not [string]::IsNullOrWhiteSpace((Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'tenantEndpoint'))) { Normalize-DataCloudUrl -Value (Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'tenantEndpoint') } elseif (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_TENANT_ENDPOINT)) { Normalize-DataCloudUrl -Value $env:DATACLOUD_TENANT_ENDPOINT } elseif (-not [string]::IsNullOrWhiteSpace((Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'tenantEndpoint'))) { Normalize-DataCloudUrl -Value (Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'tenantEndpoint') } else { '' }
        SourceName = if ($preferTargetValues -and -not [string]::IsNullOrWhiteSpace((Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'sourceName'))) { Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'sourceName' } elseif (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_SOURCE_NAME)) { $env:DATACLOUD_SOURCE_NAME } else { Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'sourceName' }
        ObjectName = if ($preferTargetValues -and -not [string]::IsNullOrWhiteSpace((Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'objectName'))) { Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'objectName' } elseif (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_OBJECT_NAME)) { $env:DATACLOUD_OBJECT_NAME } else { Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'objectName' }
        ObjectEndpoint = if ($preferTargetValues -and -not [string]::IsNullOrWhiteSpace((Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'objectEndpoint'))) { Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'objectEndpoint' } elseif (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_OBJECT_ENDPOINT)) { $env:DATACLOUD_OBJECT_ENDPOINT } else { Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'objectEndpoint' }
        SalesforceAlias = if ($preferTargetValues -and -not [string]::IsNullOrWhiteSpace((Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'salesforceAlias'))) { Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'salesforceAlias' } elseif (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_SALESFORCE_ALIAS)) { $env:DATACLOUD_SALESFORCE_ALIAS } elseif (-not [string]::IsNullOrWhiteSpace((Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'salesforceAlias'))) { Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'salesforceAlias' } else { '' }
        DataStreamLabel = Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'dataStreamLabel'
        Category = Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'category'
        PrimaryKey = Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'primaryKey'
        RecordModifiedField = Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'recordModifiedField'
        SchemaPath = Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'schemaPath'
        Notes = Get-OptionalObjectPropertyValue -InputObject $target -PropertyName 'notes'
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
    $responseProperty = $ErrorRecord.Exception.PSObject.Properties['Response']
    $response = if ($null -ne $responseProperty) { $responseProperty.Value } else { $null }
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

function Get-DataCloudUnexpectedResponseMessage {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Operation,
        [Parameter(Mandatory = $true)]
        [object]$Response
    )

    $serializedResponse = ''
    try {
        $serializedResponse = $Response | ConvertTo-Json -Depth 10 -Compress
    } catch {
        $serializedResponse = [string]$Response
    }

    if ([string]::IsNullOrWhiteSpace($serializedResponse)) {
        return '{0} returned an unexpected empty response.' -f $Operation
    }

    return '{0} returned an unexpected response: {1}' -f $Operation, $serializedResponse
}

function Get-DataCloudTokenExchangeFailureMessage {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BaseMessage,
        [string]$SalesforceAlias,
        [string]$TokenSource
    )

    if ($BaseMessage -match 'invalid_scope' -and $TokenSource -eq 'salesforce-cli-session') {
        $aliasLabel = if ([string]::IsNullOrWhiteSpace($SalesforceAlias)) { '<unknown alias>' } else { $SalesforceAlias }
        return "The Salesforce CLI session for alias '$aliasLabel' cannot exchange into Data Cloud because the org returned invalid_scope. This alias does not currently carry a Data Cloud-capable OAuth grant. Use a dedicated Data Cloud alias authorized through CommandCenterAuth with scripts/salesforce/data-cloud-login-web.ps1, or complete the saved browser callback for that alias if auth already started. Raw response: $BaseMessage"
    }

    return $BaseMessage
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
    $hasRefreshTokenFlow = (-not [string]::IsNullOrWhiteSpace($env:DATACLOUD_CLIENT_ID) -and -not [string]::IsNullOrWhiteSpace($env:DATACLOUD_REFRESH_TOKEN))

    if ([string]::IsNullOrWhiteSpace($salesforceAccessToken)) {
        if (-not [string]::IsNullOrWhiteSpace($config.SalesforceAlias)) {
            try {
                $cliSession = Get-SalesforceCliOrgSession -Alias $config.SalesforceAlias
                $salesforceAccessToken = $cliSession.accessToken
                # The active CLI session owns the org context for token exchange.
                # Do not let a stale DATACLOUD_TOKEN_EXCHANGE_URL from another org override it.
                $tokenExchangeUrl = Resolve-DataCloudTokenExchangeUrl -Value $cliSession.instanceUrl

                $tokenSource = 'salesforce-cli-session'
            } catch {
                if (-not $hasRefreshTokenFlow) {
                    throw
                }
            }
        }

        if ([string]::IsNullOrWhiteSpace($salesforceAccessToken) -and -not $hasRefreshTokenFlow) {
            throw 'No usable Data Cloud auth configuration was found. Set DATACLOUD_ACCESS_TOKEN and DATACLOUD_TENANT_ENDPOINT, set DATACLOUD_SALESFORCE_ALIAS or register the target with salesforceAlias for the dedicated Data Cloud alias, or set DATACLOUD_CLIENT_ID and DATACLOUD_REFRESH_TOKEN for token exchange.'
        }
    }

    if ([string]::IsNullOrWhiteSpace($salesforceAccessToken) -and $tokenSource -eq 'salesforce-cli-session') {
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

        if ($null -eq $salesforceResponse -or [string]::IsNullOrWhiteSpace([string](Get-OptionalObjectPropertyValue -InputObject $salesforceResponse -PropertyName 'access_token')) -or [string]::IsNullOrWhiteSpace([string](Get-OptionalObjectPropertyValue -InputObject $salesforceResponse -PropertyName 'instance_url'))) {
            throw (Get-DataCloudUnexpectedResponseMessage -Operation 'Salesforce OAuth refresh-token exchange' -Response $salesforceResponse)
        }

        $salesforceAccessToken = Get-OptionalObjectPropertyValue -InputObject $salesforceResponse -PropertyName 'access_token'
        if ([string]::IsNullOrWhiteSpace($tokenExchangeUrl)) {
            $tokenExchangeUrl = Resolve-DataCloudTokenExchangeUrl -Value (Get-OptionalObjectPropertyValue -InputObject $salesforceResponse -PropertyName 'instance_url')
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
        $exchangeErrorMessage = Get-DataCloudErrorMessage -ErrorRecord $_

        $shouldRetryWithRefreshToken = (
            $tokenSource -eq 'salesforce-cli-session' -and
            $hasRefreshTokenFlow -and
            $exchangeErrorMessage -match 'invalid_scope'
        )

        if ($shouldRetryWithRefreshToken) {
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

            if ($null -eq $salesforceResponse -or [string]::IsNullOrWhiteSpace([string](Get-OptionalObjectPropertyValue -InputObject $salesforceResponse -PropertyName 'access_token')) -or [string]::IsNullOrWhiteSpace([string](Get-OptionalObjectPropertyValue -InputObject $salesforceResponse -PropertyName 'instance_url'))) {
                throw (Get-DataCloudUnexpectedResponseMessage -Operation 'Salesforce OAuth refresh-token exchange' -Response $salesforceResponse)
            }

            $salesforceAccessToken = Get-OptionalObjectPropertyValue -InputObject $salesforceResponse -PropertyName 'access_token'
            $tokenExchangeUrl = Resolve-DataCloudTokenExchangeUrl -Value (Get-OptionalObjectPropertyValue -InputObject $salesforceResponse -PropertyName 'instance_url')
            $tokenSource = 'refresh-token-fallback'

            try {
                $exchangeResponse = Invoke-RestMethod -Method Post -Uri $tokenExchangeUrl -ContentType 'application/x-www-form-urlencoded' -Body (ConvertTo-FormUrlEncoded -Values $exchangeBody)
            } catch {
                $exchangeErrorMessage = Get-DataCloudErrorMessage -ErrorRecord $_
                throw (Get-DataCloudTokenExchangeFailureMessage -BaseMessage $exchangeErrorMessage -SalesforceAlias $config.SalesforceAlias -TokenSource $tokenSource)
            }
        } else {
            throw (Get-DataCloudTokenExchangeFailureMessage -BaseMessage $exchangeErrorMessage -SalesforceAlias $config.SalesforceAlias -TokenSource $tokenSource)
        }
    }

    if ($null -eq $exchangeResponse -or [string]::IsNullOrWhiteSpace([string](Get-OptionalObjectPropertyValue -InputObject $exchangeResponse -PropertyName 'access_token'))) {
        throw (Get-DataCloudUnexpectedResponseMessage -Operation 'Salesforce Data Cloud token exchange' -Response $exchangeResponse)
    }

    $tenantEndpoint = if (-not [string]::IsNullOrWhiteSpace($config.TenantEndpoint)) {
        $config.TenantEndpoint
    } else {
        Normalize-DataCloudUrl -Value (Get-OptionalObjectPropertyValue -InputObject $exchangeResponse -PropertyName 'instance_url')
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
        AccessToken = Get-OptionalObjectPropertyValue -InputObject $exchangeResponse -PropertyName 'access_token'
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

function Get-DataCloudJobInspectionCommand {
    param(
        [string]$TargetKey,
        [Parameter(Mandatory = $true)]
        [string]$JobId
    )

    $parts = @(
        'powershell',
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        '.\scripts\salesforce\data-cloud-get-job.ps1'
    )

    if (-not [string]::IsNullOrWhiteSpace($TargetKey)) {
        $parts += @('-TargetKey', $TargetKey)
    }

    $parts += @('-JobId', $JobId)
    return ($parts -join ' ')
}

function Get-DataCloudJobAbortCommand {
    param(
        [string]$TargetKey,
        [Parameter(Mandatory = $true)]
        [string]$JobId
    )

    $parts = @(
        'powershell',
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        '.\scripts\salesforce\data-cloud-abort-job.ps1'
    )

    if (-not [string]::IsNullOrWhiteSpace($TargetKey)) {
        $parts += @('-TargetKey', $TargetKey)
    }

    $parts += @('-JobId', $JobId)
    return ($parts -join ' ')
}

function Stop-DataCloudJob {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Context,
        [Parameter(Mandatory = $true)]
        [string]$JobId
    )

    return Invoke-DataCloudJsonRequest -Context $Context -Method Patch -RelativePath ('/api/v1/ingest/jobs/{0}' -f $JobId) -Body @{ state = 'Aborted' }
}

function Get-DataCloudJobFailureDetail {
    param(
        [object]$Job
    )

    if ($null -eq $Job) {
        return ''
    }

    $detailFields = @(
        'message',
        'errorMessage',
        'failureReason',
        'failureMessage',
        'error',
        'errors',
        'statusMessage'
    )

    foreach ($fieldName in $detailFields) {
        $property = $Job.PSObject.Properties[$fieldName]
        if ($null -eq $property -or $null -eq $property.Value) {
            continue
        }

        if ($property.Value -is [System.Collections.IEnumerable] -and -not ($property.Value -is [string])) {
            $values = @($property.Value | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
            if ($values.Count -gt 0) {
                return ($values -join '; ')
            }
        }

        $text = [string]$property.Value
        if (-not [string]::IsNullOrWhiteSpace($text)) {
            return $text
        }
    }

    return ''
}

function Format-DataCloudJobFailureMessage {
    param(
        [string]$TargetKey,
        [Parameter(Mandatory = $true)]
        [object]$Job,
        [string]$ContextLabel = 'Data Cloud ingestion job'
    )

    $jobId = Get-OptionalObjectPropertyValue -InputObject $Job -PropertyName 'id'
    $state = Get-OptionalObjectPropertyValue -InputObject $Job -PropertyName 'state'
    $detail = Get-DataCloudJobFailureDetail -Job $Job

    $message = '{0} {1} ended in state {2}.' -f $ContextLabel, $(if ([string]::IsNullOrWhiteSpace($jobId)) { '<unknown>' } else { $jobId }), $(if ([string]::IsNullOrWhiteSpace($state)) { '<unknown>' } else { $state })
    if (-not [string]::IsNullOrWhiteSpace($detail)) {
        $message = '{0} Detail: {1}' -f $message, $detail
    }

    if (-not [string]::IsNullOrWhiteSpace($jobId)) {
        $message = '{0} Inspect with: {1}' -f $message, (Get-DataCloudJobInspectionCommand -TargetKey $TargetKey -JobId $jobId)
        if ($state -in @('Open', 'UploadComplete')) {
            $message = '{0} If this job is stale, abort it with: {1}' -f $message, (Get-DataCloudJobAbortCommand -TargetKey $TargetKey -JobId $jobId)
        }
    }

    return $message
}

function Add-DataCloudJobOperatorMetadata {
    param(
        [string]$TargetKey,
        [Parameter(Mandatory = $true)]
        [object]$Job
    )

    $jobId = Get-OptionalObjectPropertyValue -InputObject $Job -PropertyName 'id'
    if ([string]::IsNullOrWhiteSpace($jobId)) {
        return $Job
    }

    $inspectCommand = Get-DataCloudJobInspectionCommand -TargetKey $TargetKey -JobId $jobId
    $Job | Add-Member -NotePropertyName 'inspectCommand' -NotePropertyValue $inspectCommand -Force

    $state = Get-OptionalObjectPropertyValue -InputObject $Job -PropertyName 'state'
    if ($state -in @('Open', 'UploadComplete')) {
        $abortCommand = Get-DataCloudJobAbortCommand -TargetKey $TargetKey -JobId $jobId
        $Job | Add-Member -NotePropertyName 'abortCommand' -NotePropertyValue $abortCommand -Force
    }

    return $Job
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
