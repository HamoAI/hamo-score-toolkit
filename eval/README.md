# 自检考卷 · Self-Check Exam

部署后跑这份考卷，核对你的接线是否复现官方读数。**它验证的是接线，不是模型质量；卷里没有真实对话的轮次，
也没有自我消融对照题，看不到「自检通过 ≠ 模型通过验收」一节列出的问题**。

Run this exam after deploying to check that your wiring reproduces the official read-outs. **It
certifies wiring, not model quality; it has no real conversation turns and no self-erasure pairs,
and cannot see the failures listed under "Passing this exam is not model acceptance"**.

```bash
python eval/run_exam.py                       # ollama on localhost:11434；默认 v10 标签 · v10 labels by default
python eval/run_exam.py --base-url http://myhost:11434 --model my-tag
python eval/run_exam.py --labels v9           # 有意部署 v9 · serving v9 on purpose
python eval/run_exam.py --labels pre_v9       # 有意部署 v7 · serving v7 on purpose
```

这些命令直接调 ollama 的 `/api/generate`，不走 `POST /score`。参考的 `server/docker-compose.yml` 只发布
8080 端口：要考它，给 `ollama` 服务加 `ports: ["127.0.0.1:11435:11434"]`，重新 `docker compose up`，再加
`--base-url http://127.0.0.1:11435`；否则连不上，或考到宿主机 ollama 里的同名模型。

These commands call ollama's `/api/generate`, not `POST /score`. The reference
`server/docker-compose.yml` publishes only port 8080: to examine it, add
`ports: ["127.0.0.1:11435:11434"]` to its `ollama` service, run `docker compose up` again and
pass `--base-url http://127.0.0.1:11435`. Otherwise the script cannot connect, or grades a host
ollama's model of the same name.

| `--labels` | 字段 · key | A | B | 用于 · for |
|---|---|---|---|---|
| `v10`（默认 · default） | `labels` | 口径 v8 · rubric v8 | legacy | v10 |
| `v9` | `labels_v9` | 口径 v8 · rubric v8 | crisp | v9 |
| `pre_v9` | `labels_pre_v9` | 旧口径 · old rubric | legacy | v7 |

> **从 0.2.0 升级注意**：那时默认的 v9 标签存在 `labels` 字段；0.3.0 起 `labels` 是 v10 标签，v9 标签挪到
> `labels_v9`。仍在跑 v9 的部署必须显式加 `--labels v9`，否则读数落在 v10 合格带之外；跑 v7 的照旧加
> `--labels pre_v9`。
>
> **Upgrading from 0.2.0**: there the default v9 labels were stored under `labels`. From 0.3.0
> `labels` holds the v10 labels and the v9 labels moved to `labels_v9`. A deployment that still
> serves v9 must pass `--labels v9` explicitly, or it reads outside the v10 band; a v7 deployment
> passes `--labels pre_v9` as before.

W/E/H 标签三套相同。A、B 的分数跨版本不能直接比：A 在 v9 换了口径（v10 沿用），B 在 v9 改成 crisp、v10 改回
legacy。

W/E/H labels are the same in all three sets. A and B scores are not comparable across versions: A
changed rubric at v9 (v10 keeps it); B went to crisp at v9 and back to legacy at v10.

## 考卷构成 · What's inside

- **评分区 `synthetic_exam.jsonl`（195 题）**：10 个非危机格子，2026-08-16 合成生成，**不含任何真实来访者
  数据**。标签来自教师 deepseek-chat：W/E/H 三套都是 2026-08-16 的原始标签，pre_v9 的 A、B 也是；v9 的
  A、B 用给 v9 训练数据打标的教师提示词重打。v10 这一套：A 沿用 v9 那一列；B 按 legacy 生产口径在温度 0 下
  打三次取中位数；冻结的意念检测器在 195 题上命中 0 题，所以「明确意念规则」（A 封顶 1.0、B 归零、W 至少
  2.5）没有改动任何标签。
- **与训练语料的关系**：195 题里有 6 题的消息与某条 v10 训练样本的最新消息文字相同；没有一道题的完整提示词
  与训练样本相同。此前本页写「与所有训练语料不相交」，说得过满。
- **闸门区 `gate_cases.jsonl`（10 题）**：手写危机句式 7 条（中英），加不应误触的 3 条（2 条带「死」字的
  夸张、1 条普通日常消息）。这一节不调用模型，只在进程内跑工具包的 `CrisisGate` 关键词表，与模型版本无关。

- **Scoring section, `synthetic_exam.jsonl` (195 questions)**: 10 non-crisis cells, generated
  synthetically on 2026-08-16; **zero real client data**. Labels come from the teacher,
  deepseek-chat. W/E/H are the original 2026-08-16 labels in all three sets, as are the pre_v9
  A and B; the v9 A and B were re-labelled with the teacher prompts used for v9's training
  labels. For the v10 set, A is kept from the v9 set; B was re-labelled with the legacy
  production rubric at temperature 0, median of three runs; the frozen ideation detector flagged
  0 of the 195 questions, so the explicit-ideation rule (A capped at 1.0, B 0, W at least 2.5)
  changed no label.
