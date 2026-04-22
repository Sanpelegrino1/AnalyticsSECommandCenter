[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ManifestPath,
    [string]$OutputPath,
    [int]$SampleRows = 200,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'DataCloud.Common.ps1')

function Get-ManifestSchemaObjects {
    param(
        [Parameter(Mandatory = $true)]
        [object]$ManifestInfo,
        [int]$SampleRows = 200
    )

    $objectNames = @()
    $schemaObjects = @()

    foreach ($fileDefinition in @($ManifestInfo.Content.files)) {
        $tableName = [string]$fileDefinition.tableName
        Assert-ValidDataCloudName -Name $tableName -Kind 'Object'
        $objectNames += $tableName

        $csvPath = Resolve-DataCloudManifestCsvPath -ManifestInfo $ManifestInfo -FileDefinition $fileDefinition
        $csvFieldProfile = Get-DataCloudCsvFieldProfiles -CsvPath $csvPath -SampleRows $SampleRows -AllowHeaderOnly -ContextLabel ("Object '$tableName'")
        if ($csvFieldProfile.fieldCount -eq 0) {
            throw "Object '$tableName' does not have any fields."
        }

        if ($csvFieldProfile.fieldCount -gt 1000) {
            throw "Object '$tableName' has $($csvFieldProfile.fieldCount) fields, which exceeds the 1000 field limit."
        }

        $fieldDefinitions = @(
            $csvFieldProfile.fields | ForEach-Object {
                [pscustomobject]@{
                    Name = $_.name
                    Schema = $_.schema
                }
            }
        )

        $schemaObjects += [pscustomobject]@{
            Name = $tableName
            CsvPath = $csvPath
            FieldCount = $fieldDefinitions.Count
            Fields = $fieldDefinitions
        }
    }

    Assert-NoCaseInsensitiveDuplicates -Values $objectNames -Kind 'object'
    return $schemaObjects
}

function Convert-SchemaObjectsToYamlLines {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$SchemaObjects
    )

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add('openapi: 3.0.3') | Out-Null
    $lines.Add('components:') | Out-Null
    $lines.Add('  schemas:') | Out-Null

    foreach ($schemaObject in $SchemaObjects) {
        $lines.Add(('    {0}:' -f $schemaObject.Name)) | Out-Null
        $lines.Add('      type: object') | Out-Null
        $lines.Add('      properties:') | Out-Null

        foreach ($field in @($schemaObject.Fields)) {
            $lines.Add(('        {0}:' -f $field.Name)) | Out-Null
            $lines.Add(('          type: {0}' -f $field.Schema.type)) | Out-Null
            if ($field.Schema.Contains('format')) {
                $lines.Add(('          format: {0}' -f $field.Schema.format)) | Out-Null
            }
        }
    }

    return @($lines)
}

$manifestInfo = Get-DataCloudManifestInfo -ManifestPath $ManifestPath
$schemaObjects = Get-ManifestSchemaObjects -ManifestInfo $manifestInfo -SampleRows $SampleRows

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $manifestLeafBase = [System.IO.Path]::GetFileNameWithoutExtension($manifestInfo.Path)
    $datasetStem = if (-not [string]::IsNullOrWhiteSpace([string]$manifestInfo.Content.datasetName)) {
        New-MetadataSafeName -Value ([string]$manifestInfo.Content.datasetName)
    } elseif ($manifestLeafBase -ieq 'manifest') {
        New-MetadataSafeName -Value (Split-Path -Leaf $manifestInfo.Directory)
    } else {
        New-MetadataSafeName -Value $manifestLeafBase
    }
    $generatedRoot = Resolve-CommandCenterPath (Join-Path 'salesforce/generated' $datasetStem)
    $OutputPath = Join-Path $generatedRoot ('{0}-ingestion-api-schema.yaml' -f $datasetStem)
}

$resolvedOutputPath = if (Test-Path $OutputPath) { (Resolve-Path $OutputPath).Path } else { [System.IO.Path]::GetFullPath($OutputPath) }
if ((Test-Path $resolvedOutputPath) -and -not $Force) {
    throw "Output path '$resolvedOutputPath' already exists. Use -Force to overwrite it."
}

$outputDirectory = Split-Path -Parent $resolvedOutputPath
if (-not (Test-Path $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}

$yamlLines = Convert-SchemaObjectsToYamlLines -SchemaObjects $schemaObjects
Set-Content -Path $resolvedOutputPath -Value $yamlLines -Encoding UTF8

Write-Output ([pscustomobject]@{
    manifestPath = $manifestInfo.Path
    outputPath = $resolvedOutputPath
    outputRoot = Split-Path -Parent $resolvedOutputPath
    objectCount = @($schemaObjects).Count
    objects = @(
        $schemaObjects | ForEach-Object {
            [pscustomobject]@{
                name = $_.Name
                fieldCount = $_.FieldCount
                csvPath = $_.CsvPath
            }
        }
    )
})