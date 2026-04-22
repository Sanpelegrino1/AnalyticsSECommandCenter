# install.ps1 — Monorepo installer for all Tableau skills
# Usage: .\install.ps1 [-Target cursor|claude|agentforce|all] [-Force] [-Skills "name1,name2"]

param(
    [switch]$Force,
    [ValidateSet("cursor", "claude", "agentforce", "all")]
    [string]$Target = "cursor",
    [string]$Skills = ""
)

$ErrorActionPreference = "Continue"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $SCRIPT_DIR

# Build args to pass through to skill installers
$passThrough = @("--target", $Target)
if ($Force) { $passThrough = @("--force") + $passThrough }

# Discover skills with install.sh / install.ps1
$skillDirs = Get-ChildItem -Path "skills" -Directory -ErrorAction SilentlyContinue
$installers = @()

foreach ($dir in $skillDirs) {
    $installPath = Join-Path $dir.FullName "install.ps1"
    $installPathSh = Join-Path $dir.FullName "install.sh"
    $skillName = $dir.Name

    if ($Skills) {
        $wanted = $Skills -split ","
        if ($skillName -notin $wanted) { continue }
    }

    if (Test-Path $installPath) {
        $installers += @{ Path = $installPath; Name = $skillName; Dir = $dir.FullName }
    } elseif (Test-Path $installPathSh) {
        # Prefer PowerShell; fall back to bash if on Windows with Git Bash/WSL
        $installers += @{ Path = $installPathSh; Name = $skillName; Dir = $dir.FullName }
    }
}

if ($installers.Count -eq 0) {
    Write-Host "No skills found to install."
    if ($Skills) {
        Write-Host "  -Skills filter: $Skills"
        $available = (Get-ChildItem -Path "skills" -Directory).Name -join " "
        Write-Host "  Available skills: $available"
    }
    exit 1
}

Write-Host ""
Write-Host "Tableau Skills — Monorepo Installer"
Write-Host "========================================="
Write-Host "Target: $Target"
Write-Host "Skills: $($installers.Count) skill(s)"
if ($Skills) { Write-Host "Filter: $Skills" }
Write-Host ""

$success = 0
$failed = 0
$failedNames = @()

foreach ($inst in $installers) {
    Write-Host "=== Installing $($inst.Name) ==="
    Push-Location $inst.Dir
    try {
        if ($inst.Path -match "\.ps1$") {
            & $inst.Path -Target $Target -Force:$Force
        } else {
            $args = @()
            if ($Force) { $args += "--force" }
            $args += "--target", $Target
            & bash $inst.Path @args
        }
        if ($LASTEXITCODE -eq 0) {
            $success++
        } else {
            $failed++
            $failedNames += $inst.Name
        }
    } catch {
        $failed++
        $failedNames += $inst.Name
        Write-Host "  Error: $_"
    } finally {
        Pop-Location
    }
    Write-Host ""
}

Write-Host "========================================="
Write-Host "Summary: $success installed, $failed failed"
if ($failed -gt 0) {
    Write-Host "Failed: $($failedNames -join ', ')"
    exit 1
}

Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Restart your agent (Cursor or Claude Code)"
Write-Host "  2. Authenticate: sf org login web --alias myorg"
Write-Host "  3. Ask the agent to create a Tableau Next visualization or share assets"
Write-Host ""