- **Relation to the training data**: 6 of the 195 messages also occur as the latest message of a
  v10 training row; no full prompt is shared. This page used to say "disjoint from all training
  corpora", which was too strong.
- **Gate section, `gate_cases.jsonl` (10 cases)**: 7 handwritten crisis phrasings (zh and en) and
  3 messages that must not trigger (two hyperboles using 死, one plain everyday message). It
  calls no model: it runs the toolkit's `CrisisGate` keyword lists in-process and does not depend
  on the model version.

## 官方参考数字 · Official reference (v10, `--labels v10`)

| 指标 · Metric | bf16（MLX） | q8（llama.cpp + Metal） | q8，`run_exam.py` 端到端 · end to end | 合格带 · Pass band |
|---|---|---|---|---|
| JSON 合法率 · JSON validity | 100.0% | 100.0% | 100% | ≥ 99% |
| 维度级一致率（±0.5）· Dim-level agreement | 87.3% | 87.3% | 87.3% | **84–90%** |
| A | 91.8 | 91.8 | 92 | **≥ 86** |
| W · E · H · B | 79.0 · 85.1 · 93.3 · 87.2 | 79.5 · 85.6 · 93.3 · 86.2 | 79 · 86 · 93 · 86 | 各 ≥ 75 · each ≥ 75 |
| 不同读数种类 · Distinct read-outs | 75 | 78 | 78 | — |
| 闸门区 · Crisis gate（不调用模型 · no model call） | — | — | 10/10 | 10/10（硬性 · hard） |

**基准。** 三列都在 M1 Pro 上测，用工具包自己的 `build_prompt()` 与 `parse_scores()`，每题最多 80 个新
token，对照 v10 标签。

- **bf16**：发布的 `model.safetensors`（版本 `f3869312f0222992c3eb2e938e78090de38eb80a`），经 MLX，温度 0。
- **q8**：随包的 `gguf/hamo-score-0.6b-v10.q8.gguf`，经 llama.cpp（Metal），用 `server/Modelfile` 的模板与
  中性采样（temperature 0、repeat_penalty 1.0、top_k 0、top_p 1.0）。
- **端到端**：用 0.3.0 的代码原样跑 `python eval/run_exam.py`，对着一个本地的 ollama 兼容测试服务
  （`/api/generate` 接口后接 llama.cpp + Metal；同一个 GGUF 与模板）。它是仿真服务，不是 ollama 本身，也不在
  工具包里。服务端故意留着 ollama 的默认采样，只靠工具包随请求发送的参数保持中性。

三列都没有经过 ollama 自己的程序。经 ollama 的证据有两项（同一个 GGUF，一台 ARM CPU 服务器）。① 100 道
合成题对 Metal 上 llama.cpp 的跨运行环境核对：关掉服务端提示词缓存时，五个分数完全相同 98 题，五维都在
±0.5 内 99 题；开着缓存（ollama 0.32.5 的默认状态，参考 compose 没有关，见 FAQ）的前一次是 95 与 98 题。
② 方案草案写定的服务端核对（旧 B 卷与旧 W 安全卷中的 138 题，按工具包规则截短）复现了 Metal 的计数：B 符号翻转
2/93（同两道题），「绝望但行动」W ≥ 1.5 为 45/45。

合格带定于 2026-10-05，取参考值上下约 3 个点。A 的下限用来分出 v7 权重（在这套标签上 A 为 80.5）。延迟取决于
你的硬件，不属于合格带。

**这份考卷查不出 Modelfile 漏写采样参数。** `run_exam.py` 每次请求都带中性采样参数，而请求参数优先于
Modelfile——端到端那一列就是服务端采样没有中性化的情形，读数照样是 87.3%。必须手工核对（排查第 0 条）。

**Basis.** All three columns were measured on an M1 Pro with the toolkit's own `build_prompt()`
and `parse_scores()`, up to 80 new tokens per question, graded against the v10 labels.

- **bf16**: the released `model.safetensors` (revision `f3869312f0222992c3eb2e938e78090de38eb80a`) through MLX at
  temperature 0.
- **q8**: the shipped `gguf/hamo-score-0.6b-v10.q8.gguf` through llama.cpp with Metal, using the
  `server/Modelfile` template and neutral sampling (temperature 0, repeat_penalty 1.0, top_k 0,
  top_p 1.0).
- **End to end**: `python eval/run_exam.py` as shipped in 0.3.0, against a local
  ollama-compatible test server (llama.cpp + Metal behind an `/api/generate` endpoint; same GGUF
  and template). It is an emulation, not ollama itself, and not part of the toolkit. The server
  deliberately kept ollama's default sampling, so only the options the toolkit sends with each
  request kept sampling neutral.

