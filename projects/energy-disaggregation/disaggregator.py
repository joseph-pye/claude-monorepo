"""
Energy disaggregation via exhaustive Bayesian MAP inference.

Given a total power reading P(t), infers which devices are on by finding
the binary state vector x that maximises:

    P(x | P(t), h, d) ∝ P(P(t)|x) · ∏_k π_k(h,d)^x_k · (1-π_k(h,d))^(1-x_k)

where P(P(t)|x) = N(P(t); Σ x_k p_k, σ²).

With ≤15 devices, exhaustive enumeration of 2^K states is fast (<1ms
for K=7). This avoids LP relaxation issues and gives exact MAP solutions.
A temporal smoothing penalty discourages rapid state changes.
"""

import numpy as np
from itertools import product

from devices import Device, MUTEX_GROUPS


# Noise parameter: std dev of unmodelled load + measurement noise (watts).
DEFAULT_SIGMA = 200.0

# Weight on temporal smoothing: cost per state flip from previous timestep.
# In units of log-probability, so ~2 means "flipping is like a 7x prior penalty".
SWITCH_COST = 1.5


def _is_valid(
    state: tuple[int, ...],
    devices: list[Device],
) -> bool:
    """Check mutex constraints."""
    device_names = [d.name for d in devices]
    for group in MUTEX_GROUPS:
        count = sum(
            state[device_names.index(n)]
            for n in group
            if n in device_names
        )
        if count > 1:
            return False
    return True


def disaggregate(
    power_w: float,
    devices: list[Device],
    hour: int,
    is_weekend: bool,
    prev_state: np.ndarray | None = None,
    sigma: float = DEFAULT_SIGMA,
) -> tuple[np.ndarray, float]:
    """
    Find the MAP device state vector given observed power.

    Returns:
        states: binary array of length K (1 = on, 0 = off)
        residual: unexplained power (watts)
    """
    K = len(devices)
    powers = np.array([d.power_watts for d in devices])

    # Precompute log-priors for each device
    log_prior_on = np.zeros(K)
    log_prior_off = np.zeros(K)
    for i, dev in enumerate(devices):
        pi = np.clip(dev.prior(hour, is_weekend), 1e-6, 1.0 - 1e-6)
        log_prior_on[i] = np.log(pi)
        log_prior_off[i] = np.log(1.0 - pi)

    best_score = -np.inf
    best_state = np.zeros(K)

    for bits in product((0, 1), repeat=K):
        state = np.array(bits, dtype=float)

        # Check mutex constraints
        if not _is_valid(bits, devices):
            continue

        # Log-likelihood: Gaussian around sum of active powers
        predicted = np.dot(state, powers)
        log_lik = -0.5 * ((power_w - predicted) / sigma) ** 2

        # Log-prior: product of Bernoulli priors
        log_prior = np.dot(state, log_prior_on) + np.dot(1.0 - state, log_prior_off)

        # Temporal smoothing: penalise state changes
        switch_penalty = 0.0
        if prev_state is not None:
            n_flips = np.sum(np.abs(state - prev_state))
            switch_penalty = -SWITCH_COST * n_flips

        score = log_lik + log_prior + switch_penalty

        if score > best_score:
            best_score = score
            best_state = state.copy()

    estimated = float(np.dot(best_state, powers))
    residual = power_w - estimated

    return best_state, residual


def format_result(
    devices: list[Device],
    states: np.ndarray,
    power_w: float,
    residual: float,
) -> str:
    """Human-readable summary of disaggregation result."""
    lines = [f"Observed: {power_w:.0f} W"]
    active = []
    for dev, on in zip(devices, states):
        if on > 0.5:
            active.append(f"  {dev.name}: {dev.power_watts:.0f} W")
    if active:
        lines.append("Active devices:")
        lines.extend(active)
    else:
        lines.append("No known devices detected.")
    lines.append(f"Residual (unmodelled): {residual:.0f} W")
    return "\n".join(lines)
