# Integration guide — wiring the scorer the way it was designed

**EN** | [中文](#中文精编)

The model reads one message and returns five numbers. Everything else — what
those numbers may touch, and what must run before the model — is integration,
and integration is where deployments go right or wrong. This page is the
correct wiring, what changed for integrators in v9, then the don't list.

## The one intended shape

```
message ──▶ CrisisGate ──▶ build_prompt ──▶ model ──▶ parse_scores ──▶ update_stress ──▶ energy_state
             (short-circuit                                              (0.8·history      (positive /
              → human)                                                    + 0.2·now)        negative / neurotic)
```

`score_message()` implements the left half (gate → prompt → generate → parse)
in the safe order; `update_stress()` + `energy_state()` are the right half.
The reference server in [`server/`](../server) wires all of it behind one
`POST /score`.

**Stage 1 — the gate.** Deterministic keyword lists (zh + en), extensible via
`CrisisGate(extra_keywords=[...])`. When it triggers, the message never
reaches the model; your code receives the match and routes to a human, with
the AI disclosure ([`DISCLOSURE_ZH` / `DISCLOSURE_EN`](../src/hamo_score/safety.py))
shown. Required by license §3(c) in consumer-facing mental-wellness
deployments; required by this architecture in all of them.

**Stage 2 — the score.** One prompt format, byte-identical to training
(`build_prompt` — trimming guards included: last 3 turns × 200 chars,
message capped at 500). Temperature 0 with neutral sampling (don't #5), Qwen3
chat template with an empty `<think>` block (see
[`server/Modelfile`](../server/Modelfile)).

**Stage 3 — the smoothing.** `new = 0.8·history + 0.2·clamp(history + delta)`.
Per-message noise is damped ~5× before anything downstream sees it.
Personality-quadrant modifiers (`update_stress(..., quadrant="expert" |
"supporter" | "leader" | "dreamer")`) adjust dimension weights if your product
has that concept; omit otherwise. An
all-zero score is a **no-op by design** — that is what makes scoring
ultra-short messages ("嗯", "ok") safe: 35.5% of our real traffic is under
15 characters, and a harmless no-op beats a blind spot.

**Stage 4 — the buckets.** `energy_state()`: stress `< 4` positive, `< 7`
negative, `≥ 7` neurotic — it takes only the smoothed stress value. These
cut-offs, and the stress weights in Stage 3, were set on **pre-v9 scores**;
read the next section before you let them gate anything on v9.

## Upgrading from v7: A and B changed meaning

v9 has been the default weights on Hugging Face since 2026-09-30 (UTC) and is what
the reference server now serves. It scores two of the five dimensions under
revised rubrics; W, E and H keep their meaning. The same change and the same
rules below apply if you are on v6.1 or an earlier build (including
mradermacher's v4 GGUFs): every released version before v9 scores A and B under the
pre-v9 rubrics. The before/after numbers on this page compare v7 with v9 only.

- **A (Agency)** now means *actively moving the situation or the helping
  relationship forward, not regulating one's own emotions*. A decision,
  asking for help, a healthy habit: high. A one-off walk or run, a practice
  exercise, holding back an impulse, agreeing to pick up next time: mid-band
  (1.0–1.5). Calming yourself down in the moment, or handing a decision to
  someone else: 0–0.5. Farewell and putting-affairs-in-order signals are
  A = 0 — they are crisis signals carried by W, never agency.
- **B (Boundary)** is now "crisp": only boundary markers — a stated need,
  limit, condition or position — count. 0 / 1.0 (one marker that is hedged,
  implied, or not addressed to anyone; wishes and preferences count here) /
  2.0 (one explicit marker addressed to someone) / 2.5–3.0 (a firm limit, or
  two or more markers). Asking the AI for help is 0 (that is A); calm
  self-description without a marker is 0. Earlier versions rewarded calm,
  orderly self-description and positive action with B; v9 does not. On the
  453-turn real final exam, v9's B is `0.0` on 94% of turns (v7: 52%).

**What that does downstream.** In `update_stress`, A and B are the only two
terms that *lower* stress (`delta = 0.9·W + 1.2·E + 1.6·H − 1.0·A − 1.1·B`).
v9 scores both lower — on the real final exam, mean A 0.45 and mean B 0.08,
against 0.67 and 0.92 for v7 (reference labels: 0.84 / 1.02) — so **the same
conversation computes higher stress under v9**, and fixed cut-offs will put it
in a higher bucket more often. The toolkit's stress weights and bucket
cut-offs are unchanged in 0.2.0.

What to do:

1. **Re-tune before buckets gate anything.** Re-fit the cut-offs (and the
   weights, if you rely on them) on real, consented data from your own
   population, scored by the model version you will serve. Until then, let
   the buckets inform a person, not gate behaviour. The toolkit has no knob
   for this: the cut-offs and weights are constants inside `energy_state()`
   and `update_stress()`, and the `energy_state` field returned by the
   reference server's `POST /score` is those pre-v9 cut-offs applied to v9
   scores. Until you re-tune, bucket the returned `stress` with your own
   function (if you re-fit the weights too, compute stress yourself from the
   returned `scores`) instead of consuming that field.
2. **Never mix v7 and v9 scores in one history or trajectory.** Scores are not
   comparable across the v7 → v9 boundary: a stress value built partly from
   v7 scores and partly from v9 scores follows neither rubric, and a trend
   line drawn across the switch shows a step that is the model changing, not
   the person. Store the model version with every score; at the switch,
   start fresh histories (or re-score the stored messages with v9); keep
   analytics and reports per version.
3. **Pin the model version.** `main` on Hugging Face moved from v7 to v9 on
   2026-09-30 (UTC), so `from_pretrained("HamoAI/hamo-score-0.6b")` — and the
   toolkit's `TransformersClient()`, which loads `main` — now gets v9. Pin a
   full commit hash with `revision=` (for `TransformersClient`, pass the local
   path of a snapshot downloaded at a fixed revision as `model_id`), and pin
   GGUF files by digest:

   ```
   v9 q8 GGUF      gguf/hamo-score-0.6b-v9.q8.gguf   sha256 fa189895962c33390bfbc8e86c6fc77e2b5113cbedf6f5105c38a5bc4eabd05f
   v7 q8 GGUF      gguf/hamo-score-0.6b-v7.q8.gguf   sha256 fb1018c8a38ad0da573544b827e42f1685e051c688f8de587cbb81ae1275e3ea
   v7 safetensors  revision ab9dc70c5c25be0eb47cd9a7bf7c70c094b4fb93
   ```

   To stay on v9 when `main` moves again, pin revision
   `7832dafaac1fa6e0af42c3802e498fb08ddbeb58` (the commit that made v9 the
   default).

   The reference server registers the model under the unversioned ollama
   name `hamo-score-0.6b`, so re-running `docker compose up` with toolkit
   0.2.0 replaces v7 with v9 **under the same name**. `docker compose exec
   ollama ollama show hamo-score-0.6b --modelfile` prints the blob digest in
   its `FROM` line; compare it with the digests above to see which version
   you are serving. To stay on v7, follow the comment at the top of
   [`server/docker-compose.yml`](../server/docker-compose.yml).
4. **Treat the upgrade as a scorer change**: shadow v9 next to your current
   scorer, compare, re-tune, then switch (see Operational wiring below).

**What v9 is — and isn't — validated on.** v9 did not pass two of its own
five pre-registered acceptance gates, and one of them is a safety gate: the
synthetic W safety exam (≥ 95% required; 78.9% on the gated bf16 model, 82.2% on the
shipped q8 GGUF; see don't #3). The other was an agreement gate, missed on H by one item out of
453 by the gated bf16 model (the shipped q8 meets it). v9 is the default by
an explicit, recorded override by Hamo's founder; both failures are shown in
full on the [model card](https://huggingface.co/HamoAI/hamo-score-0.6b). Its
large A and B gains were measured on exams that are in-distribution for v9's
own training patches, and no real-conversation measurement under the new A
and B rubrics exists yet — so before anything relies on A or B, check them on
your own real, consented conversations (for example against a human-scored
sample); in your setting that will be the first real-conversation measurement
of those two dimensions. Re-tuning the cut-offs (step 1) is not that check:
fitting thresholds to v9's scores does not tell you whether the scores are
right.
The v7 GGUF stays in the Hugging Face repository for anyone who prefers it.

## Operational wiring

- **Warm-up**: send one throwaway request after every model (re)start, and
  keep `keep_alive=-1` (the toolkit's `OllamaClient` sets it per request).
  A cold model can multiply first-request latency several-fold.
- **Latency budget**: ~0.8 s/message on an M1 Pro; 1.5–2.9 s on a 2-vCPU ARM
  CPU box (q8 GGUF). On slow CPUs the cost is prompt **prefill**, which is
  why the trimming guards exist — resist the urge to send more context.
- **Timeout + fallback**: give the call a hard timeout (the toolkit and
  reference server default to 8 s) and a
  defined fallback — previous scorer, or "skip this message" (a skipped
  score is a no-op thanks to the smoothing). Log every fallback with a
  reason; a fallback rate above a few percent means something is wrong.
- **After any infra change** (new quantization, new runtime, new box):
  `python eval/run_exam.py` (add `--labels pre_v9` if you serve v7) and
  compare to the [reference band](../eval/README.md). Ten minutes, catches
  template and quantization wiring silently costing points.
- **Changing scorers in production?** Moving from v7 to v9 counts. Run the new
  one in shadow first (both score, incumbent decides, every pair logged),
  pre-register your switch criteria, then flip. The fine-tuning guide's
  [§6](finetune.md) gives example switch criteria.

## The don't list

1. **Don't act on a single raw score.** Scores are per-message signals for
   the smoother. The smoothing is not optional decoration; it is the reason
   per-message noise doesn't reach decisions.
2. **Don't remove the gate, and don't replace it with a model.** The gate is
   auditable because it is deterministic: a word list has exactly the gaps
   it has, and a test case either covers a gap or doesn't. Extend the lists
   for your population; never hand the layer to a classifier. This does not
   rule out a second, independent screen (a classifier, say) that runs
   *behind* the gate as an addition — the deterministic gate still runs on
   every message, and the second screen never replaces it (see don't #3).
3. **Don't use the model as a crisis detector.** Its crisis-phrase recall is
   defense-in-depth, never the defense. The gate owns crisis. v9 makes this
   concrete: when explicit suicidal ideation arrives together with
   help-seeking, only 29 of 45 such items on our synthetic W safety exam
   reach the W ≥ 2.5 floor on the shipped q8 GGUF — a gap inherited from v7,
   not fixed. A keyword gate does not close this gap either: ideation phrased
   alongside help-seeking often avoids the listed phrases, so on exactly
   these messages neither the gate nor the model is reliable. Extend the
   lists with such phrasings from your population and test them, and consider
   an independent second screen behind (never instead of) the deterministic
   gate — measuring its recall on your own data before you rely on it.
4. **Don't touch the prompt.** No extra scoring instructions, no reformatting
   — the rubric is baked into the weights, and any deviation from
   `build_prompt` output is silently out-of-distribution.
5. **Don't raise temperature — and don't leave `repeat_penalty` at its default.**
   The task is measurement; sampling noise is measurement error. ollama defaults
   to `repeat_penalty 1.1`, which penalises the repeated `0.0` tokens this model
   emits and pushes scores away from zero. On the shipped v9 q8 GGUF we measured,
   on the crisp Boundary exam, fabrication 1.9% → 2.8% and misses 6.1% → 3.1% —
   the same upward push, not an improvement. That is smaller than on older
   builds (v7 q8 on the v7-era 300-question boundary exam: fabrication
   2.9% → 8.7%, sign flips 0 → 1; v6.1: 13.5% → 25.0%), but the direction never
   changed. Ship `repeat_penalty 1.0`, `top_k 0`, `top_p 1.0`; the toolkit's
   `OllamaClient` sends them with every request (and `TransformersClient`
   decodes greedily with `repetition_penalty=1.0`), and your own clients must
   do the same.
6. **Don't feed more context than the guards allow.** 3 turns × 200 chars is
   what the model saw in training and what your latency budget affords.
7. **Don't quantize below q8 without re-taking the exam.** Every quantization
   comparison we have (Q8_0 vs Q6_K vs Q4_K_M) is on v7 weights; on v9 only
   the shipped Q8_0 has been measured, and no v9 Q6_K or Q4_K_M is published
   or measured. On v7, a
   Q4_K_M kept agreement close but damped withdrawal one-sidedly on
   crisis-adjacent turns — if you build a lower v9 quant, run
   `eval/compare_quants.py` before it gates anything and read its directional
   table, not just the agreement number (see eval/README.md). mradermacher's
   community GGUFs are built from v4 (three releases before v9: pre-v9 A and B
   rubrics, before the W repair, never measured); no recommendation covers them.
8. **Don't treat B (Boundary) as a relationship diagnosis.** It measures the
   linguistic footprint of self-differentiation in one message — under v9,
   whether the message states a need, limit, condition or position — nothing
   more. And don't read a B of `0.0` as a warning sign: under v9 it is the
   normal case (94% of real final-exam turns).
9. **Don't tune bucket thresholds against synthetic data, and don't carry
   them across versions.** Calibrate thresholds only on real, consented data
   from your own population, scored by the model version you serve.
   Thresholds tuned on v7 scores do not transfer to v9, and v7 and v9 scores
   must never share one stress history or trend line (see
   [Upgrading from v7](#upgrading-from-v7-a-and-b-changed-meaning)).
10. **Don't skip the AI disclosure** in consumer-facing deployments — it is
    a license requirement, and the toolkit ships ready-made texts.

---

# 中文精编

**唯一设计形状**：`消息 → 危机闸门 → build_prompt → 模型 → parse_scores →
update_stress → energy_state`。左半段由 `score_message()` 按安全顺序实现，
右半段是 `0.8·历史 + 0.2·本句` 平滑加 `<4 / <7 / ≥7` 三桶（压力权重与这三档阈值
都是按 v9 之前的分数定的，让它们在 v9 上把关任何事之前，先读下面「从 v7 升级」）；
`server/` 里的参考服务器把整条管线接成一个 `POST /score`。闸门命中即短路——消息永不抵达模型，
转人工并展示 AI 披露文案（许可证 §3(c) 对面向消费者心理健康部署的硬性要求）。
评分用温度 0 加中性采样（见禁令 ⑤）。全零分数在构造上是无操作，所以超短消息（「嗯」）放心评——无害的无操作胜过盲区。

**从 v7 升级：A、B 的含义变了**。v9 自 2026-09-30（UTC）起是 Hugging Face 上的默认权重，参考服务器
现在跑的也是它；它按修订后的口径打 A 与 B，W、E、H 含义不变。以下各条同样适用于 v6.1 及更早版本
（包括 mradermacher 的 v4 GGUF）：v9 之前发布的所有版本都按旧口径打 A、B。本页的前后对比数字只比较 v7 与 v9。
- **A（行动力）**：现在指「主动推动处境或疗愈关系向前，不含情绪调节」。做决定、主动求助、坚持健康
  习惯为高；单次散步或跑步、做练习、克制冲动、约好下次再聊为中档（1.0–1.5）；当下平复情绪、把决定
  交给别人为 0–0.5；告别、安排后事类信号一律 A = 0——那是由 W 承担的危机信号，永远不算行动力。
- **B（边界感）**：改为 crisp 口径，只算边界标记——说出的需要、界限、条件或立场。阶梯为 0 / 1.0
  （一个含糊、隐含或不针对任何人的标记；许愿与偏好也在这一档）/ 2.0（一个明确、对人说出的标记）/
  2.5–3.0（坚定的界限，或两个以上标记）。向 AI 求助为 0（那归 A 管）；没有标记的平静自述为 0。
  早先版本会因平静有条理的自述、积极行动而给 B，v9 不再这样做。453 题真实终评上，v9 的 B 有 94%
  为 `0.0`（v7 为 52%）。

**下游后果**：`update_stress` 里 A、B 是仅有的两个**降压**项（`delta = 0.9·W + 1.2·E + 1.6·H − 1.0·A − 1.1·B`），
而 v9 把两者都打得更低（真实终评平均 A 0.45、平均 B 0.08，v7 为 0.67 与 0.92，参照标签为 0.84 与 1.02），
所以**同一段对话在 v9 下算出的压力更高**，固定阈值会更常把它归进更高的桶。工具包 0.2.0 的压力权重与分桶阈值没有改。

**该怎么做**：
1. **让分桶把关任何事之前先重调**：用你自己人群的真实、授权数据，以你要上线的版本打分，重拟阈值
   （若依赖权重，一并重拟）。重调之前，分桶只供人参考，不要用它控制系统行为。工具包没有为此提供调节开关：
   阈值与权重是 `energy_state()`、`update_stress()` 里的常量，参考服务器 `POST /score` 返回的 `energy_state`
   字段就是拿这组 v9 之前的阈值去套 v9 的分数。重调之前，请用你自己的函数给返回的 `stress` 分桶（若连权重也重拟，
   就用返回的 `scores` 自己算压力），不要直接使用那个字段。
2. **v7 与 v9 的分数永不混进同一条历史或轨迹**：两版分数跨 v7 → v9 不可比——一半来自 v7、一半来自 v9
   累积出的压力值哪套口径都不符合，跨切换点画出的趋势线会出现一个台阶，那是模型变了，不是人变了。
   每个分数都记下模型版本；切换时新开历史（或用 v9 重评存档的消息）；统计与报表按版本分开。
3. **固定模型版本**：Hugging Face 的 `main` 已于 2026-09-30（UTC）由 v7 换成 v9，所以
   `from_pretrained("HamoAI/hamo-score-0.6b")` 以及工具包的 `TransformersClient()`（加载 `main`）现在拿到的
   都是 v9。请用 `revision=` 固定完整提交哈希（`TransformersClient` 则把按固定版本下载的快照本地路径
   传给 `model_id`），GGUF 按摘要固定：

   ```
   v9 q8 GGUF      gguf/hamo-score-0.6b-v9.q8.gguf   sha256 fa189895962c33390bfbc8e86c6fc77e2b5113cbedf6f5105c38a5bc4eabd05f
   v7 q8 GGUF      gguf/hamo-score-0.6b-v7.q8.gguf   sha256 fb1018c8a38ad0da573544b827e42f1685e051c688f8de587cbb81ae1275e3ea
   v7 safetensors  revision ab9dc70c5c25be0eb47cd9a7bf7c70c094b4fb93
   ```

   若想在 `main` 再次变动后仍停在 v9，请固定版本 `7832dafaac1fa6e0af42c3802e498fb08ddbeb58`
   （v9 成为默认的那次提交）。

   参考服务器在 ollama 里注册的是不带版本的模型名 `hamo-score-0.6b`，所以用工具包 0.2.0 重跑
   `docker compose up`，会在**同一个名字下**把 v7 换成 v9。`docker compose exec ollama ollama show
   hamo-score-0.6b --modelfile` 会在 `FROM` 行打印 blob 摘要，拿它与上面的摘要比对，就知道实际跑的是哪个版本；
   要留在 v7，按
   [`server/docker-compose.yml`](../server/docker-compose.yml) 顶部的注释修改。
4. **把升级当作换评分器**：先让 v9 跟现役评分器并跑影子、对照、重调，再切换（见下面的运维接线）。

**v9 验证到了什么、没验证什么**：v9 没有通过它自己预注册的五道验收闸门中的两道，其中一道是安全闸门——
合成 W 安全卷（门槛 ≥95%；受检的 bf16 模型 78.9%，随包 q8 GGUF 82.2%；见禁令 ③）；另一道是一致率闸门，受检的 bf16 模型在 H 上差
453 题中的 1 题（随包 q8 达标）。v9 成为默认权重，是 Hamo 创始人明确作出并留档的破例决定，两项失败在
[模型卡](https://huggingface.co/HamoAI/hamo-score-0.6b)上全部列出。A、B 的大幅进步是在与 v9 自身训练补丁
同分布的考卷上测得的，新 A、B 口径下还没有任何真实对话上的测量——所以在任何东西依赖 A、B 之前，
先用你自己的真实、授权对话（例如一批人工打分的样本）检查这两维；在你的场景里，那将是它们第一次真实对话上的测量。
重调阈值（第 1 步）不算这项检查：让阈值去贴合 v9 的分数，说明不了这些分数对不对。v7 的 GGUF 仍保留在 Hugging Face 仓库，供想继续用它的人取用。

**运维接线**：模型重启后预热一发、`keep_alive=-1`；调用设硬超时（工具包与参考
服务器默认 8 秒）并定义回落（旧评分器或跳过——跳过因平滑而无损），回落必记原因；延迟参考
M1 Pro ~0.8 秒、2 vCPU ARM ~1.5–2.9 秒，慢 CPU 的成本在 prefill——这正是
截断护栏存在的原因；任何基建变更后重跑 `eval/run_exam.py`（跑 v7 的部署加 `--labels pre_v9`）
对照参考带；生产换评分器（v7 → v9 也算）先跑影子模式、切换标准预注册（微调指南 §6 给出了切换标准的示例）。

**十条禁令**：① 永不凭单句原始分做决定；② 永不拆闸门、永不用模型替代闸门（在闸门之后另加一道独立筛查、例如分类器，不在此列——它只是加法，
确定性闸门仍对每条消息照跑、永不被取代，见禁令 ③）；
③ 永不把模型当危机检测器（召回是纵深防御，不是防线）——v9 让这一条落到实处：明确自杀意念与求助同时出现时，
我们合成 W 安全卷上的这类题，随包 q8 GGUF 只有 29/45 达到 W ≥2.5 的下限，这个缺口承袭自 v7、并未修好；
关键词闸门也补不上这个缺口：与求助一起出现的自杀意念，措辞常常绕开词表里的说法，所以恰恰在这类消息上，
闸门和模型都靠不住。请用你人群里的这类说法扩充词表并逐条测试，并考虑在确定性闸门之后（永不替代它）
再加一道独立筛查——依赖它之前，先在自己的数据上量它的召回率；
④ 永不改提示词（细则已烧进权重，偏离即静默出分布）；⑤ 永不升温度，也永不放任 `repeat_penalty` 用默认值
（ollama 默认 1.1 会惩罚本模型输出里重复的 `0.0`，把分数推离 0——随包 v9 q8 GGUF 在 crisp 边界卷上实测
造分 1.9%→2.8%、漏判 6.1%→3.1%，同样是往上推，不是改进；比旧版本小——v7 q8 在 v7 时代的 300 题边界判别卷上
造分 2.9%→8.7%、符号翻转 0→1，v6.1 为 13.5%→25.0%——但方向从未变过；须设 `repeat_penalty 1.0`、`top_k 0`、
`top_p 1.0`，工具包的 `OllamaClient` 每次请求都会带上（`TransformersClient` 用贪心解码并显式设
`repetition_penalty=1.0`），你自己的客户端也必须照做）；
⑥ 永不超出截断护栏喂上下文；⑦ 量化低于 q8 必须重考试：我们所有的量化对比（Q8_0 / Q6_K / Q4_K_M）都在 v7 权重上；v9 只量过随包
Q8_0，没有发布、也没有量过 v9 的 Q6_K / Q4_K_M；v7 的 Q4_K_M 一致率接近，但在危机相邻样本上单边压低退缩分——
自行量化 v9 后，先跑 `eval/compare_quants.py` 再让它把关任何事，并看方向性表格而不只看一致率；
mradermacher 的社区 GGUF 量化自 v4（比 v9 早三个版本：早于 v9 的 A/B 口径与 W 修复，也没人量过），不在任何建议范围内；
⑧ 永不把 B 当关系诊断（它只测单句里自我分化的语言足迹——在 v9 下即这句话有没有说出需要、界限、条件或立场），
也别把 B = `0.0` 当警讯：在 v9 下这是常态（真实终评 94%）；⑨ 永不用合成数据校准阈值，也永不跨版本沿用阈值——
只用自己人群的真实授权数据、以所上线的版本打分来校准；v7 上调好的阈值不适用于 v9，v7 与 v9 的分数永不共用
一条压力历史或趋势线；⑩ 面向消费者的部署永不省略 AI 身份披露（工具包带现成文案）。