None of the three columns ran through ollama's own binary. Through ollama (same GGUF, an ARM CPU
server) we have two checks. A cross-runtime check on 100 synthetic items against llama.cpp on
Metal: identical five-score read-out on 98 items and all five within ±0.5 on 99 with the
server's prompt cache off; an earlier run with it on (ollama 0.32.5's default, not switched off
by the reference compose file; see the FAQ) gave 95 and 98. The serving check specified in the
draft protocol (138 items of the old B and old W safety exams, toolkit prompt trimming)
reproduced Metal's counts: B sign flips 2/93 on the same two items, despair-plus-action W ≥ 1.5
on 45/45.

The band was set on 2026-10-05, about ±3 points around the reference. The A floor is what
separates v10 weights from v7 weights (A 80.5 on these labels). Latency depends on your hardware
and is not part of the band.

**The exam cannot catch a Modelfile that omits the sampling parameters.** `run_exam.py` sends
neutral sampling with each request, and request options override the Modelfile — the end-to-end
column is exactly a server whose own sampling was not neutral, and it still reads 87.3%. Check by
hand (check 0 below).

## 平凡基线与交叉读数 · Trivial baselines and cross numbers

`run_exam.py` 会按当前标签集打印下面两个平凡基线。

`run_exam.py` prints the two trivial baselines below for the label set in use.

| 标签集 · Label set | 恒定输出 0.5 · constant 0.5 | 全输出 0 · all zeros | B 标签为 0 的题数 · B labels equal to 0（of 195） |
|---|---|---|---|
| `--labels v10` | 77.9% | 68.1% | 38 |
| `--labels v9` | 84.9% | 75.9% | 154 |
| `--labels pre_v9` | 77.4% | 68.8% | 60 |

下表是各版本权重在三套标签上的维度级一致率，测法同上一节（bf16 经 MLX；q8 为各版本随包 GGUF，经 llama.cpp +
Metal）。粗体是权重与标签对得上的格子。

