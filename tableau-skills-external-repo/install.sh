#!/usr/bin/env bash
# install.sh — Monorepo installer for all Tableau skills
# Usage: ./install.sh [--target cursor|claude|agentforce|all] [--force] [--skills name1,name2]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Parse args
TARGET="cursor"
FORCE=false
SKILLS_FILTER=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --target=*) TARGET="${1#*=}"; shift ;;
    --target)   shift; [[ $# -gt 0 ]] && TARGET="$1" && shift ;;
    --force)    FORCE=true; shift ;;
    --skills=*) SKILLS_FILTER="${1#*=}"; shift ;;
    --skills)   shift; [[ $# -gt 0 ]] && SKILLS_FILTER="$1" && shift ;;
    *)          shift ;;
  esac
done

# Build installer args to pass through
PASSTHROUGH=()
[[ "$FORCE" = true ]] && PASSTHROUGH+=(--force)
PASSTHROUGH+=(--target "$TARGET")

# Discover skills with install.sh
SKILL_INSTALLERS=()
for f in skills/*/install.sh; do
  [[ -f "$f" ]] || continue
  skill_name=$(basename "$(dirname "$f")")
  if [[ -n "$SKILLS_FILTER" ]]; then
    IFS=',' read -ra WANTED <<< "$SKILLS_FILTER"
    for w in "${WANTED[@]}"; do
      [[ "$skill_name" == "$w" ]] && SKILL_INSTALLERS+=("$f") && break
    done
  else
    SKILL_INSTALLERS+=("$f")
  fi
done

if [[ ${#SKILL_INSTALLERS[@]} -eq 0 ]]; then
  echo "No skills found to install."
  if [[ -n "$SKILLS_FILTER" ]]; then
    echo "  --skills filter: $SKILLS_FILTER"
    echo "  Available skills: $(ls -d skills/*/ 2>/dev/null | xargs -I {} basename {} | tr '\n' ' ')"
  fi
  exit 1
fi

echo ""
echo "Tableau Skills — Monorepo Installer"
echo "========================================="
echo "Target: $TARGET"
echo "Skills: ${#SKILL_INSTALLERS[@]} skill(s)"
[[ -n "$SKILLS_FILTER" ]] && echo "Filter: $SKILLS_FILTER"
echo ""

SUCCESS=0
FAILED=0
FAILED_NAMES=()

for installer in "${SKILL_INSTALLERS[@]}"; do
  skill_dir=$(dirname "$installer")
  skill_name=$(basename "$skill_dir")
  echo "=== Installing $skill_name ==="
  if (cd "$skill_dir" && ./install.sh "${PASSTHROUGH[@]}"); then
    ((SUCCESS++))
  else
    ((FAILED++))
    FAILED_NAMES+=("$skill_name")
  fi
  echo ""
done

echo "========================================="
echo "Summary: $SUCCESS installed, $FAILED failed"
if [[ $FAILED -gt 0 ]]; then
  echo "Failed: ${FAILED_NAMES[*]}"
  exit 1
fi

echo ""
echo "Next steps:"
echo "  1. Restart your agent (Cursor or Claude Code)"
echo "  2. Authenticate: sf org login web --alias myorg"
echo "  3. Ask the agent to create a Tableau Next visualization or share assets"
echo ""
