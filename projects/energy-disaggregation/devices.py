"""
Device definitions for energy disaggregation.

Each device has:
- name: human-readable label
- power_watts: draw when active
- prior: function of (hour, is_weekend) -> probability of being on
- min_duration_s: minimum time a device stays on once triggered (for temporal smoothing)

Devices can be loaded from learned_devices.json (output of learn.py)
or fall back to hardcoded defaults.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np


@dataclass
class Device:
    name: str
    power_watts: float
    prior: Callable[[int, bool], float]
    min_duration_s: float = 60.0


def _uniform_prior(p: float) -> Callable[[int, bool], float]:
    """Device equally likely at any hour."""
    return lambda h, weekend: p


def _time_window_prior(
    peak_hours: list[int],
    peak_prob: float,
    off_peak_prob: float,
    weekend_boost: float = 0.0,
) -> Callable[[int, bool], float]:
    """Higher probability during certain hours, with optional weekend boost."""
    def prior(hour: int, weekend: bool) -> float:
        base = peak_prob if hour in peak_hours else off_peak_prob
        if weekend:
            base = min(1.0, base + weekend_boost)
        return base
    return prior


# Morning + evening hours for showering
_shower_hours = [6, 7, 8, 9, 19, 20, 21, 22]

# Typical kettle usage: morning, lunch, afternoon, evening
_kettle_hours = [6, 7, 8, 9, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]

# Dishwasher: after meals
_dishwasher_hours = [8, 9, 10, 12, 13, 14, 18, 19, 20, 21, 22]

# Laundry: daytime on weekdays, anytime on weekends
_laundry_hours = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

# EV charging: typically overnight or evening
_ev_hours = [0, 1, 2, 3, 4, 5, 6, 22, 23]

_tv_hours = [19, 20, 21]

DEFAULT_DEVICES = [
    Device(
        name="shower_full",
        power_watts=7900,
        prior=_time_window_prior(_shower_hours, 0.08, 0.005),
        min_duration_s=180,  # showers last at least 3 minutes
    ),
    Device(
        name="shower_eco",
        power_watts=4500,
        prior=_time_window_prior(_shower_hours, 0.06, 0.005),
        min_duration_s=180,
    ),
    Device(
        name="dishwasher_heat",
        power_watts=2400,
        prior=_time_window_prior(_dishwasher_hours, 0.04, 0.005, weekend_boost=0.02),
        min_duration_s=300,  # heating stage lasts ~5+ min
    ),
    Device(
        name="dishwasher_wash",
        power_watts=1900,
        prior=_time_window_prior(_dishwasher_hours, 0.04, 0.005, weekend_boost=0.02),
        min_duration_s=600,  # wash stage lasts ~10+ min
    ),
    Device(
        name="car_charger",
        power_watts=2300,
        prior=_time_window_prior(_ev_hours, 0.15, 0.03),
        min_duration_s=1800,  # EV charges for at least 30 min
    ),
    Device(
        name="dryer",
        power_watts=2200,
        prior=_time_window_prior(_laundry_hours, 0.03, 0.005, weekend_boost=0.02),
        min_duration_s=1200,  # dryer runs for at least 20 min
    ),
    Device(
        name="kettle",
        power_watts=1000,
        prior=_time_window_prior(_kettle_hours, 0.05, 0.01),
        min_duration_s=60,  # kettle boils in 1-4 min
    ),
    Device(
        name="TV",
        power_watts=100,
        prior=_time_window_prior(_tv_hours, 0.3, 0.1),
        min_duration_s=300
    )
]


# Mutual exclusivity groups: devices that can't be on simultaneously.
# The two shower modes can't both be active at once.
MUTEX_GROUPS: list[list[str]] = [
    ["shower_full", "shower_eco"],
]


def _make_learned_prior(
    weekday_priors: dict[str, float],
    weekend_priors: dict[str, float],
    fallback: float = 0.01,
) -> Callable[[int, bool], float]:
    """Build a prior function from learned hourly probabilities."""
    def prior(hour: int, weekend: bool) -> float:
        bucket = weekend_priors if weekend else weekday_priors
        return bucket.get(str(hour), fallback)
    return prior


def load_learned_devices(
    path: str = "learned_devices.json",
    min_power_watts: float = 100.0,
) -> list[Device] | None:
    """
    Load devices from learned_devices.json (output of learn.py).

    Filters out devices with estimated power below min_power_watts
    (those are too small to meaningfully disaggregate from whole-house power).

    Returns None if the file doesn't exist.
    """
    # Resolve relative to this file's directory
    json_path = Path(__file__).parent / path
    if not json_path.exists():
        return None

    with open(json_path) as f:
        raw = json.load(f)

    devices = []
    for entity_id, info in raw.items():
        power_info = info.get("power")
        if power_info is None:
            continue

        power_watts = power_info["power_watts"]
        if power_watts < min_power_watts:
            continue

        priors = info.get("priors", {})
        prior_fn = _make_learned_prior(
            priors.get("weekday", {}),
            priors.get("weekend", {}),
        )

        min_dur = info.get("min_duration_s") or 60.0

        devices.append(Device(
            name=info.get("name", entity_id.split(".")[-1]),
            power_watts=power_watts,
            prior=prior_fn,
            min_duration_s=min_dur,
        ))

    return devices if devices else None


def get_devices(learned_path: str = "learned_devices.json") -> list[Device]:
    """
    Merge learned devices with hardcoded defaults.

    Learned devices take priority when names overlap. Hardcoded defaults
    fill in devices that aren't on smart switches (e.g. shower, kettle).
    """
    learned = load_learned_devices(learned_path) or []
    learned_names = {d.name for d in learned}

    # Start with learned devices, then add defaults that weren't learned
    merged = list(learned)
    for dev in DEFAULT_DEVICES:
        if dev.name not in learned_names:
            merged.append(dev)

    return merged
