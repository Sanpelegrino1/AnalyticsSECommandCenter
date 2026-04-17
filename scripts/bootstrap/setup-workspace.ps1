param(
    [switch]$InstallMissing
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\CommandCenter.Common.ps1')

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-JavaInstallationInfo {
    $javaCandidates = New-Object System.Collections.Generic.List[string]

    if (Test-Path 'Env:JAVA_HOME') {
        $javaCandidates.Add((Join-Path $env:JAVA_HOME 'bin\java.exe'))
    }

    if (Test-Command -Name 'java') {
        $javaCommand = Get-Command java -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($javaCommand) {
            $javaCandidates.Add($javaCommand.Source)
        }
    }

    foreach ($root in @(
        'C:\Program Files\Eclipse Adoptium',
        'C:\Program Files\Java',
        'C:\Program Files\Zulu'
    )) {
        if (-not (Test-Path $root)) {
            continue
        }

        foreach ($directory in @(Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue)) {
            $candidate = Join-Path $directory.FullName 'bin\java.exe'
            if (Test-Path $candidate) {
                $javaCandidates.Add($candidate)
            }
        }
    }

    foreach ($candidate in ($javaCandidates | Select-Object -Unique)) {
        if (-not (Test-Path $candidate)) {
            continue
        }

        $javaVersionOutput = & cmd.exe /c ('"{0}" -version 2>&1' -f $candidate) | Select-Object -First 1
        if (-not $javaVersionOutput) {
            continue
        }

        if ($javaVersionOutput -match 'version\s+"(?<value>[0-9]+)(\.[0-9]+)?') {
            $major = [int]$Matches['value']
            if ($major -eq 1 -and $javaVersionOutput -match 'version\s+"1\.(?<legacy>[0-9]+)') {
                $major = [int]$Matches['legacy']
            }

            return [pscustomobject]@{
                MajorVersion = $major
                JavaPath = $candidate
                JavaHome = Split-Path -Parent (Split-Path -Parent $candidate)
            }
        }
    }

    return [pscustomobject]@{
        MajorVersion = 0
        JavaPath = ''
        JavaHome = ''
    }
}

function Get-CodeExtensions {
    $extensions = New-Object System.Collections.Generic.List[string]

    $vsCodeRoot = Join-Path $env:LOCALAPPDATA 'Programs\Microsoft VS Code'
    if (Test-Path $vsCodeRoot) {
        foreach ($candidate in @(Get-ChildItem $vsCodeRoot -Directory -ErrorAction SilentlyContinue)) {
            $builtinCopilotPath = Join-Path $candidate.FullName 'resources\app\extensions\copilot'
            if (Test-Path $builtinCopilotPath) {
                $extensions.Add('github.copilot')
            }
        }
    }

    $extensionsDirectory = Join-Path $env:USERPROFILE '.vscode\extensions'
    if (Test-Path $extensionsDirectory) {
        $userExtensions = Get-ChildItem -Path $extensionsDirectory -Directory |
            ForEach-Object {
                if ($_.Name -match '^(?<id>.+?)-\d') {
                    $Matches['id']
                } else {
                    $_.Name
                }
            }

        foreach ($extension in @($userExtensions)) {
            $extensions.Add($extension)
        }
    }

    if (-not (Test-Command -Name 'code')) {
        return @($extensions | Select-Object -Unique)
    }

    $output = & code --list-extensions 2>$null
    foreach ($extension in @($output)) {
        $extensions.Add($extension)
    }

    return @($extensions | Select-Object -Unique)
}

function Get-NodeInstallationInfo {
    $nodeCandidates = New-Object System.Collections.Generic.List[string]

    if (Test-Path 'Env:COMMANDCENTER_NODEJS_HOME') {
        $nodeCandidates.Add((Join-Path $env:COMMANDCENTER_NODEJS_HOME 'node.exe'))
    }

    foreach ($root in @(
        (Join-Path $env:LOCALAPPDATA 'Programs\nodejs-lts'),
        (Join-Path $env:LOCALAPPDATA 'Programs\nodejs')
    )) {
        if (-not (Test-Path $root)) {
            continue
        }

        foreach ($directory in @(Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue)) {
            $candidate = Join-Path $directory.FullName 'node.exe'
            if (Test-Path $candidate) {
                $nodeCandidates.Add($candidate)
            }
        }
    }

    if (Test-Command -Name 'node') {
        $nodeCommand = Get-Command node -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($nodeCommand) {
            $nodeCandidates.Add($nodeCommand.Source)
        }
    }

    $best = $null
    foreach ($candidate in ($nodeCandidates | Select-Object -Unique)) {
        if (-not (Test-Path $candidate)) {
            continue
        }

        $nodeVersionOutput = & $candidate --version 2>&1 | Select-Object -First 1
        if ($nodeVersionOutput -match 'v(?<major>\d+)\.(?<minor>\d+)\.(?<patch>\d+)') {
            $info = [pscustomobject]@{
                MajorVersion = [int]$Matches['major']
                Version = $nodeVersionOutput
                NodePath = $candidate
                IsLtsLikely = (([int]$Matches['major']) % 2 -eq 0)
            }

            if (-not $best) {
                $best = $info
                continue
            }

            if ($info.IsLtsLikely -and -not $best.IsLtsLikely) {
                $best = $info
                continue
            }

            if ($info.MajorVersion -gt $best.MajorVersion) {
                $best = $info
            }
        }
    }

    if ($best) {
        return $best
    }

    return [pscustomobject]@{
        MajorVersion = 0
        Version = ''
        NodePath = ''
        IsLtsLikely = $false
    }
}

function Install-WingetPackage {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Id
    )

    Assert-CommandAvailable -Name 'winget' -Hint 'Install App Installer or enable winget before using -InstallMissing.'

    & winget install --id $Id -e --source winget --accept-package-agreements --accept-source-agreements --silent
    if ($LASTEXITCODE -ne 0) {
        throw "winget install failed for package '$Id'."
    }
}

