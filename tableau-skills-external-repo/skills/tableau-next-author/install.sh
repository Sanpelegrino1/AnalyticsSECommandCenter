#!/usr/bin/env bash
# install.sh — Installs Tableau Next Authoring + Semantic Authoring skills
# Usage: ./install.sh [--target cursor|claude|all] [--force]

set -e

SKILL_NAME="tableau-next-author"
SEMANTIC_SKILL_NAME="tableau-semantic-authoring"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEMANTIC_SRC_DIR="$(cd "$SCRIPT_DIR/../tableau-semantic-authoring" 2>/dev/null && pwd)"

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

# Resolve SKILL_DIR based on TARGET and skill name
get_skill_dir() {
  local t="$1"
  local name="${2:-$SKILL_NAME}"
  case $t in
    cursor)
      echo "$HOME/.cursor/skills/$name"
      ;;
    claude)
      echo "$HOME/.claude/skills/$name"
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
  "scripts"
  "templates"
)

SEMANTIC_INCLUDE=(
  "SKILL.md"
  "README.md"
  "references"
  "scripts"
  "templates"
  "evals"
)

do_install() {
  local skill_dir="$1"
  local target_name="$2"
  local src_dir="$3"
  shift 3
  local include_list=("$@")

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
  for item in "${include_list[@]}"; do
    src="$src_dir/$item"
    if [ ! -e "$src" ]; then
      echo "  Warning: $item not found, skipping"
    elif [ -d "$src" ] && { [ "$item" = "scripts" ] || [ "$item" = "templates" ] || [ "$item" = "references" ] || [ "$item" = "evals" ]; }; then
      if command -v rsync &>/dev/null; then
        rsync -a --exclude='__pycache__' --exclude='*.pyc' "$src/" "$skill_dir/$item/"
      else
        cp -r "$src" "$skill_dir/"
        find "$skill_dir/$item" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find "$skill_dir/$item" -type f -name "*.pyc" -delete 2>/dev/null || true
      fi
    else
      cp -r "$src" "$skill_dir/"
    fi
  done

  # Install Python dependencies
  if [ -f "$skill_dir/scripts/requirements.txt" ]; then
    pip install -q -r "$skill_dir/scripts/requirements.txt" 2>/dev/null || \
      pip3 install -q -r "$skill_dir/scripts/requirements.txt" 2>/dev/null || \
      echo "  Warning: Could not install Python deps. Run: pip install requests"
  fi

  echo "  Installed: $(ls "$skill_dir" | tr '\n' ' ')"
  echo ""
}

print_next_steps() {
  local target="$1"
  case $target in
    cursor)
      echo "Next steps:"
      echo "  1. Restart Cursor (the skill loads on startup)"
      echo "  2. Authenticate: sf org login web --alias myorg"
      echo "  3. Open a Cursor chat and ask it to create a Tableau Next visualization"
      ;;
    claude)
      echo "Next steps:"
      echo "  1. Restart Claude Code"
      echo "  2. Authenticate: sf org login web --alias myorg"
      echo "  3. Ask Claude to create a Tableau Next visualization"
      ;;
    all)
      echo "Next steps:"
      echo "  - Cursor: Restart Cursor, authenticate, open chat"
      echo "  - Claude Code: Restart Claude Code, authenticate"
      ;;
  esac
}

echo ""
echo "Tableau Next Authoring + Semantic Authoring — Installer"
echo "======================================================="
echo "Target: $TARGET"
if [ ! -d "$SEMANTIC_SRC_DIR" ]; then
  echo "Note: tableau-semantic-authoring not found (install from repo with both skills)"
fi
echo ""

install_skill() {
  local t="$1"
  local skill_name="$2"
  local src_dir="$3"
  shift 3
  local include_arr=("$@")
  local skill_dir
  skill_dir=$(get_skill_dir "$t" "$skill_name")
  do_install "$skill_dir" "$t" "$src_dir" "${include_arr[@]}"
}

if [ "$TARGET" = "all" ]; then
  for t in cursor claude; do
    echo "--- $t: tableau-next-author ---"
    install_skill "$t" "$SKILL_NAME" "$SCRIPT_DIR" "${INCLUDE[@]}"
    if [ -d "$SEMANTIC_SRC_DIR" ]; then
      echo "--- $t: tableau-semantic-authoring ---"
      install_skill "$t" "$SEMANTIC_SKILL_NAME" "$SEMANTIC_SRC_DIR" "${SEMANTIC_INCLUDE[@]}"
    fi
  done
  print_next_steps all
else
  echo "--- tableau-next-author ---"
  SKILL_DIR=$(get_skill_dir "$TARGET")
  do_install "$SKILL_DIR" "$TARGET" "$SCRIPT_DIR" "${INCLUDE[@]}"
  if [ -d "$SEMANTIC_SRC_DIR" ]; then
    echo "--- tableau-semantic-authoring ---"
    SEMANTIC_DIR=$(get_skill_dir "$TARGET" "$SEMANTIC_SKILL_NAME")
    do_install "$SEMANTIC_DIR" "$TARGET" "$SEMANTIC_SRC_DIR" "${SEMANTIC_INCLUDE[@]}"
  fi
  print_next_steps "$TARGET"
fi

echo ""
echo "Quick auth setup:"
echo '  export SF_ORG=myorg'
echo '  export SF_TOKEN=$(sf org display --target-org $SF_ORG --json | jq -r '"'"'.result.accessToken'"'"')'
echo '  export SF_INSTANCE=$(sf org display --target-org $SF_ORG --json | jq -r '"'"'.result.instanceUrl'"'"')'
echo ""
echo "Helper scripts (run from skill root):"
echo "  python scripts/discover_sdm.py --list          # List SDMs"
echo "  python scripts/create_dashboard.py --help      # Dashboard creation"
echo ""
if [ -d "$SEMANTIC_SRC_DIR" ]; then
  echo "Semantic authoring (run from tableau-semantic-authoring):"
  echo "  python scripts/lib/verify_paths.py           # Verify script symlinks"
  echo "  python scripts/create_calc_field.py --help    # Create calculated fields"
  echo ""
fi
echo "See README.md for full documentation."
