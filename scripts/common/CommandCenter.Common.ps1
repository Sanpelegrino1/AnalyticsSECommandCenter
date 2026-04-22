Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-CommandPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $command = Get-Command $Name -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command -and $command.Source -and (Test-Path $command.Source)) {
        return $command.Source
    }

    $candidates = switch ($Name) {
        'sf' {
            @(
                'C:\Program Files\Salesforce CLI\bin\sf.cmd',
                'C:\Program Files\sfdx\bin\sf.cmd',
                'C:\Program Files\sfdx\client\bin\sf.cmd',
                (Join-Path $env:LOCALAPPDATA 'sf\bin\sf.cmd')
            )
        }
        'sfdx' {
            @(
                'C:\Program Files\Salesforce CLI\bin\sfdx.cmd',
                'C:\Program Files\sfdx\bin\sfdx.cmd',
                'C:\Program Files\sfdx\client\bin\sfdx.cmd',
                (Join-Path $env:LOCALAPPDATA 'sf\bin\sfdx.cmd')
            )
        }
        'code' { @((Join-Path $env:LOCALAPPDATA 'Programs\Microsoft VS Code\bin\code.cmd')) }
        'git' { @('C:\Program Files\Git\cmd\git.exe') }
        default { @() }
    }

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    return $null
}

function Get-RequiredCommandPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [string]$Hint = ''
    )

    $resolvedPath = Resolve-CommandPath -Name $Name
    if (-not [string]::IsNullOrWhiteSpace($resolvedPath)) {
        return $resolvedPath
    }

    if ($Hint) {
        throw "Required command '$Name' is not available. $Hint"
    }

    throw "Required command '$Name' is not available."
}

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

    [void](Get-RequiredCommandPath -Name $Name -Hint $Hint)
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

function Get-CommandCenterEnvFilePath {
    return Join-Path (Get-CommandCenterRoot) '.env.local'
}

function Set-CommandCenterEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [AllowNull()]
        [string]$Value
    )

    $envFilePath = Get-CommandCenterEnvFilePath
    $envExamplePath = Join-Path (Get-CommandCenterRoot) '.env.example'
    if (-not (Test-Path $envFilePath)) {
        if (Test-Path $envExamplePath) {
            Copy-Item -Path $envExamplePath -Destination $envFilePath
        } else {
            New-Item -ItemType File -Path $envFilePath -Force | Out-Null
        }
    }

    $normalizedValue = if ($null -eq $Value) { '' } else { $Value }
    $updatedLine = '{0}={1}' -f $Name, $normalizedValue
    $lines = @(Get-Content -Path $envFilePath -ErrorAction SilentlyContinue)
    $updated = $false

    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match ('^{0}=' -f [regex]::Escape($Name))) {
            $lines[$index] = $updatedLine
            $updated = $true
            break
        }
    }

    if (-not $updated) {
        $lines += $updatedLine
    }

    Set-Content -Path $envFilePath -Value $lines -Encoding UTF8
    Set-Item -Path ("Env:{0}" -f $Name) -Value $normalizedValue
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
