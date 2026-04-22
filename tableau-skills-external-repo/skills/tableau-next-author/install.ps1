# install.ps1 — Installs Tableau Next Authoring + Semantic Authoring skills
# Usage: .\install.ps1 [-Target cursor|claude|all] [-Force]

param(
    [switch]$Force,
    [ValidateSet("cursor", "claude", "all")]
    [string]$Target = "cursor"
)

$ErrorActionPreference = "Stop"

$SKILL_NAME = "tableau-next-author"
$SEMANTIC_SKILL_NAME = "tableau-semantic-authoring"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$SEMANTIC_SRC_DIR = Join-Path (Split-Path -Parent $SCRIPT_DIR) "tableau-semantic-authoring"

# Resolve skill directory based on target
function Get-SkillDir {
    param([string]$t, [string]$name = $SKILL_NAME)
    switch ($t) {
        "cursor" {
            Join-Path $env:USERPROFILE ".cursor\skills\$name"
        }
        "claude" {
            Join-Path $env:USERPROFILE ".claude\skills\$name"
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
    "scripts",
    "templates"
)

$SEMANTIC_INCLUDE = @(
    "SKILL.md",
    "README.md",
    "references",
    "scripts",
    "templates",
    "evals"
)

function Install-ToDir {
    param(
        [string]$SkillDir,
        [string]$TargetName,
        [string]$SrcDir,
        [string[]]$Include
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
    foreach ($item in $Include) {
        $src = Join-Path $SrcDir $item
        if (-not (Test-Path $src)) {
            Write-Host "  Warning: $item not found, skipping"
            continue
        }
        $dest = Join-Path $SkillDir $item
        if ($item -eq "scripts" -or $item -eq "templates" -or $item -eq "references" -or $item -eq "evals") {
            New-Item -ItemType Directory -Force -Path $dest | Out-Null
            robocopy $src $dest /E /SL /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NC /NS | Out-Null
        } else {
            Copy-Item -Path $src -Destination $dest -Force
        }
    }

    # Install Python dependencies
    $requirementsPath = Join-Path $SkillDir "scripts\requirements.txt"
    if (Test-Path $requirementsPath) {
        try {
            python -m pip install -q -r $requirementsPath 2>$null
        } catch {
            try {
                python3 -m pip install -q -r $requirementsPath 2>$null
            } catch {
                Write-Host "  Warning: Could not install Python deps. Run: pip install requests"
            }
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
            Write-Host "  2. Authenticate: sf org login web --alias myorg"
            Write-Host "  3. Open a Cursor chat and ask it to create a Tableau Next visualization"
        }
        "claude" {
            Write-Host "Next steps:"
            Write-Host "  1. Restart Claude Code"
            Write-Host "  2. Authenticate: sf org login web --alias myorg"
            Write-Host "  3. Ask Claude to create a Tableau Next visualization"
        }
        "all" {
            Write-Host "Next steps:"
            Write-Host "  - Cursor: Restart Cursor, authenticate, open chat"
            Write-Host "  - Claude Code: Restart Claude Code, authenticate"
        }
    }
}

Write-Host ""
Write-Host "Tableau Next Authoring + Semantic Authoring — Installer"
Write-Host "======================================================="
Write-Host "Target: $Target"
if (-not (Test-Path $SEMANTIC_SRC_DIR)) {
    Write-Host "Note: tableau-semantic-authoring not found (install from repo with both skills)"
}
Write-Host ""

if ($Target -eq "all") {
    foreach ($t in @("cursor", "claude")) {
        Write-Host "--- $t : tableau-next-author ---"
        $skillDir = Get-SkillDir $t
        Install-ToDir -SkillDir $skillDir -TargetName $t -SrcDir $SCRIPT_DIR -Include $INCLUDE
        if (Test-Path $SEMANTIC_SRC_DIR) {
            Write-Host "--- $t : tableau-semantic-authoring ---"
            $semanticDir = Get-SkillDir $t $SEMANTIC_SKILL_NAME
            Install-ToDir -SkillDir $semanticDir -TargetName $t -SrcDir $SEMANTIC_SRC_DIR -Include $SEMANTIC_INCLUDE
        }
    }
    Write-NextSteps "all"
} else {
    Write-Host "--- tableau-next-author ---"
    $skillDir = Get-SkillDir $Target
    Install-ToDir -SkillDir $skillDir -TargetName $Target -SrcDir $SCRIPT_DIR -Include $INCLUDE
    if (Test-Path $SEMANTIC_SRC_DIR) {
        Write-Host "--- tableau-semantic-authoring ---"
        $semanticDir = Get-SkillDir $Target $SEMANTIC_SKILL_NAME
        Install-ToDir -SkillDir $semanticDir -TargetName $Target -SrcDir $SEMANTIC_SRC_DIR -Include $SEMANTIC_INCLUDE
    }
    Write-NextSteps $Target
}

Write-Host ""
Write-Host "Quick auth setup:"
Write-Host '  $env:SF_ORG = "myorg"'
Write-Host '  $env:SF_TOKEN = (sf org display --target-org $env:SF_ORG --json | ConvertFrom-Json).result.accessToken'
Write-Host '  $env:SF_INSTANCE = (sf org display --target-org $env:SF_ORG --json | ConvertFrom-Json).result.instanceUrl'
Write-Host ""
Write-Host "Helper scripts (run from skill root):"
Write-Host "  python scripts\discover_sdm.py --list          # List SDMs"
Write-Host "  python scripts\create_dashboard.py --help      # Dashboard creation"
Write-Host ""
if (Test-Path $SEMANTIC_SRC_DIR) {
    Write-Host "Semantic authoring (run from tableau-semantic-authoring):"
    Write-Host "  python scripts\lib\verify_paths.py           # Verify script symlinks"
    Write-Host "  python scripts\create_calc_field.py --help   # Create calculated fields"
    Write-Host ""
}
Write-Host "See README.md for full documentation."
