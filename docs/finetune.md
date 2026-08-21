# Fine-tuning hamo-score-0.6b for your own population

**EN** | [中文](#中文)

This guide is for engineers at professional mental-wellness institutions who
downloaded [HamoAI/hamo-score-0.6b](https://huggingface.co/HamoAI/hamo-score-0.6b)
and want to adapt it — to a new language, a new population, a different
register — using their own **consented** data.

It is the distilled playbook of five model generations, including two we
**rejected** after training completed (v5 and v6, both for crisis-recall
regressions). The rejections taught us more than the successes, so they are in
here as rules. Everything below was learned on one MacBook and about US$7 of
API spend — this is not a cluster-scale process.

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

Fine-tune when the **linguistic footprint** your population produces is
materially different from the training distribution: a language the model is
weak in (it is Chinese-primary: zh 60% / mixed 22% / en 18%), a distinct
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
their explicit consent, upsampled ×3 (~8% of corpus). External client/user
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
set along with the real data. Result: crisis W-misses on the final exam jumped
from 5 to 9, and the entire generation was rejected. The screening rule:

1. Run every candidate real row's **text** through your crisis word list
   (the gate's own list is a good start).
2. Every row that hits the list gets human review.
3. Any row whose label contradicts its text (crisis text, benign label) is
   removed or relabeled before training. No exceptions for "it's only 3 rows"
   — 3 rows out of ~16,000 was enough to nearly double our miss count (5 → 9).

**R3. Never train the model to detect crisis.** The deterministic gate owns
crisis detection. High W-recall on crisis-adjacent text is defense-in-depth
and we track it (see §6), but it is never the defense.

**R4. Hygiene.** De-identify everything. Real data never goes into git
(`.gitignore` it before the first export exists). Keep a one-page data map:
what you collected, whose consent, which file, which split.

---

## 3. Build your exam before your curriculum

The first artifact of the project is not training data. It is a held-out exam
of **real** turns from your population that will **never be trained on** — and
a qualified teacher. Order matters: if the exam comes second, you will
unconsciously build it out of what your model is good at.

**Split three ways.** Ours: 1,198 real de-identified turns → a
teacher-qualification / calibration set (440) and a held-out final. The final
is touched **once** per generation, for the shipping decision — never for
checkpoint selection, never for prompt iteration. If your calibration set
later enters training (ours did, in v6.1, under R1 consent), carve a fresh
selection split out of held-out territory first; a set you train on can no
longer select checkpoints.

**Record decision context with each row.** Store, alongside message, context
and gold scores, the prior stress level (and any per-user modifier metadata)
at the moment the message arrived. You need it to compute decision-level
agreement (§6) — without it you can only measure dimensions, and dimensions
are the wrong headline number.

**Qualify your teacher before it labels anything.** Whatever model you use to
label training data (we use `deepseek-chat` with the production rubric at
temperature 0), make it sit your real exam first. Our bar on 440 real turns:
dimension-level ±0.5 agreement ~89% (88.7%), decision-level 97.5%. Look at
per-dimension numbers, not just the mean: our teacher first scored 72% on the
Boundary dimension — a fixable operational-definition mismatch, closed to 78%
(90% at ±1.0) with calibration notes in the rubric prompt. A broken dimension
hides comfortably inside a good average.

**Measure your incumbent's self-consistency.** We scored the same messages
twice with the reference scorer in two live environments: it agreed with
itself only 94–98% at dimension level. That is the practical ceiling. Knowing
it stops you from burning weeks chasing 99% against a gold standard that is
itself 95% reproducible.

**If you build an LLM judge** for anything that touches humans: it must reach
kappa ≥ 0.6 agreement with a licensed professional before you trust it.

---

## 4. Training data format

### The exact shape

Training rows are chat-format JSONL, one per line, as consumed by `mlx-lm`:

```json
{"messages": [
  {"role": "user", "content": "给来访者最新消息打分（AWEHB，0.0-3.0）。\n此前对话:\nassistant: 这周过得怎么样？\n最新消息: 今天试着出门散了个步"},
  {"role": "assistant", "content": "{\"A\": 1.5, \"W\": 0.0, \"E\": 0.0, \"H\": 0.0, \"B\": 1.0}"}
]}
```

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
> "worry-shaped text → suppress W". Crisis W-misses went from 5 to 10–18
> (2–3×) across checkpoints, and the generation was rejected. An admission
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
real turns, upsampled ×3 to ~8% of the corpus, on top of the synthetic
curriculum — and moved dimension-level agreement +1.6pt (84.0% → 85.6%), with
the conversational-action dimension jumping 81% → 85%, an all-time high for
that dimension. Screen them per R2, upsample them so
the model actually sees them, and keep them out of every eval split.

---

## 5. The LoRA recipe

This is the actual config that trained the released v6.1 weights (`mlx-lm`,
one M1 Pro MacBook, 16GB). Paths adapted, numbers untouched:

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
  length, halve the batch. The healthy config peaks at ~4.7GB and ends around
  loss 0.06.
- **`max_seq_length: 1024`, not 512.** Tempting to shorten for speed, but
  512 truncates long messages with 5-turn contexts — exactly the samples the
  style quotas fought to include.

`save_every: 1200` yields six checkpoints — that is your selection pool for
§6, so don't save less often to save disk.

Rough wall-clock: a full 7,200-iteration run over a ~16k-row corpus takes on
the order of a few hours on an M1 Pro — start it after lunch, select
checkpoints before dinner. The valid split exists to watch for divergence
during training, **not** to pick checkpoints (next section explains why).

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
   this column is blind exactly where you can least afford it. We now refuse
   any checkpoint above the incumbent's miss count *at selection time*, not
   just at final acceptance.
4. **Distinct output vectors** — the collapse detector. One early generation
   scored decently while emitting only **59** distinct five-score
   combinations against 233 in real data: it had quietly become a 14-cell
   grid classifier with cell-center scores. Watch this number, plus mid-band
   usage (are 1.0s and 1.5s ever emitted?). A scorer that cannot say "1.0"
   is not measuring.

**The acceptance hard gate.** The winning checkpoint sits the final exam —
the split touched once — and ships only if:

> decision-level ≥ your incumbent, **AND** crisis-miss ≤ your incumbent.

Either fails → the generation is rejected and the incumbent stays. No
averaging the two, no "but dimensions improved". We rejected two trained,
plausible-looking generations on this gate (v5: misses 2–3× worse; v6:
misses 5 → 9 from three poisoned rows). Both rejections cost a training run;
shipping either would have cost trust in the instrument.

If you run against live traffic, do it in **shadow** first: new model scores
in parallel, incumbent still decides, every pair logged. Preregister the
switch criteria before you look at the data (ours: ≥1 week of shadow,
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

Stay at **q8_0**: it lands inside the reference band in our tests, and on the
ARM CPU servers we deploy to it was not even slower than q4 (q8 dot-product
kernels are good on ARM). Aggressive quantization (q4 and below) is where
JSON validity and agreement start to crumble.

Create the ollama model with the **empty-think template and temperature 0** —
this is the single most common wiring mistake. Use
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
```

```bash
ollama create my-score-model -f Modelfile
```

In production, set `keep_alive=-1` and send one warm-up request after every
restart (the toolkit's `OllamaClient` already sends `keep_alive=-1` per
request).

**Then take the exam.** The toolkit ships a deployment self-check — 195
synthetic teacher-labeled questions plus 10 handwritten crisis-gate cases:

```bash
python eval/run_exam.py --model my-score-model
```

Compare against the reference band in [`eval/README.md`](../eval/README.md)
(JSON validity ≥99%, dimension-level 81–86%, gate **10/10 — hard
requirement**). Two notes for fine-tuners:

- If your fine-tune deliberately changed the score distribution — new rubric,
  materially different population — the shipped exam's labels reflect *our*
  rubric and may no longer be a fair test. Regenerate your own exam with your
  qualified teacher: same shape (~200 synthetic questions, a fresh random
  seed disjoint from all your training corpora, zero real data), same format
  (`message` / `context` / `labels` rows).
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

## 8. What you owe under the license

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

## Appendix: six generations at a glance

| Generation | What changed | Outcome |
|---|---|---|
| v2 | first distillation, 7.5k synthetic | shipped — dim 81%, decision 95.4% |
| v3.x | rebalance + defect repair | shipped — decision 96.8% |
| v4 | 8-agent data audit: prompt masking, style quotas, mid-band cells, 15k corpus | shipped — dim 84.0% (+3.1), crisis misses 11 → 5, output vectors 59 → 87 |
| v5 | synthetic patch cells with a W-cap admission gate | **rejected** — crisis misses 2–3× worse; taught us the distress-adjacent W-cap rule |
| v6 | +440 real turns, incumbent's labels unscreened | **rejected** — 3 crisis-artifact rows in training, misses 5 → 9; taught us R2 |
| v6.1 (released) | same 440 real turns, teacher labels, crisis-artifact screening | shipped — dim 85.6%, decision 96.2%, crisis misses 4 |

Those six adjudicated generations sit on top of about ten actual training
runs — pilots, restarts, and a same-size rerun or two that never earned a row
here, plus one run on a student three times larger that gained roughly a point
and was dropped. Budget for that ratio: you will train more often than you
will ship.

The pattern worth copying is not any single number. It is that every
generation faced the same exam, the exam never entered training, and the
gate for shipping was written down before the results existed. Two rejections
is not a failure statistic — it is the evidence the process works.

---

# 中文

## 给专业机构的微调指南（精编）

你从 HuggingFace 下载了
[hamo-score-0.6b](https://huggingface.co/HamoAI/hamo-score-0.6b)，想用**经
授权的**自有数据把它适配到你的人群、语域或语言。本文是我们六代模型（含两代
拒收）蒸馏出来的操作手册。先立框架：它是**测量仪器**——不是聊天机器人、不是
诊断工具、不是治疗师，也**不是危机检测器**。危机处理由模型上游的确定性闸门
（`CrisisGate`）负责——这是许可证 HAMO-RAIL-S §3(c) 对面向消费者的心理健康
部署的硬性要求，也是本项目架构对一切部署的要求。微调不改变、也不允许改变
这一点。

### 一、先想清楚要不要微调

多数需求不需要动权重：人群特有的危机说法 → `CrisisGate(extra_keywords=[...])`
一行扩词表；下游敏感度 → 改 `stress.py` 里的平滑与分桶阈值（Apache-2.0 参考
代码，本来就是给你改的）；个别句子评分不服 → 记住分数要经 `0.8·历史 + 0.2·本句`
平滑，单句噪声会被吸收，成规律的分歧走仓库的「评分分歧」issue 模板。真正该
微调的场景：新语言（模型以中文为主）、明显不同的语域人群、你们临床团队正式
定义的量表变体。**永远不要**为了"让模型会认危机"而微调——闸门管危机，模型管
其余，倒过来就是在诱惑别人拆闸门。

### 二、数据红线（先于一切采集）

- **R1 知情同意**：我们的训练语料全部为合成数据，唯一例外是 v6.1 起加入的
  440 条真实对话轮次——来自三位公司内部员工（创始人与两位咨询师）、经本人明示
  授权、×3 上采样约占语料 8%；**外部来访者对话从不入训，构造上保证**。照此
  执行：真实来访数据可做考卷（当地法规与治理允许时），入训必须有书面、可撤回
  的本人授权。「已脱敏」不等于授权。
- **R2 危机工件筛查**：v6 拒收的教训。危机内容在生产里被上游短路，会留下
  「危机原文 + 近零分数」的毒标签。3 条这样的行随真实数据入训，终评危机漏检
  从 5 涨到 9，整代拒收。规则：真实行入训前，原文过一遍危机词表；命中必经
  人工复核；文标矛盾（危机文本配良性标签）的行删除或重标。3/16000 就足以让
  漏检近乎翻倍（5→9）——没有「才几条」的豁免。
- **R3 永不训练模型识别危机**：确定性闸门独占此职责，模型的危机语召回只是
  纵深防御。
- **R4 卫生**：全量脱敏；真实数据不进 git；保留一页式数据台账。

### 三、先出考卷，再编教材

项目第一件产物是**真实数据终评考卷**（永不入训），第二件是**过了资格考的
教师**。顺序颠倒，你会不自觉地照着模型的长处出题。三切分：教师资格/校准集、
选点集、终局集（每代只碰一次）。校准集若日后经授权入训（我们 v6.1 就这么做
了），须先从留出区另切选点集。每行连同消息、上下文、金标一起，**记录当时的
压力值等决策上下文**——否则算不了决策级。教师资格考：给训练数据打标的模型
（我们用 deepseek-chat + 生产量表 + temperature 0）先考你的真题，我们的线：
维度级 ±0.5 约 89%、决策级 97.5%；要逐维看——我们教师 B 维初考 72%，靠量表
校准注记修到 78%，平均数会把坏维度藏起来。再量一下现任评分器的自洽：同批
消息打两遍只有 94–98% 一致，这就是天花板。若另建 LLM judge 用于任何触人
环节：与持牌专业人员的 kappa ≥ 0.6 才可用。

### 四、训练数据格式

mlx-lm 聊天格式 JSONL，user 内容**必须**用 `hamo_score.build_prompt` 构造
（训练与推理提示词逐字节一致，截短护栏一并生效；工具包安装：
`pip install hamo-score`）；assistant 内容是单个 JSON
对象：五键、一位小数、0.5 网格，无任何多余文字。

```json
{"messages": [
  {"role": "user", "content": "给来访者最新消息打分（AWEHB，0.0-3.0）。\n此前对话:\nassistant: 这周过得怎么样？\n最新消息: 今天试着出门散了个步"},
  {"role": "assistant", "content": "{\"A\": 1.5, \"W\": 0.0, \"E\": 0.0, \"H\": 0.0, \"B\": 1.0}"}
]}
```

合成教材按场景格子组织，配**准入闸门**（教师标签落在格子设计带内才收，否则
弃样）。**v5 铁律：凡文本与痛苦相邻的格子，准入禁设 W 上限**——v5 的「有界
担忧链」格子设了 W≤1.0 准入，等于教模型「担忧文本→压 W」，危机漏检翻 2–3
倍，整代拒收。风格配额要对齐真实分布：我们的真实流量 35.5% 是 15 字以内短
消息、62% 带多轮上下文，合成器天然写不出这些——按真实占比强制配额，再加
生成器口头禅黑名单、中间档（0.5/1.0/1.5）标签强制出现、纯原型样本 <20% 封顶。
真实授权数据少量即有效：440 条 ×3 上采样让维度级 +1.6pt（84.0→85.6），A 维
81→85 创历代新高。

### 五、LoRA 配方（MLX，一台 MacBook）

发布版 v6.1 的真实配置（路径改成你的，数字别动）：base
`mlx-community/Qwen3-0.6B-bf16`，LoRA rank 8 / scale 20 / 16 层，
`batch_size: 4`，`iters: 7200`，LR `7e-5` cosine 退火至 `7e-6`（warmup 100），
**`mask_prompt: true`**，`grad_checkpoint: true`，`max_seq_length: 1024`，
`save_every: 1200`。运行：`python -m mlx_lm lora -c finetune.yaml`。三个数字
是伤疤：① `mask_prompt` 不开，72% 梯度耗在给来访者消息做语言建模上（我们
瞎跑了六轮才发现），单开此项决策级 +1.4pp；② 16GB 机器上 seq 1024 配
batch 8 会顶到 16.6GB 并**无声数值爆炸**（loss 0.118→10.8），序列翻倍、
batch 减半，健康跑法峰值 4.7GB；③ seq 别降到 512——会截断长上下文样本，
正是配额辛苦补进来的那些。全程约数小时量级，午后开跑、晚饭前选点。

### 六、选点与验收

**永不用合成 valid loss 选点**——我们的合成 valid 比真实分布重尾 3 倍，在
它上面早停等于为假分布选模型。选点在**真实校准集**上、按**决策级**（分数过
确定性压力折算后的状态桶一致率，即下游真正消费的数字）。选点表四列：维度级
±0.5（诊断用）、决策级（选点用，<2pt 视为噪声）、**危机漏检数**（金标 W≥2.5
而预测 <0.5——v5 的选点冠军漏检 18 条，没有这一列的选点在最不能瞎的地方是
瞎的）、**输出向量种类数**（塌缩探测器：某早期学生只会输出 59 种五维组合，
真实数据有 233 种——它退化成了格子分类器）。终局硬闸（预先写死）：**决策级
≥ 现任 且 危机漏检 ≤ 现任**，任一不过整代拒收、现任留任——我们照此拒了
v5 和 v6 两代。接真实流量先跑**影子模式**，切换标准预注册（我们的：影子
≥1 周、回退率 <2%、决策级 ≥96%、平滑压力轨迹偏差 ≤0.05、危机零漏检）。

### 七、上线

`python -m mlx_lm fuse` 融合 → llama.cpp `convert_hf_to_gguf.py --outtype q8_0`
转 GGUF（就用 q8：参考带内，且 ARM CPU 上不比 q4 慢；q4 以下开始碎）→
`ollama create`，模板必须带**空 `<think>` 块 + temperature 0**（照抄
`server/Modelfile`，这是最常见的接线错误）→ 生产设 `keep_alive=-1`、重启后
预热一发。最后交卷：`python eval/run_exam.py --model 你的模型`，对照
`eval/README.md` 参考带（JSON ≥99%、维度级 81–86%、**闸门 10/10 硬性**）。
若你的微调实质改变了评分分布，随包考卷的标签已不公允——用你的合格教师按同样
形制重出一份（约 200 题合成、全新种子与训练语料不相交、零真实数据）。闸门区
与训练无关，**任何情况下必须 10/10**：它不调模型，进程内跑工具包的
`CrisisGate` 词表——7 条危机句式必中、3 条黑色幽默不得误触。注意它**不**验证
你的部署是否真把每条消息先送过闸门，那是你自己要做的集成测试。闸门区不过
说明词表被改动了，修好再上线；绕过闸门的面向消费者心理健康部署则直接违反
许可证 §3(c)。

### 八、许可证义务

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

### 附：六代小史

v2 首蒸（维度 81）→ v3.x 配平（决策 96.8）→ v4 审计驱动重修数据（维度
84.0，漏检 11→5）→ **v5 拒收**（W 上限准入闸门，漏检 2–3×）→ **v6 拒收**
（3 条危机工件入训，漏检 5→9）→ **v6.1 发布**（440 条授权真实数据 + 工件
筛查，维度 85.6、漏检 4）。这六代定谳之下是约十次实际训练——试跑、重启、
没能挣到一行表格的重训，外加一次三倍大学生的实验（只涨约一分，弃）。按这个
比例做预算：训练的次数一定多于发布的次数。值得复制的不是任何一个数字，而是流程本身：每代
考同一张考卷，考卷永不入训，验收标准在出分前写死。两次拒收不是事故率——
是流程在起作用的证据。
