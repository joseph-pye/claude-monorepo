# Claude Monorepo

A personal monorepo for quick POC projects, primarily built from the Claude mobile app. Projects span Python scripts and services, Home Assistant configuration, and (eventually) React UIs.

## Structure

```
claude-monorepo/
├── projects/           # Individual projects, one directory per project
├── templates/          # Starter templates for new projects
│   ├── python/         # Python script / service starter
│   └── home-assistant/ # Home Assistant config starter
└── scripts/            # Repo maintenance helpers
    └── new-project.sh  # Scaffold a new project from a template
```

## Starting a New Project

Use the helper script to scaffold a new project from a template:

```bash
# Python project
./scripts/new-project.sh python my-project-name

# Home Assistant config snippet
./scripts/new-project.sh home-assistant my-ha-config
```

This copies the appropriate template into `projects/<name>/` and sets up the basics so you can dive straight into the interesting part.

## Templates

### Python

A minimal Python starter suited to quick POC scripts and Claude API integrations:

- `main.py` — entry point with a simple argument-parsing skeleton
- `requirements.txt` — empty (or pre-filled with common deps)
- `.env.example` — common environment variables (`ANTHROPIC_API_KEY`, etc.)

### Home Assistant

A minimal Home Assistant config snippet template:

- `configuration.yaml` — top-level includes skeleton
- `automations.yaml` — automation list stub
- `scripts.yaml` — scripts list stub

## Conventions

- **One directory per project** under `projects/`. Keep projects self-contained.
- **Python**: use a `venv` inside the project directory (`python -m venv .venv`). Pin deps in `requirements.txt`.
- **Secrets**: never commit `.env` files. Always commit `.env.example` with placeholder values.
- **Naming**: `kebab-case` for project directory names.

## Tech Stack

| Layer | Choice |
|---|---|
| Scripting | Python 3.11+ |
| AI / LLM | Anthropic Claude API (`anthropic` SDK) |
| Home Automation | Home Assistant YAML |
| UI (future) | React (Vite) |
