# hamo-score-toolkit

**EN** | [中文](#中文)（中文说明在本页下半部分）

Client toolkit and **safety scaffold** for [HamoAI/hamo-score-0.6b](https://huggingface.co/HamoAI/hamo-score-0.6b) —
the little model that takes a conversational pulse (AWEHB: Agency / Withdrawal / Extremity / Hostility / Boundary).

This repo is the missing half of the model: the exact prompt format, tolerant
output parsing, the smoothing-and-buckets math the scores are designed to feed,
and — front and center — the **crisis gate** that the model license
([HAMO-RAIL-S §3c](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/LICENSE))
requires upstream of the model in any consumer-facing deployment.

> ⚠️ The model is not a chatbot, not a diagnostic instrument, and **not a
> crisis detector**. This toolkit makes the safe integration pattern the easy one.

> **Upgrading from v7? Toolkit 0.2.0 moves to hamo-score-0.6b v9, and v9 changed what A and B mean.**
> A (Agency) and B (Boundary) are scored under revised rubrics: B is `0.0` on 94% of the
> 453-turn real-conversation final exam (v7: 52%), and A comes out lower on average too. Both
> carry negative weights in the stress formula, so the same conversation computes **higher
> stress** under v9. This toolkit's stress weights and bucket cut-offs are unchanged and were set
> on pre-v9 scores — **re-tune them before letting buckets gate anything**, and do not compare
> scores across the v7 → v9 boundary. No real-conversation measurement of the new A and B exists
> yet: before anything relies on them, check them against a human-scored sample of your own
> consented conversations. Re-tuning thresholds on v9's own scores is not that check.
>
> **The pip version does not choose the model: the GGUF your ollama model was built from, or the
> Hugging Face revision you load, does.** `pip install -U hamo-score`
> changes no weights: an ollama model keeps serving the GGUF it was created from until you re-run
> `ollama create` against the v9 GGUF, while `TransformersClient()` and
> `from_pretrained("HamoAI/hamo-score-0.6b")` load Hugging Face `main`, which has been v9 since
> 2026-09-30 (UTC), under any toolkit version. What 0.2.0 moves to v9 is the reference server,
> `server/Modelfile` and the self-check exam's labels.
>
> v9 also **failed 2 of its 5 pre-registered acceptance gates, one of them a safety gate** (it
> under-scores withdrawal when suicidal ideation arrives together with help-seeking — a gap v7
> shares and v9 did not fix), and is the default by an explicit, recorded override by Hamo's
> founder. Both failures are shown in full on
> the [model card](https://huggingface.co/HamoAI/hamo-score-0.6b#evaluation) — one more reason the
> upstream crisis gate is not optional.
>
> **v7 remains available**: `gguf/hamo-score-0.6b-v7.q8.gguf` in the same repo. For the ollama
> quick start, download it and point `FROM` in `server/Modelfile` at it. The Docker server does
> not read `server/Modelfile`, so for it follow the switch note at the top of
> `server/docker-compose.yml`. The v7 safetensors are at revision
> `ab9dc70c5c25be0eb47cd9a7bf7c70c094b4fb93`: pass it as `revision=` to `from_pretrained`.
> `TransformersClient` takes no `revision` argument, so download a snapshot at that revision
> (`hf download HamoAI/hamo-score-0.6b --revision ab9dc70c5c25be0eb47cd9a7bf7c70c094b4fb93 --exclude "gguf/*" --local-dir ./hamo-score-v7`)
> and pass its local path as `model_id`. Pinning by revision and GGUF digest, and the rest of
> the upgrade steps:
> [Upgrading from v7](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/integration.md#upgrading-from-v7-a-and-b-changed-meaning).

> 💬 **Think a score is wrong? Tell us — that's the most valuable thing you can send.**
> [**Open a disagreement report →**](https://github.com/HamoAI/hamo-score-toolkit/issues/new?template=score_disagreement.md) (message + the model's score + the score you'd
> give). Every report goes into the human gold-label program that steers the next version.
> The reference scorer this model was distilled to replace disagreed with *itself* roughly 2–6% of the
> time in small spot checks (about a dozen messages each), so "the model is wrong here" is a real
> finding, not a nuisance.

## 5-minute start (ollama)

```bash
# 0. clone this repo — server/Modelfile and eval/ live here, not in the pip package
git clone https://github.com/HamoAI/hamo-score-toolkit.git && cd hamo-score-toolkit

# 1. get the model (one-time) — v9; for v7, fetch gguf/hamo-score-0.6b-v7.q8.gguf and edit FROM in server/Modelfile
hf download HamoAI/hamo-score-0.6b gguf/hamo-score-0.6b-v9.q8.gguf --local-dir /tmp/hamo
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
    print(r.scores)             # v9: {'A': 2.0, 'W': 0.5, 'E': 0.0, 'H': 0.0, 'B': 0.0}
    stress = update_stress(r.scores, current_stress=3.0)
    print(energy_state(stress)) # 'positive' / 'negative' / 'neurotic'
```

That's the whole intended shape: **gate → score → smooth → bucket**. Scores are
per-message signals; never act on a single raw score.

## One-command server (Docker)

No Python integration needed — run the whole pipeline as an HTTP service:

```bash
git clone https://github.com/HamoAI/hamo-score-toolkit.git && cd hamo-score-toolkit/server
docker compose up          # downloads the v9 GGUF (639MB, one-time), creates + warms the model
```

```bash
curl -s localhost:8080/score -H 'content-type: application/json' \
  -d '{"message": "最近总觉得撑不太住", "current_stress": 3.0}'
# → {"crisis": {...}, "scores": {"A": 0.0, "W": 2.5, ...}, "stress": 3.45, "energy_state": "positive", "latency_ms": ...}
```

`POST /score` runs gate → score → smooth → bucket; crisis-gated requests never
reach the model. `GET /healthz` probes the model end-to-end. To stay on v7, see
the switch note at the top of `server/docker-compose.yml`.

## Verify your deployment

A 195-question synthetic exam (teacher-labeled, zero real data) plus 10
handwritten crisis-gate cases. Run it from the repo root (step 0 above) against
your own deployment and compare with the official reference band in
[eval/README.md](https://github.com/HamoAI/hamo-score-toolkit/blob/main/eval/README.md):

```bash
python eval/run_exam.py    # reference (v9 bf16): JSON 100%, dim-level 88.9%, gate 10/10
```

Expected band: dim-level 86–92%, each dimension ≥ 75%, JSON ≥ 99%, gate 10/10
(the shipped v9 q8 GGUF scores 89.3%). The exam's A and B labels were re-labelled
for v9 with the same teacher prompts that labelled v9's training data, so the
exam is in-distribution by construction, and under the crisp B rubric most labels
are 0. A pass certifies your wiring (prompt, template, sampling, parser), not
model quality. Deploying v7 on purpose? Run with `--labels pre_v9` and compare
against the v7 reference (83.5%).

## Adapting it to your own population

Read [docs/finetune.md](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/finetune.md) — the ten-generation fine-tuning
playbook: the four generations we rejected and exactly why (two for crisis-recall
regressions, two for failing pre-registered gates), and v9, released by an
explicit founder override after failing two of its five gates. Data red lines
first, then the real LoRA recipe, checkpoint selection with a crisis-miss column
(and why the candidate is now fixed in advance), and the pre-registered
acceptance gates.

## What's in the box

| Module | What it gives you |
|---|---|
| `hamo_score.prompt` | The one true prompt format + built-in trimming guards (3×200-char turns, 500-char message) |
| `hamo_score.parse` | Think-block-tolerant JSON parsing, grid snapping |
| `hamo_score.client` | `OllamaClient` / `TransformersClient` + `score_message()` safe pipeline |
| `hamo_score.stress` | Reference smoothing (`0.8·history + 0.2·message`) + energy-state buckets (cut-offs set on pre-v9 scores — re-tune for v9) |
| `hamo_score.safety` | `CrisisGate` (zh/en word lists, extensible) + AI-disclosure texts |

More docs: the [integration guide](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/integration.md) (the correct wiring +
the ten-point don't list), the [FAQ](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/faq.md), and the
[fine-tuning playbook](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/finetune.md). Runnable examples in
[`examples/`](https://github.com/HamoAI/hamo-score-toolkit/tree/main/examples): quickstart, batch CSV scoring, and a session-monitor
demo with the crisis short-circuit (the last two take `--mock` to run without a model).

Design notes worth reading before integrating: the model card's
[Evaluation](https://huggingface.co/HamoAI/hamo-score-0.6b#evaluation) and
[Limitations](https://huggingface.co/HamoAI/hamo-score-0.6b#limitations--known-residuals)
sections — including v9's two failed acceptance gates, why its gains on the
v9-specific exams are in-distribution rather than real-conversation evidence,
and why the reference scorer's own self-consistency (94–98%) is a rough
practical ceiling.

## Disagree with a score? (please tell us)

This is the one contribution we ask for. [**Open a disagreement report →**](https://github.com/HamoAI/hamo-score-toolkit/issues/new?template=score_disagreement.md)

Useful reports carry three things: the **message** (redact freely — we don't want
identifiable text), **the score the model gave**, and **the score you would give**.
Context turns and your population/language help but are optional.

Every report is triaged into the human gold-label program: where licensed
practitioners disagree with the model at a rate above its own noise floor, that
becomes a training-data gap for the next generation. Disagreements are how this
model gets better; silent workarounds are how it stays wrong.

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

> **从 v7 升级？工具包 0.2.0 转向 hamo-score-0.6b v9，而 v9 改变了 A 与 B 的含义。** A（行动力）与 B（边界感）改按修订后的口径打分：453 条真实对话终评题中 94% 的 B 为 `0.0`（v7 为 52%），A 平均也更低。两者在压力公式中都是负权重，所以同一段对话在 v9 下算出的压力会**更高**。本工具包的压力权重与状态桶阈值没有改动，是按 v9 之前的分数定的——**让状态桶把关任何事之前，请先重新校准**；v7 → v9 前后的分数也不可相互比较。新 A、B 口径下还没有任何真实对话上的测量：在任何东西依赖这两维之前，先拿你自己真实、授权对话中一批人工打分的样本核对。用 v9 自己的分数重调阈值不算这项检查。
>
> **跑哪个模型由你 ollama 模型所用的 GGUF、或你加载的 Hugging Face 版本决定，不由 pip 版本决定。** `pip install -U hamo-score` 不会换任何权重：ollama 里的模型仍跑它创建时用的那个 GGUF，直到你用 v9 GGUF 重新 `ollama create`；反过来，`TransformersClient()` 与 `from_pretrained("HamoAI/hamo-score-0.6b")` 加载的是 Hugging Face 的 `main`，自 2026-09-30（UTC）起就是 v9，与工具包版本无关。0.2.0 切到 v9 的是参考服务器、`server/Modelfile` 与自检考卷的标签。
>
> v9 还**没有通过它预注册的五道验收闸门中的两道，其中一道是安全闸门**（来访者表达自杀意念、同时又在求助时，它会把退缩 W 打低——v7 也有这个缺口，v9 没有修好）；它成为默认权重，是 Hamo 创始人明确作出并留档的破例决定。两项失败的完整数字见[模型卡](https://huggingface.co/HamoAI/hamo-score-0.6b#evaluation)——这也是上游危机闸门不可省的又一个理由。
>
> **v7 仍可用**：同一仓库的 `gguf/hamo-score-0.6b-v7.q8.gguf`。走 ollama 五分钟上手的，下载它并把 `server/Modelfile` 的 FROM 指向它；Docker 服务器不读 `server/Modelfile`，须按 `server/docker-compose.yml` 顶部的切换说明操作。v7 safetensors 在固定版本 `ab9dc70c5c25be0eb47cd9a7bf7c70c094b4fb93`：`from_pretrained` 直接传 `revision=`；`TransformersClient` 没有 `revision` 参数，须先按该版本下载快照（`hf download HamoAI/hamo-score-0.6b --revision ab9dc70c5c25be0eb47cd9a7bf7c70c094b4fb93 --exclude "gguf/*" --local-dir ./hamo-score-v7`），再把本地路径传给 `model_id`。按版本号与 GGUF 摘要固定模型、以及其余升级步骤，见[集成指南·从 v7 升级](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/integration.md#中文精编)。

**五分钟上手**：见上方英文段——先 `git clone` 本仓库（`server/Modelfile` 与 `eval/` 在仓库里，不在 pip 包里）→ `hf download` 拉 v9 GGUF（要用 v7 就改拉 `gguf/hamo-score-0.6b-v7.q8.gguf`，并改 `server/Modelfile` 的 FROM）→ `ollama create` → `pip install` → 四行代码跑通 **闸门 → 评分 → 平滑 → 状态桶** 完整链路。切记：分数是逐句信号，永远不要凭单句原始分做任何决定。

**一键服务器**：`git clone` 本仓库后 `cd server && docker compose up`——自动拉 v9 GGUF、建模型、预热，`POST localhost:8080/score` 直接返回 危机/五维分/压力值/状态桶，危机命中的请求永远不会碰到模型。想留在 v7，见 `server/docker-compose.yml` 顶部的切换说明。

**部署自检**：在仓库根目录跑 `python eval/run_exam.py`——195 题合成考卷（教师标注，零真实数据）+ 10 条手写危机闸门用例，对照 [eval/README.md](https://github.com/HamoAI/hamo-score-toolkit/blob/main/eval/README.md) 的官方参考带（v9 bf16 参考值：JSON 合法率 100%、维度级 88.9%、闸门 10/10；合格带：维度级 86–92%、各维 ≥75%、JSON ≥99%、闸门 10/10；随包 v9 q8 GGUF 实测 89.3%）验证你的部署接线正确。考卷的 A、B 标签已按 v9 口径、用给 v9 训练数据打标的同一套教师提示词重标，天然与 v9 同分布；crisp B 口径下大多数标签又是 0——所以过关证明的是接线（提示词、模板、采样、解析）正确，不证明模型质量。故意部署 v7 的，请加 `--labels pre_v9` 对照 v7 参考值（83.5%）。

**想微调到你自己的人群？** 读 [docs/finetune.md](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/finetune.md)——十代模型蒸出来的完整打法：四代拒收的确切原因（两代因危机召回退步，两代没过预注册闸门），以及五道闸门只过三道、由创始人明确破例发布的 v9。内容包括数据红线、真实 LoRA 配方、带危机漏检列的选点表（以及为什么现在改为事先固定受检检查点）、预注册验收闸门。

**更多文档**：[集成指南](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/integration.md)（正确接线 + 十条禁令）、[FAQ](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/faq.md)、[微调指南](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/finetune.md)；[`examples/`](https://github.com/HamoAI/hamo-score-toolkit/tree/main/examples) 里有可跑的快速上手、批量打分与会话监测演示（后两个带 `--mock`，无模型也能看管线；会话监测演示带危机短路）。集成前值得先读模型卡的 [Evaluation](https://huggingface.co/HamoAI/hamo-score-0.6b#evaluation) 与 [Limitations](https://huggingface.co/HamoAI/hamo-score-0.6b#limitations--known-residuals) 两节——包括 v9 没过的两道闸门、为什么 v9 专属考卷上的进步是同分布证据而非真实对话证据，以及为什么参照评分器自身的自洽率（94–98%）只是粗略的实际上限。

**对某个评分不服？请一定告诉我们——这是我们唯一请求的贡献。** [**提一条分歧报告 →**](https://github.com/HamoAI/hamo-score-toolkit/issues/new?template=score_disagreement.md)：给出「消息（可自由脱敏）+ 模型给的分 + 你认为该给的分」三样即可。每一条都会进入人类金标计划分诊：凡持牌从业者与模型的分歧率高过模型自身的噪声底噪，那就是下一代的训练数据缺口。这个模型蒸馏来替代的那个参照评分器，在小规模抽查（每次十来条消息）中自己重打同一句约有 2–6% 不一致——所以「这里模型判错了」是真发现，不是打扰。

**许可证**：工具包代码 Apache-2.0；模型权重 HAMO-RAIL-S 1.0（自由使用附四条限制，用本工具包默认管线即天然满足危机处理条款）。
