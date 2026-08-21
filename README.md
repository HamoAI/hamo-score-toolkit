# hamo-score-toolkit

**EN** | [中文](#中文)

Client toolkit and **safety scaffold** for [HamoAI/hamo-score-0.6b](https://huggingface.co/HamoAI/hamo-score-0.6b) —
the little model that takes a conversational pulse (AWEHB: Agency / Withdrawal / Extremity / Hostility / Boundary).

This repo is the missing half of the model: the exact prompt format, tolerant
output parsing, the smoothing-and-buckets math the scores are designed to feed,
and — front and center — the **crisis gate** that the model license
([HAMO-RAIL-S §3c](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/LICENSE))
requires upstream of the model in any consumer-facing deployment.

> ⚠️ The model is not a chatbot, not a diagnostic instrument, and **not a
> crisis detector**. This toolkit makes the safe integration pattern the easy one.

## 5-minute start (ollama)

```bash
# 1. get the model (one-time)
hf download HamoAI/hamo-score-0.6b gguf/hamo-score-0.6b-v61.q8.gguf --local-dir /tmp/hamo
ollama create hamo-score-0.6b -f server/Modelfile

# 2. install the toolkit
pip install hamo-score
```

```python
from hamo_score import OllamaClient, score_message, update_stress, energy_state

client = OllamaClient(model="hamo-score-0.6b")
r = score_message(client, "虽然还是有点提不起劲，不过今天把拖了两周的体检约上了",
                  history=[{"role": "assistant", "content": "这周过得怎么样？"}])

if r.crisis.triggered:          # deterministic gate ran BEFORE the model
    route_to_human(r.crisis.matched)
elif r.scores:
    print(r.scores)             # {'A': 2.5, 'W': 0.5, 'E': 0.0, 'H': 0.0, 'B': 1.0}
    stress = update_stress(r.scores, current_stress=3.0)
    print(energy_state(stress)) # 'positive' / 'negative' / 'neurotic'
```

That's the whole intended shape: **gate → score → smooth → bucket**. Scores are
per-message signals; never act on a single raw score.

## One-command server (Docker)

No Python integration needed — run the whole pipeline as an HTTP service:

```bash
git clone https://github.com/HamoAI/hamo-score-toolkit.git && cd hamo-score-toolkit/server
docker compose up          # downloads the GGUF (639MB, one-time), creates + warms the model
```

```bash
curl -s localhost:8080/score -H 'content-type: application/json' \
  -d '{"message": "最近总觉得撑不太住", "current_stress": 3.0}'
# → {"crisis": {...}, "scores": {"A":..}, "stress": 3.1, "energy_state": "positive", "latency_ms": ...}
```

`POST /score` runs gate → score → smooth → bucket; crisis-gated requests never
reach the model. `GET /healthz` probes the model end-to-end.

## Verify your deployment

A 195-question synthetic exam (teacher-labeled, zero real data) plus 10
handwritten crisis-gate cases. Run it against your own deployment and compare
with the official reference band in [eval/README.md](eval/README.md):

```bash
python eval/run_exam.py    # reference: JSON 100%, dim-level 84.0%, gate 10/10
```

## Adapting it to your own population

Read [docs/finetune.md](docs/finetune.md) — the six-generation fine-tuning
playbook, including the two generations we rejected for crisis-recall
regressions and exactly why. Data red lines first, then the real LoRA recipe,
checkpoint selection with a crisis-miss column, and the acceptance hard gate.

## What's in the box

| Module | What it gives you |
|---|---|
| `hamo_score.prompt` | The one true prompt format + built-in trimming guards (3×200-char turns, 500-char message) |
| `hamo_score.parse` | Think-block-tolerant JSON parsing, grid snapping |
| `hamo_score.client` | `OllamaClient` / `TransformersClient` + `score_message()` safe pipeline |
| `hamo_score.stress` | Reference smoothing (`0.8·history + 0.2·message`) + energy-state buckets |
| `hamo_score.safety` | `CrisisGate` (zh/en word lists, extensible) + AI-disclosure texts |

More docs: the [integration guide](docs/integration.md) (the correct wiring +
the ten-point don't list), the [FAQ](docs/faq.md), and the
[fine-tuning playbook](docs/finetune.md). Runnable examples in
[`examples/`](examples): quickstart, batch CSV scoring, and a session-monitor
demo with the crisis short-circuit (both take `--mock` to run without a model).

Design notes worth reading before integrating: the model card's
[Evaluation](https://huggingface.co/HamoAI/hamo-score-0.6b#evaluation) and
[Limitations](https://huggingface.co/HamoAI/hamo-score-0.6b#limitations--known-residuals)
sections — including why the reference scorer's own self-consistency (94–98%)
is the practical ceiling.

## Disagree with a score?

Open an issue with the **score disagreement** template (message + model score +
what you think it should be). Disagreement reports feed the human gold-label
program that steers future versions.

## License

Toolkit code: **Apache-2.0**. Model weights: **HAMO-RAIL-S 1.0** (free use with
four restrictions — no standalone clinical determinations, no consequential
decisions about individuals, keep independent upstream crisis handling + AI
disclosure in consumer deployments, no re-identification). Using this toolkit's
default pipeline satisfies the crisis-handling pattern by construction.

---

# 中文

[hamo-score-0.6b](https://huggingface.co/HamoAI/hamo-score-0.6b) 的客户端工具包与**安全脚手架**——给对话把脉的小模型（AWEHB 五维：行动力/退缩/极端化/敌意/边界）。

这个仓库是模型的另一半：唯一正确的提示词格式、容错解析、分数该喂进去的平滑折算与状态桶，以及放在最前面的**危机闸门**——模型许可证（HAMO-RAIL-S §3c）要求任何面向消费者的心理健康部署都必须在模型上游保留独立的危机处理，本工具包让「合规的接法」成为「最省事的接法」。

**五分钟上手**：见上方英文段——`hf download` 拉 GGUF → `ollama create` → `pip install` → 四行代码跑通 **闸门 → 评分 → 平滑 → 状态桶** 完整链路。切记：分数是逐句信号，永远不要凭单句原始分做任何决定。

**一键服务器**：`cd server && docker compose up`——自动拉 GGUF、建模型、预热，`POST localhost:8080/score` 直接返回 危机/五维分/压力值/状态桶，危机命中的请求永远不会碰到模型。

**部署自检**：`python eval/run_exam.py`——195 题合成考卷（教师标注，零真实数据）+ 10 条手写危机闸门用例，对照 [eval/README.md](eval/README.md) 的官方参考带（JSON 合法率 100%、维度级 84.0%、闸门 10/10）验证你的部署接线正确。

**想微调到你自己的人群？** 读 [docs/finetune.md](docs/finetune.md)——六代模型蒸出来的完整打法（含两代拒收与确切原因）：数据红线、真实 LoRA 配方、带危机漏检列的选点表、验收硬闸。

**更多文档**：[集成指南](docs/integration.md)（正确接线 + 十条禁令）、[FAQ](docs/faq.md)、[微调指南](docs/finetune.md)；[`examples/`](examples) 里有可跑的批量打分与会话监测演示（带 `--mock`，无模型也能看管线）。

**对某个评分不服？** 用 issue 里的「评分分歧」模板提交（消息 + 模型分 + 你认为的分）——分歧报告会进入人类金标计划，直接影响后续版本。

**许可证**：工具包代码 Apache-2.0；模型权重 HAMO-RAIL-S 1.0（自由使用附四条限制，用本工具包默认管线即天然满足危机处理条款）。
