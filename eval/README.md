# 自检考卷 · Self-Check Exam

部署完成后，用这份考卷验证你的部署是否复现了官方数字。
After deploying, run this exam to verify your deployment reproduces the official numbers.

> **自工具包 0.2.0 起，本考卷按 v9 口径判卷**：A、B 两列已按 v9 的新口径重标，官方参考值改为 v9。
> 有意部署 v7？请加 `--labels pre_v9`，对照每题保留的旧标签（见下文「部署的是 v7？」）。
>
> **Since toolkit 0.2.0 this exam grades against the v9 rubrics**: its A and B labels were
> re-labelled and the official reference is now v9. Deploying v7 on purpose? Pass
> `--labels pre_v9` to grade against the pre-v9 labels each question keeps (see "Deploying v7?" below).

```bash
python eval/run_exam.py                       # ollama on localhost:11434
python eval/run_exam.py --base-url http://myhost:11434 --model my-tag
python eval/run_exam.py --labels pre_v9       # 有意部署 v7 时 · a v7 deployment on purpose
```

## 考卷构成 · What's inside

- **评分区 `synthetic_exam.jsonl`（195 题）**：10 个非危机场景格子（闲聊、省略回复、躯体陈述、
  第三方冲突、顶撞助手、自我批评、短促求助、隐含重度、敌意但清晰、长篇倾诉）各约 20 题。
  全部合成生成（2026-08-16 全新种子，与所有训练语料不相交），教师标签来自 deepseek-chat：
  W/E/H 按生产口径；A、B 于 2026-09-29 按 v9 口径重标（见下文），旧标签逐题保留在
  `labels_pre_v9` 字段。**不含任何真实来访者数据。**
- **闸门区 `gate_cases.jsonl`（10 题）**：手写危机句式 7 条（中英）+ 黑色幽默/夸张表达 3 条
  （不应误触）。这一节不调用模型——它在进程内跑工具包的 `CrisisGate` 词表，与模型版本无关。
  注意它不验证你的部署是否真把每条消息先送过闸门，那是你自己要做的集成测试。

Scoring section: 195 synthetic, teacher-labeled (deepseek-chat) questions across 10 non-crisis
cells; fresh seed, disjoint from all training corpora; **zero real client data**. W/E/H are
labelled under the production rubric; A and B were re-labelled on 2026-09-29 for the v9 rubrics
(see below), and each question keeps its previous labels in `labels_pre_v9`. Gate section: 10
handwritten cases (7 crisis phrasings zh+en, 3 dark-humor lookalikes) run against the toolkit's
`CrisisGate` word lists in-process — independent of the model version. It does not test that
your deployment actually routes every message through the gate before the model — that wiring
is an integration test you own.

## 官方参考数字 · Official reference (v9)

| 指标 Metric | 参考值 Reference（v9 bf16） | 合格带 Expected band |
|---|---|---|
| JSON 合法率 JSON validity | 100% | ≥ 99% |
| 维度级一致率 Dim-level agreement (±0.5) | 88.9% | 86–92% |
| 分维 Per-dim | A 91 · W 80 · E 86 · H 92 · B 96 | 各维 ≥ 75% · each ≥ 75% |
| 闸门区 Crisis gate | 10/10 | 10/10（硬性 hard requirement） |

参考值测于 v9 bf16 权重（MLX，M1 Pro，**温度 0 且无重复惩罚**；本考卷上延迟 P50 0.57 秒，不作横向参考——
延迟取决于你的硬件，不属于合格带）。我们发布的 v9 q8_0 GGUF 经 llama.cpp（`server/Modelfile` 的模板，
中性采样：temperature 0、top_k 0、top_p 1.0、repeat_penalty 1.0）实测：JSON 100%、维度级 89.3%
（A 92 · W 80 · E 87 · H 92 · B 96）、闸门 10/10，落在合格带内；经 ollama 部署同样应落在带内，轻微浮动来自
量化与采样器实现差异。若你的 ollama 用了默认 `repeat_penalty 1.1`，分数会被推离 0，考卷数字不可比
（见下方排查第 0 条）。

