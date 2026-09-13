# 自检考卷 · Self-Check Exam

部署完成后，用这份考卷验证你的部署是否复现了官方数字。
After deploying, run this exam to verify your deployment reproduces the official numbers.

```bash
python eval/run_exam.py                       # ollama on localhost:11434
python eval/run_exam.py --base-url http://myhost:11434 --model my-tag
```

## 考卷构成 · What's inside

- **评分区 `synthetic_exam.jsonl`（195 题）**：10 个非危机场景格子（闲聊、省略回复、躯体陈述、
  第三方冲突、顶撞助手、自我批评、短促求助、隐含重度、敌意但清晰、长篇倾诉）各约 20 题。
  全部合成生成（2026-08-16 全新种子，与所有训练语料不相交），教师标签来自 deepseek-chat +
  生产 rubric。**不含任何真实来访者数据。**
- **闸门区 `gate_cases.jsonl`（10 题）**：手写危机句式 7 条（中英）+ 黑色幽默/夸张表达 3 条
  （不应误触）。这一节不调用模型——它在进程内跑工具包的 `CrisisGate` 词表。注意它不验证
  你的部署是否真把每条消息先送过闸门，那是你自己要做的集成测试。

Scoring section: 195 synthetic, teacher-labeled questions across 10 non-crisis cells; fresh seed,
disjoint from all training corpora; **zero real client data**. Gate section: 10 handwritten cases
(7 crisis phrasings zh+en, 3 dark-humor lookalikes) run against the toolkit's `CrisisGate` word
lists in-process. It does not test that your deployment actually routes every message through the
gate before the model — that wiring is an integration test you own.

## 官方参考数字 · Official reference (v7)

| 指标 Metric | 参考值 Reference | 合格带 Expected band |
|---|---|---|
| JSON 合法率 JSON validity | 100% | ≥ 99% |
| 维度级一致率 Dim-level agreement (±0.5) | 83.5% | 81–86% |
| 分维 Per-dim | A 85 · W 79 · E 82 · H 92 · B 79 | 各维 ≥ 75% |
| 闸门区 Crisis gate | 10/10 | 10/10（硬性 hard requirement） |

参考值测于 v7 bf16 权重（MLX, M1 Pro；本合成考卷上延迟 P50 0.61s，不作横向参考——延迟取决于你的硬件），
**采样为温度 0 且无重复惩罚**——若你的 ollama 用了默认 `repeat_penalty 1.1`，分数会整体偏高，
考卷数字不可比（见下方排查第 0 条）。
我们发布的 v7 q8_0 GGUF 经 llama.cpp（`server/Modelfile` 的模板，中性采样：temperature 0、top_k 0、
top_p 1.0、repeat_penalty 1.0）实测：JSON 100%、维度级 83.8%（A 85 · W 79 · E 82 · H 92 · B 81）、
闸门 10/10，落在合格带内；经 ollama 部署同样应落在带内，轻微浮动来自量化与采样器实现差异。
v7 在这份合成考卷上比 v6.1 低约 0.7 个点（同一脚本复测 v6.1 bf16 为 84.2%，此前发布值 84.0%），
与 v7 在内部 453 题终评集上维度级低 0.5 个点的方向一致；合格带不变。

Reference measured on v7 bf16 weights (MLX, M1 Pro, temperature 0, no repeat penalty). The shipped
v7 q8_0 GGUF, run through llama.cpp with the Modelfile template and neutral sampling (temperature 0,
top_k 0, top_p 1.0, repeat_penalty 1.0), scored JSON 100%, 83.8% dim-level (A 85 · W 79 · E 82 ·
H 92 · B 81) and gate 10/10 — inside the band. A q8 GGUF deployment via ollama should land inside
the band too; small drift comes from quantization and sampler differences. v7 sits ~0.7 pt below
v6.1 on this synthetic exam (v6.1 bf16 re-run through the same harness: 84.2%, vs 84.0% published
earlier) — the same direction as its 0.5-pt dim-level dip on the internal 453-turn final split; the
band is unchanged. Latency (v7 bf16 P50 0.61 s on M1 Pro, on this synthetic exam) depends entirely
on your hardware and is not part of the band.

