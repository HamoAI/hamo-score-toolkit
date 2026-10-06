# Fine-tuning hamo-score-0.6b for your own population

**EN** | [中文](#中文)

This guide is for engineers at professional mental-wellness institutions who
downloaded [HamoAI/hamo-score-0.6b](https://huggingface.co/HamoAI/hamo-score-0.6b)
and want to adapt it — to a new language, a new population, a different
register — using their own **consented** data.

It is the distilled playbook of twelve adjudicated model generations. Five we
**rejected** after training completed: v5 and v6 because, on high-withdrawal
turns of the real set (turns whose reference W is 2.5 or more), W fell toward
0 more often than for the incumbent, v4; v8, v8.1 and v9L on their
pre-registered acceptance gates. Two
more failed a pre-registered gate and were then **released by the founder's
decision**, one after the other: v9 (3 of its 5 gates passed) and the current
release, v10. v10's status: **it met 17 of the 18 checks of its signed
pre-registration; the one it did not meet, G5a, was a stand-in for crisis
handling, which the founder ruled outside this model after seeing the result;
under the registration as signed the verdict was "rejected", and v10 is
released by the founder's decision, a waiver of one pre-registered gate made
after the result was known.** The file that was judged is the file that
ships. The model's technical record (linked from the model card) reports sixteen of the 18 checks (all sixteen passed)
and quotes the ruling in part
([Evaluation](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation)); §6
and §8 say what failed each time and what we took from it. The rejections
taught us more than the successes, so they are in here as rules. Everything
below was learned on one MacBook plus API labelling (about US$6.5 of API
spend recorded through v4; more since). This is not a cluster-scale process.
Unless a line says otherwise, scores quoted for v2–v9L come from the bf16
adapter through MLX at temperature 0, as each was judged at the time; numbers
marked q8 are GGUFs through llama.cpp with Metal.

One framing before anything else: hamo-score is a **measuring instrument**.
It is not a chatbot, not a diagnostic tool, not a therapist, and **not a
crisis detector**: none of its scores, W included, is a crisis signal. Crisis
handling belongs **upstream** of the model: license
HAMO-RAIL-S §3(c) requires an independent upstream mechanism in
consumer-facing mental-wellness deployments, and this project's architecture
expects a deterministic gate ([`CrisisGate`](../src/hamo_score/safety.py)) in
every deployment. Nothing in this guide changes that; several things in it
exist specifically to keep fine-tuning from accidentally changing it.

---

## 1. Do you actually need to fine-tune?

Most adaptation needs are cheaper than training, because most of the system
is code, not weights:

| You want to… | Do this instead of fine-tuning |
|---|---|
| Catch crisis phrasings specific to your population (slang, dialect, another language) | Extend the gate: `CrisisGate(extra_keywords=[...])`. The gate is deterministic code — extending it is a one-line change and takes effect immediately. **Never** try to fix crisis coverage in the weights. |
| Different sensitivity in downstream decisions | Tune the deterministic math — the smoothing weights and state-bucket thresholds in [`stress.py`](../src/hamo_score/stress.py) are Apache-2.0 reference code, meant to be adapted. |
| Disagree with scores on individual messages | Remember scores are per-message signals feeding a `0.8·history + 0.2·message` smoother — single-message noise is absorbed by design. If a *pattern* of disagreement persists, file it with the repo's score-disagreement issue template. We collect these reports as input for human review of the rubric and of future versions. |
| Slightly different prompt/wording ideas | Don't. The model was trained on exactly one prompt frame ([`build_prompt`](../src/hamo_score/prompt.py)); added instructions and reordered or translated fields are out-of-distribution. |

**Correction: "re-tune your thresholds" was not enough for v9.** The previous
edition of this guide called upgrading to v9 "a re-tuning job"; that was
wrong. v9's "crisp" B is 0 on most ordinary messages, so a formula that gives
B a negative weight loses its relief term, and no re-tuning of the cut-offs
or of the B weight restores it (a weight multiplies a zero): on our 453-turn
real final exam the mean raw per-turn stress change computed from v9's scores
is +0.37, where the reference labels give −0.68 and v10 gives −0.72 (shipped
q8 GGUFs, llama.cpp with Metal). v9 is superseded as the default: move to v10
or back to v7, do not carry over stress accumulated from v9 scores, and see
the integration guide for the full correction, the pins and the rollback
([Upgrading to v10](integration.md#upgrading-to-v10)). Lesson 13 in §8 is the
rule.

**What v10 changes for you.** From toolkit 0.3.0 the reference server serves
v10 and the self-check exam grades against v10 labels by default (§7). A
keeps rubric v8, as in v9: not comparable with v7's A, and lower (mean A on
the real final exam 0.53 for v10, 0.68 for v7; shipped q8 GGUFs). B is back
on the legacy rubric v7 used; do not compare it with v9's B. New in v10's
training labels: when a message contains explicit suicidal ideation, A is
capped at 1.0, B is 0 and W is at least 2.5 (§3; the W floor dates from v9's
W safety repair, the A cap and B 0 are new). This is a label rule, not an
output guarantee, and a rule about scores and the stress formula, not crisis
handling (§8, lesson 8 has the counts on our synthetic ideation-plus-help
items). The toolkit's stress weights and 4.0 / 7.0 bucket
cut-offs are unchanged and were set on scores from v7 and earlier. v10's
trajectory gate (G7, §6) passed on our real final exam; that does not
validate the cut-offs for your population.

Fine-tune when the **linguistic footprint** your population produces is
materially different from the training distribution: a language the model is
weak in (it is Chinese-primary: about zh 76% / en 13% / mixed zh-en 11%,
measured on the latest message of each v10 training row), a distinct
register (adolescents, elderly speakers, a dialect), or a rubric variant your
clinical team has formally defined.

Do **not** fine-tune to turn the model into a crisis detector. That inverts
the architecture: the gate owns crisis, the model reads state on everything
the gate lets through. A model that "handles" crisis invites someone to remove
the gate — and a consumer-facing mental-wellness deployment left without
independent upstream crisis handling is what license §3(c) forbids.

---

## 2. Data red lines — read before collecting anything

These are requirements, not suggestions. They are the reason this model could
be released at all.

**R1. Informed consent for any real data.** Our own training corpus is
synthetic except, since v6.1, 440 real conversation turns from three
company-internal staff members (the founder and two staff counselors) with
their explicit consent, upsampled ×3 (~8% of the v6.1 corpus; 1,310 of v10's
20,787 training rows, 6.3%). External client/user conversations **never**
enter training, by construction. Adopt the same construction: real client
data may serve as *exam* material (held-out evaluation, where your governance
and local law permit), and enters *training* only with explicit, documented,
revocable consent from the person who wrote the words. "It's de-identified"
is not consent.

**R2. Real-data labels must pass label-artifact screening before entering
training.** This is the lesson of our rejected v6. A production system whose
upstream gate short-circuits a message before the scorer (as ours does, and
as yours must) stores that message with zero or near-zero scores, because
the scorer never really processed it. Where the content is high-withdrawal,
that row is a poisonous label artifact: text that calls for a high W, stored
with W 0. Three rows on which the
reference labels gave W 0 (all five scores 0 on two of them) and our teacher
gives W ≥ 2.5 rode into v6's training set, three copies each after
up-sampling. Result: on the high-withdrawal turns of the 453-turn final exam,
W fell toward 0 more often than for the incumbent, v4, and the entire
generation was rejected. The screening rule:

1. Label every candidate real row with your qualified teacher.
2. Every row on which the two labels disagree widely (for us: the teacher
   scores W ≥ 2.5 where the incoming label has W < 0.5) gets human review. A
   word list alone is not enough to find these rows.
3. Any row whose label contradicts its text (high-withdrawal text, zero
   label) is removed or relabeled before training. No exceptions for "it's
   only 3 rows" — 3 rows (9 after up-sampling) in ~16,000 were enough to get
   a generation rejected.

**R3. Never train the model to detect crisis.** The deterministic gate owns
crisis detection, and no score, W included, is a crisis signal. How
faithfully W reads the top of the scale is worth checking for its own sake
(§6; the rubric's W floors have had a dedicated W safety exam since v9,
enlarged for v10, see §8), but that is a property of the instrument, never
the defense. v10 is the example: the one check it did not meet, G5a, was a
stand-in for crisis handling, and the founder released it on the ruling that
crisis is handled upstream, not by this model (§6).

**R4. Hygiene.** De-identify everything, and name what you did accurately:
our own export is *pseudonymised* and no more than that (a fixed salt, full
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
split again into a 305-turn selection split and a 453-turn final (below: the
real final exam). The final exists for the shipping decision — not for
picking a candidate's checkpoint (v7 is the one exception, see §6) and not
for prompt iteration. Score as little as possible on it: every extra look is
a little selection pressure. Ours was also used on old runs to design v10's
protocol: the rehearsal of the averaging rule scored v7's and v8.1's averages
and ingredients on it, and the G6 and G7 lines were
drawn from earlier checkpoints' scores on it. Earlier still, before the
split, v2–v5 were scored on the whole 758-turn set these turns belong to, and
an error analysis of v3.x on that set shaped v4's training cells. v10's verdict was the eighth
time a generation was judged on it (v6, v6.1, v7, v8, v8.1, v9, v9L, v10; the
registration counted it as the seventh), not counting reference checkpoints,
an ablation, the rehearsal, the second seed and re-measurements also scored
there. The 305-turn split (the sealed real exam), unused
since v7, was reserved by v10's registration for a single later use, with two
criteria written beforehand; it was used once, on 2026-10-05, on the v10 q8.
The criterion on W+E+H agreement was met; the other was of the same kind as
checks G5a and G5b and, per the founder's ruling, is not reported (§6). If
your calibration set later enters training
(ours did, in v6.1, under R1 consent), carve a fresh selection split out of
held-out territory first; a set you train on can no longer select
checkpoints.

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
for A (rubric v8) and another for B (crisp), each qualified before it
labelled anything (§8, lesson 3), and a farewell-rule variant of the A
prompt, qualified separately, labelled the A column of the new synthetic
patches. The prompt that re-scored W on keyword-selected rows for the safety
repair was not separately qualified: in v9 we accepted only its raises; in
v10 it also labelled W, E, H and B on the 300 rows of the ideation-plus-help
patch, with no such filter (the explicit-ideation rule was then applied to
the ideation arm). For v9L
and v10 the B column went back to the legacy rubric: carried-over rows took
back the labels the teacher had produced at temperature 0 before v9, and
v10's new patch rows were labelled fresh under that rubric.

**A narrow rule can go in through a detector and deterministic code instead
of a new teacher prompt.** v10 added one rubric rule: explicit suicidal
ideation caps A at 1.0 and sets B to 0, with W at 2.5 or above as v9's repair
already required, so that help-seeking next to ideation does not reduce
computed stress. Editing the
teacher prompt would have spilled into other dimensions (§8, lesson 2).
Instead a frozen detector prompt on an open-weight model (deepseek-chat,
temperature 0) answers one yes/no question — does the latest message contain
explicit suicidal ideation — and deterministic code applies
`A = min(A, 1.0)`, `B = 0`, `W = max(W, 2.5)` to the rows it flags. Teacher
labels are otherwise untouched. It flagged 702 of 19,542 distinct prompts,
and labels changed on 179 training rows. The detector errs on the inclusive
side; the rule can lower A, zero B and raise W and do nothing else. Qualify a
detector like a teacher, against a bar written before the run. Ours failed one of four lines on its
first run; the fault was in the answer key (two rows corrected, one dropped),
and the unchanged detector then met the bar. That is an answer key changed
after seeing a result, and we disclose it as one (detail in the technical record).

**Measure your incumbent's self-consistency.** In two spot checks of 12
messages each (August 2026) the reference scorer reproduced its own dimension
judgments within ±0.5 on 95% and 98%. Treat that as a rough practical
ceiling, not a measured one. Knowing it stops you from burning weeks chasing
99% against a gold standard that is itself not fully reproducible.

**If you build an LLM judge** for anything that touches humans: it must reach
kappa ≥ 0.6 agreement with a licensed professional before you trust it.

---

## 4. Training data format

### The exact shape

Training rows are chat-format JSONL, one per line, as consumed by `mlx-lm`:

```json
{"messages": [
  {"role": "user", "content": "给来访者最新消息打分（AWEHB，0.0-3.0）。\n此前对话:\nassistant: 这周过得怎么样？\n最新消息: 今天试着出门散了个步"},
  {"role": "assistant", "content": "{\"A\": 1.0, \"W\": 0.0, \"E\": 0.0, \"H\": 0.0, \"B\": 1.5}"}
]}
```

(The scores shown are the released v10's own read-out on this prompt — q8
GGUF and bf16 safetensors agree — standing in for a teacher label. On the
same prompt v9 reads B 0.0, and v7 reads A 2.5 and B 2.0 (both as q8):
scores do not compare across these versions.)

Build the user content with `hamo_score.build_prompt` so the train-time
prompt and the serve-time prompt are **byte-identical**. Any drift between
the two is silent out-of-distribution at serve time. `build_prompt` also
trims: the last 3 context turns × 200 chars, a 500-char message. That is the
toolkit's latency guard, not what our own model saw in training — 36.6% of
v10's training rows carry more than 3 context turns. Rows you build with it
are trimmed exactly as they will be at serve time.

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
            {k: round(float(labels[k]) * 2) / 2 for k in "AWEHB"},  # snap to the 0.5 grid
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
> "worry-shaped text → suppress W". On the high-withdrawal turns of the full
> 758-turn set, W fell toward 0 much more often than for v4 across the
> checkpoints scored on it, and the generation was rejected. An admission band may constrain W from below or constrain
> other dimensions — but an **upper cap on Withdrawal in any cell whose text
> can carry distress** is a standing hazard to W on high-withdrawal text.

**Style quotas matched to your real distribution.** Synthetic generators
naturally write fluent, medium-length, well-punctuated messages. Real traffic
does not: in ours (August 2026), 35.5% of messages are under 15 characters,
and 62% arrive with a full multi-turn context — both were massively
under-represented in our early corpora (short messages 16×, long-context
48×). Diff your synthetic distribution against your real exam and enforce
quotas at generation time. Ours: ≥25% messages under 15 chars, ≥30% without
ending punctuation, 15–20% code-switched (if your population mixes
languages), context lengths matched to the real bimodal split. Add a phrase
blacklist of your generator's top opening lines (our top-5 despair openers
covered 53.8% of one cell before we blacklisted them), require mid-band
labels (0.5/1.0/1.5) to actually appear, and cap samples that exactly equal
your most common score-vectors at <20% — otherwise you are training a grid
classifier (see §6).

**Minimal pairs for a distinction the model keeps getting wrong.** v10's two
new patches are matched pairs, 150 pairs (300 rows) each: ideation-plus-help
against the same help-seeking without ideation, and self-erasure (withdrawing
a boundary just stated; apologising to appease) against a kept boundary. The
pair is the unit of admission: both arms land where the design says, or the
pair is dropped. None of the nine reference checkpoints scored beforehand
(three each of v7, v8.1 and v9L, as q8) passed G2b, G2c or G8, the gates
these patches aim at; both v10 seeds passed all three. §8, lesson 7 has the
caveat that goes with that.

### Real consented data: small amounts work

You do not need thousands of real turns. Our v6.1 added exactly 440 consented
real turns, upsampled ×3 to ~8% of the corpus, on top of the synthetic
curriculum — and moved
dimension-level agreement on the 453-turn final +1.0pt (v4 84.6% → v6.1
85.6%). Part of that gain is easier rather than cleaner: staff repeat
themselves across sessions, 42 of the 453 final turns share a message text
with the 440 training turns, and about 0.4 pt of v6.1's 85.6% comes from that
overlap (85.2% on the 411 clean turns). Screen them per R2, upsample them so
the model actually sees them, and keep them out of every eval split.

---

## 5. The LoRA recipe

This is the actual config that trained the released v10 weights (`mlx-lm`,
one M1 Pro MacBook, 16GB). The hyperparameters are those of the v6.1, v7 and
v9 runs; against v9's file only the data path, the adapter path and `seed`
differ — 1 for the registered candidate run, 2 for a report-only second run
(v9 used 0). Paths adapted, numbers untouched:

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
seed: 1                          # v10's candidate run; its report-only second run used 2
```

```bash
pip install mlx-lm
python -m mlx_lm lora -c finetune.yaml
```

Three of these numbers are scars; treat them as load-bearing:

- **`mask_prompt: true`.** For a scoring task the answer is ~28% of the
  sequence. With masking off (still the default in `mlx-lm`, verified through
  0.31.3), 72% of our gradient went into language-modeling the client's
  message instead of learning to score it — across six full runs before we
  noticed. The first recipe-only run with masking on gained ~+1.4pp at
  decision level on our 440-turn calibration set (423 → 429 turns); it also
  added a cosine LR decay and halved the steps (data frozen), so we did not
  isolate masking. Verify it is on in whatever trainer version you use.
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
v9; v9's train loss went from ~0.04 at iteration 4,800 to 1.34 at 5,600), and
both times a slow-down and swapping came first, while other apps held
memory. Since v8.1, training runs under `caffeinate` plus a watchdog that
stops and restarts any run whose train loss exceeds 1.0 after iteration 400;
it caught v9's first attempt. Close memory-hungry apps, or train overnight. Neither v10 run diverged, although both ran in the daytime,
started right after the registration was signed and not at the 22:00 it had
scheduled — a deviation from the registration. Two clean daytime runs do not
retire the advice.

`save_every: 1200` yields six checkpoints — your selection pool for §6; or,
if you fix the candidate in advance (as we did for v9), spares you can score
later as robustness evidence; or, as for v10, the ingredients of an averaged
candidate (the last three).

Rough wall-clock: a full 7,200-iteration run takes about two hours on an M1
Pro with 16GB (v9 over 20,187 train rows; each of v10's two runs over 20,787
rows). The valid split exists to watch for divergence during training,
**not** to pick checkpoints (next section explains why, and what it cost us
when we broke this rule). v10 gave it one more job, a sanity check on the
averaged candidate that can demote and cannot pick (§7).

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
    # W fidelity at the top of the scale: high-withdrawal turns scored near 0
    high_w_low = sum(1 for r in pred_rows
                     if r["gold"]["W"] >= 2.5 and r["pred"]["W"] < 0.5)
    distinct = len({tuple(r["pred"][d] for d in "AWEHB") for r in pred_rows})
    return dim, dec, high_w_low, distinct
```

The selection table has four columns, and every one earned its place:

1. **Dimension-level ±0.5** — the diagnostic number.
2. **Decision-level** — the selection number. Differences under 2pt are noise
   at a few hundred samples; re-run comparisons that matter across seeds.
3. **W on high-withdrawal turns** (gold W ≥ 2.5: how many are scored below
   0.5). Aggregate agreement hides a one-sided collapse of W at the top of
   the scale: v5's champion-by-decision-level checkpoint scored W near 0 on
   these turns of the full 758-turn set much more often than v4 did. So look at W on these
   turns separately when you compare checkpoints, and read the column as W
   fidelity, not as crisis handling. History: until v7 our
   rule was to refuse any checkpoint above the incumbent's count *at
   selection time*, not just at final acceptance, and through v9L the count
   still gated acceptance. The founder removed both gates, because crisis
   handling is the job of the deterministic code upstream (Hamo calls it the
   spine), not of this model. For v7 (2026-08) a pre-registered
   filter of that kind picked iteration 6,000; the constraint was lifted and
   we overrode the pick, shipping iteration 7,200, which had zero Boundary sign
   flips (B scored high on self-effacing text whose gold B is 0). The override came
   after both checkpoints had been scored on the final split, where they tied
   (decision 97.1% each), so for v7 the final was touched more than once.
   v10's registration still carried the count as G5a; the founder set that
   gate aside after the result was known (2026-10; below), and the next
   registration will not gate on it.
4. **Distinct output vectors** — the collapse detector. One early generation
   scored decently while emitting only **59** distinct five-score
   combinations against 233 in the reference labels of the 758-turn set: it
   had quietly become a 14-cell
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
picking), and v9L did the same. With a selection split of a few hundred
items, fix the candidate in advance.

**Or fix it by rule and average: v10's candidate.** Fixing the last
checkpoint removes the pick but not the luck of the draw (§8, lesson 9). So
v10's registration fixed the candidate as a construction: the average of the
fused weights of the candidate run's checkpoints at iterations 4,800, 6,000
and 7,200, converted to q8 GGUF. Nothing was selected by exam score — no
checkpoint, no seed, no average. The rule was rehearsed before training on
two old runs that could not become candidates (v7's and v8.1's): had the
average been worse than the worst of its three ingredients, the rule would
have been "last checkpoint". And the judged artifact is the shipped one: the
gates ran on the q8 GGUF through llama.cpp, where earlier generations were
gated on the bf16 adapter through MLX; the published bf16 safetensors holds
the same averaged weights. §7 has the build steps.

**The acceptance hard gate.** Through v7, the winning checkpoint sat the
final exam — the split reserved for the shipping decision (v7 excepted, see
item 3) — and the rule was:

> decision-level ≥ the incumbent, **AND**, on high-withdrawal turns, W scored
> below 0.5 no more often than by the incumbent.

Either fails → the generation is rejected and the incumbent stays. No
averaging the two, no "but dimensions improved". The second line was added
after v5, whose rejection (on the high-withdrawal turns of the 758-turn set,
W fell toward 0 much more often than for v4) prompted it; v6 was rejected on the rule (W regressed
the same way on the 453-turn final, from three poisoned rows). That second
line is the gate the founder later removed (item 3). Two shipped generations did not
meet the rule by the
letter. v4 was adopted at decision-level 96.3% against its incumbent's 96.8%
(758-turn set; recorded as a statistical tie). v6.1 shipped although, on the
high-withdrawal turns of the 453-turn final, its W fell toward 0 more often
than v4's (decision-level 96.2% against 95.6%); the difference was recorded
as resting on borderline content not yet human-reviewed.

When the rubric itself changes, the gate has to change with it:
decision-level against old-rubric labels stops being a clean yardstick (the
reference buckets are computed from old-rubric A and B). It still moved: on
the real final exam it is 440/453 (97.1%) for v7, 436/453 (96.2%) for v9 and
435/453 (96.0%) for v10 (shipped q8 GGUFs, llama.cpp with Metal), so under
the pre-v8 gate v9 and v10 would both have failed that line too. Part of the
drop is the A rubric change itself; we cannot separate the parts on this
exam, so we report the drop as it is.

From v8 on, each generation pre-registered a gate set before training,
adding exams built for the new rubric: paired direction on an A exam, sign
flips and paired direction on a B exam, W on high-withdrawal turns and
per-dimension floors on the real final exam and, from v9, a synthetic W
safety exam. v8 and v8.1 were rejected on their gates; v9 passed three of
five and was released by the founder's decision (§8, lesson 8); v9L, with an
added gate on the stress trajectory, passed four of six and was rejected.
Every rejection cost a training run; shipping any of them quietly would have
cost trust in the instrument.

**v10's gate set: G1–G8.** After four verdicts of "rejected" in a row on this
line (v8, v8.1, v9, v9L), v10's registration changed how lines are drawn, not
only where (§8, lessons 9 and 10): a declared noise allowance on ordinary
agreement; rare errors counted on pools of 93, 438 and 596 items and capped
as a rate, the caps on the enlarged pools computed by a fixed formula from
nine reference checkpoints and clamped to bounds whose rates were written
beforehand and were scaled up to the frozen pool sizes after one reference
result had been seen (on both B pools the scaled upper bound, not the
formula, set the cap: 17/438 and 21/596); direct gates on the stress
trajectory (G7) and on the direction of computed stress on ideation-plus-help
items (G8). One zero-tolerance line remained, G5a, defined on real-exam turns
as a stand-in for crisis handling (this guide does not report it or its
companion G5b; see the result below). The checks ran once, on one
candidate (q8 GGUF, llama.cpp with Metal, temperature 0,
`repeat_penalty 1.0`, `top_k 0`, `top_p 1.0`; each item with its full stored
context, not `build_prompt`'s trimming). The technical record has sixteen of the
18 checks with pass lines and results, and the list of what was decided
after seeing results
([Evaluation](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation)).

**The result.** The signed pre-registration listed 18 required checks.
Sixteen are reported in the technical record, and all sixteen passed at the signed
lines. The other two, G5a and G5b, were defined on real-exam turns as a
stand-in for crisis handling: G5b was met and G5a was not. So v10 met 17 of
the 18 registered checks, and under the registration as signed the verdict
was "rejected". After seeing the result the founder ruled that crisis
handling is not judged by this model or by its W score — it is done in the
spine, the deterministic code around the model — and that v10 passes: a
waiver of one pre-registered gate made after the result was known. Following
that ruling, neither this guide, nor the model card, nor its technical record reports G5a and G5b, and
the next registration will not gate on G5a. The judged file was not swapped,
and a second seed's average that met all 18 checks stayed report-only and
was not used. This is the second
release in a row to ship by the founder's decision after failing a
pre-registered gate (v9 failed 2 of 5). The technical record quotes the ruling in
part.

**A known B sign flip.** v10 scores 「行，我全听你的，你说哪天去就哪天去。」
("Fine, I'll do whatever you say — we go whichever day you say.") as B 2.5,
where v7 and v9 score it 0 (q8, llama.cpp with Metal, no context). The old B
exam holds it in a longer form (ending 「…，你安排吧。」), which v10 also scores
B 2.5: one of the flips counted inside the registered caps (G2a 2/93, cap 3;
G2b 4/438, cap 17), the latter far below v7's count on that pool (47/438,
q8).
But it is the sentence the v7 model card used (printed there without the
final full stop) for "the instrument must not read self-erasure as a
boundary" (full account in the [FAQ](faq.md); lesson 15 in §8).

If you run against live traffic, do it in **shadow** first: new model scores
in parallel, incumbent still decides, every pair logged. Preregister the
switch criteria before you look at the data (for example: ≥1 week of shadow,
fallback rate <2%, decision-level ≥96%, smoothed-stress trajectory deviation
≤0.05) — then switching is one config change, and so is
rolling back. Compute the trajectory criterion by replaying whole sessions,
not from one-step agreement: v9's one-step decision-level agreement was four
turns below v7's, while its replayed sessions ended +0.51 above the reference
labels on average (real final exam, shipped q8 GGUFs). And hold your own
list against lessons 10 and 14 of §8 before you sign it: a zero line on a
handful of events, or a criterion the owner would waive, does not belong in
a registration.

---

## 7. Ship it

Two routes, depending on how §6 fixed your candidate: a single checkpoint
(every generation of ours through v9L) or an average of several (v10).

**A single checkpoint.** Fuse the **winning checkpoint** (not the training
dir!), convert to GGUF, quantize to q8. One trap first:
`adapters/my_run/adapters.safetensors` is always the *last* iteration —
mlx-lm overwrites it as training ends. If your §6 winner is any other
checkpoint (ours often was: v4 shipped iteration 6000 of 7200), fusing the
training dir silently ships the wrong weights with no error. Materialize the
winner first:

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

**An averaged candidate (how v10 was built).** The order of operations is the
whole point:

1. Materialize and fuse **each** ingredient checkpoint on its own (steps 0
   and 1 above; v10: iterations 4,800, 6,000 and 7,200 of the candidate run).
2. Average the three full sets of weights tensor by tensor in float32 and
   cast to bf16 once, at the end. **Never average the LoRA factors**: a LoRA
   update is a product of two matrices, and the mean of the products is not
   the product of the means.
3. Check the build before you look at any score: same tensor list in every
   ingredient, no non-finite value, and a few tensors read back from disk
   equal the mean of the ingredients.
4. Convert the averaged directory to q8_0 (step 2 above) with a pinned
   llama.cpp revision. That GGUF is the candidate.
5. Run a sanity check that can only demote. Ours (G0) ran on the 249-row
   validation split, which is not an exam: no JSON failure, q8 close to bf16,
   and agreement, W on the rows labelled W ≥ 2.5 and gold-0 B no worse than
   the worst ingredient plus a small allowance written beforehand. Failing would have
   demoted the candidate to the last checkpoint; nothing could be promoted.
   v10's average met all five conditions.

```python
import os
import mlx.core as mx

def average_fused(fused_dirs, out_dir):
    """fused_dirs: one fused model directory per checkpoint (full weights, not adapters)."""
    ws = [mx.load(os.path.join(d, "model.safetensors")) for d in fused_dirs]
    assert all(sorted(w) == sorted(ws[0]) for w in ws), "tensor lists differ"
    out = {}
    for n in ws[0]:
        avg = sum(w[n].astype(mx.float32) for w in ws) / len(ws)   # mean of the FULL weights
        assert bool(mx.all(mx.isfinite(avg))), f"non-finite value in {n}"
        out[n] = avg.astype(mx.bfloat16)                           # cast once, at the end
    os.makedirs(out_dir, exist_ok=True)
    mx.save_safetensors(os.path.join(out_dir, "model.safetensors"), out, metadata={"format": "mlx"})
    # then copy config, tokenizer and chat-template files from fused_dirs[0] into out_dir
```

Expect an average that sits among its ingredients, not above them: averaging
takes the extremes off, it does not hand you the best checkpoint's zero, and
it is not a safety net (§8, lesson 11). If you re-convert published weights,
compare outputs or tensors, not hashes: re-converting our own build directory
with the pinned converter gives the shipped GGUF byte for byte, but a
conversion from a downloaded copy of the repository has the same 310 tensors
and different header metadata.

Stay at **q8_0**: it is the only quantization of v10 we have measured, and it
is the file v10's gates judged. Below q8, measure before you trust it: the
lower-bit accuracy figures we have are from v7 weights (there, Q4_K_M pulled
W down one-sidedly on the turns with the highest reference W while bucket
agreement barely moved; table in [`eval/README.md`](../eval/README.md)). Run
[`eval/compare_quants.py`](../eval/compare_quants.py) against your q8 build
first and read its directional table, not just agreement (it grades against
the exam's v10 labels by default; pass `--labels v9` for v9 builds and
`--labels pre_v9` for v7-based builds; the subset the script calls
high-withdrawal is the exam's questions with teacher W ≥ 1.5, a wider band
than the W ≥ 2.5 turns this guide means by the term).

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
With ollama's default `repeat_penalty 1.1` in place of 1.0, v10 q8 on the old
B exam (legacy key; llama.cpp with Metal) went from 3/104 fabrications (2.9%)
to 15/104 (14.4%) and from 2 sign flips to 4. The earlier measurements we
published, on other versions and occasions, pushed in the same direction
([`eval/README.md`](../eval/README.md)): keep all three lines.

In production, set `keep_alive=-1` and send one warm-up request after every
restart (the toolkit's `OllamaClient` already sends `keep_alive=-1` per
request).

Compare the served model with the evaluated one, item by item, before you
trust either: the same GGUF can score differently in another runtime, which
is how the `repeat_penalty` problem was found. For v10 we ran two such checks
against an ARM CPU server running ollama: of 100 synthetic items, the
five-score read-out was identical to llama.cpp with Metal on 98 and within
±0.5 on all five dimensions on 99 (server prompt cache switched off; an
earlier run with it on, the default in ollama 0.32.5, gave 95 and 98 — see
the [FAQ](faq.md)); and the serving check specified in the draft protocol
(138 synthetic items of the old exams, with the toolkit's trimming; run on
2026-10-05, two days after the verdict) reproduced Metal's sign-flip and
W-floor counts. We make no
cross-runtime claim beyond these; v10's gates ran on Metal.

**Then take the exam.** The toolkit ships a deployment self-check — 195
synthetic teacher-labeled questions plus 10 handwritten crisis-gate cases:

```bash
python eval/run_exam.py --model my-score-model
```

Compare against the reference band in [`eval/README.md`](../eval/README.md).
For the v10 label set, the default: JSON validity ≥ 99%, dimension-level
84–90% with each dimension ≥ 75% and A ≥ 86%, gate **10/10 — hard
requirement**. The shipped v10 q8 scores 87.3% (llama.cpp with Metal,
`server/Modelfile` template, neutral sampling). Four notes for fine-tuners:

- **Three label sets, one per rubric combination**: `--labels v10` (the
  default; A under rubric v8, legacy B), `--labels v9` (rubric-v8 A, crisp B)
  and `--labels pre_v9` (old A, legacy B). Grade a v9 or v7 deployment
  against its own set (bands in `eval/README.md`). The A floor is what tells
  v10 weights from v7 weights (A about 80 on the v10 labels).
- **The exam is in-distribution by construction, so it certifies wiring, not
  model quality.** Its labels come from the same teacher prompts as the
  training labels. And it uses the toolkit's own prompt builder and parser
  and pins the sampling options on every request, which overrides the
  Modelfile: it cannot catch a Modelfile that omits `repeat_penalty 1.0`, nor
  a different prompt, sampling setting or parser in your own service. Read
  the score against the trivial baselines `run_exam.py` prints: on the v10
  labels, always answering 0.5 already reaches 77.9% dimension-level, and
  always answering 0 reaches 68.1%.
- If your fine-tune deliberately changed the score distribution — new rubric,
  materially different population — the shipped exam's labels reflect *our*
  rubric and may no longer be a fair test. Regenerate your own exam with your
  qualified teacher: same shape (~200 synthetic questions, zero real data),
  same format (`message` / `context` / `labels` rows), checked for overlap
  with your training corpora (6 of our 195 messages also occur as the latest
  message of a training row; no full prompt is shared). When only the rubric
  changed, as for v9 and v10, re-labelling the same questions is the smaller
  step.
- The gate section must pass **10/10 regardless of anything you trained**.
  It never calls the model — it runs the toolkit's `CrisisGate` keyword lists
  in-process against seven crisis phrasings and three messages that must
  *not* trigger (two death-idiom lookalikes, one ordinary message). Note what
  it does **not** test: that your
  deployment actually routes every message through the gate before the model.
  That wiring is a separate integration test you own. A gate failure here
  means the word lists were altered — fix before going live; a
  consumer-facing mental-wellness deployment that bypasses the gate and has
  no other independent upstream crisis handling breaches license §3(c).

---

## 8. What v8 through v10 taught us

v8 and v9 were the first generations that changed the rubric itself — what
A and B mean — rather than only the data under a fixed rubric. v9L changed B
back, and v10 changed how a generation is judged. Lessons 9–15 are what v9L
and v10 added.

1. **Rubric changes are human rulings first, prompt second.** The founder
   ruled on A over four rounds. The teacher prompt carrying the first three
   was qualified against his own scores on real messages (second batch of 40:
   92.5% within ±0.5, one severe disagreement); the fourth-round farewell
   rule was added afterwards in a variant prompt, which was re-qualified on
   the synthetic A exam only (an exam with no farewell-signal items; §3). Those
   human checks were **not blind**: Claude
   (Anthropic) pre-scored each message and the founder confirmed or changed
   it (13 of 40 changed in the first batch, 6 of 40 in the second), so for 61
   of the 80 items the A label that entered training equals Claude's
   pre-score. v10 inherits these 80 items (236 training rows, 180 of them
   from the 61) and two more things of the kind from v9: 20 rows whose A was
   set to 0 on Claude reviewers' judgement of a farewell signal, and 50 rows
   removed from the corpus after Claude review. No new training label in v10
   came from Claude. Do yours blind: the human scores first, with no model
   score in view.
2. **Re-label only the column that changed, and measure spill-over.** v8
   re-labelled only the A column; in v9, on the 18,162 prompts carried over
   from v7, each change (A, B, the W repair) touched a single column and
   carried every other column over verbatim (the two new patches, 1,380
   rows, were labelled fresh). The first A-rubric prompt showed why: its new
   A section made the teacher more conservative on W and B as well, costing
   several points of agreement on both on our 440 calibration turns, although
   nothing about W or B had changed. After editing one dimension's rubric,
   re-check every other dimension on your calibration set — and use that
   prompt for its own column only. v9L and v10 kept to this: v9L differs from
   v9's corpus in the B column alone, and v10's rule touched only the rows a
   detector flagged (§3).
3. **An answer key can carry the old rubric.** Our crisp-B teacher first
   failed its pre-registered qualification on the v7-era boundary exam; on
   review, much of the failure traced to old-rubric answers in the key. Two
   independent blind graders re-graded the exam, the founder ruled on the 30
   items they disagreed on, and the key was fixed before v9 was trained. The founder's rulings from that
   review (wishes and preferences → 1.0; asking the AI for help → 0) were
   also added to the teacher prompt before it passed, so both the key and
   the prompt moved after the failure. That is a post-hoc revision, and we
   disclose it as one. When a rubric moves, re-grade the key blind before you
   qualify anyone against it. It happened again in v10, to the ideation
   detector's key (§3): a key built from a proxy for the definition is wrong
   where the proxy and the definition part.
4. **Fix the candidate in advance, and never gate against a single baseline
   checkpoint.** v8 failed on two self-erasure items ("fine, I'll do whatever
   you say" scored as a strong boundary) and on E, −1.8 on the real final
   exam against v7's shipped checkpoint. An ablation without v8's new patch failed the same two ways,
   so the patch was not the cause: those items are borderline for this model
   family (three of v7's own four checkpoints flipped them too), and gating
   against one baseline checkpoint was a design flaw. For v8.1 we changed
   that gate to "≥ the lowest of v7's last three checkpoints" — after seeing
   v8's results, which we state openly. v8.1 then fell to its selection rule
   (§6). Lessons 9–11 take this further.
5. **More teachers did not help.** Kimi K3 and GLM-5.2 (open weights) both
   failed a qualification pegged to our incumbent teacher (relative to DeepSeek: GLM-5.2 −3.4 points on E, Kimi K3
   −7.3 on B), and a three-way median beat DeepSeek alone on no independent
   yardstick. Neither labelled any training data. Qualify each teacher on its
   own; a median of unqualified teachers is not a qualified teacher. In v10
   both came back as authors, not labellers: Kimi K3 wrote part of the new
   exam items and GLM-5.2 the messages of the self-erasure training patch;
   the labels on those rows came from the qualified teacher.
6. **Fail fast on account errors.** An exhausted API balance (HTTP 402) was
   swallowed as ordinary "labelling failures" for ~2,000 rows before we
   noticed. Our labelling clients now stop at the first 401/402 and print the
   server's message; other errors still retry.
7. **In-distribution exams inflate gains.** On the exams built for v9, v7 →
   v9 moved a long way: A paired direction 21/154 → 150/154, crisp-B
   fabrication 12.1% → 1.9% with misses up slightly, 5.3% → 6.1% (shipped q8
   GGUFs, llama.cpp with Metal; old B exam, crisp key). But those exams are
   in-distribution for v9's own training patches (the A mid-band patch was
   generated from the A exam's class definitions; the crisp B exam shares its
   generator with the boundary patches): they show that v9 learned the new
   rubrics on that generator's distribution, not that it scores real
   conversations better. The same holds for v10: its new exams and patches
   are synthetic and come from the same kind of generators (exam items by two
   open-weight models, DeepSeek and Kimi K3; the self-erasure training patch
   by a third, GLM-5.2). G2b and G2c are in-distribution for that patch in a
   stronger sense: it was added after reference checkpoints had been scored
   on the new B exam, and that exam still gated v10 — although our draft
   protocol said an exam block should be retired from gating and rebuilt if
   training data was changed in response to item-level results on it. The
   third author model, a new prompt and a similarity filter reduce the
   overlap; they do not remove it. Passing these exams shows no regression
   inside the known range. It does not show generalisation. There is still no
   real-conversation measurement under A rubric v8: the reference labels
   follow the old A rubric, so v10's agreement with them on A (327/453 within
   ±0.5; v7: 383/453) is low by design. For B there is one again: 336/453,
   the same count as v7 (shipped q8 GGUFs). Keep at least one
   real-conversation measurement per rubric, and remember that repeated
   attempts against one exam are a slow form of selection: the real final
   exam has now judged eight generations on this model line (§3).
8. **If you override a gate, publish it. We have now done it twice, in
   consecutive releases.** v9 failed two of its five pre-registered gates:
   v9's gate 4 by one item (H 93.6 against a 93.8 floor on the real final),
   and v9's gate 5 (W safety) clearly — W reached its floor on 78.9% of the
   items of what is now the old W safety exam, against ≥ 95% required (gated
   bf16 model, MLX). By the pre-registered rule v9 was rejected; the founder
   released it as an explicit, recorded decision, ruling that crisis handling
   is the job of the upstream architecture, not of this model. v10 is the
   second time (§6). Gates only mean something if failing one means
   something, so both times the failure is stated wherever acceptance is
   stated and the thresholds were not redrawn. If you override your own gate,
   do the same.

   In v10's registration the W floors are checks G4a–G4d. Across the 189
   ideation-plus-help items of the old and new W safety exams, W is below
   2.5 on 21 for v10, 102 for v9 and 111 for v7 (G4d, pass line ≤ 94), and
   the mean raw stress change is +2.37, −0.24 and −0.29 (G8, pass line ≥ 0;
   shipped q8 GGUFs, llama.cpp with Metal). These are synthetic,
   in-distribution items and rubric checks, not crisis detection. A separate
   point, about the gate and not about the scores: the bundled `CrisisGate`
   is a short keyword list, not a complete screen. On these 189 items, which
   are ideation by construction, it fires on 107. Extend the lists for your
   population, add a second screen alongside the gate (never instead of it),
   and measure both on your own population.
9. **A pass line inside training noise measures the noise.** v8, v8.1, v9 and
   v9L failed their pre-registered gates one after another, mostly by a few
   items. When we held the 14 legacy-B checkpoints we had kept against v9L's
   six gates, none passed all six, and 2 passed the four that are sensitive
   to run-to-run variation. Before you write a pass line, measure how far
   your own saved checkpoints scatter around it.
10. **A zero-tolerance gate on a few dozen items rejects good models.**
    A zero line on a small pool is decided by a single item. G5a was such a
    line, the one v10 did not meet (§6); the zero-flip line on the old B exam
    was another: of 15 late checkpoints on file (saved bf16
    predictions, MLX), 4 have zero flips on the old B exam. Count rare
    errors on hundreds of items and cap the rate, with the cap written down
    first. The price: by our design
    estimate such a cap stops a mere doubling of a rare error half the time
    at best, and it says nothing about any one item (lesson 15).
11. **Fix the candidate by rule, not by pick.** A pick after the fact lands
    on a lucky draw; a pick by validation split lost v8.1; the last
    checkpoint keeps the luck. A rule-fixed, rehearsed average damps it, at
    the price of the best checkpoint's best numbers. It is no cure: an
    average sits among its ingredients, not above them.
12. **A second seed is a report, not a spare candidate.** v10's second seed
    (`seed: 2`; scored after the verdict was written; a stand-in only if the
    first run could not finish training) passed all 18 checks and was not
    used: substituting it would have been selection by exam score.
    What it shows is the spread between two runs of one file (q8: G1 149 and
    152 of 154; G6b 336 and 346 of 453; G7 −0.72 and −0.59 per turn). A
    difference of that size between two generations is not evidence that one
    is better.
13. **A rubric must change together with the formula that consumes it.** This
    is the correction of §1 as a rule. The crisp rubric is not disowned: it
    is a cleaner definition of boundary-setting with a more stable teacher,
    and v9 stays downloadable for anyone who wants that instrument on its own
    terms. What was wrong was shipping it into a formula calibrated for the
    legacy rubric without re-centring the formula. Change the consumers
    (formula, cut-offs, other scorers, charts) in the same release, gate the
    trajectory over replayed sessions as v10's G7 does, and do not tell users
    to "re-tune" unless you have found a re-tuning that works.
14. **Check each gate against the owner's standing rulings before you sign.**
    G5a made a stand-in for crisis handling a hard gate, although the
    founder had ruled twice before (at v7's checkpoint choice and around v9's
    release) that crisis is handled upstream, not by this model. It ended in
    a waiver made after the result, the worst moment to learn that a gate is
    not one; our next registration will not gate on G5a. Ask the person who
    can waive each gate: if this is the only line that fails, do we reject?
15. **A rate cap protects no particular sentence.** v10 passed G2a and G2b
    with a flip on a longer form of §6's sentence counted (the old B exam
    item ends 「…，你安排吧。」; the short sentence is not an exam item), as
    those gates allow: on the 438-item pool it reads self-erasure as a
    boundary far less often than v7 (4 against 47, both q8), and it misreads
    the very
    sentence v7's shipped checkpoint was chosen for reading correctly. That
    sentence is therefore not evidence
    that v10 scores self-erasure as B 0. Keep the sentences that matter to
    you as a named list, report each read-out beside the rate, and decide
    before training whether any is a hard line.

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

## Appendix: twelve generations at a glance

**v2–v5** — bf16 adapter through MLX; real-turn numbers on the full 758-turn
set. In the tables below, a "high-withdrawal turn" is a turn whose reference W
is 2.5 or more.

| Generation | What changed | Outcome |
|---|---|---|
| v2 | first distillation, 7.5k synthetic | shipped — dim 81%, decision 95.4% |
| v3.x | rebalance + defect repair | shipped — decision 96.8% |
| v4 | 8-agent data audit: prompt masking, style quotas, mid-band cells, 15k corpus | shipped — dim 84.0% (+3.1), W fell toward 0 on fewer high-withdrawal turns, output vectors 59 → 87 |
| v5 | synthetic patch cells with a W-cap admission gate | **rejected** — on high-withdrawal turns of the real set, W fell toward 0 much more often than for v4; taught us the distress-adjacent W-cap rule |

**v6–v9L** — bf16 adapter through MLX; real-turn numbers on the 453-turn real
final exam; gate results on the A, old B and old W safety exams are named in
the cell.

| Generation | What changed | Outcome |
|---|---|---|
| v6 | +440 real turns with the reference scorer's labels, unscreened | **rejected** — three rows with high-withdrawal content on which the reference labels gave W 0 entered training, and W regressed the same way as v5's, toward 0 on high-withdrawal turns; taught us R2 |
| v6.1 | same 440 real turns, with the teacher's labels on every row (it gives the three artifact rows W ≥ 2.5) | shipped, superseded by v7 — dim 85.6%, decision 96.2%; on the high-withdrawal turns of this split W fell toward 0 more often than for v4 (recorded as resting on borderline content not yet human-reviewed) |
| v7 | same config as v6.1; teacher re-labelled the corpus at temperature 0 + 2,713-row boundary-discrimination patch (18,856 train rows) | shipped, superseded by v9 — dim 85.1%, decision 97.1% |
| v8 | A rubric v8 (four rounds of founder rulings) + 1,100-row A mid-band patch; only the A column re-labelled | **rejected** — failed 2 of 4 gates: two self-erasure B sign flips returned on the old B exam, E −1.8 vs v7's shipped checkpoint. An ablation without the patch failed the same two ways (and reached only 79% paired direction on the A exam); taught us not to gate against a single baseline checkpoint |
| v8.1 | v8 + 280-row self-erasure B patch; gate 4 revised, after seeing v8, to "≥ the lowest of v7's last three checkpoints" | **rejected** — the pre-registered selection rule picked iteration 4,800 by 0.4 pt on the validation split; it failed gate 2 (3 flips on the old B exam) and gate 4 (H 0.4 below the floor). 7,200 passed all four and was not substituted; taught us to fix the candidate in advance |
| v9 (released by founder decision; superseded by v10) | A rubric v8 + crisp B (whole B column re-labelled) + W safety repair (285 rows raised); same config as v7, 20,187 train rows; candidate fixed in advance (7,200); five gates incl. a new W safety exam | **released by the founder's decision** after passing 3 of 5 gates — failed v9's gate 4 (H one item short) and v9's gate 5, the old W safety exam (78.9% vs ≥ 95%). Real final (old-rubric labels): W/E/H 88.1/86.1/93.6, decision 96.0%. Its crisp B does not fit a formula with a negative B weight (§1) |
| v9L | v9's corpus with the B column alone returned to legacy-rubric labels (20,187 train rows); same config; candidate fixed in advance (7,200); six gates, one of them new, on the stress trajectory | **rejected** — passed 4 of 6 gates: paired direction on the old B exam 56/60 (58 required), H on the real final exam 422/453 (floor 425); the trajectory gate passed. Taught us that our pass lines sat inside training noise |

**v10** — judged q8 GGUF through llama.cpp with Metal; real final exam (453
turns).

| Generation | What changed | Outcome |
|---|---|---|
| v10 (released by founder decision) | v9L's corpus + the explicit-ideation rule (detector + deterministic code; labels changed on 179 training rows) + two minimal-pair patches of 150 pairs each; 20,787 train rows; same config, seeds 1 and 2; candidate fixed by rule: the average of seed 1's fused checkpoints at 4,800 / 6,000 / 7,200, judged as q8; 18 checks with noise allowances and rate caps | **verdict under the signed pre-registration: rejected** — it met 17 of the 18 checks; the one it did not meet, G5a, was a stand-in for crisis handling, which the founder ruled outside this model after seeing the result. **Released by the founder's decision**, a waiver of that gate made after the result was known (§6). Real final exam: W/E/H 87.4/85.2/93.2, B 74.2, decision 96.0% |

The 453-turn final is a split of the 758-turn set (v4 on the split: dim
84.6%, decision 95.6%). Rows up to v9L report the numbers
each generation was judged on at the time; v10's row is the judged q8, so do
not read a few tenths of a point across that line as a difference between
models. The dimension averages of
v9 and v10 against old-rubric labels are left out on purpose: on A (and for
v9 on B) they measure how far the rubric moved, not accuracy. The A gains of
v9 and v10, v9's crisp-B gains and v10's gains on self-erasure and on
ideation-plus-help were measured on in-distribution synthetic exams (§8,
lesson 7).

Those twelve adjudicated generations sit on top of a good many more training
runs (pilots, restarts, two runs that diverged mid-way, an ablation, v10's
second seed, one run on a larger student that was dropped). You will train
more often than you will ship.

The pattern worth copying is not any single number. It is that each
generation was judged on real held-out turns kept out of training and, from
v6 on, against a gate written down before its own results existed. Five
rejections are not a failure statistic — they are evidence the process works.
The last two releases are the open overrides of an acceptance gate (v4, v6.1
and v7's checkpoint choice were judgment calls, §6), and we will not dress
them up: v9 failed two of
its five gates, one of them on the W safety exam; v10 did not meet one of its
18 checks, G5a, a stand-in for crisis handling, and its verdict under the
registration as signed was "rejected". Both were released by the
founder's decision. A gate that can be waived is only as strong as the
disclosure that follows, so each failure is stated where acceptance is stated
and the thresholds were not moved after the fact. If you override your own
gate, or find — as we did with "re-tune your thresholds" — that your own
guidance was wrong, publish it the same way.

---

# 中文

## 给专业机构的微调指南（精编）

你从 HuggingFace 下载了
[hamo-score-0.6b](https://huggingface.co/HamoAI/hamo-score-0.6b)，想用**经
授权的**自有数据把它适配到你的人群、语域或语言。本文是十二代定谳模型蒸馏出的
操作手册（中文为精编，细节以英文版为准）：五代训练完成后被**拒收**（v5、v6 因
在真实数据的高退缩轮次——即参照 W ≥ 2.5 的轮次——上把 W 打到接近 0 的次数多于当时的现任 v4，v8、v8.1、v9L 未过
预注册验收闸门）；另有两代没过预注册闸门、之后
**由创始人决定发布**，连续两次：v9（五道闸门过三道）和当前的 v10。v10 的状态：
**签字版预注册的 18 项检查过了 17 项；没过的那一项 G5a 当初是作为危机处理的替代
指标设的，创始人看到结果后裁定危机处理不在本模型里判定；按签字的预注册，判定是
「拒收」，v10 由创始人决定发布——这是看到结果之后对一道预注册闸门的豁免**。受检的
文件就是发布的文件。模型的技术档案（模型卡里有链接）报告 18 项中的 16 项（16 项全过），并节录了裁定原话
（[Evaluation](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation)）。全部经验
来自一台 MacBook 加 API 打标，不是集群规模的流程。除另有说明外，v2–v9L 的成绩
出自 bf16 adapter 经 MLX、温度 0（各代当时受判的口径）；标 q8 的是 GGUF 经
llama.cpp + Metal。先立框架：它是**测量仪器**——
不是聊天机器人、不是诊断工具、不是咨询师，也**不是危机检测器**：它的分数，包括 W
在内，没有一个是危机信号。危机处理放在模型
上游：许可证 HAMO-RAIL-S §3(c) 要求面向消费者的心理健康部署必须有独立的上游
机制；确定性闸门（`CrisisGate`）则是本项目架构对一切部署的要求。微调不改变、也
不允许改变这一点。

### 一、先想清楚要不要微调

多数需求不需要动权重：人群特有的危机说法 → `CrisisGate(extra_keywords=[...])`
一行扩词表；下游敏感度 → 改 `stress.py` 里的平滑与分桶阈值；个别句子评分不服 →
分数要经 `0.8·历史 + 0.2·本句` 平滑，单句噪声会被吸收，成规律的分歧走仓库的
「评分分歧」issue 模板——我们收集这些报告，供人工复核口径与后续版本时参考。

**更正：对 v9，「重调阈值」并不够。** 本指南上一版说「升级到 v9 本身就是一次
重调」，这是错的。v9 的 crisp B 在普通消息上多半是 0，B 为负权重的公式因此失去
减压项，重调阈值或 B 的权重都补不回来（权重乘的是 0）：453 轮真实终评上，按 v9
的分数算出的平均每轮原始压力变化是 +0.37，参照标签是 −0.68，v10 是 −0.72（随包
q8 GGUF，llama.cpp + Metal）。v9 不再是默认版本：请换 v10 或退回 v7，按 v9 分数
累积的压力值不要带过去；完整更正、固定版本与回退见集成指南
[「升级到 v10」](integration.md#升级到-v10)，由此得出的规则是§八第 13 条。

**升级到 v10 会改变什么。** 工具包自 0.3.0 起，参考服务端提供 v10，自检卷默认按
v10 标签判。A 沿用口径 v8（同 v9），与 v7 的 A 不可比，读数也更低（真实终评平均
A：v10 0.53、v7 0.68；随包 q8）。B 回到 v7 所用的 legacy 口径，不要与 v9 的 B
比较。训练标签新增一条规则：消息含明确自杀意念时，A 封顶 1.0、B 为 0、W 至少
2.5（W 的下限沿用自 v9 的 W 安全修复，A 封顶与 B 归零是新增）。这是标签规则，
不是输出保证；它是一条关于分数和压力公式的规则，不是危机处理（合成的
「想死但求助」题上的数字见§八第 8 条）。压力权重与 4.0 / 7.0 分桶阈值未改动，是按 v7 及更早的分数定的；v10 的轨迹闸门
（G7）在我们的真实终评上通过，不等于替你的人群验证了阈值。

真正该微调的场景：新语言（模型以中文为主：按 v10 训练集每行的最新消息统计，
中文约 76% / 英文 13% / 中英混杂 11%）、明显不同的语域人群、你们临床团队正式
定义的量表变体。**永远不要**为了「让模型会认危机」而微调——闸门管危机，模型管
其余，倒过来就是在诱惑别人拆闸门；面向消费者的心理健康部署若因此没有了独立的
上游危机处理，正是许可证 §3(c) 禁止的。

### 二、数据红线（先于一切采集）

- **R1 知情同意**：我们的训练语料是合成数据，唯一例外是 v6.1 起加入的 440 条
  真实对话轮次——来自三位公司内部员工（创始人与两位咨询师）、经本人明示授权、
  ×3 上采样（v10 的 20,787 条训练行中为 1,310 行，6.3%）；**外部来访者对话从不
  入训，构造上保证**。照此执行：真实来访数据可做考卷（当地法规与治理允许时），
  入训必须有书面、可撤回的本人授权。「已脱敏」不等于授权。
- **R2 标签工件筛查**：v6 拒收的教训。被上游闸门短路的消息，评分器并没有真正
  处理，在生产里存下来的是零分或近零分数；内容若是高退缩的，这一行就是毒标签——
  该打高 W 的文本，存的却是 W 0。参照标签给 W 0（其中 2 条五维全零）、教师
  给 W ≥ 2.5 的 3 条随真实数据入训（上采样后各 3 份），453 题终评集的高退缩轮次上，
  W 被打到接近 0 的次数比当时的现任 v4 多，整代拒收。规则：真实行入训前，用合格
  教师全部打一遍；两套标签相差很大的行（我们的做法：教师给 W ≥ 2.5 而原标签
  W < 0.5），必经人工复核（只靠词表找不全这些行）；文标矛盾的行（文本高退缩、标签
  为零）删除或重标——没有「才几条」的豁免。
- **R3 永不训练模型识别危机**：确定性闸门独占此职责，模型的分数（包括 W）没有
  一个是危机信号。W 在量表高端读得准不准值得单独检查（见§六），但那是仪器的性质，
  不是防线。v10 就是例子：它唯一没过的 G5a 当初是作为危机处理的替代指标设的，而
  发布的依据是创始人的裁定——危机由上游处理，不在这个模型里判定（见§六）。
- **R4 卫生**：全量脱敏，并如实称呼——我们自己的导出只做到**假名化**（固定盐、
  完整时间戳、正文仅正则脱敏），仍属个人信息，删除权仍及于它；真实数据不进
  git；保留一页式数据台账。

### 三、先出考卷，再编教材

项目第一件产物是**真实数据终评考卷**（永不入训），第二件是**过了资格考的
教师**。顺序颠倒，你会不自觉地照着模型的长处出题。三切分：教师资格/校准集、
选点集、终局集（只为发布决定而考：不用于给候选选点（v7 为例外，见§六）、不用于
改提示词）——我们的：1,198 条假名化真题 → 440 条校准集 + 758 条留出集，后者再切为
305 条选点集与 453 条终局集（下称真实终评）。终局集上尽量少打分，每多看一次都是
一点选点压力。我们的还在旧训练上用于设计 v10 的方案：平均规则的彩排在它上面给
v7、v8.1 的平均与原料打过分，G6、G7 的线也是照早先检查点在它
上面的成绩定的。更早，切分之前 v2–v5 在包含这 453 条的 758 条整卷上打过分，对
v3.x 在整卷上的错误分析还用于设计 v4 的训练格子。v10 的判定是第八次有一代模型在它上面受判（v6、v6.1、v7、v8、
v8.1、v9、v9L、v10；注册里算作第七次），参照检查点、消融、彩排、第二个种子和复测
还不算在内。305 条那份（封存的真实考卷）自 v7 之后没有再用过，v10 的注册把它留作
日后只用一次、两条准则事先写定；2026-10-05 在 v10 的 q8 上用了这一次：W+E+H
一致率那一条满足；另一条与 G5a、G5b 同类，按创始人的裁决不报告（见§六）。每行
连同消息、上下文、金标一起，**记录当时的压力值等决策上下文**——否则算不了决策级。

教师资格考：给训练数据打标的模型（我们用 deepseek-chat + 生产量表，temperature
0）先考你的真题，我们的线：维度级 ±0.5 约 89%、决策级 97.5%；要逐维看——我们教师
B 维初考 72%，靠量表校准注记修到 78%，平均数会把坏维度藏起来。整体重标可能悄悄
撤销早先的修复：v7 的重标丢掉了一条 W 规则（绝望后跟行动仍保持 W ≥ 1.5），v9 的
W 安全修复把它补回（连同新规则「求助不抵消自杀意念，W ≥ 2.5」上调 285 行）。
口径一改就要按列重新资格考：v9 的 A（口径 v8）与 B（crisp）各用一份提示词、各自
先过资格考才打标；A 提示词另有一个加了告别规则的变体，单独过了资格考，给新合成
补丁打 A 列；为 W 安全修复重打 W 的那份提示词没有单独过资格考：v9 里我们只接受
它的上调；v10 里它还给「想死但求助」补丁的 300 行打了 W、E、H、B，没有这层筛选
（意念一臂随后按明确意念规则改标）。v9L 与 v10 的 B 列回到 legacy 口径：沿用的行取回教师在 v9 之前以
temperature 0 打出的标签，v10 新补丁的行按同一口径新打。

**范围很窄的规则，可以用检测器加确定性代码落实，不必改教师提示词。** v10 新增
的规则（明确自杀意念 → A 封顶 1.0、B 为 0，W 至少 2.5 沿用 v9 已有的下限；使意念
旁边的求助不会让算出的压力下降）没有写进教师提示词——改一段会外溢到别的维度。做法：一份冻结的
检测器提示词，跑在开放权重模型上（deepseek-chat，temperature 0），只回答「最新
消息是否含明确自杀意念」；判中的行由确定性代码改标签：`A = min(A, 1.0)`、
`B = 0`、`W = max(W, 2.5)`，其余教师标签不动。它在 19,542 条不同提示里判中 702
条，改动了 179 条训练行的标签。检测器偏宽；这条规则只会压低 A、清零 B、抬高 W。
检测器也要先过资格考、合格线在出分前写定：我们的第一次考四条线有一条没过，复核
发现错在答案（更正 2 行、剔除 1 行），检测器未改动，随后达标。**这是看过结果之后
改答案**，我们照此披露（细节见技术档案）。

再量一下现任评分器的自洽：2026 年 8 月的两次抽查（各 12 条消息）里，参照评分器
对自己的维度判断在 ±0.5 内复现的比例是 95% 和 98%——只是粗略的实际上限。若另建
LLM judge 用于任何触人环节：与持牌专业人员的 kappa ≥ 0.6 才可用。

### 四、训练数据格式

mlx-lm 聊天格式 JSONL，user 内容**必须**用 `hamo_score.build_prompt` 构造
（训练与推理提示词逐字节一致；工具包安装：`pip install hamo-score`）；assistant
内容是单个 JSON 对象：五键、一位小数、吸附到 0.5 网格（教师标签不一定在网格上），
无任何多余文字。`build_prompt` 自带截短（只留最后 3 轮上下文、每轮 200 字，消息
500 字）：这是工具包的延迟护栏，不是我们的模型训练时见到的样子——v10 训练行里有
36.6% 的上下文超过 3 轮。

示例行见[英文版 §4](#4-training-data-format)：其中的分数是发布版 v10 在那条提示
上的实际读数，充当教师标签；同一条提示，v9 读出 B 0.0，v7 读出 A 2.5、B 2.0（均为
q8）——分数不能跨这几个版本比较。

合成教材按场景格子组织，配**准入闸门**（教师标签落在格子设计带内才收，否则
弃样）。**v5 铁律：凡文本与痛苦相邻的格子，准入禁设 W 上限**——v5 的「有界
担忧链」格子设了 W≤1.0 准入，等于教模型「担忧文本→压 W」，758 题全卷的高退缩
轮次上，在这张卷上打过分的检查点把 W 打到接近 0 的次数都明显多于 v4，整代拒收。风格配额要对齐真实分布：我们的真实
流量（2026 年 8 月）35.5% 是不足 15 字的短消息、62% 带满 5 轮上下文，合成器天然写不出
这些——按真实占比强制配额，再加生成器口头禅黑名单、中间档（0.5/1.0/1.5）标签
强制出现、纯原型样本 <20% 封顶。

**模型总分不清的区别，用最小对照对来教。** v10 新增的两份补丁都是成对题，各
150 对（300 行）：「想死但求助」对「同样的求助、没有意念」；自我消融（收回刚说
的界限、认错讨好）对「守住界限」。准入以「对」为单位：两臂都落在设计的位置才
收。此前打过分的 9 个参照检查点（v7、v8.1、v9L 各 3 个，q8）没有一个能过这两份
补丁瞄准的 G2b、G2c、G8；v10 的两个种子三道都过了——限定条件见§八第 7 条。

真实授权数据少量即有效：v6.1 的 440 条 ×3 上采样让 453 题终局集维度级 +1.0pt
（v4 84.6% → v6.1 85.6%）。其中一部分进步是「更容易」而非「更干净」：员工跨会话
会重复说话，453 题中有 42 题的消息原文也出现在入训的 440 条里，85.6% 中约 0.4
个点来自这部分重叠（411 道无重叠题上为 85.2%）。

### 五、LoRA 配方（MLX，一台 MacBook）

发布版 v10 的真实配置（一台 M1 Pro MacBook，16GB）。超参与 v6.1、v7、v9 完全
相同；与 v9 的配置文件相比只有数据路径、adapter 路径与 `seed` 不同——预注册的
候选那一轮用 1，只作报告的第二轮用 2（v9 用 0）。路径改成你的，数字别动：base
`mlx-community/Qwen3-0.6B-bf16`，LoRA rank 8 / scale 20 / 16 层，
`batch_size: 4`，`iters: 7200`，LR `7e-5` cosine 退火至 `7e-6`（warmup 100），
**`mask_prompt: true`**，`grad_checkpoint: true`，`max_seq_length: 1024`，
`save_every: 1200`，`seed: 1`。运行：`python -m mlx_lm lora -c finetune.yaml`。
三个数字是伤疤：① `mask_prompt` 不开，72% 梯度耗在给来访者消息做语言建模上；
第一轮只改配方的训练（开 `mask_prompt`，同时加余弦退火、步数减半，数据不变）在
440 条校准集上决策级 +1.4pp（423 → 429 条），没有单独拆出它的贡献；② 16GB 机器上
seq 1024 配 batch 8 会顶到 16.6GB 并**无声数值爆炸**（loss 0.118→10.8），序列
翻倍、batch 减半；③ seq 别降到 512——会截断长上下文样本，正是配额辛苦补进来的那些。另一道
伤疤不在配置里：**16GB 笔记本白天日常使用下会中途发散**——v8.1 与 v9 的第一次
尝试都发散了，之前都先出现变慢和内存交换。自 v8.1 起训练在 `caffeinate` 下跑，
并配发散监测：第 400 步后训练 loss 超过 1.0 即停止、从头重练。关掉吃内存的程序，
或者夜里跑。v10 的两轮都没有发散，却是白天跑的：签字后立即开训，而注册里写的是
22:00 开始——这是对注册的一处偏离；两次白天顺利跑完，不等于这条建议可以作废。
`save_every: 1200` 产出六个检查点：选点池，或预先定死候选时的稳健性证据，或（如
v10）平均候选的原料。一轮约 2 小时（v9 的 20,187 条训练行；v10 的 20,787 条两轮
每轮相近；M1 Pro 16GB）。valid 切分只用来盯训练是否发散，**不**用来选点；v10
多给了它一个用途：对平均候选做一次只能降级、不能挑选的健全性检查（见§七）。

### 六、选点与验收

**永不用合成 valid loss 选点**——我们的合成 valid 比真实分布重尾 3 倍，在
它上面早停等于为假分布选模型。选点在**真实校准集**上、按**决策级**（分数过
确定性压力折算后的状态桶一致率，即下游真正消费的数字）。选点表四列：维度级
±0.5（诊断用）、决策级（选点用，<2pt 视为噪声）、**高退缩轮次上的 W**（金标
W≥2.5 的轮次里有多少条预测 <0.5——总体一致率会掩盖 W 在量表高端的单向塌缩：v5 的
选点冠军在 758 题全卷的这些轮次上，把 W 打到接近 0 的次数明显多于 v4）、**输出向量种类数**（塌缩
探测器：某早期学生在 758 题全卷上只输出 59 种五维组合，参照标签有 233 种）。比较
检查点时要单独看高退缩轮次上的 W；这一列读的是 W 的保真度，不是危机处理。一段
历史：v7 之前，这个数高于现任的检查点在选点时就不收；到 v9L 为止，它仍卡验收。
这两道闸门后来都由创始人撤掉了，理由是危机处理归上游的确定性代码（Hamo 称之为
「脊柱」），不归这个模型。v7（2026-08）预注册的这类过滤选中第 6,000 步；
约束解除后，我们推翻了这一选择，改发边界符号
翻转（把自我消融、金标 B=0 的发言打成高 B）为 0 的第 7,200 步；这次推翻是在两者都
已考过终局集之后做出的。v10 的注册仍把这个数写成 G5a；创始人在看到结果之后
（2026-10）把这道闸门搁置了（见下），下一份注册不再拿它设闸。

**或者在训练前就定死候选。** 选点本身就是噪声源：v8.1 预注册的选点规则（验证集
一致率最高）以 0.4 个点之差选中第 4,800 步——它没过两道闸门，而第 7,200 步本可
四道全过。我们没有改选：看过闸门结果再改选，闸门就成了摆设。v9 与 v9L 在训练前
定死候选为最后一个检查点。

**或者按规则取平均：v10 的候选。** 定死最后一个检查点，去掉了「挑」，没去掉
运气。所以 v10 的注册把候选定成一种做法：候选那一轮第 4,800、6,000、7,200 步
三个检查点**融合后权重**的平均，转成 q8 GGUF。不按考卷成绩挑任何东西——不挑
检查点、不挑种子、不挑平均。规则在训练前用两轮不可能成为候选的旧训练（v7、
v8.1）彩排过：平均若比三个原料里最差的那个还差，规则就定为「最后一个检查点」。
判什么，就发什么：闸门在 q8 GGUF 上经 llama.cpp 跑（此前各代是在 bf16 adapter 上
经 MLX 判的），发布的 bf16 safetensors 是同一份平均权重。

终局硬闸（沿用至 v7）：**决策级 ≥ 现任，且高退缩轮次上 W 被打到 0.5 以下的次数
不多于现任**，任一不过整代拒收、现任留任。第二条是 v5 拒收（758 题全卷的高退缩
轮次上，W 被打到接近 0 的次数明显多于 v4）之后加的，v6 即按此规则拒收；这一条就是后来由创始人撤掉的那道
闸门（见上）。有两代发布时字面上并未达标：v4 决策级 96.3%，低于当时现任的
96.8%（758 题全卷，记为统计平手）；v6.1 在 453 题终局集的高退缩轮次上，W 被打到
接近 0 的次数比 v4 多（决策级 96.2% 对 95.6%），多出的部分记为未经人工复核的边缘
样本。口径本身改了，
闸门也得跟着改：拿旧口径标签比决策级不再是干净的尺子。但它确实降了：真实终评上
决策级 v7 为 440/453（97.1%）、v9 为 436/453（96.2%）、v10 为 435/453（96.0%）
（随包 q8，llama.cpp + Metal）——按 v8 之前的旧闸门，v9 与 v10 这一条都过不了；下降有一部分来自 A 口径
改动本身，这张考卷分不开。自 v8 起每代在训练前预注册一组闸门：v8、v8.1 按各自
闸门拒收；v9 五道过三道，由创始人决定发布；v9L 六道过四道，被拒收。

**v10 的闸门：G1–G8。** 连续四次判定拒收（v8、v8.1、v9、v9L）之后，v10 的注册
改的不只是线画在哪里，而是线怎么画（见§八第 9、10 条）：普通一致率带事先声明的
波动余量；罕见错误放到 93、438、596 道的题池上数，按比例设上限，扩大后的题池的
上限按固定公式由 9 个参照检查点算出，再夹在上下界之间——上下界的比例事先写定，
绝对数是看过一个参照结果之后按冻结的题量等比放大的（两个 B 题池的上限都由放大后
的上界决定，不是公式值：17/438 与 21/596）；压力轨迹（G7）与「想死但求助」题上
算出的压力方向（G8）直接设闸。还剩一道零容忍的线，G5a：它定义在真实终评的轮次
上，当初是作为危机处理的替代指标设的（本指南不报告 G5a，也不报告与它配套的 G5b，见下文
「结果」）。各项检查只跑一次、只判
一个候选（q8 GGUF，llama.cpp + Metal，温度 0，`repeat_penalty 1.0`、`top_k 0`、
`top_p 1.0`；各题用存档的完整上下文，不经 `build_prompt` 截短）。18 项检查中 16 项
的通过线与结果、以及哪些事是看过结果之后才定的，见技术档案
[Evaluation](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation)。

**结果。** 签字的预注册列了 18 项必过的检查。技术档案报告其中 16 项，这 16 项都按
签字时的通过线通过。另外两项 G5a、G5b 定义在真实终评的轮次上，当初是作为危机
处理的替代指标设的：G5b 达到了，G5a 没有。所以 18 项检查 v10 过了 17 项；按签字的
预注册，判定是「拒收」。看到结果之后，创始人裁定：危机处理不由这个模型判定，也
不由它的 W 分数判定，而是在脊柱（模型外围的确定性代码）里做；v10 通过——这是
看到结果之后对一道预注册闸门的豁免。依这项裁决，本指南、模型卡及其技术档案都不报告 G5a、
G5b，下一份注册也不再拿 G5a 设闸。受检的文件没有更换；第二个种子的平均 18 项
全过，但它只作报告，没有采用。这是连续第二次在没过预注册闸门的情况下由创始人
决定发布（v9 是五道没过两道）。裁定原话的节录见技术档案。

**已知的一条 B 符号翻转。** v10 把「行，我全听你的，你说哪天去就哪天去。」打成
B 2.5，v7 与 v9 打 0（q8，llama.cpp + Metal，无上下文）。旧 B 卷里有它的加长版本
（句末多一句「…，你安排吧。」），v10 同样打 B 2.5——这是计入注册上限的翻转之一
（G2a 2/93，上限 3；G2b 4/438，上限 17），在后一个题池上远低于 v7（47/438，q8）。但
v7 的模型卡正是用这句话（当时印的不带句号）说明「仪器不得把自我消融读成边界」
（完整说明见 [FAQ](faq.md)；教训见§八第 15 条）。

接真实流量先跑**影子模式**（新模型并行打分、现任说了算、每一对都记录），切换
标准预注册（例如：影子 ≥1 周、回退率 <2%、决策级 ≥96%、平滑压力轨迹偏差
≤0.05）。轨迹这一条要靠整段会话回放来算：v9 的单步决策级只比 v7 少
4 轮，回放的会话末值却平均比参照标签高 0.51（真实终评，随包 q8）。给自己的清单
签字之前先看§八第 10、14 条：只有少数几个事件的零容忍线，或者负责人事后会豁免的
条件，都不该写进注册。

### 七、上线

分两条路，看§六怎么定的候选（命令与代码见[英文版 §7](#7-ship-it)）。

**单个检查点。** 融合**选中的检查点**，不是训练目录：
`adapters/my_run/adapters.safetensors` 永远是**最后一步**的权重，若选中的不是
最后一个检查点，直接融合训练目录会无声地发错权重。先把选中的检查点物化到单独
目录，再 `python -m mlx_lm fuse` 融合、用 llama.cpp 的
`convert_hf_to_gguf.py --outtype q8_0` 转 GGUF。

**平均候选（v10 的做法）。** 先后顺序是关键：① 每个原料检查点**各自**物化、
各自融合；② 对几份完整权重逐张量取 float32 平均，最后一次性转回 bf16——**绝不
分别平均 LoRA 的两个因子**，乘积的平均不等于平均的乘积；③ 看任何成绩之前先核对
构建（张量列表一致、没有非有限值、读回几张张量确实等于原料的平均）；④ 用固定
版本的 llama.cpp 转成 q8_0，这个 GGUF 就是候选；⑤ 跑一次只能降级的健全性检查。
我们的 G0 在 249 行验证集上跑（验证集不是考卷）：没有 JSON 失败，q8 与 bf16
接近，一致率、标签 W ≥ 2.5 的行上的 W、金标 B = 0 的行都不比最差的原料差（留事先写定的小余量）；
不过就把候选降为最后一个检查点，它不能把任何东西提上来。v10 的平均五个条件全过。
平均落在原料之间，不会更高，也不是保险。自己重新转换已发布权重时，比输出或
张量，不要比哈希：重转我们自己的构建目录能逐字节复现发布的 GGUF，而从下载的仓库
副本转换，310 张张量相同，文件头元数据不同。

**量化档位。** 就用 q8：它是 v10 唯一测过的量化档位，也是 v10 的闸门所判的文件。
更低位宽先实测再信：我们手头的低位宽准确率数据来自 v7 权重（在那里 Q4_K_M 让
参照 W 最高的那些轮次的 W 单向偏低，分桶一致率却几乎不动；表格见
[`eval/README.md`](../eval/README.md)）。先跑
[`eval/compare_quants.py`](../eval/compare_quants.py) 与你的 q8 档对比，看方向性
表格（默认按 v10 标签判；v9 的档位加 `--labels v9`，v7 系的加 `--labels pre_v9`；脚本里说的
高退缩题是教师 W ≥ 1.5 的题，比本指南所说的高退缩轮次（参照 W ≥ 2.5）范围更宽）。

**建模与采样。** `ollama create` 时模板必须带**空 `<think>` 块 + temperature 0 +
中性采样**（`repeat_penalty 1.0`、`top_k 0`、`top_p 1.0`）；照抄 `server/Modelfile`
（只改 `FROM` 一行）。ollama 默认的 repeat_penalty 1.1 会把分数从 0 往上推，这有
实测：换成 1.1 后，v10 q8 在旧 B 卷（legacy 答案；llama.cpp + Metal）上的造分从
3/104（2.9%）升到 15/104（14.4%），符号翻转从 2 条变成 4 条；此前公布过的实测
方向都相同（见 [`eval/README.md`](../eval/README.md)）。生产设 `keep_alive=-1`、
重启后预热一发。

**把「服务出来的模型」和「评测用的模型」逐题对一遍**：同一个 GGUF 换个运行环境
可能打出不同的分。v10 对一台跑 ollama 的 ARM CPU 服务器做过两项核对：100 道
合成题，五维读数与 llama.cpp + Metal 完全相同的 98 道，五维都在 ±0.5 内的 99 道
（关掉服务端提示词缓存后测得；此前开着缓存——ollama 0.32.5 的默认设置——跑的一次
是 95 道和 98 道，见 [FAQ](faq.md)）；方案草案写定的服务端核对（138 道旧考卷的合成题，按
工具包规则截短；2026-10-05 才跑，在判定两天之后）复现了 Metal 上的符号翻转数与
W 达标数。此外不作跨运行环境的声明；v10 的闸门是在 Metal 上跑的。

**最后交卷**：`python eval/run_exam.py --model 你的模型`，对照 `eval/README.md`
的参考带。默认按 v10 标签判：JSON ≥ 99%、维度级 84–90%、各维 ≥ 75% 且 A ≥ 86%、
**闸门 10/10 硬性**；随包 v10 q8 为 87.3%（llama.cpp + Metal，`server/Modelfile`
模板，中性采样）。

- **三套标签**：`--labels v10`（默认；A 口径 v8、legacy B）、`--labels v9`（A
  口径 v8、crisp B）、`--labels pre_v9`（旧 A、legacy B）。部署 v9 或 v7 的，按它
  自己那一套判。A 的下限用来分辨 v10 权重与 v7 权重（后者在 v10 标签上 A 约 80）。
- **考卷天然同分布，验证的是接线，不是模型质量。** 它的标签与训练标签出自同一套
  教师提示词。它用工具包自己的提示词构造与解析器，每次请求都带固定的采样参数
  （优先于 Modelfile）——所以查不出 Modelfile 漏写 `repeat_penalty 1.0`，也查不出
  你自己服务里用了别的提示词、采样设置或解析器。分数要对着平凡基线读：在 v10
  标签上，永远输出 0.5 的部署维度级就有 77.9%，永远输出 0 的有 68.1%。
- 若你的微调实质改变了评分分布，随包考卷的标签已不公允——用你的合格教师按同样
  形制重出一份（约 200 题合成、零真实数据），并查它与训练语料的重叠（我们的 195
  题里有 6 题的消息也是某条训练行的最新消息，没有整条提示相同的）。
- 闸门区与训练无关，**任何情况下必须 10/10**：它不调模型，进程内跑工具包的
  `CrisisGate` 词表。它**不**验证你的部署是否真把每条消息先送过闸门，那是你自己
  要做的集成测试。面向消费者的心理健康部署若绕过闸门、又没有别的独立上游危机
  处理，就直接违反许可证 §3(c)。

### 八、v8 到 v10 的教训

v8、v9 是头两代改动口径本身（A、B 的含义）的模型；v9L 把 B 改了回去，v10 改的是
「一代模型怎么判」。来龙去脉见英文版 §8，这里只留结论与必须披露的事实。

1. **改口径先靠人的裁决，再落到提示词。** 创始人对 A 作了四轮裁决；带前三轮口径
   的教师提示词以他本人在真实消息上的打分为准过了资格考。第四轮的告别规则是此后
   加进一个变体提示词的，变体只在合成 A 考卷上重考过（卷里没有告别信号类题）。这些
   人工终审**不是盲打**：由
   Claude（Anthropic）先给每条预打分，创始人逐条确认或修改（第一批 40 条改 13
   条，第二批 40 条改 6 条），所以这 80 条里有 61 条，进入训练的 A 标签就等于
   Claude 的预打分。v10 沿用这 80 条（236 条训练行，其中 180 行属于那 61 条）；
   同样沿自 v9 的还有两项：20 行的 A 依 Claude 审核员对告别信号的判断改为 0，50
   行经 Claude 审核后移出语料。v10 没有新增出自 Claude 的训练标签。你们请盲打：
   人先打分，看不到任何模型分数。
2. **只重标改动的那一列，并测外溢。** 第一版 A 口径提示词让教师在 W、B 上也变
   保守，尽管 W、B 的口径没变。所以每处改动只动一列：v9L 与 v9 的语料只差 B
   一列，v10 的规则只动检测器判中的行。改完一维，要在校准集上复查其余每一维。
3. **答案卷里可能残留旧口径。** crisp B 教师最初没过预注册资格考，多半错在答案
   里的旧口径；盲审重定答案、并把创始人的裁定补进教师提示词之后才过关。答案卷
   和提示词都在失败之后动了：这是事后修订，我们照此披露。v10 的意念检测器又
   遇到一次（见§三）。口径一动，先盲审重定答案，再拿它考任何教师。
4. **闸门别只拿一个基线检查点比。** v8 挂在两道自我消融题和 E 上；不加补丁的
   消融版同样失败——这些题是这一系列模型的临界题，v7 自己四个检查点中三个也
   翻过。v8.1 把闸门改为「不低于 v7 最后三个检查点的最低值」，是看过 v8 结果
   之后改的，我们如实写明。
5. **多加教师没有帮助。** Kimi K3 与 GLM-5.2（开放权重）都没通过以现任教师为
   基准的资格考，三家取中位数也不比 DeepSeek 单独强；两位都没有给训练数据打过
   标签。v10 里它们只当出题人：Kimi K3 出了一部分新考题，GLM-5.2 写了自我消融
   训练补丁的句子，这些行的标签仍出自合格的教师。
6. **账户类错误要立刻失败。** API 余额耗尽（HTTP 402）曾被当作普通「打标失败」
   吞掉约 2,000 行；打标客户端现在遇到 401/402 立即停止。
7. **同分布考卷会放大进步。** v9 在为它造的考卷上进步很大，但那些考卷与它自己的
   训练补丁同分布。v10 也一样：新考卷与补丁都是合成的，出自同一类生成器（考题
   由两个开放权重模型 DeepSeek 与 Kimi K3 出，自我消融训练补丁由第三个 GLM-5.2
   出）。G2b、G2c 对这份补丁的同分布还要更进一层：补丁是在参照检查点于新 B 卷上
   打过分之后才加的，而这张卷仍用来给 v10 设闸——尽管我们的方案草案写过：若因为
   某块考题的逐题结果改了训练数据，这块考题就该退出设闸、重新出题。换第三个出题
   模型、新写提示词、按相似度过滤，只能减少重叠，不能消除。过了这些考卷，只说明
   「在已知范围内没有退步」，不说明能推广。A 口径 v8 之下，至今没有真实对话上的
   测量：参照标签按旧 A 口径打，v10 的 A 与它的一致（453 题中 327 题在 ±0.5 内；
   v7 为 383 题）是有意偏低的。B 则重新有了一项：336/453，与 v7 同数（随包 q8，
   llama.cpp + Metal）。对同一张考卷反复尝试也是一种缓慢的选点——这条线上，真实
   终评已经判过八代模型（见§三）。
8. **推翻闸门，就要公开。我们已经连续两个发布版这样做了。** v9 没过自己预注册的
   五道闸门中的两道：v9 的闸门 4 差一题；v9 的闸门 5（W 安全卷）差得明显——W 达到
   下限的题只有 78.9%，要求 ≥95%（受检 bf16 模型，经 MLX）。按预注册规则 v9 是
   拒收；创始人仍决定发布并明确留档，裁定危机处理是上游架构的职责、不是这个模型
   的职责。v10 是第二次（见§六）。两次都把失败写在讲验收的地方，门槛没有事后
   重划。你若推翻自己的闸门，请同样处理。

   v10 的注册里，查 W 下限的是 G4a–G4d 这几项检查。新旧两张 W 安全卷的 189 道
   「想死但求助」题里，W 低于 2.5 的：v10 为 21 题，v9 为 102 题，v7 为 111 题
   （G4d，通过线 ≤ 94）；平均原始压力变化依次是 +2.37、−0.24、−0.29（G8，通过线
   ≥ 0；随包 q8，llama.cpp + Metal）。这些是合成的同分布题，是对口径的检查，不是
   危机检测。另有一点，说的是闸门、不是分数：随包的 `CrisisGate` 只是一份简短的
   关键词表，不是完整筛查；这 189 题按出题设计都含意念，它命中 107 题。请按你的人群
   扩充词表，在闸门旁边（而不是替代它）加第二层筛查，并在你自己的人群上实测两者。
9. **通过线落在训练波动之内，量到的就是波动。** v8、v8.1、v9、v9L 接连没过各自的
   预注册闸门，多数只差几道题。我们把手头留着的 14 个 legacy B 检查点拿 v9L 的
   六道闸门量了一遍：没有一个能六道全过，对训练波动敏感的四道也只有 2 个能过。
   写通过线之前，先量一量你自己存下的检查点在这条线两侧散得多开。
10. **几十道题上的零容忍闸门会拒掉好模型。** 小题池上的零容忍线，一道题就定了
    结果。G5a 就是这样一条线，也是 v10 没过的那一项（见§六）；旧 B 卷上的零翻转线
    是另一条：手头 15 个后期检查点
    （存档的 bf16 预测，MLX）里，在旧 B 卷上零翻转的有 4 个。罕见错误要放到几百道题上数，按比例设上限，上限事先写定。
    代价是：按我们的设计估算，这类上限对「罕见错误只翻一倍」至多拦住一半，对任何
    一道具体的题也什么都不保证（见第 15 条）。
11. **候选按规则定，不靠挑。** 事后挑，线就落在一次好手气上；按验证集挑，v8.1
    就是这样输的；定死最后一个检查点，留下了运气。按规则取平均并先彩排，能削掉
    一部分运气，代价是拿不到最好那个检查点的最好成绩。它不是万灵药：平均落在原料
    之间，不会更高。
12. **第二个种子是报告，不是备选候选。** v10 的第二个种子（同一份配置、
    `seed: 2`；判定写出之后才打分；只有第一轮训不完时才顶上）18 项全过，但没有
    采用：换上它，就是按考卷成绩挑选。它显示的是同一份配置训两次相差多少（q8：
    G1 为 149 与 152，共 154；G6b 为 336 与 346，共 453；G7 每轮 −0.72 与
    −0.59）——两代模型之间若只差这么多，不能当作一代比另一代好的证据。
13. **改口径，必须连同消费它的公式一起改。** 这是§一那条更正的规则版。crisp
    口径本身我们不否定：它对「划界」的定义更干净，教师也更稳；v9 仍可下载，供想
    单独用这把尺子的人取用。错的是没有给公式重新定心，就把它放进了按 legacy
    口径校准的公式。消费一个维度的东西（公式、阈值、其他打分器、图表）要在同一次
    发布里一起改；给整段会话回放的轨迹设闸（如 v10 的 G7）；没找到可行的重调
    办法，就别告诉用户「重调」。
14. **签字之前，把每道闸门对照负责人已有的裁决查一遍。** G5a 把一项危机处理的
    替代指标设成了硬闸，而创始人此前已两次裁定（v7 选点时、v9 发布前后）：
    危机由上游处理，不归这个模型。结局是一次看到结果之后的豁免——发现「这道闸门
    其实不算数」最糟的时刻；我们下一份注册不再拿 G5a 设闸。签字之前去问
    那个有权豁免的人：如果只有这一条没过，我们真的拒收吗？
15. **比例上限保不住任何一句具体的话。** v10 通过 G2a 与 G2b 时，算在内的是§六
    那句话一个加长版本上的翻转（旧 B 卷那道题句末多一句「…，你安排吧。」；短句本身
    不是考题），这两道闸门本来就允许：在 438 题的题池上，v10 把自我消融读成边界的
    次数远少于 v7（4 条对 47 条，均为 q8），却把 v7 发布检查点当初因之入选的那句话读错了。
    所以这句话不能当作「v10 把自我消融打成 B 0」的证据。对你重要的句子要列成
    具名清单，在比例旁边逐句报告读数，并在训练之前决定其中有没有硬线。

### 九、许可证义务

两个许可证别搞混：**工具包代码 Apache-2.0**（你的集成代码不受限）；**模型
权重 HAMO-RAIL-S 1.0**，你微调出的权重是**衍生权重**：§1 允许自由使用、
修改、再分发（含商用、免版税）；§2 要求再分发时保留 LICENSE 文件与源仓库
指引（基座 Qwen3-0.6B 的 Apache-2.0 声明继续有效）；§3 的四条使用限制
**必须实质性地随权重传递给任何接收方**——不得独立做临床判定（须持牌专业人员
掌握决定权）、不得把分数作为对可识别个人重大决定的唯一或主要依据（雇佣、
保险、信贷等）或用于隐蔽心理监控、面向消费者的心理健康部署必须保留独立的
上游危机处理与 AI 披露、不得从分数重识别个人或把分数与身份做超出合法授权
用途的关联；§5：实质违反 §3 即自动终止授权。

### 附：十二代小史

逐代表格与各代数字的口径见英文版附录，这里只列梗概。v2 首蒸 → v3.x 配平 → v4
审计驱动重修数据 → **v5 拒收**（W 上限准入闸门；真实数据的高退缩轮次（参照 W ≥ 2.5）上，W 被打到接近
0 的次数明显多于 v4）→ **v6 拒收**（3 条内容高退缩、参照标签却给 W 0 的行入训，W 以同样的方式
退步）→ v6.1 发布（440 条授权真实
数据，改用教师标签）→ v7 发布（教师以 temperature 0 重标全量语料 + 边界区分补丁）→ **v8
拒收**（A 口径 v8；四道闸门挂两道）→ **v8.1 拒收**（预注册选点规则选中的检查点
挂了两道闸门；四道全过的另一个检查点未改选）→ **v9 由创始人决定发布，已被 v10
取代**（A 口径 v8 + crisp B + W 安全修复；五道闸门过三道，挂 v9 的闸门 4（H 差
一题）与 v9 的闸门 5 W 安全卷（78.9%，要求 ≥95%；受检 bf16 模型，经 MLX）；它的
crisp B 配不上 B 为负权重的公式，见§一）→ **v9L 拒收**（v9 的语料只把 B 一列
改回 legacy 标签；六道闸门过四道，挂在旧 B 卷成对方向 56/60（要求 58）与真实终评
H 422/453（下限 425）上（受检 bf16 模型，经 MLX）——教训：通过线落在训练波动
之内）→ **v10 由创始人决定发布**（v9L 的语料 + 明确意念规则（检测器加确定性
代码，改动 179 条训练行的标签）+ 两份最小对照补丁各 150 对，共 20,787 条训练行；
候选按规则定为种子 1 第 4,800 / 6,000 / 7,200 步融合权重的平均，判的是 q8。
**按签字的预注册，判定是拒收**：18 项过了 17 项；没过的那一项 G5a 当初是作为危机
处理的替代指标设的，创始人看到结果后裁定危机处理不在本模型里判定。**由创始人决定
发布**，是看到结果之后对这一道闸门的豁免（见§六）。真实终评（受检 q8，llama.cpp +
Metal）：W/E/H 87.4/85.2/93.2%、B 74.2%、决策级 96.0%）。

v9、v10 在 A 上的进步，v9 在 crisp B 上的进步，v10 在自我消融与「想死但求助」上
的进步，都是在同分布合成考卷上测的（见§八第 7 条）。值得复制的不是任何一个
数字，而是流程本身：每代都在不入训的真实留出题上受检，自 v6 起验收标准在该代
出分前写死。五次拒收不是事故率——是流程在起作用的证据。最近两个发布版是公开推翻
验收闸门的两次（v4、v6.1 与 v7 的选点属于裁量，见§六），我们不粉饰：v9 没过五道闸门中的两道，
其中一道在 W 安全卷上；v10 没过 18 项检查中的一项 G5a（当初是作为危机处理的替代
指标设的），按签字的预注册判定是「拒收」。两者都由创始人决定发布。能被豁免的闸门，强度只取决于豁免之后的披露——所以每一项失败
都写在讲验收的地方，门槛没有事后改动。你若推翻自己的闸门，或者像我们对「重调
阈值」那样发现自己给过的建议是错的，也请同样公开。
