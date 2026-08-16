"""Crisis gate — the non-negotiable upstream guard.

hamo-score is NOT a crisis detector, and the model license (HAMO-RAIL-S §3c)
requires consumer-facing deployments to handle crisis content with an
independent deterministic mechanism UPSTREAM of the model. This module is the
reference implementation of that pattern: a keyword gate that runs BEFORE
scoring and short-circuits the pipeline when triggered.

The gate is deliberately simple, deterministic, and auditable. Extend the
word lists for your population; never replace this layer with a model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

ZH_CRISIS = [
    "自杀", "自残", "不想活", "想死", "去死", "结束生命", "结束自己",
    "活不下去", "活着没意思了", "割腕", "跳楼", "安眠药", "烧炭",
    "遗书", "了结", "解脱了", "永远消失",
]
EN_CRISIS = [
    "suicide", "kill myself", "end my life", "self-harm", "self harm",
    "hurt myself", "cut myself", "don't want to live", "dont want to live",
    "better off dead", "overdose", "end it all",
]

DISCLOSURE_ZH = "我是 AI 支持工具，不是执业治疗师。如果你正处于危机中，请立即联系当地的危机热线或专业人员。"
DISCLOSURE_EN = ("I am an AI support tool, not a licensed therapist. "
                 "If you are in crisis, please contact a local crisis line or a professional immediately.")


@dataclass
class CrisisResult:
    triggered: bool
    matched: List[str] = field(default_factory=list)


class CrisisGate:
    """Deterministic keyword gate. Run on every message BEFORE scoring."""

    def __init__(self, extra_keywords: Optional[List[str]] = None):
        self.keywords = ZH_CRISIS + EN_CRISIS + (extra_keywords or [])

    def check(self, message: str) -> CrisisResult:
        low = (message or "").lower()
        hits = [k for k in self.keywords if k.lower() in low]
        return CrisisResult(triggered=bool(hits), matched=hits)
