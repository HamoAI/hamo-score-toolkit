# hamo-score-toolkit

**EN** | [中文](https://github.com/HamoAI/hamo-score-toolkit#中文)（中文说明在本页下半部分）

Client toolkit and **safety scaffold** for [HamoAI/hamo-score-0.6b](https://huggingface.co/HamoAI/hamo-score-0.6b) —
the little model that takes a conversational pulse (AWEHB: Agency / Withdrawal / Extremity / Hostility / Boundary).

This repo is the missing half of the model: the exact prompt format, tolerant
output parsing, the smoothing-and-buckets math the scores are designed to feed,
and — front and center — the **crisis gate**, a reference implementation of the
independent upstream crisis handling that the model license
([HAMO-RAIL-S §3c](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/LICENSE))
requires in consumer-facing mental-wellness deployments.

> ⚠️ The model is not a chatbot, not a diagnostic instrument, and **not a
> crisis detector**. It scores five dimensions of one message. It does not
> detect or handle crises, and none of its scores — W included — is a crisis
> signal. Crisis handling is the job of deterministic code around the model
> (Hamo calls it "the spine"), which must run before the model on every path
> that feeds it: **the upstream crisis gate is not optional.** The toolkit's
> `CrisisGate` is a keyword list to start from, not a complete screen.

> **Toolkit 0.3.0 moves to hamo-score-0.6b v10. If you moved to v9, read the correction below:
> our advice to "re-tune thresholds" for v9 was not enough.**
>
> - **What v10 scores.** A (Agency) follows rubric v8, as in v9. B (Boundary) is back on the
>   **legacy rubric** that v7 and earlier used; v9's narrower "crisp" B is not in v10. New: on
>   explicit suicidal ideation, v10's training labels cap A at 1.0 and set B to 0, and enforce
>   v9's W floor of 2.5. **Scores are not comparable across versions** (A changed meaning at v9; B
>   changed at v9 and changed back at v10): store the model version with every score and keep
>   versions apart in histories and reports. A under rubric v8 has no real-conversation
>   measurement yet, so check it against a human-scored sample of your own consented
>   conversations before anything relies on it.
> - **Correction about v9.** v9 scores B under the crisp rubric, so B is 0 on most ordinary
>   messages and the relief term of a stress formula with a negative B weight
>   (`hamo_score.stress` is one) disappears: on the 453-turn real final exam the mean raw
>   per-turn stress change computed from v9's scores is +0.37, where the exam's reference
>   labels give −0.68 and v10 −0.72 (pseudonymised conversations of consenting internal staff;
>   each version's shipped q8 GGUF, llama.cpp with Metal). Re-tuning the cut-offs or the B
>   weight cannot repair this — a weight multiplies a zero — so if you feed v9 scores into such
>   a formula, move to v10 or go back to v7, and do not carry stress accumulated from v9 scores
>   into a v10 deployment.
> - **Acceptance status: rejected under the signed pre-registration; released by the founder's
>   decision.** The shipped q8 GGUF met 17 of the 18 checks of the signed pre-registration.
>   The one it did not meet, G5a, was a stand-in for crisis handling, which the founder ruled
>   outside this model after seeing the result; under the registration as signed the verdict
>   was "rejected", and v10 is released by the founder's decision. This is a waiver of one
>   pre-registered gate made after the result was known, and the second release in a row that
>   ships by founder decision after failing a pre-registered gate (v9 failed 2 of 5). Full
>   statement: the model's [technical record](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation) (linked from the model card).
> - **Known B sign flip.** v10 scores the self-erasure sentence 「行，我全听你的，你说哪天去就哪天去。」
>   ("Fine, I'll do whatever you say — we go whichever day you say.") **B 2.5**, where v7 and
>   v9 score 0 (no context; shipped q8 GGUFs, llama.cpp with Metal). v10's sign-flip counts
>   are inside the registered caps, but this sentence is the very example earlier model cards
>   used for "the instrument must not read self-erasure as a boundary": do not read a high B
>   from v10 as proof that a boundary was kept ([FAQ](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/faq.md)).
> - **The pip version does not choose the model.** `pip install -U hamo-score` changes no
>   weights: an ollama model keeps serving the GGUF it was created from, and
>   `TransformersClient()` and `from_pretrained("HamoAI/hamo-score-0.6b")` load Hugging Face
>   `main`, which is v10 from 2026-10-06 (UTC) and was v9 from 2026-09-30 until then. The
>   reference server registers the unversioned ollama name `hamo-score-0.6b`, so
>   `docker compose up` from 0.3.0 replaces whatever that name served before with v10.
> - **v9 and v7 remain available.** `gguf/hamo-score-0.6b-v9.q8.gguf` and
>   `gguf/hamo-score-0.6b-v7.q8.gguf` sit next to the v10 file on `main`; their safetensors
>   are at pinned revisions. Digests, revisions, how to pin or switch (ollama, Docker,
>   transformers) and the remaining upgrade steps:
>   [Upgrading to v10](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/integration.md#upgrading-to-v10).
> - **0.3.1:** documentation only — crisis handling is outside the model's scope, and the
>   documents no longer assess the model against it; no change to code behaviour, weights
>   or exam.

> 💬 **Think a score is wrong? Tell us — it is the one contribution we ask for.**
> [**Open a disagreement report →**](https://github.com/HamoAI/hamo-score-toolkit/issues/new?template=score_disagreement.md)
> with the message (redact freely — we don't want identifiable text), the model version or
> file, the score the model gave and the score you would give. We collect these reports as
> input for human review of the rubric and of future versions.

## 5-minute start (ollama)

```bash
# 0. clone this repo — server/Modelfile and eval/ live here, not in the pip package
git clone https://github.com/HamoAI/hamo-score-toolkit.git && cd hamo-score-toolkit

# 1. get the model (one-time) — v10; for v9 or v7, fetch that version's GGUF instead and edit FROM in server/Modelfile
hf download HamoAI/hamo-score-0.6b gguf/hamo-score-0.6b-v10.q8.gguf --local-dir /tmp/hamo
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
    print(r.scores)             # v10: {'A': 2.0, 'W': 0.0, 'E': 0.0, 'H': 0.0, 'B': 2.0}
    stress = update_stress(r.scores, current_stress=3.0)
    print(energy_state(stress)) # 'positive' / 'negative' / 'neurotic'
```

That's the whole intended shape: **gate → score → smooth → bucket**. Scores are
per-message signals; never act on a single raw score.

The read-out in the comment is from the shipped v10 q8 GGUF (llama.cpp with
Metal). On this input the v9 q8 GGUF returns B 0.0 and the v7 q8 GGUF B 1.5,
both with W 0.5: if you see one of those, check which GGUF your model was built
from.

Keep sampling neutral: temperature 0, `repeat_penalty 1.0`, `top_k 0`,
`top_p 1.0`. The toolkit's clients and `server/Modelfile` already do; set all
four yourself if you call the model any other way. At `repeat_penalty 1.1`
(ollama's default), fabrication on the old B exam (legacy key) — no-boundary
items (five classes) and low arms of pairs scored B ≥ 1.0 — rises from 3/104
(2.9%) to 15/104 (14.4%) for the shipped v10 q8 GGUF (llama.cpp with Metal).

## One-command server (Docker)

Run the whole pipeline as an HTTP service:

```bash
git clone https://github.com/HamoAI/hamo-score-toolkit.git && cd hamo-score-toolkit/server
docker compose up          # downloads the v10 GGUF (639MB, one-time), creates + warms the model
```

```bash
curl -s localhost:8080/score -H 'content-type: application/json' \
  -d '{"message": "虽然还是有点提不起劲，不过今天把拖了两周的体检约上了", "history": [{"role": "assistant", "content": "这周过得怎么样？"}], "current_stress": 3.0}'
# → {"crisis": {"triggered": false, "matched": []}, "scores": {"A": 2.0, "W": 0.0, "E": 0.0, "H": 0.0, "B": 2.0}, "latency_ms": ..., "stress": 2.4, "energy_state": "positive"}
```

The scores in this sample are the read-out given above (v10 q8 GGUF, llama.cpp
with Metal); `stress` and `energy_state` follow from them. We have no recorded
run of this request through the Docker server (the same GGUF through ollama on
CPU), where a read-out can occasionally differ: in a 100-item check of this
GGUF, ollama on an ARM CPU server and llama.cpp with Metal agreed exactly on
98 with the server's prompt cache off, and on 95 in an earlier run with it on
(ollama 0.32.5's default, which the reference compose file does not switch
off).

`POST /score` runs gate → score, then smooth → bucket when the request carries
`current_stress`; crisis-gated requests never reach the model. `GET /healthz`
probes the model end-to-end. To serve v9 or v7 instead, follow the note at the
top of `server/docker-compose.yml`.

## Verify your deployment

The toolkit self-check exam: 195 synthetic, teacher-labelled questions plus 10
handwritten crisis-gate cases. Run it from the repo root against your own
deployment, with the label set of the version you serve:

```bash
python eval/run_exam.py                    # v10 labels (default)
python eval/run_exam.py --labels v9        # checking a v9 deployment on purpose
python eval/run_exam.py --labels pre_v9    # checking a v7 deployment on purpose
```

`run_exam.py` calls the ollama endpoint itself (`--base-url`, default
`http://127.0.0.1:11434`), not `POST /score`, and the Docker reference server
does not publish that port. To check that server, add
`ports: ["127.0.0.1:11435:11434"]` to the `ollama` service in
`server/docker-compose.yml`, run `docker compose up` again and pass
`--base-url http://127.0.0.1:11435`. With the defaults the script fails, or
grades whatever a host ollama serves as `hamo-score-0.6b`.

Pass band on the v10 labels: dimension-level 84–90%, each dimension ≥ 75%,
**A ≥ 86%**, JSON ≥ 99%, gate 10/10 (a keyword list; it does not depend on the
model). Reference, on an M1 Pro: 87.3% for both the v10 bf16 safetensors (MLX)
and the shipped q8 GGUF (llama.cpp with Metal, `server/Modelfile` template,
neutral sampling). The A floor separates v10 weights from v7 weights (A 80.5 on
these labels); v9 weights show up as B 57.4. Bands for the other label sets,
trivial baselines, quantization and troubleshooting:
[eval/README.md](https://github.com/HamoAI/hamo-score-toolkit/blob/main/eval/README.md).

**A pass certifies wiring, not model quality.** The labels come from the same
teacher prompts as the training labels, so the exam is in-distribution by
construction, and it runs through the toolkit's own prompt, sampling and
parser, not yours. A constant 0.5 output already scores 77.9% on the v10
labels, so read the per-dimension lines and the distinct-read-out count that
`run_exam.py` prints, not the headline alone.

## What's in the box

| Module | What it gives you |
|---|---|
| `hamo_score.prompt` | The exact prompt format + built-in trimming as a latency guard (3×200-char turns, 500-char message). The real final exam and old B exam figures quoted here were run on full stored context, not this trimming |
| `hamo_score.parse` | Think-block-tolerant JSON parsing, grid snapping |
| `hamo_score.client` | `OllamaClient` / `TransformersClient` (needs `pip install "hamo-score[transformers]"`) + `score_message()` safe pipeline |
| `hamo_score.stress` | Reference smoothing (`0.8·history + 0.2·message`) + energy-state buckets. Weights and cut-offs were set on legacy-rubric scores (v7 and earlier) and v10's A is on a different rubric: check the buckets on your own data before they gate anything. Do not feed it v9 scores |
| `hamo_score.safety` | `CrisisGate` (zh/en word lists, extensible) + AI-disclosure texts |

The default `CrisisGate` word lists are a starting point, not coverage. On the
189 synthetic ideation-plus-help items of the old and new W safety exams the
gate fires on 107. Extend the lists for your population and language.

## Where the details live

| Doc | What's in it |
|---|---|
| [Integration guide](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/integration.md) | Correct wiring, upgrading to v10 (the full correction about v9, pins and digests), the don't list |
| [FAQ](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/faq.md) | Sampling, crisis handling, the known B sign flip |
| [Fine-tuning playbook](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/finetune.md) | Adapting the model to your own population: data red lines, the LoRA recipe, acceptance gates, and the record of twelve adjudicated generations, five of them rejected |
| [`examples/`](https://github.com/HamoAI/hamo-score-toolkit/tree/main/examples) | Quickstart, batch CSV scoring, a session-monitor demo with the crisis short-circuit (the last two take `--mock` to run without a model) |
| Technical record: [Evaluation](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation), [Limitations](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#limitations--known-residuals) | The verdict, the sixteen of the 18 checks that the technical record reports, what was decided after results were seen, and why passing the synthetic exams shows no regression inside the known range, not generalisation |

## License

Toolkit code: **Apache-2.0**. Model weights: **HAMO-RAIL-S 1.0** (free use with
four restrictions — no standalone clinical determinations; not the sole or
primary basis for consequential decisions about an identifiable person, and no
covert monitoring of a person's psychological state; keep independent upstream
crisis handling + AI disclosure in consumer-facing mental-wellness deployments;
no re-identification). The default pipeline puts a gate upstream of the model,
as the crisis-handling clause asks; extending its word lists (measured above)
is your job.

---

# 中文

[hamo-score-0.6b](https://huggingface.co/HamoAI/hamo-score-0.6b) 的客户端工具包与**安全脚手架**——给对话把脉的小模型（AWEHB 五维：行动力/退缩/极端化/敌意/边界）。

这个仓库是模型的另一半：提示词格式、容错解析、分数该喂进去的平滑折算与状态桶，以及放在最前面的**危机闸门**。模型许可证（[HAMO-RAIL-S §3c](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/LICENSE)）要求面向消费者的心理健康类部署在模型上游保留独立的危机处理，危机闸门是这一要求的参考实现。

> ⚠️ 这个模型不是聊天机器人，不是诊断工具，**也不是危机检测器**。它给一条消息的五个维度打分，不识别也不处理危机；它的分数，包括 W 在内，没有一个是危机信号。危机处理由模型外围的确定性代码负责（Hamo 称之为「脊柱」），凡把消息送进模型的路径，这层代码都必须先于模型运行：**上游的危机闸门不可省。** 工具包的 `CrisisGate` 是一份关键词表，只是起点，不是完整筛查。

> **工具包 0.3.0 转向 hamo-score-0.6b v10。已经换到 v9 的，请先读下面的更正：当时让大家为 v9「重调阈值」，这个建议并不够。**
>
> - **v10 打的是什么。** A（行动力）按 v8 口径，与 v9 相同。B（边界感）回到 v7 及更早版本所用的 **legacy 口径**，v9 那套更窄的 crisp B 不在 v10 里。新增：消息含明确的自杀意念时，v10 的训练标签把 A 封顶在 1.0、B 置 0，并落实 v9 已有的 W 下限 2.5。**各版本的分数不可相互比较**（A 的含义在 v9 改过；B 在 v9 改过，v10 又改了回来）：给每个分数存下模型版本，历史与报表按版本分开。v8 口径的 A 至今没有真实对话上的测量，依赖它之前，请先拿你自己授权对话里一批人工打分的样本核对。
> - **关于 v9 的更正。** v9 的 B 按 crisp 口径打分，多数普通消息的 B 是 0，B 为负权重的压力公式（`hamo_score.stress` 就是一个）里减压项随之消失：453 轮真实终评上，按 v9 的分数算出的平均每轮原始压力变化是 +0.37，考卷的参照标签是 −0.68，v10 是 −0.72（假名化的内部员工对话，当事人已授权；各版本随包 q8 GGUF，llama.cpp + Metal）。重调阈值或 B 的权重都修不好，因为权重乘的是 0；把 v9 的分数喂进这类公式的，请换到 v10 或退回 v7，也不要把按 v9 分数累积的压力值带进 v10 的部署。
> - **验收状态：按签字的预注册为「拒收」；由创始人决定发布。** 随包 q8 GGUF 在签字版预注册的 18 项检查里过了 17 项。没过的那一项 G5a 当初是作为危机处理的替代指标设的；创始人看到结果后裁定，危机处理不在本模型里判定，由脊柱负责。按签字的预注册，判定是「拒收」；v10 由创始人决定发布。这是在结果已知之后对一道预注册闸门的豁免，也是连续第二个没过预注册闸门、由创始人决定发布的版本（v9 五道闸门没过两道）。完整说明见模型的[技术档案](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation)（模型卡里有链接）。
> - **已知的一条 B 符号翻转。** 自我消融句「行，我全听你的，你说哪天去就哪天去。」v10 打 **B 2.5**，v7 与 v9 打 0（无上下文；各版本随包 q8 GGUF，llama.cpp + Metal）。v10 的符号翻转条数在预注册的上限之内，但这一句正是此前的模型卡用来说明「仪器不可把自我消融读成边界」的例句：不要把 v10 给出的高 B 当成「守住了边界」的证据（详见 [FAQ](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/faq.md)）。
> - **跑哪个模型不由 pip 版本决定。** `pip install -U hamo-score` 不换任何权重：ollama 里的模型仍跑它创建时用的那个 GGUF；`TransformersClient()` 与 `from_pretrained("HamoAI/hamo-score-0.6b")` 加载的是 Hugging Face 的 `main`，它自 2026-10-06（UTC）起是 v10，此前自 2026-09-30 起是 v9。参考服务器在 ollama 里用不带版本号的模型名 `hamo-score-0.6b`，所以用 0.3.0 执行 `docker compose up`，会把这个名字下原先的模型换成 v10。
> - **v9、v7 仍可用。** `gguf/hamo-score-0.6b-v9.q8.gguf` 与 `gguf/hamo-score-0.6b-v7.q8.gguf` 和 v10 的文件一起放在 `main` 上，两者的 safetensors 在固定版本。摘要、版本号、怎样固定或切换（ollama、Docker、transformers）以及其余升级步骤，见[集成指南·升级到 v10](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/integration.md#升级到-v10)。
> - **0.3.1：** 只改文档——危机处理不在本模型的职责范围内，文档不再拿危机处理来衡量这个模型；代码行为、权重与考卷均无变化。

**五分钟上手**：代码见上方英文段。先 `git clone` 本仓库（`server/Modelfile` 与 `eval/` 在仓库里，不在 pip 包里）；要用 v9 或 v7，就改拉对应的 GGUF，并改 `server/Modelfile` 的 FROM。完整链路是 **闸门 → 评分 → 平滑 → 状态桶**；分数是逐句信号，不要凭单句原始分做任何决定。示例注释里的读数是随包 v10 q8 GGUF 的输出（llama.cpp + Metal）；同一输入，v9 q8 GGUF 给出 B 0.0，v7 q8 GGUF 给出 B 1.5，两者的 W 都是 0.5。打出这两者之一的，请核对模型是用哪个 GGUF 建的。

采样要保持中性：temperature 0、`repeat_penalty 1.0`、`top_k 0`、`top_p 1.0`。工具包的客户端与 `server/Modelfile` 已设好；用别的方式调用模型时，四项都要自己设。`repeat_penalty` 取 1.1（ollama 的默认值）时，随包 v10 q8 GGUF（llama.cpp + Metal）在旧 B 卷（legacy 答案）上的造分（五类没有边界的单题与成对题的低臂被打到 B ≥ 1.0）从 3/104（2.9%）升到 15/104（14.4%）。

**一键服务器**：`cd server && docker compose up`，自动拉 v10 GGUF（639MB，仅首次）、建模型、预热。`POST localhost:8080/score` 返回危机判定与五维分，请求里带 `current_stress` 时另返回压力值与状态桶；危机命中的请求不会送到模型；`GET /healthz` 端到端探活。想改跑 v9 或 v7，见 `server/docker-compose.yml` 顶部的说明。

**部署自检**：工具包自检卷是 195 道合成题（教师标注）加 10 条手写危机闸门用例。在仓库根目录跑 `python eval/run_exam.py`，部署哪个版本就按哪套标签判卷：默认 `--labels v10`，v9 用 `--labels v9`，v7 用 `--labels pre_v9`。`run_exam.py` 直接调用 ollama 接口（`--base-url`，默认 `http://127.0.0.1:11434`），不走 `POST /score`，而 Docker 参考服务器没有把这个端口映射到宿主机：要考它，先在 `server/docker-compose.yml` 的 `ollama` 服务下加 `ports: ["127.0.0.1:11435:11434"]`，重新 `docker compose up`，再带上 `--base-url http://127.0.0.1:11435`。按默认参数，脚本要么报错，要么考到宿主机 ollama 里名为 `hamo-score-0.6b` 的模型。v10 标签的合格带：维度级 84–90%、各维 ≥ 75%、**A ≥ 86%**、JSON ≥ 99%、闸门 10/10（闸门是关键词表，与模型无关）。参考值（M1 Pro）：v10 bf16 safetensors（MLX）与随包 q8 GGUF（llama.cpp + Metal，`server/Modelfile` 的模板加中性采样）都是 87.3%。A 的下限用来区分 v10 与 v7 的权重（v7 在这套标签上 A 为 80.5）；拿成 v9 的权重，B 只有 57.4。另两套标签的合格带、平凡基线、量化与排查办法见 [eval/README.md](https://github.com/HamoAI/hamo-score-toolkit/blob/main/eval/README.md)。

**过关证明的是接线正确，不证明模型质量。** 考卷的标签与训练标签出自同一套教师提示词，天然与模型同分布；它走的是工具包自己的提示词、采样参数与解析器，不检查你自己的。恒定输出 0.5 在 v10 标签上就能得 77.9%，所以不要只看总分，还要看 `run_exam.py` 打印的分维成绩与不同读数的种数。

**模块一览**：`hamo_score.prompt`（提示词格式；内置截断作延迟保护：上下文 3 轮 × 200 字、消息 500 字；本页引用的真实终评与旧 B 卷按完整上下文跑，未经这层截断）、`hamo_score.parse`（容错解析）、`hamo_score.client`（两种客户端与 `score_message()` 安全管线；`TransformersClient` 需 `pip install "hamo-score[transformers]"`）、`hamo_score.stress`（参考平滑与状态桶；权重与阈值按 legacy 口径（v7 及更早）的分数定，而 v10 的 A 是另一套口径：让状态桶把关任何事之前，先用你自己的数据核对；不要把 v9 的分数喂给它）、`hamo_score.safety`（`CrisisGate` 中英词表与 AI 披露文案）。

默认的 `CrisisGate` 词表只是起点，不等于覆盖。新旧两份 W 安全卷合计 189 道合成的「想死但求助」题，闸门命中 107 题。请按你的人群与语言扩充词表。

**细节在哪里**：[集成指南](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/integration.md)（正确接线、升级到 v10、关于 v9 的完整更正、固定版本与摘要、禁令清单）；[FAQ](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/faq.md)（采样、危机处理、已知的 B 符号翻转）；[微调指南](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/finetune.md)（微调到你自己的人群：数据红线、LoRA 配方、验收闸门，以及十二代经过裁定的模型的记录，其中五代拒收）；[`examples/`](https://github.com/HamoAI/hamo-score-toolkit/tree/main/examples)（快速上手、批量打分、带危机短路的会话监测演示，后两个带 `--mock`，无模型也能跑）；技术档案的 [Evaluation](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation) 与 [Limitations](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#limitations--known-residuals)（判定、18 项检查里技术档案报告的 16 项、哪些事是看到结果之后才定的、为什么通过合成考卷只说明在已知范围内没有退步而不说明泛化）。

**对某个评分不服？请告诉我们——这是我们唯一请求的贡献。** [**提一条分歧报告 →**](https://github.com/HamoAI/hamo-score-toolkit/issues/new?template=score_disagreement.md)，给出消息（可自由脱敏，我们不要可识别个人的文字）、模型版本或文件、模型给的分、你认为该给的分。我们收集这些报告，作为人工复核口径与后续版本的输入。

**许可证**：工具包代码 Apache-2.0；模型权重 HAMO-RAIL-S 1.0（自由使用，附四条限制：不得单独据以作临床判定；不得作为对可识别个人作重大决定的唯一或主要依据，也不得用于隐蔽监测他人的心理状态；面向消费者的心理健康类部署须保留独立的上游危机处理并披露 AI 身份；不得重新识别个人）。默认管线按危机处理条款的要求把闸门放在模型上游；扩充默认词表（能拦住多少见上面的实测）是你的责任。
