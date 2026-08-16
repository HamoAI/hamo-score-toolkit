"""Reference implementation of the downstream state math.

AWEHB scores are per-message signals and are NOT meant to be consumed raw.
In Hamo's production engine they feed deterministic code: an exponential
blend smooths per-message noise ~5×, and the smoothed stress maps to one of
three energy states that gate how deep a conversation may go. This module is
that pattern, released as a reference — we recommend the same shape in any
deployment.

Formula (published in the model card):
    session delta = 0.9·W + 1.2·E + 1.6·H − 1.0·A − 1.1·B   (quadrant-modified)
    new_stress    = 0.8 · history + 0.2 · clamp(history + delta, 0, 10)
"""
from __future__ import annotations

from typing import Dict, Optional

QUADRANTS = ("expert", "supporter", "leader", "dreamer")


def update_stress(
    scores: Dict[str, float],
    current_stress: float,
    quadrant: Optional[str] = None,
) -> float:
    """One smoothing step: blend this message's signal into historical stress.

    Args:
        scores: AWEHB dict from :func:`hamo_score.parse.parse_scores`.
        current_stress: prior stress level, 0–10.
        quadrant: optional personality quadrant for signal modifiers.

    Returns:
        Updated stress level (0–10). All-zero scores are a no-op by design:
        a neutral message carries no signal and must not decay state.
    """
    a, w, e, h, b = (scores[k] for k in "AWEHB")
    if quadrant == "expert":
        w, h = w * 1.2, h * 1.3
    elif quadrant == "supporter":
        w = w * 1.3
    elif quadrant == "leader":
        h, a = h * 1.2, a * 1.2
    elif quadrant == "dreamer":
        e, h, b = e * 1.2, h * 1.2, b * 1.2

    if a == w == e == h == b == 0.0:
        return current_stress

    delta = 0.9 * w + 1.2 * e + 1.6 * h - 1.0 * a - 1.1 * b
    message_stress = max(0.0, min(current_stress + delta, 10.0))
    return max(0.0, min(0.8 * current_stress + 0.2 * message_stress, 10.0))


def energy_state(stress_level: float) -> str:
    """Map stress (0–10) to the three-band energy state."""
    if stress_level < 4.0:
        return "positive"
    if stress_level < 7.0:
        return "negative"
    return "neurotic"
