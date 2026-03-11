#!/usr/bin/env bash
# new-project.sh — scaffold a new project from a template
#
# Usage:
#   ./scripts/new-project.sh <template> <project-name>
#
# Templates:  python | home-assistant
# Example:
#   ./scripts/new-project.sh python weather-summary
#   ./scripts/new-project.sh home-assistant motion-lights

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATES_DIR="$REPO_ROOT/templates"
PROJECTS_DIR="$REPO_ROOT/projects"

usage() {
  echo "Usage: $0 <template> <project-name>"
  echo ""
  echo "Available templates:"
  for d in "$TEMPLATES_DIR"/*/; do
    echo "  $(basename "$d")"
  done
  exit 1
}

# ── Args ──────────────────────────────────────────────────────────────────────
[[ $# -ne 2 ]] && usage

TEMPLATE="$1"
PROJECT_NAME="$2"

# Validate template
TEMPLATE_DIR="$TEMPLATES_DIR/$TEMPLATE"
if [[ ! -d "$TEMPLATE_DIR" ]]; then
  echo "Error: template '$TEMPLATE' not found in $TEMPLATES_DIR"
  echo ""
  usage
fi

# Validate project name (kebab-case, no spaces)
if [[ ! "$PROJECT_NAME" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
  echo "Error: project name must be lowercase kebab-case (e.g. my-cool-project)"
  exit 1
fi

DEST_DIR="$PROJECTS_DIR/$PROJECT_NAME"

if [[ -d "$DEST_DIR" ]]; then
  echo "Error: $DEST_DIR already exists"
  exit 1
fi

# ── Scaffold ──────────────────────────────────────────────────────────────────
echo "Creating $DEST_DIR from template '$TEMPLATE'..."
cp -r "$TEMPLATE_DIR" "$DEST_DIR"

# Replace <project-name> placeholder in all text files
find "$DEST_DIR" -type f \( -name "*.py" -o -name "*.md" -o -name "*.yaml" -o -name "*.txt" \) | while read -r file; do
  # macOS-compatible sed; -i '' works on both BSD and GNU sed
  sed -i "s/<project-name>/$PROJECT_NAME/g" "$file"
done

echo ""
echo "Done! Your new project is at:"
echo "  $DEST_DIR"
echo ""
echo "Next steps:"
case "$TEMPLATE" in
  python)
    echo "  cd projects/$PROJECT_NAME"
    echo "  python -m venv .venv && source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    echo "  cp .env.example .env  # then fill in your keys"
    echo "  python main.py"
    ;;
  home-assistant)
    echo "  cd projects/$PROJECT_NAME"
    echo "  # Edit the YAML files, then copy into your HA config directory"
    ;;
esac
