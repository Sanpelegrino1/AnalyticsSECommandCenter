# install.ps1 — Installs the Tableau Next Record Access Shares Skill
# Usage: .\install.ps1 [-Target cursor|claude|all] [-Force]

param(
    [switch]$Force,
    [ValidateSet("cursor", "claude", "all")]
    [string]$Target = "cursor"
)

$ErrorActionPreference = "Stop"

$SKILL_NAME = "tableau-next-record-access-shares"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

# Resolve skill directory based on target
function Get-SkillDir {
    param([string]$t)
    switch ($t) {
        "cursor" {
            Join-Path $env:USERPROFILE ".cursor\skills\$SKILL_NAME"
        }
        "claude" {
            Join-Path $env:USERPROFILE ".claude\skills\$SKILL_NAME"
        }
        default {
            Write-Error "Unknown target: $t"
        }
    }
}

# Files and directories to install (whitelist)
$INCLUDE = @(
    "SKILL.md",
    "README.md",
    "references",
    "evals"
)

function Install-ToDir {
    param(
        [string]$SkillDir,
        [string]$TargetName
    )

    if (Test-Path $SkillDir) {
        if ($Force) {
            Write-Host "Force flag set — reinstalling..."
            Remove-Item -Path $SkillDir -Recurse -Force
        } else {
            Write-Host "Skill already installed at: $SkillDir"
            Write-Host ""
            $response = Read-Host "Overwrite? [y/N]"
            if ($response -notmatch "^[Yy]$") {
                Write-Host "Skipping $TargetName."
                return
            }
            Remove-Item -Path $SkillDir -Recurse -Force
        }
    }

    New-Item -ItemType Directory -Force -Path $SkillDir | Out-Null

    Write-Host "Installing to $SkillDir ..."
    foreach ($item in $INCLUDE) {
        $src = Join-Path $SCRIPT_DIR $item
        if (-not (Test-Path $src)) {
            Write-Host "  Warning: $item not found, skipping"
            continue
        }
        $dest = Join-Path $SkillDir $item
        if (Test-Path $src -PathType Container) {
            New-Item -ItemType Directory -Force -Path $dest | Out-Null
            robocopy $src $dest /E /NFL /NDL /NJH /NJS /NC /NS | Out-Null
        } else {
            Copy-Item -Path $src -Destination $dest -Force
        }
    }

    $files = (Get-ChildItem -Path $SkillDir).Name -join " "
    Write-Host "  Installed: $files"
    Write-Host ""
}

function Write-NextSteps {
    param([string]$t)
    switch ($t) {
        "cursor" {
            Write-Host "Next steps:"
            Write-Host "  1. Restart Cursor (the skill loads on startup)"
            Write-Host "  2. Authenticate with your Salesforce org"
            Write-Host "  3. Ask the agent to share a Tableau Next workspace or dashboard"
        }
        "claude" {
            Write-Host "Next steps:"
            Write-Host "  1. Restart Claude Code"
            Write-Host "  2. Authenticate with your Salesforce org"
            Write-Host "  3. Ask Claude to share Tableau Next assets"
        }
        "all" {
            Write-Host "Next steps:"
            Write-Host "  - Cursor: Restart Cursor, authenticate, open chat"
            Write-Host "  - Claude Code: Restart Claude Code, authenticate"
        }
    }
}

Write-Host ""
Write-Host "Tableau Next Record Access Shares Skill — Installer"
Write-Host "===================================================="
Write-Host "Target: $Target"
Write-Host ""

if ($Target -eq "all") {
    foreach ($t in @("cursor", "claude")) {
        Write-Host "--- $t ---"
        $skillDir = Get-SkillDir $t
        Install-ToDir -SkillDir $skillDir -TargetName $t
    }
    Write-NextSteps "all"
} else {
    $skillDir = Get-SkillDir $Target
    Install-ToDir -SkillDir $skillDir -TargetName $Target
    Write-NextSteps $Target
}

Write-Host ""
Write-Host "Quick auth setup:"
Write-Host '  $env:SF_ORG = "myorg"'
Write-Host '  $env:SF_TOKEN = (sf org display --target-org $env:SF_ORG --json | ConvertFrom-Json).result.accessToken'
Write-Host ""
Write-Host "See README.md for full documentation."
