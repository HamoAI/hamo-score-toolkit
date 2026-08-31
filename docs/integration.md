# Integration guide — wiring the scorer the way it was designed

**EN** | [中文](#中文精编)

The model reads one message and returns five numbers. Everything else — what
those numbers may touch, and what must run before the model — is integration,
and integration is where deployments go right or wrong. This page is the
correct wiring, then the don't list.

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
message capped at 500). Temperature 0, Qwen3 chat template with an empty
`<think>` block (see [`server/Modelfile`](../server/Modelfile)).

**Stage 3 — the smoothing.** `new = 0.8·history + 0.2·clamp(history + delta)`.
Per-message noise is damped ~5× before anything downstream sees it.
Personality-quadrant modifiers (`update_stress(..., quadrant="expert" |
"supporter" | "leader" | "dreamer")`) adjust dimension weights if your product
has that concept; omit otherwise. An
all-zero score is a **no-op by design** — that is what makes scoring
ultra-short messages ("嗯", "ok") safe: 35.5% of our real traffic is under
15 characters, and a harmless no-op beats a blind spot.

**Stage 4 — the buckets.** `energy_state()`: stress `< 4` positive, `< 7`
negative, `≥ 7` neurotic — it takes only the smoothed stress value.

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
  `python eval/run_exam.py` and compare to the
  [reference band](../eval/README.md). Ten minutes, catches template and
  quantization wiring silently costing points.
- **Changing scorers in production?** Run the new one in shadow first
  (both score, incumbent decides, every pair logged), pre-register your
  switch criteria, then flip. We ran this exact play; the fine-tuning guide
  [§6](finetune.md) has the numbers.

## The don't list

1. **Don't act on a single raw score.** Scores are per-message signals for
   the smoother. The smoothing is not optional decoration; it is the reason
   per-message noise doesn't reach decisions.
2. **Don't remove the gate, and don't replace it with a model.** The gate is
   auditable because it is deterministic: a word list has exactly the gaps
   it has, and a test case either covers a gap or doesn't. Extend the lists
   for your population; never hand the layer to a classifier.
3. **Don't use the model as a crisis detector.** Its crisis-phrase recall is
   defense-in-depth, never the defense. The gate owns crisis.
4. **Don't touch the prompt.** No extra scoring instructions, no reformatting
   — the rubric is baked into the weights, and any deviation from
   `build_prompt` output is silently out-of-distribution.
5. **Don't raise temperature — and don't leave `repeat_penalty` at its default.**
   The task is measurement; sampling noise is measurement error. ollama defaults
   to `repeat_penalty 1.1`, which penalises the repeated `0.0` tokens this model
   emits and silently inflates scores away from zero (we measured fabrication
   13.5% → 25.0% on our own exam). Ship `repeat_penalty 1.0`, `top_k 0`,
   `top_p 1.0`.
6. **Don't feed more context than the guards allow.** 3 turns × 200 chars is
   what the model saw in training and what your latency budget affords.
7. **Don't quantize below q8 without re-taking the exam.** q4 and below is
   where JSON validity and agreement start to crumble.
8. **Don't treat B (Boundary) as a relationship diagnosis.** It measures the
   linguistic footprint of self-differentiation in one message, nothing more.
9. **Don't tune bucket thresholds against synthetic data.** Calibrate
   thresholds only on real, consented data from your own population.
10. **Don't skip the AI disclosure** in consumer-facing deployments — it is
    a license requirement, and the toolkit ships ready-made texts.

---

# 中文精编

**唯一设计形状**：`消息 → 危机闸门 → build_prompt → 模型 → parse_scores →
update_stress → energy_state`。左半段由 `score_message()` 按安全顺序实现，
右半段是 `0.8·历史 + 0.2·本句` 平滑加 `<4 / <7 / ≥7` 三桶；`server/` 里的参考
服务器把整条管线接成一个 `POST /score`。闸门命中即短路——消息永不抵达模型，
转人工并展示 AI 披露文案（许可证 §3(c) 对面向消费者心理健康部署的硬性要求）。
全零分数在构造上是无操作，所以超短消息（「嗯」）放心评——无害的无操作胜过盲区。

**运维接线**：模型重启后预热一发、`keep_alive=-1`；调用设硬超时（工具包与参考
服务器默认 8 秒）并定义回落（旧评分器或跳过——跳过因平滑而无损），回落必记原因；延迟参考
M1 Pro ~0.8 秒、2 vCPU ARM ~1.5–2.9 秒，慢 CPU 的成本在 prefill——这正是
截断护栏存在的原因；任何基建变更后重跑 `eval/run_exam.py` 对照参考带；生产
换评分器先跑影子模式、切换标准预注册（见微调指南 §6）。

**十条禁令**：① 永不凭单句原始分做决定；② 永不拆闸门、永不用模型替代闸门；
③ 永不把模型当危机检测器（召回是纵深防御，不是防线）；④ 永不改提示词（细则
已烧进权重，偏离即静默出分布）；⑤ 永不升温度，也永不放任 `repeat_penalty` 用默认值（ollama 默认 1.1 会惩罚本模型输出里重复的 `0.0`，静默把分数推高——实测造分率 13.5%→25.0%；须设 `repeat_penalty 1.0`、`top_k 0`、`top_p 1.0`）；
⑥ 永不超出截断护栏喂上下文；⑦ 量化低于 q8 必须重考试；⑧ 永不把 B 当关系
诊断（它只测单句里自我分化的语言足迹）；⑨ 永不用合成数据校准阈值；⑩ 面向
消费者的部署永不省略 AI 身份披露（工具包带现成文案）。
