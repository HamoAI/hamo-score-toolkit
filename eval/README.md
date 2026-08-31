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

## 官方参考数字 · Official reference (v6.1)

| 指标 Metric | 参考值 Reference | 合格带 Expected band |
|---|---|---|
| JSON 合法率 JSON validity | 100% | ≥ 99% |
| 维度级一致率 Dim-level agreement (±0.5) | 84.0% | 81–86% |
| 分维 Per-dim | A 86 · W 81 · E 84 · H 91 · B 79 | 各维 ≥ 75% |
| 闸门区 Crisis gate | 10/10 | 10/10（硬性 hard requirement） |

参考值测于 bf16 权重（MLX, M1 Pro；延迟 P50 0.81s 不作横向参考——延迟取决于你的硬件），
**采样为温度 0 且无重复惩罚**——若你的 ollama 用了默认 `repeat_penalty 1.1`，分数会整体偏高，
考卷数字不可比（见下方排查第 0 条）。
q8 GGUF 经 ollama 部署的数字应落在合格带内；轻微浮动来自量化与采样器实现差异。

Reference measured on bf16 weights (MLX, M1 Pro). A q8 GGUF deployment via ollama should land
inside the band; small drift comes from quantization and sampler differences. Latency depends
entirely on your hardware and is not part of the band.

## 量化档位怎么选 · Choosing a quantization

社区（mradermacher）提供了 Q2_K→f16 共 12 个静态 GGUF 档。我们用内部 453 题终评集
（真实脱敏对话，不公开）实测了其中两档，与我们发布指标所用的 Q8_0 对比：

The community ([mradermacher](https://huggingface.co/mradermacher/hamo-score-0.6b-GGUF))
publishes twelve static GGUF builds. We measured two of them against our internal 453-turn
final exam (real, de-identified, not public), alongside the Q8_0 our published numbers come from:

| | Q8_0 | Q6_K | Q4_K_M |
|---|---|---|---|
| 维度级 ±0.5 Dim-level | 85.5% | 84.4% | 84.2% |
| 决策级（状态桶）Decision-level | 96.2% | 95.8% | 95.6% |
| 危机 W 漏检 Crisis W-misses (n=37) | 4 | 3 | **5** |
| 危机子集 W 均值 Mean W on those turns（金标 gold 2.84） | 2.39 | 2.26 | **2.01** |
| 体积 Size | 0.64 GB | 0.50 GB | 0.40 GB |

**建议 Recommendation**：门控行为的部署用 **Q8_0**；内存紧张时 **Q6_K** 是我们愿意背书的最低档
（退缩信号基本无损）；**Q4_K_M** 适合研究/离线/由人来读分数的场景——若被迫用于门控，请下调
退缩阈值补偿，并把确定性危机检测保持在上游。其余九档未验证，更低比特应默认更差。

Use **Q8_0** where read-outs gate behaviour; **Q6_K** is the lowest build we would validate for
gating use; **Q4_K_M** is for research and human-read scores. The other nine are unvalidated.

**方法论上更重要的一点 · The methodological point**：三档的桶一致率只差 0.4–0.6 个百分点，
但底下 Q4_K_M 在 37 条危机相邻样本上有 20 条比 Q8_0 打得更低、仅 1 条更高——**桶的边界粗到
足以吸收一个被压扁的信号，只看一致率永远发现不了这件事。** 所以本目录提供了
`compare_quants.py`：它跑本仓库的合成考卷（零真实数据），除了各档一致率，还输出**方向性衰减
表**——每个维度「更低/更高」的条数分布，以及高退缩子集上的同一分布。单边分布就是结论。

Bucket agreement moved only 0.4–0.6 points across all three builds, while underneath, Q4_K_M
scored lower than Q8_0 on 20 of 37 crisis-adjacent turns and higher on exactly 1. **Buckets are
coarse enough to absorb a damped signal — agreement alone will never surface it.** Hence
`compare_quants.py` in this directory: it runs the synthetic exam (no real data) across builds
and prints a **directional attenuation table** — lower/higher counts per dimension, and the same
split restricted to high-withdrawal turns. A one-sided split is the finding.

```bash
ollama create hamo-q8 -f server/Modelfile        # FROM: ...q8_0.gguf
ollama create hamo-q4 -f server/Modelfile.q4     # FROM: ...q4_k_m.gguf
python eval/compare_quants.py --models hamo-q8 hamo-q4
```

## 数字不对时 · If your numbers are off

大幅偏离合格带几乎总是接线问题，不是模型问题，按序排查：

0. **先查采样参数**（最常见、最隐蔽）：`ollama show <model> --parameters` 必须看到
   `repeat_penalty 1`。ollama 默认 1.1，会惩罚本模型输出里重复的 `0.0`，把分数系统性
   推高——实测造分率 13.5%→25.0%，而一致率只掉几个百分点，很容易被当成「正常波动」。
1. **JSON 合法率 < 99%** → 提示词模板错了。检查 Modelfile/template 是否带空 `<think>` 块
   （见 `server/docker-compose.yml`），temperature 是否为 0。
2. **维度级 < 78%** → 大概率没用 `build_prompt()`（自造提示词），或量化过狠（q4 以下）。
3. **闸门区 ≠ 10/10** → 你改动或绕过了 `CrisisGate`。这是许可证 §3(c) 的红线，修复后再上线。

Big deviations are almost always wiring, not the model: broken template (check the empty
`<think>` block and temperature 0), a hand-rolled prompt instead of `build_prompt()`, or
over-aggressive quantization. A failed gate section means the `CrisisGate` was altered or
bypassed — that's the license §3(c) red line; fix before going live.
