Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-CommandCenterRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
}

function Resolve-CommandCenterPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    return Join-Path (Get-CommandCenterRoot) $RelativePath
}

function Assert-CommandAvailable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [string]$Hint = ''
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        if ($Hint) {
            throw "Required command '$Name' is not available. $Hint"
        }

        throw "Required command '$Name' is not available."
    }
}

function Import-CommandCenterEnv {
    param(
        [switch]$Force
    )

    $root = Get-CommandCenterRoot
    $envFiles = @(
        (Join-Path $root '.env.local'),
        (Join-Path $root '.env')
    )

    foreach ($file in $envFiles) {
        if (-not (Test-Path $file)) {
            continue
        }

        foreach ($line in Get-Content -Path $file) {
            if ([string]::IsNullOrWhiteSpace($line)) {
                continue
            }

            $trimmed = $line.Trim()
            if ($trimmed.StartsWith('#')) {
                continue
            }

            $separatorIndex = $trimmed.IndexOf('=')
            if ($separatorIndex -lt 1) {
                continue
            }

            $name = $trimmed.Substring(0, $separatorIndex).Trim()
            $value = $trimmed.Substring($separatorIndex + 1).Trim()
            $value = $value.Trim('"')

            if ($Force -or -not (Test-Path "Env:$name") -or [string]::IsNullOrWhiteSpace((Get-Item "Env:$name").Value)) {
                Set-Item -Path "Env:$name" -Value $value
            }
        }
    }
}

function Read-JsonFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        return $null
    }

    $raw = Get-Content -Path $Path -Raw
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return $null
    }

    return $raw | ConvertFrom-Json
}

function Write-JsonFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [object]$Value
    )

    $directory = Split-Path -Parent $Path
    if (-not (Test-Path $directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }

    $Value | ConvertTo-Json -Depth 20 | Set-Content -Path $Path -Encoding UTF8
}

function Get-UtcTimestamp {
    return [DateTime]::UtcNow.ToString('s') + 'Z'
}

function Ensure-Directory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}
