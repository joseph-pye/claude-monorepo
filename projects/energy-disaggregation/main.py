"""
energy-disaggregation — NILM-style power disaggregation using ILP inference.

Polls a Shelly EM power sensor via Home Assistant and infers which
appliances are currently active using Bayesian priors + ILP optimisation.
"""

import argparse
import os
import time
from datetime import datetime

from dotenv import load_dotenv

from devices import get_devices
from disaggregator import disaggregate, format_result
import ha_client

load_dotenv()


def run_demo(power_values: list[float], hour: int, is_weekend: bool) -> None:
    """Run disaggregation on a list of power readings (demo / offline mode)."""
    devices = get_devices()
    prev_state = None

    for i, p in enumerate(power_values):
        states, residual = disaggregate(p, devices, hour, is_weekend, prev_state)
        print(f"\n--- Reading {i+1} ---")
        print(format_result(devices, states, p, residual))
        prev_state = states


def run_live(interval_s: float) -> None:
    """Poll Home Assistant and run disaggregation in a loop."""
    entity_id = os.environ.get("HA_POWER_ENTITY", "sensor.shelly_em_channel_1_power")
    devices = get_devices()
    prev_state = None

    print(f"Polling {entity_id} every {interval_s}s...")
    print(f"Tracking {len(devices)} device signatures.\n")

    while True:
        try:
            state = ha_client.get_state(entity_id)
            power = float(state["state"])
            now = datetime.now()
            hour = now.hour
            is_weekend = now.weekday() >= 5

            states, residual = disaggregate(
                power, devices, hour, is_weekend, prev_state
            )
            timestamp = now.strftime("%H:%M:%S")
            print(f"\n[{timestamp}]")
            print(format_result(devices, states, power, residual))

            prev_state = states

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(interval_s)


def main(args: argparse.Namespace) -> None:
    if args.demo:
        # Demo mode: simulate some power readings
        readings = [float(x) for x in args.demo.split(",")]
        hour = args.hour if args.hour is not None else datetime.now().hour
        run_demo(readings, hour, args.weekend)
    else:
        run_live(args.interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--interval", type=float, default=15.0,
        help="Polling interval in seconds (default: 30)",
    )
    parser.add_argument(
        "--demo", type=str, default=None,
        help="Comma-separated power values for offline demo, e.g. '8200,2500,350'",
    )
    parser.add_argument(
        "--hour", type=int, default=None,
        help="Override hour-of-day for demo mode (0-23)",
    )
    parser.add_argument(
        "--weekend", action="store_true",
        help="Treat as weekend for demo mode priors",
    )
    main(parser.parse_args())
