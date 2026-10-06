"""Reference implementation of the downstream state math.

AWEHB scores are per-message signals and are NOT meant to be consumed raw.
In Hamo's production engine they feed deterministic code: an exponential
blend smooths per-message noise ~5×, and the smoothed stress maps to one of
three energy states that gate how deep a conversation may go. This module is
that pattern, released as a reference — we recommend the same shape in any
deployment.

Formula (the model card prints the same formula and cites this module as the
reference implementation):
    session delta = 0.9·W + 1.2·E + 1.6·H − 1.0·A − 1.1·B   (quadrant-modified)
    new_stress    = 0.8 · history + 0.2 · clamp(history + delta, 0, 10)

Version caveat: these weights and the 4.0 / 7.0 cut-offs in energy_state() were
set on scores from the legacy rubrics (v7 and earlier).

v10 scores B under the legacy rubric again. On our 453-turn real final exam the
mean raw per-turn stress change computed from v10's read-outs is -0.72, against
-0.68 from the reference labels and -0.76 from v7 (each version's shipped q8,
llama.cpp + Metal, same exam and settings). Replaying sessions of three or more
turns, v10 ends 0.14 below the reference labels on average (v7: 0.10 below; the
pre-registered limit was ±0.15).
v10's A follows rubric v8, not the A these cut-offs were set on, so check the
buckets on your own data before they gate anything.

v9 scored B under a narrower ("crisp") rubric: B is 0 on most turns, the relief
term vanishes, and the same computation gives +0.37 per turn (replay drift
+0.51), so stress drifts upward. Re-tuning the cut-offs or the B weight does not repair that (a weight
multiplies a zero), and earlier advice here to "re-tune for v9" was not enough.
Do not feed v9 scores into this module; use v10 or v7.

版本注意：上述权重与 energy_state() 的 4.0 / 7.0 阈值按 legacy 口径（v7 及更早）的分数定。
v10 的 B 回到 legacy 口径：在 453 轮真实终评上，按 v10 的读数算出的平均每轮原始压力变化是
-0.72，参照标签是 -0.68，v7 是 -0.76（都是各版本随包 q8，llama.cpp + Metal，同一套考卷与设置）；
按会话回放（三轮及以上），v10 的末值平均比参照标签低 0.14（v7 低 0.10，预注册上限 ±0.15）。v10 的 A 用的是 v8 口径，
与定阈值时的 A 不同，让分桶把关任何事之前请先用你自己的数据核对。
v9 的 B 用的是更窄的 crisp 口径，多数轮次为 0，减压项消失，同样的计算得到每轮 +0.37（回放漂移 +0.51），压力会
持续上漂。重调阈值或 B 的权重都救不回来（权重乘的是 0）；此处早先「为 v9 重调」的建议并不够。
不要把 v9 的分数喂给本模块，请用 v10 或 v7。
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
    """Map stress (0–10) to the three-band energy state.

    The 4.0 / 7.0 cut-offs were set on legacy-rubric scores (v7 and earlier).
    Check them on your own data before they gate anything, and do not use them
    with v9 scores (see the module docstring).
    """
    if stress_level < 4.0:
        return "positive"
    if stress_level < 7.0:
        return "negative"
    return "neurotic"
