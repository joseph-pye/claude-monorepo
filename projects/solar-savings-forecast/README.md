# solar-savings-forecast

Fetches real energy consumption and electricity price data from Home Assistant, then models annual savings for various solar panel + battery configurations.

## What it does

1. Pulls hourly power usage (Shelly EM) and electricity price history from HA
2. Builds an average hourly consumption/price profile per month
3. Simulates a full year with solar generation (UK irradiance data) and optional battery storage
4. Outputs a comparison table showing annual bill, savings, export income, install cost, and payback period

## Setup

```bash
cd projects/solar-savings-forecast
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in your HA_URL and HA_TOKEN
```

## Usage

```bash
# Default scenarios with 30 days of data
python main.py

# Custom: compare specific solar/battery combos
python main.py --solar 3 4 6 --battery 0 5 10 13.5

# Use 90 days of history for better accuracy
python main.py --days 90 --monthly

# Different export rate
python main.py --export-rate 0.15
```

## Parameters

| Flag | Default | Description |
|------|---------|-------------|
| `--days` | 30 | Days of HA history to analyse |
| `--solar` | preset | Solar array sizes in kWp (e.g. `3 4 6`) |
| `--battery` | preset | Battery sizes in kWh (e.g. `0 5 10`) |
| `--export-rate` | 0.04 | SEG export rate in £/kWh |
| `--monthly` | off | Show monthly consumption breakdown |
