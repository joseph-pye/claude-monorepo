"""
solar-savings-forecast

Fetches energy usage and electricity price data from Home Assistant,
then models savings for various solar panel + battery configurations.
"""

import argparse
import os
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

from dotenv import load_dotenv

import ha_client

load_dotenv()

# ── Defaults ─────────────────────────────────────────────────────────────────

POWER_ENTITY = os.getenv("POWER_ENTITY", "sensor.home_shelly_em_channel_1_power")
PRICE_ENTITY = os.getenv("PRICE_ENTITY", "sensor.garage_electricity_meter_current_rate")

# UK averages for solar irradiance by month (kWh per kWp per day)
# Source: approximate UK south-facing panel yield data
MONTHLY_SOLAR_YIELD_PER_KWP = {
    1: 0.8, 2: 1.3, 3: 2.3, 4: 3.3, 5: 4.0, 6: 4.5,
    7: 4.3, 8: 3.7, 9: 2.8, 10: 1.7, 11: 0.9, 12: 0.6,
}

# Hourly solar generation profile (fraction of daily total by hour)
# Bell curve peaking at solar noon (hour 12-13)
HOURLY_SOLAR_PROFILE = {
    0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.01,
    6: 0.03, 7: 0.05, 8: 0.08, 9: 0.10, 10: 0.12, 11: 0.13,
    12: 0.13, 13: 0.12, 14: 0.10, 15: 0.08, 16: 0.05, 17: 0.03,
    18: 0.01, 19: 0.0, 20: 0.0, 21: 0.0, 22: 0.0, 23: 0.0,
}

# SEG (Smart Export Guarantee) rate in £/kWh for surplus sold to grid
DEFAULT_EXPORT_RATE = 0.04

# System costs (£) — rough UK market mid-range
COST_PER_KWP_SOLAR = 1500  # installed cost per kWp
COST_PER_KWH_BATTERY = 500  # installed cost per kWh of battery


# EV charging defaults
DEFAULT_EV_CHARGER_KW = 7.0    # typical home charger max rate
DEFAULT_EV_DAILY_CAPACITY = 20.0  # kWh the car can absorb per day on average
# Probability the car is home and plugged in by hour (weekday-ish average)
# Home overnight + evenings, away during work hours
EV_HOME_PROBABILITY = {
    0: 0.9, 1: 0.9, 2: 0.9, 3: 0.9, 4: 0.9, 5: 0.9,
    6: 0.8, 7: 0.5, 8: 0.3, 9: 0.2, 10: 0.2, 11: 0.2,
    12: 0.2, 13: 0.2, 14: 0.2, 15: 0.3, 16: 0.4, 17: 0.6,
    18: 0.8, 19: 0.9, 20: 0.9, 21: 0.9, 22: 0.9, 23: 0.9,
}


@dataclass
class HourlyRecord:
    hour: int  # 0-23
    month: int  # 1-12
    consumption_kwh: float
    price_per_kwh: float  # £/kWh


@dataclass
class EVConfig:
    charger_kw: float = DEFAULT_EV_CHARGER_KW
    daily_capacity_kwh: float = DEFAULT_EV_DAILY_CAPACITY


@dataclass
class Scenario:
    name: str
    solar_kwp: float
    battery_kwh: float
    ev: EVConfig | None = None


