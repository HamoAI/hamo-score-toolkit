#!/usr/bin/env python3
"""Compare quantization builds — including the damage a headline number hides.

Why this exists: when we measured v7 builds of hamo-score-0.6b against our
internal 453-turn final exam (llama.cpp, neutral sampling), state-bucket
agreement moved only 0.4 points from q8_0 to q4_k_m (97.1% -> 96.7%) — near
enough to call them equivalent. Underneath, q4_k_m still *attenuates*
one-sidedly exactly where a scorer must not go quiet: on the 37 crisis-adjacent
turns (gold W >= 2.5) of that split it scored W lower than q8_0 on 6 and higher
on 1 (mean W 2.58 -> 2.50), though it added no crisis miss there. (q6_k was indistinguishable
from q8_0.) State buckets are coarse enough to absorb a damped signal, so bucket
agreement alone will never surface it.

An earlier version of this note cited a larger gap ("every dimension drifts
toward zero"); that compared our v6.1 q8_0 against community GGUF builds made
from older (v4) weights, so it was mostly a version gap, not a quantization gap.
See eval/README.md for the v7 table.

This script runs the toolkit's synthetic exam against two or more deployments
and reports three things per pair:

  1. per-build agreement (the numbers you'd publish),
  2. head-to-head divergence (identical read-outs, same bucket, |Δstress|),
  3. **directional attenuation** — for each dimension, how often build B scores
     LOWER than build A vs higher, and the same split restricted to the exam's
     high-withdrawal turns. A one-sided split there is the finding.

Usage (each build is an ollama tag you created from a different GGUF). The repo
ships only server/Modelfile — copy it once per extra build and change only its
FROM line. No v7 q6_k/q4_k_m GGUF is published; quantize the v7 weights yourself
(llama.cpp: convert_hf_to_gguf.py to f16, then llama-quantize; see eval/README.md).

    cp server/Modelfile Modelfile.q4                    # then edit FROM: ...q4_k_m.gguf
    ollama create hamo-q8  -f server/Modelfile          # FROM: the shipped q8_0 GGUF
    ollama create hamo-q4  -f Modelfile.q4
    python eval/compare_quants.py --models hamo-q8 hamo-q4

The exam is synthetic and teacher-labeled — no real client data — so anyone can
run this. Numbers are not comparable to ours in absolute terms (different exam);
the *shape* of the comparison is what transfers.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hamo_score import OllamaClient, build_prompt, energy_state, parse_scores, update_stress

HERE = os.path.dirname(os.path.abspath(__file__))
DIMS = "AWEHB"
# Stress level the bucket walk starts from. Fixed for all builds so the only
# variable is the read-out itself.
BASELINE_STRESS = 5.0
# A turn counts as crisis-adjacent when the teacher labelled withdrawal this
# high. This is the subset where attenuation stops being cosmetic.
HIGH_W = 1.5


def run_build(model: str, base_url: str, exam: list, timeout: float) -> dict:
    client = OllamaClient(base_url=base_url, model=model, timeout=timeout)
    preds, bad, lats = {}, 0, []
    t0 = time.time()
    for i, q in enumerate(exam, 1):
        t1 = time.time()
        out = client.generate(build_prompt(q["message"], q.get("context")))
        lats.append(time.time() - t1)
        p = parse_scores(out)
        if p is None:
            bad += 1
            continue
        preds[q["id"]] = p
        if i % 50 == 0:
            print(f"  {model}: {i}/{len(exam)}  {time.time()-t0:.0f}s", file=sys.stderr)
    return {"model": model, "preds": preds, "bad": bad, "lats": sorted(lats)}


def report_build(res: dict, gold: dict) -> None:
    preds, ids = res["preds"], sorted(res["preds"])
    n = len(ids)
    print(f"\n== {res['model']} (n={n}, unparseable {res['bad']}) ==")
    per_dim = {}
    for d in DIMS:
        diffs = [abs(gold[i][d] - preds[i][d]) for i in ids]
        per_dim[d] = sum(1 for x in diffs if x <= 0.5) / n
    print("  dim ±0.5: " + " ".join(f"{d}{per_dim[d]:.0%}" for d in DIMS)
          + f"  | mean {statistics.mean(per_dim.values()):.1%}")
    combos = len({tuple(preds[i][d] for d in DIMS) for i in ids})
    print(f"  JSON validity {n/(n+res['bad']):.1%} | distinct read-outs {combos}"
          f" | latency P50 {res['lats'][len(res['lats'])//2]:.2f}s")


def compare(a: dict, b: dict, gold: dict) -> None:
    ids = sorted(set(a["preds"]) & set(b["preds"]))
    n = len(ids)
    ident = sum(1 for i in ids if all(a["preds"][i][d] == b["preds"][i][d] for d in DIMS))
    same_bucket, ds = 0, []
    for i in ids:
        sa = update_stress(a["preds"][i], BASELINE_STRESS)
        sb = update_stress(b["preds"][i], BASELINE_STRESS)
        ds.append(abs(sa - sb))
        if energy_state(sa) == energy_state(sb):
            same_bucket += 1
    print(f"\n== {a['model']} vs {b['model']} — head to head (n={n}) ==")
    print(f"  identical read-outs {ident/n:.1%} | same state bucket {same_bucket/n:.1%}"
          f" | mean |Δstress| {statistics.mean(ds):.3f}")

    print(f"\n== directional attenuation: is {b['model']} systematically lower? ==")
    print(f"  {'dim':<5}{'lower':>7}{'higher':>8}{'same':>7}{'mean Δ':>9}")
    for d in DIMS:
        lo = sum(1 for i in ids if b["preds"][i][d] < a["preds"][i][d])
        hi = sum(1 for i in ids if b["preds"][i][d] > a["preds"][i][d])
        md = statistics.mean(b["preds"][i][d] - a["preds"][i][d] for i in ids)
        print(f"  {d:<5}{lo:>7}{hi:>8}{n-lo-hi:>7}{md:>+9.3f}")

    hi_ids = [i for i in ids if gold[i]["W"] >= HIGH_W]
    if hi_ids:
        lo = sum(1 for i in hi_ids if b["preds"][i]["W"] < a["preds"][i]["W"])
        up = sum(1 for i in hi_ids if b["preds"][i]["W"] > a["preds"][i]["W"])
        ma = statistics.mean(a["preds"][i]["W"] for i in hi_ids)
        mb = statistics.mean(b["preds"][i]["W"] for i in hi_ids)
        gm = statistics.mean(gold[i]["W"] for i in hi_ids)
        print(f"\n  High-withdrawal subset (teacher W ≥ {HIGH_W}, n={len(hi_ids)}):")
        print(f"    {b['model']} lower on {lo}, higher on {up}")
        print(f"    mean W — teacher {gm:.2f} | {a['model']} {ma:.2f} | {b['model']} {mb:.2f}")
        if lo >= 3 * max(up, 1) and mb < ma - 0.05:
            print("    ⚠️  one-sided damping on the turns that matter most. If this build")
            print("        gates safety-relevant behaviour, lower your withdrawal thresholds")
            print("        to compensate — and keep deterministic crisis detection upstream.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True,
                    help="two or more ollama tags, reference build first")
    ap.add_argument("--base-url", default="http://127.0.0.1:11434")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    exam = [json.loads(l) for l in open(os.path.join(HERE, "synthetic_exam.jsonl"))]
    if args.limit:
        exam = exam[: args.limit]
    gold = {q["id"]: q["labels"] for q in exam}
    print(f"Exam: {len(exam)} synthetic questions | builds: {', '.join(args.models)}")

    results = []
    for m in args.models:
        r = run_build(m, args.base_url, exam, args.timeout)
        report_build(r, gold)
        results.append(r)

    for r in results[1:]:
        compare(results[0], r, gold)

    print("\nReference build is the first --models entry. Bucket agreement alone is not")
    print("enough to clear a build for gating use — read the attenuation table.")


if __name__ == "__main__":
    main()
