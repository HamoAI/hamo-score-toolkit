"""Reference scoring server — the license-compliant integration pattern as a service.

POST /score        {message, history?, current_stress?, quadrant?}
                   → {crisis, scores, stress, energy_state, latency_ms}
GET  /healthz      → model reachability probe

The pipeline is gate → score → smooth → bucket. Crisis-gated requests return
``{"crisis": {"triggered": true, ...}}`` and are NEVER sent to the model —
route them to your human/crisis pathway.
"""
from __future__ import annotations

import os
import time
from typing import Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from hamo_score import (CrisisGate, OllamaClient, energy_state, score_message,
                        update_stress)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
MODEL = os.environ.get("SCORE_MODEL", "hamo-score-0.6b")
TIMEOUT = float(os.environ.get("SCORE_TIMEOUT", "8"))

app = FastAPI(title="hamo-score reference server")
client = OllamaClient(base_url=OLLAMA_URL, model=MODEL, timeout=TIMEOUT)
gate = CrisisGate()


class ScoreRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None
    current_stress: Optional[float] = None
    quadrant: Optional[str] = None


@app.post("/score")
def score(req: ScoreRequest):
    t0 = time.time()
    r = score_message(client, req.message, req.history, crisis_gate=gate)
    out = {
        "crisis": {"triggered": r.crisis.triggered, "matched": r.crisis.matched},
        "scores": r.scores,
        "latency_ms": int((time.time() - t0) * 1000),
    }
    if r.scores is not None and req.current_stress is not None:
        stress = update_stress(r.scores, req.current_stress, req.quadrant)
        out["stress"] = round(stress, 3)
        out["energy_state"] = energy_state(stress)
    return out


@app.get("/healthz")
def healthz():
    try:
        raw = client.generate("给来访者最新消息打分（AWEHB，0.0-3.0）。\n最新消息: 探活")
        return {"ok": bool(raw), "model": MODEL}
    except Exception as e:  # pragma: no cover
        return {"ok": False, "model": MODEL, "error": str(e)[:120]}
