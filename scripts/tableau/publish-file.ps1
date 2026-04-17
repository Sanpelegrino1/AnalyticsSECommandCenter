param(
    [string]$TargetKey,
    [Parameter(Mandatory = $true)]
    [ValidateSet('workbook', 'datasource')]
    [string]$ContentType,
    [Parameter(Mandatory = $true)]
    [string]$Path,
    [string]$ProjectId,
    [switch]$Overwrite
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '_Tableau.Common.ps1')

if (-not (Test-Path $Path)) {
    throw "File not found: $Path"
}

$resolvedPath = Resolve-Path $Path
$fileName = [System.IO.Path]::GetFileNameWithoutExtension($resolvedPath)
$extension = [System.IO.Path]::GetExtension($resolvedPath).TrimStart('.').ToLowerInvariant()

Invoke-TableauSession -TargetKey $TargetKey -ScriptBlock {
    param($context)

    $targetProjectId = $ProjectId
    if (-not $targetProjectId) {
        $targetProjectId = $context.Config.DefaultProjectId
    }

    if (-not $targetProjectId) {
        throw 'Provide -ProjectId or set TABLEAU_DEFAULT_PROJECT_ID in .env.local.'
    }

    $endpoint = if ($ContentType -eq 'workbook') { 'workbooks' } else { 'datasources' }
    $partName = if ($ContentType -eq 'workbook') { 'tableau_workbook' } else { 'tableau_datasource' }
    $typeParameter = if ($ContentType -eq 'workbook') { 'workbookType' } else { 'datasourceType' }
    $publishUri = '{0}/api/{1}/sites/{2}/{3}?{4}={5}&overwrite={6}' -f $context.Config.ServerUrl, $context.Config.ApiVersion, $context.SiteId, $endpoint, $typeParameter, $extension, $Overwrite.ToString().ToLowerInvariant()

    $metadata = @{}
    $metadata[$ContentType] = @{
        name = $fileName
        project = @{
            id = $targetProjectId
        }
    }

    Add-Type -AssemblyName System.Net.Http
    $client = [System.Net.Http.HttpClient]::new()
    $client.DefaultRequestHeaders.Add('X-Tableau-Auth', $context.AuthToken)
    $client.DefaultRequestHeaders.Add('Accept', 'application/json')

    try {
        $content = [System.Net.Http.MultipartFormDataContent]::new('----CommandCenterBoundary')

        $requestPayload = [System.Net.Http.StringContent]::new(($metadata | ConvertTo-Json -Depth 10), [System.Text.Encoding]::UTF8, 'application/json')
        $content.Add($requestPayload, 'request_payload')

        $fileBytes = [System.IO.File]::ReadAllBytes($resolvedPath)
        $fileContent = [System.Net.Http.ByteArrayContent]::new($fileBytes)
        $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse('application/octet-stream')
        $content.Add($fileContent, $partName, [System.IO.Path]::GetFileName($resolvedPath))

        $response = $client.PostAsync($publishUri, $content).GetAwaiter().GetResult()
        $responseBody = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) {
            throw "Tableau publish failed: $responseBody"
        }

        $responseBody | ConvertFrom-Json | ConvertTo-Json -Depth 20
    } finally {
        $client.Dispose()
    }
}
