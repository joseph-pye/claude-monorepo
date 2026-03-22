# energy-disaggregation

> NILM-style energy disaggregation — infers which appliances are active from a single whole-house power reading (Shelly EM via Home Assistant).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your HA URL, token, and power sensor entity ID
```

## Usage

### Live mode (polls Home Assistant)
```bash
python main.py                     # poll every 30s
python main.py --interval 10       # poll every 10s
```

### Demo mode (offline testing)
```bash
python main.py --demo "8200,2500,350" --hour 7
python main.py --demo "4800,2300,150" --hour 22 --weekend
```

## Learning from history

Instead of hardcoding device signatures, learn them from your HA smart switch history:

```bash
# Auto-discover all switch entities and learn from 30 days of history
python learn.py --discover --days 30

# Or specify switches explicitly
python learn.py --switch-entities "switch.kettle,switch.car_charger,switch.dryer" --days 14
```

This outputs `learned_devices.json`. Once that file exists, `main.py` automatically uses the learned devices instead of the hardcoded defaults.

## How it works

Uses exhaustive Bayesian MAP inference over binary device states to find the most likely combination of active devices given:
- **Observed total power** from the Shelly EM
- **Device power signatures** — learned from correlating smart switch events with power changes, or hardcoded
- **Time-of-day priors** — learned from historical on/off patterns, or hardcoded
- **Temporal smoothing** — penalises rapid state changes between readings

## Adding devices

Manually: edit `devices.py` to add devices with their power draw and time-of-day priors.

Automatically: add a smart switch/plug to the device, then re-run `python learn.py` to pick it up from history.
