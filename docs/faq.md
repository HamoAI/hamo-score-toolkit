# FAQ

**EN** | [中文](#中文)

**Why must the template contain an empty `<think>` block?**
The student is a Qwen3 base fine-tuned with thinking disabled; at serve time
the template pre-fills an empty think block so the model goes straight to the
JSON. Without it the model may emit its own think text — and under the
recommended `num_predict 80` cap the JSON is often cut off before it appears,
so expect parse failures, not just latency. This is the #1 wiring mistake;
copy [`server/Modelfile`](../server/Modelfile) as-is.

**Why temperature 0?**
Scoring is measurement. Sampling noise is measurement error, and the 0.5 grid
gives it nowhere useful to go. All official numbers are measured at 0.

**The first request after startup is slow / times out.**
Cold start. Send one warm-up request after every model (re)start and keep
`keep_alive=-1` (the toolkit's client sets it per request). If later requests
are still slow, the cost is prompt prefill on a slow CPU — check that you are
not exceeding the trimming guards.

**My output isn't valid JSON.**
`parse_scores()` returns `None`; treat it as "skip this message" (a no-op via
the smoothing) — never crash, never guess. If it happens on more than ~1% of
messages, your wiring is broken: check the empty think template, temperature 0,
and `num_predict ≥ 80`. Then run `eval/run_exam.py` — JSON validity below 99%
always has a wiring cause.

**Which languages does it support?**
Chinese-primary: the training corpus was ~60% zh, ~22% mixed code-switching,
~18% en. English works; expect the weaker side of the band. Other languages
are untested — that's what [fine-tuning](finetune.md) is for.

**What about ultra-short messages like "嗯" or "ok"?**
Score them, with context attached. An all-zero result is a designed no-op —
harmless. In our real traffic 35.5% of messages are under 15 characters;
skipping them creates a blind spot exactly where distressed people go terse.

**Can I send more conversation context for better accuracy?**
No. `build_prompt` trims to the last 3 turns × 200 chars (message capped at
500) because that is what the model saw in training — and on CPU boxes,
prefill on longer contexts is what blows latency budgets. More context is
out-of-distribution *and* slower.

**Do I need a GPU?**
No. q8 GGUF on a 2-vCPU ARM server scores in 1.5–2.9 s; an M1 laptop ~0.8 s
(bf16 via MLX). Stay at q8 — below that, JSON validity and agreement start to crumble.

**Is it a crisis detector?**
No, and it must never be deployed as one. Crisis handling is the deterministic
`CrisisGate` upstream — a license requirement (§3c) in consumer-facing
mental-wellness deployments. The model's own crisis-phrase recall is
defense-in-depth, never the defense.

**Why does my exam score say 84% when the model card says 85.6%?**
Different exams. 85.6%/96.2% (v6.1) is graded on the real 453-turn held-out
final, which never leaves the building. The shipped synthetic exam is a
different paper whose job is to certify *your wiring*, not the model —
what matters is landing inside the 81–86% band.

**Can I fine-tune it on my own data?**
Yes — [docs/finetune.md](finetune.md) is the full six-generation playbook,
data red lines first. Your fine-tuned weights remain under HAMO-RAIL-S (the
guide's §8 covers what you owe).

**What exactly do the two licenses cover?**
This repo's code: Apache-2.0, no restrictions. The model weights: HAMO-RAIL-S
1.0 — free commercial use with four restrictions (no standalone clinical
determinations; no consequential decisions about identifiable individuals; keep
independent upstream crisis handling + AI disclosure in consumer mental-wellness
deployments; no re-identification). The toolkit's default pipeline satisfies
the crisis-handling half of that clause by construction; showing the AI
disclosure (ready-made texts included) is still on you.

**I think a score is wrong.**
Maybe! The reference scorer it replaced disagrees with itself 2–6% of the time
on repeat runs. If a *pattern* of disagreement persists, file the
**score disagreement** issue template — reports feed the human gold-label
program that steers future versions.

---

# 中文

**为什么模板必须带空 `<think>` 块？** 学生是关闭思考训练的 Qwen3，模板预填
空 think 让它直接吐 JSON。没有它模型会自己「想」——在推荐的 80 token 输出帽下，
JSON 常常还没吐出来就被截断：等着你的是解析失败，不只是延迟。
这是第一大接线错误，照抄 `server/Modelfile`。

**为什么温度必须 0？** 评分是测量，采样噪声就是测量误差。官方数字全部测于 0。

**启动后第一条请求慢/超时？** 冷启动。重启后预热一发，`keep_alive=-1`（调用
设硬超时，工具包与参考服务器默认 8 秒）。之后
仍慢就是慢 CPU 的 prefill 成本——检查是否超出截断护栏。

**输出不是合法 JSON？** `parse_scores()` 返回 `None`，按「跳过本句」处理
（平滑使其无损）——不崩溃、不瞎猜。超过 ~1% 就是接线坏了：查空 think 模板、
温度 0、`num_predict ≥ 80`，再跑自检考卷。

**支持哪些语言？** 中文为主（语料 zh 60% / 混杂 22% / en 18%）。英文可用但
偏合格带弱侧；其他语言未测——那是微调指南的活。

**「嗯」这类超短消息评不评？** 评，带上下文评。全零=无操作，无害。真实流量
35.5% 是 15 字以内短消息——跳过它们等于在人最沉默的地方开盲区。

**多喂点上下文会不会更准？** 不会。3 轮×200 字是模型训练时见过的形状，超出
即出分布，且慢 CPU 的 prefill 会吃爆延迟预算。

**需要 GPU 吗？** 不需要。2 vCPU ARM 服务器 q8 1.5–2.9 秒，M1 笔记本 ~0.8 秒
（MLX bf16）。
量化守住 q8。

**它是危机检测器吗？** 不是，也永远不许当危机检测器部署。危机归上游确定性
闸门（许可证 §3c）；模型的危机语召回只是纵深防御。

**为什么我考出 84% 而模型卡写 85.6%？** 两张不同的卷子。85.6%/96.2% 判于
453 条真实终评卷（永不出门）；随包的是另一张合成卷，任务是认证**你的接线**——
落在 81–86% 合格带内即正确。

**能用自己的数据微调吗？** 能——[微调指南](finetune.md)是完整六代打法，数据
红线在最前。微调出的权重仍受 HAMO-RAIL-S 约束（指南 §8）。

**评分不服怎么办？** 可能你是对的！被替换的参照评分器自己重打同句也有 2–6%
不一致。成规律的分歧请用「评分分歧」issue 模板提交——报告直接喂给引导后续
版本的人类金标计划。
