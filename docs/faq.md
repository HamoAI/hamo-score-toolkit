# FAQ

**EN** | [中文](#中文)

For toolkit 0.4.1, which serves model **v10h**. Unless stated otherwise, numbers
are for the shipped q8 GGUF through llama.cpp with Metal on an Apple M1 Pro, at
temperature 0 with `repeat_penalty 1.0`, `top_k 0`, `top_p 1.0`; v7, v9 and v10
numbers are their shipped q8 GGUFs run the same way on the same exam files.
"bf16" is the safetensors through MLX. Acceptance-exam numbers use each item's
full context, not `build_prompt`'s trimming; the self-check exam and the ARM
serving check use the trimming. "The real final exam" is 453 real turns from
pseudonymised conversations of three consenting internal staff members, graded
against reference labels (from the production rubric's LLM scorer, with human
corrections on 5 of the 453 turns; these are not counselor scores) and not
distributed. The other exams are synthetic.

**Why does the template contain an empty `<think>` block?**
The model was trained on chat text whose assistant turn is an empty think block
followed by the JSON. The `TEMPLATE` in [`server/Modelfile`](../server/Modelfile)
pre-fills that block, and the published q8 reference used it through llama.cpp.
Copy it unchanged.

By default ollama 0.32.5, 0.40.12 and 0.40.13 store this template but serve the
GGUF's own chat template instead (`ollama show <tag> --template` prints it; on
0.40.13 `/api/show` reports `template_source: gguf_chat_template`). Nothing is
pre-filled then: the model writes the empty block itself, then the JSON, and the
response text starts with `<think>`. `parse_scores()` handles that; a bare
`json.loads` on the response fails.

Measured on 2026-10-31 and 11-01 on one Apple-silicon Mac (Docker under Colima,
arm64 CPU, ollama 0.40.13): on the 195 exam questions and on 1,415 other distinct
synthetic prompts no answer had think text and none was cut off at
`num_predict 80`. `"think": false` in the request, or `OLLAMA_GO_TEMPLATE=1` on
the server, pre-fills the block, and the response starts with `{`. On the 195
questions, with the model warmed and the prompt cache off, the two paths agreed
exactly on 189 and within ±0.5 on all 195 (86.7% without the pre-filled block,
86.4% with it). With `OLLAMA_GO_TEMPLATE=1` and a `TEMPLATE` that has no think
block, the model again wrote the block itself: JSON 100%, 86.7%. The toolkit's
client does not send `think`.

**Why temperature 0 — and why must I also neutralise `repeat_penalty`?**
Scoring is measurement; sampling noise is measurement error. And
**`repeat_penalty 1.1`**, ollama's default through 0.32.9 (1.0 from 0.32.10),
does harm, because this model's output —
`{"A": 0.0, "W": 0.0, "E": 0.0, "H": 0.0, "B": 0.0}` — is repetitive by
design: penalising repeated tokens pushes scores away from 0, i.e. fabricates
signal, with no error. Measured on v10 q8 with the old B exam (300 questions,
legacy key), changing only 1.0 → 1.1 takes fabrication (no-boundary and low-arm
items scored B ≥ 1.0) from 3/104 (2.9%) to 15/104 (14.4%) and B sign flips
(gold B 0 scored ≥ 2.0) from 2 to 4 of 93. v6.1, v7 and v9 were pushed in the
same direction when measured (their figures, as published at the time, are in
[eval/README.md](../eval/README.md)).

Always set `repeat_penalty 1.0`, `top_k 0`, `top_p 1.0`. `server/Modelfile`
and `server/docker-compose.yml` set them, and the toolkit's `OllamaClient`
sends them with every request (request options override the Modelfile); a
client you write yourself is covered only by the Modelfile unless it sends
them too, and by nothing if your Modelfile omits them. The self-check exam
goes through the toolkit's client, so it cannot catch a Modelfile that omits
them: check with `ollama show <tag> --parameters`.

