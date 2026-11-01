# Integration guide — wiring the scorer the way it was designed

**EN** | [中文](#中文精编)

The model reads one message and returns five numbers. What those numbers may
touch, and what must run before the model, is integration. This page gives the
intended wiring, the upgrade guides for v10h (toolkit 0.4.0) and v10 (toolkit
0.3.0) with a correction about v9, the version pins, and the don't list.

## The one intended shape

```
message ──▶ CrisisGate ──▶ build_prompt ──▶ model ──▶ parse_scores ──▶ update_stress ──▶ energy_state
```

`score_message()` implements the left half in the safe order; `update_stress()`
and `energy_state()` are the right half. The reference server in
[`server/`](../server) wires all of it behind one `POST /score`.

1. **Gate.** Deterministic keyword lists (zh + en), extensible via
   `CrisisGate(extra_keywords=[...])`. When it triggers, the message does not
   reach the model: route to a human and show the AI disclosure
   (`DISCLOSURE_ZH` / `DISCLOSURE_EN` in
   [`safety.py`](../src/hamo_score/safety.py)). License §3(c) requires an
   independent crisis mechanism upstream of the model, and an AI disclosure, in
   consumer-facing mental-wellness deployments; this architecture expects the
   gate in every deployment.
2. **Score.** One prompt format (`build_prompt`: the last 3 turns × 200
   characters of context, the message capped at 500), temperature 0 with
   neutral sampling (don't #5), and the chat template in
   [`server/Modelfile`](../server/Modelfile) (Qwen3 with an empty `<think>`
   block). By default ollama 0.32.5, 0.40.12 and 0.40.13 store this template but
   serve the GGUF's own chat template instead (see the [FAQ](faq.md)).
3. **Smooth.** `new = 0.8·history + 0.2·clamp(history + delta)`, with
   `delta = 0.9·W + 1.2·E + 1.6·H − 1.0·A − 1.1·B`; an optional `quadrant=`
   adjusts the weights. Per-message noise is damped ~5×, and an all-zero score
   is a **no-op by design**, which makes scoring ultra-short messages ("嗯",
   "ok") safe.
4. **Bucket.** `energy_state()`: stress `< 4` positive, `< 7` negative, `≥ 7`
   neurotic. The cut-offs and the step-3 weights were set on legacy-rubric
   scores (v7 and earlier): read the upgrade sections below before the buckets
   gate anything, and do not feed v9 scores into steps 3 and 4.

## Upgrading to v10h

v10h has been the default weights on Hugging Face since 2026-10-31 (UTC)
and is what the reference server serves from toolkit 0.4.0; v10 was the default
from 2026-10-06 to 2026-10-31 (UTC). The library's behaviour does not
change in 0.4.0: the model does. Scores are **not comparable across v7, v9, v10
and v10h**:

| version | A (Agency) | B (Boundary) | W, E, H |
|---|---|---|---|
| v7 and earlier | old rubric | legacy rubric | production rubric |
| v9 | rubric v8 | "crisp" rubric | production rubric, with a W safety repair |
| v10 | rubric v8 | legacy rubric | as v9 |
| v10h | the counselor review of v10's scores | the same review | the same review |

The v10h row describes its synthetic training rows; the staff rows in its
training set keep their teacher-era labels. Coming from v9 or v7, read
"Upgrading to v10" below as well: the correction about v9 is there.

**Basis of the numbers on this page**, unless a line says otherwise: each
version's shipped q8 GGUF, llama.cpp with Metal on an M1 Pro, temperature 0,
`repeat_penalty 1.0`, `top_k 0`, `top_p 1.0`, the same exam files. Numbers
from the real final exam and from the B and W safety exams were measured on
each item's full stored context, not through `build_prompt`'s trimming (the
model's [technical record](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md),
linked from the model card, says the same); the self-check exam and the 138-item serving check
did use the trimming. So those exam numbers describe the model on full
context, not the toolkit pipeline end to end. "The real final exam" is 453
turns of pseudonymised conversations from three consenting internal staff
members, labelled under the production rubric ("reference labels", not
counselor scores). External user conversations never enter training.

### What v10h changes

v10h is v10's prompts and training recipe with the answers on the synthetic
training rows replaced by the scores of a review by human counselors engaged by
Hamo. Their names, number and credentials are not published; the limits of the
review are in the technical record
([How it was trained](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#how-it-was-trained)).
Where the review disagrees with earlier rubric bands or with the overlay rules,
the review stands: the founder decided this after seeing the results.

- **A (Agency)** follows the review rather than the earlier rubric bands, and
  reads lower. On the A exam, scores inside those bands fall from 590 (v10) to
  519 of 632. Runs (50/50 → 26/50) and walks (52/52 → 40/52): the review moved
  part of these rows from 1.0 to 1.5, and v10h learned about that proportion.
  Collaborative help-seeking (27/40 → 1/40, mostly 1.5): the review has no such
  class, so the link to it is an inference. Healthy habits (54/59 → 45/59) are
  different: the 30 closest rows of the review keep A ≥ 2, so this looks like
  the general drop in A carried too far, not something the labels ask for. Pair
  direction holds at 150 of 154 (v10: 149). On the real final exam mean A is
  0.43 (v10: 0.53; reference labels: 0.84).
- **W, E and B** follow the review too, and the review is not one uniform
  scale: it was done in batches and its W, E and B scoring drifts across the
  sheet, so v10h learned a blend. On the real final exam mean W is 0.33
  (v10: 0.39).
- **H** reads higher on real messages: on the real final exam mean H is 0.13
  (v10: 0.08; reference labels: 0.14), and H carries the largest weight in the
  stress formula.
- **B** still credits a report of positive action, and it appears on more
  messages. On the real final exam B is 0.0 on 201 of 453 turns (v10: 223), and
  all-zero outputs are 25.6% (v10: 32.2%; reference labels: 15.5%). On the old
  B exam, legacy key, fabrication (a no-boundary item scored B ≥ 1.0) goes
  3 → 18 of 104 and misses (a limit-setting item scored B ≤ 0.5) 21 → 8 of 180.
- **The overlay rules.** The explicit-ideation rule, the farewell rule and the
  W safety repair ("What v10 scores", below) are not applied on top of the
  review's scores on the synthetic rows. The counts are in the technical
  record; they are facts about labels, not about crisis handling (don't #3).
- **The sentence v10 scored B 2.5** ("What v10 scores", below) gets B 0 from
  v10h, with and without the final full stop, on the shipped q8, MLX bf16 and
  transformers bf16 (no context). That is one sentence: flips remain on other
  items (4 of the 438 self-erasure items, 4 of the 596 gold-0 items, 13 of the
  166 real final-exam turns with reference B 0), so a high B from v10h is still
  not evidence that a boundary was kept ([FAQ](faq.md)).
- **Computed stress.** On the real final exam the mean raw per-turn stress
  change is −0.63 from v10h's scores (v10: −0.72; reference labels: −0.68), and
  the session-replay drift is −0.14, as for v10 (gate G7 allows −0.83 to −0.43,
  and a drift within ±0.15). In session replay, 64–68 of 295 turns sit at
  computed stress ≥ 6.0 for the two v10h seeds, against 56–58 for the two v10
  seeds and 43 for the reference labels.

### Upgrade steps from v10

1. **Do not mix v10 and v10h in one history or trajectory.** A and W read lower
   on average and all-zero outputs are fewer, so a trend line across the switch
   shows a step that is the model changing, not the person. Store the model
   version with every score; at the switch, start fresh histories or re-score
   the stored messages; keep analytics and reports per version.
2. **Re-check any threshold set on v10's scores, and check the buckets on your
   own data before they gate anything.** The 4.0 / 7.0 cut-offs and the stress
   weights are unchanged in toolkit 0.4.0, and v10h's A follows the review, on
   which they were not set. What stands behind them for v10h is gate G7 on one
   exam of internal staff conversations, scored on full, untrimmed context,
   with the drift 0.013 from its limit. Replay real, consented sessions from
   your own population through `update_stress` with v10h's scores; until then,
   let the buckets inform a person, not gate behaviour.
3. **Check A before anything relies on it.** Real conversations have no
   counselor scores and the real exams' reference labels use the older A
   rubric, so v10h's A has no real-conversation measurement. Compare it with a
   human-scored sample of your own real, consented conversations.
4. **Pin the model version** (next subsection).
5. **Treat the upgrade as a scorer change**, as in step 7 under "Upgrading to
   v10": shadow first, pre-registered switch criteria, trajectories over
   replayed sessions.
6. **Self-check the deployment** with `python eval/run_exam.py` (band under
   "Operational wiring").

### Pins and rollback

`main` on Hugging Face is now v10h, so
`from_pretrained("HamoAI/hamo-score-0.6b")` and the toolkit's
`TransformersClient()`, which loads `main`, get v10h. Pin whichever version you
serve: safetensors by full commit hash with `revision=` (`TransformersClient`
takes no `revision` argument; give it the local path of a snapshot downloaded
at a fixed revision as `model_id`), GGUF files by digest:

```
v10h q8 GGUF      gguf/hamo-score-0.6b-v10h.q8.gguf  sha256 3b5a5999a79f5cca917c24583779f67375d477aae6834e2443137f6ee738fb88  (639,446,976 bytes)
v10h safetensors  revision d29c03288b6f553c748c9b9daefcb34b0f405497  (model.safetensors sha256 c664997dcadc56b9820b9ae7f8c2687d66c34f79cb9dfcf51a5b14d04ef1ecc9, 1,192,134,901 bytes)
v10 q8 GGUF       gguf/hamo-score-0.6b-v10.q8.gguf   sha256 6d6f5cd684803a126bbd9615ded100e8a574a2ec6486d579a6a357d6da295490  (639,446,976 bytes)
v10 safetensors   revision f3869312f0222992c3eb2e938e78090de38eb80a  (model.safetensors sha256 a7d3a90b66a5a2ef5aba8908b947dad221b2749bfc4bcd7d4f590925f002bc44)
v9 q8 GGUF        gguf/hamo-score-0.6b-v9.q8.gguf    sha256 fa189895962c33390bfbc8e86c6fc77e2b5113cbedf6f5105c38a5bc4eabd05f
v9 safetensors    revision 7832dafaac1fa6e0af42c3802e498fb08ddbeb58
v7 q8 GGUF        gguf/hamo-score-0.6b-v7.q8.gguf    sha256 fb1018c8a38ad0da573544b827e42f1685e051c688f8de587cbb81ae1275e3ea
v7 safetensors    revision ab9dc70c5c25be0eb47cd9a7bf7c70c094b4fb93
v6.1 q8 GGUF      gguf/hamo-score-0.6b-v61.q8.gguf
```

The five GGUF files listed are all in `gguf/` on `main`.

- **Serving.** The reference server registers the unversioned ollama name
  `hamo-score-0.6b`, so `docker compose up --build` from `main` replaces
  whatever that name served before with v10h **under the same name**. Use
  `main` or `v0.4.1`: the compose file at the `v0.4.0` tag fails at the
  download step. After you update the repository, run
  `docker compose up -d --build` in `server/`: compose builds the api image
  only when it is missing, so without `--build` it keeps the image it already
  built, with the old server code. That also holds after `docker compose down`
  and from a new clone on the same machine.
  `docker compose exec ollama ollama show hamo-score-0.6b --modelfile` prints
  the blob digest in its `FROM` line; compare it with the digests above. To
  keep serving v10, v9 or v7, first edit the file name and both digests as the
  comment at the top of
  [`server/docker-compose.yml`](../server/docker-compose.yml) says. Outside
  Docker, a model keeps the GGUF it was created from: to switch, point `FROM`
  in [`server/Modelfile`](../server/Modelfile) at the file you want and run
  `ollama create` again. With Docker, after a version switch the previous GGUF
  stays in the `model-cache` volume (about 640 MB each), and ollama prunes its
  own copy. This does no harm. To remove one:
  `docker compose run --rm --no-deps --entrypoint rm setup -f /models/<file>`.
- **Staying on v10**, if thresholds or histories built on its scores cannot be
  re-baselined yet, or if you want A on the earlier rubric bands (A exam in
  band: 590 of 632, v10h 519): self-check with
  `python eval/run_exam.py --labels v10`, the same labels as the default,
  against v10's band ("Operational wiring"). You give up v10h's closer fit to
  the counselor review, and B returns to 2.5 on the sentence under "What v10
  scores". v10's own acceptance status is at the end of "Upgrading to v10".
- **Staying on v9**: self-check with `python eval/run_exam.py --labels v9`. Do
  not feed its scores into `update_stress()` or `energy_state()`, and do not
  consume the `stress` and `energy_state` fields of `POST /score` while it
  serves v9 (the correction below). v9 failed 2 of its 5 pre-registered gates,
  one of them v9's gate 5 (W safety).
- **Staying on v7 or older**: self-check with
  `python eval/run_exam.py --labels pre_v9`. v7 predates the explicit-ideation
  rule: on v7 (shipped q8) the mean raw stress change over the 189
  ideation-plus-help items is −0.29 (v10: +2.37; v10h: +2.51); versions older
  than v7 were not measured on these items. Whatever the version, the gate in
  front of the model is not optional (don't #3).

### v10h's acceptance status

v10h's registration, frozen before training, asked one main question: is it
closer to the counselor review than v10? On 978 held-out synthetic items the
answer is yes: mean absolute error against the review is 0.142, against 0.255
for v10. It also carried over v10's 18 checks and met 17. The one it did not
meet, G5a, and G5b were stand-ins for crisis handling; the registration made
both report-only, because the founder ruled crisis handling outside this model.
The other 16 all passed. The comparison with the review is on synthetic
messages only: real conversations have no counselor scores, and on the real
final exam v10h ties v10 against the reference scorer (same state bucket on 440
and 435 of 453 turns). Full statement and the table of reported checks:
technical record,
[Evaluation](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation).

## Upgrading to v10

*This section describes the previous release (toolkit 0.3.x). It still applies
to v10h unless the section above says otherwise.*

v10 was the default weights on Hugging Face from 2026-10-06 to 2026-10-31
(UTC) and is what the reference server serves in toolkits 0.3.0 and 0.3.1; v9
was the default from 2026-09-30 to 2026-10-06. The table of versions, the pins
and the rollback steps are in the section above.

v10 adds the **explicit-ideation rule**: when a message contains explicit
suicidal ideation, A is capped at 1.0 and B is 0 (both new in v10), and W is at
least 2.5 (a floor that dates from v9's W safety repair). "v7 and earlier"
includes v6.1 and the community GGUFs
(`mradermacher/hamo-score-0.6b-GGUF`), which are built from the v4 weights,
five releases behind v10h (v6.1, v7, v9, v10, v10h); no number on this page was
measured on them.

### What v10 scores

- **A (Agency)** follows rubric v8, as in v9: *actively moving the situation or
  the helping relationship forward, not regulating one's own emotions*. High: a
  decision, asking for help, a healthy habit. Mid-band (1.0–1.5): a one-off
  walk or run, a practice exercise, holding back an impulse, agreeing to pick
  up next time. 0–0.5: calming yourself down in the moment, handing a decision
  to someone else. Farewell and putting-affairs-in-order signals are A = 0.
- **B (Boundary)** is back on the legacy rubric of v7 and earlier: clear
  self-expression, read broadly. High: a stated need, limit, position or value,
  and also calm, structured self-description and positive-action messages. Low:
  chaotic venting, bare fragments, brief unelaborated mood statements. v9's
  narrower "crisp" B (only boundary markers count, so most messages score 0) is
  not in v10.
- **The explicit-ideation rule**: its A cap and B 0 are new, so that
  help-seeking next to ideation does not reduce computed stress. It is in
  v10's training labels; the toolkit does not apply it at inference. On the 189
  synthetic ideation-plus-help items of the old and new W safety exams, the
  mean raw stress change from v10's scores is +2.37 (gate G8 requires ≥ 0;
  v10h: +2.51), from v9's −0.24, from v7's −0.29. These items come from the same kind of
  generators as v10's training patches: they show no regression inside the
  known range, not generalisation. These numbers describe the direction of
  the stress formula on those items, not crisis detection (don't #3).
- **A known B sign flip.** With no context, v10 scores 「行，我全听你的，你说哪天去就哪天去。」
  ("Fine, I'll do whatever you say — we go whichever day you say.") B 2.5 where
  v7, v9 and v10h score 0. Earlier model cards used this sentence as the example for
  "the instrument must not read self-erasure as a boundary" (the v7 card
  without the final full stop, a form v10 scores B 2.0; the v9 card only its
  first clause), so a high B from v10 is not evidence that a boundary was kept
  ([FAQ](faq.md)).

### Correction: re-tuning thresholds does not repair v9

Toolkit 0.2.0 and the v9 model card told you to "re-tune thresholds" before
letting the buckets gate anything on v9. That advice was not enough.

- v9 scores B under the crisp rubric, so B is 0 on most ordinary messages. The
  stress formula gives B a negative weight; with B at 0 the relief term
  disappears. On the real final exam the mean raw per-turn stress change from
  v9's scores is positive where the reference labels' is negative, and replayed
  sessions drift upward:

  | scorer | mean raw per-turn stress change | session-replay drift vs reference labels | turns with B = 0.0 |
  |---|---|---|---|
  | reference labels | −0.68 | 0 (by definition) | — |
  | v7 | −0.76 | −0.10 | 234/453 (51.7%) |
  | v9 | +0.37 | +0.51 | 429/453 (94.7%) |
  | v10 | −0.72 | −0.14 | 223/453 (49.2%) |
  | v10h | −0.63 | −0.14 | 201/453 (44.4%) |

  "Raw per-turn change" is `delta` in `update_stress` (quadrant-modified),
  before the 0.8/0.2 blend. "Drift" is the mean, over the 50 sessions of three
  or more turns (295 of the 453 turns), of the difference in end-of-session
  stress, in points on the 0–10 scale, when each session is replayed with the
  scorer's read-outs instead of the reference labels.
- Re-tuning the cut-offs or the B weight cannot repair this: a weight
  multiplies a zero. Only an added constant could, and the constant was not
  stable: the value that cancelled the drift on the real final exam differed
  from the value fitted on a second set of staff turns (the trained-on
  calibration set). We did not find a re-tuning that works.
- So v9 is superseded as the default. v10 returns B to the legacy rubric, and a
  new gate (G7) checks the stress trajectory directly. If you moved to v9 and
  feed its scores into `update_stress()`, or into any formula with a negative B
  weight, move to v10h or v10, or go back to v7.
- The crisp rubric itself is not disowned: it is a cleaner definition of
  boundary-setting and its teacher is more stable. What was wrong was shipping
  it into a formula calibrated for the legacy rubric without re-centring the
  formula. v9 stays downloadable for anyone who wants the crisp-B instrument on
  its own terms (pins above).

### Upgrade steps to v10

1. **Coming from v9: do not carry v9 state forward.** Stress accumulated from
   v9 scores contains the upward drift. Also drop what you built on v9's B
   (mean B on the real final exam: 0.08 under v9, 0.98 under v10): cut-offs or
   weights re-fitted on v9 scores, and any rule, report or dashboard that
   assumes "B 0.0 is the normal case" (don't #8).
2. **Coming from v7 or earlier: A changed meaning; B is the same rubric,
   except that explicit ideation now forces B to 0.** On the real final exam
   mean A is 0.68 under v7 and 0.53 under v10, and mean B 0.92 and 0.98; the
   net effect on stress is small on this exam (v7 and v10 rows of the table).
   That does not make the two versions interchangeable message by message
   (steps 3 and 4).
3. **Do not mix versions in one history or trajectory.** v7, v9, v10 and v10h
   are four different instruments; a trend line across a switch shows a step that
   is the model changing, not the person. Store the model version with every
   score; at a switch, start fresh histories or re-score the stored messages;
   keep analytics and reports per version.
4. **Check the buckets on your own data before they gate anything.** The
   4.0 / 7.0 cut-offs and the stress weights are unchanged in toolkits 0.3.0
   and 0.4.0.
   They were set on legacy-rubric scores, and v10's A follows a rubric they
   were not set on; what stands behind them for v10 is gate G7 (the v10 row of
   the table; allowed: mean change −0.83 to −0.43, drift within ±0.15) on one
   exam of internal staff conversations, scored on full, untrimmed context.
   Replay real, consented sessions from your own population through
   `update_stress` with v10 scores; until then, let the buckets inform a
   person, not gate behaviour. The cut-offs and weights are constants, also
   behind the `energy_state` field of `POST /score`: to use your own, bucket
   the returned `stress` or compute stress from the returned `scores` yourself.
5. **Check A before anything relies on it.** The reference labels follow the
   old A rubric, so v10's A agrees with them less often than v7's by design,
   and there is still no real-conversation measurement under A rubric v8.
   Compare A with a human-scored sample of your own real, consented
   conversations; checking where the buckets land is not that check.
6. **Pin the model version** ("Pins and rollback", above).
7. **Treat the upgrade as a scorer change.** Run v10 in shadow first (both
   score, the incumbent decides, every pair logged), pre-register your switch
   criteria (examples: fine-tuning guide, [§6](finetune.md)), and compare
   trajectories over replayed sessions, not only per-turn agreement, which is
   the check that did not show v9's drift.

### v10's acceptance status

v10 met 17 of the 18 checks of its signed pre-registration. The one it did
not meet, G5a, was a stand-in for crisis handling. After seeing the result,
the founder ruled that crisis handling is not judged by this model or by its
W score: it is done in the deterministic code around the model, which Hamo
calls the spine. Under the registration as signed the verdict was
**rejected**; v10 is released by the founder's decision. That is a waiver of
one pre-registered gate made after the result was known, and the second
release in a row that ships by founder decision after failing a
pre-registered gate (v9 failed 2 of 5). Full statement and the table of
reported checks: technical record,
[Evaluation](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation).

## Operational wiring

- **Warm-up**: send one throwaway request after every model (re)start, and keep
  `keep_alive=-1` (`OllamaClient` sets it per request). Send the warm-up with a
  long timeout, not through an 8-second client: ollama aborts a load when the
  client disconnects, so a load slower than the timeout never finishes. On one
  Apple-silicon Mac (Docker under Colima, arm64 CPU, ollama 0.40.13), this was
  reproduced only under an artificial CPU cap or a shortened timeout; slow
  hardware itself was not tested. On the reference server, after a reboot or an
  `ollama` crash the model comes back unloaded. The health check on `api`
  ("Reference server", below) then loads it if no request does first, and it
  can finish a load slower than `SCORE_TIMEOUT`.
- **Timeout + fallback**: give the call a hard timeout and a defined fallback:
  the previous scorer, or "skip this message" (a skipped score is a no-op). The
  toolkit's client and the reference server's `POST /score` default to 8 s; on
  an ARM CPU server running ollama the v10h q8 GGUF took P50 2.09 s, P95 2.57 s,
  maximum 2.87 s per message (138 synthetic items with the toolkit's prompt trimming; v10 on the
  same check: P50 2.13 s, P95 2.53 s, maximum 2.91 s). That is not a worst case: these prompts are well short of what the
  guards allow, CPU latency grows with prompt length, and latency at the guard
  limit was not measured on v10 or v10h. Log every fallback with a reason and record which scorer
  produced each score; a fallback rate above a few percent means something is
  wrong. The reference server has no fallback of its own. On a timeout (8 s by
  default; set `SCORE_TIMEOUT` under the `api` service's `environment`) or with
  the model down, `POST /score` returns HTTP 500 with the body
  `Internal Server Error`. A reply that does not parse returns HTTP 200 with
  `scores: null`. A gate hit also has `scores: null`, with `crisis.triggered`
  true: read `crisis` first and route those to your crisis pathway. Treat the
  other two cases as skip or fallback. From 0.4.1 an invalid request does not
  reach the model and gets HTTP 422. For example: an unknown field, at the top
  level or inside a history turn; a turn with no `content`; a `role` other than
  `user` or `assistant` (`role` may be left out; it defaults to `user`); a
  `quadrant` other than `expert`, `supporter`, `leader` or `dreamer`
  (case-sensitive); a `current_stress` that is not a JSON number from 0 to 10 (a
  number string, a boolean, NaN and Infinity are rejected); a `message` that is
  missing or not a string; and a body that is not valid JSON. A `null` in
  `history`, `current_stress` or `quadrant` counts as leaving the field out. The
  reply is `{"detail": [{"type": ..., "loc": [...], "msg": ...}]}` and does not
  echo the rejected value. A body the server cannot decode, such as Chinese text
  sent in GBK, gets HTTP 400 instead, and its `detail` is a string, not a list.
  Fix the request: sending it again unchanged gets the same reply. A gate hit is
  answered normally (HTTP 200, `crisis.triggered` true, `scores` null) even if
  another field is invalid: when the body parses and `message` is a string, the
  gate reads it before the 422 is decided.
- **After any infra change** (new quantization, runtime or machine): run
  `python eval/run_exam.py` and compare with the
  [reference band](../eval/README.md). The script calls ollama's
  `/api/generate` itself, not `POST /score`, and the Docker reference server
  publishes only the API port (that page says how to check it). It grades
  against v10's label set by default: there are no counselor labels for this
  exam, and `--labels v10h` (the default) and `--labels v10` are two names for
  the same labels (`eval/compare_quants.py` takes the same `--labels` flag).
  Band for v10h weights: dimension-level 84–90%, each dimension ≥ 75%, A ≥ 81,
  JSON validity ≥ 99%, crisis gate 10/10. On llama.cpp with Metal the A floor
  sits above v7 weights (A 80.5 on these labels); through ollama on one
  Apple-silicon Mac (Docker under Colima, arm64 CPU, ollama 0.40.13), warmed, v7
  reads A 81.0, exactly on the floor. The script prints `A81%` either way, so also
  check the dimension-level number and B
  ([eval/README.md](../eval/README.md)). Band for v10 weights: the same, with
  A ≥ 86%. The labels come from the same teacher prompts as v10's training
  labels: a pass checks wiring, not model quality. It shows that your deployment agrees with the exam's labels about as well as the reference does, and that `num_predict` is not too small, through the toolkit's own prompt, sampling and parser, not yours. It does not show which version you serve (v10 weights also pass v10h's band), and it does not check the chat template or `stop`: on ollama 0.40.13 tags without them read the same on 60 questions. Check those with `ollama show <tag> --template` and `--parameters`.
- **Reference server**: `POST /score` has no authentication. Compose publishes
  the API on `127.0.0.1:8080` only.
  [Docker's documentation](https://docs.docker.com/engine/network/port-publishing/) warns that in Docker Engine releases older than 28.0.0, hosts on the same network segment can still reach a port published this way.
  `127.0.0.1` is not an authentication mechanism: any process on this machine
  can call the API. To serve other machines, put your own access control in
  front. A reverse proxy running on this machine outside Docker can forward to `127.0.0.1:8080`, with the compose file unchanged. Change the `api` service's `ports` line in `server/docker-compose.yml` to `"8080:8080"` only if the control runs outside this machine: that line publishes the API on every interface of this machine, so a proxy here no longer stands in front of it.
  `GET /healthz` scores a short probe and returns HTTP 200 with `ok: true` only
  if the reply parses as a score within `SCORE_TIMEOUT`; otherwise it returns
  HTTP 503 with `ok: false` and `error`. It waits in ollama's queue, so a busy
  model can report 503. Its own timeout is `HEALTHZ_TIMEOUT`, by default 60 s,
  or `SCORE_TIMEOUT` if that is longer. A probe that took longer than
  `SCORE_TIMEOUT` returns 503 even if it finished loading the model; the next
  one passes if the model is fast enough. The health check on `api` calls
  `/healthz` every 60 s, so when idle it adds one model call a minute. Docker
  shows `healthy`, or `unhealthy` after three failures in a row, and does not
  restart a container for that.

## The don't list

1. **Don't act on a single raw score.** Scores are per-message signals for the
   smoother; smoothing is why per-message noise does not reach decisions.
2. **Don't remove the gate, and don't replace it with a model.** The gate is
   auditable because it is deterministic: a word list has exactly the gaps it
   has. A second, independent screen may run *behind* the gate as an addition,
   never instead of it.
3. **Don't use the model as a crisis detector.** It scores five dimensions of
   one message. It does not detect or handle crises, and none of its scores,
   W included, is a crisis signal. Crisis handling is the job of
   deterministic code that runs before the model, on every path that feeds
   it, batch and visit-level re-scoring included; when the gate triggers, the
   message is not scored and must not enter the history that later prompts
   carry. `CrisisGate` is a keyword list, a floor to build on and not a
   complete screen: on the 189 synthetic ideation-plus-help items of the old
   and new W safety exams its lists fire on 107 (56.6%). Extend the lists
   with phrasings from your population and test them, and consider an
   independent second screen behind the gate, measuring its recall on your
   own data before you rely on it.
4. **Don't touch the prompt.** No extra scoring instructions, no reformatting:
   the rubric is baked into the weights, and a prompt whose frame differs from
   `build_prompt`'s (extra instructions, renamed or reordered fields, a
   translated frame) is out-of-distribution, with no warning. How much context
   to send is a separate matter (don't #6). From 0.4.1 `build_prompt()` removes
   `<|im_end|>` and `<|im_start|>` from the message and from each history `role`
   and `content`, so a message cannot close its own turn. `score_message()` and
   `POST /score` inherit this. The rest of the text stays in the prompt. If you
   build prompts without `build_prompt()`, call `strip_turn_markers()` on the
   same fields: otherwise a message containing these two markers can close its
   own turn and open another, and the score then comes from the forged text. A
   single replace is not enough: one pass over `<|im_<|im_end|>end|>` leaves a
   marker behind. The tokenizer's other added tokens, for example
   `<|endoftext|>`, `<think>`, `</think>` and `<tool_call>`, are not removed. On
   one Apple-silicon Mac (Docker under Colima, arm64 CPU, ollama 0.40.13), eight
   of them were inserted one at a time into 40 synthetic messages, in the middle
   or before a following sentence, through ollama's `/api/generate`: all five
   scores stayed within ±0.5 of the same text without the token on 37–40 of 40,
   about the same as inserting the plain text `[x]` (37 and 39 of 40).
5. **Don't raise temperature, and don't leave `repeat_penalty` at its
   default.** `repeat_penalty 1.1`, ollama's default through 0.32.9 (1.0 from
   0.32.10), pushes scores away from
   zero (measured on v10: q8 GGUF, old B exam, legacy key, fabrication
   3/104 → 15/104, B sign flips 2 → 4 of 93). Ship temperature 0, `repeat_penalty 1.0`,
   `top_k 0`, `top_p 1.0`: `OllamaClient` sends them with every request and
   `TransformersClient` decodes greedily with `repetition_penalty=1.0`; your
   own clients must do the same ([eval/README.md](../eval/README.md)).
6. **Don't feed more context than the guards allow.** `build_prompt` keeps the
   last 3 turns × 200 characters and caps the message at 500: a CPU latency
   budget, and the configuration the self-check exam runs with. It is not "what
   the model saw in training", as earlier versions of this page said: 36.6% of
   v10's training rows carry more than 3 context turns.
7. **Don't quantize below q8 without re-taking the exam.** On v10 and v10h only
   the shipped Q8_0 has been measured; the published Q8_0 / Q6_K / Q4_K_M
   comparison is on v7 weights. Run `eval/compare_quants.py` on a lower quant
   before it gates anything, and read its directional table, not just the
   agreement number ([eval/README.md](../eval/README.md)).
8. **Don't treat B (Boundary) as a relationship diagnosis.** It scores the
   wording of one message. Under the legacy rubric a B above 0 is not evidence
   that the person set a boundary (calm self-description and positive action
   score too), and a B of `0.0` is not a warning sign: v10h gives it on 201 of
   453 turns of the real final exam (44.4%; v10: 223, 49.2%). Toolkit 0.2.0
   called it "the normal case (94% of real final-exam turns)" here: that was
   v9's crisp rubric (re-measured for v10's release on the shipped q8: 429 of
   453, 94.7%), not v10 or v10h. B can also be wrong in the direction that
   matters (the known B sign flip).
9. **Don't tune bucket thresholds against synthetic data, and don't carry
   thresholds or histories across versions** (the upgrade steps above). For v9,
   re-tuning does not repair the drift (the correction above).
10. **Don't skip the AI disclosure** in consumer-facing deployments: it is a
    license requirement, and the toolkit ships ready-made texts.

---

# 中文精编

## 唯一的设计形状

`消息 → 危机闸门 → build_prompt → 模型 → parse_scores → update_stress → energy_state`。左半段由 `score_message()` 按安全顺序实现；右半段是平滑 `新值 = 0.8·历史 + 0.2·clamp(历史 + delta)`（`delta = 0.9·W + 1.2·E + 1.6·H − 1.0·A − 1.1·B`）加 `<4 / <7 / ≥7` 三桶；`server/` 的参考服务器把整条管线接成一个 `POST /score`。

- **闸门**：确定性关键词表（中、英），可用 `CrisisGate(extra_keywords=[...])` 扩充。命中即短路：消息不进模型，转人工并展示 AI 披露文案。许可证 §3(c) 要求面向消费者的心理健康类部署在模型上游有独立的危机处理机制，并披露 AI 身份；本架构要求每个部署都带这道闸门。
- **评分**：只用 `build_prompt` 一种提示词格式（最近 3 轮上下文、每轮 200 字，消息 500 字封顶），温度 0 加中性采样（禁令 ⑤）。聊天模板用 [`server/Modelfile`](../server/Modelfile) 里的（Qwen3，带空 `<think>` 块）。ollama 0.32.5、0.40.12、0.40.13 默认会存下这段模板，但实际用 GGUF 自带的聊天模板（见 [FAQ](faq.md)）。
- **平滑**：全零分数在构造上是无操作，超短消息（「嗯」）可以放心评。
- **分桶**：压力权重与 4 / 7 两档阈值按 legacy 口径（v7 及更早）的分数定。让分桶把关任何事之前先读下面的升级章节；v9 的分数不要喂给平滑与分桶。

## 升级到 v10h

v10h 自 2026-10-31（UTC）起是 Hugging Face 上的默认权重，工具包 0.4.0 的参考服务器跑的也是它；v10 在 2026-10-06 至 2026-10-31（UTC）期间是默认权重。0.4.0 里库的行为没有变化，变的是模型。**v7、v9、v10、v10h 的分数互不可比**：

| 版本 | A（行动力） | B（边界感） | W、E、H |
|---|---|---|---|
| v7 及更早 | 旧口径 | legacy 口径 | 生产口径 |
| v9 | v8 口径 | crisp 口径 | 生产口径，加 W 安全修复 |
| v10 | v8 口径 | legacy 口径 | 同 v9 |
| v10h | 咨询师对 v10 分数的复核 | 同左 | 同左 |

v10h 这一行说的是它的合成训练行；训练集里的内部员工行沿用教师时期的标签。从 v9 或 v7 来的，请把下面的「升级到 v10」也读一遍，关于 v9 的更正在那里。

**本页数字的口径**（另有说明的除外）：各版本随包的 q8 GGUF，llama.cpp 加 Metal（M1 Pro），温度 0，`repeat_penalty 1.0`、`top_k 0`、`top_p 1.0`，同一批考卷文件。真实终评与 B 卷、W 安全卷上的数字，各题按存档的完整上下文打分，没有经过 `build_prompt` 的截短（模型的[技术档案](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md)同此说明，模型卡里有链接）；自检卷和 138 题的服务端核对则用了截短。所以这些数字说的是完整上下文下的模型，不是工具包整条管线。「真实终评」是 453 轮假名化的对话，来自三位知情同意的内部员工，按生产口径标注（「参照标签」，不是咨询师的分数）。外部用户的对话从不进入训练。

### v10h 改了什么

v10h 沿用 v10 的提示词和训练配方，把合成训练行的答案换成 Hamo 请的真人咨询师复核后的分数。他们的姓名、人数和资质不公开；这份复核的限度见技术档案的 [How it was trained](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#how-it-was-trained) 一节。复核与此前的口径分数带或叠加规则不一致时，以复核为准：这是创始人看到结果之后的决定。

- **A（行动力）** 跟随复核，不跟此前的口径分数带，读数变低。A 卷上落在这些分数带内的题从 v10 的 590 题降到 519 题（共 632 题）。跑步 50/50 → 26/50、散步 52/52 → 40/52：复核把这两类的一部分行从 1.0 改成 1.5，v10h 学到了这个比例。协作式求助 27/40 → 1/40（多数打 1.5）：复核表没有这一类，两者的联系是推断。健康习惯 54/59 → 45/59 不同：复核表里最接近的 30 行 A 都还 ≥ 2，更像是压低 A 的规律被推广过头，不是标签的要求。成对方向没有退：154 对中 150 对（v10 为 149 对）。真实终评上平均 A 是 0.43（v10 0.53，参照标签 0.84）。
- **W、E、B** 同样跟随复核，而这份复核不是一把尺子：它是分批做的，W、E、B 的打分前后有漂移，所以 v10h 学到的是折中。真实终评上平均 W 是 0.33（v10 0.39）。
- **H** 在真实消息上读数升高：真实终评上平均 H 是 0.13（v10 0.08，参照标签 0.14），而 H 在压力公式里权重最大。
- **B** 仍给「报告积极行动」记分，而且出现在更多消息上。真实终评上 453 轮中有 201 轮 B 为 0.0（v10 为 223 轮），全零输出 25.6%（v10 32.2%，参照标签 15.5%）。旧 B 卷（legacy 答案）上，造分（没有边界的题被打成 B ≥ 1.0）是 104 题中 3 题 → 18 题，漏判（划了界限的题被打成 B ≤ 0.5）是 180 题中 21 题 → 8 题。
- **叠加规则。** 明确自杀意念规则、告别规则和 W 安全修复（见下面的「v10 打的是什么」）不再叠加到合成行的复核分上。相应的行数见技术档案；这些是关于标签的事实，与危机处理无关（禁令 ③）。
- **v10 打成 B 2.5 的那句话**（见下面的「v10 打的是什么」），v10h 打 B 0：带不带句末句号都一样，随包 q8、MLX bf16、transformers bf16 都一样（无上下文）。这只是一句话，别的题上翻转还在（438 道自我消融题中 4 道，596 道标准答案为 0 的题中 4 道，真实终评 166 轮参照 B 为 0 的轮次中 13 轮），所以 v10h 给出的高 B 仍不能当作守住了边界的证据（详见 [FAQ](faq.md)）。
- **算出的压力。** 真实终评上，按 v10h 的分数算出的平均每轮原始压力变化是 −0.63（v10 −0.72，参照标签 −0.68），会话回放漂移 −0.14，与 v10 相同（闸门 G7 的范围：−0.83 至 −0.43，漂移 ±0.15 以内）。会话回放的 295 轮里，算出的压力 ≥ 6.0 的轮次，v10h 两个种子是 64–68 轮，v10 两个种子是 56–58 轮，参照标签是 43 轮。

### 从 v10 升级的步骤

1. **v10 和 v10h 的分数不混进同一条历史或轨迹**。A、W 的平均读数变低，全零输出变少，跨切换点的趋势线会出现一个台阶，那是模型变了，不是人变了。每个分数都记下模型版本；切换时新开历史或重评存档的消息；统计与报表按版本分开。
2. **在 v10 分数上定的阈值要重新核对；让分桶把关任何事之前，先用自己的数据核对**。4.0 / 7.0 阈值与压力权重在工具包 0.4.0 里没有改，而 v10h 的 A 跟随复核，它们不是按这个定的。对 v10h，支撑它们的是一份内部员工对话考卷上的闸门 G7，打分用的是没有截短的完整上下文，漂移离界限只差 0.013。请把你自己人群的真实、授权会话用 v10h 的分数过一遍 `update_stress`；在此之前，分桶只供人参考，不要用它控制系统行为。
3. **任何东西依赖 A 之前，先检查它**。真实对话没有咨询师分数，真实考卷的参照标签用的又是旧 A 口径，所以 v10h 的 A 没有真实对话上的测量。请拿你自己的真实、授权对话对照一批人工打分的样本。
4. **固定模型版本**（见下一小节）。
5. **把升级当作换评分器**，做法同「升级到 v10」第 7 步：先跑影子，切换标准预注册，对照回放整段会话的轨迹。
6. **自检部署**：`python eval/run_exam.py`（合格带见「运维接线」）。

### 固定版本与回退

Hugging Face 的 `main` 现在是 v10h，`from_pretrained("HamoAI/hamo-score-0.6b")` 和工具包的 `TransformersClient()`（加载 `main`）拿到的都是 v10h。无论跑哪个版本都请固定：safetensors 用 `revision=` 固定完整提交哈希（`TransformersClient` 没有 `revision` 参数，须把按固定 revision 下载的快照本地路径传给 `model_id`），GGUF 按 sha256 摘要固定。文件名、摘要与 revision 见英文部分「Pins and rollback」的代码块（v10h 的 revision 为 d29c03288b6f553c748c9b9daefcb34b0f405497，v10 的为 f3869312f0222992c3eb2e938e78090de38eb80a）；所列五个 GGUF 都在 `main` 的 `gguf/` 下。

- **服务端**：参考服务器在 ollama 里注册的是不带版本的模型名 `hamo-score-0.6b`，所以用 `main` 执行 `docker compose up --build`，会在**同一个名字下**把原先的模型换成 v10h。请用 `main` 或 `v0.4.1`：`v0.4.0` 标签里的 compose 文件会在下载这一步失败。更新仓库后要在 `server/` 下运行 `docker compose up -d --build`：compose 只在 api 镜像缺失时才构建，不加 `--build` 就继续用已经构建好的镜像，也就是旧的服务代码；`docker compose down` 之后、在同一台机器上重新克隆之后也是这样。`docker compose exec ollama ollama show hamo-score-0.6b --modelfile` 会在 `FROM` 行打印 blob 摘要，与代码块里的摘要比对即知跑的是哪一版。要继续跑 v10、v9 或 v7，请先按 [`server/docker-compose.yml`](../server/docker-compose.yml) 顶部的注释改掉文件名和两处摘要。不用 Docker 时，模型一直用它创建时的那个 GGUF：要换版本，把 [`server/Modelfile`](../server/Modelfile) 的 `FROM` 指向想用的文件，重新 `ollama create`。用 Docker 时，换版本后旧的 GGUF 留在 `model-cache` 卷里（每个约 640 MB），ollama 会清掉自己那一份。这不会造成问题。要删掉一个：`docker compose run --rm --no-deps --entrypoint rm setup -f /models/<file>`。
- **留在 v10**，适合照 v10 分数建的阈值或历史暂时无法重建基线，或想让 A 回到此前的分数带时（A 卷带内 632 题中 590 题，v10h 519 题）：自检用 `python eval/run_exam.py --labels v10`，标签与默认相同，按 v10 的合格带判（见「运维接线」）。这样就放弃了 v10h 更贴近咨询师复核的部分，「v10 打的是什么」里那句话的 B 也回到 2.5。v10 自己的验收状态见「升级到 v10」的末尾。
- **留在 v9**：自检用 `python eval/run_exam.py --labels v9`。不要把它的分数喂给 `update_stress()` 或 `energy_state()`；参考服务器跑 v9 时，`POST /score` 返回的 `stress` 与 `energy_state` 字段也不要用（见下面的更正）。v9 没有通过自己预注册的五道闸门中的两道，其中一道是 v9 的闸门 5（W 安全）。
- **留在 v7 或更早**：自检用 `python eval/run_exam.py --labels pre_v9`。v7 早于明确自杀意念规则：在 v7（随包 q8）上，189 道「想死但求助」题的平均原始压力变化是 −0.29（v10 为 +2.37，v10h 为 +2.51）；比 v7 更早的版本没有在这些题上测过。无论哪个版本，模型前面的闸门都不可省（禁令 ③）。

### v10h 的验收状态

v10h 的预注册在训练前冻结，主要问题是：它是否比 v10 更接近咨询师的复核？在 978 道留出的合成题上，答案是肯定的：与复核的平均绝对误差是 0.142，v10 是 0.255。预注册还沿用了 v10 的 18 项检查，v10h 过了 17 项。没过的是 G5a；G5a 和 G5b 都是危机处理的替代指标，创始人裁定危机处理不归本模型，预注册因此把这两项定为只报告。其余 16 项全过。与复核的比较只在合成消息上：真实对话没有咨询师分数；在真实终评上，以参照评分器为准，v10h 与 v10 打平（453 轮中落在同一状态桶的分别是 440 和 435 轮）。完整说明与所报告各项检查的表格见技术档案的 [Evaluation](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation) 一节。

## 升级到 v10

*本节写的是上一版（工具包 0.3.x）。除非上面 v10h 的部分另有说明，它仍然适用。*

v10 在 2026-10-06 至 2026-10-31（UTC）期间是 Hugging Face 上的默认权重，工具包 0.3.0、0.3.1 的参考服务器跑的也是它；v9 在 2026-09-30 至 2026-10-06 期间是默认权重。各版本的对照表、固定版本与回退步骤都在上一节。

v10 另加**明确自杀意念规则**：消息含明确自杀意念时，A 封顶 1.0、B 为 0（这两条是 v10 新增），W 不低于 2.5（这条下限来自 v9 的 W 安全修复）。「v7 及更早」包括 v6.1 和社区 GGUF（`mradermacher/hamo-score-0.6b-GGUF`）；后者量化自 v4 权重，比 v10h 落后五个版本（v6.1、v7、v9、v10、v10h），本页的数字都不是在它们上面测的。

### v10 打的是什么

- **A（行动力）** 沿用 v8 口径，与 v9 相同：「主动推动处境或疗愈关系向前，不含情绪调节」。高：做决定、主动求助、健康习惯。中档（1.0–1.5）：单次散步或跑步、做练习、克制冲动、约好下次再聊。0–0.5：当下平复情绪、把决定交给别人。告别、安排后事类信号 A = 0。
- **B（边界感）** 回到 v7 及更早版本的 legacy 口径：宽泛理解的「清晰的自我表达」。高：说出需要、界限、立场或价值，以及平静有条理的自述、积极行动类消息。低：混乱的宣泄、零碎的只言片语、不展开的一句心情。v9 更窄的 crisp 口径（只算边界标记，多数消息为 0）不在 v10 里。
- **明确自杀意念规则**：A 封顶与 B 归零是新增的，为的是不让求助把算出的压力拉低。规则落在 v10 的训练标签上，工具包在推理时不执行它。新旧 W 安全卷共 189 道合成的「想死但求助」题上，按 v10 的分数算出的平均原始压力变化是 +2.37（闸门 G8 要求 ≥ 0；v10h 为 +2.51），v9 是 −0.24，v7 是 −0.29。这些题与 v10 的训练补丁出自同一类生成器：说明的是已知范围内没有退步，不是泛化。这些数字说的是压力公式在这类题上的方向，不是危机检测（禁令 ③）。
- **一条已知的 B 符号翻转**：不带上下文时，v10 把「行，我全听你的，你说哪天去就哪天去。」打成 B 2.5，v7、v9 与 v10h 打 0。此前的模型卡拿这句话说明「仪器不可把自我消融读成边界」（v7 卡印的是不带句末句号的写法，v10 对那种写法打 B 2.0；v9 卡只用了前半句），所以 v10 给出的高 B 不能当作守住了边界的证据（详见 [FAQ](faq.md)）。

### 更正：「重调阈值」修不好 v9

工具包 0.2.0 与 v9 模型卡都让你在 v9 上先「重调阈值」再让分桶把关。这条建议不够。

- v9 的 B 用 crisp 口径，多数普通消息上 B 为 0。压力公式给 B 的是负权重，B 为 0，减压项就没有了。真实终评上，按 v9 的分数算出的平均每轮原始压力变化为正，而参照标签为负，回放的会话向上漂：

  | 打分器 | 平均每轮原始压力变化 | 会话回放漂移 | B = 0.0 的轮次 |
  |---|---|---|---|
  | 参照标签 | −0.68 | 0（按定义） | — |
  | v7 | −0.76 | −0.10 | 234/453（51.7%） |
  | v9 | +0.37 | +0.51 | 429/453（94.7%） |
  | v10 | −0.72 | −0.14 | 223/453（49.2%） |
  | v10h | −0.63 | −0.14 | 201/453（44.4%） |

  「每轮原始变化」即 `update_stress` 里的 `delta`（含象限修正），在 0.8/0.2 平滑之前。「漂移」是把三轮及以上的 50 个会话（453 轮中的 295 轮）用该打分器的读数回放，会话结束时的压力与用参照标签回放之差的平均，单位是 0–10 量表上的分。
- 重调阈值或 B 的权重都修不好：权重乘的是 0。只有外加一个常数项才行，而所需的常数并不稳定：在真实终评回放上抵消漂移的取值，与在另一批内部员工轮次（入训的校准集）上调出的取值不同。我们没有找到可行的重调办法。
- 所以 v9 不再是默认版本。v10 把 B 改回 legacy 口径，并新增一道闸门（G7）直接检查压力轨迹。如果你已换到 v9，并把它的分数喂给 `update_stress()` 或任何给 B 负权重的公式，请换到 v10h 或 v10，或退回 v7。
- crisp 口径本身没有被否定：它对「划边界」的定义更干净，教师也更稳定。错在把它接进一条按 legacy 口径校准的公式，却没有给公式重新定心。v9 仍可下载，供想单独使用 crisp B 这把尺子的人取用（固定方式见上）。

### 升级到 v10 的步骤

1. **从 v9 来：不要把 v9 的状态带过来**。用 v9 分数累积出的压力值里含有上漂。建立在 v9 的 B 上的东西也要丢掉（真实终评上平均 B：v9 为 0.08，v10 为 0.98）：在 v9 分数上重拟的阈值或权重，以及默认「B = 0.0 是常态」的规则、报表、看板（禁令 ⑧）。
2. **从 v7 或更早版本来：A 换了含义；B 仍是同一套口径，只是明确自杀意念时 B 归零**。真实终评上平均 A 在 v7 下是 0.68，在 v10 下是 0.53；平均 B 是 0.92 与 0.98；在这份考卷上对压力的净效果很小（上表 v7 与 v10 两行）。这不代表两版分数逐条可以互换（见第 3、4 步）。
3. **不同版本的分数不混进同一条历史或轨迹**。v7、v9、v10、v10h 是四把不同的尺子；跨切换点的趋势线会出现一个台阶，那是模型变了，不是人变了。每个分数都记下模型版本；切换时新开历史或重评存档的消息；统计与报表按版本分开。
4. **让分桶把关任何事之前，先用自己的数据核对**。4.0 / 7.0 阈值与压力权重在工具包 0.3.0 和 0.4.0 里都没有改。它们按 legacy 口径的分数定，而 v10 的 A 用的不是那套口径；对 v10，支撑它们的是一份内部员工对话考卷上的闸门 G7（上表 v10 一行；允许范围：平均变化 −0.83 至 −0.43，漂移 ±0.15 以内），打分用的是没有截短的完整上下文。请把你自己人群的真实、授权会话用 v10 的分数过一遍 `update_stress`；在此之前，分桶只供人参考，不要用它控制系统行为。阈值与权重是常量，`POST /score` 的 `energy_state` 字段也用它们算：要用自己的，就自己给返回的 `stress` 分桶，或用返回的 `scores` 自己算压力。
5. **任何东西依赖 A 之前，先检查它**。参照标签用旧 A 口径，v10 的 A 与它们的一致率低于 v7 是设计使然；v8 口径的 A 至今没有真实对话上的测量。请拿你自己的真实、授权对话对照一批人工打分的样本；核对分桶落在哪里不算这项检查。
6. **固定模型版本**（见上面的「固定版本与回退」）。
7. **把升级当作换评分器**。先跑影子（两边都评分，现役的说了算，每一对都记录），切换标准预注册（示例见微调指南 [§6](finetune.md)），并对照回放整段会话的轨迹，不能只比逐轮一致率——没看出 v9 上漂的正是逐轮一致率。

### v10 的验收状态

签字的预注册方案里的 18 项检查，v10 过了 17 项。没过的那一项 G5a，当初是作为危机处理的替代指标设的；看到结果之后，创始人裁定：危机处理不由本模型判定，也不由它的 W 分数判定，而是在模型外围的确定性代码里做（Hamo 称之为「脊柱」）。按签字的预注册判定为**拒收**；v10 的发布出自创始人的决定。这是在结果已知之后对一道预注册闸门的豁免，也是连续第二个未通过预注册闸门、由创始人决定发布的版本（v9 是五道闸门没过两道）。完整说明与所报告各项检查的表格见技术档案的 [Evaluation](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation) 一节。

## 运维接线

- **预热**：模型每次（重）启动后先发一条预热请求，并保持 `keep_alive=-1`（`OllamaClient` 每次请求都带）。预热请求要用长超时，不要走 8 秒的客户端：客户端断开时 ollama 会中止加载，比超时更慢的加载永远完不成。在一台 Apple 芯片的 Mac 上（Colima 里的 Docker，arm64 CPU，ollama 0.40.13），这只在人为限制 CPU 或缩短超时的情况下复现过，慢硬件本身没有测过。参考服务器上，机器重启或 `ollama` 崩溃后，模型回来时是未加载的。这时 `api` 的健康检查（见下面的「参考服务器」）会加载它，除非有请求先加载了；比 `SCORE_TIMEOUT` 更慢的加载，它也能等完。
- **超时与回落**：调用设硬超时，并定义回落：旧评分器，或跳过这条消息（跳过等于无操作）。工具包客户端与参考服务器的 `POST /score` 默认 8 秒；运行 ollama 的 ARM CPU 服务器上，v10h q8 GGUF 每条消息 P50 2.09 秒、P95 2.57 秒、最长 2.87 秒（138 道按工具包截短规则构造的合成题；v10 在同一项核对上是 P50 2.13 秒、P95 2.53 秒、最长 2.91 秒）。这不是最坏情况：这些提示词远短于护栏允许的长度，而 CPU 上的延迟随提示词变长而增加，护栏上限处的延迟没有在 v10 或 v10h 上测过。每次回落都记原因，并记下每个分数出自哪个评分器；回落率超过百分之几，说明有地方出了问题。参考服务器本身没有回落。超时（默认 8 秒；要改就在 `api` 服务的 `environment` 里设 `SCORE_TIMEOUT`）或模型不在时，`POST /score` 返回 HTTP 500，正文是 `Internal Server Error`。回复解析不出来时返回 HTTP 200，`scores` 为 null。闸门命中时 `scores` 同样是 null，但 `crisis.triggered` 为 true：要先读 `crisis`，命中的转入你的危机处理路径。其余两种情况按跳过或回落处理。从 0.4.1 起，无效请求不会到达模型，返回 HTTP 422。例如：顶层或 history 某一轮里有未知字段；某一轮没有 `content`；`role` 不是 `user` 或 `assistant`（`role` 可以省略，默认 `user`）；`quadrant` 不是 `expert`、`supporter`、`leader`、`dreamer`（区分大小写）；`current_stress` 不是 0 到 10 之间的 JSON 数字（数字字符串、布尔值、NaN、Infinity 都会被拒绝）；`message` 缺失或不是字符串；请求体不是合法 JSON。`history`、`current_stress`、`quadrant` 写 `null` 等于没写。正文是 `{"detail": [{"type": ..., "loc": [...], "msg": ...}]}`，不回显被拒的值。服务器解码不了的请求体（比如用 GBK 发送的中文）得到的是 HTTP 400，这时 `detail` 是字符串，不是列表。要改请求本身：原样再发，得到的还是同样的回复。闸门命中时，即使其他字段无效也照常回答（HTTP 200，`crisis.triggered` 为 true，`scores` 为 null）：只要请求体能解析、`message` 是字符串，闸门就会在判定 422 之前读它。
- **任何基建变更后**（换量化、运行时或机器）：重跑 `python eval/run_exam.py`，对照[参考带](../eval/README.md)。脚本直接调用 ollama 的 `/api/generate`，不走 `POST /score`，而 Docker 参考服务器只发布 API 端口（怎样考它见该页）。默认按 v10 那套标签判卷：这份考卷没有咨询师标签，`--labels v10h`（默认）和 `--labels v10` 是同一套标签的两个名字（`eval/compare_quants.py` 有同一个 `--labels` 开关）。v10h 权重的合格带：维度级 84–90%、各维 ≥ 75%、A ≥ 81、JSON 合法率 ≥ 99%、危机闸门 10/10。在 llama.cpp + Metal 上，A 的下限高于 v7 权重（这套标签上 A 为 80.5）；经 ollama 在一台 Apple 芯片的 Mac 上（Colima 里的 Docker，arm64 CPU，ollama 0.40.13）实测，模型已预热时，v7 的 A 是 81.0，正好压线。两种情况脚本都打印 `A81%`，所以还要看维度级和 B（见 [eval/README.md](../eval/README.md)）。v10 权重的合格带：其余相同，A ≥ 86%。标签与 v10 的训练标签出自同一套教师提示词：这份卷检查的是接线，不是模型质量。过关说明你的部署与考卷标签的一致程度和参考值相当、`num_predict` 没有设得过小，走的是工具包自己的提示词、采样与解析器，不是你的。它说明不了你跑的是哪个版本（v10 权重也过得了 v10h 的带），也不检查聊天模板和 `stop`：在 ollama 0.40.13 上，60 道题里缺了这两项的 ollama 标签读数相同。这两项用 `ollama show <tag> --template` 和 `--parameters` 核对。
- **参考服务器**：`POST /score` 没有认证。compose 只把 API 发布在 `127.0.0.1:8080` 上。[Docker 文档](https://docs.docker.com/engine/network/port-publishing/)提醒：在 Docker Engine 28.0.0 之前的版本上，同一网段的主机仍能访问这样发布的端口。`127.0.0.1` 不是认证手段：这台机器上的任何进程都能调用 API。要给其他机器用，先在前面放上你自己的访问控制。运行在这台机器上、Docker 之外的反向代理可以转发到 `127.0.0.1:8080`，compose 文件不用改。只有访问控制在这台机器之外时，才把 `server/docker-compose.yml` 里 `api` 服务的 `ports` 改成 `"8080:8080"`：这样 API 会发布在这台机器的每个网卡上，本机的代理就不再挡在它前面了。`GET /healthz` 给一条短探测打分：只有回复能在 `SCORE_TIMEOUT` 内解析成分数时，才返回 HTTP 200 和 `ok: true`；否则返回 HTTP 503，带 `ok: false` 和 `error`。它要在 ollama 的队列里排队，所以模型忙时可能报 503。它自己的超时是 `HEALTHZ_TIMEOUT`，默认 60 秒，`SCORE_TIMEOUT` 更长时取后者。探测耗时超过 `SCORE_TIMEOUT` 时，即使它已把模型加载完也返回 503；模型够快的话，下一次就能通过。`api` 的健康检查每 60 秒调用一次 `/healthz`，所以空闲时每分钟多一次模型调用。Docker 显示 `healthy`，连续失败三次后显示 `unhealthy`，不会因此重启容器。

## 十条禁令

① **不凭单句原始分做决定**。分数是给平滑器用的逐句信号；有了平滑，逐句噪声才到不了决策。

② **不拆闸门，不用模型替代闸门**。闸门因为是确定性的才可审计：词表的缺口就是那些缺口。在闸门**之后**另加一道独立筛查可以，但只能是加法，不能替代它。

③ **不把模型当危机检测器**。它给一条消息的五个维度打分，不识别也不处理危机；它的分数，包括 W 在内，没有一个是危机信号。危机处理由模型之前的确定性代码负责：凡把消息送进模型的路径都要先过这一层，批量重评、按整次访问重评的路径也不例外；闸门命中时，这条消息不评分，也不得进入后续提示词携带的历史。`CrisisGate` 是一份关键词表，只是起点，不是完整筛查：新旧 W 安全卷共 189 道合成的「想死但求助」题里，它命中 107 题（56.6%）。请用你人群里的说法扩充词表并逐条测试，并考虑在闸门之后再加一道独立筛查；依赖它之前，先在自己的数据上量它的召回率。

④ **不改提示词**。不加评分指令，不改格式：细则已烧进权重，框架与 `build_prompt` 不同的提示词（加指令、改字段名或顺序、把框架翻译成别的语言）即出分布，而且不会有任何提示。上下文给多少是另一回事（见禁令 ⑥）。从 0.4.1 起，`build_prompt()` 会从消息和 history 每一轮的 `role`、`content` 里去掉 `<|im_end|>` 和 `<|im_start|>`，所以消息不能结束自己这一轮。`score_message()` 和 `POST /score` 都继承这一点。其余文字仍留在提示词里。不用 `build_prompt()`、自己拼提示词的，要对这些字段调用 `strip_turn_markers()`：否则消息里带这两个标记就能结束自己这一轮、再开一轮，分数随之来自伪造的文字。替换一遍不够：`<|im_<|im_end|>end|>` 去掉一遍后还会留下一个。分词器里的其他附加标记（例如 `<|endoftext|>`、`<think>`、`</think>`、`<tool_call>`）不会被去掉。在一台 Apple 芯片的 Mac 上（Colima 里的 Docker，arm64 CPU，ollama 0.40.13），把其中 8 个逐个插入 40 条合成消息，插在中间或下一句之前，经 ollama 的 `/api/generate` 打分：40 条里有 37–40 条，五个分数都在不插入时的 ±0.5 内，与插入普通文字 `[x]`（40 条里 37 条和 39 条）差不多。

⑤ **不升温度，也不放任 `repeat_penalty` 用默认值**。`repeat_penalty 1.1`（ollama 0.32.9 及以前的默认值，0.32.10 起为 1.0）会把分数推离 0（在 v10 上测得：q8 GGUF，旧 B 卷，legacy 答案，造分 3/104 → 15/104，B 符号翻转 93 题中 2 条 → 4 条）。须设温度 0、`repeat_penalty 1.0`、`top_k 0`、`top_p 1.0`：`OllamaClient` 每次请求都会带上，`TransformersClient` 用贪心解码并显式设 `repetition_penalty=1.0`；你自己的客户端也必须照做（详见 [eval/README.md](../eval/README.md)）。

⑥ **不超出截断护栏喂上下文**。`build_prompt` 保留最近 3 轮、每轮 200 字，消息 500 字封顶：这是 CPU 的延迟预算，也是自检考卷所用的配置。它不是本页此前所说的「模型在训练里见过的」：v10 的训练行有 36.6% 上下文超过 3 轮。

⑦ **量化低于 q8 必须重考**。v10 和 v10h 都只量过随包的 Q8_0；已公布的 Q8_0 / Q6_K / Q4_K_M 对比是在 v7 权重上做的。自行量化后，先跑 `eval/compare_quants.py` 再让它把关任何事，并看方向性表格而不只看一致率（见 [eval/README.md](../eval/README.md)）。

⑧ **不把 B（边界感）当关系诊断**。它只对单条消息的措辞打分。legacy 口径下，B 大于 0 不能证明这个人划了边界（平静的自述、积极行动同样得分）；B = `0.0` 也不是警讯：真实终评上 v10h 有 201/453 轮（44.4%）打 B `0.0`（v10 是 223 轮，49.2%）。工具包 0.2.0 在这里称它为「常态（真实终评 94%）」，那是 v9 的 crisp 口径（v10 发布时按随包 q8 重测：453 轮中 429 轮，94.7%），对 v10 和 v10h 都不成立。B 还可能朝要紧的方向错（见那条已知的 B 符号翻转）。

⑨ **不用合成数据校准阈值，也不跨版本沿用阈值或历史**（见上面的升级步骤）。对 v9，重调修不好上漂（见上面的更正）。

⑩ **面向消费者的部署不省略 AI 身份披露**：这是许可证要求，工具包带现成文案。
