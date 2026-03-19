# ha-financial-commitments — Home Assistant config

Track mortgage renewals, insurance expiry dates, subscriptions, and other financial commitments directly in Home Assistant. Get Telegram reminders at 90, 30, and 7 days before expiry, plus a weekly Monday summary.

## Files

| File | Purpose |
|---|---|
| `configuration.yaml` | Top-level config — shows what to add to your HA config |
| `financial_commitments.yaml` | Package: input helpers, template sensors, summary sensors |
| `automations.yaml` | Daily reminder check, weekly summary, urgent real-time alert |
| `scripts.yaml` | On-demand summary script (trigger from UI or Developer Tools) |
| `lovelace-dashboard.yaml` | Dashboard with summary cards and per-commitment entity cards |

## Included commitments (starter set)

| Slug | Default category |
|---|---|
| `mortgage` | mortgage |
| `car_insurance` | insurance |
| `home_insurance` | insurance |
| `broadband` | subscription |
| `energy` | contract |
| `phone` | contract |

Each commitment has: expiry date, provider, amount, notes, category, and an archive toggle.

## Installation

1. **Set up the Telegram Bot integration** in HA first:
   - Settings > Devices & Services > Add Integration > Telegram Bot
   - This creates the `notify.telegram` service used by the automations

2. **Copy all YAML files** into your HA config directory (`/config/` or `~/.homeassistant/`):
   ```bash
   cp financial_commitments.yaml automations.yaml scripts.yaml /config/
   ```

3. **Add to your `configuration.yaml`** (or merge with existing):
   ```yaml
   homeassistant:
     packages:
       financial_commitments: !include financial_commitments.yaml

   automation: !include automations.yaml
   script: !include scripts.yaml
   ```

4. **Restart Home Assistant**.

5. **Set your commitment dates**: go to Settings > Devices & Services > Helpers, or use the Lovelace dashboard to edit inline.

6. **Import the dashboard** (optional): go to Settings > Dashboards > Add Dashboard, choose raw YAML config, and paste the contents of `lovelace-dashboard.yaml`.

## Adding a new commitment

To add a new commitment (e.g. gym membership), you need to add entries in `financial_commitments.yaml`:

1. **input_datetime** — `commitment_gym_expiry` (the expiry date)
2. **input_text** — `commitment_gym_provider`, `commitment_gym_amount`, `commitment_gym_notes`
3. **input_select** — `commitment_gym_category`
4. **input_boolean** — `commitment_gym_archived`
5. **template sensor** — `Gym — Days Remaining` (copy an existing one, change the entity IDs)

Then add the sensor entity ID to the list in:
- The summary sensors in `financial_commitments.yaml`
- The daily check automation in `automations.yaml` (add a `choose` block)
- The weekly summary sensor list in `automations.yaml`
- The urgent alert trigger list in `automations.yaml`
- The `scripts.yaml` summary script sensor list
- A new card in `lovelace-dashboard.yaml`

Yes, this is the trade-off vs the FastAPI app — adding a commitment is YAML editing rather than clicking a button. But for a stable set of 6-20 commitments that rarely change, it's much less to maintain.

## Automations

| Automation | Schedule | What it does |
|---|---|---|
| Daily Reminder Check | Every day at 9:00am | Sends Telegram alert if any commitment is at exactly 90, 30, or 7 days, or expired |
| Weekly Summary | Monday at 9:05am | Full summary of all active commitments with status labels |
| Urgent Alert | Real-time | Fires immediately when any commitment drops to 7 days or below |

## Scripts

| Script | What it does |
|---|---|
| `fin_commitment_send_summary` | Manually trigger a full summary via Telegram (call from Developer Tools or a button card) |

## Entity IDs

### Sensors (auto-calculated)
- `sensor.mortgage_days_remaining`
- `sensor.car_insurance_days_remaining`
- `sensor.home_insurance_days_remaining`
- `sensor.broadband_days_remaining`
- `sensor.energy_days_remaining`
- `sensor.phone_contract_days_remaining`
- `sensor.financial_commitments_total_active`
- `sensor.financial_commitments_urgent_count`
- `sensor.financial_commitments_expired_count`

### Input helpers (editable)
- `input_datetime.commitment_<slug>_expiry`
- `input_text.commitment_<slug>_provider`
- `input_text.commitment_<slug>_amount`
- `input_text.commitment_<slug>_notes`
- `input_select.commitment_<slug>_category`
- `input_boolean.commitment_<slug>_archived`
