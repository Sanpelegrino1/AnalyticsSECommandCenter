# install.ps1 — Installs the Tableau Next Package & Deploy Skill
# Usage: .\install.ps1 [-Target cursor|claude|all] [-Force]

param(
    [switch]$Force,
    [ValidateSet("cursor", "claude", "all")]
    [string]$Target = "cursor"
)

$ErrorActionPreference = "Stop"

$SKILL_NAME = "tableau-next-package-deploy"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

function Get-SkillDir {
    param([string]$t)
    switch ($t) {
        "cursor" { Join-Path $env:USERPROFILE ".cursor\skills\$SKILL_NAME" }
        "claude" { Join-Path $env:USERPROFILE ".claude\skills\$SKILL_NAME" }
        default { Write-Error "Unknown target: $t" }
    }
}

$INCLUDE = @("SKILL.md", "references", "scripts", "evals")

function Install-ToDir {
    param([string]$SkillDir, [string]$TargetName)

    if (Test-Path $SkillDir) {
        if ($Force) {
            Write-Host "Force flag set — reinstalling..."
            Remove-Item -Path $SkillDir -Recurse -Force
        } else {
            Write-Host "Skill already installed at: $SkillDir"
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
            robocopy $src $dest /E /SL /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS | Out-Null
        } else {
            Copy-Item -Path $src -Destination $dest -Force
        }
    }

    $reqPath = Join-Path $SkillDir "scripts\requirements.txt"
    if (Test-Path $reqPath) {
        try {
            python -m pip install -q -r $reqPath 2>$null
        } catch {
            Write-Host "  Warning: Run 'pip install requests' for Python scripts"
        }
    }

    Write-Host "  Installed: $((Get-ChildItem -Path $SkillDir).Name -join ' ')"
    Write-Host ""
}

Write-Host ""
Write-Host "Tableau Next Package & Deploy — Installer"
Write-Host "========================================="
Write-Host "Target: $Target"
Write-Host ""

$skillDir = Get-SkillDir $Target
Install-ToDir -SkillDir $skillDir -TargetName $Target

Write-Host "Next steps:"
Write-Host "  1. Restart Cursor"
Write-Host "  2. Authenticate: sf org login web --alias myorg"
Write-Host "  3. Ask the agent to package or deploy a Tableau Next dashboard"
Write-Host ""
Write-Host "Scripts:"
Write-Host "  python scripts\package_dashboard.py --org myorg --list"
Write-Host "  python scripts\deploy_package.py --org myorg --package tableauNext\Sales_package.json"
Write-Host ""
Write-Host "See SKILL.md for full documentation."
