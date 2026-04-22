#!/usr/bin/env bash
# install.sh — Installs the Tableau Next Package & Deploy Skill
# Usage: ./install.sh [--target cursor|claude|all] [--force]

set -e

SKILL_NAME="tableau-next-package-deploy"
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
      exit 1
      ;;
  esac
}

# Files and directories to install
INCLUDE=("SKILL.md" "references" "scripts" "evals")

do_install() {
  local skill_dir="$1"
  local target_name="$2"

  if [ -d "$skill_dir" ]; then
    if [ "$FORCE" = true ]; then
      echo "Force flag set — reinstalling..."
      rm -rf "$skill_dir"
    else
      echo "Skill already installed at: $skill_dir"
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
        rsync -a --exclude='__pycache__' --exclude='*.pyc' "$src/" "$skill_dir/$item/"
      else
        cp -r "$src" "$skill_dir/"
      fi
    else
      cp "$src" "$skill_dir/"
    fi
  done

  if [ -f "$skill_dir/scripts/requirements.txt" ]; then
    pip install -q -r "$skill_dir/scripts/requirements.txt" 2>/dev/null || \
      pip3 install -q -r "$skill_dir/scripts/requirements.txt" 2>/dev/null || \
      echo "  Warning: Run 'pip install requests' for Python scripts"
  fi

  echo "  Installed: $(ls "$skill_dir" | tr '\n' ' ')"
  echo ""
}

print_next_steps() {
  echo "Next steps:"
  echo "  1. Restart Cursor (the skill loads on startup)"
  echo "  2. Authenticate: sf org login web --alias myorg"
  echo "  3. Ask the agent to package or deploy a Tableau Next dashboard"
  echo ""
  echo "Scripts (run from skill root):"
  echo "  python scripts/package_dashboard.py --org myorg --list"
  echo "  python scripts/package_dashboard.py --org myorg --dashboard Sales_Dashboard"
  echo "  python scripts/deploy_package.py --org myorg --package tableauNext/Sales_package.json"
}

echo ""
echo "Tableau Next Package & Deploy — Installer"
echo "========================================="
echo "Target: $TARGET"
echo ""

SKILL_DIR=$(get_skill_dir "$TARGET")
do_install "$SKILL_DIR" "$TARGET"
print_next_steps

echo "See SKILL.md for full documentation."