注意合格带下限离「根本没在评分」并不远：在 v9 标签上，一个永远输出 0.5 的部署维度级就有 84.9%，且各维都
≥75%；全输出 0 为 75.9%。所以 `run_exam.py` 会同时打印这两个平凡基线，以及不同读数的种类数（正确部署的模型
在全卷上有几十种）；若它提示读数寥寥无几，先查 GGUF、聊天模板、服务端是否采纳请求参数，再看一致率。

Reference measured on v9 bf16 weights (MLX, M1 Pro, temperature 0, no repeat penalty). The
shipped v9 q8_0 GGUF, run through llama.cpp with the Modelfile template and neutral sampling
(temperature 0, top_k 0, top_p 1.0, repeat_penalty 1.0), scored JSON 100%, 89.3% dim-level
(A 92 · W 80 · E 87 · H 92 · B 96) and gate 10/10 — inside the band. A q8 GGUF deployment via
ollama should land inside the band too; small drift comes from quantization and sampler
differences. If your ollama runs with its default `repeat_penalty 1.1`, scores are pushed away
from zero and the numbers are not comparable (see check 0 below). Latency (v9 bf16 P50 0.57 s on
M1 Pro, on this exam) depends entirely on your hardware and is not part of the band.

Note how close the band's floor is to a deployment that is not scoring at all: on the v9 labels,
a constant 0.5 output already reaches 84.9% dimension-level, with every dimension ≥ 75%; all
zeros reaches 75.9%. That is why `run_exam.py` also prints these trivial baselines and the number
of distinct read-outs (a correctly served model produces several dozen on the full exam). If it
warns of only a handful, check the GGUF, the chat template and that your server honours request
options before trusting the agreement number.

### 考卷怎么重标的 · How the exam was re-labelled

v9 改变了五路分数中两路的含义：A 按口径 v8（主动推动处境或疗愈关系向前，不含情绪调节），B 按 crisp 口径
（只算边界标记——说出的需要、界限、条件或立场）。旧标签按旧口径打，拿它考 v9，量出的只是口径移动了多远。
所以 2026-09-29 我们用 v9 训练标签所用的**同一套已过资格考的教师提示词**（deepseek-chat，温度 0；A 为口径 v8
加告别规则，B 为 crisp）重打了 A、B 两列；W/E/H 一字未动；旧标签逐题保留在 `labels_pre_v9`。A 标签均值
0.48 → 0.42，B 1.14 → 0.44；A 有 39/195 题变动超过 0.5，B 有 79/195 题。

v9 changed what two of the five scores mean: A follows rubric v8 (actively moving the situation
or the helping relationship forward, not regulating one's own emotions) and B the crisp rubric
(only boundary markers count — a stated need, limit, condition or position). Old-rubric labels
would only measure how far the rubric moved. So on 2026-09-29 we re-labelled the A and B columns
with **the same qualified teacher prompts used for v9's training labels** (deepseek-chat,
temperature 0; A rubric v8 with the farewell rule, crisp B). W/E/H are untouched, and every
question keeps its previous labels in `labels_pre_v9`. Mean A label 0.48 → 0.42, mean B
1.14 → 0.44; A moved by more than 0.5 on 39/195 questions, B on 79/195.

### 为什么 B 一致率这么高 · Why B agreement is so high

crisp 口径下大多数 B 标签是 0（195 题中 154 题，重标前为 60 题），而 v9 也大多输出 0——B 的 96% 有一部分是
基础比例，不是判别力。更根本的是：标签出自与 v9 训练标签相同的教师提示词，这份考卷**按构造就与 v9 同分布**。
所以它认证的是你的**接线**（提示词、模板、采样、解析器），不是模型质量：88.9% 不要当成准确率引用，
也不要拿它和 v7 比高低。

Under crisp B most labels are 0 (154 of the 195, against 60 before the re-label) and v9 mostly
outputs 0, so B's 96% is partly base rate, not discrimination. More fundamentally, the labels
come from the same teacher prompts as v9's training labels, so this exam is **in-distribution for
v9 by construction**. It certifies your **wiring** (prompt, template, sampling, parser), not model
quality: do not cite 88.9% as accuracy, and do not use it to rank v9 against v7.

### 自检通过 ≠ 模型通过验收 · Passing this exam is not model acceptance

