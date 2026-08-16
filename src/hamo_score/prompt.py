"""Prompt construction for hamo-score-0.6b.

The model was trained on EXACTLY ONE prompt format — its scoring rubric is
baked into the weights. Do not add instructions, do not translate the frame,
do not reorder fields: any deviation is out-of-distribution.

Trimming guards are built in (3 turns × 200 chars context, 500-char message):
they keep worst-case prefill within interactive latency on CPU-only servers
and were validated to preserve 98.1% score self-agreement (±0.5).
"""
from __future__ import annotations

from typing import Dict, List, Optional

STUDENT_PROMPT = "给来访者最新消息打分（AWEHB，0.0-3.0）。\n{ctx}最新消息: {msg}"

CTX_TURNS = 3
CTX_CHARS = 200
MSG_CHARS = 500


def build_prompt(message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """Build the scoring prompt.

    Args:
        message: the client's latest message (the one to score).
        history: optional prior turns, oldest first, as
            ``[{"role": "user"|"assistant", "content": "..."}]``.
            Only the last ``CTX_TURNS`` turns are used, each capped at
            ``CTX_CHARS`` characters.
    """
    message = (message or "")[:MSG_CHARS]
    ctx = ""
    if history:
        recent = history[-CTX_TURNS:]
        lines = [
            f"{m.get('role', 'user')}: {(m.get('content') or '')[:CTX_CHARS]}"
            for m in recent
        ]
        ctx = "此前对话:\n" + "\n".join(lines) + "\n"
    return STUDENT_PROMPT.format(ctx=ctx, msg=message)
