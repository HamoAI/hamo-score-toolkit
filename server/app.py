"""Reference scoring server — the license-compliant integration pattern as a service.

POST /score        {message, history?, current_stress?, quadrant?}
                   → {crisis, scores, latency_ms}, plus {stress, energy_state}
                     when current_stress is sent and scores is not null.
                     scores is null on a gate hit, or if the reply does not parse.
                     A gate hit is answered even if another field is invalid. Otherwise
                     an unknown field or an invalid value gets HTTP 422.
GET  /healthz      → scores a short probe and reports ok only if the reply parses as
                     a score within SCORE_TIMEOUT. HTTP 200 when ok, 503 when not, so
                     a model too busy to answer in time reports 503.

The pipeline is gate → score → smooth → bucket. Crisis-gated requests return
``{"crisis": {"triggered": true, ...}}`` and are NEVER sent to the model —
route them to your human/crisis pathway. The gate runs before any model call and
outside the worker pool, so a gated reply does not wait behind them.
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Dict, List, Literal, Optional

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from hamo_score import (CrisisGate, CrisisResult, OllamaClient, energy_state,
                        parse_scores, score_message, update_stress)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
MODEL = os.environ.get("SCORE_MODEL", "hamo-score-0.6b")
TIMEOUT = float(os.environ.get("SCORE_TIMEOUT", "8"))
HEALTHZ_TIMEOUT = float(os.environ.get("HEALTHZ_TIMEOUT", max(60.0, TIMEOUT)))
PROBE = "给来访者最新消息打分（AWEHB，0.0-3.0）。\n最新消息: 探活"

app = FastAPI(title="hamo-score reference server")
client = OllamaClient(base_url=OLLAMA_URL, model=MODEL, timeout=TIMEOUT)
# By default never shorter than SCORE_TIMEOUT: ollama aborts a load when its client disconnects,
# so this is the request that can finish loading a model that loads slowly.
probe_client = OllamaClient(base_url=OLLAMA_URL, model=MODEL, timeout=HEALTHZ_TIMEOUT)
gate = CrisisGate()


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"] = "user"
    content: str


class ScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    history: Optional[List[Turn]] = None
    current_stress: Optional[float] = Field(default=None, ge=0, le=10, allow_inf_nan=False, strict=True)
    quadrant: Optional[Literal["expert", "supporter", "leader", "dreamer"]] = None


def reply(crisis: CrisisResult, scores: Optional[Dict[str, float]], t0: float) -> dict:
    return {
        "crisis": {"triggered": crisis.triggered, "matched": crisis.matched},
        "scores": scores,
        "latency_ms": int((time.time() - t0) * 1000),
    }


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):
    # A gate hit needs no other field, so a bad one must not cost the message its verdict.
    message = exc.body.get("message") if isinstance(exc.body, dict) else None
    if isinstance(message, str):
        crisis = gate.check(message)
        if crisis.triggered:
            return JSONResponse(reply(crisis, None, time.time()))
    # The default reply echoes the rejected input: that would copy client text
    # into the response, and NaN or Infinity cannot be rendered as JSON (a 500).
    detail = [{k: e[k] for k in ("type", "loc", "msg")} for e in exc.errors()]
    return JSONResponse({"detail": detail}, status_code=422)


@app.post("/score")
async def score(req: ScoreRequest):
    t0 = time.time()
    crisis = gate.check(req.message)
    if crisis.triggered:
        return reply(crisis, None, t0)
    history = [t.model_dump() for t in req.history] if req.history else None
    r = await run_in_threadpool(score_message, client, req.message, history, crisis_gate=gate)
    out = reply(r.crisis, r.scores, t0)
    if r.scores is not None and req.current_stress is not None:
        stress = update_stress(r.scores, req.current_stress, req.quadrant)
        out["stress"] = round(stress, 3)
        out["energy_state"] = energy_state(stress)
    return out


@app.get("/healthz")
async def healthz():
    t0 = time.time()
    try:
        # Not /score's worker pool: a saturated server can still answer this.
        raw = await asyncio.to_thread(probe_client.generate, PROBE)
    except Exception as e:
        return _not_ok(str(e)[:200])
    if parse_scores(raw) is None:
        return _not_ok("reply did not parse as a score")
    secs = time.time() - t0
    if secs > TIMEOUT:  # a load finished, or a queue passed; /score would have given up
        return _not_ok(f"scored in {secs:.1f} s, over SCORE_TIMEOUT")
    return {"ok": True, "model": MODEL}


def _not_ok(error: str) -> JSONResponse:
    return JSONResponse({"ok": False, "model": MODEL, "error": error}, status_code=503)
