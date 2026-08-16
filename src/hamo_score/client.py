"""Backends and the one-call convenience API.

The safe default path::

    from hamo_score import OllamaClient, score_message
    result = score_message(OllamaClient(), "今天试着出门散了个步", history=[...])

``score_message`` runs the crisis gate FIRST (license §3c pattern). Bypassing
it requires an explicit, greppable ``unsafe_disable_crisis_gate=True``.
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .parse import parse_scores
from .prompt import build_prompt
from .safety import CrisisGate, CrisisResult


class OllamaClient:
    """Scores via a local/remote ollama server (or any /api/generate clone)."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434",
                 model: str = "hamo-score-0.6b", timeout: float = 8.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        payload = {"model": self.model, "prompt": prompt, "stream": False,
                   "keep_alive": -1, "options": {"temperature": 0}}
        req = urllib.request.Request(
            f"{self.base_url}/api/generate", json.dumps(payload).encode(),
            {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read()).get("response", "")


class TransformersClient:
    """Scores via HuggingFace transformers (GPU/CPU). Lazy-imports torch."""

    def __init__(self, model_id: str = "HamoAI/hamo-score-0.6b", device: Optional[str] = None):
        from transformers import AutoModelForCausalLM, AutoTokenizer  # lazy
        import torch
        self._torch = torch
        self.tok = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id, torch_dtype=torch.bfloat16,
            device_map=device or "auto")

    def generate(self, prompt: str) -> str:
        text = self.tok.apply_chat_template(
            [{"role": "user", "content": prompt}],
            add_generation_prompt=True, tokenize=False, enable_thinking=False)
        inputs = self.tok(text, return_tensors="pt").to(self.model.device)
        with self._torch.no_grad():
            out = self.model.generate(**inputs, max_new_tokens=80, do_sample=False)
        return self.tok.decode(out[0][inputs["input_ids"].shape[1]:])


@dataclass
class ScoreResult:
    scores: Optional[Dict[str, float]]
    crisis: CrisisResult
    raw: str = ""

    @property
    def ok(self) -> bool:
        return self.scores is not None and not self.crisis.triggered


def score_message(client, message: str,
                  history: Optional[List[Dict[str, str]]] = None,
                  crisis_gate: Optional[CrisisGate] = None,
                  unsafe_disable_crisis_gate: bool = False) -> ScoreResult:
    """Gate → prompt → generate → parse, in the order the license requires.

    When the crisis gate triggers, scoring is SKIPPED and ``result.crisis``
    carries the matched terms — route the user to your human/crisis pathway.
    """
    if not unsafe_disable_crisis_gate:
        gate = crisis_gate or CrisisGate()
        crisis = gate.check(message)
        if crisis.triggered:
            return ScoreResult(scores=None, crisis=crisis)
    else:
        crisis = CrisisResult(triggered=False)

    raw = client.generate(build_prompt(message, history))
    return ScoreResult(scores=parse_scores(raw), crisis=crisis, raw=raw)