**The first request after startup is slow / times out.**
Cold start. Send one warm-up request after every model (re)start and keep
`keep_alive=-1` (the toolkit's client sets it per request; the client and
the reference server's `POST /score` default to an 8-second hard timeout).
Send the warm-up with a long timeout, not through an 8-second client: ollama
aborts a load when the client disconnects, so a load slower than the timeout
never finishes. On one Apple-silicon Mac (Docker under Colima, arm64 CPU, ollama
0.40.13), this was reproduced only under an artificial CPU cap or a shortened
timeout. If later requests are still slow, the usual cost is prompt prefill
on a slow CPU — check the trimming guards.

In the reference server (`server/docker-compose.yml`), the `setup` service warms
the model during `docker compose up`, before `api` starts. After a crash or a
reboot, `ollama` and `api` restart by themselves. `setup` does not run then, so
a restarted `ollama` has no model loaded. `api`'s health check loads it, or the
first request does if it loads within `SCORE_TIMEOUT` (8 s by default). The
check calls `/healthz` every 60 s. `/healthz` scores a short probe with its
own timeout (`HEALTHZ_TIMEOUT`, by default 60 s, or `SCORE_TIMEOUT` if that is
longer), so it can finish a load slower than `SCORE_TIMEOUT`. A probe that took
longer than `SCORE_TIMEOUT` returns 503 even if it finished loading the model;
the next one passes if the model is fast enough.

Measured on 2026-11-01 on one Apple-silicon Mac (Docker under Colima, arm64 CPU,
ollama 0.40.13): after a VM restart with no request at all, the health check
loaded the model about 61 s after `api` started. With `SCORE_TIMEOUT` set to
0.7 s, shorter than the load (about 1.3 s there), 0 of 48 `POST /score` calls
succeeded in 130 s without the health check: each one aborted the load. With it,
calls failed until the first probe finished the load, then succeeded. Slow
hardware itself was not tested.

If you limit the ollama container with `cpuset`, set `LLAMA_ARG_THREADS` to the
number of CPUs. On one Apple-silicon Mac (Docker under Colima, arm64 CPU, ollama
0.40.13), limited to 2 of the VM's 4 CPUs and 1500 MiB, llama-server otherwise
kept 4 threads: warm-up took 125 s against about 3 s, and `/score` was still
returning 500 when the run was stopped more than 400 s later. With
`LLAMA_ARG_THREADS=2` the stack came up in 11 s.

**The ollama process keeps growing in memory on a small machine.**
On ollama 0.32.5 and 0.40.13 the bundled llama-server keeps a host-memory
prompt cache, on by default (limit 8 GiB), that grows with every distinct
prompt: on 0.32.5 on a 4 GB machine we saw the process grow from 1.3 GB to
3.3 GB over 100 distinct prompts.
Setting `LLAMA_ARG_CACHE_RAM=0` in the ollama service environment stopped the
growth (1,277 → 1,294 MB over the same 100 prompts) with median latency
unchanged. The reference `server/docker-compose.yml` on `main` has set it since
2026-10-31, and the file at the `v0.4.1` tag sets it too; the file at the
`v0.4.0` tag does not.

Measured on 2026-10-31 on one Apple-silicon Mac (Docker under Colima, arm64 CPU,
ollama 0.40.13), with short one-line synthetic messages through `POST /score`: 100 distinct prompts grew the process by 975 MB with the
cache on and by 2.3 MB with it off, with the median request time unchanged.
Growth depends on prompt length. Under a 4 GiB memory limit, 2 CPUs and `LLAMA_ARG_THREADS=2`, with the cache on, a
serial pass through `POST /score` had the runner killed for memory at message
182, and a separate exam pass crashed with HTTP 500. With the same limits and the
cache off, 195 of 195 were served, nothing was killed, the exam read 86.5%, and
the ollama container peaked at about 1.3 GiB. These are container limits, not
real small machines.

**My output isn't valid JSON.**
`parse_scores()` returns `None`; treat it as "skip this message" (the smoothed
state stays unchanged) — never crash, never guess. Above ~1% of messages,
suspect your wiring before the model (v10h q8: 0 unparseable outputs across the
six acceptance exams). Check temperature 0, `num_predict ≥ 80` and that the
prompt comes from `build_prompt()`: on ollama 0.40.13 `num_predict 20` and one
hand-written prompt each gave JSON 0%. On ollama 0.32.5, 0.40.12 and 0.40.13 a
response that starts with an empty think block is normal: `parse_scores()`
handles it, a bare `json.loads` does not. Then run `eval/run_exam.py`; to run
it against the Docker server, first publish the ollama port as
[eval/README.md](../eval/README.md) describes.

**Which languages does it support?**
Chinese-primary. By the latest message of each of the 20,787 v10 training
rows (v10h's 20,001 rows are those minus the rows it held out or removed):
76.0% Chinese, 13.1% English, 10.9% mixed Chinese–English. We publish no
per-language accuracy for v10 or v10h; other languages are untested — that is
what [fine-tuning](finetune.md) is for.

**What about ultra-short messages like "嗯" or "ok"?**
Score them, with context attached. An all-zero result is a designed no-op.
Short messages are common in real conversations; skipping them creates a blind
spot exactly where distressed people go terse.

**Can I send more conversation context for better accuracy?**
Not through the toolkit, which trims it; whether more context helps is not
measured on v10 or v10h, and context length can move a score. `build_prompt`
keeps the last 3 turns × 200 characters and caps the message at 500: a latency
guard for CPU-only servers, not what the model saw in training (36.6% of v10's
training rows carry more than 3 context turns) nor what the acceptance exams
ran on (full context). The guard's 98.1% score self-agreement (±0.5) dates from
August 2026 and was not re-measured on v10 or v10h.

**Do I need a GPU?**
No. Measured on the v10h q8 on an ARM CPU server running ollama: P50 2.09 s, P95
2.57 s, max 2.87 s per message (138 synthetic items, toolkit trimming, model
loaded; prompts far shorter than the trimming allows, so not a worst case).
v10 on the same check: P50 2.13 s, P95 2.53 s, max 2.91 s.

Where scores gate behaviour, use the shipped Q8_0, the one v10h quantization we
have measured; compare your own against it with `eval/compare_quants.py`
first. The community GGUF quantizations on Hugging Face were made from the v4
weights, five releases behind v10h, and we have not validated them. Details:
[eval/README.md](../eval/README.md).

**Is it a crisis detector?**
No, and it must not be deployed as one. It scores five dimensions of one
message; it does not detect or handle crises, and none of its scores, W
included, is a crisis signal. Crisis handling is the job of deterministic code
around the model (Hamo calls it "the spine"), which must run before the model
on every path that feeds it. The license (§3c) requires consumer-facing
mental-wellness deployments to handle crisis and self-harm content with an
independent mechanism upstream of the model. The toolkit's `CrisisGate` is a
reference implementation: `score_message()` runs it first and skips the model
when it fires.

*The explicit-ideation rule does not change this.* v10's training labels apply
an explicit-ideation rule (explicit suicidal ideation: A at most 1.0, B 0, W
at least 2.5). It is a rule about scores and the stress formula, not crisis
handling: the A cap and B 0 are new in v10, added so that help-seeking next to
ideation does not reduce computed stress. On v10h's synthetic rows the rule is
no longer applied as an overlay: the counselor review's scores stand. On the
189 synthetic ideation-plus-help items of the old and new W safety exams, the
mean raw stress change is +2.51 from v10h's scores, +2.37 from v10's, −0.24
from v9's and −0.29 from v7's (gate G8 required at least 0). Two more
registered checks count, among the same 189 items, those scored W < 1.5 (G4c,
pass line ≤ 37: v10h 5, v10 6, v9 53, v7 37) and W < 2.5 (G4d, pass line ≤ 94:
v10h 8, v10 21, v9 102, v7 111). The items are of the same kind as the 150-pair
training patch added for this rule, which stays in v10h's corpus with the
review's scores (in v10 the rule was also applied to corpus rows a detector
flagged, changing labels on 179 existing rows): they show the training took,
not that the behaviour generalises.

*Acceptance status.* v10h's registration, frozen before training, asked one
main question: is it closer to the counselor review than v10? On 978 held-out
synthetic items the answer is yes. It also carried over v10's 18 checks and met
17. The one it did not meet, G5a, and G5b were stand-ins for crisis handling;
the registration made both report-only, because Hamo's founder ruled crisis
handling outside this model: it is not judged by this model or by its W score,
it is done in the spine. The other 16 all passed. v10's own status is
different: under its signed pre-registration the verdict was **rejected**, and
v10 was released by the founder's decision. Full statements and the table of
reported checks: the model's
[technical record, Evaluation](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation)
(linked from the model card).

*The bundled gate is a floor to build on, not a complete screen.* `CrisisGate`
is a keyword list, not a model. It fires on 107 of the 189 ideation-plus-help
items (56.6%). Extend the lists for your population, add a second screen
alongside the gate (never instead of it), and measure its recall on your own
data before relying on it.

**What changed in v10h, and what does the counselor review show?**
v10h keeps v10's prompts and training recipe and replaces the answers on the
synthetic training rows with the scores of a review by human counselors engaged
by Hamo; their names, number and credentials are not published. On 978 held-out
synthetic items, mean absolute error against that review is 0.142 for v10h and
0.255 for v10. That comparison is on synthetic messages only: real conversations
have no counselor scores, the 440 staff turns in training keep their teacher-era
labels, and on the real final exam v10h ties v10 against the reference scorer
(same state bucket on 440 and 435 of 453 turns).

The review is not one uniform scale: it was done in batches and its W, E and B
scoring drifts across the review, so v10h learned a blend. Where it differs from
the earlier rubric bands or overlay rules, the review stands, so A reads lower:
519 of 632 inside the earlier bands on the A exam (v10: 590), and mean A 0.43 on
the real final exam (v10: 0.53; reference labels: 0.84). Limits of the review:
[technical record](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#how-it-was-trained).
Switching from v10:
[integration guide](integration.md#upgrading-to-v10h).

**I moved to v9, my computed stress went up, and the docs told me to re-tune thresholds. Was that right?**
No. That advice (v9 model card, toolkit 0.2.0) was not enough; this is the
correction. v9's crisp-rubric B is 0 on most ordinary messages, so the relief
term of the stress formula, where B has a negative weight, disappears: on the
real final exam the mean raw per-turn stress change from v9's read-outs is
+0.37 where the reference labels give −0.68 (v10: −0.72, v10h: −0.63), and
replayed sessions drift upward. Re-tuning the cut-offs or the B weight cannot
repair this: a weight multiplies a zero.

If v9's scores feed `update_stress()` or any formula with a negative B weight,
move to v10h or v10 (v10 put B back on the legacy rubric, and v10h's B labels
start from there), or go back to v7, and do not carry over stress state
accumulated from v9 scores: it contains the drift. Do not blend or compare
scores across versions. The full correction, what to re-check after a switch
(the 4.0 / 7.0 buckets among them), digests, pinned revisions and rollback
steps are in the integration guide
([v10h](integration.md#upgrading-to-v10h), [v10](integration.md#upgrading-to-v10)).
First read the acceptance status above and the known B sign flip below.

**v10 scored a self-erasing sentence as a boundary — is that a bug?**
It is a known error of the v10 weights, not a wiring problem. With no
context, v10 scores 「行，我全听你的，你说哪天去就哪天去。」 ("Fine, I'll do
whatever you say — we go whichever day you say.") as **B 2.5**; v7 and v9
score it B 0.0 (an ARM CPU server running ollama gives the same 2.5 for v10;
so does the second seed). The v7 model card used this sentence (printed
without the final full stop) as its example of what the instrument must not
do: read self-erasure as a boundary; the v9 card cited its first clause. On
this sentence v10 does it. The read-out is brittle: without the final full
stop v10 gives B 2.0, and 「行，我全听你的，你安排吧」 gets B 0.0.

v10h scores this sentence B 0, with and without the final full stop, on the
shipped q8, MLX bf16 and transformers bf16 (no context). That is one sentence:
flips remain on other items.

How often — B sign flips (gold B 0 scored B ≥ 2.0):

| pool | v10h | v10 | registered cap | v9 | v7 |
|---|---|---|---|---|---|
| old B exam (legacy key), gold-0 items | 0/93 | 2/93 | ≤ 3 | 0/93 | 0/93 |
| self-erasure pool (old + new B exams) | 4/438 | 4/438 | ≤ 17 | 13/438 | 47/438 |
| real final exam: reference-B-0 turns scored B ≥ 2.0 | 13/166 | 12/166 | ≤ 17 | 1/166 | 10/166 |

v10h and v10 are inside each registered cap and far below v7 on the
self-erasure pool. v10 flips two items of the old B exam where v7, v9 and v10h
flip none, and both are slightly above v7 on the real final exam. Three
cautions. The self-erasure pool is in-distribution for the 150-pair
self-erasure training patch added in v10, which stays in v10h's corpus with the
review's scores: it shows the patch took, not how either version behaves on
real conversations. The last row counts any high B on a reference-B-0 turn, not
only self-erasure. v9's 0/93 and 1/166 are low because its crisp B is 0 on most
messages, at the cost described in the previous answer; on the self-erasure
pool v9 (13) is above v10h and v10 (4).

Why it matters: B has a negative weight in the stress formula, so a flipped B
reads the moment someone hands themselves over as relief. Do not take a high B
from v10h or v10 as proof that a boundary was kept, and do not act on any single raw
score: let rules fire on the smoothed state (`update_stress()` blends each
message in at 0.2) or on a pattern across turns. If a rule keys on
boundary-setting, test it on self-erasing phrasings from your own population
first.

**Why does my exam score say about 87% when the technical record says 82.8%?**
Different exams, different labels. The technical record's 82.8% (v10h, shipped
q8, five dimensions averaged) is on the real final exam, whose reference labels
follow the old A rubric: v10h's A there (319/453, 70.4% within ±0.5) measures
how far A has moved from that rubric, not accuracy.

The self-check exam is 195 synthetic questions, and there are no counselor
labels for it: v10h is graded on v10's label set, so a gap against v10's number
says nothing about which is right. Those labels come from the same teacher
prompts as v10's training labels, so for v10 the exam is in-distribution by
construction. Either way a pass checks *wiring*, not model quality: it shows that your deployment agrees with the exam's labels about as well as the reference does, and that `num_predict` is not too small, through the toolkit's own prompt, sampling and parser, not yours. It does not show which version you serve (v10 weights also pass v10h's band), and it does not check the chat template or `stop`: on ollama 0.40.13 tags without them read the same on 60 questions. Check those with `ollama show <tag> --template` and `--parameters`.
The v10h reference is 86.7%
for the shipped q8 and 86.8% for bf16; the pass band is dimension-level 84–90%,
each dimension ≥ 75%, A ≥ 81, JSON validity ≥ 99%, crisis gate 10/10. Do not
read 87% as accuracy: answering 0.5 on every dimension already scores 77.9% on
these labels. Under the band, check which weights and labels you are running:
on llama.cpp with Metal the A floor sits above v7 weights (A 80.5 on these labels); through ollama on one Apple-silicon Mac (Docker under Colima, arm64 CPU, ollama 0.40.13), warmed, v7 reads A 81.0, exactly on the floor. The
script prints `A81%` either way, so also check the dimension-level
number and B; a v9 or v7 deployment needs `--labels v9` or `--labels pre_v9`.
A v10 deployment uses `--labels v10` and keeps its own band (A ≥ 86%, reference
87.3%). Details:
[eval/README.md](../eval/README.md).

**Can I fine-tune it on my own data?**
Yes — [docs/finetune.md](finetune.md) is the generation-by-generation
playbook, data red lines early, including the six generations we rejected
(v5, v6, v8, v8.1, v9L, v10r) and the two, v9 and v10, released by founder
decision after failing pre-registered gates. Fine-tuned weights remain under
HAMO-RAIL-S (see the guide's license section).

**What exactly do the two licenses cover?**
This repo's code: Apache-2.0, with no use restrictions. The model weights:
HAMO-RAIL-S 1.0 — free commercial use with four restrictions (no standalone
clinical determinations; not the sole or primary basis for consequential
decisions about an identifiable person, and no covert monitoring; independent
upstream crisis handling and AI disclosure in consumer mental-wellness
deployments; no re-identification). The toolkit's default pipeline puts the
upstream mechanism in place structurally, but its keyword recall is partial
(see "Is it a crisis detector?"), so it does not by itself make a deployment
safe; showing the AI disclosure (ready-made texts included) is still on you.

**I think a score is wrong.**
Maybe. The reference scorer does not always agree with itself: in two spot
checks of 12 messages each (August 2026) it reproduced its own dimension
judgments within ±0.5 on 95% and 98%. First check which rubric your version
follows. **A** changed meaning at v9 (rubric v8; no real-conversation
measurement under it yet) and stays changed in v10. **B** changed to the crisp
rubric at v9 and back at v10 to the legacy rubric of v7 and earlier, where
calm, clear self-description earns B as well as a stated need or limit. v10
also applies the explicit-ideation rule. **v10h** starts from v10's rubrics, and
where the counselor review differs from them the review stands; its A has no
real-conversation measurement either. The known B sign flip is in the
self-erasure answer above. Rubric summaries:
[integration guide](integration.md#upgrading-to-v10h) and
[technical record](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md). If a *pattern* of
disagreement persists, file the **score disagreement** issue template, naming
the model version or file. We collect these reports as input for human review
of the rubric and of future versions.

---

# 中文

对应工具包 0.4.1，参考服务器跑的是 **v10h**。除另有说明，数字都测于随包 q8 GGUF：llama.cpp + Metal（Apple M1 Pro），温度 0，`repeat_penalty 1.0`、`top_k 0`、`top_p 1.0`；v7、v9、v10 的数字是各自随包的 q8 GGUF 在同样条件、同一份考卷上跑的。「bf16」指 safetensors 经 MLX 运行。验收考卷的数字用每题的完整上下文，不经 `build_prompt` 截短；自检卷和 ARM 服务器上的核对则经过截短。「真实终评」是 453 轮真实对话，来自三位知情同意的内部员工，已假名化，按参照标签（出自按生产口径打分的 LLM 评分器，其中 5 轮经人工修正；不是咨询师的分数）判卷，不对外分发。其余考卷都是合成的。

**为什么模板带空 `<think>` 块？** 模型的训练文本里，assistant 这一轮是一个空 think 块加 JSON。[`server/Modelfile`](../server/Modelfile) 的 `TEMPLATE` 预填了这个块，已发布的 q8 参考读数经 llama.cpp 用的就是它。请原样照抄。

ollama 0.32.5、0.40.12、0.40.13 默认会存下这段模板，但实际用 GGUF 自带的聊天模板（`ollama show <tag> --template` 打印的就是它；0.40.13 的 `/api/show` 报告 `template_source: gguf_chat_template`）。这时不会预填：模型自己写出空 think 块，再写 JSON，响应文本以 `<think>` 开头。`parse_scores()` 能处理；对响应直接 `json.loads` 会失败。

2026-10-31 与 11-01 在一台 Apple 芯片的 Mac 上（Colima 里的 Docker，arm64 CPU，ollama 0.40.13）实测：195 道考题和另外 1,415 条不同的合成提示词，没有一条回答带思考文字，也没有一条在 `num_predict 80` 处被截断。请求里带 `"think": false`，或服务端设 `OLLAMA_GO_TEMPLATE=1`，就会预填这个块，响应以 `{` 开头。模型已预热、提示词缓存关闭时，在这 195 题上，两条路径有 189 题完全一致，全部在 ±0.5 内（不预填 86.7%，预填 86.4%）。设了 `OLLAMA_GO_TEMPLATE=1` 而 `TEMPLATE` 里没有 think 块时，模型同样自己写出这个块：JSON 100%，86.7%。工具包的客户端不发 `think`。

**为什么温度必须 0，还必须中性化 `repeat_penalty`？** 评分是测量，采样噪声就是测量误差。而 **`repeat_penalty 1.1`**（ollama 0.32.9 及以前的默认值，0.32.10 起为 1.0）有害：本模型的输出 `{"A": 0.0, "W": 0.0, "E": 0.0, "H": 0.0, "B": 0.0}` 天然高度重复——惩罚重复 token 等于把分数从 0 往上推，凭空造出信号，还不报错。在 v10 q8 上测得：旧 B 卷（300 题，legacy 答案）上只把 1.0 换成 1.1，造分（没有边界的题与低臂题被打成 B ≥ 1.0）从 3/104（2.9%）升到 15/104（14.4%），B 符号翻转（标准答案 B 为 0 的题被打成 ≥ 2.0）在 93 题中从 2 条变成 4 条。v6.1、v7、v9 当时测出来也是往这个方向推（它们当时公布的数字见 [eval/README.md](../eval/README.md)）。

请始终设置 `repeat_penalty 1.0`、`top_k 0`、`top_p 1.0`。`server/Modelfile` 和 `server/docker-compose.yml` 已写好，工具包的 `OllamaClient` 也在每次请求里带上（请求参数优先于 Modelfile）；自己写的客户端若不随请求带上这三项，就只剩 Modelfile 这一层；Modelfile 也漏写，就一层都没有。自检卷走的是工具包的客户端，查不出漏写这三项的 Modelfile——请用 `ollama show <tag> --parameters` 核对。

**启动后第一条请求慢/超时？** 冷启动。每次（重新）加载模型后先预热一发，并保持 `keep_alive=-1`（工具包客户端每次请求都带；客户端与参考服务器的 `POST /score` 默认 8 秒硬超时）。预热请求要用长超时，不要走 8 秒的客户端：客户端断开时 ollama 会中止加载，比超时更慢的加载永远完不成。在一台 Apple 芯片的 Mac 上（Colima 里的 Docker，arm64 CPU，ollama 0.40.13），这只在人为限制 CPU 或缩短超时的情况下复现过。之后仍慢，通常是慢 CPU 上的 prefill 成本——检查截断护栏。

参考服务器（`server/docker-compose.yml`）里，`setup` 服务在 `docker compose up` 期间预热模型，之后 `api` 才启动。崩溃或机器重启后，`ollama` 和 `api` 会自动重启。这时 `setup` 不再运行，所以重启后的 `ollama` 没有加载模型。模型由 `api` 的健康检查加载；能在 `SCORE_TIMEOUT`（默认 8 秒）内加载完的话，第一条请求也会加载。健康检查每 60 秒调用一次 `/healthz`。`/healthz` 用自己的超时（`HEALTHZ_TIMEOUT`，默认 60 秒；`SCORE_TIMEOUT` 更长时取后者）给一条短探测打分，所以能完成比 `SCORE_TIMEOUT` 更慢的加载。探测耗时超过 `SCORE_TIMEOUT` 时，即使它已把模型加载完也返回 503；模型够快的话，下一次就能通过。

2026-11-01 在一台 Apple 芯片的 Mac 上（Colima 里的 Docker，arm64 CPU，ollama 0.40.13）实测：虚拟机重启后没有任何请求时，健康检查在 `api` 启动约 61 秒后加载了模型。把 `SCORE_TIMEOUT` 设成 0.7 秒（短于那台机器上约 1.3 秒的加载时间）后：没有健康检查时，130 秒内 48 次 `POST /score` 调用全部失败，每一次都中止了加载；有健康检查时，调用一直失败，直到第一次探测完成加载，之后就成功了。慢硬件本身没有测过。

用 `cpuset` 限制 ollama 容器时，把 `LLAMA_ARG_THREADS` 设成 CPU 数。在一台 Apple 芯片的 Mac 上（Colima 里的 Docker，arm64 CPU，ollama 0.40.13），限制到虚拟机 4 个 CPU 中的 2 个和 1500 MiB 内存时，不设的话 llama-server 仍是 4 个线程：预热用了 125 秒（不限制时约 3 秒），运行超过 400 秒后停掉时 `/score` 仍在返回 500。设 `LLAMA_ARG_THREADS=2` 后 11 秒就绪。

**小内存机器上，ollama 进程的内存越涨越高？** ollama 0.32.5 和 0.40.13 自带的 llama-server 有一个放在主机内存里的提示词缓存，默认开启（上限 8 GiB），每来一条不同的提示词就多占一份：在 0.32.5 上，我们在一台 4 GB 的机器上看到，100 条不同的提示词让进程从 1.3 GB 涨到 3.3 GB。在 ollama 服务的环境变量里设 `LLAMA_ARG_CACHE_RAM=0` 后不再增长（同样 100 条，1,277 → 1,294 MB），延迟中位数不变。`main` 上参考的 `server/docker-compose.yml` 自 2026-10-31 起设了这一项，`v0.4.1` 标签里的文件也设了；`v0.4.0` 标签里的文件没有设。

2026-10-31 在一台 Apple 芯片的 Mac 上（Colima 里的 Docker，arm64 CPU，ollama 0.40.13）用较短的单行合成消息（经 `POST /score`）实测：100 条不同的提示词，缓存开着时进程涨了 975 MB，关掉时涨了 2.3 MB，请求耗时中位数不变。增长幅度取决于提示词长度。在 4 GiB 内存限制、2 个 CPU、`LLAMA_ARG_THREADS=2` 下，缓存开着时，一遍串行的 `POST /score` 在第 182 条消息时运行进程因内存不足被杀，另一遍考卷因 HTTP 500 中断。同样的限制下关掉缓存，195 条全部返回，没有进程被杀，考卷 86.5%，ollama 容器峰值约 1.3 GiB。这些是容器限制，不是真正的小内存机器。

**输出不是合法 JSON？** `parse_scores()` 返回 `None`，按「跳过本句」处理（平滑后的状态不变）——不崩溃、不瞎猜。超过约 1% 时，先怀疑接线而不是模型（v10h q8 在六份验收考卷上无法解析的输出合计 0 条）。检查温度 0、`num_predict ≥ 80`，以及提示词是否出自 `build_prompt()`：在 ollama 0.40.13 上，`num_predict 20` 和一段手写的提示词都让 JSON 合法率降到 0%。在 ollama 0.32.5、0.40.12、0.40.13 上，响应以空 think 块开头是正常的：`parse_scores()` 能处理，直接 `json.loads` 不行。然后跑 `eval/run_exam.py`；要考 Docker 服务器，先按 [eval/README.md](../eval/README.md) 发布 ollama 的端口。

**支持哪些语言？** 中文为主。按 v10 训练集 20,787 行每行的最新消息统计（v10h 的 20,001 行是这些行去掉留出和移除的部分）：中文 76.0%、英文 13.1%、中英混杂 10.9%。我们没有公布 v10 或 v10h 分语言的准确率；其他语言未测——那是[微调指南](finetune.md)的事。

**「嗯」这类超短消息评不评？** 评，带上下文评。全零是设计好的无操作。真实对话里短消息很常见——跳过它们，等于在人最沉默的地方开一块盲区。

**多喂点上下文会不会更准？** 经工具包喂不进去，它会截短；多给会不会更准，v10 和 v10h 上都没有量过，而上下文长短本身会改变分数。`build_prompt` 只保留最后 3 轮 × 200 字，消息截到 500 字：这是给纯 CPU 服务器的延迟护栏，不是「模型训练时看到的样子」（v10 的训练行有 36.6% 上下文超过 3 轮），验收考卷用的则是完整上下文。护栏「截短后评分自一致（±0.5）98.1%」是 2026 年 8 月量的，没有在 v10 或 v10h 上重测。

**需要 GPU 吗？** 不需要。在 v10h 的 q8 上测得：一台运行 ollama 的 ARM CPU 服务器上，每条 P50 2.09 秒、P95 2.57 秒、最长 2.87 秒（138 道合成题，按工具包规则截短，模型已加载；提示词远短于截短上限，不是最坏情况）。v10 在同一项核对上是 P50 2.13 秒、P95 2.53 秒、最长 2.91 秒。

要让分数把关行为，就用随包的 Q8_0——v10h 的量化我们只量过这一档；自行量化后，先用 `eval/compare_quants.py` 与它对比。Hugging Face 上的社区 GGUF 量化自 v4 权重，比 v10h 落后五个发布版本，我们没有验证过。详见 [eval/README.md](../eval/README.md)。

**它是危机检测器吗？** 不是，也不能当危机检测器部署。它给一条消息的五个维度打分，不识别也不处理危机；它的分数，包括 W 在内，没有一个是危机信号。危机处理由模型外围的确定性代码负责（Hamo 称之为「脊柱」），凡把消息送进模型的路径，这层代码都必须先于模型运行。许可证（§3c）要求：面向消费者的心理健康类部署，必须由模型上游的独立机制处理危机与自伤内容。工具包的 `CrisisGate` 是参考实现：`score_message()` 先跑闸门，闸门触发就跳过模型。

*明确自杀意念规则不改变这一点。* v10 的训练标签加了一条明确自杀意念规则（出现明确的自杀意念时，A 封顶 1.0、B 为 0、W 至少 2.5）。这是一条关于分数和压力公式的规则，不是危机处理：A 封顶和 B 归零是 v10 新增的，为的是不让意念旁边的求助压低算出的压力。在 v10h 的合成行上这条规则不再叠加，以咨询师的复核分为准。新旧两份 W 安全卷共 189 道合成的「想死但求助」题上，平均原始压力变化按 v10h 的分数算是 +2.51，v10 是 +2.37，v9 是 −0.24，v7 是 −0.29（闸门 G8 要求不低于 0）。另有两项预注册检查，数的是这 189 题里 W 低于 1.5 的题数（G4c，通过线 ≤ 37：v10h 5、v10 6、v9 53、v7 37）和 W 低于 2.5 的题数（G4d，通过线 ≤ 94：v10h 8、v10 21、v9 102、v7 111）。这些题与为这条规则新加的训练补丁（150 对）同类，这批补丁留在 v10h 的语料里，用的是复核分（在 v10 里，规则还套用到全语料里被检测器标出的行，改了 179 行已有标签）：说明训练起了作用，不说明这种行为能泛化。

*验收状态。* v10h 的预注册在训练前冻结，主要问题是：它是否比 v10 更接近咨询师的复核？在 978 道留出的合成题上，答案是肯定的。预注册还沿用了 v10 的 18 项检查，v10h 过了 17 项。没过的是 G5a；G5a 和 G5b 都是危机处理的替代指标，Hamo 创始人裁定危机处理不归本模型，预注册因此把这两项定为只报告：危机处理不由本模型判定，也不由它的 W 分数判定，而是在脊柱里做。其余 16 项全过。v10 自己的状态不同：按签字的预注册，判定是**拒收**，v10 凭创始人的决定发布。完整说明与所报告各项检查的表格见模型的[技术档案的 Evaluation 一节](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation)（模型卡里有链接）。

*随包的闸门只是起点，不是完整筛查。* `CrisisGate` 是一份关键词表，不是模型。189 道「想死但求助」题它命中 107 道（56.6%）。请按你的人群扩充词表，在闸门旁边（而不是代替它）加第二层筛查，并在依赖它之前先在自己的数据上量出召回率。

**v10h 改了什么？咨询师复核说明了什么？** v10h 沿用 v10 的提示词和训练配方，把合成训练行的答案换成 Hamo 请的真人咨询师复核后的分数；他们的姓名、人数和资质不公开。在 978 道留出的合成题上，与这份复核的平均绝对误差 v10h 是 0.142，v10 是 0.255。这个比较只在合成消息上：真实对话没有咨询师分数，训练里的 440 轮内部员工对话沿用教师时期的标签；在真实终评上，以参照评分器为准，v10h 与 v10 打平（453 轮中落在同一状态桶的分别是 440 和 435 轮）。

这份复核不是一把尺子：它是分批做的，W、E、B 的打分前后有漂移，所以 v10h 学到的是折中。它与此前的口径分数带或叠加规则不同时，以复核为准，所以 A 读数偏低：A 卷落在此前分数带内的有 632 题中 519 题（v10 是 590 题），真实终评上平均 A 0.43（v10 0.53，参照标签 0.84）。复核的限度见[技术档案](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#how-it-was-trained)，从 v10 切换见[集成指南「升级到 v10h」](integration.md#升级到-v10h)。

**我换到了 v9，算出来的压力变高了，文档让我「重调阈值」——这个建议对吗？** 不对。那条建议（出自 v9 模型卡和工具包 0.2.0）不够，这里是更正。v9 的 crisp 口径让大多数普通消息的 B 为 0；压力公式里 B 是负权重，减压项就此消失：在真实终评上，按 v9 的读数算出的平均每轮原始压力变化是 +0.37，参照标签是 −0.68（v10 是 −0.72，v10h 是 −0.63），回放出来的会话整体上漂。重调分桶阈值或 B 的权重都救不回来：权重乘的是 0。

如果 v9 的分数喂给了 `update_stress()`，或任何 B 为负权重的公式：换到 v10h 或 v10（v10 把 B 改回 legacy 口径，v10h 的 B 标签从那里出发），或退回 v7；用 v9 分数累积出来的压力状态带着这段漂移，不要沿用。不同版本的分数不要混用，也不要互相比较。完整的更正、切换后要核对什么（包括 4.0 / 7.0 的分桶）、文件摘要、固定版本与回退步骤见集成指南（[升级到 v10h](integration.md#升级到-v10h)、[升级到 v10](integration.md#升级到-v10)）。动手之前，先读上面的验收状态和下面这条已知的 B 符号翻转。

**v10 把一句自我消融的话打成了「有边界」——这是 bug 吗？** 这是 v10 权重的一个已知错误，不是接线问题。不带上下文时，v10 把「行，我全听你的，你说哪天去就哪天去。」打成 **B 2.5**；v7 和 v9 都打 B 0.0（在运行 ollama 的 ARM CPU 服务器上 v10 同样是 2.5，第二个种子也是 2.5）。v7 的模型卡正是拿这句话（印的是不带句号的写法）当例子，说明这把尺子不能做什么：不能把自我消融读成边界；v9 的模型卡引的是它的前半句。在这句话上，v10 恰恰这么读了。读数还很脆：去掉句末的句号，v10 给 B 2.0；「行，我全听你的，你安排吧」得到 B 0.0。

v10h 把这句话打成 B 0：带不带句末句号都一样，随包 q8、MLX bf16、transformers bf16 都一样（无上下文）。这只是一句话，别的题上翻转还在。

发生得有多频繁——B 符号翻转（标准答案 B 为 0 的题被打成 B ≥ 2.0）：

| 题池 | v10h | v10 | 预注册上限 | v9 | v7 |
|---|---|---|---|---|---|
| 旧 B 卷（legacy 答案）中标准答案为 0 的题 | 0/93 | 2/93 | ≤ 3 | 0/93 | 0/93 |
| 自我消融题池（新旧 B 卷合并） | 4/438 | 4/438 | ≤ 17 | 13/438 | 47/438 |
| 真实终评：参照标签 B 为 0 的轮次被打成 B ≥ 2.0 | 13/166 | 12/166 | ≤ 17 | 1/166 | 10/166 |

v10h 和 v10 每一行都在预注册上限之内，在自我消融题池上远低于 v7。v10 在旧 B 卷上翻了 2 题，而 v7、v9、v10h 一题没翻；在真实终评上两者都比 v7 略高。读表有三点要留意：自我消融题池与 v10 新加的自我消融训练补丁（150 对）同分布，这批补丁留在 v10h 的语料里，用的是复核分，所以这一行说明的是补丁起了作用，不是这两版在真实对话上的表现；最后一行数的是参照标签 B 为 0 的轮次上各种原因的高 B，不只是自我消融；v9 的 0/93 和 1/166 低，是因为它的 crisp B 在大多数消息上本来就是 0（代价见上一条），而在自我消融题池上 v9（13）反而高于 v10h 和 v10（4）。

为什么要紧：B 在压力公式里是负权重，B 一旦翻转，系统就会把一个人交出自己的那一刻读成「减压」。不要把 v10h 或 v10 给出的高 B 当成「守住了边界」的证据，也不要凭任何单条原始分数采取行动：规则看平滑后的状态（`update_stress()` 每条消息只按 0.2 的比例融入），或看跨轮次的模式。产品里若有规则专门看「划边界」，先用你自己人群里的自我消融说法测一遍。

**为什么我考出约 87%，而技术档案写的是 82.8%？** 两张不同的卷子、两套不同的标签。技术档案的 82.8%（v10h，随包 q8，五维平均）出自真实终评，那套参照标签用的是旧的 A 口径：v10h 在那张卷上的 A（319/453，±0.5 内 70.4%）衡量的是 A 离那套口径挪动了多远，不是准确率。

自检卷是 195 道合成题，它没有咨询师标签：v10h 按 v10 那套标签判卷，所以它与 v10 的分数差说明不了谁对。这套标签与 v10 的训练标签出自同一套教师提示词，对 v10 按构造就是同分布。无论哪一版，这份卷检查的都是**接线**，不是模型水平：过关说明你的部署与考卷标签的一致程度和参考值相当、`num_predict` 没有设得过小，走的是工具包自己的提示词、采样与解析器，不是你的。它说明不了你跑的是哪个版本（v10 权重也过得了 v10h 的带），也不检查聊天模板和 `stop`：在 ollama 0.40.13 上，60 道题里缺了这两项的 ollama 标签读数相同。这两项用 `ollama show <tag> --template` 和 `--parameters` 核对。v10h 的参考值：随包 q8 86.7%，bf16 86.8%；合格带：维度级 84–90%、每一维 ≥ 75%、A ≥ 81、JSON 合法率 ≥ 99%、危机闸门 10/10。别把 87% 读成准确率：每一维都答 0.5，在这套标签上就有 77.9%。低于合格带时，先核对跑的是哪份权重、哪套标签：在 llama.cpp + Metal 上，A 的下限高于 v7 权重（这套标签上 A 为 80.5）；在一台 Apple 芯片的 Mac 上（Colima 里的 Docker，arm64 CPU，ollama 0.40.13）经 ollama，模型已预热时，v7 的 A 是 81.0，正好压线。两种情况脚本都打印 `A81%`，所以还要看维度级和 B；部署的是 v9 或 v7，要加 `--labels v9` 或 `--labels pre_v9`；部署 v10 的用 `--labels v10`，沿用它自己的合格带（A ≥ 86%，参考值 87.3%）。详见 [eval/README.md](../eval/README.md)。

**能用自己的数据微调吗？** 能——[微调指南](finetune.md)按代讲完整打法，数据红线靠前；拒收的六代（v5、v6、v8、v8.1、v9L、v10r）和没过预注册闸门、凭创始人决定发布的两代（v9、v10）都写在里面。微调出的权重仍受 HAMO-RAIL-S 约束（见指南的许可证一节）。

**两份许可证分别管什么？** 本仓库的代码：Apache-2.0，没有使用限制。模型权重：HAMO-RAIL-S 1.0——可免费商用，但有四条限制（不得独立做临床判定；不得作为对可识别个人做重大决定的唯一或主要依据，也不得用于隐蔽监测；面向消费者的心理健康类部署须有独立的上游危机处理与 AI 身份披露；不得重识别）。工具包的默认管线在结构上放好了这道上游机制，但它的关键词召回有限（见「它是危机检测器吗？」），单靠它并不能让部署变得安全；展示 AI 身份披露（附现成文案）仍是你的责任。

**评分不服怎么办？** 可能你是对的。参照评分器自己也不总是前后一致：2026 年 8 月的两次抽查（每次 12 条消息）里，它在 ±0.5 内复现自己维度判断的比例是 95% 和 98%。下结论之前，先看你所用版本遵循哪套口径。**A** 的含义在 v9 改过（v8 口径，至今没有真实对话上的测量），v10 沿用。**B** 在 v9 改成 crisp 口径，v10 改回 v7 及更早版本用的 legacy 口径：平静、清楚的自我陈述和说出的需要、界限一样给 B。v10 另有明确自杀意念规则。**v10h** 从 v10 的口径出发，咨询师的复核与这些口径不同时以复核为准；它的 A 同样没有真实对话上的测量。已知的 B 符号翻转见上面自我消融那一条。口径摘要见[集成指南](integration.md#升级到-v10h)和[技术档案](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md)。成规律的分歧请用「评分分歧」issue 模板提交，并写明模型版本或文件。我们收集这些报告，作为人工复核口径和后续版本的输入。
