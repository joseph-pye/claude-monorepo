"""
Learn device power signatures and time-of-day priors from Home Assistant history.

For each monitored switch/plug entity:
1. Pulls state history (on/off transitions) and concurrent power sensor history
2. Measures the power delta at each transition to estimate device wattage
3. Counts on-time per hour/day-type to build empirical priors

Outputs learned_devices.json for use by the disaggregator.
"""

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np
from dotenv import load_dotenv

import ha_client

load_dotenv()

# How close in time (seconds) a power reading must be to a switch event
# to count as "concurrent"
ALIGNMENT_WINDOW_S = 60

# Minimum number of transition events to trust a power estimate
MIN_TRANSITIONS = 3

# Entity name suffixes/substrings that indicate config toggles, not appliances
EXCLUDE_PATTERNS = [
    "_led", "_disable_", "_enable_", "_setting", "_config",
    "_indicator", "_buzzer", "_child_lock", "_button_lock",
    "_power_on_behavior", "_do_not_disturb", "_night_mode",
    "_auto_off", "_away_mode", "_calibrat", "_restart",
    "_firmware", "_ota", "_debug", "_diagnostic",
    "_crossfade", "_loudness", "_surround", "_detach",
]


def _is_appliance_entity(entity_id: str) -> bool:
    """Filter out config/setting switches that aren't real appliances."""
    name = entity_id.lower()
    return not any(pat in name for pat in EXCLUDE_PATTERNS)


def _parse_timestamp(ts: str) -> datetime:
    """Parse HA timestamp string to datetime."""
    # HA uses ISO format, sometimes with +00:00 or Z
    ts = ts.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        # Fallback: strip timezone for naive comparison
        return datetime.fromisoformat(ts.split("+")[0])


def _build_power_timeline(
    power_history: list[dict],
) -> list[tuple[datetime, float]]:
    """Convert power sensor history to (timestamp, watts) pairs."""
    timeline = []
    for record in power_history:
        try:
            val = float(record["state"])
        except (ValueError, KeyError):
            continue
        ts = _parse_timestamp(record["last_changed"])
        timeline.append((ts, val))
    return sorted(timeline, key=lambda x: x[0])


def _find_nearest_power(
    power_timeline: list[tuple[datetime, float]],
    target_time: datetime,
    window_s: float = ALIGNMENT_WINDOW_S,
) -> float | None:
    """Find the power reading closest to target_time within window."""
    best_val = None
    best_delta = window_s + 1

    for ts, watts in power_timeline:
        delta = abs((ts - target_time).total_seconds())
        if delta < best_delta:
            best_delta = delta
            best_val = watts
    return best_val if best_delta <= window_s else None


def _extract_transitions(
    switch_history: list[dict],
) -> list[tuple[datetime, str, str]]:
    """Extract (timestamp, from_state, to_state) transitions from switch history."""
    transitions = []
    prev_state = None
    for record in switch_history:
        state = record["state"]
        if state not in ("on", "off"):
            prev_state = state
            continue
        if prev_state is not None and prev_state != state:
            ts = _parse_timestamp(record["last_changed"])
            transitions.append((ts, prev_state, state))
        prev_state = state
    return transitions


def learn_power_signature(
    switch_history: list[dict],
    power_timeline: list[tuple[datetime, float]],
) -> dict:
    """
    Estimate a device's power draw from its switch transitions
    correlated with total power changes.

    Returns dict with 'power_watts', 'std_watts', 'n_events',
    or None if insufficient data.
    """
    transitions = _extract_transitions(switch_history)
    deltas = []

    for ts, from_state, to_state in transitions:
        # Find the nearest power reading before and after the transition.
        # Shelly EM reports every 15s, so we look 8s either side (half the
        # interval) with a 20s max search window for some slack.
        before_time = ts - timedelta(seconds=8)
        after_time = ts + timedelta(seconds=8)

        power_before = _find_nearest_power(power_timeline, before_time, 20)
        power_after = _find_nearest_power(power_timeline, after_time, 20)

        if power_before is None or power_after is None:
            continue

        delta = power_after - power_before
        if to_state == "on":
            deltas.append(delta)  # positive = power increase
        else:
            deltas.append(-delta)  # flip sign for off transitions

    if len(deltas) < MIN_TRANSITIONS:
        return None

    arr = np.array(deltas)

    # IQR-based outlier removal: discard deltas outside 1.5*IQR of the
    # middle 50%. This handles contamination from overlapping device
    # transitions much better than raw std filtering.
    q1, q3 = np.percentile(arr, [25, 75])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    filtered = arr[(arr >= lower) & (arr <= upper)]

    if len(filtered) < MIN_TRANSITIONS:
        filtered = arr  # fall back to unfiltered if too few remain

    median_power = float(np.median(filtered))
    std_power = float(np.std(filtered))

    # Reject if the estimate is negative (can't draw negative watts)
    if median_power <= 0:
        return None

    return {
        "power_watts": round(median_power, 0),
        "std_watts": round(std_power, 0),
        "n_events": len(filtered),
        "n_events_raw": len(deltas),
    }


