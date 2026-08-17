#!/usr/bin/env python3
"""Deployment self-check: did you wire hamo-score-0.6b correctly?

Runs two sections against YOUR deployment:
  1. Scoring exam — 195 synthetic, teacher-labeled questions. Measures JSON
     validity, dimension-level agreement (±0.5) vs teacher labels, latency.
  2. Gate exam — 10 crisis/near-miss phrasings. Verifies the CrisisGate
     catches what it must and stays quiet on dark-humor lookalikes.

Usage:
    python eval/run_exam.py                       # ollama on localhost
    python eval/run_exam.py --base-url http://myhost:11434 --model my-tag

Compare your numbers against eval/README.md. Deviations far outside the
reference band usually mean a wrong prompt template, a broken parser, or an
over-aggressive quantization — not a worse model.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hamo_score import CrisisGate, OllamaClient, build_prompt, parse_scores

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:11434")
    ap.add_argument("--model", default="hamo-score-0.6b")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    client = OllamaClient(base_url=args.base_url, model=args.model, timeout=30)

    # ---- Section 1: scoring ----
    exam = [json.loads(l) for l in open(os.path.join(HERE, "synthetic_exam.jsonl"))]
    if args.limit:
        exam = exam[: args.limit]
    print(f"Section 1 — scoring exam: {len(exam)} questions")
    per = {d: [] for d in "AWEHB"}
    lats, invalid = [], 0
    for i, q in enumerate(exam, 1):
        t0 = time.time()
        raw = client.generate(build_prompt(q["message"], q.get("context")))
        lats.append(time.time() - t0)
        s = parse_scores(raw)
        if s is None:
            invalid += 1
            continue
        for d in "AWEHB":
            per[d].append(1 if abs(s[d] - q["labels"][d]) <= 0.5 else 0)
        if i % 50 == 0:
            print(f"  {i}/{len(exam)}", file=sys.stderr)
    dims = {d: (sum(v) / len(v) if v else 0.0) for d, v in per.items()}
    avg = statistics.mean(dims.values())
    lats.sort()
    print(f"  JSON validity : {(len(exam)-invalid)/len(exam):.1%}")
    print(f"  dim agreement : {avg:.1%}  ({' '.join(f'{d}{dims[d]:.0%}' for d in 'AWEHB')})")
    print(f"  latency       : P50 {lats[len(lats)//2]:.2f}s  P95 {lats[int(len(lats)*0.95)]:.2f}s")

    # ---- Section 2: crisis gate ----
    gate = CrisisGate()
    cases = [json.loads(l) for l in open(os.path.join(HERE, "gate_cases.jsonl"))]
    wrong = [c["id"] for c in cases
             if gate.check(c["message"]).triggered != (c["expect"] == "triggered")]
    print(f"Section 2 — crisis gate: {len(cases)-len(wrong)}/{len(cases)} correct"
          + (f"  ✗ {wrong}" if wrong else "  ✓"))

    print("\nCompare against the reference band in eval/README.md.")


if __name__ == "__main__":
    main()
