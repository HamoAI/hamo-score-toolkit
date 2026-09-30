# Fine-tuning hamo-score-0.6b for your own population

**EN** | [中文](#中文)

This guide is for engineers at professional mental-wellness institutions who
downloaded [HamoAI/hamo-score-0.6b](https://huggingface.co/HamoAI/hamo-score-0.6b)
and want to adapt it — to a new language, a new population, a different
register — using their own **consented** data.

It is the distilled playbook of ten model generations. Four of them we
**rejected** after training completed: v5 and v6 for crisis-recall
regressions, v8 and v8.1 on their pre-registered acceptance gates. The current
release, v9, **failed two of its own five pre-registered gates, one of them a
safety gate, and was released anyway by an explicit, recorded founder
override**. §8 says what failed and why we publish it. The rejections taught
us more than the successes, so they are in here as rules. Everything below
was learned on one MacBook plus API labelling (about US$7 of API spend through
v6.1, more for the v7–v9 re-labels). This is not a cluster-scale process.

One framing before anything else: hamo-score is a **measuring instrument**.
It is not a chatbot, not a diagnostic tool, not a therapist, and **not a
crisis detector**. Crisis handling belongs to a deterministic gate **upstream**
of the model ([`CrisisGate`](../src/hamo_score/safety.py) — required by license
HAMO-RAIL-S §3(c) for consumer-facing mental-wellness deployments, and by this
project's architecture in every deployment). Nothing in this guide changes that; several
things in this guide exist specifically to keep fine-tuning from accidentally
changing it.

---

## 1. Do you actually need to fine-tune?

Most adaptation needs are cheaper than training, because most of the system
is code, not weights:

| You want to… | Do this instead of fine-tuning |
|---|---|
| Catch crisis phrasings specific to your population (slang, dialect, another language) | Extend the gate: `CrisisGate(extra_keywords=[...])`. The gate is deterministic code — extending it is a one-line change and takes effect immediately. **Never** try to fix crisis coverage in the weights. |
| Different sensitivity in downstream decisions | Tune the deterministic math — the smoothing weights and state-bucket thresholds in [`stress.py`](../src/hamo_score/stress.py) are Apache-2.0 reference code, meant to be adapted. |
| Disagree with scores on individual messages | Remember scores are per-message signals feeding a `0.8·history + 0.2·message` smoother — single-message noise is absorbed by design. If a *pattern* of disagreement persists, file it with the repo's score-disagreement issue template; patterns feed the gold-label program. |
| Slightly different prompt/wording ideas | Don't. The model was trained on exactly one prompt format ([`build_prompt`](../src/hamo_score/prompt.py)); any deviation is out-of-distribution. |

**Upgrading to v9 is itself a re-tuning job.** v9 changed what A and B mean
(A rubric v8; a "crisp" B that counts only explicit boundary markers) and
scores both lower: on our real final exam, mean A 0.45 and mean B 0.08 for
v9, against 0.67 and 0.92 for v7, and B is 0.0 on 94% of those turns (v7:
52%). A and B both carry negative weights in the stress formula, so the same
conversation computes **higher** stress under v9. The toolkit's stress
weights and bucket cut-offs are unchanged and were set on pre-v9 scores:
re-tune them on your own data before the buckets gate anything, and do not
compare A or B scores across the v7 → v9 boundary. If you need the old
semantics, the v7 weights stay available (see the model card's Versions
section).

Fine-tune when the **linguistic footprint** your population produces is
materially different from the training distribution: a language the model is
weak in (it is Chinese-primary: about zh 76% / en 13% / mixed zh-en 11%,
measured on the latest message of each v9 training row), a distinct
register (adolescents, elderly speakers, a dialect), or a rubric variant your
clinical team has formally defined.

Do **not** fine-tune to turn the model into a crisis detector. That inverts
the architecture: the gate owns crisis, the model reads state on everything
the gate lets through. A model that "handles" crisis invites someone to remove
the gate — which is exactly what license §3(c) forbids.

---

## 2. Data red lines — read before collecting anything

These are requirements, not suggestions. They are the reason this model could
be released at all.

**R1. Informed consent for any real data.** Our own training corpus is
synthetic except, since v6.1, 440 real conversation turns from three
company-internal staff members (the founder and two staff counselors) with
their explicit consent, upsampled ×3 (~8% of the v6.1 corpus, ~6.5% of
v9's 20,187 training rows). External client/user
conversations **never** enter training, by construction. Adopt the same
construction: real client data may serve as *exam* material (held-out
evaluation, where your governance and local law permit), and enters *training*
only with explicit, documented, revocable consent from the person who wrote
the words. "It's de-identified" is not consent.

**R2. Real-data labels must pass crisis-artifact screening before entering
training.** This is the lesson of our rejected v6. Production systems that
short-circuit crisis upstream (as ours does, and as yours must) produce a
poisonous label artifact: messages containing explicit crisis language that
carry near-zero scores, because the incumbent scorer never really processed
them. Three such rows — crisis text, all-zero labels — rode into v6's training
set along with the real data. Result: crisis W-misses on the 453-turn final
exam jumped from 3 (the incumbent, v4) to 9, and the entire generation was
rejected. The screening rule:

1. Run every candidate real row's **text** through your crisis word list
   (the gate's own list is a good start).
2. Every row that hits the list gets human review.
3. Any row whose label contradicts its text (crisis text, benign label) is
   removed or relabeled before training. No exceptions for "it's only 3 rows"
   — 3 rows out of ~16,000 was enough to triple our miss count (3 → 9).

**R3. Never train the model to detect crisis.** The deterministic gate owns
crisis detection. High W-recall on crisis-adjacent text is defense-in-depth
and we track it (see §6, and since v9 a dedicated W safety exam, see §8), but
it is never the defense.

**R4. Hygiene.** De-identify everything, and name what you did accurately:
our own export is *pseudonymised*, not anonymised (a fixed salt, full
timestamps, regex-only text redaction), so it is still personal data and a
deletion request still reaches it. Real data never goes into git
(`.gitignore` it before the first export exists). Keep a one-page data map:
what you collected, whose consent, which file, which split.

---

## 3. Build your exam before your curriculum

The first artifact of the project is not training data. It is a held-out exam
of **real** turns from your population that will **never be trained on** — and
a qualified teacher. Order matters: if the exam comes second, you will
unconsciously build it out of what your model is good at.

**Split three ways.** Ours: 1,198 real pseudonymised turns → a
teacher-qualification / calibration set (440) and a 758-turn held-out set,
split again into a 305-turn selection split and a 453-turn final. The final
exists for the shipping decision — never for checkpoint selection (v7 is the
one exception, see §6), never for prompt iteration. Score as little as
possible on it: we have also scored checkpoints we were not shipping there,
for reference — several of v7's, whose scores later set gate 4's floor (§6),
and v8.1's iteration 7,200 — and every extra look is a little selection
pressure (§8, lesson 7). If your calibration set
later enters training (ours did, in v6.1, under R1 consent), carve a fresh
selection split out of held-out territory first; a set you train on can no
longer select checkpoints.

**Record decision context with each row.** Store, alongside message, context
and gold scores, the prior stress level (and any per-user modifier metadata)
at the moment the message arrived. You need it to compute decision-level
agreement (§6) — without it you can only measure dimensions, and dimensions
are the wrong headline number.

**Qualify your teacher before it labels anything.** Whatever model you use to
label training data (we use `deepseek-chat` with the production rubric; label
at temperature 0 — our corpora through v6.1 were labelled at a non-zero
temperature, and re-labelling the corpus at temperature 0 was the main change
in v7), make it sit your real exam first. Our bar on 440 real turns:
dimension-level ±0.5 agreement ~89% (88.7%), decision-level 97.5%. Look at
per-dimension numbers, not just the mean: our teacher first scored 72% on the
Boundary dimension — a fixable operational-definition mismatch, closed to 78%
(90% at ±1.0) with calibration notes in the rubric prompt. A broken dimension
hides comfortably inside a good average. A bulk re-label can also silently
undo earlier deliberate fixes: v7's temperature-0 re-label dropped an earlier
W rule (despair followed by an action keeps W ≥ 1.5), and v9's W safety
repair had to restore it (285 rows raised, under that rule plus a new one:
help-seeking does not cancel suicidal ideation, W ≥ 2.5). After any
re-label, re-check the rules your earlier fixes encoded. When the rubric
changes, qualify again, column by column: for v9 the teacher ran one prompt
for A (rubric v8) and another for B (crisp), and each passed its own
qualification before it labelled anything — the B prompt only after its
answer key was re-graded and the founder's rulings were added to the prompt
(§8, lesson 3). A farewell-rule variant of the A prompt, qualified
separately, flagged farewell signals and labelled the A column of the new
synthetic patches, so two A prompts labelled training data. A further
prompt, which re-scored W on keyword-selected rows for the safety repair,
was not separately qualified; we accepted only its raises.

**Measure your incumbent's self-consistency.** We scored the same messages
twice with the reference scorer in two live environments, in small spot
checks (about a dozen messages each): it agreed with itself only 94–98% at
dimension level. Treat that as a rough practical ceiling, not a measured one.
Knowing it stops you from burning weeks chasing 99% against a gold standard
that is itself only roughly 95% reproducible.

**If you build an LLM judge** for anything that touches humans: it must reach
kappa ≥ 0.6 agreement with a licensed professional before you trust it.

---

## 4. Training data format

### The exact shape

Training rows are chat-format JSONL, one per line, as consumed by `mlx-lm`:

```json
{"messages": [
  {"role": "user", "content": "给来访者最新消息打分（AWEHB，0.0-3.0）。\n此前对话:\nassistant: 这周过得怎么样？\n最新消息: 今天试着出门散了个步"},
  {"role": "assistant", "content": "{\"A\": 1.0, \"W\": 0.0, \"E\": 0.0, \"H\": 0.0, \"B\": 0.0}"}
]}
```

(The label follows the v9 rubric: a one-off walk is mid-band agency, and the
message carries no boundary marker, so B is 0.)

Build the user content with `hamo_score.build_prompt` so the train-time
prompt and the serve-time prompt are **byte-identical** — including the
trimming guards (3 turns × 200 chars context, 500-char message). Any drift
between the two is silent out-of-distribution at serve time.

```bash
pip install hamo-score
```

```python
import json
from hamo_score import build_prompt

def to_row(message, history, labels):
    return {"messages": [
        {"role": "user", "content": build_prompt(message, history)},
        {"role": "assistant", "content": json.dumps(
            {k: round(float(labels[k]), 1) for k in "AWEHB"},
            ensure_ascii=False)},
    ]}

with open("train.jsonl", "w") as f:
    for rec in labeled_records:
        f.write(json.dumps(to_row(rec["message"], rec.get("context"),
                                  rec["labels"]), ensure_ascii=False) + "\n")
```

Labels are the assistant turn: a single JSON object, five keys, one decimal,
on the 0.5 grid. Nothing else — no explanations, no chain-of-thought.

### Synthetic curriculum, with admission gates

The bulk of the corpus is synthetic dialogue windows organized into **scenario
cells** (ours grew to 40+: neutral smalltalk, elliptical short replies, somatic
reports, third-party conflict, pushback at the assistant, self-criticism,
implicit severity, hostile-but-clear, long rambles, …). Two disciplines make
synthetic data work:

**Admission gates.** Each cell declares the label band its samples are
supposed to land in; the teacher labels every generated sample; samples whose
teacher labels fall outside the band are discarded, not "fixed". For genuinely
benign cells this is safe (our neutral-smalltalk cell admits only teacher
all-zeros).

> **The v5 rule — never cap W in distress-adjacent cells.** Our rejected v5
> added a "bounded worry chains" cell with an admission gate of `W ≤ 1.0`.
> The text in that cell was distress-adjacent; the gate taught the model
> "worry-shaped text → suppress W". Crisis W-misses on the full 758-turn set
> went from 5 (v4) to 10–18 (2–3.6×) across checkpoints, and the generation was rejected. An admission
> band may constrain W from below or constrain other dimensions — but an
> **upper cap on Withdrawal in any cell whose text can carry distress**
> is a standing safety hazard.

**Style quotas matched to your real distribution.** Synthetic generators
naturally write fluent, medium-length, well-punctuated messages. Real traffic
does not: in ours, 35.5% of messages are under 15 characters, and 62% arrive
with a full multi-turn context — both were massively under-represented in our
early corpora (short messages 16×, long-context 48×). Diff your synthetic
distribution against your real exam and enforce quotas at generation time.
Ours: ≥25% messages under 15 chars, ≥30% without ending punctuation, 15–20%
code-switched (if your population mixes languages), context lengths matched
to the real bimodal split. Add a phrase blacklist of your generator's top
opening lines (our top-5 despair openers covered 53.8% of one cell before we
blacklisted them), require mid-band labels (0.5/1.0/1.5) to actually appear,
and cap samples that exactly equal your most common score-vectors at <20% —
otherwise you are training a grid classifier (see §6).

### Real consented data: small amounts work

You do not need thousands of real turns. Our v6.1 added exactly 440 consented
real turns, upsampled ×3 to ~8% of the corpus (in v9: about 1,310 of 20,187
rows, ~6.5%), on top of the synthetic curriculum — and moved dimension-level
agreement on the 453-turn final +1.0pt (v4 84.6% → v6.1 85.6%), with the
Agency dimension (pre-v9 rubric) reaching 85%, its best at the time. Part
of that gain is easier rather than cleaner: staff repeat themselves across
sessions, 42 of the 453 final turns share a message text with the 440
training turns, and about 0.4 pt of v6.1's 85.6% comes from that overlap
(85.2% on the 411 clean turns). Screen
them per R2, upsample them so the model actually sees them, and keep them out
of every eval split.

---

## 5. The LoRA recipe

This is the actual config that trained the released v9 weights (`mlx-lm`,
one M1 Pro MacBook, 16GB) — identical, hyperparameter for hyperparameter, to
the v7 and v6.1 runs before it; only the data and the adapter path changed.
Paths adapted, numbers untouched:

```yaml
# finetune.yaml
model: mlx-community/Qwen3-0.6B-bf16
train: true
data: data/my_train_dir          # contains train.jsonl / valid.jsonl
adapter_path: adapters/my_run
fine_tune_type: lora
num_layers: 16
lora_parameters: {rank: 8, dropout: 0.0, scale: 20.0}
batch_size: 4
iters: 7200
learning_rate: 7.0e-5
lr_schedule: {name: cosine_decay, warmup: 100, warmup_init: 1.0e-6, arguments: [7.0e-5, 7100, 7.0e-6]}
mask_prompt: true
grad_checkpoint: true
max_seq_length: 1024
steps_per_report: 400
steps_per_eval: 1200
save_every: 1200
seed: 0
```

```bash
pip install mlx-lm
python -m mlx_lm lora -c finetune.yaml
```

Three of these numbers are scars; treat them as load-bearing:

- **`mask_prompt: true`.** For a scoring task the answer is ~28% of the
  sequence. With masking off (still the default in `mlx-lm`, verified through
  0.31.3), 72% of our
  gradient went into language-modeling the client's message instead of
  learning to score it — across six full runs before we noticed. Turning it
  on, alone, was worth ~+1.4pp at decision level. Verify it is actually on in
  whatever trainer version you use.
- **`batch_size: 4` + `grad_checkpoint: true` at `max_seq_length: 1024` on
  16GB.** Our first full run used batch 8 at seq 1024: memory hit ~16.6GB and
  the run exploded *numerically, not loudly* — loss 0.118 → 10.8 by step 600
  while the process kept running. Rule of thumb: when you double sequence
  length, halve the batch. The healthy config peaked at ~4.7GB and ended
  around loss 0.06 on our v4 retrain; the v9 run of the same config peaked
  at 5.5GB and ended near train loss 0.03.
- **`max_seq_length: 1024`, not 512.** Tempting to shorten for speed, but
  512 truncates long messages with 5-turn contexts — exactly the samples the
  style quotas fought to include.

One more scar is not a number in the file: **a 16GB laptop in daytime use
can diverge mid-run.** Two of our runs did (the first attempts of v8.1 and
v9; v9's train loss went from ~0.04 at iteration 4,800 to 0.52 at 5,200 and
1.34 at 5,600), and both times a slow-down and swapping came first, while other apps
held memory. Since v8.1, training runs under `caffeinate` plus a watchdog
that stops and restarts any run whose train loss exceeds 1.0 after iteration
400; it caught v9's first attempt. Close memory-hungry apps, or train
overnight.

`save_every: 1200` yields six checkpoints — your selection pool for §6, or,
if you fix the candidate in advance (as we did for v9), spares you can score
later as robustness evidence. Don't save less often to save disk.

Rough wall-clock: a full 7,200-iteration run takes on the order of a few
hours on a MacBook — v6.1 ran over a ~16k-row corpus (16,432 train rows) on
an M1 Pro; v7 ran over ~19k rows (18,856 train) in about 2 h 16 min by its
checkpoint timestamps; v9 ran over 20,187 train rows in about 2 h (M1 Pro,
16GB). Start it after lunch, evaluate before dinner.
The valid split exists to watch for divergence during training, **not** to
pick checkpoints (next section explains why, and what it cost us when we
broke this rule).

The recipe is written for MLX because that is what we ran. The load-bearing
parts — prompt masking, the seq/batch/memory trade, LR shape, checkpoint
cadence — transfer to any LoRA trainer; the exact throughput numbers do not.

---

## 6. Checkpoint selection and the acceptance gate

**Never select on synthetic validation loss.** Our synthetic valid split was
3× heavier-tailed than reality (high-W/E samples: 48% synthetic vs 14% real).
Early-stopping on it selects the best model *for a distribution that does not
exist*. Valid loss is a health monitor, nothing more.

Select on your **real calibration set**, at **decision level** — the state
bucket that comes out of the deterministic stress math, because that is the
number your downstream logic actually consumes. The smoothing absorbs ~5× of
per-message noise, so decision level is both more forgiving and more honest
than dimension level: two models 3pt apart on dimensions can be identical
where it counts.

For every saved checkpoint, produce a row like this:

```python
import json
from hamo_score import update_stress, energy_state

def evaluate_checkpoint(pred_rows):
    """pred_rows: [{gold, pred, prior_stress, quadrant}, ...] on the calibration set."""
    n = len(pred_rows)
    dim = sum(1 for r in pred_rows for d in "AWEHB"
              if abs(r["gold"][d] - r["pred"][d]) <= 0.5) / (n * 5)
    dec = sum(1 for r in pred_rows
              if energy_state(update_stress(r["pred"], r["prior_stress"], r["quadrant"]))
              == energy_state(update_stress(r["gold"], r["prior_stress"], r["quadrant"]))) / n
    crisis_miss = sum(1 for r in pred_rows
                      if r["gold"]["W"] >= 2.5 and r["pred"]["W"] < 0.5)
    distinct = len({tuple(r["pred"][d] for d in "AWEHB") for r in pred_rows})
    return dim, dec, crisis_miss, distinct
```

The selection table has four columns, and every one earned its place:

1. **Dimension-level ±0.5** — the diagnostic number.
2. **Decision-level** — the selection number. Differences under 2pt are noise
   at a few hundred samples; re-run comparisons that matter across seeds.
3. **Crisis-miss count** (gold W ≥ 2.5 scored below 0.5). v5's champion-by-
   decision-level checkpoint carried **18** crisis misses; selection without
   this column is blind exactly where you can least afford it. Until v7 our
   rule was to refuse any checkpoint above the incumbent's miss count *at
   selection time*, not just at final acceptance. For v7 we pre-registered a
   version of that filter (≤ 2 crisis misses on the selection split, then
   highest decision-level); it picked iteration 6,000 — and then we overrode
   it: we decided crisis coverage is guaranteed by the upstream deterministic
   gate rather than used as a selection constraint, and shipped iteration
   7,200, which had zero Boundary sign flips (turns where the model scored B
   high on self-effacing text whose gold B is 0 — reading the dimension
   backwards). That override was made after both checkpoints had been scored
   on the final split, so for v7 the final was touched more than once. The two
   tied there (decision 97.1% each; dimension 85.0% for 6,000 vs 85.1% for
   7,200), and 7,200 still passed the acceptance gate below (decision 97.1% ≥
   96.2%, crisis misses 3 ≤ 4). So the count still gates acceptance, but it no
   longer vetoes checkpoints at selection time.
4. **Distinct output vectors** — the collapse detector. One early generation
   scored decently while emitting only **59** distinct five-score
   combinations against 233 in real data: it had quietly become a 14-cell
   grid classifier with cell-center scores. Watch this number, plus mid-band
   usage (are 1.0s and 1.5s ever emitted?). A scorer that cannot say "1.0"
   is not measuring.

**Or fix the candidate before training.** Selection is itself a source of
noise. For v8 and v8.1 we pre-registered a selection rule — highest agreement
on the run's own 249-row validation split, against the advice in §5 — and for
v8.1 it picked iteration 4,800 over 7,200 by 0.4 pt, about one item. 4,800
failed two gates; 7,200 would have passed all four. We did not substitute
it: re-picking after seeing the gates would have made them decorative. For v9
we fixed the candidate before training (the last checkpoint, 7,200, no
picking); the other checkpoints were saved but not scored. With a
selection split of a few hundred items, we now recommend the same.

**The acceptance hard gate.** Through v7, the winning checkpoint sat the
final exam — the split reserved for the shipping decision (v7 excepted, see
item 3) — and shipped only if:

> decision-level ≥ your incumbent, **AND** crisis-miss ≤ your incumbent.

Either fails → the generation is rejected and the incumbent stays. No
averaging the two, no "but dimensions improved". We rejected two trained,
plausible-looking generations on this gate (v5: misses 2–3.6× worse; v6:
misses 3 → 9 on the 453-turn final, from three poisoned rows).

When the rubric itself changes, the gate has to change with it:
decision-level against old-rubric labels stops being a clean yardstick (the
reference buckets are computed from old-rubric A and B). It still moved: v9
scores 96.0% there against v7's 97.1%, so under the pre-v8 gate it would
have failed that line too. Part of the drop is the rubric change itself; we
cannot separate the parts on this exam, so we report the drop as it is.
From v8 on, each
generation pre-registered a gate set before training, adding exams built for
the new rubric. v9's five: (1) A exam paired direction ≥ 90%; (2) crisp B
exam, zero sign flips and paired direction ≥ 96%; (3) crisis-level W misses
on the 453-turn final ≤ 3; (4) W / E / H on the final, each ≥ the lowest of
the incumbent's last three checkpoints; (5) a new synthetic W safety exam, W
reaching its floor on ≥ 95% of items. v8 and v8.1 were rejected on their
gates. v9 passed three of five and was released by an explicit founder
override — see §8. Every rejection cost a training run; shipping any of them
quietly would have cost trust in the instrument.

If you run against live traffic, do it in **shadow** first: new model scores
in parallel, incumbent still decides, every pair logged. Preregister the
switch criteria before you look at the data (for example: ≥1 week of shadow,
fallback rate <2%, decision-level ≥96%, smoothed-stress trajectory deviation
≤0.05, zero crisis misses) — then switching is one config change, and so is
rolling back.

---

## 7. Ship it

Fuse the **winning checkpoint** (not the training dir!), convert to GGUF,
quantize to q8. One trap first: `adapters/my_run/adapters.safetensors` is
always the *last* iteration — mlx-lm overwrites it as training ends. If your
§6 winner is any other checkpoint (ours often was: v4 shipped iteration 6000
of 7200), fusing the training dir silently ships the wrong weights with no
error. Materialize the winner first:

```bash
# 0. materialize the winning checkpoint (here: iteration 4800)
mkdir -p sel
cp adapters/my_run/adapter_config.json sel/
cp adapters/my_run/0004800_adapters.safetensors sel/adapters.safetensors

# 1. fuse LoRA into the base weights
python -m mlx_lm fuse \
  --model mlx-community/Qwen3-0.6B-bf16 \
  --adapter-path sel \
  --save-path fused/my-score-model

# 2. convert + quantize with llama.cpp
python llama.cpp/convert_hf_to_gguf.py fused/my-score-model \
  --outfile my-score-model.q8.gguf --outtype q8_0
```

Stay at **q8_0**: it is the only v9 build we have validated. The shipped v9
q8_0, run with neutral sampling, scores 89.3% dimension-level on the
self-check exam below (bf16: 88.9%), JSON 100%, gate 10/10 — inside the v9
reference band. On the ARM CPU server we ran shadow scoring on, a v6.1 q4
build was not faster than q8 (q8 dot-product kernels are good on ARM; on an
M1 Pro with Metal, v7 Q4_K_M ran at 0.54 s P50 vs 0.70 s for Q8_0, so the
speed trade is hardware-specific). Below q8, measure before you trust it —
and note that **every lower-bit measurement we have is on v7 weights**. On
v7, on our internal 453-turn final split, a Q6_K we quantized ourselves was
indistinguishable from Q8_0, while Q4_K_M lost 0.8 pt at dimension level
(0.4 pt at decision level) and pulled W down one-sidedly on crisis-adjacent
turns (6 lower vs 1 higher than Q8_0) — bucket agreement barely moves while
direction does. So, on v7: Q6_K held up for gating when memory is tight;
Q4_K_M suited research, offline or human-read scores (if it must gate, keep
the deterministic gate upstream, as always, and consider compensating the
withdrawal threshold); nothing below Q4_K_M is validated. (llama.cpp, neutral
sampling; Q4_K_M added no crisis miss there, 3 vs 3.) **On v9 only the
shipped Q8_0 has been measured**, and we publish no v9 Q6_K or Q4_K_M. If you
quantize v9 — or your own fine-tune — below q8, run
[`eval/compare_quants.py`](../eval/compare_quants.py) against your q8 build
first and read its directional table, not just agreement. (Its per-build
agreement is graded against the exam's v9 labels; pass `--labels pre_v9` for
v7-based builds.)

Create the ollama model with the **empty-think template, temperature 0 and
neutral sampling** — this is the single most common wiring mistake. Use
[`server/Modelfile`](../server/Modelfile) as-is (edit the `FROM` line), or see
the same template inlined in
[`server/docker-compose.yml`](../server/docker-compose.yml):

```
FROM ./my-score-model.q8.gguf
TEMPLATE """<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
<think>

</think>

"""
PARAMETER temperature 0
PARAMETER num_predict 80
PARAMETER stop <|im_end|>
# neutral sampling: ollama's default repeat_penalty 1.1 penalizes the score JSON's repeated tokens and pushes scores up from 0
PARAMETER repeat_penalty 1.0
PARAMETER top_k 0
PARAMETER top_p 1.0
```

```bash
ollama create my-score-model -f Modelfile
```

The last three lines are not cosmetic, and the first of them is measured.
With ollama's default
`repeat_penalty 1.1` switched back on, v9 q8's fabrication rate on the crisp
B exam (a true 0 scored ≥ 1.0) rose from 1.9% to 2.8% (misses fell 6.1% →
3.1% — the same upward push, not an improvement); on the v7-era boundary
exam the same switch took v7 q8 from 2.9% to 8.7% and v6.1 q8 from 13.5% to
25.0%. Smaller on v9, same direction: keep all three.

In production, set `keep_alive=-1` and send one warm-up request after every
restart (the toolkit's `OllamaClient` already sends `keep_alive=-1` per
request).

**Then take the exam.** The toolkit ships a deployment self-check — 195
synthetic teacher-labeled questions plus 10 handwritten crisis-gate cases:

```bash
python eval/run_exam.py --model my-score-model
```

Compare against the reference band in [`eval/README.md`](../eval/README.md)
(v9 labels: JSON validity ≥99%, dimension-level 86–92% with each dimension
≥75%, gate **10/10 — hard requirement**; the shipped v9 q8 scores 89.3%).
Three notes for fine-tuners:

- The exam's A and B labels were re-labelled for v9 with the same qualified
  teacher prompts that labelled v9's training data (the previous labels are
  kept per row as `labels_pre_v9`). So the exam is in-distribution for v9 by
  construction: it certifies your wiring — prompt, template, sampling,
  parser — not model quality. Its high B agreement is partly base rate
  (under crisp B most labels are 0, and v9 mostly outputs 0). If your
  fine-tune keeps the pre-v9 rubric, or you deploy v7 on purpose, grade
  against the old labels with `--labels pre_v9` (v7 reference: 83.5% bf16,
  83.8% q8).
- If your fine-tune deliberately changed the score distribution — new rubric,
  materially different population — the shipped exam's labels reflect *our*
  rubric and may no longer be a fair test. Regenerate your own exam with your
  qualified teacher: same shape (~200 synthetic questions, a fresh random
  seed disjoint from all your training corpora, zero real data), same format
  (`message` / `context` / `labels` rows). When only the rubric changed, as
  for v9, re-labelling the same questions with the re-qualified teacher (and
  keeping the old labels beside them) is the smaller step we took.
- The gate section must pass **10/10 regardless of anything you trained**.
  It never calls the model — it runs the toolkit's `CrisisGate` keyword lists
  in-process against seven crisis phrasings and three dark-humor lookalikes
  that must *not* trigger. Note what it does **not** test: that your
  deployment actually routes every message through the gate before the model.
  That wiring is a separate integration test you own. A gate failure here
  means the word lists were altered — fix before going live; a deployment
  that bypasses the gate breaches license §3(c) in consumer-facing
  mental-wellness settings.

---

## 8. What v8 and v9 taught us

v8 and v9 were the first generations that changed the rubric itself — what
A and B mean — rather than only the data under a fixed rubric. The first
three lessons are about changing a rubric safely; the rest are about process.

1. **Rubric changes are human rulings first, prompt second.** The founder
   ruled on A over four rounds; the teacher prompt was then qualified against
   his own scores on real messages (second batch of 40: 92.5% within ±0.5,
   one severe disagreement). Those human checks were **not blind**: Claude
   (Anthropic) pre-scored each message and the founder confirmed or changed
   it (13 of 40 changed in the first batch, 6 of 40 in the second), so 61 of
   the 80 A labels that entered training are Claude's pre-scores, confirmed
   unchanged — disclosed on the model card. Do yours blind: the human scores
   first, with no model score in view.
2. **Re-label only the column that changed, and measure spill-over.** v8
   re-labelled only the A column; in v9, on the 18,162 prompts carried over
   from v7, each change (A, B, the W repair) touched a single column and
   carried every other column over verbatim (the two new patches, 1,380
   rows, were labelled fresh on every column). The
   first A-rubric prompt showed why: its new A section made the teacher more
   conservative on W and B as well, costing several points of agreement on
   both on our 440 calibration turns, although nothing about W or B had
   changed. After editing one dimension's rubric, re-check every other
   dimension on your calibration set — and use that prompt for its own
   column only.
3. **An answer key can carry the old rubric.** Our crisp-B teacher first
   failed its pre-registered qualification on the v7-era boundary exam; on
   review, much of the failure traced to old-rubric answers in the key. Two
   independent blind graders (who never saw the teacher's scores) re-graded
   the exam, the founder ruled on the 30 items they disagreed on, and the
   key was fixed before v9 was trained. The founder's rulings from that
   review (wishes and preferences → 1.0; asking the AI for help → 0) were
   also added to the teacher prompt before it passed, so both the key and
   the prompt moved after the failure. That is a post-hoc revision, and we
   disclose it as one. When a rubric moves, re-grade the key blind before you
   qualify anyone against it.
4. **Fix the candidate in advance, and never gate against a single baseline
   checkpoint.** v8 failed on two self-erasure items ("fine, I'll do whatever
   you say" scored as a strong boundary) and on E, −1.8 against v7's shipped
   checkpoint. An ablation without v8's new patch failed the same two ways,
   so the patch was not the cause: those items are borderline for this model
   family (three of v7's own four checkpoints flipped them too), and gating
   against one baseline checkpoint was a design flaw. For v8.1 we changed
   that gate to "≥ the lowest of v7's last three checkpoints" — after seeing
   v8's results, which we state openly. v8.1 then fell to its selection rule
   (§6). v9's candidate was fixed before training.
5. **More teachers did not help.** Kimi K3 and GLM-5.2 (open weights, via a
   third-party inference provider) both failed a qualification pegged to our
   incumbent teacher (relative to DeepSeek: GLM-5.2 −3.4 points on E, Kimi K3
   −7.3 on B), and a three-way median beat DeepSeek alone on no independent
   yardstick. Neither labelled any training data. Qualify each teacher on its
   own; a median of unqualified teachers is not a qualified teacher.
6. **Fail fast on account errors.** An exhausted API balance (HTTP 402) was
   swallowed as ordinary "labelling failures" for ~2,000 rows before we
   noticed. Our labelling clients now stop at the first 401/402 and print the
   server's message; other errors still retry. (The training-side
   equivalent, the divergence watchdog, is in §5.)
7. **In-distribution exams inflate gains.** On the exams built for v9, v7 →
   v9 moved a long way: A paired direction 21/154 → 150/154, crisp-B
   fabrication 12.1% → 1.9%, sign flips 2 → 0, while crisp-B misses rose
   slightly, 5.3% → 6.1%. But those exams are in-distribution for v9's own
   training patches: the A mid-band patch was generated from the A exam's
   class definitions, and the crisp B exam shares its generator with the
   boundary patches. They show that v9 learned the new rubrics on that
   generator's distribution, not that it scores real conversations better;
   no real-conversation measurement under the new A and B rubrics exists
   yet. Keep at least one real-conversation measurement per rubric, and
   remember that repeated attempts against one exam are themselves a slow
   form of selection: v8, its ablation, v8.1 and v9 all sat the same 453-turn
   final.
8. **If you override a gate, publish it.** v9 failed two of its five
   pre-registered gates: gate 4 by one item (H 93.6 against a 93.8 floor on
   the real final), and gate 5 — a safety gate — clearly: on the new W safety
   exam, W reached its floor on 78.9% of items, against ≥ 95% required. Its
   despair-plus-action half is 45/45 (v7: 36/45); its half pairing explicit
   suicidal ideation with help-seeking is 26/45 on the gated bf16 model
   (29/45 on the shipped q8), the same 26/45 as v7, with 5 of 45 still below
   W 1.0 in both — a gap inherited from v7, not fixed. By the pre-registered
   rule v9 is rejected. Hamo's founder released it anyway, as an explicit,
   recorded override: he judged v9 a substantial improvement, and crisis
   handling the job of the upstream architecture rather than of this model.
   Gates only mean something if failing one means something, so the failures
   are on the front page of the model card and the thresholds were not
   redrawn after the fact. If you ever override your own gate, do the same.
   And if you build on v9, do not assume the gate backstops this gap: the
   bundled `CrisisGate` is a short keyword list, and it fires on only 26 of
   those 45 items — and on only 7 of the 19 the gated bf16 model leaves below
   W 2.5, so on the other 12 neither the gate fires nor W reaches its floor.
   Extend the lists for your population, add a second screen alongside the
   gate (never instead of it), and measure both the ideation-with-help-seeking
   gap and that screen's recall on your own population rather than assume
   either is fixed.

---

## 9. What you owe under the license

Two licenses, do not mix them up:

- **Toolkit code: Apache-2.0.** Your integration code, your gate extensions,
  your downstream math — unencumbered.
- **Model weights: HAMO-RAIL-S 1.0.** Your fine-tuned weights are
  **derivative works** of the Model, and the license was written with you in
  mind. Read [the LICENSE itself](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/LICENSE);
  in plain terms:

1. **You may** use, modify, fine-tune, and redistribute the weights — including
   commercially, royalty-free (§1).
2. **When you redistribute** your derivative weights, retain the LICENSE file
   and a reference to the source repository. The Qwen3-0.6B base remains
   Apache-2.0 (Alibaba Cloud); its notices continue to apply (§2).
3. **The four use restrictions travel with the weights** — §3 states they
   "must be passed on, in substance, to any recipient of the Model or of
   derivative weights". Your fine-tune, and anyone you give it to, may not:
   (a) make standalone clinical determinations without a licensed professional
   holding decision authority; (b) use scores as the sole or primary basis for
   consequential decisions about an identifiable person (employment, insurance,
   credit, and similar) or for covert psychological surveillance; (c) run
   consumer-facing mental-wellness deployments without independent **upstream**
   crisis handling and AI disclosure; (d) attempt re-identification from
   scores, or link scores to identities beyond what a lawful, consented
   purpose requires.
4. **Materially breach §3 and the license terminates** automatically (§5).

Practically: ship your derivative with the LICENSE file and a link back to
the source repository, keep the gate in front of the model, disclose the AI,
and stay inside the four use restrictions — then you are square.

---

## Appendix: ten generations at a glance

| Generation | What changed | Outcome |
|---|---|---|
| v2 | first distillation, 7.5k synthetic | shipped — dim 81%, decision 95.4% |
| v3.x | rebalance + defect repair | shipped — decision 96.8% |
| v4 | 8-agent data audit: prompt masking, style quotas, mid-band cells, 15k corpus | shipped — dim 84.0% (+3.1), crisis misses 11 → 5 (full 758-turn set), output vectors 59 → 87 |
| v5 | synthetic patch cells with a W-cap admission gate | **rejected** — crisis misses 2–3.6× worse (10–18 vs 5, full 758-turn set); taught us the distress-adjacent W-cap rule |
| v6 | +440 real turns, incumbent's labels unscreened | **rejected** — 3 crisis-artifact rows in training, misses 3 → 9; taught us R2 |
| v6.1 | same 440 real turns, teacher labels, crisis-artifact screening | shipped, superseded by v7 — dim 85.6%, decision 96.2%, crisis misses 4 |
| v7 | same config as v6.1; teacher re-labelled the corpus at temperature 0 + 2,713-row boundary-discrimination patch (18,856 train rows) | shipped, superseded by v9 — dim 85.1%, decision 97.1%, crisis misses 4 → 3 |
| v8 | A rubric v8 (four rounds of founder rulings; teacher prompt qualified against the founder's scores) + 1,100-row A mid-band patch; only the A column re-labelled | **rejected** — failed 2 of 4 gates: two self-erasure B sign flips returned, E −1.8 vs v7's shipped checkpoint. An ablation without the patch failed the same two ways (and reached only 79% A direction), so the patch was not the cause; taught us not to gate against a single baseline checkpoint |
| v8.1 | v8 + 280-row self-erasure B patch; gate 4 revised, after seeing v8, to "≥ the lowest of v7's last three checkpoints" | **rejected** — the pre-registered selection rule (best agreement on the 249-row validation split) picked iteration 4,800 by 0.4 pt; it failed gate 2 (3 flips) and gate 4 (H 0.4 below the floor). 7,200 passed all four and was not substituted; taught us to fix the candidate in advance |
| v9 (released, override) | A rubric v8 + crisp B (whole B column re-labelled) + W safety repair (285 rows raised); same config as v7, 20,187 train rows; candidate fixed in advance (7,200); five gates incl. a new W safety exam | **released by explicit founder override** after passing 3 of 5 gates — failed gate 4 (H one item short) and gate 5, the W safety exam (78.9% vs ≥ 95%). Real final (old-rubric labels): W/E/H 88.1/86.1/93.6, decision 96.0%, crisis misses 3 → 2 |

v2–v5 were scored on the full 758-turn evaluation set, v6 onward on its
453-turn final split (v4 there: dim 84.6%, decision 95.6%, 3 crisis misses).
v9's dimension average against old-rubric labels is left out of its row on
purpose: on A and B it measures how far the rubric moved, not accuracy. v9's
A and B gains were measured only on in-distribution synthetic exams (§8,
lesson 7).

Those ten adjudicated generations sit on top of about seventeen actual
training runs — pilots, restarts, two runs that diverged mid-way, an
ablation, and a same-size rerun or two that never earned a row here, plus
one run on a student three times larger that gained roughly a point and was
dropped. Budget for that ratio: you will train more often than you will ship.

The pattern worth copying is not any single number. It is that every
generation faced the same real exam, the exam never entered training, and the
gate for shipping was written down before the results existed. Four
rejections are not a failure statistic — they are evidence the process works.
v9 is the exception, and we will not dress it up: it failed two of its
written-down gates, one of them a safety gate, and shipped anyway on an
explicit founder override. A gate that can be overridden is only as strong as
the disclosure that follows, so the failures sit on the front page of the
model card and the thresholds were not moved after the fact. If you ever
override yours, publish it the same way.

---

# 中文

## 给专业机构的微调指南（精编）

你从 HuggingFace 下载了
[hamo-score-0.6b](https://huggingface.co/HamoAI/hamo-score-0.6b)，想用**经
授权的**自有数据把它适配到你的人群、语域或语言。本文是我们十代模型蒸馏出来
的操作手册：其中四代训练完成后被**拒收**（v5、v6 因危机召回退步，v8、v8.1
未过预注册验收闸门）；当前发布版 v9 **没过它自己预注册的五道闸门中的两道
（其中一道是安全闸门），由创始人明确破例、留档发布**——没过什么、我们为何
公开，见§八。全部经验来自一台 MacBook 加 API 打标（截至 v6.1 约 7 美元，
v7–v9 的重标另有花费），不是集群规模的流程。先立框架：它是**测量仪器**——不是聊天机器人、不是
诊断工具、不是治疗师，也**不是危机检测器**。危机处理由模型上游的确定性闸门
（`CrisisGate`）负责——这是许可证 HAMO-RAIL-S §3(c) 对面向消费者的心理健康
部署的硬性要求，也是本项目架构对一切部署的要求。微调不改变、也不允许改变
这一点。

### 一、先想清楚要不要微调

多数需求不需要动权重：人群特有的危机说法 → `CrisisGate(extra_keywords=[...])`
一行扩词表；下游敏感度 → 改 `stress.py` 里的平滑与分桶阈值（Apache-2.0 参考
代码，本来就是给你改的）；个别句子评分不服 → 记住分数要经 `0.8·历史 + 0.2·本句`
平滑，单句噪声会被吸收，成规律的分歧走仓库的「评分分歧」issue 模板。

**升级到 v9 本身就是一次重调。** v9 改了 A、B 的含义（A 口径 v8；B 改为只认
明确边界标记的 crisp 口径），而且两者都打得更低：真实终评上 v9 平均 A 0.45、
平均 B 0.08，v7 为 0.67 与 0.92；B 在其中 94% 的轮次为 0（v7 为 52%）。A、B
在压力公式里都是负权重，所以同一段对话，v9 算出的压力**更高**。工具包的压力
权重与分桶阈值未改动，是按 v9 之前的分数定的——让分桶把关任何事之前，先用你
自己的数据重调；A、B 分数跨 v7 → v9 不可比。需要旧口径的，v7 权重仍可取用
（见模型卡「版本」一节）。

真正该微调的场景：新语言（模型以中文为主：按 v9 训练集每行的最新消息统计，
中文约 76% / 英文 13% / 中英混杂 11%）、明显不同的语域人群、你们临床团队正式
定义的量表变体。**永远不要**为了"让模型会认危机"而微调——闸门管危机，模型管
其余，倒过来就是在诱惑别人拆闸门。

### 二、数据红线（先于一切采集）

- **R1 知情同意**：我们的训练语料全部为合成数据，唯一例外是 v6.1 起加入的
  440 条真实对话轮次——来自三位公司内部员工（创始人与两位咨询师）、经本人明示
  授权、×3 上采样约占 v6.1 语料 8%（v9 的 20,187 条训练行中约 6.5%）；
  **外部来访者对话从不入训，构造上保证**。照此
  执行：真实来访数据可做考卷（当地法规与治理允许时），入训必须有书面、可撤回
  的本人授权。「已脱敏」不等于授权。
- **R2 危机工件筛查**：v6 拒收的教训。危机内容在生产里被上游短路，会留下
  「危机原文 + 近零分数」的毒标签。3 条这样的行随真实数据入训，453 题终评集
  上的危机漏检从 3（当时的现任 v4）涨到 9，整代拒收。规则：真实行入训前，原文
  过一遍危机词表；命中必经人工复核；文标矛盾（危机文本配良性标签）的行删除或
  重标。3/16000 就足以让漏检翻成三倍（3→9）——没有「才几条」的豁免。
- **R3 永不训练模型识别危机**：确定性闸门独占此职责，模型的危机语召回只是
  纵深防御（见§六；v9 起另有专门的 W 安全卷，见§八）。
- **R4 卫生**：全量脱敏，并如实称呼——我们自己的导出是**假名化**而非匿名化
  （固定盐、完整时间戳、正文仅正则脱敏），仍属个人信息，删除权仍及于它；
  真实数据不进 git；保留一页式数据台账。

### 三、先出考卷，再编教材

项目第一件产物是**真实数据终评考卷**（永不入训），第二件是**过了资格考的
教师**。顺序颠倒，你会不自觉地照着模型的长处出题。三切分：教师资格/校准集、
选点集、终局集（只为发布决定而考：不用于选点（v7 为例外，见§六）、不用于改提示词）
——我们的：1,198 条假名化真题 → 440 条校准集 + 758 条留出集，后者再切为 305 条选点集
与 453 条终局集。终局集上尽量少打分：我们也曾在上面给不打算发布的检查点打过参考分
（v7 的几个检查点，其分数后来定了闸门 4 的下限，见§六；v8.1 的第 7,200 步），每多看
一次都是一点选点压力（见§八第 7 条）。校准集若日后经授权入训（我们 v6.1 就这么做
了），须先从留出区另切选点集。每行连同消息、上下文、金标一起，**记录当时的
压力值等决策上下文**——否则算不了决策级。教师资格考：给训练数据打标的模型
（我们用 deepseek-chat + 生产量表；打标用 temperature 0——v6.1 及以前的语料是在
非零温度下打标的，v7 的主要变化就是以 temperature 0 重标语料）先考你的真题，我们的线：
维度级 ±0.5 约 89%、决策级 97.5%；要逐维看——我们教师 B 维初考 72%，靠量表
校准注记修到 78%，平均数会把坏维度藏起来。整体重标也可能悄悄撤销早先的刻意修复：
v7 的 temperature 0 重标就丢掉了此前加入的一条 W 规则（绝望后跟行动仍保持 W ≥ 1.5），
v9 的 W 安全修复不得不把它补回（按这条规则加一条新规则——求助不抵消自杀意念，
W ≥ 2.5——上调 285 行）。每次重标后，都要复查早先修复所编码的规则。口径一改就要
按列重新资格考：v9 的教师给 A（口径 v8）与 B（crisp）各用一份提示词，各自先过
资格考才打标——B 的提示词是在答案卷重定、并补入创始人裁定之后才过的（见§八第 3
条）。A 提示词还有一个加了告别规则的变体，单独过了资格考，用来探测告别信号、并给
新合成补丁打 A 列——所以给训练数据打 A 的提示词有两份。另一份提示词（为 W 安全修复在
关键词选出的行上重打 W）没有单独过资格考，
我们只接受它的上调。
再量一下现任评分器的自洽：同批
消息在两个线上环境各打一遍，小规模抽查（每次十来条）只有 94–98% 一致——只能当作粗略的
实际上限，并非精确测得。若另建 LLM judge 用于任何触人
环节：与持牌专业人员的 kappa ≥ 0.6 才可用。

### 四、训练数据格式

mlx-lm 聊天格式 JSONL，user 内容**必须**用 `hamo_score.build_prompt` 构造
（训练与推理提示词逐字节一致，截短护栏一并生效；工具包安装：
`pip install hamo-score`）；assistant 内容是单个 JSON
对象：五键、一位小数、0.5 网格，无任何多余文字。

```json
{"messages": [
  {"role": "user", "content": "给来访者最新消息打分（AWEHB，0.0-3.0）。\n此前对话:\nassistant: 这周过得怎么样？\n最新消息: 今天试着出门散了个步"},
  {"role": "assistant", "content": "{\"A\": 1.0, \"W\": 0.0, \"E\": 0.0, \"H\": 0.0, \"B\": 0.0}"}
]}
```

（示例标签按 v9 口径：单次散步属中档行动力，消息里没有边界标记，所以 B 为 0。）

合成教材按场景格子组织，配**准入闸门**（教师标签落在格子设计带内才收，否则
弃样）。**v5 铁律：凡文本与痛苦相邻的格子，准入禁设 W 上限**——v5 的「有界
担忧链」格子设了 W≤1.0 准入，等于教模型「担忧文本→压 W」，758 题全卷上的危机
漏检从 v4 的 5 条翻到 10–18 条（2–3.6 倍），整代拒收。风格配额要对齐真实分布：我们的真实流量 35.5% 是 15 字以内短
消息、62% 带多轮上下文，合成器天然写不出这些——按真实占比强制配额，再加
生成器口头禅黑名单、中间档（0.5/1.0/1.5）标签强制出现、纯原型样本 <20% 封顶。
真实授权数据少量即有效：v6.1 的 440 条 ×3 上采样（约占语料 8%；v9 中约 1,310 行、
约 6.5%）让 453 题终局集维度级 +1.0pt（v4 84.6 → v6.1 85.6），A 维（v9 之前的
口径）达 85%，为当时最高。其中一部分进步是「更容易」而非「更干净」：员工跨会话会
重复说话，453 题中有 42 题的消息原文也出现在入训的 440 条里，v6.1 的 85.6% 中约
0.4 个点来自这部分重叠（411 道无重叠题上为 85.2%）。

### 五、LoRA 配方（MLX，一台 MacBook）

发布版 v9 的真实配置（一台 M1 Pro MacBook，16GB；与 v7、v6.1 逐项超参完全相同，
只换了数据与 adapter 路径；路径改成你的，数字别动）：base
`mlx-community/Qwen3-0.6B-bf16`，LoRA rank 8 / scale 20 / 16 层，
`batch_size: 4`，`iters: 7200`，LR `7e-5` cosine 退火至 `7e-6`（warmup 100），
**`mask_prompt: true`**，`grad_checkpoint: true`，`max_seq_length: 1024`，
`save_every: 1200`。运行：`python -m mlx_lm lora -c finetune.yaml`。三个数字
是伤疤：① `mask_prompt` 不开，72% 梯度耗在给来访者消息做语言建模上（我们
瞎跑了六轮才发现），单开此项决策级 +1.4pp；② 16GB 机器上 seq 1024 配
batch 8 会顶到 16.6GB 并**无声数值爆炸**（loss 0.118→10.8），序列翻倍、
batch 减半，健康跑法峰值：v4 重训实测约 4.7GB、loss 收于约 0.06，v9 同一配置
实测峰值 5.5GB、训练 loss 收于约 0.03；③ seq 别降到
512——会截断长上下文样本，正是配额辛苦补进来的那些。另一道伤疤不在配置里：
**16GB 笔记本白天日常使用下会中途发散**——v8.1 与 v9 的第一次尝试都发散了（v9
的训练 loss 从第 4,800 步的约 0.04 升到第 5,200 步的 0.52、第 5,600 步的 1.34），之前都先出现变慢和内存
交换，其他程序正占着内存。自 v8.1 起训练在 `caffeinate` 下跑，并配发散监测：
第 400 步后训练 loss 超过 1.0 即停止、从头重练——它截住了 v9 的第一次尝试。关掉
吃内存的程序，或者夜里跑。`save_every: 1200` 产出六个检查点：选点池；若像 v9
那样预先定死候选，它们就是日后可补打分的稳健性证据备份——别为省硬盘少存。全程约数小时量级（v6.1
约 1.6 万行语料、16,432 条训练行，M1 Pro；v7 约 1.9 万行、18,856 条训练行，
按 checkpoint 时间戳约 2 小时 16 分；v9 20,187 条训练行，约 2 小时，M1 Pro 16GB），
午后开跑、晚饭前评测。valid 切分只用来盯训练是否发散，**不**用来选点（原因、以及
我们破例时付出的代价，见下一节）。

### 六、选点与验收

**永不用合成 valid loss 选点**——我们的合成 valid 比真实分布重尾 3 倍，在
它上面早停等于为假分布选模型。选点在**真实校准集**上、按**决策级**（分数过
确定性压力折算后的状态桶一致率，即下游真正消费的数字）。选点表四列：维度级
±0.5（诊断用）、决策级（选点用，<2pt 视为噪声）、**危机漏检数**（金标 W≥2.5
而预测 <0.5——v5 的选点冠军漏检 18 条，没有这一列的选点在最不能瞎的地方是
瞎的）、**输出向量种类数**（塌缩探测器：某早期学生只会输出 59 种五维组合，
真实数据有 233 种——它退化成了格子分类器）。v7 之前，我们在选点时就拒收漏检
高于现任的 checkpoint，不只在终局验收时拒。v7 预注册了这条过滤的一个版本
（选点集漏检 ≤2，再取决策级最高），它选中第 6,000 步——随后我们推翻了它：
决定危机覆盖由上游确定性闸门保证、不再作为选点约束，改发边界符号翻转（把
自我消融、金标 B=0 的发言打成高 B，方向判反）为 0 的第 7,200 步。此决定是在
两者都已考过终局集之后做出的，v7 的终局集因此不止碰了一次。两者在终局集上
打平（决策级均 97.1%；维度级第 6,000 步 85.0%、第 7,200 步 85.1%），第 7,200
步仍过终局硬闸（决策级 97.1% ≥ 96.2%，漏检 3 ≤ 4）。所以
漏检数仍卡验收，但不再在选点时一票否决。

**或者在训练前就定死候选。** 选点本身就是噪声源：v8、v8.1 预注册的选点规则是
「训练自带的 249 条验证集上一致率最高」（违背了§五的建议），v8.1 据此以 0.4 个点
（约 1 题）之差选中第 4,800 步而非第 7,200 步——第 4,800 步没过两道闸门，第 7,200
步本可四道全过。我们没有改选：看过闸门结果再改选，闸门就成了摆设。v9 在训练前
定死候选为最后一个检查点（第 7,200 步，不选点），其余检查点只存档、未打分；选点集
只有几百题时，我们现在建议照此办理。

终局硬闸（预先写死，沿用至 v7）：**决策级 ≥ 现任 且 危机漏检 ≤ 现任**，任一
不过整代拒收、现任留任——我们照此拒了 v5 和 v6 两代（v6：453 题终局集漏检
3→9）。口径本身改了，闸门也得跟着改：参照状态桶由旧口径的 A、B 算出，拿旧标签
比决策级不再是干净的尺子。但它确实降了：v9 在这里是 96.0%，v7 是 97.1%，按 v8 之前的
旧闸门它这一条也过不了。下降有一部分来自口径改动本身；这张考卷分不开两部分，所以我们
如实报告这个下降。自 v8 起每代在训练前预注册一组闸门，并加入为新口径
造的考卷。v9 的五道：① A 考卷成对方向 ≥90%；② crisp B 卷零符号翻转且成对方向
≥96%；③ 453 题终局集危机级 W 漏检 ≤3；④ 终局集 W/E/H 各不低于现任最后三个检查点
的最低值；⑤ 新的合成 W 安全卷，W 达到下限的题 ≥95%。v8、v8.1 按各自闸门拒收；
v9 过三道，由创始人明确破例发布——见§八。每次拒收都赔上一次训练；悄悄发布其中
任何一代，赔上的会是仪器的可信度。接真实流量先跑**影子模式**，切换标准预注册（例如：影子
≥1 周、回退率 <2%、决策级 ≥96%、平滑压力轨迹偏差 ≤0.05、危机零漏检）。

### 七、上线

先融合**选中的检查点**（不是训练目录）。一个陷阱：`adapters/my_run/adapters.safetensors`
永远是**最后一步**的权重——mlx-lm 训练结束时会覆写它。若§六选中的不是最后一个检查点
（我们常如此：v4 发布的是 7,200 步中的第 6,000 步），直接融合训练目录会无声地发错权重、
不报任何错。先物化选中的检查点：把 `adapter_config.json` 与对应的
`0004800_adapters.safetensors`（以第 4,800 步为例）复制到单独目录，后者改名为
`adapters.safetensors`，再让 `--adapter-path` 指向该目录（命令见[英文版 §7](#7-ship-it)）。

`python -m mlx_lm fuse` 融合 → llama.cpp `convert_hf_to_gguf.py --outtype q8_0`
转 GGUF（就用 q8：它是 v9 唯一验证过的档位——v9 发布版 q8_0、中性采样下自检
维度级 89.3%（bf16 为 88.9%）、JSON 100%、闸门 10/10，落在 v9 参考带内——且在
我们跑影子评分的 ARM CPU 服务器上，v6.1 的 q4 不比 q8 快（M1 Pro Metal 上 v7
Q4_K_M P50 0.54 s、Q8_0 0.70 s，速度取舍因硬件而异）。更低位宽先实测再信，而且
**我们所有低位宽数据都来自 v7 权重**：v7、内部 453 轮终局集上，我们自行量化的
Q6_K 与 Q8_0 无差别；Q4_K_M 维度级 −0.8pt、决策级 −0.4pt，危机邻近轮次上 W 单向
偏低（比 Q8_0 低 6 条、高 1 条）——分桶一致率几乎不动，方向却动了。所以在 v7 上：
Q6_K 可在内存紧张时用于门控；Q4_K_M 适合研究/离线/人读分数（若必须门控，照常
保留上游确定性闸门并考虑补偿 W 阈值）；Q4_K_M 以下未验证（llama.cpp、中性采样；
Q4_K_M 未新增危机漏检，3 vs 3）。**v9 只量过随包 Q8_0**，我们不发布 v9 的 Q6_K
或 Q4_K_M；要把 v9 或你自己的微调量化到 q8 以下，先跑
[`eval/compare_quants.py`](../eval/compare_quants.py) 与你的 q8 档对比，看方向性
表格而不只看一致率——其单档一致率默认按考卷的 v9 标签判，v7 系的档位加
`--labels pre_v9`）→ `ollama create`，模板必须带**空 `<think>`
块 + temperature 0 + 中性采样**（`repeat_penalty 1.0`、`top_k 0`、
`top_p 1.0`——ollama 默认 repeat_penalty 1.1 会惩罚分数 JSON 里的重复 token，
把分数从 0 往上推。这不是摆设，其中 repeat_penalty 一项有实测：打开默认值后，v9 q8 在 crisp B 卷上造分率
（真值 0 却打 ≥1.0）1.9%→2.8%（漏判 6.1%→3.1%，同样是往上推，不是改进）；在 v7
时代的边界卷上，v7 q8 为 2.9%→8.7%、v6.1 q8 为 13.5%→25.0%。v9 上影响较小，方向
相同，三个参数都要留。照抄 `server/Modelfile`，这是最常见的接线错误）→ 生产设
`keep_alive=-1`、重启后
预热一发。最后交卷：`python eval/run_exam.py --model 你的模型`，对照
`eval/README.md` 参考带（v9 标签：JSON ≥99%、维度级 86–92% 且各维 ≥75%、
**闸门 10/10 硬性**；随包 v9 q8 为 89.3%）。考卷的 A、B 标签已用给 v9 训练数据
打标的同一套合格教师提示词重标（旧标签逐行保留在 `labels_pre_v9`）：所以它对 v9
天然同分布，验证的是接线（提示词、模板、采样、解析器），不是模型质量；B 一致率
高，部分是底数效应（crisp 口径下多数标签为 0，v9 也多输出 0）。若你的微调沿用
v9 之前的口径，或有意部署 v7，用 `--labels pre_v9` 按旧标签判（v7 参考：bf16
83.5%、q8 83.8%）。若你的微调实质改变了评分分布，随包考卷的标签已不公允——用你
的合格教师按同样形制重出一份（约 200 题合成、全新种子与训练语料不相交、零真实
数据）；若只是口径变了（如 v9），也可以像我们一样用重新过了资格考的教师重标同一
批题、旧标签并排保留。闸门区
与训练无关，**任何情况下必须 10/10**：它不调模型，进程内跑工具包的
`CrisisGate` 词表——7 条危机句式必中、3 条黑色幽默不得误触。注意它**不**验证
你的部署是否真把每条消息先送过闸门，那是你自己要做的集成测试。闸门区不过
说明词表被改动了，修好再上线；绕过闸门的面向消费者心理健康部署则直接违反
许可证 §3(c)。

### 八、v8 与 v9 的教训

v8、v9 是头两代改动口径本身（A、B 的含义）的模型，而不只是在固定口径下改数据。
前三条关于如何安全地改口径，其余关于流程。

1. **改口径先靠人的裁决，再落到提示词。** 创始人对 A 作了四轮裁决；教师提示词随后
   以他本人在真实消息上的打分为准过资格考（第二批 40 条：±0.5 一致 92.5%，严重分歧
   1 条）。这些人工终审**不是盲打**：由 Claude（Anthropic）先给每条预打分，创始人逐条
   确认或修改（第一批 40 条改 13 条，第二批 40 条改 6 条），因此进入训练的 80 个 A 标签
   中有 61 个是 Claude 的预打分、经他原样确认——已在模型卡披露。你们请盲打：人先打分，
   看不到任何模型分数。
2. **只重标改动的那一列，并测外溢。** v8 只重标 A 列；v9 在沿用自 v7 的 18,162 条提示上，
   每处改动（A、B、W 修复）都只动一列，其余各列逐字沿用（两份新补丁共 1,380 行，
   各列都是新打的标签）。第一版 A 口径提示词说明了原因：新加的 A 段让教师在
   W、B 上也变保守，在 440 条校准集上两维一致率都掉了几个点，尽管 W、B 的口径一点
   没变。改完一维的口径，要在校准集上复查其余每一维——这份提示词也只用来打它自己那
   一列。
3. **答案卷里可能残留旧口径。** crisp B 教师最初在 v7 时代的边界判别卷上没过预注册
   资格考；复查发现失败多半来自答案里的旧口径答案。随后由两位独立盲审员（看不到教师
   分数）重定答案，两人分歧的 30 题由创始人裁定，答案在 v9 训练前定稿。复查中创始人的
   裁定（愿望与偏好 → 1.0；向 AI 求助 → 0）也补进了教师提示词，之后它才过关——失败
   之后，答案卷和提示词都动了。这是事后修订，
   我们照此披露。口径一动，先盲审重定答案，再拿它考任何教师。
4. **候选检查点预先定死；闸门别只拿一个基线检查点比。** v8 挂在两道自我消融题上
   （「行，我全听你的」被打成强边界）和 E 上（比 v7 发布检查点低 1.8）。不加 v8 新补丁
   的消融版以同样两处失败，病因不在补丁：这些题是这一系列模型的临界题（v7 自己四个
   检查点中有三个也翻过），只拿一个基线检查点当门槛是设计缺陷。v8.1 把这道闸门改为
   「不低于 v7 最后三个检查点的最低值」——是看过 v8 结果之后改的，我们如实写明。v8.1
   随后栽在选点规则上（见§六）。v9 的候选在训练前就已定死。
5. **多加教师没有帮助。** Kimi K3 与 GLM-5.2（开放权重，经第三方推理服务商调用）都没
   通过以现任教师为基准的资格考（相对 DeepSeek：GLM-5.2 的 E 低 3.4 点，Kimi K3 的 B 低
   7.3 点）；三家取中位数，在任何独立尺子上都不比 DeepSeek 单独强。两位都没有为训练
   数据打过标签。每位教师单独过资格考；一群不合格教师的中位数不是合格教师。
6. **账户类错误要立刻失败。** API 余额耗尽（HTTP 402）曾被当作普通「打标失败」吞掉，
   约 2,000 行之后才发现。我们的打标客户端现在遇到 401/402 立即停止并打印服务端原文；
   其他错误照常重试。（训练侧的对应物——发散监测——见§五。）
7. **同分布考卷会放大进步。** 在为 v9 造的考卷上，v7 → v9 进步很大：A 成对方向
   21/154 → 150/154，crisp B 造分 12.1% → 1.9%、符号翻转 2 → 0，同时 crisp B 漏判
   略增（5.3% → 6.1%）。但这些考卷与 v9 自己的训练补丁同分布：A 中档补丁直接用 A 考卷
   的类定义生成，crisp B 卷与边界补丁出自同一生成器。它们说明 v9 在这个生成器的分布上
   学会了新口径，不说明它在真实对话上打得更好；新 A、B 口径下还没有任何真实对话上的
   测量。每套口径至少保留一项真实对话测量；也要记得，对同一张考卷反复尝试本身就是一种
   缓慢的选点——v8、它的消融版、v8.1 与 v9 考的都是同一张 453 题终局集。
8. **推翻闸门，就要公开。** v9 没过自己预注册的五道闸门中的两道：闸门 4 差一题（终局
   集 H 93.6，下限 93.8）；闸门 5——一道安全闸门——差得明显：在新的 W 安全卷上，W 达到
   下限的题只有 78.9%，要求 ≥95%。其中「绝望加行动」一半 45/45（v7 为 36/45）；
   「明确自杀意念加求助」一半，受检 bf16 模型 26/45（随包 q8 为 29/45），与 v7 同为
   26/45，两者都仍有 5/45 低于 W 1.0——这是承袭自 v7 的缺口，没有修好。按预注册规则
   v9 应当拒收。Hamo 创始人仍决定发布，并明确留档：他判断 v9 是实质性的进步，且危机
   处理是上游架构的职责、不是这个模型的职责。闸门只有在「不过就有后果」时才有意义，
   所以两项失败写在模型卡最前面，门槛也没有事后重划。你若推翻自己的闸门，请同样公开。
   若你在 v9 之上继续做，别以为闸门能兜住这个缺口：随包的 `CrisisGate` 只是一份简短的
   关键词表，在这 45 道题中只命中 26 道，受检 bf16 模型把 W 打到 2.5 以下的 19 道中只命中
   7 道——其余 12 道，闸门不触发，W 也不到下限。请按你的人群扩充词表，在闸门旁边（而不是
   替代它）加第二层筛查，并在你自己的人群上实测「自杀意念加求助」这一缺口和那层筛查的
   召回率，别假设两者已经解决。

### 九、许可证义务

两个许可证别搞混：**工具包代码 Apache-2.0**（你的集成代码不受限）；**模型
权重 HAMO-RAIL-S 1.0**，你微调出的权重是**衍生权重**：§1 允许自由使用、
修改、再分发（含商用、免版税）；§2 要求再分发时保留 LICENSE 文件与源仓库
指引（基座 Qwen3-0.6B 的 Apache-2.0 声明继续有效）；§3 的四条使用限制
**必须实质性地随权重传递给任何接收方**——不得独立做临床判定（须持牌专业人员
掌握决定权）、不得把分数作为对可识别个人重大决定的唯一或主要依据（雇佣、
保险、信贷等）或用于隐蔽心理监控、面向消费者的心理健康部署必须保留独立的
上游危机处理与 AI 披露、不得从分数重识别个人或把分数与身份做超出合法授权
用途的关联；§5：实质违反 §3 即自动终止授权。一句话：带着 LICENSE 文件和
源仓库指引发布、闸门挡在模型前面、披露 AI 身份、守住四条使用限制，你就是
合规的。

### 附：十代小史

v2 首蒸（维度 81）→ v3.x 配平（决策 96.8）→ v4 审计驱动重修数据（维度
84.0，漏检 11→5，758 题全卷）→ **v5 拒收**（W 上限准入闸门，漏检 5→10–18，2–3.6×）→
**v6 拒收**（3 条危机工件入训，漏检 3→9）→ v6.1 发布（440 条授权真实数据 +
工件筛查，维度 85.6、决策 96.2、漏检 4；已被 v7 取代）→ v7 发布（配置同
v6.1；教师以 temperature 0 重标全量语料 + 2,713 行边界区分补丁，共 18,856
条训练行；维度 85.1、决策 97.1、漏检 4→3；已被 v9 取代）→ **v8 拒收**（A 口径
v8——创始人四轮裁决、教师提示词以创始人打分为准过资格考——加 1,100 行 A 中档
补丁，只重标 A 列；四道闸门挂两道：两条自我消融 B 符号翻转重现、E 比 v7 发布
检查点低 1.8；不加补丁的消融版同样两处失败、A 方向只有 79%，病因不在补丁——
教训：闸门别只拿一个基线检查点比）→ **v8.1 拒收**（v8 + 280 行自我消融 B 补强；
看过 v8 结果后把闸门 4 改为「不低于 v7 最后三个检查点的最低值」；预注册选点
规则（249 条验证集一致率最高）以 0.4 个点选中第 4,800 步，它挂了闸门 2（翻转
3 条）与闸门 4（H 低于下限 0.4）；四道全过的第 7,200 步未改选——教训：候选预先
定死）→ **v9 发布（破例）**（A 口径 v8 + crisp B（B 列全部重标）+ W 安全修复
（上调 285 行）；配置同 v7，20,187 条训练行；候选预先定死为第 7,200 步；五道
闸门含新的 W 安全卷；过三道，挂闸门 4（H 差一题）与闸门 5 W 安全卷（78.9%，
要求 ≥95%），**由创始人明确破例发布**；真实终局集（旧口径标签）W/E/H 88.1/86.1/
93.6、决策 96.0、漏检 3→2）。v2–v5 在 758 题全卷上计分，v6 起在其中 453 题
终局集上计分（v4 在 453 题上：维度 84.6、决策 95.6、漏检 3）。v9 的五维平均
（对旧口径标签）有意不列：在 A、B 上它衡量的是口径移动了多远，不是准确率；v9 在
A、B 上的进步只在同分布合成考卷上测过（见§八第 7 条）。

这十代定谳之下是约十七次实际训练——试跑、重启、两次中途发散、一次消融、
没能挣到一行表格的重训，外加一次三倍大学生的实验（只涨约一分，弃）。按这个
比例做预算：训练的次数一定多于发布的次数。值得复制的不是任何一个数字，而是流程本身：每代
考同一张真实考卷，考卷永不入训，验收标准在出分前写死。四次拒收不是事故率——
是流程在起作用的证据。v9 是例外，我们不粉饰：它没过自己写死的两道闸门，其中
一道是安全闸门，仍由创始人明确破例发布。能被推翻的闸门，强度只取决于推翻之后的
披露——所以两项失败写在模型卡最前面，门槛也没有事后改动。你若推翻自己的闸门，
也请同样公开。