def learn_priors(
    switch_history: list[dict],
    n_hours: int = 24,
) -> dict:
    """
    Build empirical P(on | hour, day_type) from switch history.

    Returns dict with 'weekday' and 'weekend' keys, each mapping
    hour (str) -> probability.
    """
    # Count time spent in each state per (hour, is_weekend) bucket
    on_seconds = defaultdict(float)  # (hour, is_weekend) -> seconds on
    total_seconds = defaultdict(float)

    records = []
    for record in switch_history:
        state = record["state"]
        if state not in ("on", "off"):
            continue
        ts = _parse_timestamp(record["last_changed"])
        records.append((ts, state))

    records.sort(key=lambda x: x[0])

    for i in range(len(records) - 1):
        ts_start, state = records[i]
        ts_end, _ = records[i + 1]

        # Split the interval into hour-sized buckets
        current = ts_start
        while current < ts_end:
            hour = current.hour
            is_weekend = current.weekday() >= 5
            key = (hour, is_weekend)

            # Time until end of this hour or end of interval
            next_hour = current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            bucket_end = min(next_hour, ts_end)
            duration = (bucket_end - current).total_seconds()

            total_seconds[key] += duration
            if state == "on":
                on_seconds[key] += duration

            current = bucket_end

    # Convert to probabilities
    weekday_priors = {}
    weekend_priors = {}
    for hour in range(24):
        for is_weekend in (False, True):
            key = (hour, is_weekend)
            total = total_seconds.get(key, 0)
            if total > 0:
                prob = round(on_seconds.get(key, 0) / total, 4)
            else:
                prob = 0.0
            if is_weekend:
                weekend_priors[str(hour)] = prob
            else:
                weekday_priors[str(hour)] = prob

    return {"weekday": weekday_priors, "weekend": weekend_priors}


def learn_min_duration(switch_history: list[dict]) -> float | None:
    """Estimate minimum on-duration from transition history."""
    transitions = _extract_transitions(switch_history)
    on_durations = []
    last_on_time = None

    for ts, from_state, to_state in transitions:
        if to_state == "on":
            last_on_time = ts
        elif to_state == "off" and last_on_time is not None:
            duration = (ts - last_on_time).total_seconds()
            if duration > 0:
                on_durations.append(duration)
            last_on_time = None

    if len(on_durations) < MIN_TRANSITIONS:
        return None

    # 10th percentile as minimum typical duration
    return round(float(np.percentile(on_durations, 10)), 0)


