#!/usr/bin/env bash
# install.sh — Installs the Tableau Next Record Access Shares Skill
# Usage: ./install.sh [--target cursor|claude|all] [--force]

set -e

SKILL_NAME="tableau-next-record-access-shares"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse args
TARGET="cursor"
FORCE=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --target=*) TARGET="${1#*=}"; shift ;;
    --target)   shift; [[ $# -gt 0 ]] && TARGET="$1" && shift ;;
    --force)    FORCE=true; shift ;;
    *)          shift ;;
  esac
done

# Resolve SKILL_DIR based on TARGET
get_skill_dir() {
  local t="$1"
  case $t in
    cursor)
      echo "$HOME/.cursor/skills/$SKILL_NAME"
      ;;
    claude)
      echo "$HOME/.claude/skills/$SKILL_NAME"
      ;;
    *)
      echo "Unknown target: $t" >&2
      echo "Usage: ./install.sh [--target cursor|claude|all] [--force]" >&2
      echo "  --target   cursor (default), claude, or all" >&2
      echo "  --force    overwrite without prompting" >&2
      exit 1
      ;;
  esac
}

# Files and directories to install (whitelist)
INCLUDE=(
  "SKILL.md"
  "README.md"
  "references"
  "evals"
)

do_install() {
  local skill_dir="$1"
  local target_name="$2"

  # Check if already installed
  if [ -d "$skill_dir" ]; then
    if [ "$FORCE" = true ]; then
      echo "Force flag set — reinstalling..."
      rm -rf "$skill_dir"
    else
      echo "Skill already installed at: $skill_dir"
      echo ""
      printf "Overwrite? [y/N] "
      read -r response
      if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Skipping $target_name."
        return 0
      fi
      rm -rf "$skill_dir"
    fi
  fi

  mkdir -p "$skill_dir"

  echo "Installing to $skill_dir ..."
  for item in "${INCLUDE[@]}"; do
    src="$SCRIPT_DIR/$item"
    if [ ! -e "$src" ]; then
      echo "  Warning: $item not found, skipping"
    elif [ -d "$src" ]; then
      if command -v rsync &>/dev/null; then
        rsync -a "$src/" "$skill_dir/$item/"
      else
        cp -r "$src" "$skill_dir/"
      fi
    else
      cp -r "$src" "$skill_dir/"
    fi
  done

  echo "  Installed: $(ls "$skill_dir" | tr '\n' ' ')"
  echo ""
}

print_next_steps() {
  local target="$1"
  case $target in
    cursor)
      echo "Next steps:"
      echo "  1. Restart Cursor (the skill loads on startup)"
      echo "  2. Authenticate with your Salesforce org"
      echo "  3. Ask the agent to share a Tableau Next workspace or dashboard"
      ;;
    claude)
      echo "Next steps:"
      echo "  1. Restart Claude Code"
      echo "  2. Authenticate with your Salesforce org"
      echo "  3. Ask Claude to share Tableau Next assets"
      ;;
    all)
      echo "Next steps:"
      echo "  - Cursor: Restart Cursor, authenticate, open chat"
      echo "  - Claude Code: Restart Claude Code, authenticate"
      ;;
  esac
}

echo ""
echo "Tableau Next Record Access Shares Skill — Installer"
echo "===================================================="
echo "Target: $TARGET"
echo ""

if [ "$TARGET" = "all" ]; then
  for t in cursor claude; do
    echo "--- $t ---"
    SKILL_DIR=$(get_skill_dir "$t")
    do_install "$SKILL_DIR" "$t"
  done
  print_next_steps all
else
  SKILL_DIR=$(get_skill_dir "$TARGET")
  do_install "$SKILL_DIR" "$TARGET"
  print_next_steps "$TARGET"
fi

echo ""
echo "Quick auth setup:"
echo '  export SF_ORG=myorg'
echo '  export SF_TOKEN=$(sf org display --target-org $SF_ORG --json | jq -r '"'"'.result.accessToken'"'"')'
echo ""
echo "See README.md for full documentation."