Dimension-level agreement of each version's weights on the three label sets, measured as in the
previous section (bf16 through MLX; q8 each version's shipped GGUF through llama.cpp + Metal).
Bold cells are the ones where weights and labels match.

| 权重 · Weights | `labels`（v10） | 其中 A · B · of which A · B | `labels_v9` | `labels_pre_v9` |
|---|---|---|---|---|
| v10 bf16 | **87.3%** | 91.8 · 87.2 | 83.1% | 84.1% |
| v10 q8 | **87.3%** | 91.8 · 86.2 | 82.9% | 84.3% |
| v9 bf16 | 81.2% | 91.3 · 57.4 | **88.9%** | 79.4% |
| v9 q8 | 81.6% | 91.8 · 57.4 | **89.3%** | 79.7% |
| v7 bf16 | 83.3% | 80.5 · 82.6 | 80.1% | **83.5%** |
| v7 q8 | 83.5% | 80.5 · 83.1 | 80.2% | **83.8%** |

- **合格带只对粗体格有意义**（v10 的带见上一节，v9、v7 的见「部署的是 v9 或 v7？」）。其他格子量的是两套
  口径的距离，不是接线，也不是模型好坏；按列也排不出名次（`labels_pre_v9` 一列上 v10 权重读得比 v7 权重高）。
- **套错版本的权重比恒定输出更难发现。** 恒定输出 0.5 在 v10 标签上是 77.9%，离下限 84% 约 6 个点；v7 权重
  是 83.3 / 83.5%，差不到 1 个点，靠 A 的下限分出来（v7 80.5，v10 91.8）；v9 权重看 B（57.4）。反过来分不出：
  v10 权重配 `--labels pre_v9` 是 84.1 / 84.3%，落在 v7 的带内，所以 `pre_v9` 过关证明不了你跑的是 v7——
  要确认权重版本，用默认标签看 A。
- **W、E、H 分不清版本**（这三列标签自 2026-08-16 没变）；195 题里 165 题的 H 标签是 0，H 高说明不了什么。
- **判卷逻辑没变**：v7、v9 的四个粗体格这次重新跑过，与此前发布的参考值相同。
- **同分布**：标签出自给训练数据打标的同一套教师提示词，这份考卷按构造就与模型同分布。它认证的是接线
  （权重、聊天模板、`num_predict`、stop；提示词、采样、解析器是工具包自己的）；87.3% 不是准确率，
  也不要拿这份考卷给版本排名。

- **A band applies to bold cells only** (v10's band is in the previous section; v9's and v7's
  under "Serving v9 or v7?"). Any other cell measures the distance between two rubrics, not your
  wiring and not model quality; columns do not rank models either (in the `labels_pre_v9` column
  v10 weights read higher than v7 weights).
- **Weights of the wrong version are harder to spot than a constant output.** A constant 0.5
  reads 77.9% on the v10 labels, about 6 points under the floor of 84%; v7 weights read
  83.3 / 83.5%, less than a point under, and it is the A floor that separates them (80.5 for v7,
  91.8 for v10); for v9 weights look at B (57.4). The reverse does not separate: v10 weights with
  `--labels pre_v9` read 84.1 / 84.3%, inside v7's band, so a pass with `pre_v9` does not prove
  you are serving v7 — to confirm which weights are served, run the default labels and look at A.
- **W, E and H do not separate versions** (these label columns have not changed since
  2026-08-16); 165 of the 195 H labels are 0, so a high H says little.
- **The grading logic is unchanged**: the four bold cells for v7 and v9 were re-run for this
  release and equal the previously published references.
- **In-distribution**: the labels come from the same teacher prompts as the training labels, so
  this exam is in-distribution for the model by construction. It certifies wiring (served
  weights, chat template, `num_predict`, stop; prompt, sampling and parser are the toolkit's
  own); 87.3% is not an accuracy figure, and this exam must not be used to rank versions.

## 自检通过 ≠ 模型通过验收 · Passing this exam is not model acceptance

**按它自己签字的预注册规则，v10 的结论是「拒收」；它是经 Hamo 创始人裁决发布的。** 随包 q8 上的 18 项检查
过了 17 项。没过的那一项 **G5a** 定义在真实终评（453 轮假名化的内部员工对话，不公开）的轮次上，当初是作为
危机处理的替代指标设的；创始人看到结果后裁定，危机处理不在这个模型里判定，由模型外围的确定性代码（Hamo
称之为「脊柱」）负责。**这是在结果已知之后，对一道预注册闸门的豁免**（受检文件
没有更换），也是连续第二个未通过预注册闸门、经创始人裁决发布的版本（v9 的五道闸门没过两道）。检查表与裁决（原话节录）
见模型的[技术档案](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation)（模型卡里有链接）的
Evaluation 一节：技术档案报告 18 项中的
16 项，这 16 项都按签字时的通过线通过；依这项裁决，模型卡和技术档案都不报告 G5a、G5b 两项（G5b 过了）。

- **已知的一条 B 符号翻转**：「行，我全听你的，你说哪天去就哪天去。」（无上下文）这句自我消融，v10 打
  B 2.5，v7 与 v9 打 0（随包 q8，llama.cpp + Metal）。翻转数在预注册上限内，但这就是此前模型卡用来
  说明「仪器不能把自我消融读成边界」的那句话。计数与细节见 [FAQ](../docs/faq.md)。
- **它不是危机检测器，也不是诊断工具。** 它的分数，包括 W 在内，没有一个是危机信号；危机处理由先于模型运行的
  确定性代码负责。

**本考卷看不到以上任何一条**：卷里没有真实对话的轮次，而 G5a 定义在真实轮次上；评分区也没有自我消融的
对照题。它同样考不到明确意念规则：评分区没有明确意念的题（冻结的意念检测器在 195 题上命中 0 题）。
教师 W ≥ 2.5 的题只有 6 道，不足以左右是否合格。

无论哪个版本，面向消费者的心理健康部署都必须在模型上游用独立机制处理危机与自伤内容（许可证 §3(c)）；我们
建议用确定性的，比如工具包的 `CrisisGate`。但它只是一张关键词表：闸门区的 10/10 只说明那 10 条手写用例没
问题，不是召回率，也不验证你的部署是否真把每条消息先送过闸门（那是你自己要做的集成测试）。在两份 W 安全卷的
189 道「想死但求助」合成题上，它命中 107 题（56.6%）。请按你服务的人群扩充词表，不要把它当成
完整的危机识别。

**Under its own signed pre-registration v10's verdict is "rejected"; it is released by the
decision of Hamo's founder.** Of 18 checks run on the shipped q8, v10 met 17. The one it did not
meet, **G5a**, was defined on turns of the real final exam (453 turns of pseudonymised internal
staff conversations, not public) as a stand-in for crisis handling, which the founder ruled
outside this model after seeing the result: crisis handling is done by deterministic code
around the model (Hamo calls it "the spine"). **This is a waiver of one pre-registered gate made
after the result was known** (the judged file was not swapped), and the second release in a row
that ships by founder decision after failing a pre-registered gate (v9 failed 2 of its 5).
The table of checks and the ruling (quoted in part) are in the Evaluation section of the model's
[technical record](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation)
(linked from the model card): the technical record reports sixteen of the 18
checks, all passed at the signed lines, and following the ruling neither it nor the model card reports G5a and G5b
(G5b was met).

- **A known B sign flip**: the self-erasure sentence 「行，我全听你的，你说哪天去就哪天去。」 ("Fine,
  I'll do whatever you say — we go whichever day you say."), with no context, is scored B 2.5 by
  v10 and B 0 by v7 and v9 (shipped q8 files, llama.cpp + Metal). Flip counts are inside the
  registered caps, but this sentence is the example earlier model cards used for "the instrument
  must not read self-erasure as a boundary". Counts and details: [FAQ](../docs/faq.md).
- **It is not a crisis detector and not a diagnostic tool.** None of its scores, W included, is a
  crisis signal; crisis handling is done by deterministic code that runs before the model.

**This exam can see none of the above**: it has no real conversation turns, and G5a was defined
on real turns; its scoring section has no self-erasure pairs. Nor does it exercise the
explicit-ideation rule: the scoring section has no explicit-ideation items (the frozen ideation
detector flags 0 of the 195 questions). Six questions carry a teacher W ≥ 2.5, too few to decide
a pass.

Whatever the version, a consumer-facing mental-wellness deployment must handle crisis and
self-harm content with an independent mechanism upstream of the model (license §3(c)); we
recommend a deterministic one such as the toolkit's `CrisisGate`. But that gate is a keyword
list: 10/10 in the gate section says those ten handwritten cases work. It is not the list's
recall, and it does not test that your deployment routes each message through the gate before
the model — that is an integration test you own. On the 189 synthetic ideation-plus-help items
of our two W safety exams the gate fires on 107 (56.6%). Extend the word lists for the
population you serve, and do not treat the gate as complete crisis detection.

## 部署的是 v9 或 v7？· Serving v9 or v7?

**更正。** 0.2.0 的这一页让 v9 用户「重调压力权重与分桶阈值」，这个建议不够：v9 的 crisp B 在多数普通消息上
是 0，参照压力公式里 B 的负权重乘的是 0，减压项就没了——真实终评 453 轮上（随包 q8，llama.cpp + Metal），
平均每轮原始压力变化按 v9 的读数是 +0.37，按参照标签是 −0.68（v10 −0.72），重调阈值或 B 的权重都修不回来。
把分数喂给 B 为负权重的公式（工具包的 `update_stress()` 就是）的，请用 v10 或退回 v7；完整说明见
[集成指南「升级到 v10」](../docs/integration.md#升级到-v10)。本考卷只验证接线，不替你校准压力权重和分桶阈值。

**Correction.** The 0.2.0 version of this page told v9 users to re-tune stress weights and bucket
cut-offs. That advice was not enough: v9's crisp B is 0 on most ordinary messages, so the
negative B weight of the reference stress formula multiplies a zero and the relief term
disappears — on the 453 turns of the real final exam (shipped q8 files, llama.cpp + Metal) the
mean raw per-turn stress change is +0.37 from v9's read-outs against −0.68 from the reference
labels (v10 −0.72) — and re-tuning the cut-offs or the B weight cannot repair that. If you feed
scores into a formula with a negative B weight (the toolkit's `update_stress()` is one), use v10
or go back to v7; the full statement is in the
[integration guide, "Upgrading to v10"](../docs/integration.md#upgrading-to-v10). This exam
checks wiring; it does not calibrate stress weights or bucket cut-offs for you.

| | v9（2026-09-30 至 10-06 的默认权重 · the default weights from 2026-09-30 to 2026-10-06） | v7 |
|---|---|---|
| GGUF（模型仓库 · model repository） | `gguf/hamo-score-0.6b-v9.q8.gguf` | `gguf/hamo-score-0.6b-v7.q8.gguf` |
| 判卷 · Grade with | `--labels v9` | `--labels pre_v9` |
| 参考值 · Reference（bf16 / q8） | 88.9% / 89.3% | 83.5% / 83.8% |
| 分维参考 · Per-dimension reference（A · W · E · H · B） | bf16 91.3 · 80.0 · 85.6 · 91.8 · 95.9；q8 91.8 · 80.0 · 86.7 · 92.3 · 95.9 | bf16 84.6 · 79.5 · 82.1 · 91.8 · 79.5；q8 84.6 · 79.5 · 82.1 · 92.3 · 80.5 |
| 合格带 · Band（另要求各维 ≥ 75%、JSON ≥ 99%、闸门 10/10 · plus each dimension ≥ 75%, JSON ≥ 99%, gate 10/10） | 86–92% | 81–86% |

- 摘要、safetensors 固定版本与回退步骤见[集成指南](../docs/integration.md#升级到-v10)；
  `server/docker-compose.yml` 顶部列了这两个版本的文件名与摘要。
- **v9**：v9 标签里 195 题有 154 题的 B 是 0，95.9% 的 B 一致率有一部分只是基础比例；恒定输出 0.5 在这套
  标签上就有 84.9%，所以要同时看读数种类数（参考值 57 / 56）。v9 没有通过它自己五道预注册闸门中的两道
  （v9 的闸门 4：真实终评上 W/E/H 的下限；v9 的闸门 5：W 安全），同样经创始人裁决发布。
- **v9 与 v7**：上游的危机处理同样不能省（见上一节）。

- Digests, pinned safetensors revisions and rollback steps are in the
  [integration guide](../docs/integration.md#upgrading-to-v10); the top of
  `server/docker-compose.yml` lists the file names and digests of these two versions.
- **v9**: 154 of the 195 v9 B labels are 0, so v9's 95.9% on B is partly base rate, and on these
  labels a constant 0.5 output already reads 84.9% — read the number of distinct read-outs as
  well (reference 57 / 56). v9 failed two of its own five pre-registered gates (v9's gate 4, the
  W/E/H floors on the real final exam, and v9's gate 5 (W safety)) and was likewise released by
  founder decision.
- **v9 and v7**: upstream crisis handling is not optional for them either (see the previous
  section).

## 量化档位怎么选 · Choosing a quantization

**v10 的量化档位我们只量过随包的 Q8_0**（文件名里的 q8）：18 项验收检查就是在这个文件上跑的。下面
Q6_K / Q4_K_M 的数字全部来自 v7 权重；v9 也只量过 Q8_0。

**同一组权重，两个文件。** `model.safetensors`（bf16）与随包 GGUF 是同一组平均权重，GGUF 由
`convert_hf_to_gguf.py --outtype q8_0` 转出（llama.cpp `748d4225`）。本考卷上两者同为 87.3%，但逐题不能
互换：本卷 195 题里五个分数完全相同的有 176 题（90.3%），技术档案列出的另外四份考卷上是 93.7–96.2%。
部署 safetensors 的，参考 bf16 一列（经 MLX 测得；本卷没有经 transformers 跑过）。

**自己重转，哈希对不上是正常的。** 在我们的构建目录里重转，得到的文件与随包 GGUF 逐字节相同；从模型仓库
下载后重转则不同：310 个张量全部逐字节相同，但转换器会把文件夹名和模型卡的 front matter 写进文件头，哈希
因此不同。请比较张量或输出，不要比哈希。随包文件头里 `general.name = V10S1_Tailavg`（构建标签），没有
许可证字段；模型许可证照样适用。

**社区量化档**（[mradermacher](https://huggingface.co/mradermacher/hamo-score-0.6b-GGUF)，感谢）是 2026-08-05
由 **v4 权重**制作的，比 v10 落后四个发布版本（v6.1、v7、v9、v10）：A 用旧口径，早于 W 安全修复与明确意念
规则。我们没有对它们的有效测量：本页早先那张拿 v6.1 的 Q8_0 去比这些 v4 档的对比表量到的是版本差，已撤回。
下面的建议不涵盖它们。

**The shipped Q8_0 (the q8 of the file name) is the only v10 quantization we have measured**: it
is the file the 18 acceptance checks ran on. The Q6_K / Q4_K_M numbers below come from v7
weights; on v9, too, Q8_0 is the one quantization we measured.

**One set of weights, two files.** `model.safetensors` (bf16) and the shipped GGUF hold the same
averaged weights; the GGUF is `convert_hf_to_gguf.py --outtype q8_0` of them (llama.cpp
`748d4225`). On this exam both read 87.3%, but item by item they are not interchangeable: they
give the identical five-score read-out on 176 of this exam's 195 questions (90.3%) and on
93.7–96.2% of items on the four other exams listed in the technical record. If you serve the
safetensors, the bf16 column is the nearest reference: it was measured through MLX, and this
exam was not run through transformers.

**If you re-convert, expect a different hash.** Re-converting our build directory reproduces the
shipped GGUF byte for byte; converting a download of the model repository does not: all 310
tensors are byte-identical, but the converter writes the folder name and the model card's front
matter into the header, so the hash differs. Compare tensors or outputs, not hashes. The
shipped header shows `general.name = V10S1_Tailavg` (a build label) and carries no license
field; the model license applies all the same.

**The community builds** by
[mradermacher](https://huggingface.co/mradermacher/hamo-score-0.6b-GGUF) (thank you) were made on
2026-08-05 from the **v4 weights**, four releases behind v10 (v6.1, v7, v9, v10): they score A
under the old rubric and predate the W safety repair and the explicit-ideation rule. We have no
valid measurement of them: the earlier comparison on this page of a v6.1 Q8_0 against these v4
builds measured a version gap and was withdrawn. The recommendation below does not cover them.

| v7 权重，真实终评 453 轮 · v7 weights, real final exam (453 turns) | bf16 (MLX) | Q8_0（已发布 · published） | Q6_K（未发布 · unpublished） | Q4_K_M（未发布 · unpublished） |
|---|---|---|---|---|
| 维度级（±0.5）· Dim-level | 85.1% | 85.3% | 85.3% | 84.5% |
| 决策级（状态桶）· Decision-level (state bucket) | 97.1% | 97.1% | 96.9% | 96.7% |
| 参照 W ≥ 2.5 的 37 轮的 W 均值 · Mean W on the 37 turns with reference W ≥ 2.5（参照标签 reference labels 2.84） | 2.58 | 2.58 | 2.58 | **2.50** |
| 这 37 轮上 W 低于 / 高于 Q8_0 · W lower / higher than Q8_0 on those 37 | 0 / 0 | — | 1 / 1 | **6 / 1** |
| 体积 · Size | — | 0.64 GB | 0.50 GB | 0.40 GB |

Q6_K 与 Q4_K_M 由我们用 llama.cpp 从 v7 的 f16 GGUF 量化。同一提示词与解析器；bf16 经 MLX（温度 0），GGUF
各档经 llama.cpp（Metal）、中性采样。

在 v7 上，Q6_K 与 Q8_0 接近。Q4_K_M 决策级只低 0.4 个点，但在参照 W ≥ 2.5 的 37 轮上
单边压低 W。**状态桶粗到足以吸收一个被压低的信号，只看一致率发现不了这件事。** v10 的低比特档在这些轮次上
会怎样，没有量过。

**建议。** 读数要把关行为的，用随包 **Q8_0**。**Q6_K / Q4_K_M** 我们不发布：自己量化后，先跑
`compare_quants.py` 与随包 Q8_0 对比，再让它把关任何事。在 v7 上，Q4_K_M 适合研究、离线和由人来读分数的
场景；若被迫用于把关，考虑下调退缩阈值补偿。上游危机处理的要求对任何档位都成立。v7 上低于 Q4_K_M 的档位
没有量过；没量过的一律按更差对待。

Q6_K and Q4_K_M were quantized by us with llama.cpp from a v7 f16 GGUF. Same prompt and parser;
bf16 through MLX (temperature 0), the GGUF builds through llama.cpp with Metal, neutral sampling.

On v7, Q6_K tracks Q8_0. Q4_K_M loses only 0.4 points decision-level, but it damps W
one-sidedly on the 37 turns with reference W ≥ 2.5. **State buckets are coarse enough to absorb a
damped signal; agreement alone does not show it.** What a lower-bit v10 build does on these
turns is unmeasured.

**Recommendation.** Where read-outs gate behaviour, use the shipped **Q8_0**. We publish no
**Q6_K / Q4_K_M**: quantize the weights yourself and run `compare_quants.py` against the shipped
Q8_0 before the build gates anything. On v7, Q4_K_M suited research, offline use and scores read
by a person; if one is forced into gating, consider lowering your withdrawal threshold to
compensate. The upstream crisis requirement holds at any quantization. On v7 we measured nothing
below Q4_K_M; assume anything unmeasured is worse.

```bash
# 1. 已发布的权重（HF 格式；main 即 v10）→ f16 GGUF · released weights (HF format; main is v10) → f16 GGUF
python llama.cpp/convert_hf_to_gguf.py <v10-weights-dir> --outtype f16 --outfile hamo-score-0.6b-v10.f16.gguf
# 2. f16 → 目标档位 · f16 → target quant（Q6_K 或 or Q4_K_M）
llama-quantize hamo-score-0.6b-v10.f16.gguf hamo-score-0.6b-v10.q4_k_m.gguf Q4_K_M
# 3. 每档复制一份 server/Modelfile，只改 FROM · one copy of server/Modelfile per build, change only FROM
#    （原文件的 FROM 是 · the shipped FROM is /tmp/hamo/gguf/hamo-score-0.6b-v10.q8.gguf）
cp server/Modelfile Modelfile.q4                 # then edit FROM → your ...v10.q4_k_m.gguf
ollama create hamo-q8 -f server/Modelfile        # 基准档在前 · reference build first: the shipped v10 Q8_0
ollama create hamo-q4 -f Modelfile.q4
python eval/compare_quants.py --models hamo-q8 hamo-q4
```

`compare_quants.py` 在本仓库的合成考卷上跑各档（零真实数据），除各档一致率外，还输出**方向性衰减表**：每个
维度「更低 / 更高」的题数，以及高退缩题（教师 W ≥ 1.5）上 W 更低 / 更高的题数与各档 W 均值。单边分布就是
结论。一致率默认对照 v10 标签；比 v9 各档加 `--labels v9`，比 v7 各档加 `--labels pre_v9`。只比同一版本的
档位，跨版本量出的是版本差。

`compare_quants.py` runs the synthetic exam (no real data) across builds and prints, besides
per-build agreement, a **directional attenuation table**: lower / higher counts per dimension,
and, on high-withdrawal questions (teacher W ≥ 1.5), W lower / higher counts and each build's
mean W. A one-sided split is the finding. Agreement is graded against the v10 labels by default;
pass `--labels v9` for v9 builds and `--labels pre_v9` for v7 builds. Compare builds of one
version; across versions the script measures a version gap.

## 数字不对时 · If your numbers are off

大幅偏离合格带多半是接线问题，不是模型问题。按序排查：

0. **先查采样参数，而且要手工查——这份考卷看不到它。** `ollama show <model> --parameters` 必须看到
   `repeat_penalty 1`；你自己的服务也要随请求带上 temperature 0、repeat_penalty 1.0、top_k 0、top_p 1.0。
   ollama 默认的 1.1 会惩罚本模型输出里重复的 `0.0`，把分数推离 0。随包 v10 q8 实测（旧 B 卷，legacy 答案，
   300 道合成题，不在本仓库；llama.cpp + Metal），只把 repeat_penalty 从 1.0 改成 1.1：造分（应打低的题
   打到 B ≥ 1.0）3/104（2.9%）→ 15/104（14.4%）；B 符号翻转 93 题中 2 → 4 题；成对方向正确 59/60 → 58/60；
   漏判（应打高的题打到 B ≤ 0.5）21/180（11.7%）→ 12/180（6.7%），这个「下降」是同一股上推，不是改进。
   更早版本按当时发布的数字（llama.cpp，CPU；同一批题，legacy 答案）：v7 造分 2.9% → 8.7%、符号翻转
   0 → 1；v6.1 造分 13.5% → 25.0%、符号翻转 6 → 10。v9 按其模型卡发布的数字（crisp 答案）：造分
   1.9% → 2.8%。各次测量的运行环境与答案不同，幅度不能互相比较；方向每次都一样。
1. **维度级在 80–84% 上下，JSON 与闸门区都正常** → 多半是权重与标签套错了，对照交叉读数表：
   - B 只有 57 左右：v9 权重配了默认标签，工具包升到 0.3.0、服务仍是 v9 时最常见。加 `--labels v9`，或把
     服务换成 v10。
   - A 只有 80 左右：v7 权重配了默认标签。加 `--labels pre_v9`，或把服务换成 v10。
   - 约 83%、A 正常：v10 权重配了 `--labels v9`（83.1% / 82.9%）。去掉这个开关。

   核对三处：Modelfile 的 `FROM` 指向哪个 GGUF，服务实际调用哪个模型标签，命令行带了哪个 `--labels`。
2. **JSON 合法率 < 99%** → 聊天模板错了：检查模板是否带空 `<think>` 块（见 `server/Modelfile`）。温度由
   考卷随请求发送为 0，只有服务端不采纳请求参数时才出问题（第 3 条）。
3. **维度级明显低于 84% 且不是第 1 条，或脚本提示不同读数太少**（全卷少于 19 种，即近乎恒定输出；v10
   参考值 75 / 78）→ 服务端跑的多半不是「随包 q8 + 随包模板」：GGUF 不对，模板与 `server/Modelfile` 不同，
   用了没量过的量化档，或服务端不采纳请求参数（此时生效的是它自己的采样默认值）。考卷用的是工具包的
   `build_prompt()` 与 `parse_scores()`，查不出你自己服务里的提示词、采样与解析——那些要另外对照
   `build_prompt()` 核对。
4. **闸门区 ≠ 10/10** → 你运行的 `hamo_score` 里 `CrisisGate` 的词表被改动了（这一节在进程内直接跑闸门）。
   许可证 §3(c) 要求在模型上游用独立机制处理危机与自伤内容；修复后再上线。

Large deviations from the band are usually wiring, not the model. Check in this order.

0. **Sampling parameters first — by hand, because this exam cannot see them.**
   `ollama show <model> --parameters` must show `repeat_penalty 1`, and your own service must
   send temperature 0, repeat_penalty 1.0, top_k 0 and top_p 1.0 as well. ollama's default 1.1
   penalises the repeated `0.0` in this model's output and pushes scores away from zero. Measured
   on the shipped v10 q8 (old B exam, legacy key, 300 synthetic questions, not shipped here;
   llama.cpp + Metal), changing only repeat_penalty from 1.0 to 1.1: fabrication (items that
   should score low, scored B ≥ 1.0) 3/104 (2.9%) → 15/104 (14.4%); B sign flips 2 → 4 of 93;
   pair direction 59/60 → 58/60; misses (items that should score high, scored B ≤ 0.5) 21/180
   (11.7%) → 12/180 (6.7%) — that drop is the same upward push, not an improvement. Earlier
   versions, as published at the time (llama.cpp on CPU; same questions, legacy key): v7
   fabrication 2.9% → 8.7%, sign flips 0 → 1; v6.1 fabrication 13.5% → 25.0%, sign flips 6 → 10.
   As published on the v9 card (crisp key): v9 fabrication 1.9% → 2.8%. These occasions differ in
   runtime and answer key, so their effect sizes are not comparable; the push is in the same
   direction each time.
1. **Dimension-level around 80–84% with JSON and the gate section fine** usually means weights
   and labels are mismatched. Compare with the cross table:
   - B near 57: v9 weights on the default labels — the common case after upgrading the toolkit to
     0.3.0 while still serving v9. Pass `--labels v9`, or serve v10.
   - A near 80: v7 weights on the default labels. Pass `--labels pre_v9`, or serve v10.
   - About 83% with A normal: v10 weights with `--labels v9` (83.1% / 82.9%). Drop the flag.

   Check three things: which GGUF your Modelfile's `FROM` points to, which model tag your service
   calls, and which `--labels` you passed.
2. **JSON validity below 99%** means a broken chat template: check the empty `<think>` block (see
   `server/Modelfile`). The exam sends temperature 0 itself, so temperature can only be wrong on
   a server that ignores request options (case 3).
3. **Dimension-level clearly below 84% and not case 1, or the script warns of few distinct
   read-outs** (fewer than 19 on the full exam, that is, close to a constant output; the v10
   reference has 75 / 78): the server is most likely not running the shipped q8 behind the
   shipped template — the wrong GGUF, a chat template that differs from `server/Modelfile`, an
   unmeasured quantization, or a server that ignores request options (its own sampling defaults
   then apply).
   The exam uses the toolkit's `build_prompt()` and `parse_scores()`, so it cannot check the
   prompt, sampling or parser of your own service; compare those with `build_prompt()` separately.
4. **Gate section below 10/10**: the `CrisisGate` word lists in the `hamo_score` you are running
   have been altered (this section runs the gate in-process). License §3(c) requires an
   independent mechanism upstream of the model for crisis and self-harm content; fix it before
   going live.
