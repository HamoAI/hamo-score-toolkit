# FAQ

**EN** | [中文](#中文)

**Why must the template contain an empty `<think>` block?**
The student is a Qwen3 base fine-tuned with thinking disabled; at serve time
the template pre-fills an empty think block so the model goes straight to the
JSON. Without it the model may emit its own think text — and under the
recommended `num_predict 80` cap the JSON is often cut off before it appears,
so expect parse failures, not just latency. This is the #1 wiring mistake;
copy [`server/Modelfile`](../server/Modelfile) as-is.

**Why temperature 0 — and why must I also neutralise `repeat_penalty`?**
Scoring is measurement. Sampling noise is measurement error, and the 0.5 grid
gives it nowhere useful to go. All official numbers are measured at temperature 0
**with no repetition penalty**.

This second half bites hard and silently. **ollama defaults to
`repeat_penalty 1.1`**, and this model's output — `{"A": 0.0, "W": 0.0, "E": 0.0,
"H": 0.0, "B": 0.0}` — is deliberately repetitive. Penalising repeated tokens
pushes scores *away from 0*, i.e. it fabricates signal. We measured it on our own
300-question boundary exam, same weights, sampling as the only variable. On the
shipped v9 q8 GGUF (exam graded under the crisp B rubric), switching from 1.0 to
1.1 takes the fabrication rate **1.9% → 2.8%**; boundary sign-flips (a `0.0`
scored `≥2.0`) stay at 0, and the miss rate falls (6.1% → 3.1%) — the same
upward push, not an improvement. On older builds (v7-era grading) the effect was
larger: the v7 q8 GGUF went **2.9% → 8.7%** fabrication and **0 → 1** sign-flips;
v6.1 went 13.5% → 25.0% and 6 → 10. Smaller on v9, same direction. The weights
were fine; the runtime was not. Always ship `repeat_penalty 1.0`, `top_k 0`,
`top_p 1.0` — [`server/Modelfile`](../server/Modelfile) has them.

**The first request after startup is slow / times out.**
Cold start. Send one warm-up request after every model (re)start and keep
`keep_alive=-1` (the toolkit's client sets it per request; the client and the
reference server default to an 8-second hard timeout). If later requests
are still slow, the cost is prompt prefill on a slow CPU — check that you are
not exceeding the trimming guards.

**My output isn't valid JSON.**
`parse_scores()` returns `None`; treat it as "skip this message" (a no-op via
the smoothing) — never crash, never guess. If it happens on more than ~1% of
messages, your wiring is broken: check the empty think template, temperature 0,
and `num_predict ≥ 80`. Then run `eval/run_exam.py` — JSON validity below 99%
always has a wiring cause.

**Which languages does it support?**
Chinese-primary: about 76% zh, 13% en and 11% mixed zh-en code-switching,
measured on the latest message of each v9 training row. English works but is
less tested. Other languages are untested — that's what
[fine-tuning](finetune.md) is for.

**What about ultra-short messages like "嗯" or "ok"?**
Score them, with context attached. An all-zero result is a designed no-op —
harmless. Short messages are common in real conversations; skipping them
creates a blind spot exactly where distressed people go terse.

**Can I send more conversation context for better accuracy?**
Not usefully. The model was trained with up to 5 prior turns (some longer than
200 chars); `build_prompt` keeps only the last 3 turns × 200 chars (message
capped at 500) as a latency guard — on CPU boxes, prefill on longer contexts is
what blows latency budgets — and the guard was validated to preserve 98.1%
score self-agreement (±0.5). More than 5 turns is out-of-distribution; anything
between the guard and 5 turns is just slower.

**Do I need a GPU?**
No. q8 GGUF on a 2-vCPU ARM server scores in 1.5–2.9 s; an Apple M1 Pro ~0.8 s
(bf16 via MLX). Where scores gate behaviour, use the shipped Q8_0 — **for v9 it
is the only build we have measured.** Our quantization comparison was run on v7
weights only: there, a self-made Q6_K was indistinguishable from Q8_0 on our
internal 453-turn final split, while Q4_K_M pulled W down on crisis-adjacent
turns and suited only research or human-read scores. We publish no v9 Q6_K or
Q4_K_M; if you quantize v9 yourself, run `eval/compare_quants.py` against the
shipped Q8_0 before letting it gate anything, and assume anything unmeasured is
worse. The community GGUFs were made from the v4 weights — three releases before
v9, before its A/B rubrics and W repair — have never been validated (our only
run of them was a superseded, version-confounded comparison), and no
recommendation covers them. See [eval/README.md](../eval/README.md).

**Is it a crisis detector?**
No, and it must never be deployed as one. Crisis handling is the deterministic
`CrisisGate` upstream — a license requirement (§3c) in consumer-facing
mental-wellness deployments. The model's own crisis-phrase recall is
defense-in-depth, never the defense. v9 makes this more than a formality: when
suicidal ideation arrives together with help-seeking, it under-scores W (on the
shipped q8, only 29 of 45 such synthetic items reach the required W ≥ 2.5) —
the safety gate v9 failed. The gap is inherited from v7, not introduced by v9:
v7 is no better on these items (both leave 5 of the 45 below W 1.0), so rolling
back to v7 does not close it. Nor does the bundled gate on its own: `CrisisGate`
is a short keyword list, and it fires on only 26 of those 45 items — and on only
7 of the 19 that the gated bf16 weights leave below W 2.5. Ideation phrased
alongside help-seeking often slips past a word list. Extend the lists for your
population, add a second screen alongside the gate (never instead of it), and
measure its recall on your own data before relying on it.

**v9 scores B as 0 on most messages, and my stress went up after upgrading. Is it broken?**
No — the rubric changed, and your thresholds have to follow it. v9 scores A and
B under revised rubrics. **B** now counts only boundary markers — a stated need,
limit, condition or position; calm, orderly self-description and positive action
no longer earn B, and asking the AI for help is A, not B. **A** now means
actively moving the situation or the helping relationship forward; calming
yourself down in the moment is coping (0–0.5), and a one-off walk or run, a
practice exercise, holding back an impulse or agreeing to pick up next time sit
in the mid-band (1.0–1.5), while a decision or asking for help stays high. On
the real 453-turn final exam, B is `0.0` on 94% of turns (v7: 52%), and mean
A / B fell from 0.67 / 0.92 to 0.45 / 0.08. Both carry
negative weights in the stress formula, so **the same conversation computes
higher stress under v9**. The toolkit's stress weights and bucket cut-offs are
unchanged and were set on pre-v9 scores: re-tune them on your own data before
letting buckets gate anything, and don't compare or blend scores across the
v7 → v9 boundary.

Know what you are upgrading to: v9 **failed 2 of its 5 pre-registered acceptance
gates**, one of them a safety gate (see the previous answer), and is the default
by an explicit, recorded override by Hamo's founder — the
[model card](https://huggingface.co/HamoAI/hamo-score-0.6b) shows both failures
in full. Its large A and B gains were measured on synthetic exams that are
in-distribution for v9's training patches; there is no real-conversation
measurement under the new A and B rubrics yet.

v7 is still available: the GGUF stays at `gguf/hamo-score-0.6b-v7.q8.gguf` (the
header of [`server/docker-compose.yml`](../server/docker-compose.yml) shows how
to switch the reference server back), and the v7 safetensors at revision
`ab9dc70c5c25be0eb47cd9a7bf7c70c094b4fb93`. Self-check a v7 deployment with
`python eval/run_exam.py --labels pre_v9`.

**Why does my exam score say about 89% when the model card says 77.4%?**
Different exams, different labels. The model card's 77.4% (v9 bf16, all five
dimensions averaged; decision-level 96.0%) is graded on the real 453-turn
held-out final, which never leaves the building — and whose labels still use the
**old** A and B rubric, so on that exam v9's A and B columns measure how far the
rubric moved, not accuracy (W / E / H, unchanged in meaning, are
88.1 / 86.1 / 93.6). The shipped synthetic exam is a different paper, with A and
B re-labelled for v9's rubrics: v9 bf16 reference 88.9%; the shipped q8 GGUF at
neutral sampling 89.3%. Its job is to certify *your wiring* (prompt, template,
sampling, parser), not the model — what matters is landing inside the band in
[eval/README.md](../eval/README.md) (86–92% dimension-level, every dimension
≥ 75%, JSON ≥ 99%, gate 10/10). Don't read 89% as model quality: its labels come
from the same teacher prompts as v9's training labels, so the exam is
in-distribution by construction, and B agrees so often partly because most
crisp-B labels are 0 and v9 mostly outputs 0. If you see about 80% instead,
check which model and which labels you are running: v9 graded against the
pre-v9 labels (as an older toolkit does) scores 79.4% bf16 / 79.7% q8, and v7
graded against the new v9 labels scores 80.1% bf16 / 80.2% q8 — so a server
still serving the v7 GGUF looks the same. If you deploy v7 on purpose, pass
`--labels pre_v9` and expect about 83.5% (bf16) / 83.8% (q8).

**Can I fine-tune it on my own data?**
Yes — [docs/finetune.md](finetune.md) is the full generation-by-generation
playbook, data red lines first, including the generations we rejected (v5, v6,
v8, v8.1) and v9's release by override. Your fine-tuned weights remain under
HAMO-RAIL-S (the guide's license section covers what you owe).

**What exactly do the two licenses cover?**
This repo's code: Apache-2.0, no restrictions. The model weights: HAMO-RAIL-S
1.0 — free commercial use with four restrictions (no standalone clinical
determinations; no consequential decisions about identifiable individuals; keep
independent upstream crisis handling + AI disclosure in consumer mental-wellness
deployments; no re-identification). The toolkit's default pipeline puts the
independent upstream mechanism in place structurally, but its keyword recall is
partial (see "Is it a crisis detector?"), so it does not by itself make a
deployment safe; showing the AI disclosure (ready-made texts included) is still
on you.

**I think a score is wrong.**
Maybe! The reference scorer this model was distilled to replace disagreed with
itself 2–6% of the time in small repeat-run spot checks (about a dozen messages
each) — treat that as a rough noise floor, not a precise one. If it's A or B,
first check it against the v9 rubric on the model card — a lot changed. If a *pattern* of disagreement persists, file the
**score disagreement** issue template — reports feed the human gold-label
program that steers future versions.

---

# 中文

**为什么模板必须带空 `<think>` 块？** 学生是关闭思考训练的 Qwen3，模板预填
空 think 让它直接吐 JSON。没有它模型会自己「想」——在推荐的 80 token 输出帽下，
JSON 常常还没吐出来就被截断：等着你的是解析失败，不只是延迟。
这是第一大接线错误，照抄 `server/Modelfile`。

**为什么温度必须 0，还必须中性化 `repeat_penalty`？** 评分是测量，采样噪声就是测量误差。官方数字全部测于温度 0 **且无重复惩罚**。

后半句坑得很深且无声：**ollama 默认 `repeat_penalty 1.1`**，而本模型的输出 `{"A": 0.0, "W": 0.0, ...}` 天然高度重复——惩罚重复 token 等于**把分数从 0 往上推**，也就是凭空造出信号。我们在自己的 300 题边界判别考卷上实测过，同一份权重、只改采样：随包 v9 q8 GGUF（按 crisp B 口径判卷）从 1.0 换成 1.1，造分率 **1.9% → 2.8%**，边界符号翻转（真值 0.0 被打 ≥2.0）保持 0 条，漏判率从 6.1% 降到 3.1%——那是同一股往上推的力，不是改进。旧版本（按 v7 时代答案判卷）上影响更大：v7 q8 GGUF 造分率 **2.9% → 8.7%**、翻转 **0 条 → 1 条**；v6.1 为 13.5% → 25.0%、6 条 → 10 条。v9 上变小了，但方向一样。权重没问题，运行时有问题。请始终带上 `repeat_penalty 1.0`、`top_k 0`、`top_p 1.0`（[`server/Modelfile`](../server/Modelfile) 已内置）。

**启动后第一条请求慢/超时？** 冷启动。重启后预热一发，`keep_alive=-1`（调用
设硬超时，工具包与参考服务器默认 8 秒）。之后
仍慢就是慢 CPU 的 prefill 成本——检查是否超出截断护栏。

**输出不是合法 JSON？** `parse_scores()` 返回 `None`，按「跳过本句」处理
（平滑使其无损）——不崩溃、不瞎猜。超过 ~1% 就是接线坏了：查空 think 模板、
温度 0、`num_predict ≥ 80`，再跑自检考卷。

**支持哪些语言？** 中文为主（按 v9 训练集每行的最新消息统计：中文约 76% / 英文 13% /
中英混杂 11%）。英文可用但测试较少；其他语言未测——那是微调指南的活。

**「嗯」这类超短消息评不评？** 评，带上下文评。全零=无操作，无害。真实对话里
短消息很常见——跳过它们等于在人最沉默的地方开盲区。

**多喂点上下文会不会更准？** 不会更准多少。模型训练时见过最多 5 轮上下文（部分超过 200 字）；
`build_prompt` 只保留最后 3 轮 × 200 字、消息截到 500 字，这是延迟护栏——慢 CPU 上长上下文的
prefill 会吃爆延迟预算——而且经验证截短后仍保持 98.1% 的评分自一致（±0.5）。超过 5 轮才出分布；
护栏与 5 轮之间只是更慢。

**需要 GPU 吗？** 不需要。2 vCPU ARM 服务器 q8 1.5–2.9 秒，M1 Pro 笔记本 ~0.8 秒
（MLX bf16）。
门控行为的部署用随包 Q8_0——**v9 我们只量过这一档**。我们的量化对比只在 v7 权重上做过：
当时自量化的 Q6_K 在内部 453 轮终评集上与 Q8_0 无差别，Q4_K_M 则会把危机相邻样本的 W
往下压，只适合研究或由人来读分数。我们不发布 v9 的 Q6_K 或 Q4_K_M；自行量化 v9 后，先用
`eval/compare_quants.py` 与随包 Q8_0 对比，再让它门控任何东西；未量过的一律默认更差。
社区 GGUF 量化自 v4 权重——比 v9 早三个版本，早于 v9 的 A/B 口径与 W 修复——从未经过验证
（唯一一次跑它们是已作废、混了版本差的那张对比），不在任何建议范围内。详见 [eval/README.md](../eval/README.md)。

**它是危机检测器吗？** 不是，也永远不许当危机检测器部署。危机归上游确定性
闸门（许可证 §3c）；模型的危机语召回只是纵深防御。v9 让这一条不只是形式：自杀意念与
求助同时出现时，它会把 W 打低（随包 q8 在 45 道此类合成题中只有 29 道达到规定的
W ≥2.5）——这正是 v9 没过的那道安全闸门。这个缺口承袭自 v7、并非 v9 新引入：v7 在这类题上
并不更好（两者都有 5 道题 W 低于 1.0），所以退回 v7 也补不上它。工具包自带的闸门单靠自己也补不上：
`CrisisGate` 只是一份简短的关键词表，在这 45 道题中只命中 26 道，受检 bf16 权重把 W 打到 2.5 以下的
19 道中只命中 7 道——与求助一起说出的自杀意念常常漏过词表。请按你的人群扩充词表，在闸门旁边（而不是
替代它）加第二层筛查，并在依赖它之前先在你自己的数据上量出召回率。

**v9 在大多数消息上把 B 打成 0，升级后压力值还变高了——是坏了吗？** 没坏，是口径变了，
你的阈值也得跟着变。v9 按修订后的口径打 A 与 B。**B** 现在只算边界标记——说出的需要、
界限、条件或立场；平静有条理的自述和积极行动不再给 B，向 AI 求助归 A 不归 B。**A** 现在
指主动推动处境或疗愈关系向前；当下平复情绪属于应对（0–0.5），单次散步或跑步、做练习、
克制冲动、约好下次再聊落在中档（1.0–1.5），做决定与主动求助仍是高分。
453 题真实终评上，94% 的 B 为 `0.0`（v7 为 52%），平均 A / B 从 0.67 / 0.92 降到
0.45 / 0.08。两者在压力公式里都是负权重，所以**同一段对话，v9 算出的压力更高**。工具包的
压力权重与分桶阈值没有改，是按 v9 之前的分数定的：让分桶把关任何事之前，先用你自己的数据
重调；也不要跨 v7 → v9 比较或混合分数。

升级前也要知道你换上的是什么：v9 **没过它预注册的五道验收闸门中的两道**，其中一道是安全
闸门（见上一条），它成为默认权重是 Hamo 创始人明确作出并留档的破例决定——
[模型卡](https://huggingface.co/HamoAI/hamo-score-0.6b)完整列出了两项失败。它在 A、B 上的
大幅进步测于与 v9 训练补丁同分布的合成考卷；新 A、B 口径下还没有任何真实对话上的测量。

v7 仍可用：GGUF 保留在 `gguf/hamo-score-0.6b-v7.q8.gguf`
（[`server/docker-compose.yml`](../server/docker-compose.yml) 文件头写了如何把参考服务器换回
v7），v7 safetensors 在固定版本 `ab9dc70c5c25be0eb47cd9a7bf7c70c094b4fb93`。v7 部署的自检
请用 `python eval/run_exam.py --labels pre_v9`。

**为什么我考出约 89% 而模型卡写 77.4%？** 两张不同的卷子、两套不同的标签。模型卡的
77.4%（v9 bf16，五维平均；决策级 96.0%）判于 453 条真实终评卷（永不出门），而这张卷的标签
仍是**旧的** A、B 口径——在那张卷上，v9 的 A、B 两列衡量的是口径移动了多远，不是准确率
（含义不变的 W / E / H 为 88.1 / 86.1 / 93.6）。随包的是另一张合成卷，A、B 已按 v9 口径
重标：v9 bf16 参考值 88.9%，随包 q8 GGUF 在中性采样下 89.3%。它的任务是认证**你的接线**
（提示词、模板、采样、解析），不是给模型打分——落在 [eval/README.md](../eval/README.md)
的合格带内（维度级 86–92%、每一维 ≥75%、JSON ≥99%、闸门 10/10）即正确。别把 89% 读成
模型水平：它的标签与 v9 训练标签出自同一套教师提示词，按构造就是同分布；B 一致率高，部分
只是因为 crisp B 下大多数标签是 0、v9 也大多输出 0。如果你考出约 80%，先核对跑的是哪个模型、
用的是哪套标签：用 v9 之前的旧标签给 v9 判卷（旧版工具包就是这样判的）为 bf16 79.4% / q8 79.7%；
而 v7 在 v9 新标签上为 bf16 80.1% / q8 80.2%——服务器若仍在跑 v7 GGUF，看起来也一样。如果你有意部署 v7，
请加 `--labels pre_v9`，参考值约 83.5%（bf16）/ 83.8%（q8）。

**能用自己的数据微调吗？** 能——[微调指南](finetune.md)是完整的历代打法，数据红线在最前，
拒收的 v5、v6、v8、v8.1 与 v9 的破例发布都写在里面。微调出的权重仍受 HAMO-RAIL-S 约束
（见指南中的许可证一节）。

**两份许可证分别管什么？** 本仓库的代码：Apache-2.0，无限制。模型权重：HAMO-RAIL-S 1.0——
可免费商用，但有四条限制（不得独立做临床判定；不得对可识别的个人做重大决定；面向消费者的心理
健康部署须保留独立的上游危机处理与 AI 身份披露；不得重识别）。工具包的默认管线在结构上就把这道
独立的上游机制放好了，但它的关键词召回有限（见「它是危机检测器吗？」），单靠它并不能让部署变得
安全；展示 AI 身份披露（附现成文案）仍是你的责任。

**评分不服怎么办？** 可能你是对的！这个模型蒸馏来替代的参照评分器，在小规模重打抽查
（每次约十来条消息）中自己也有 2–6% 不一致——把它当作粗略的噪声底，而非精确值。如果是 A 或 B，先对照模型卡里的 v9 口径——这两维变化很大。成规律的分歧请用
「评分分歧」issue 模板提交——报告直接喂给引导后续版本的人类金标计划。
