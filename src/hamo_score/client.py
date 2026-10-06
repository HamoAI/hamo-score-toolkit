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


# Neutral sampling, sent with every request. The output is highly repetitive
# ('"A": 0.0, "W": 0.0, ...'), so any repeat penalty pushes scores away from 0 —
# with repeat_penalty 1.1 (ollama's default) the fabrication rate on the old B exam rose in each of the
# four versions we measured (v6.1, v7 and v10 under the legacy key, v9 under the crisp key). v10 q8,
# old B exam (legacy key), llama.cpp + Metal: 3/104 -> 15/104 (2.9% -> 14.4%). Request options
# override the Modelfile, so a Modelfile that omits these can no longer silently break scoring.
# 中性采样，随每次请求发送：输出里大量重复的 "0.0"，任何重复惩罚都会把分数推离 0
# （repeat_penalty 取 ollama 的默认值 1.1 时，我们量过的四个版本在旧 B 卷上的造分率都升高：v6.1、v7、v10 按 legacy 答案，
# v9 按 crisp 答案；v10 随包 q8，旧 B 卷（legacy 答案），llama.cpp + Metal：3/104 → 15/104，即 2.9% → 14.4%）。
# 请求参数优先于 Modelfile，所以即使 Modelfile 漏写，评分也不会再被悄悄带偏。
SAMPLING_OPTIONS = {"temperature": 0, "repeat_penalty": 1.0, "top_k": 0, "top_p": 1.0}


class OllamaClient:
    """Scores via a local/remote ollama server (or any /api/generate clone)."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434",
                 model: str = "hamo-score-0.6b", timeout: float = 8.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        payload = {"model": self.model, "prompt": prompt, "stream": False,
                   "keep_alive": -1, "options": dict(SAMPLING_OPTIONS)}
        req = urllib.request.Request(
            f"{self.base_url}/api/generate", json.dumps(payload).encode(),
            {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read()).get("response", "")


class TransformersClient:
    """Scores via HuggingFace transformers (GPU/CPU). Needs: pip install "hamo-score[transformers]"
    (transformers, torch and accelerate). Lazy-imports torch."""

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
            # Greedy + explicit repetition_penalty=1.0, so a generation_config.json
            # carrying a penalty (e.g. from a fine-tune) cannot override it.
            out = self.model.generate(**inputs, max_new_tokens=80, do_sample=False,
                                      repetition_penalty=1.0)
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