## 量化档位怎么选 · Choosing a quantization

社区（mradermacher，感谢）提供了 Q2_K→f16 共 12 个静态 GGUF 档，但它们是 2026-08-05 由
**v4 权重**制作的，比 v7 早两个发布版本，已经过时。下表全部来自 **v7 权重**：Q8_0 即我们发布的
GGUF；Q6_K 与 Q4_K_M 由我们用 llama.cpp 从 v7 f16 GGUF 自行量化，**未在任何地方发布**。测于内部
453 题终评集（真实假名化对话，不公开），同一提示词、同一解析器；bf16 经 MLX（温度 0），各 GGUF 档经
llama.cpp 中性采样：

The community builds by [mradermacher](https://huggingface.co/mradermacher/hamo-score-0.6b-GGUF)
(twelve static quants, Q2_K→f16 — thank you) were made on 2026-08-05 from the **v4 weights**, two
releases before v7, and are outdated. Everything below comes from **v7 weights**: Q8_0 is the
shipped GGUF; Q6_K and Q4_K_M were quantized by us with llama.cpp from a v7 f16 GGUF and are **not
published anywhere**. Measured on our internal 453-turn final exam (real, pseudonymised, not
public) with the same prompt and parser; bf16 via MLX (temperature 0), the GGUF builds via
llama.cpp with neutral sampling:

| | bf16 (MLX) | Q8_0 | Q6_K | Q4_K_M |
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
2.58 → 2.50），但这次没有多出危机漏检。

On v7, Q6_K is indistinguishable from Q8_0 on this exam; against Q8_0, Q4_K_M loses 0.8 pt
dim-level and 0.4 pt decision-level and still attenuates one-sidedly on the crisis-adjacent subset
(6 lower vs 1 higher, mean W 2.58 → 2.50), but did not add a crisis miss here.

**更正 · Correction**：本节此前发布的对比（Q6_K 维度级低约 1 个点、Q4_K_M 在 37 条危机相邻样本中
20 条低于 Q8_0、漏检 5 条）拿的是 v6.1 的 Q8_0 去比由 v4 权重制作的社区档——差距主要是版本差，
不是量化差。那张表已作废，以上表为准。

The comparison previously published here (Q6_K ~1 point lower, Q4_K_M lower than Q8_0 on 20 of 37
crisis-adjacent turns with 5 misses) compared a v6.1 Q8_0 against community builds made from v4
weights, so the gap was mostly a version gap, not a quantization gap. It is superseded by the table
above.

**建议 Recommendation**：门控行为的部署用 **Q8_0**（我们发布的档）；内存紧张时，**从 v7 权重自行
量化的 Q6_K** 已验证可用于门控；**Q4_K_M** 适合研究/离线/由人来读分数的场景——若被迫用于门控，
确定性危机闸门必须保持在上游（这一条任何档位都是硬性要求），并考虑下调退缩阈值补偿。低于 Q4_K_M
的档位未验证；社区各档（v4 权重）同样未验证。

Use **Q8_0** (the shipped GGUF) where read-outs gate behaviour; a **Q6_K quantized from v7** is
validated for gating when memory is tight; **Q4_K_M** is for research, offline and human-read
scores — if forced into gating, keep the deterministic crisis gate upstream (always required) and
consider compensating the withdrawal threshold. Builds below Q4_K_M are unvalidated, and so are the
community builds (v4 weights).

**想要 v7 的 Q6_K / Q4_K_M？目前只能自己量化 · Want a v7 Q6_K / Q4_K_M? For now, quantize it yourself**
（社区档是 v4，我们没有发布低比特档 · the community builds are v4 and we publish no low-bit build）：

```bash
# 1. 已发布的 v7 权重（HF 格式）→ f16 GGUF · released v7 weights (HF format) → f16 GGUF
python llama.cpp/convert_hf_to_gguf.py <v7-weights-dir> --outtype f16 --outfile hamo-score-0.6b-v7.f16.gguf
# 2. f16 → 目标档位 · f16 → target quant（Q6_K 或 or Q4_K_M）
llama-quantize hamo-score-0.6b-v7.f16.gguf hamo-score-0.6b-v7.q6_k.gguf Q6_K
```

**方法论上更重要的一点 · The methodological point**（在 v7 上依然可见）：Q8_0 → Q4_K_M 的桶一致率
只差 0.4 个百分点（97.1% → 96.7%），但底下 Q4_K_M 在 37 条危机相邻样本上有 6 条比 Q8_0 打得更低、
仅 1 条更高——**桶的边界粗到足以吸收一个被压扁的信号，只看一致率永远发现不了这件事。** 所以本目录
提供了 `compare_quants.py`：它跑本仓库的合成考卷（零真实数据），除了各档一致率，还输出**方向性衰减
表**——每个维度「更低/更高」的条数分布，以及高退缩子集上的同一分布。单边分布就是结论。

Still visible on v7: bucket agreement moved only 0.4 points from Q8_0 to Q4_K_M (97.1% → 96.7%),
while underneath, Q4_K_M scored W lower than Q8_0 on 6 of 37 crisis-adjacent turns and higher on
exactly 1. **Buckets are coarse enough to absorb a damped signal — agreement alone will never
surface it.** Hence `compare_quants.py` in this directory: it runs the synthetic exam (no real
data) across builds and prints a **directional attenuation table** — lower/higher counts per
dimension, and the same split restricted to high-withdrawal turns. A one-sided split is the finding.

```bash
# 仓库只带 server/Modelfile：每个档位复制一份，只改 FROM 行
# The repo ships only server/Modelfile: copy it per build and change only the FROM line
cp server/Modelfile Modelfile.q4                 # then edit FROM → your ...v7.q4_k_m.gguf
ollama create hamo-q8 -f server/Modelfile        # FROM: the shipped q8_0 GGUF
ollama create hamo-q4 -f Modelfile.q4
python eval/compare_quants.py --models hamo-q8 hamo-q4
```

## 数字不对时 · If your numbers are off

大幅偏离合格带几乎总是接线问题，不是模型问题，按序排查：

0. **先查采样参数**（最常见、最隐蔽）：`ollama show <model> --parameters` 必须看到
   `repeat_penalty 1`。ollama 默认 1.1，会惩罚本模型输出里重复的 `0.0`，把分数系统性
   推高——发布的 v7 q8 GGUF 在模型卡的 300 题边界判别考卷（B 维，不在本仓库）上实测：造分率
   2.9%→8.7%、边界符号翻转（真值 0.0 被打 ≥2.0）0→1；漏判率 12.8%→6.7% 的「下降」是同一股上推，
   不是改进；配对方向正确率两者都是 98.3%，很容易被当成「正常波动」。（v6.1 上同一开关：造分率
   13.5%→25.0%，符号翻转 6→10。）
1. **JSON 合法率 < 99%** → 提示词模板错了。检查 Modelfile/template 是否带空 `<think>` 块
   （见 `server/docker-compose.yml`），temperature 是否为 0。
2. **维度级 < 78%** → 大概率没用 `build_prompt()`（自造提示词），或量化过狠（q4 以下）。
3. **闸门区 ≠ 10/10** → 你改动或绕过了 `CrisisGate`。这是许可证 §3(c) 的红线，修复后再上线。

Check sampling first: `ollama show <model> --parameters` must show `repeat_penalty 1`. ollama's
default 1.1 penalises the repeated `0.0` in this model's output and pushes scores up — on the
shipped v7 q8 GGUF, measured on the model card's 300-question boundary-discrimination exam
(B dimension; not shipped here), fabrication goes 2.9% → 8.7% and boundary sign flips (a true 0.0
scored ≥2.0) 0 → 1, while paired direction accuracy stays at 98.3% — easy to mistake for normal
noise; the lower miss rate under 1.1 (12.8% → 6.7%) is the same upward push, not an improvement.
(On v6.1 the same switch took fabrication 13.5% → 25.0% and sign flips 6 → 10.)

Big deviations are almost always wiring, not the model: broken template (check the empty
`<think>` block and temperature 0), a hand-rolled prompt instead of `build_prompt()`, or
over-aggressive quantization. A failed gate section means the `CrisisGate` was altered or
bypassed — that's the license §3(c) red line; fix before going live.
