# FAQ

**EN** | [中文](#中文)

For toolkit 0.3.1, which serves model **v10**. Unless stated otherwise, numbers
are for the shipped q8 GGUF through llama.cpp with Metal on an Apple M1 Pro, at
temperature 0 with `repeat_penalty 1.0`, `top_k 0`, `top_p 1.0`; v7 and v9
numbers are their shipped q8 GGUFs run the same way on the same exam files.
"bf16" is the safetensors through MLX. Acceptance-exam numbers use each item's
full context, not `build_prompt`'s trimming; the self-check exam and the ARM
serving check use the trimming. "The real final exam" is 453 real turns from
pseudonymised conversations of three consenting internal staff members, graded
against reference labels (from the production rubric's LLM scorer, with human
corrections on 5 of the 453 turns) and not distributed. The other exams are
synthetic.

**Why must the template contain an empty `<think>` block?**
The student is a Qwen3 base fine-tuned with thinking disabled; the template
pre-fills an empty think block so the model goes straight to the JSON. Without
it the model may emit think text, and under the `num_predict 80` cap the JSON
can be cut off — expect parse failures, not just latency. Copy the `TEMPLATE`
block of [`server/Modelfile`](../server/Modelfile) unchanged.

**Why temperature 0 — and why must I also neutralise `repeat_penalty`?**
Scoring is measurement; sampling noise is measurement error. And **ollama
defaults to `repeat_penalty 1.1`**, while this model's output —
`{"A": 0.0, "W": 0.0, "E": 0.0, "H": 0.0, "B": 0.0}` — is repetitive by
design: penalising repeated tokens pushes scores away from 0, i.e. fabricates
signal, with no error. On v10 q8 with the old B exam (300 questions, legacy
key), changing only 1.0 → 1.1 takes fabrication (no-boundary and low-arm
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
`keep_alive=-1` (the toolkit's client sets it per request; client and
reference server default to an 8-second hard timeout). If later requests are
still slow, the usual cost is prompt prefill on a slow CPU — check the
trimming guards.

**The ollama process keeps growing in memory on a small machine.**
On ollama 0.32.5 the bundled llama-server keeps a host-memory prompt cache
(default limit 8 GiB) that grows with every distinct prompt: on a 4 GB machine
we saw the process grow from 1.3 GB to 3.3 GB over 100 distinct prompts.
Setting `LLAMA_ARG_CACHE_RAM=0` in the ollama service environment stopped the
growth (1,277 → 1,294 MB over the same 100 prompts) with median latency
unchanged. The reference `server/docker-compose.yml` does not set it.

**My output isn't valid JSON.**
`parse_scores()` returns `None`; treat it as "skip this message" (the smoothed
state stays unchanged) — never crash, never guess. Above ~1% of messages,
suspect your wiring before the model (v10 q8: 0 unparseable outputs across the
six acceptance exams). Check the empty think template, temperature 0 and
`num_predict ≥ 80`, then run `eval/run_exam.py`.

**Which languages does it support?**
Chinese-primary. By the latest message of each of the 20,787 v10 training
rows: 76.0% Chinese, 13.1% English, 10.9% mixed Chinese–English. We publish no
per-language accuracy for v10; other languages are untested — that is what
[fine-tuning](finetune.md) is for.

**What about ultra-short messages like "嗯" or "ok"?**
Score them, with context attached. An all-zero result is a designed no-op.
Short messages are common in real conversations; skipping them creates a blind
spot exactly where distressed people go terse.

**Can I send more conversation context for better accuracy?**
Not through the toolkit, which trims it; whether more context helps is not
measured on v10, and context length can move a score. `build_prompt` keeps the
last 3 turns × 200 characters and caps the message at 500: a latency guard for
CPU-only servers, not what the model saw in training (36.6% of training rows
carry more than 3 context turns) nor what the acceptance exams ran on (full
context). The guard's 98.1% score self-agreement (±0.5) dates from August 2026
and was not re-measured on v10.

**Do I need a GPU?**
No. The shipped q8 on an ARM CPU server running ollama: P50 2.13 s, P95
2.53 s, max 2.91 s per message (138 synthetic items, toolkit trimming, model
loaded; prompts far shorter than the trimming allows, so not a worst case).

Where scores gate behaviour, use the shipped Q8_0, the one v10 quantization we
have measured; compare your own against it with `eval/compare_quants.py`
first. The community GGUF quantizations on Hugging Face were made from the v4
weights, four releases behind v10, and we have not validated them. Details:
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
ideation does not reduce computed stress. On the 189 synthetic
ideation-plus-help items of the old and new W safety exams, the mean raw
stress change is +2.37 from v10's scores, −0.24 from v9's and −0.29 from v7's
(gate G8 required at least 0). Two more registered checks count, among the
same 189 items, those scored W < 1.5 (G4c, pass line ≤ 37: v10 6, v9 53,
v7 37) and W < 2.5 (G4d, pass line ≤ 94: v10 21, v9 102, v7 111). The items
are of the same kind as the 150-pair training patch added for this rule (the
rule was also applied to corpus rows a detector flagged, changing labels on
179 existing rows): they show the training took, not that the behaviour
generalises.

*Acceptance status.* v10 met 17 of the 18 checks of its signed
pre-registration. The one it did not meet, G5a, was a stand-in for crisis
handling. After seeing the result, Hamo's founder ruled that crisis handling
is not judged by this model or by its W score: it is done in the spine. Under
the registration as signed the verdict was **rejected**; v10 is released by
the founder's decision. This is a waiver of one pre-registered gate made after
the result was known, and the second release in a row to ship by founder
decision after failing a pre-registered gate (v9 failed 2 of 5). Full statement
and the table of reported checks:
[model card, Evaluation](https://huggingface.co/HamoAI/hamo-score-0.6b#evaluation).

*The bundled gate is a floor to build on, not a complete screen.* `CrisisGate`
is a keyword list, not a model. It fires on 107 of the 189 ideation-plus-help
items (56.6%). Extend the lists for your population, add a second screen
alongside the gate (never instead of it), and measure its recall on your own
data before relying on it.

**I moved to v9, my computed stress went up, and the docs told me to re-tune thresholds. Was that right?**
No. That advice (v9 model card, toolkit 0.2.0) was not enough; this is the
correction. v9's crisp-rubric B is 0 on most ordinary messages, so the relief
term of the stress formula, where B has a negative weight, disappears: on the
real final exam the mean raw per-turn stress change from v9's read-outs is
+0.37 where the reference labels give −0.68 (v10: −0.72), and replayed
sessions drift upward. Re-tuning the cut-offs or the B weight cannot repair
this: a weight multiplies a zero.

If v9's scores feed `update_stress()` or any formula with a negative B weight,
move to v10 (B back on the legacy rubric) or go back to v7, and do not carry
over stress state accumulated from v9 scores: it contains the drift. Do not
blend or compare scores across versions. The full correction, what to
re-check under v10 (the 4.0 / 7.0 buckets among them), digests, pinned
revisions and rollback steps are in the
[integration guide](integration.md#upgrading-to-v10). First read the
acceptance status above and the known B sign flip below.

**v10 scored a self-erasing sentence as a boundary — is that a bug?**
It is a known error of the released weights, not a wiring problem. With no
context, v10 scores 「行，我全听你的，你说哪天去就哪天去。」 ("Fine, I'll do
whatever you say — we go whichever day you say.") as **B 2.5**; v7 and v9
score it B 0.0 (an ARM CPU server running ollama gives the same 2.5 for v10;
so does the second seed). The v7 model card used this sentence (printed
without the final full stop) as its example of what the instrument must not
do: read self-erasure as a boundary; the v9 card cited its first clause. On
this sentence v10 does it. The read-out is brittle: without the final full
stop v10 gives B 2.0, and 「行，我全听你的，你安排吧」 gets B 0.0.

How often — B sign flips (gold B 0 scored B ≥ 2.0):

| pool | v10 | registered cap | v9 | v7 |
|---|---|---|---|---|
| old B exam (legacy key), gold-0 items | 2/93 | ≤ 3 | 0/93 | 0/93 |
| self-erasure pool (old + new B exams) | 4/438 | ≤ 17 | 13/438 | 47/438 |
| real final exam: reference-B-0 turns scored B ≥ 2.0 | 12/166 | ≤ 17 | 1/166 | 10/166 |

v10 is inside each registered cap and far below v7 on the self-erasure pool,
but it flips two items of the old B exam where v7 and v9 flip none, and is
slightly above v7 on the real final exam. Three cautions. The self-erasure
pool is in-distribution for the 150-pair self-erasure training patch added in
v10: it shows the patch took, not how v10 behaves on real conversations. The
last row counts any high B on a reference-B-0 turn, not only self-erasure.
v9's 0/93 and 1/166 are low because its crisp B is 0 on most messages, at the
cost described in the previous answer; on the self-erasure pool v9 (13) is
above v10 (4).

Why it matters: B has a negative weight in the stress formula, so a flipped B
reads the moment someone hands themselves over as relief. Do not take a high B
from v10 as proof that a boundary was kept, and do not act on any single raw
score: let rules fire on the smoothed state (`update_stress()` blends each
message in at 0.2) or on a pattern across turns. If a rule keys on
boundary-setting, test it on self-erasing phrasings from your own population
first.

**Why does my exam score say about 87% when the model card says 82.4%?**
Different exams, different labels. The card's 82.4% (v10, five dimensions
averaged; same figure for q8 and bf16) is on the real final exam, whose
reference labels follow the old A rubric: v10's A there (327/453, 72.2% within
±0.5) measures how far rubric v8 moved A, not accuracy.

The self-check exam is 195 synthetic questions whose labels come from the same
teacher prompts as the training labels. It is in-distribution by construction:
a pass certifies *wiring* (the served weights and the server's template,
`num_predict` and stop, through the toolkit's own prompt, sampling and parser,
not yours), not model quality. The v10 reference is 87.3% for both bf16 and
the shipped q8; the pass band is dimension-level 84–90%, each dimension ≥ 75%,
A ≥ 86%, JSON validity ≥ 99%, crisis gate 10/10. Do not read 87% as accuracy:
answering 0.5 on every dimension already scores 77.9% on these labels. Under
the band, check which weights and labels you are running: the A floor
separates v10 weights from v7 weights (A about 80), and a v9 or v7 deployment
needs `--labels v9` or `--labels pre_v9`. Details:
[eval/README.md](../eval/README.md).

**Can I fine-tune it on my own data?**
Yes — [docs/finetune.md](finetune.md) is the generation-by-generation
playbook, data red lines early, including the five generations we rejected
(v5, v6, v8, v8.1, v9L) and the two, v9 and v10, released by founder decision
after failing pre-registered gates. Fine-tuned weights remain under
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
also applies the explicit-ideation rule; its known B sign flip is in the
self-erasure answer above. Rubric summaries:
[integration guide](integration.md#upgrading-to-v10) and
[model card](https://huggingface.co/HamoAI/hamo-score-0.6b). If a *pattern* of
disagreement persists, file the **score disagreement** issue template, naming
the model version or file. We collect these reports as input for human review
of the rubric and of future versions.

---

# 中文

对应工具包 0.3.1，随包模型是 **v10**。除另有说明，数字都测于随包 q8 GGUF：llama.cpp + Metal（Apple M1 Pro），温度 0，`repeat_penalty 1.0`、`top_k 0`、`top_p 1.0`；v7、v9 的数字是各自随包的 q8 GGUF 在同样条件、同一份考卷上跑的。「bf16」指 safetensors 经 MLX 运行。验收考卷的数字用每题的完整上下文，不经 `build_prompt` 截短；自检卷和 ARM 服务器上的核对则经过截短。「真实终评」是 453 轮真实对话，来自三位知情同意的内部员工，已假名化，按参照标签（出自按生产口径打分的 LLM 评分器，其中 5 轮经人工修正）判卷，不对外分发。其余考卷都是合成的。

**为什么模板必须带空 `<think>` 块？** 学生是关闭思考训练的 Qwen3，模板预填一个空 think 块，让它直接输出 JSON。没有它，模型可能先「想」一段；在 `num_predict 80` 的上限下 JSON 可能被截断——你看到的会是解析失败，不只是变慢。请原样照抄 [`server/Modelfile`](../server/Modelfile) 的 `TEMPLATE` 段。

**为什么温度必须 0，还必须中性化 `repeat_penalty`？** 评分是测量，采样噪声就是测量误差。而 **ollama 默认 `repeat_penalty 1.1`**，本模型的输出 `{"A": 0.0, "W": 0.0, "E": 0.0, "H": 0.0, "B": 0.0}` 天然高度重复——惩罚重复 token 等于把分数从 0 往上推，凭空造出信号，还不报错。v10 q8 在旧 B 卷（300 题，legacy 答案）上只把 1.0 换成 1.1：造分（没有边界的题与低臂题被打成 B ≥ 1.0）从 3/104（2.9%）升到 15/104（14.4%），B 符号翻转（标准答案 B 为 0 的题被打成 ≥ 2.0）在 93 题中从 2 条变成 4 条。v6.1、v7、v9 当时测出来也是往这个方向推（它们当时公布的数字见 [eval/README.md](../eval/README.md)）。

请始终设置 `repeat_penalty 1.0`、`top_k 0`、`top_p 1.0`。`server/Modelfile` 和 `server/docker-compose.yml` 已写好，工具包的 `OllamaClient` 也在每次请求里带上（请求参数优先于 Modelfile）；自己写的客户端若不随请求带上这三项，就只剩 Modelfile 这一层；Modelfile 也漏写，就一层都没有。自检卷走的是工具包的客户端，查不出漏写这三项的 Modelfile——请用 `ollama show <tag> --parameters` 核对。

**启动后第一条请求慢/超时？** 冷启动。每次（重新）加载模型后先预热一发，并保持 `keep_alive=-1`（工具包客户端每次请求都带；客户端与参考服务器默认 8 秒硬超时）。之后仍慢，通常是慢 CPU 上的 prefill 成本——检查截断护栏。

**小内存机器上，ollama 进程的内存越涨越高？** ollama 0.32.5 自带的 llama-server 有一个放在主机内存里的提示词缓存（默认上限 8 GiB），每来一条不同的提示词就多占一份：我们在一台 4 GB 的机器上看到，100 条不同的提示词让进程从 1.3 GB 涨到 3.3 GB。在 ollama 服务的环境变量里设 `LLAMA_ARG_CACHE_RAM=0` 后不再增长（同样 100 条，1,277 → 1,294 MB），延迟中位数不变。参考的 `server/docker-compose.yml` 没有设这一项。

**输出不是合法 JSON？** `parse_scores()` 返回 `None`，按「跳过本句」处理（平滑后的状态不变）——不崩溃、不瞎猜。超过约 1% 时，先怀疑接线而不是模型（v10 q8 在六份验收考卷上无法解析的输出合计 0 条）。检查空 think 模板、温度 0、`num_predict ≥ 80`，再跑 `eval/run_exam.py`。

**支持哪些语言？** 中文为主。按 v10 训练集 20,787 行每行的最新消息统计：中文 76.0%、英文 13.1%、中英混杂 10.9%。我们没有公布 v10 分语言的准确率；其他语言未测——那是[微调指南](finetune.md)的事。

**「嗯」这类超短消息评不评？** 评，带上下文评。全零是设计好的无操作。真实对话里短消息很常见——跳过它们，等于在人最沉默的地方开一块盲区。

**多喂点上下文会不会更准？** 经工具包喂不进去，它会截短；多给会不会更准，v10 上没有量过，而上下文长短本身会改变分数。`build_prompt` 只保留最后 3 轮 × 200 字，消息截到 500 字：这是给纯 CPU 服务器的延迟护栏，不是「模型训练时看到的样子」（36.6% 的训练行上下文超过 3 轮），验收考卷用的则是完整上下文。护栏「截短后评分自一致（±0.5）98.1%」是 2026 年 8 月量的，没有在 v10 上重测。

**需要 GPU 吗？** 不需要。随包 q8 在一台运行 ollama 的 ARM CPU 服务器上：每条 P50 2.13 秒、P95 2.53 秒、最长 2.91 秒（138 道合成题，按工具包规则截短，模型已加载；提示词远短于截短上限，不是最坏情况）。

要让分数把关行为，就用随包的 Q8_0——v10 的量化我们只量过这一档；自行量化后，先用 `eval/compare_quants.py` 与它对比。Hugging Face 上的社区 GGUF 量化自 v4 权重，比 v10 落后四个发布版本，我们没有验证过。详见 [eval/README.md](../eval/README.md)。

**它是危机检测器吗？** 不是，也不能当危机检测器部署。它给一条消息的五个维度打分，不识别也不处理危机；它的分数，包括 W 在内，没有一个是危机信号。危机处理由模型外围的确定性代码负责（Hamo 称之为「脊柱」），凡把消息送进模型的路径，这层代码都必须先于模型运行。许可证（§3c）要求：面向消费者的心理健康类部署，必须由模型上游的独立机制处理危机与自伤内容。工具包的 `CrisisGate` 是参考实现：`score_message()` 先跑闸门，闸门触发就跳过模型。

*明确自杀意念规则不改变这一点。* v10 的训练标签加了一条明确自杀意念规则（出现明确的自杀意念时，A 封顶 1.0、B 为 0、W 至少 2.5）。这是一条关于分数和压力公式的规则，不是危机处理：A 封顶和 B 归零是 v10 新增的，为的是不让意念旁边的求助压低算出的压力。新旧两份 W 安全卷共 189 道合成的「想死但求助」题上，平均原始压力变化按 v10 的分数算是 +2.37，v9 是 −0.24，v7 是 −0.29（闸门 G8 要求不低于 0）。另有两项预注册检查，数的是这 189 题里 W 低于 1.5 的题数（G4c，通过线 ≤ 37：v10 6、v9 53、v7 37）和 W 低于 2.5 的题数（G4d，通过线 ≤ 94：v10 21、v9 102、v7 111）。这些题与为这条规则新加的训练补丁（150 对）同类（规则还套用到全语料里被检测器标出的行，改了 179 行已有标签）：说明训练起了作用，不说明这种行为能泛化。

*验收状态。* 签字版预注册的 18 项检查，v10 过了 17 项。没过的那一项 G5a，当初是作为危机处理的替代指标设的；Hamo 创始人看到结果后裁定，危机处理不由本模型判定，也不由它的 W 分数判定，而是在脊柱里做。按签字的预注册，判定是**拒收**；v10 凭创始人的决定发布。这是在结果已知之后对一道预注册闸门的豁免，v10 也是连续第二个没过预注册闸门、凭创始人决定发布的版本（v9 的五道闸门没过两道）。完整说明与所报告各项检查的表格见[模型卡的 Evaluation 一节](https://huggingface.co/HamoAI/hamo-score-0.6b#evaluation)。

*随包的闸门只是起点，不是完整筛查。* `CrisisGate` 是一份关键词表，不是模型。189 道「想死但求助」题它命中 107 道（56.6%）。请按你的人群扩充词表，在闸门旁边（而不是代替它）加第二层筛查，并在依赖它之前先在自己的数据上量出召回率。

**我换到了 v9，算出来的压力变高了，文档让我「重调阈值」——这个建议对吗？** 不对。那条建议（出自 v9 模型卡和工具包 0.2.0）不够，这里是更正。v9 的 crisp 口径让大多数普通消息的 B 为 0；压力公式里 B 是负权重，减压项就此消失：在真实终评上，按 v9 的读数算出的平均每轮原始压力变化是 +0.37，参照标签是 −0.68（v10 是 −0.72），回放出来的会话整体上漂。重调分桶阈值或 B 的权重都救不回来：权重乘的是 0。

如果 v9 的分数喂给了 `update_stress()`，或任何 B 为负权重的公式：换到 v10（B 回到 legacy 口径），或退回 v7；用 v9 分数累积出来的压力状态带着这段漂移，不要沿用。不同版本的分数不要混用，也不要互相比较。完整的更正、换到 v10 后要核对什么（包括 4.0 / 7.0 的分桶）、文件摘要、固定版本与回退步骤见[集成指南「升级到 v10」](integration.md#升级到-v10)。动手之前，先读上面的验收状态和下面这条已知的 B 符号翻转。

**v10 把一句自我消融的话打成了「有边界」——这是 bug 吗？** 这是已发布权重的一个已知错误，不是接线问题。不带上下文时，v10 把「行，我全听你的，你说哪天去就哪天去。」打成 **B 2.5**；v7 和 v9 都打 B 0.0（在运行 ollama 的 ARM CPU 服务器上 v10 同样是 2.5，第二个种子也是 2.5）。v7 的模型卡正是拿这句话（印的是不带句号的写法）当例子，说明这把尺子不能做什么：不能把自我消融读成边界；v9 的模型卡引的是它的前半句。在这句话上，v10 恰恰这么读了。读数还很脆：去掉句末的句号，v10 给 B 2.0；「行，我全听你的，你安排吧」得到 B 0.0。

发生得有多频繁——B 符号翻转（标准答案 B 为 0 的题被打成 B ≥ 2.0）：

| 题池 | v10 | 预注册上限 | v9 | v7 |
|---|---|---|---|---|
| 旧 B 卷（legacy 答案）中标准答案为 0 的题 | 2/93 | ≤ 3 | 0/93 | 0/93 |
| 自我消融题池（新旧 B 卷合并） | 4/438 | ≤ 17 | 13/438 | 47/438 |
| 真实终评：参照标签 B 为 0 的轮次被打成 B ≥ 2.0 | 12/166 | ≤ 17 | 1/166 | 10/166 |

v10 每一行都在预注册上限之内，在自我消融题池上远低于 v7；但在旧 B 卷上它翻了 2 题，而 v7 和 v9 一题没翻，在真实终评上也比 v7 略高。读表有三点要留意：自我消融题池与 v10 新加的自我消融训练补丁（150 对）同分布，说明的是补丁起了作用，不是 v10 在真实对话上的表现；最后一行数的是参照标签 B 为 0 的轮次上各种原因的高 B，不只是自我消融；v9 的 0/93 和 1/166 低，是因为它的 crisp B 在大多数消息上本来就是 0（代价见上一条），而在自我消融题池上 v9（13）反而高于 v10（4）。

为什么要紧：B 在压力公式里是负权重，B 一旦翻转，系统就会把一个人交出自己的那一刻读成「减压」。不要把 v10 给出的高 B 当成「守住了边界」的证据，也不要凭任何单条原始分数采取行动：规则看平滑后的状态（`update_stress()` 每条消息只按 0.2 的比例融入），或看跨轮次的模式。产品里若有规则专门看「划边界」，先用你自己人群里的自我消融说法测一遍。

**为什么我考出约 87%，而模型卡写的是 82.4%？** 两张不同的卷子、两套不同的标签。模型卡的 82.4%（v10，五维平均；q8 与 bf16 数字相同）出自真实终评，那套参照标签用的是旧的 A 口径：v10 在那张卷上的 A（327/453，±0.5 内 72.2%）衡量的是 v8 口径把 A 挪动了多远，不是准确率。

自检卷是 195 道合成题，标签与训练标签出自同一套教师提示词，按构造就是同分布：过关认证的是**接线**（你部署的权重，服务端的模板、`num_predict` 与 stop；走的是工具包自己的提示词、采样与解析器，不是你的），不是模型水平。v10 的参考值：bf16 与随包 q8 都是 87.3%；合格带：维度级 84–90%、每一维 ≥ 75%、A ≥ 86%、JSON 合法率 ≥ 99%、危机闸门 10/10。别把 87% 读成准确率：每一维都答 0.5，在这套标签上就有 77.9%。低于合格带时，先核对跑的是哪份权重、哪套标签：A 的下限用来区分 v10 权重和 v7 权重（v7 的 A 约 80）；部署的是 v9 或 v7，要加 `--labels v9` 或 `--labels pre_v9`。详见 [eval/README.md](../eval/README.md)。

**能用自己的数据微调吗？** 能——[微调指南](finetune.md)按代讲完整打法，数据红线靠前；拒收的五代（v5、v6、v8、v8.1、v9L）和没过预注册闸门、凭创始人决定发布的两代（v9、v10）都写在里面。微调出的权重仍受 HAMO-RAIL-S 约束（见指南的许可证一节）。

**两份许可证分别管什么？** 本仓库的代码：Apache-2.0，没有使用限制。模型权重：HAMO-RAIL-S 1.0——可免费商用，但有四条限制（不得独立做临床判定；不得作为对可识别个人做重大决定的唯一或主要依据，也不得用于隐蔽监测；面向消费者的心理健康类部署须有独立的上游危机处理与 AI 身份披露；不得重识别）。工具包的默认管线在结构上放好了这道上游机制，但它的关键词召回有限（见「它是危机检测器吗？」），单靠它并不能让部署变得安全；展示 AI 身份披露（附现成文案）仍是你的责任。

**评分不服怎么办？** 可能你是对的。参照评分器自己也不总是前后一致：2026 年 8 月的两次抽查（每次 12 条消息）里，它在 ±0.5 内复现自己维度判断的比例是 95% 和 98%。下结论之前，先看你所用版本遵循哪套口径。**A** 的含义在 v9 改过（v8 口径，至今没有真实对话上的测量），v10 沿用。**B** 在 v9 改成 crisp 口径，v10 改回 v7 及更早版本用的 legacy 口径：平静、清楚的自我陈述和说出的需要、界限一样给 B。v10 另有明确自杀意念规则；已知的 B 符号翻转见上面自我消融那一条。口径摘要见[集成指南](integration.md#升级到-v10)和[模型卡](https://huggingface.co/HamoAI/hamo-score-0.6b)。成规律的分歧请用「评分分歧」issue 模板提交，并写明模型版本或文件。我们收集这些报告，作为人工复核口径和后续版本的输入。