def fetch_hourly_data(days: int) -> list[HourlyRecord]:
    """Pull power (W) and price (£/kWh) history from HA, bucket into hourly records."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    print(f"Fetching {days} days of history ({start.date()} to {end.date()})...")
    history = ha_client.get_history(
        [POWER_ENTITY, PRICE_ENTITY], start, end, minimal_response=True
    )

    power_raw = history.get(POWER_ENTITY, [])
    price_raw = history.get(PRICE_ENTITY, [])

    if not power_raw:
        print(f"WARNING: No data for {POWER_ENTITY}")
        print("Available entities in response:", list(history.keys()))
    if not price_raw:
        print(f"WARNING: No data for {PRICE_ENTITY}")
        print("Available entities in response:", list(history.keys()))

    # Parse into (timestamp, value) pairs
    def parse_series(raw: list[dict]) -> list[tuple[datetime, float]]:
        out = []
        for rec in raw:
            try:
                val = float(rec["state"])
            except (ValueError, KeyError):
                continue
            ts = datetime.fromisoformat(rec["last_changed"])
            out.append((ts, val))
        return sorted(out, key=lambda x: x[0])

    power_series = parse_series(power_raw)
    price_series = parse_series(price_raw)

    if not power_series:
        raise SystemExit("No valid power data found. Check your POWER_ENTITY.")

    # Build a price lookup: for each timestamp, the price that was in effect
    def price_at(ts: datetime) -> float:
        """Find the price in effect at a given timestamp."""
        last_price = 0.30  # fallback ~30p/kWh
        for pts, pval in price_series:
            if pts > ts:
                break
            last_price = pval
        return last_price

    # Bucket power readings into hourly energy consumption
    hourly: dict[tuple[int, int, int, int], list[float]] = {}  # (year, month, day, hour) -> [watts]
    for ts, watts in power_series:
        key = (ts.year, ts.month, ts.day, ts.hour)
        hourly.setdefault(key, []).append(watts)

    records = []
    for (year, month, day, hour), watt_readings in hourly.items():
        avg_watts = sum(watt_readings) / len(watt_readings)
        consumption_kwh = avg_watts / 1000.0  # W average over 1h ≈ kWh
        ts = datetime(year, month, day, hour, tzinfo=timezone.utc)
        price = price_at(ts)
        records.append(HourlyRecord(
            hour=hour,
            month=month,
            consumption_kwh=consumption_kwh,
            price_per_kwh=price,
        ))

    print(f"  Parsed {len(records)} hourly records from {len(power_series)} power samples")
    return records


def build_average_day_by_month(records: list[HourlyRecord]) -> dict[int, dict[int, tuple[float, float]]]:
    """
    Build average consumption and price profile per month per hour.
    Returns: {month: {hour: (avg_kwh, avg_price)}}
    """
    buckets: dict[tuple[int, int], list[tuple[float, float]]] = {}
    for r in records:
        key = (r.month, r.hour)
        buckets.setdefault(key, []).append((r.consumption_kwh, r.price_per_kwh))

    result: dict[int, dict[int, tuple[float, float]]] = {}
    for (month, hour), values in buckets.items():
        avg_kwh = sum(v[0] for v in values) / len(values)
        avg_price = sum(v[1] for v in values) / len(values)
        result.setdefault(month, {})[hour] = (avg_kwh, avg_price)

    return result


def simulate_year(
    profile: dict[int, dict[int, tuple[float, float]]],
    solar_kwp: float,
    battery_kwh: float,
    export_rate: float,
    ev: EVConfig | None = None,
) -> dict:
    """
    Simulate a full year hour-by-hour with given solar + battery + EV config.

    The EV acts as a solar soak: surplus solar charges the car (one-way, no V2G).
    Priority order for surplus: 1) battery, 2) EV, 3) export.
    """
    days_in_month = {
        1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
        7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31,
    }

    totals = {
        "grid_cost_baseline": 0.0,
        "grid_cost_with_solar": 0.0,
        "export_income": 0.0,
        "solar_generated": 0.0,
        "solar_self_consumed": 0.0,
        "solar_to_battery": 0.0,
        "solar_to_ev": 0.0,
        "solar_exported": 0.0,
        "grid_import_kwh_baseline": 0.0,
        "grid_import_kwh_with_solar": 0.0,
        "ev_grid_avoided": 0.0,
    }

    battery_soc = 0.0  # current state of charge in kWh
    battery_efficiency = 0.90  # round-trip efficiency
    ev_daily_remaining = 0.0  # how much the EV can still absorb today

    for month in range(1, 13):
        daily_solar_kwh = MONTHLY_SOLAR_YIELD_PER_KWP.get(month, 2.0) * solar_kwp
        month_days = days_in_month[month]

        for _ in range(month_days):
            # Reset EV capacity each day
            if ev:
                ev_daily_remaining = ev.daily_capacity_kwh

            for hour in range(24):
                # Get consumption and price for this hour
                if month in profile and hour in profile[month]:
                    consumption, price = profile[month][hour]
                else:
                    consumption = 0.3  # fallback ~300W average
                    price = 0.30

                # Solar generation this hour
                solar_kwh = daily_solar_kwh * HOURLY_SOLAR_PROFILE.get(hour, 0.0)

                # Baseline cost (no solar)
                totals["grid_cost_baseline"] += consumption * price
                totals["grid_import_kwh_baseline"] += consumption
                totals["solar_generated"] += solar_kwh

                # With solar: first offset consumption
                net = consumption - solar_kwh

                if net > 0:
                    # Solar didn't cover demand — use battery if available
                    self_consumed = solar_kwh
                    battery_discharge = min(battery_soc, net)
                    battery_soc -= battery_discharge
                    grid_needed = net - battery_discharge

                    totals["solar_self_consumed"] += self_consumed
                    totals["solar_to_battery"] += battery_discharge
                    totals["grid_cost_with_solar"] += grid_needed * price
                    totals["grid_import_kwh_with_solar"] += grid_needed
                else:
                    # Surplus solar
                    surplus = -net
                    self_consumed = consumption
                    totals["solar_self_consumed"] += self_consumed

                    # 1) Charge battery with surplus
                    battery_space = battery_kwh - battery_soc
                    actual_to_battery = min(surplus, battery_space)
                    battery_soc += actual_to_battery * battery_efficiency
                    surplus -= actual_to_battery

                    # 2) Charge EV with remaining surplus (if home and plugged in)
                    to_ev = 0.0
                    if ev and surplus > 0 and ev_daily_remaining > 0:
                        home_prob = EV_HOME_PROBABILITY.get(hour, 0.5)
                        max_charge = min(
                            surplus,
                            ev.charger_kw,  # charger rate limit
                            ev_daily_remaining,  # daily capacity limit
                        )
                        to_ev = max_charge * home_prob
                        ev_daily_remaining -= to_ev
                        surplus -= to_ev
                        totals["solar_to_ev"] += to_ev
                        # EV solar charging avoids buying grid power later
                        totals["ev_grid_avoided"] += to_ev * price

                    # 3) Export remainder
                    totals["solar_exported"] += surplus
                    totals["export_income"] += surplus * export_rate

    return totals


def format_currency(amount: float) -> str:
    return f"\u00a3{amount:,.2f}"


def print_report(
    scenarios: list[Scenario],
    profile: dict[int, dict[int, tuple[float, float]]],
    export_rate: float,
):
    """Print a comparative report for all scenarios."""
    print("\n" + "=" * 80)
    print("SOLAR + BATTERY SAVINGS FORECAST")
    print("=" * 80)

    # Check if any scenario has EV (for display purposes)
    any_ev = any(sc.ev for sc in scenarios)

    # Baseline (no solar)
    baseline = simulate_year(profile, 0, 0, export_rate)
    baseline_cost = baseline["grid_cost_baseline"]
    baseline_kwh = baseline["grid_import_kwh_baseline"]

    print(f"\nBaseline annual electricity cost: {format_currency(baseline_cost)}")
    print(f"Baseline annual consumption:      {baseline_kwh:,.0f} kWh")
    print(f"Average effective rate:            {baseline_cost / baseline_kwh * 100:.1f}p/kWh")

    print(f"\nExport (SEG) rate assumed:         {export_rate * 100:.1f}p/kWh")
    print()

    # Table header
    header = (
        f"{'Scenario':<30} {'Solar':>6} {'Batt':>6} {'Annual':>10} {'Saving':>10} "
        f"{'Export':>8} {'Net Save':>10} {'Cost':>10} {'Payback':>8}"
    )
    print(header)
    print(
        f"{'':30} {'(kWp)':>6} {'(kWh)':>6} {'Bill':>10} {'vs Base':>10} "
        f"{'Income':>8} {'/ Year':>10} {'Install':>10} {'(years)':>8}"
    )
    print("-" * len(header))

    for sc in scenarios:
        result = simulate_year(profile, sc.solar_kwp, sc.battery_kwh, export_rate, sc.ev)

        annual_bill = result["grid_cost_with_solar"]
        saving_vs_baseline = baseline_cost - annual_bill
        export_income = result["export_income"]
        ev_avoided = result["ev_grid_avoided"]
        net_annual_saving = saving_vs_baseline + export_income + ev_avoided

        install_cost = (sc.solar_kwp * COST_PER_KWP_SOLAR) + (sc.battery_kwh * COST_PER_KWH_BATTERY)
        payback_years = install_cost / net_annual_saving if net_annual_saving > 0 else float("inf")

        print(
            f"{sc.name:<30} {sc.solar_kwp:>6.1f} {sc.battery_kwh:>6.1f} "
            f"{format_currency(annual_bill):>10} {format_currency(saving_vs_baseline):>10} "
            f"{format_currency(export_income):>8} {format_currency(net_annual_saving):>10} "
            f"{format_currency(install_cost):>10} {payback_years:>7.1f}y"
        )

    # Detailed breakdown for each scenario
    print("\n" + "-" * 80)
    print("DETAILED BREAKDOWN")
    print("-" * 80)

    for sc in scenarios:
        result = simulate_year(profile, sc.solar_kwp, sc.battery_kwh, export_rate, sc.ev)
        print(f"\n  {sc.name}")
        print(f"    Solar generated:    {result['solar_generated']:>8,.0f} kWh/year")
        print(f"    Self-consumed:      {result['solar_self_consumed']:>8,.0f} kWh/year")
        print(f"    Battery throughput: {result['solar_to_battery']:>8,.0f} kWh/year")
        if sc.ev:
            print(f"    EV solar charging:  {result['solar_to_ev']:>8,.0f} kWh/year")
            print(f"    EV grid avoided:    {format_currency(result['ev_grid_avoided']):>8}/year")
        print(f"    Exported to grid:   {result['solar_exported']:>8,.0f} kWh/year")
        print(f"    Grid import:        {result['grid_import_kwh_with_solar']:>8,.0f} kWh/year (was {baseline_kwh:,.0f})")
        self_sufficiency = (1 - result["grid_import_kwh_with_solar"] / baseline_kwh) * 100
        print(f"    Self-sufficiency:   {self_sufficiency:>7.0f}%")


def main(args: argparse.Namespace) -> None:
    # Fetch data from Home Assistant
    records = fetch_hourly_data(args.days)
    profile = build_average_day_by_month(records)

    ev = None
    if args.ev:
        ev = EVConfig(
            charger_kw=args.ev_charger_kw,
            daily_capacity_kwh=args.ev_daily_kwh,
        )
        print(f"  EV modelled: {ev.charger_kw}kW charger, {ev.daily_capacity_kwh}kWh daily capacity")

    # Define scenarios
    scenarios = []

    for kwp in args.solar:
        for batt in args.battery:
            if kwp == 0 and batt == 0:
                continue
            label_parts = []
            if kwp > 0:
                label_parts.append(f"{kwp}kWp solar")
            if batt > 0:
                label_parts.append(f"{batt}kWh battery")
            if ev:
                label_parts.append("EV")
            name = " + ".join(label_parts)
            scenarios.append(Scenario(name=name, solar_kwp=kwp, battery_kwh=batt, ev=ev))

    if not scenarios:
        scenarios = [
            Scenario("3kWp solar only", 3.0, 0),
            Scenario("4kWp solar only", 4.0, 0),
            Scenario("6kWp solar only", 6.0, 0),
            Scenario("3kWp + 5kWh battery", 3.0, 5.0),
            Scenario("4kWp + 5kWh battery", 4.0, 5.0),
            Scenario("4kWp + 10kWh battery", 4.0, 10.0),
            Scenario("6kWp + 10kWh battery", 6.0, 10.0),
            Scenario("6kWp + 13.5kWh (Powerwall)", 6.0, 13.5),
        ]
        if args.ev:
            # Duplicate scenarios with EV added
            ev_scenarios = []
            for sc in scenarios:
                ev_scenarios.append(Scenario(
                    name=f"{sc.name} + EV",
                    solar_kwp=sc.solar_kwp,
                    battery_kwh=sc.battery_kwh,
                    ev=ev,
                ))
            scenarios.extend(ev_scenarios)

    print_report(scenarios, profile, args.export_rate)

    # Monthly breakdown
    if args.monthly:
        print("\n" + "=" * 80)
        print("MONTHLY CONSUMPTION PROFILE (from HA data)")
        print("=" * 80)
        month_names = [
            "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ]
        print(f"\n{'Month':<6} {'Avg Daily kWh':>14} {'Avg Price (p/kWh)':>18}")
        print("-" * 40)
        for month in range(1, 13):
            if month not in profile:
                continue
            daily_kwh = sum(kwh for kwh, _ in profile[month].values())
            avg_price = sum(p for _, p in profile[month].values()) / len(profile[month])
            print(f"{month_names[month]:<6} {daily_kwh:>14.1f} {avg_price * 100:>17.1f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Solar + battery savings forecast using Home Assistant energy data"
    )
    parser.add_argument(
        "--days", type=int, default=30,
        help="Days of HA history to analyse (default: 30)",
    )
    parser.add_argument(
        "--solar", type=float, nargs="+", default=[],
        help="Solar array sizes in kWp to evaluate (e.g. --solar 3 4 6)",
    )
    parser.add_argument(
        "--battery", type=float, nargs="+", default=[],
        help="Battery sizes in kWh to evaluate (e.g. --battery 0 5 10)",
    )
    parser.add_argument(
        "--export-rate", type=float, default=DEFAULT_EXPORT_RATE,
        help=f"Export rate in £/kWh (default: {DEFAULT_EXPORT_RATE})",
    )
    parser.add_argument(
        "--monthly", action="store_true",
        help="Show monthly consumption profile breakdown",
    )
    parser.add_argument(
        "--ev", action="store_true",
        help="Model EV as solar soak (absorbs surplus instead of exporting)",
    )
    parser.add_argument(
        "--ev-charger-kw", type=float, default=DEFAULT_EV_CHARGER_KW,
        help=f"EV charger max rate in kW (default: {DEFAULT_EV_CHARGER_KW})",
    )
    parser.add_argument(
        "--ev-daily-kwh", type=float, default=DEFAULT_EV_DAILY_CAPACITY,
        help=f"Average daily kWh the EV can absorb (default: {DEFAULT_EV_DAILY_CAPACITY})",
    )
    main(parser.parse_args())