function Ensure-Extension {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Id,
        [string[]]$InstalledExtensions
    )

    if ($null -eq $InstalledExtensions) {
        $InstalledExtensions = @()
    }

    if ($InstalledExtensions -contains $Id) {
        return $true
    }

    if (-not $InstallMissing) {
        return $false
    }

    Assert-CommandAvailable -Name 'code' -Hint 'VS Code command line integration is required to install extensions automatically.'
    & code --install-extension $Id --force
    return ($LASTEXITCODE -eq 0)
}

$checks = @(
    @{ Name = 'Git'; Command = 'git'; PackageId = 'Git.Git'; Required = $true },
    @{ Name = 'VS Code'; Command = 'code'; PackageId = 'Microsoft.VisualStudioCode'; Required = $true },
    @{ Name = 'Salesforce CLI'; Command = 'sf'; PackageId = 'Salesforce.cli'; Required = $true },
    @{ Name = 'sfdx compatibility'; Command = 'sfdx'; PackageId = ''; Required = $false },
    @{ Name = 'Node.js LTS'; Command = 'node'; PackageId = 'OpenJS.NodeJS.LTS'; Required = $true },
    @{ Name = 'Python 3.11+'; Command = 'python'; PackageId = 'Python.Python.3.12'; Required = $true },
    @{ Name = 'curl.exe'; Command = 'curl.exe'; PackageId = ''; Required = $true },
    @{ Name = 'winget'; Command = 'winget'; PackageId = ''; Required = $false }
)

$results = New-Object System.Collections.Generic.List[object]

foreach ($check in $checks) {
    $present = Test-Command -Name $check.Command

    if (-not $present -and $InstallMissing -and $check.PackageId) {
        Install-WingetPackage -Id $check.PackageId
        $present = Test-Command -Name $check.Command
    }

    $results.Add([pscustomobject]@{
        Category = 'Tool'
        Name = $check.Name
        Status = if ($present) { 'Present' } else { 'Missing' }
    })
}

$pythonVersion = if (Test-Command -Name 'python') { (& python --version 2>&1) } else { '' }
$pythonValid = $false
if ($pythonVersion -match 'Python\s+(?<major>\d+)\.(?<minor>\d+)') {
    $pythonValid = ([int]$Matches['major'] -gt 3) -or (([int]$Matches['major'] -eq 3) -and ([int]$Matches['minor'] -ge 11))
}

$results.Add([pscustomobject]@{
    Category = 'Validation'
    Name = 'Python version'
    Status = if ($pythonValid) { $pythonVersion } else { 'Needs Python 3.11 or newer' }
})

$nodeInfo = Get-NodeInstallationInfo

$results.Add([pscustomobject]@{
    Category = 'Validation'
    Name = 'Node version'
    Status = if ($nodeInfo.IsLtsLikely) { "$($nodeInfo.Version) at $($nodeInfo.NodePath)" } elseif ($nodeInfo.Version) { "Installed version $($nodeInfo.Version) is not an LTS major" } else { 'Missing Node.js' }
})

$javaInfo = Get-JavaInstallationInfo
if ($javaInfo.MajorVersion -lt 11 -and $InstallMissing) {
    Install-WingetPackage -Id 'EclipseAdoptium.Temurin.21.JDK'
    $javaInfo = Get-JavaInstallationInfo
}

$results.Add([pscustomobject]@{
    Category = 'Validation'
    Name = 'JDK for Salesforce extensions'
    Status = if ($javaInfo.MajorVersion -ge 11) { "Java $($javaInfo.MajorVersion) at $($javaInfo.JavaHome)" } else { 'Missing supported JDK (11, 17, or 21)' }
})

$requiredExtensions = @(
    'GitHub.copilot',
    'GitHub.copilot-chat',
    'salesforce.salesforcedx-vscode',
    'humao.rest-client',
    'redhat.vscode-xml',
    'redhat.vscode-yaml',
    'dotenv.dotenv-vscode',
    'yzhang.markdown-all-in-one'
)

$installedExtensions = @(Get-CodeExtensions)
foreach ($extension in $requiredExtensions) {
    $available = Ensure-Extension -Id $extension -InstalledExtensions $installedExtensions
    if ($available -and -not ($installedExtensions -contains $extension)) {
        $installedExtensions += $extension
    }

    $results.Add([pscustomobject]@{
        Category = 'Extension'
        Name = $extension
        Status = if ($available) { 'Present' } else { 'Missing' }
    })
}

$root = Get-CommandCenterRoot
$envLocalPath = Join-Path $root '.env.local'
if (-not (Test-Path $envLocalPath)) {
    Copy-Item -Path (Join-Path $root '.env.example') -Destination $envLocalPath
    $results.Add([pscustomobject]@{
        Category = 'Workspace'
        Name = '.env.local'
        Status = 'Created from .env.example'
    })
} else {
    $results.Add([pscustomobject]@{
        Category = 'Workspace'
        Name = '.env.local'
        Status = 'Already present'
    })
}

$results | Format-Table -AutoSize
