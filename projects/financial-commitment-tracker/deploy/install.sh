#!/usr/bin/env bash
# install.sh — Run INSIDE the LXC to install the financial commitment tracker.
#
# Can also be run standalone on any fresh Debian 12 / Ubuntu 22.04+ box:
#   curl -sSL <raw-url>/install.sh | bash

set -euo pipefail

APP_DIR="/opt/fin-tracker"
APP_USER="fintracker"
REPO_URL="https://github.com/joseph-pye/claude-monorepo.git"
PROJECT_PATH="projects/financial-commitment-tracker"
BRANCH="main"

echo "==> Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq curl git nginx python3 python3-venv python3-pip > /dev/null

echo "==> Installing Node.js 20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null
apt-get install -y -qq nodejs > /dev/null

echo "==> Creating app user..."
id "$APP_USER" &>/dev/null || useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"

echo "==> Cloning repo..."
rm -rf "$APP_DIR"
git clone --depth 1 --branch "$BRANCH" "$REPO_URL" /tmp/repo
cp -r "/tmp/repo/$PROJECT_PATH" "$APP_DIR"
rm -rf /tmp/repo

echo "==> Setting up Python venv..."
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo "==> Building frontend..."
cd "$APP_DIR/frontend"
npm ci --silent
npx vite build
cd "$APP_DIR"

# Clean up node_modules after build — not needed at runtime
rm -rf "$APP_DIR/frontend/node_modules"

echo "==> Creating data directory..."
mkdir -p "$APP_DIR/data"

echo "==> Writing default .env..."
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env" 2>/dev/null || cat > "$APP_DIR/.env" <<'ENVEOF'
# Telegram Bot Token — get one from @BotFather on Telegram
TELEGRAM_BOT_TOKEN=your-bot-token-here

# Your Telegram Chat ID — send /start to @userinfobot to find yours
TELEGRAM_CHAT_ID=your-chat-id-here

# Database path
DATABASE_URL=sqlite:///./data/commitments.db

# Reminder check interval in minutes
REMINDER_CHECK_INTERVAL=60
ENVEOF
fi

echo "==> Setting ownership..."
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "==> Installing systemd service..."
cat > /etc/systemd/system/fin-tracker.service <<'UNITEOF'
[Unit]
Description=Financial Commitment Tracker
After=network.target

[Service]
Type=simple
User=fintracker
Group=fintracker
WorkingDirectory=/opt/fin-tracker
EnvironmentFile=/opt/fin-tracker/.env
ExecStart=/opt/fin-tracker/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNITEOF

echo "==> Installing nginx config..."
cat > /etc/nginx/sites-available/fin-tracker <<'NGINXEOF'
server {
    listen 80 default_server;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINXEOF

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/fin-tracker /etc/nginx/sites-enabled/fin-tracker

echo "==> Starting services..."
systemctl daemon-reload
systemctl enable --now fin-tracker
systemctl enable --now nginx
nginx -t && systemctl reload nginx

echo ""
echo "==> Installation complete!"
echo "    App running at http://$(hostname -I | awk '{print $1}')"
echo "    Edit /opt/fin-tracker/.env to configure Telegram, then:"
echo "      systemctl restart fin-tracker"
