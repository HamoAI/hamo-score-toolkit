"""Parse model output into AWEHB scores.

The model may emit an empty ``<think>`` block before the JSON — parsing must
tolerate that. Scores are clamped to [0, 3] and snapped to the 0.5 grid the
model was trained on.
"""
from __future__ import annotations

import json
import re
from typing import Dict, Optional

DIMS = "AWEHB"
_JSON_RE = re.compile(r"\{[^{}]*\}")


def parse_scores(text: str) -> Optional[Dict[str, float]]:
    """Extract ``{"A": .., "W": .., "E": .., "H": .., "B": ..}`` from raw output.

    Returns None if no valid score object is found.
    """
    m = _JSON_RE.search(text or "")
    if not m:
        return None
    try:
        d = json.loads(m.group())
    except json.JSONDecodeError:
        return None
    if not all(k in d and isinstance(d[k], (int, float)) for k in DIMS):
        return None
    return {k: _snap(float(d[k])) for k in DIMS}


def _snap(v: float) -> float:
    """Clamp to [0, 3] and snap to the 0.5 grid."""
    v = max(0.0, min(3.0, v))
    return round(v * 2) / 2