v9 **没有通过它自己预注册的五道验收闸门中的两道**（五道须全过，按预注册规则 v9 应被拒收）：闸门 4（真实终评上
W/E/H 各自不得低于 v7 最后三个检查点中的最低值 86.8 / 84.8 / 93.8——受检 bf16 的 H 为 93.6，差一题；随包 q8
恰好达标）与闸门 5，**一道安全闸门**：W 安全卷要求 ≥95%，受检 bf16 为 78.9%（71/90）、
随包 q8 为 82.2%（74/90）——来访者表达自杀意念、同时又在求助时，W 会被打低（随包 q8 在这类题上只有 29/45
达到 W ≥2.5）。v9 成为默认权重，是 Hamo 创始人明确作出并留档的破例决定。本考卷评分区没有危机格子，碰不到
这个缺口；完整成绩与破例理由见[模型卡](https://huggingface.co/HamoAI/hamo-score-0.6b)。无论哪个版本，
面向消费者的心理健康部署都必须在模型上游用独立机制处理危机与自伤内容（许可证 §3(c)）；我们建议用确定性的，
比如工具包的 `CrisisGate`。

v9 **did not pass two of its own five pre-registered acceptance gates** (all five had to pass; by
the pre-registered rule v9 is rejected): gate 4 (W/E/H on the real final exam must each reach the
lowest of v7's last three checkpoints, 86.8 / 84.8 / 93.8 — the gated bf16 reached H 93.6, one
item short; the shipped q8 meets it exactly) and gate 5, **a safety gate**: the W safety exam requires ≥ 95%, and
v9 scored 78.9% (71/90) gated bf16 and 82.2% (74/90) shipped q8 — it under-scores withdrawal when
suicidal ideation arrives together with help-seeking (the shipped q8 keeps W ≥ 2.5 on only 29/45
such items). v9 is the default by an explicit, recorded override by Hamo's founder. This exam's
scoring section has no crisis cells and cannot see that gap; the full results and the reason for
the override are on the [model card](https://huggingface.co/HamoAI/hamo-score-0.6b). Whatever the
version, a consumer-facing mental-wellness deployment must handle crisis and self-harm content
with an independent mechanism upstream of the model (license §3(c)); we recommend a deterministic
one such as the toolkit's `CrisisGate`.

### 阈值要重调 · Re-tune your thresholds

A、B 跨 v7 → v9 不可比。两者在压力公式里都是负权重，而 v9 把两者都打得更低（模型卡：真实终评上 v9 平均
A 0.45、平均 B 0.08，v7 为 0.67 与 0.92），同一段对话在 v9 下算出的压力更高。工具包的压力权重与分桶阈值
没有改，是按 v9 之前的分数定的——在让分桶把关任何事之前，先用你自己的数据重调。本考卷只验证接线，
不替你校准阈值。

A and B are not comparable across the v7 → v9 boundary. Both carry negative weights in the stress
formula and v9 scores both lower (model card, real final exam: v9 mean A 0.45 and mean B 0.08,
against 0.67 and 0.92 for v7), so the same conversation computes higher stress under v9. The
toolkit's stress weights and bucket cut-offs are unchanged and were set on pre-v9 scores —
re-tune them on your own data before letting buckets gate anything. This exam checks wiring; it
does not calibrate thresholds for you.

### 交叉读数与判卷脚本校验 · Cross numbers and harness check

| 维度级 Dim-level | `labels`（v9 口径 · v9 rubrics） | `labels_pre_v9`（旧口径 · old rubrics） |
|---|---|---|
| v9 bf16 | **88.9%** | 79.4% |
| v9 q8_0 | **89.3%** | 79.7% |
| v7 bf16 | 80.1% | **83.5%** |
| v7 q8_0 | 80.2% | **83.8%** |

判卷逻辑没变（0.2.0 只加了选择标签集的 `--labels` 开关）：v7 bf16 在 `labels_pre_v9` 上复现了此前发布的参考值，逐维一致（83.5%，
A 85 · W 79 · E 82 · H 92 · B 79）——所以参考值从 83.5% 变成 88.9%，来自新标签与新模型，不来自判卷脚本。
每个模型都在「自己那套口径」的标签上得分最高，这正说明这份考卷量的是口径是否一致，不是哪个模型更好。
模型卡为 v9 在本考卷上给出的「79.7%」，就是右列 v9 q8_0 那一格（旧标签）。

The grading logic is unchanged (0.2.0 only adds the `--labels` switch): v7 bf16 on
`labels_pre_v9` reproduces the previously published reference exactly, dimension by dimension (83.5%, A 85 · W 79 · E 82 · H 92 · B 79) — so the move
from 83.5% to 88.9% comes from the new labels and the new model, not from the harness. Each model
scores highest on the labels of its own rubric, which is exactly why this exam measures rubric
agreement, not which model is better. The 79.7% the model card gives for v9 on this exam is the
v9 q8_0 cell in the right-hand column (old labels).

### 部署的是 v7？· Deploying v7?

回退或有意继续用 v7（模型仓库里的 `gguf/hamo-score-0.6b-v7.q8.gguf`，或 safetensors 固定版本
`ab9dc70c5c25be0eb47cd9a7bf7c70c094b4fb93`）时，请用 `--labels pre_v9` 对照旧标签：v7 参考值 83.5%（bf16）/
83.8%（q8），合格带沿用此前的 81–86%、各维 ≥75%、JSON ≥99%、闸门 10/10。拿 v7 去考新标签会得到约 80%，
低于 v9 合格带——那是口径差，不是接线错。

If you roll back to or deliberately stay on v7 (`gguf/hamo-score-0.6b-v7.q8.gguf` in the model
repository, or the safetensors at revision `ab9dc70c5c25be0eb47cd9a7bf7c70c094b4fb93`), grade
against the old labels with `--labels pre_v9`: the v7 reference is 83.5% (bf16) / 83.8% (q8), and
the band stays the previous one — 81–86%, each dimension ≥ 75%, JSON ≥ 99%, gate 10/10. v7 graded
against the new labels reads about 80%, below the v9 band — a rubric difference, not a wiring
fault.

```bash
python eval/run_exam.py --model my-v7-tag --labels pre_v9
```

## 量化档位怎么选 · Choosing a quantization

**下表每个数字都来自 v7 权重；v9 我们只量过随包的 Q8_0**（即上文随包 q8 的 89.3% 实测，以及模型卡闸门表的 q8 列）。v9 的
Q6_K / Q4_K_M 既没有发布、也没有量过——自己量化出来的档位，先跑 `compare_quants.py` 再让它门控任何东西。
社区（mradermacher，感谢）提供了 Q2_K→f16 共 12 个静态 GGUF 档，但它们是 2026-08-05 由 **v4 权重**制作的，
比 v9 早三个发布版本，早于 v9 的 A/B 口径与 W 安全修复，也从未经过验证（我们唯一一次跑它们，就是下文已作废的
那张对比，基线用错了版本）——已经过时，不在下面任何建议范围内。

下表：Q8_0 即我们发布的 v7 GGUF（仍保留在模型仓库）；Q6_K 与 Q4_K_M 由我们用 llama.cpp 从 v7 f16 GGUF
自行量化，**未在任何地方发布**。测于内部 453 题终评集（真实假名化对话，不公开），同一提示词、同一解析器；
bf16 经 MLX（温度 0），各 GGUF 档经 llama.cpp 中性采样：

**Every number in the table below comes from v7 weights; on v9 we have measured only the shipped
Q8_0** (the 89.3% q8 reading above, and the q8 column of the model card's gate table). No v9 Q6_K or Q4_K_M is
published or measured — if you build one, run `compare_quants.py` before letting it gate
anything. The community builds by
[mradermacher](https://huggingface.co/mradermacher/hamo-score-0.6b-GGUF) (twelve static quants,
Q2_K→f16 — thank you) were made on 2026-08-05 from the **v4 weights**, three releases before v9:
they predate v9's A and B rubrics and its W safety repair, have never been validated (the only
time we ran them was the superseded comparison below, against a mismatched v6.1 baseline), and
are outdated and not covered by any recommendation below.

In the table, Q8_0 is the v7 GGUF (still in the model repository); Q6_K and Q4_K_M were quantized
by us with llama.cpp from a v7 f16 GGUF and are **not published anywhere**. Measured on our
internal 453-turn final exam (real, pseudonymised, not public) with the same prompt and parser;
bf16 via MLX (temperature 0), the GGUF builds via llama.cpp with neutral sampling:

| v7 权重 · v7 weights | bf16 (MLX) | Q8_0 | Q6_K | Q4_K_M |
|---|---|---|---|---|
| 维度级 ±0.5 Dim-level | 85.1% | 85.3% | 85.3% | 84.5% |
| 决策级（状态桶）Decision-level | 97.1% | 97.1% | 96.9% | 96.7% |
| 危机 W 漏检 Crisis W-misses（金标 gold W≥2.5 → pred <0.5, n=37） | 3 | 3 | 3 | 3 |
| 危机子集 W 均值 Mean W on those 37 turns（金标 gold 2.84） | 2.58 | 2.58 | 2.58 | **2.50** |
| 这 37 条上比 Q8_0 更低/更高 W lower / higher than Q8_0 on those 37 | 0 / 0 | — | 1 / 1 | **6 / 1** |
| 全部 453 条相对 Q8_0 的平均分偏移 Mean score shift vs Q8_0 (all 453) | ≈0 | — | 各维均在 ±0.011 内 every dim within ±0.011 | A −0.05 · W −0.03 · E −0.01 · H +0.00 · B +0.00 |
| 体积 Size | — | 0.64 GB | 0.50 GB | 0.40 GB |
| 延迟 P50 latency（453 题终评集 453-turn split；M1 Pro, Metal, llama.cpp） | 0.83 s (MLX) | 0.70 s | 0.56 s | 0.54 s |

**读法 Reading**：在 v7 上，Q6_K 在这份考卷上与 Q8_0 无法区分；Q4_K_M 相对 Q8_0 维度级掉 0.8 个百分点、
决策级掉 0.4 个百分点，并且在危机相邻子集上仍然单边衰减（6 条更低 vs 1 条更高，W 均值
2.58 → 2.50），但这次没有多出危机漏检。v9 的 W 安全缺口（闸门 5）只会让这条提醒更重要，而不是更不重要。

On v7, Q6_K is indistinguishable from Q8_0 on this exam; against Q8_0, Q4_K_M loses 0.8 pt
dim-level and 0.4 pt decision-level and still attenuates one-sidedly on the crisis-adjacent subset
(6 lower vs 1 higher, mean W 2.58 → 2.50), but did not add a crisis miss here. v9's W-safety gap
(gate 5) makes this caution stronger, not weaker.

**更正 · Correction**：本节更早发布的对比（Q6_K 维度级低约 1 个点、Q4_K_M 在 37 条危机相邻样本中
20 条低于 Q8_0、漏检 5 条）拿的是 v6.1 的 Q8_0 去比由 v4 权重制作的社区档——差距主要是版本差，
不是量化差。那张表已作废，以上表为准。

An earlier comparison published here (Q6_K ~1 point lower, Q4_K_M lower than Q8_0 on 20 of 37
crisis-adjacent turns with 5 misses) compared a v6.1 Q8_0 against community builds made from v4
weights, so the gap was mostly a version gap, not a quantization gap. It is superseded by the table
above.

**建议 Recommendation**：门控行为的部署用 **Q8_0**（我们发布的档，v9 与 v7 都有）。**Q6_K** 只在 v7 上验证过
（与 Q8_0 包括危机相邻子集都分不出差别）；v9 的 Q6_K 是合理的猜测但未经实测，自己量化后先跑
`compare_quants.py` 再让它门控任何东西。**Q4_K_M** 只在 v7 上量过，当时适合研究/离线/由人来读分数的场景；
我们不发布 v9 的 Q4_K_M——若被迫用于门控，考虑下调退缩阈值补偿。无论哪个档位，面向消费者的部署都必须在上游
用独立机制处理危机与自伤内容（许可证 §3(c)），我们建议用确定性闸门。v7 上低于 Q4_K_M 的档位没有量过，v9 上只量过 Q8_0；社区各档（v4 权重）
同样未验证。未量过的一律默认更差。

Use **Q8_0** (the shipped build, for v9 and v7) where read-outs gate behaviour. **Q6_K** is
validated on v7 only, where it was indistinguishable from Q8_0 including the crisis-adjacent
subset; a v9 Q6_K is a reasonable guess but unmeasured — if you build one, run `compare_quants.py`
before letting it gate anything. **Q4_K_M** was measured on v7 only, where it suited research,
offline and human-read scores; we publish no v9 Q4_K_M, and if one is forced into gating, consider
compensating the withdrawal threshold. At any quantization, a consumer-facing deployment must
handle crisis and self-harm content with an independent mechanism upstream (license §3(c)); we
recommend a deterministic gate. On v7 we did not measure builds below Q4_K_M; on v9 we
have measured only Q8_0; the community builds (v4 weights) are unvalidated too. Assume anything
unmeasured is worse.

**想要 v9 的 Q6_K / Q4_K_M？只能自己量化，并且先量再用 · Want a v9 Q6_K / Q4_K_M? Quantize it yourself — and measure it before use**
（社区档是 v4，我们没有发布低比特档 · the community builds are v4 and we publish no low-bit build）：

```bash
# 1. 已发布的权重（HF 格式；main 即 v9，v7 在固定版本 ab9dc70c…）→ f16 GGUF
#    released weights (HF format; main is v9, v7 is at revision ab9dc70c…) → f16 GGUF
python llama.cpp/convert_hf_to_gguf.py <v9-weights-dir> --outtype f16 --outfile hamo-score-0.6b-v9.f16.gguf
# 2. f16 → 目标档位 · f16 → target quant（Q6_K 或 or Q4_K_M）
llama-quantize hamo-score-0.6b-v9.f16.gguf hamo-score-0.6b-v9.q6_k.gguf Q6_K
# 3. 与 Q8_0 对比后再用（见下）· compare against Q8_0 before use (below)
```

**方法论上更重要的一点 · The methodological point**（在 v7 上可见）：Q8_0 → Q4_K_M 的桶一致率
只差 0.4 个百分点（97.1% → 96.7%），但底下 Q4_K_M 在 37 条危机相邻样本上有 6 条比 Q8_0 打得更低、
仅 1 条更高——**桶的边界粗到足以吸收一个被压扁的信号，只看一致率永远发现不了这件事。** 所以本目录
提供了 `compare_quants.py`：它跑本仓库的合成考卷（零真实数据），除了各档一致率，还输出**方向性衰减
表**——每个维度「更低/更高」的条数分布，以及高退缩子集（教师 W ≥1.5）上的同一分布。单边分布就是结论。
各档一致率默认对照 v9 标签；比较 v7 各档时加 `--labels pre_v9`。只比较同一版本的档位——拿 v7 档去比 v9 档，
量出的是版本差（上面那条更正就是前车之鉴）。

Visible on v7: bucket agreement moved only 0.4 points from Q8_0 to Q4_K_M (97.1% → 96.7%),
while underneath, Q4_K_M scored W lower than Q8_0 on 6 of 37 crisis-adjacent turns and higher on
exactly 1. **Buckets are coarse enough to absorb a damped signal — agreement alone will never
surface it.** Hence `compare_quants.py` in this directory: it runs the synthetic exam (no real
data) across builds and prints a **directional attenuation table** — lower/higher counts per
dimension, and the same split restricted to high-withdrawal turns (teacher W ≥ 1.5). A one-sided
split is the finding. Per-build agreement is graded against the v9 labels by default; pass
`--labels pre_v9` when comparing v7 builds. Compare builds of the same version only — a v7 build
against a v9 build measures a version gap (the correction above is the cautionary tale).

```bash
# 仓库只带 server/Modelfile：每个档位复制一份，只改 FROM 行
# The repo ships only server/Modelfile: copy it per build and change only the FROM line
cp server/Modelfile Modelfile.q4                 # then edit FROM → your ...v9.q4_k_m.gguf
ollama create hamo-q8 -f server/Modelfile        # FROM: the shipped v9 q8_0 GGUF
ollama create hamo-q4 -f Modelfile.q4
python eval/compare_quants.py --models hamo-q8 hamo-q4
```

## 数字不对时 · If your numbers are off

大幅偏离合格带几乎总是接线问题，不是模型问题，按序排查：

0. **先查采样参数**（最常见、最隐蔽）：`ollama show <model> --parameters` 必须看到
   `repeat_penalty 1`。ollama 默认 1.1，会惩罚本模型输出里重复的 `0.0`，把分数系统性推离 0。
   随包 v9 q8 GGUF 在模型卡的 crisp B 卷上（B 维，不在本仓库；该卷与 v9 的训练补丁同分布）实测：造分率
   1.9% → 2.8%；漏判率 6.1% → 3.1% 的「下降」是同一股上推，不是改进；符号翻转 0 → 0、配对方向正确率
   100% → 100% 纹丝不动——只看这两个数永远发现不了。影响比旧版本小（v7 在 v7 时代的边界判别卷上：造分率
   2.9% → 8.7%、符号翻转 0 → 1；v6.1：13.5% → 25.0%、6 → 10），但方向相同，三个参数仍是必需的。本考卷
   195 题中 154 题的 B 标签是 0，这些题上任何被推到 0.5 以上的分数都直接记为不一致。
1. **维度级约 80%，JSON 与闸门区都正常** → 多半是权重与标签套错了：要么在用 v9 之前的权重（v7 或更早，
   包括社区的 v4 档）考 v9 标签——v7 在新标签上正是约 80%；要么反过来，用 v9 权重加了 `--labels pre_v9`
   ——v9 在旧标签上是 79.4%（bf16）/ 79.7%（q8）（见上方交叉读数）。更早的版本没有在新标签上跑过，它们同样
   按旧口径打 A、B。检查 Modelfile 的 `FROM` 指向哪个 GGUF、服务实际调用哪个模型标签、命令行带没带
   `--labels`：v7 配 `--labels pre_v9`，v9 用默认标签。
2. **JSON 合法率 < 99%** → 提示词模板错了。检查 Modelfile/template 是否带空 `<think>` 块
   （见 `server/docker-compose.yml`），temperature 是否为 0。
3. **维度级明显低于合格带下限 86%，且不是第 1 条的情况** → 大概率没用 `build_prompt()`（自造提示词），
   或用了未经测量的量化档（v9 只量过 Q8_0）。
4. **闸门区 ≠ 10/10** → 你改动或绕过了 `CrisisGate`。这是许可证 §3(c) 的红线，修复后再上线。

Check sampling first: `ollama show <model> --parameters` must show `repeat_penalty 1`. ollama's
default 1.1 penalises the repeated `0.0` in this model's output and pushes scores away from zero.
On the shipped v9 q8 GGUF, measured on the model card's crisp B exam (B dimension; not shipped
here; in-distribution for v9's training patches), fabrication goes 1.9% → 2.8%, the lower miss
rate (6.1% → 3.1%) is the same upward push rather than an improvement, and sign flips (0 → 0) and
paired direction (100% → 100%) do not move at all — so those two numbers alone would never reveal
it. The effect is smaller than on older builds (v7 on the v7-era boundary exam: fabrication
2.9% → 8.7%, sign flips 0 → 1; v6.1: 13.5% → 25.0%, 6 → 10) but points the same way, so the three
parameters remain mandatory. On this exam 154 of the 195 B labels are 0, and any of those pushed
above 0.5 counts directly as a disagreement.

Dim-level around 80% with JSON and the gate section fine usually means weights and labels are
mismatched: either pre-v9 weights (v7 or older, including the v4 community builds) graded against
the v9 labels — v7 reads about 80% there — or the reverse, v9 weights graded with
`--labels pre_v9`, which reads 79.4% (bf16) / 79.7% (q8) (cross numbers above). Older versions
have not been run against the new labels, and they too score A and B on the old rubrics. Check
which GGUF your Modelfile's `FROM` points to, which model tag your service actually calls, and
whether you passed `--labels`: v7 goes with `--labels pre_v9`, v9 with the default.

Other big deviations are almost always wiring, not the model. JSON validity below 99% means a
broken template (check the empty `<think>` block and temperature 0). Dim-level clearly below the
band's floor of 86%, when it is not the ~80% case above, usually means a hand-rolled prompt
instead of `build_prompt()` or an unmeasured quantization (on v9 only Q8_0 has been measured). A
gate section below 10/10 means the `CrisisGate` was altered or bypassed — that's the license
§3(c) red line; fix before going live.
