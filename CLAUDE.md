# CLAUDE.md — Notes for Claude

This file gives you (future Claude) the context you need to work effectively in this repo without asking lots of questions.

## What this repo is

A personal monorepo owned by joseph-pye. Projects are mostly quick POCs spun up from the Claude mobile app. The owner's primary interests:

- Python scripts and small services, often using the Anthropic Claude API
- Home Assistant automation config (YAML)
- Occasional React / Vite UI work in the future

## Repo layout

```
projects/           ← actual projects, one subdirectory each
templates/
  python/           ← copy this to bootstrap a Python project
  home-assistant/   ← copy this to bootstrap an HA config snippet
scripts/
  new-project.sh   ← scaffolding helper
CLAUDE.md           ← this file
README.md           ← human-readable overview
.gitignore          ← covers Python, Node, HA, and general cruft
```

## How to start a new project

When the user asks to create a new project, scaffold it from the right template:

```bash
./scripts/new-project.sh python <project-name>
# or
./scripts/new-project.sh home-assistant <project-name>
```

Then open `projects/<project-name>/` and implement the user's idea. Update the project's own `README.md` to describe what it does.

## Coding conventions

### Python
- Target **Python 3.11+**.
- Use a **`venv`** at `.venv/` inside the project directory — never install into the system Python.
- Pin all runtime dependencies in `requirements.txt` (`pip freeze > requirements.txt` after installing).
- Store secrets in a `.env` file (never committed). Always provide a matching `.env.example` with placeholder values and comments.
- Load env vars with `python-dotenv` (`from dotenv import load_dotenv; load_dotenv()`).
- For Claude API calls, use the `anthropic` SDK. Default to the latest capable model — currently **`claude-sonnet-4-6`** unless the task specifically warrants Opus (complex reasoning) or Haiku (speed/cost).
- Prefer simple, readable scripts over clever abstractions — these are POCs.

### Home Assistant
- Keep config modular: use `!include` to split automations, scripts, and scenes into their own files.
- Comments are encouraged — HA YAML can be cryptic six months later.
- Test automations in the HA developer tools before committing.

### React / Vite (future)
- Bootstrap with `npm create vite@latest`.
- Prefer functional components and hooks.
- No CSS framework is mandated — pick whatever suits the POC.

## Environment variables (common)

| Variable | Used for |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic Claude API |

Homelab secrets (HA token, Proxmox API token, etc.) are loaded from `~/.claude/secrets.env` via a SessionStart hook. See `.env.secrets.example` for the expected variables.

## Git workflow

- The default branch is `main`.
- Feature branches follow the pattern `claude/<short-description>-<id>`.
- Commit messages should be short and imperative, e.g. `add project: weather-summary`.
- There is no CI pipeline — keep it simple.

## Homelab (Tailscale IPs)

| Variable | Hostname | IP |
|---|---|---|
| `HOMELAB_HOMEASSISTANT_IP` | homeassistant | 100.87.154.43 |
| `HOMELAB_COCKPIT_IP` | cockpit | 100.70.197.112 |
| `HOMELAB_JELLYFIN_IP` | jellyfin | 100.92.199.114 |
| `HOMELAB_JENNYS_MACBOOK_AIR_IP` | jennys-macbook-air | 100.119.54.48 |
| `HOMELAB_JOSEPHS_MAC_MINI_IP` | josephs-mac-mini | 100.126.214.89 |
| `HOMELAB_NGINXPROXYMANAGER_IP` | nginxproxymanager | 100.87.141.101 |
| `HOMELAB_PROXMOX_IP` | proxmox | 100.89.214.33 |
| `HOMELAB_PYECRAFT_IP` | pyecraft | 100.99.173.57 |
| `HOMELAB_IMMICH_IP` | immich | 100.68.110.65 |
| `HOMELAB_JOSEPHS_IPHONE_15_PRO_IP` | josephs-iphone-15-pro | 100.104.32.4 |

## Things to avoid

- Do not commit `.env` files, `venv`/`.venv` directories, `__pycache__`, `node_modules`, or HA `.storage/` directories — `.gitignore` covers these.
- Do not add framework boilerplate or over-engineer POC scripts. The goal is to get to the interesting logic fast.
- Do not modify `templates/` when working on a specific project — templates are the source of truth for new projects.
