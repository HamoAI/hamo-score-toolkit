#!/usr/bin/env python3
"""Deployment self-check: is your server serving hamo-score-0.6b as measured?

Runs two sections against YOUR deployment:
  1. Scoring exam — 195 synthetic, teacher-labeled questions. Measures JSON
     validity, dimension-level agreement (±0.5) vs teacher labels, the number
     of distinct read-outs, latency.
  2. Gate exam — 10 crisis/near-miss phrasings. Verifies the CrisisGate
     catches what it must and stays quiet on dark-humor lookalikes.

Usage:
    python eval/run_exam.py                       # ollama on localhost
    python eval/run_exam.py --base-url http://myhost:11434 --model my-tag
    python eval/run_exam.py --labels pre_v9       # checking a v7 deployment on purpose

The exam's A and B labels follow the v9 rubrics (the default). Each question
also keeps its pre-v9 labels, which is what a v7 deployment should be checked
against — v9 changed what A and B mean.

What a pass covers: the exam always builds the prompt with the toolkit's
build_prompt(), sends the toolkit's pinned sampling (SAMPLING_OPTIONS:
temperature 0, repeat_penalty 1.0, top_k 0, top_p 1.0) with every request, and
parses with parse_scores(). A pass therefore certifies the served weights and
the server's chat template, num_predict and stop settings, called through the
toolkit's own prompt, sampling and parser. Request options override the
Modelfile, so this exam cannot catch a Modelfile that omits repeat_penalty 1.0,
nor a prompt, sampling setting or parser in your own service — check those
separately (`ollama show <tag> --parameters`; compare your prompt with
build_prompt()).

Compare your numbers against eval/README.md. Deviations far outside the
reference band usually mean the wrong GGUF or the wrong label set, a wrong chat
template, a server that ignores request options, or an over-aggressive
quantization — not a worse model. The dimension-level number alone cannot rule
out a broken deployment: most labels are 0 or 0.5, so a constant output lands
close to the band. The script prints those trivial baselines for the label set
in use and warns when the deployment produced few distinct read-outs (a
correctly served model produces several dozen on the full exam).
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


def constant_agreement(exam, label_key, value):
    """Dimension-level agreement a deployment would get by always answering `value`."""
    return statistics.mean(
        statistics.mean(1 if abs(value - q[label_key][d]) <= 0.5 else 0 for q in exam)
        for d in "AWEHB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:11434")
    ap.add_argument("--model", default="hamo-score-0.6b")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--labels", choices=["v9", "pre_v9"], default="v9",
                    help="label set to grade against: v9 (default) or pre_v9 (for a v7 deployment)")
    args = ap.parse_args()
    label_key = "labels" if args.labels == "v9" else "labels_pre_v9"
    client = OllamaClient(base_url=args.base_url, model=args.model, timeout=30)

    # ---- Section 1: scoring ----
    exam = [json.loads(l) for l in open(os.path.join(HERE, "synthetic_exam.jsonl"))]
    if args.limit:
        exam = exam[: args.limit]
    print(f"Section 1 — scoring exam: {len(exam)} questions, graded against {args.labels} labels")
    per = {d: [] for d in "AWEHB"}
    lats, invalid, readouts = [], 0, set()
    for i, q in enumerate(exam, 1):
        t0 = time.time()
        raw = client.generate(build_prompt(q["message"], q.get("context")))
        lats.append(time.time() - t0)
        s = parse_scores(raw)
        if s is None:
            invalid += 1
            continue
        readouts.add(tuple(s[d] for d in "AWEHB"))
        for d in "AWEHB":
            per[d].append(1 if abs(s[d] - q[label_key][d]) <= 0.5 else 0)
        if i % 50 == 0:
            print(f"  {i}/{len(exam)}", file=sys.stderr)
    dims = {d: (sum(v) / len(v) if v else 0.0) for d, v in per.items()}
    avg = statistics.mean(dims.values())
    lats.sort()
    print(f"  JSON validity : {(len(exam)-invalid)/len(exam):.1%}")
    print(f"  dim agreement : {avg:.1%}  ({' '.join(f'{d}{dims[d]:.0%}' for d in 'AWEHB')})")
    print(f"  trivial floor : constant 0.5 → {constant_agreement(exam, label_key, 0.5):.1%},"
          f" all zeros → {constant_agreement(exam, label_key, 0.0):.1%}"
          f"  (same labels; a score near these proves nothing)")
    print(f"  read-outs     : {len(readouts)} distinct across {len(exam) - invalid} parsed answers")
    if len(readouts) < max(3, len(exam) // 10):
        print("  ⚠️  few distinct read-outs — the deployment looks (near-)constant. Check the GGUF,"
              " the chat template and that the server honours request options before trusting"
              " the agreement number.")
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
