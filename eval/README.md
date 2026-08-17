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

参考值测于 bf16 权重（MLX, M1 Pro；延迟 P50 0.81s 不作横向参考——延迟取决于你的硬件）。
q8 GGUF 经 ollama 部署的数字应落在合格带内；轻微浮动来自量化与采样器实现差异。

Reference measured on bf16 weights (MLX, M1 Pro). A q8 GGUF deployment via ollama should land
inside the band; small drift comes from quantization and sampler differences. Latency depends
entirely on your hardware and is not part of the band.

## 数字不对时 · If your numbers are off

大幅偏离合格带几乎总是接线问题，不是模型问题，按序排查：

1. **JSON 合法率 < 99%** → 提示词模板错了。检查 Modelfile/template 是否带空 `<think>` 块
   （见 `server/docker-compose.yml`），temperature 是否为 0。
2. **维度级 < 78%** → 大概率没用 `build_prompt()`（自造提示词），或量化过狠（q4 以下）。
3. **闸门区 ≠ 10/10** → 你改动或绕过了 `CrisisGate`。这是许可证 §3(c) 的红线，修复后再上线。

Big deviations are almost always wiring, not the model: broken template (check the empty
`<think>` block and temperature 0), a hand-rolled prompt instead of `build_prompt()`, or
over-aggressive quantization. A failed gate section means the `CrisisGate` was altered or
bypassed — that's the license §3(c) red line; fix before going live.
