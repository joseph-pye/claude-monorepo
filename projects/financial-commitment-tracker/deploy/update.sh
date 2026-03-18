#!/usr/bin/env bash
# update.sh — Run inside the LXC to pull latest code and redeploy.
#
# Usage: bash /opt/fin-tracker/deploy/update.sh

set -euo pipefail

APP_DIR="/opt/fin-tracker"
REPO_URL="https://github.com/joseph-pye/claude-monorepo.git"
PROJECT_PATH="projects/financial-commitment-tracker"
BRANCH="main"

echo "==> Pulling latest code..."
rm -rf /tmp/repo
git clone --depth 1 --branch "$BRANCH" "$REPO_URL" /tmp/repo

echo "==> Updating app files (preserving .env and data)..."
# Back up config and data
cp "$APP_DIR/.env" /tmp/.env.bak
cp -r "$APP_DIR/data" /tmp/data.bak

# Replace app files
rm -rf "$APP_DIR/frontend" "$APP_DIR"/*.py "$APP_DIR/requirements.txt"
cp /tmp/repo/$PROJECT_PATH/*.py "$APP_DIR/"
cp /tmp/repo/$PROJECT_PATH/requirements.txt "$APP_DIR/"
cp -r /tmp/repo/$PROJECT_PATH/frontend "$APP_DIR/frontend"

# Restore config and data
mv /tmp/.env.bak "$APP_DIR/.env"
rm -rf "$APP_DIR/data" && mv /tmp/data.bak "$APP_DIR/data"
rm -rf /tmp/repo

echo "==> Updating Python dependencies..."
"$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo "==> Rebuilding frontend..."
cd "$APP_DIR/frontend"
npm ci --silent
npx vite build
rm -rf node_modules
cd "$APP_DIR"

echo "==> Fixing ownership..."
chown -R fintracker:fintracker "$APP_DIR"

echo "==> Restarting service..."
systemctl restart fin-tracker

echo "==> Update complete!"
