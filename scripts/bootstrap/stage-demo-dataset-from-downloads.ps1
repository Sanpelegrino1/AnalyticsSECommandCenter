[CmdletBinding()]
param(
    [string]$DownloadsRoot = (Join-Path $HOME 'Downloads'),
    [string]$ZipPath,
    [string]$ZipNamePattern = '*.zip',
    [string]$DemoName,
    [string]$DestinationRoot = 'Demos',
    [string]$OutputPath,
    [switch]$Force,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\CommandCenter.Common.ps1')

function Resolve-StageDatasetArchivePath {
    param(
        [string]$DownloadsRoot,
        [string]$ZipPath,
        [string]$ZipNamePattern
    )

    if (-not [string]::IsNullOrWhiteSpace($ZipPath)) {
        $candidatePath = if ([System.IO.Path]::IsPathRooted($ZipPath)) { $ZipPath } else { Join-Path $DownloadsRoot $ZipPath }
        if (-not (Test-Path -LiteralPath $candidatePath -PathType Leaf)) {
            throw "Zip archive '$candidatePath' was not found."
        }

        return (Resolve-Path -LiteralPath $candidatePath).Path
    }

    if (-not (Test-Path -LiteralPath $DownloadsRoot -PathType Container)) {
        throw "Downloads root '$DownloadsRoot' was not found."
    }

    $archives = @(
        Get-ChildItem -LiteralPath $DownloadsRoot -File -Filter '*.zip' |
            Where-Object { $_.Name -like $ZipNamePattern } |
            Sort-Object LastWriteTimeUtc -Descending
    )

    if ($archives.Count -eq 0) {
        throw "No zip archives in '$DownloadsRoot' matched pattern '$ZipNamePattern'."
    }

    return $archives[0].FullName
}

function ConvertTo-DemoFolderName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    $trimmed = $Value.Trim()
    $trimmed = $trimmed -replace '\.zip$', ''
    $trimmed = $trimmed -replace '-downloads(\s*\(\d+\))?$', ''
    $trimmed = $trimmed -replace '_downloads(\s*\(\d+\))?$', ''
    $trimmed = $trimmed.Trim()
    if ([string]::IsNullOrWhiteSpace($trimmed)) {
        throw 'Unable to derive a demo folder name from the provided archive or demo name.'
    }

    return $trimmed
}

function Get-StageDatasetInventory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DemoDirectory,
        [Parameter(Mandatory = $true)]
        [string]$CommandCenterRoot
    )

    $files = @(
        Get-ChildItem -LiteralPath $DemoDirectory -File -Recurse |
            Sort-Object FullName
    )

    $manifestPaths = @(
        $files |
            Where-Object { $_.Name -ieq 'manifest.json' } |
            ForEach-Object {
                [pscustomobject]@{
                    relativePath = $_.FullName.Substring($CommandCenterRoot.Length).TrimStart('\') -replace '\\', '/'
                    fullPath = $_.FullName
                }
            }
    )

    $csvPaths = @(
        $files |
            Where-Object { $_.Extension -ieq '.csv' } |
            ForEach-Object {
                [pscustomobject]@{
                    relativePath = $_.FullName.Substring($CommandCenterRoot.Length).TrimStart('\') -replace '\\', '/'
                    fullPath = $_.FullName
                    sizeBytes = $_.Length
                }
            }
    )

    $fileRecords = @(
        $files | ForEach-Object {
            [pscustomobject]@{
                relativePath = $_.FullName.Substring($CommandCenterRoot.Length).TrimStart('\') -replace '\\', '/'
                fullPath = $_.FullName
                sizeBytes = $_.Length
                extension = $_.Extension
            }
        }
    )

    return [pscustomobject]@{
        fileCount = $fileRecords.Count
        manifestPaths = $manifestPaths
        csvPaths = $csvPaths
        files = $fileRecords
    }
}

function Expand-StageDatasetNestedArchives {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RootDirectory,
        [switch]$Force
    )

    $expandedArchives = @()
    $visitedArchivePaths = @{}

    while ($true) {
        $nestedArchives = @(
            Get-ChildItem -LiteralPath $RootDirectory -File -Recurse -Filter '*.zip' |
                Where-Object { -not $visitedArchivePaths.ContainsKey($_.FullName) } |
                Sort-Object FullName
        )

        if ($nestedArchives.Count -eq 0) {
            break
        }

        foreach ($nestedArchive in $nestedArchives) {
            $visitedArchivePaths[$nestedArchive.FullName] = $true
            $destinationDirectory = Join-Path $nestedArchive.DirectoryName $nestedArchive.BaseName

            if ((Test-Path -LiteralPath $destinationDirectory) -and $Force) {
                Remove-Item -LiteralPath $destinationDirectory -Recurse -Force
            }

            if (-not (Test-Path -LiteralPath $destinationDirectory)) {
                Ensure-Directory -Path $destinationDirectory
                Expand-Archive -LiteralPath $nestedArchive.FullName -DestinationPath $destinationDirectory -Force:$Force
            }

            $expandedArchives += [pscustomobject]@{
                archivePath = $nestedArchive.FullName
                destinationDirectory = $destinationDirectory
            }
        }
    }

    return @($expandedArchives)
}

$commandCenterRoot = Get-CommandCenterRoot
$resolvedArchivePath = Resolve-StageDatasetArchivePath -DownloadsRoot $DownloadsRoot -ZipPath $ZipPath -ZipNamePattern $ZipNamePattern
$archiveItem = Get-Item -LiteralPath $resolvedArchivePath
$resolvedDemoName = if (-not [string]::IsNullOrWhiteSpace($DemoName)) { ConvertTo-DemoFolderName -Value $DemoName } else { ConvertTo-DemoFolderName -Value $archiveItem.BaseName }

$resolvedDestinationRoot = if ([System.IO.Path]::IsPathRooted($DestinationRoot)) { $DestinationRoot } else { Resolve-CommandCenterPath $DestinationRoot }
$demoDirectory = Join-Path $resolvedDestinationRoot $resolvedDemoName
Ensure-Directory -Path $resolvedDestinationRoot

if ((Test-Path -LiteralPath $demoDirectory) -and $Force) {
    Remove-Item -LiteralPath $demoDirectory -Recurse -Force
}

Ensure-Directory -Path $demoDirectory
Expand-Archive -LiteralPath $resolvedArchivePath -DestinationPath $demoDirectory -Force:$Force
$expandedArchives = Expand-StageDatasetNestedArchives -RootDirectory $demoDirectory -Force:$Force

$inventory = Get-StageDatasetInventory -DemoDirectory $demoDirectory -CommandCenterRoot $commandCenterRoot
$record = [pscustomobject]@{
    archivePath = $resolvedArchivePath
    demoName = $resolvedDemoName
    demoDirectory = $demoDirectory
    expandedArchives = @($expandedArchives)
    inventory = $inventory
}

if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
    $resolvedOutputPath = if ([System.IO.Path]::IsPathRooted($OutputPath)) { $OutputPath } else { Resolve-CommandCenterPath $OutputPath }
    Write-JsonFile -Path $resolvedOutputPath -Value $record
}

if ($Json) {
    $record | ConvertTo-Json -Depth 20
} else {
    $record
}