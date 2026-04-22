param(
    [switch]$InstallMissing
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\CommandCenter.Common.ps1')

function Resolve-CommandPath {
    param([string]$Name)

    $command = Get-Command $Name -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command -and $command.Source -and (Test-Path $command.Source)) {
        if (-not ($Name -eq 'python' -and $command.Source -like '*\WindowsApps\python.exe')) {
            return $command.Source
        }
    }

    $candidates = switch ($Name) {
        'git' { @('C:\Program Files\Git\cmd\git.exe') }
        'code' { @((Join-Path $env:LOCALAPPDATA 'Programs\Microsoft VS Code\bin\code.cmd')) }
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
        'node' {
            @(
                'C:\Program Files\nodejs\node.exe',
                (Join-Path $env:LOCALAPPDATA 'Programs\nodejs-lts\node.exe'),
                (Join-Path $env:LOCALAPPDATA 'Programs\nodejs\node.exe')
            )
        }
        'python' {
            @(
                (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
                (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'),
                'C:\Program Files\Python312\python.exe',
                'C:\Program Files\Python311\python.exe'
            )
        }
        'curl.exe' { @('C:\Windows\System32\curl.exe') }
        'winget' { @((Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\winget.exe')) }
        default { @() }
    }

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    return $null
}

function Test-Command {
    param([string]$Name)
    return [bool](Resolve-CommandPath -Name $Name)
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
        'C:\Program Files\Zulu',
        (Join-Path $env:LOCALAPPDATA 'Programs\Eclipse Adoptium'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Java'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Zulu')
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
    $builtinCopilotPath = Join-Path $vsCodeRoot 'resources\app\extensions\copilot'
    if (Test-Path $builtinCopilotPath) {
        $extensions.Add('github.copilot')
    }

    $extensionsDirectory = Join-Path $env:USERPROFILE '.vscode\extensions'
    if (Test-Path $extensionsDirectory) {
        $userExtensions = Get-ChildItem -Path $extensionsDirectory -Directory |
            ForEach-Object {
                if ($_.Name -match '^(?<id>.+?)-\d') {
                    $Matches['id'].ToLowerInvariant()
                } else {
                    $_.Name.ToLowerInvariant()
                }
            }

        foreach ($extension in @($userExtensions)) {
            $extensions.Add($extension)
        }
    }

    $codePath = Resolve-CommandPath -Name 'code'
    if (-not $codePath) {
        return @($extensions | Select-Object -Unique)
    }

    $output = & $codePath --list-extensions 2>$null
    foreach ($extension in @($output)) {
        $extensions.Add($extension.ToLowerInvariant())
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

    $nodeCommandPath = Resolve-CommandPath -Name 'node'
    if ($nodeCommandPath) {
        $nodeCandidates.Add($nodeCommandPath)
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

    $wingetPath = Resolve-CommandPath -Name 'winget'
    if (-not $wingetPath) {
        throw 'Install App Installer or enable winget before using -InstallMissing.'
    }

    & $wingetPath install --id $Id -e --source winget --accept-package-agreements --accept-source-agreements --silent
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

    $normalizedId = $Id.ToLowerInvariant()

    if ($InstalledExtensions -contains $normalizedId) {
        return $true
    }

    if (-not $InstallMissing) {
        return $false
    }

    $codePath = Resolve-CommandPath -Name 'code'
    if (-not $codePath) {
        throw 'VS Code command line integration is required to install extensions automatically.'
    }

    & $codePath --install-extension $Id --force
    return ($LASTEXITCODE -eq 0)
}

$checks = @(
    @{ Name = 'Git'; Command = 'git'; PackageId = 'Git.Git'; Required = $true },
    @{ Name = 'VS Code'; Command = 'code'; PackageId = 'Microsoft.VisualStudioCode'; Required = $true },
    @{ Name = 'Salesforce CLI'; Command = 'sf'; PackageId = 'OpenCLICollective.salesforce-cli'; Required = $true },
    @{ Name = 'sfdx compatibility'; Command = 'sfdx'; PackageId = 'Salesforce.sfdx-cli'; Required = $false },
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

$pythonPath = Resolve-CommandPath -Name 'python'
$pythonVersion = if ($pythonPath) { (& $pythonPath --version 2>&1) } else { '' }
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
    'github.copilot-chat',
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
