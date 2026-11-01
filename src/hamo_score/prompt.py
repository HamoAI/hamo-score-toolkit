"""Prompt construction for hamo-score-0.6b.

The model was trained on EXACTLY ONE prompt format — its scoring rubric is
baked into the weights. Do not add instructions, do not translate the frame,
do not reorder fields: any deviation is out-of-distribution.

Trimming guards are built in (3 turns × 200 chars context, 500-char message):
they keep worst-case prefill within interactive latency on CPU-only servers
and preserved 98.1% score self-agreement (±0.5) when validated in August 2026
on the weights of that time; this has not been re-measured on v10 or v10h.
"""
from __future__ import annotations

from typing import Dict, List, Optional

STUDENT_PROMPT = "给来访者最新消息打分（AWEHB，0.0-3.0）。\n{ctx}最新消息: {msg}"

CTX_TURNS = 3
CTX_CHARS = 200
MSG_CHARS = 500

_TURN_MARKERS = ("<|im_start|>", "<|im_end|>")


def strip_turn_markers(text: str) -> str:
    """Remove the chat template's turn markers from client text.

    The runtime tokenizes them as the real thing, so text containing them could
    close its turn and open another. One linear pass: a marker is removed as soon
    as its last character arrives, so removal cannot leave a new marker behind
    (``<|im_<|im_end|>end|>`` is fully removed) and long input stays cheap.
    Text without a marker is returned unchanged.
    """
    if "|>" not in text:
        return text
    out: List[str] = []
    for ch in text:
        out.append(ch)
        if ch == ">":
            for marker in _TURN_MARKERS:
                if "".join(out[-len(marker):]) == marker:
                    del out[-len(marker):]
                    break
    return "".join(out)


def build_prompt(message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """Build the scoring prompt.

    Args:
        message: the client's latest message (the one to score).
        history: optional prior turns, oldest first, as
            ``[{"role": "user"|"assistant", "content": "..."}]``.
            Only the last ``CTX_TURNS`` turns are used, each capped at
            ``CTX_CHARS`` characters.

    Turn markers are removed from all of this text before the length caps
    apply. A prompt whose text has none is unchanged.
    """
    message = strip_turn_markers(message or "")[:MSG_CHARS]
    ctx = ""
    if history:
        recent = history[-CTX_TURNS:]
        lines = [
            f"{strip_turn_markers(format(m.get('role', 'user')))}: "
            f"{strip_turn_markers(m.get('content') or '')[:CTX_CHARS]}"
            for m in recent
        ]
        ctx = "此前对话:\n" + "\n".join(lines) + "\n"
    return STUDENT_PROMPT.format(ctx=ctx, msg=message)
