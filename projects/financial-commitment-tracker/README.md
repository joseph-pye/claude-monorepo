# Financial Commitment Tracker

Track mortgage renewals, insurance expiry dates, subscriptions, and other big financial commitments. Get Telegram reminders at 90, 30, and 7 days before expiry, plus a weekly all-clear summary every Monday.

## Setup

### Backend

```bash
cd projects/financial-commitment-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — see Telegram setup below
```

### Frontend

```bash
cd frontend
npm install
npm run build
```

### Telegram Bot Setup

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot`, follow the prompts, and copy the bot token
3. Message [@userinfobot](https://t.me/userinfobot) and send `/start` to get your chat ID
4. Put both values in your `.env` file

## Running

```bash
# From the project root (with venv activated)
python main.py
```

This starts the API server on `http://localhost:8000` with the built React frontend served at the root.

For development with hot-reload on the frontend:

```bash
# Terminal 1 — backend
python main.py

# Terminal 2 — frontend dev server (proxies API to backend)
cd frontend && npm run dev
```

## Features

- **Dashboard** — at-a-glance status of all commitments (ok / upcoming / soon / urgent / expired)
- **CRUD** — add, edit, archive, and delete commitments
- **Renewal flow** — one-click renew with suggested +1 year date, resets reminder flags
- **Telegram reminders** — automatic alerts at 90, 30, and 7 days before expiry
- **Weekly summary** — every Monday at 9am, a full rundown of what's coming up and reassurance when nothing needs attention
- **Categories** — mortgage, insurance, subscription, loan, warranty, contract, membership

## Deploying to Proxmox LXC

The `deploy/` directory contains everything needed to run this on a Proxmox LXC container (Debian 12).

### Quick start (from the Proxmox host)

```bash
# Clone the repo on the Proxmox host (or scp the deploy/ folder)
cd projects/financial-commitment-tracker/deploy

# Create LXC container 200 on local-lvm, install everything automatically
bash create-lxc.sh 200 local-lvm
```

This will:
- Download the Debian 12 template (if needed)
- Create a lightweight LXC (512 MB RAM, 1 core, 4 GB disk)
- Install Python, Node, nginx inside the container
- Clone the repo, build the frontend, set up a venv
- Create a `fin-tracker` systemd service (auto-starts on boot)
- Proxy port 80 (nginx) → port 8000 (uvicorn)

### After creation

```bash
# Set your Telegram credentials
pct exec 200 -- nano /opt/fin-tracker/.env

# Restart to pick up the new config
pct exec 200 -- systemctl restart fin-tracker

# Check the IP
pct exec 200 -- hostname -I
```

Then open `http://<container-ip>` in your browser.

### Manual install (any Debian/Ubuntu box)

```bash
# Copy install.sh to the target machine and run it
bash install.sh
```

### Updating

```bash
# Inside the LXC
bash /opt/fin-tracker/deploy/update.sh
```

This pulls the latest code, rebuilds the frontend, updates Python deps, and restarts the service. Your `.env` and database are preserved.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/commitments` | List all commitments |
| POST | `/api/commitments` | Create a commitment |
| GET | `/api/commitments/:id` | Get one commitment |
| PATCH | `/api/commitments/:id` | Update a commitment |
| DELETE | `/api/commitments/:id` | Delete a commitment |
| POST | `/api/commitments/:id/renew` | Renew with new expiry date |
| GET | `/api/status` | Dashboard summary counts |
| GET | `/api/categories` | List distinct categories |