def run_learning(
    power_entity: str,
    switch_entities: list[str],
    days: int = 30,
    output_path: str = "learned_devices.json",
) -> dict:
    """
    Main learning pipeline.

    Args:
        power_entity: HA entity ID for whole-house power sensor
        switch_entities: list of HA entity IDs for smart switches/plugs
        days: how many days of history to pull
        output_path: where to write learned device JSON
    """
    end = datetime.now()
    start = end - timedelta(days=days)

    all_entities = [power_entity] + switch_entities
    print(f"Fetching {days} days of history for {len(all_entities)} entities...")
    history = ha_client.get_history(all_entities, start, end, minimal_response=True)

    if power_entity not in history:
        print(f"ERROR: No history found for power entity '{power_entity}'")
        return {}

    power_timeline = _build_power_timeline(history[power_entity])
    print(f"  Power sensor: {len(power_timeline)} readings")

    learned = {}
    for entity_id in switch_entities:
        print(f"\n--- {entity_id} ---")

        if entity_id not in history:
            print("  No history found, skipping.")
            continue

        switch_hist = history[entity_id]
        transitions = _extract_transitions(switch_hist)
        print(f"  {len(transitions)} state transitions found")

        # Learn power signature
        sig = learn_power_signature(switch_hist, power_timeline)
        if sig is None:
            print(f"  Skipped: too few transitions, negative power, or too noisy")
        else:
            raw = sig.get('n_events_raw', sig['n_events'])
            print(f"  Estimated power: {sig['power_watts']:.0f} W "
                  f"(std dev: {sig['std_watts']:.0f} W, "
                  f"{sig['n_events']}/{raw} events kept after outlier removal)")

        # Learn priors
        priors = learn_priors(switch_hist)
        weekday_avg = np.mean([v for v in priors["weekday"].values()])
        weekend_avg = np.mean([v for v in priors["weekend"].values()])
        print(f"  Avg prior: weekday={weekday_avg:.3f}, weekend={weekend_avg:.3f}")

        # Learn min duration
        min_dur = learn_min_duration(switch_hist)
        if min_dur is not None:
            print(f"  Min on-duration (p10): {min_dur:.0f} s")

        learned[entity_id] = {
            "entity_id": entity_id,
            "name": entity_id.split(".")[-1],
            "power": sig,
            "priors": priors,
            "min_duration_s": min_dur,
        }

    # Write output
    with open(output_path, "w") as f:
        json.dump(learned, f, indent=2)
    print(f"\nWrote {len(learned)} devices to {output_path}")

    return learned


def main(args: argparse.Namespace) -> None:
    power_entity = args.power_entity or os.environ.get(
        "HA_POWER_ENTITY", "sensor.shelly_em_channel_1_power"
    )

    extra_excludes = args.exclude.split(",") if args.exclude else []

    if args.switch_entities:
        switch_entities = args.switch_entities.split(",")
    elif args.discover:
        print("Discovering switch entities...")
        switches = ha_client.list_entities("switch")
        all_ids = [s["entity_id"] for s in switches]
        total = len(all_ids)

        # Filter out config/setting entities
        switch_entities = [eid for eid in all_ids if _is_appliance_entity(eid)]
        # Apply user-specified excludes
        if extra_excludes:
            switch_entities = [
                eid for eid in switch_entities
                if not any(pat in eid for pat in extra_excludes)
            ]

        filtered = total - len(switch_entities)
        print(f"Found {total} switch entities, filtered {filtered} non-appliance entries.")
        print(f"\n{len(switch_entities)} candidates:")
        for eid in switch_entities:
            print(f"  {eid}")
        if not args.yes:
            resp = input("\nProceed with these? [y/N] ")
            if resp.lower() != "y":
                print("Aborted.")
                return
    else:
        print("Specify --switch-entities or use --discover to auto-detect.")
        return

    run_learning(
        power_entity=power_entity,
        switch_entities=switch_entities,
        days=args.days,
        output_path=args.output,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Learn device signatures from Home Assistant history"
    )
    parser.add_argument(
        "--power-entity", type=str, default=None,
        help="Power sensor entity ID (default: from HA_POWER_ENTITY env var)",
    )
    parser.add_argument(
        "--switch-entities", type=str, default=None,
        help="Comma-separated list of switch entity IDs to learn from",
    )
    parser.add_argument(
        "--discover", action="store_true",
        help="Auto-discover all switch entities from Home Assistant",
    )
    parser.add_argument(
        "--days", type=int, default=30,
        help="Days of history to analyse (default: 30)",
    )
    parser.add_argument(
        "--output", type=str, default="learned_devices.json",
        help="Output JSON file path (default: learned_devices.json)",
    )
    parser.add_argument(
        "--exclude", type=str, default=None,
        help="Extra comma-separated substrings to exclude from discovery, e.g. 'bedroom,guest'",
    )
    parser.add_argument(
        "--yes", "-y", action="store_true",
        help="Skip confirmation prompts",
    )
    main(parser.parse_args())
