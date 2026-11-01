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

> **Toolkit 0.4.0 moves to hamo-score-0.6b v10h. If you moved to v9, read the correction below:
> our advice to "re-tune thresholds" for v9 was not enough.**
>
> - **What v10h is.** v10's prompts and training recipe, with the answers on the synthetic
>   training rows replaced by the scores of a review by human counselors engaged by Hamo. Their
>   names, number and credentials are not published; the limits of the review are in the model's
>   [technical record](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#how-it-was-trained)
>   (linked from the model card). The 440 pseudonymised turns from consenting internal staff
>   keep their teacher-era labels.
> - **What it scores.** Where the review differs from the earlier rubrics, the review stands.
>   Those rubrics are v10's: A under rubric v8, B on the **legacy rubric** that v7 and earlier
>   used (v9's narrower "crisp" B is in neither version), and an explicit-ideation rule in the
>   training labels (A capped at 1.0, B 0, with v9's W floor of 2.5), which is no longer applied
>   as an overlay on v10h's synthetic rows. On the 453-turn real final exam (pseudonymised
>   conversations of consenting internal staff; each version's shipped q8 GGUF, llama.cpp with
>   Metal), A and W read lower than v10's (mean A 0.43 against 0.53, mean W 0.33 against 0.39)
>   and all-zero outputs are fewer (25.6% against 32.2%). **Scores are not comparable across
>   versions** (A changed meaning at v9; B changed at v9 and changed back at v10; v10h's
>   synthetic labels are the review's): store the model version with every score and keep
>   versions apart in histories and reports. v10h's A has no real-conversation measurement: real
>   conversations have no counselor scores, and the real exams' reference labels use the older
>   A rubric. Check it against a human-scored sample of your own consented conversations before
>   anything relies on it.
> - **Correction about v9.** v9 scores B under the crisp rubric, so B is 0 on most ordinary
>   messages and the relief term of a stress formula with a negative B weight
>   (`hamo_score.stress` is one) disappears: on the real final exam the mean raw per-turn stress
>   change computed from v9's scores is +0.37, where the exam's reference labels give −0.68, v10
>   −0.72 and v10h −0.63. Re-tuning the cut-offs or the B weight cannot repair this — a weight
>   multiplies a zero — so if you feed v9 scores into such a formula, move to v10h or v10, or go
>   back to v7, and do not carry stress accumulated from v9 scores into the new deployment.
> - **Acceptance status.** v10h's registration, frozen before training, asked one main question:
>   is it closer to the counselor review than v10? On 978 held-out synthetic items the answer is
>   yes. It also carried over v10's 18 checks and met 17. The one it did not meet, G5a, and G5b
>   were stand-ins for crisis handling; the registration made both report-only, because the
>   founder ruled crisis handling outside this model. The other 16 all passed. The comparison
>   with the review is on synthetic messages only: real conversations have no counselor scores,
>   and on the real final exam v10h ties v10 against the reference scorer. Full statement, and
>   v10's own status (rejected under its signed pre-registration, released by the founder's
>   decision): the [technical record](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation).
> - **Known B sign flip.** v10 scores the self-erasure sentence 「行，我全听你的，你说哪天去就哪天去。」
>   ("Fine, I'll do whatever you say — we go whichever day you say.") **B 2.5**; v10h, v9 and v7
>   score it 0 (no context; shipped q8 GGUFs, llama.cpp with Metal). That is one sentence, and the
>   very example earlier model cards used for "the instrument must not read self-erasure as a
>   boundary". v10h's sign-flip counts are inside the registered caps but not zero (4 of the 596
>   items whose B should be 0): do not read a high B from v10h or v10 as proof that a boundary
>   was kept ([FAQ](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/faq.md)).
> - **The pip version does not choose the model.** `pip install -U hamo-score` changes no
>   weights: an ollama model keeps serving the GGUF it was created from, and
>   `TransformersClient()` and `from_pretrained("HamoAI/hamo-score-0.6b")` load Hugging Face
>   `main`, which is v10h from 2026-10-31 (UTC), was v10 from 2026-10-06 (UTC) until then
>   and v9 from 2026-09-30 before that. The reference server registers the unversioned ollama
>   name `hamo-score-0.6b`, so `docker compose up --build` from `main` replaces whatever that name
>   served before with v10h.
> - **v10, v9 and v7 remain available.** `gguf/hamo-score-0.6b-v10.q8.gguf`,
>   `gguf/hamo-score-0.6b-v9.q8.gguf` and `gguf/hamo-score-0.6b-v7.q8.gguf` sit next to the v10h
>   file on `main`; their safetensors are at pinned revisions. Digests, revisions, how to pin or
>   switch (ollama, Docker, transformers) and the remaining upgrade steps:
>   [Upgrading to v10h](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/integration.md#upgrading-to-v10h).
> - **0.4.1:** unlike 0.4.0, this release changes the library's behaviour. The new
>   `strip_turn_markers` removes `<|im_start|>` and `<|im_end|>`, nested forms included.
>   `build_prompt` applies it to the message and to each history `role` and `content`; a prompt
>   whose text has no marker is byte-identical to 0.4.0. `CrisisGate.check` reads the text with
>   the markers removed. `OllamaClient`'s HTTP errors now carry ollama's reason (still
>   `urllib.error.HTTPError`, same code, body still readable). The reference server changes
>   too. Its port is published on `127.0.0.1:8080` only. `POST /score` now answers HTTP 422
>   to requests it accepted before: an unknown field at the top level or inside a history turn,
>   a history turn with no `content`, a `role` other than `user` or `assistant`, a `quadrant`
>   other than `expert`, `supporter`, `leader`, `dreamer`, or a `current_stress` that is a number
>   string, a boolean, NaN, Infinity or outside 0 to 10. `/healthz` can return HTTP 503. After
>   you update the repository, run `docker compose up -d --build` in `server/`. No change to
>   weights, exam, labels or bands.
> - **0.4.0:** serves v10h, whose synthetic labels were re-scored by human counselors engaged
>   by Hamo; no change to the library's behaviour.
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

# 1. get the model, one-time. huggingface_hub provides the hf command. For v10, v9 or v7 fetch that GGUF instead and edit FROM in server/Modelfile
pip install -U huggingface_hub
hf download HamoAI/hamo-score-0.6b gguf/hamo-score-0.6b-v10h.q8.gguf --local-dir /tmp/hamo
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
    print(r.scores)             # v10h: {'A': 1.5, 'W': 0.0, 'E': 0.0, 'H': 0.0, 'B': 1.5}
    stress = update_stress(r.scores, current_stress=3.0)
    print(energy_state(stress)) # 'positive' / 'negative' / 'neurotic'
```

That's the whole intended shape: **gate → score → smooth → bucket**. Scores are
per-message signals; never act on a single raw score.

The read-out in the comment is from the shipped v10h q8 GGUF (llama.cpp with
Metal). On this input the v10 q8 GGUF returns A 2.0, B 2.0, the v9 q8 GGUF
B 0.0 and the v7 q8 GGUF B 1.5, the last two with W 0.5: if you see one of
those, check which GGUF your model was built from.

`Error: 400 Bad Request: invalid model name` from `ollama create` (ollama
0.40.13) means the GGUF is not at the path in `FROM`;
`HTTP Error 404: Not Found: model '<name>' not found` from the client means
ollama has no model of that name.

Keep sampling neutral: temperature 0, `repeat_penalty 1.0`, `top_k 0`,
`top_p 1.0`. The toolkit's clients and `server/Modelfile` already do; set all
four yourself if you call the model any other way. Measured on v10: at
`repeat_penalty 1.1`, ollama's default through 0.32.9 (1.0 from 0.32.10),
fabrication on the old B exam (legacy
key) — no-boundary
items (five classes) and low arms of pairs scored B ≥ 1.0 — rises from 3/104
(2.9%) to 15/104 (14.4%) for the shipped v10 q8 GGUF (llama.cpp with Metal).

## One-command server (Docker)

Run the whole pipeline as an HTTP service:

```bash
git clone https://github.com/HamoAI/hamo-score-toolkit.git && cd hamo-score-toolkit/server
docker compose up --build
```

It pulls the images, downloads the v10h GGUF, then creates and warms the model.
A first run pulls about 2.9 GB of images and the 639 MB GGUF, and takes about
8.7 GB of disk (measured on linux/arm64; x86 not measured). The GGUF is fetched
once per `model-cache` volume. Use `main`, as these commands do, or `v0.4.1`: the
compose file at the `v0.4.0` tag fails at the download step.

```bash
curl -s localhost:8080/score -H 'content-type: application/json' \
  -d '{"message": "虽然还是有点提不起劲，不过今天把拖了两周的体检约上了", "history": [{"role": "assistant", "content": "这周过得怎么样？"}], "current_stress": 3.0}'
```

It returns:

```text
{"crisis": {"triggered": false, "matched": []}, "scores": {"A": 1.5, "W": 0.0, "E": 0.0, "H": 0.0, "B": 1.5}, "latency_ms": ..., "stress": 2.4, "energy_state": "positive"}
```

Recorded on 2026-10-31 on one Apple-silicon Mac (Docker under Colima, arm64
CPU, ollama 0.40.13): `docker compose up` from a clean clone needed no other
step, and this request returned exactly these scores, `stress` and
`energy_state`. The VM had 4 CPUs and 6 GiB and the images were already pulled.
On the VM's first boot `/healthz` timed out until `systemd-logind`, spinning
inside the VM, was restarted; after `colima stop` and `start` this did not
recur. Compose pins `ollama/ollama:0.40.13` and `curlimages/curl:8.23.0`, the
images of that run; to change ollama, edit `image:` and run the self-check
again. On 2026-11-01, on the same Mac and VM size, with the images already
pulled, `docker compose up -d --build` from empty volumes finished in about
64 s (72 s on an earlier run), and this request again returned exactly these
scores, `stress` and `energy_state`.
We have no x86 run. A read-out can still differ from llama.cpp
with Metal: on the exam's 195 questions, with the model warmed and the prompt
cache off, 184 were identical and all were within ±0.5, and in a 100-item check
through ollama on an ARM CPU server, also with the cache off, 96 were identical.

`POST /score` runs gate → score, then smooth → bucket when the request carries
`current_stress`; crisis-gated requests never reach the model. `GET /healthz`
scores a short probe and returns HTTP 200 with `ok: true` only if the reply
parses as a score within `SCORE_TIMEOUT`; otherwise it returns HTTP 503 with
`ok: false` and `error`. It runs outside `/score`'s worker pool, so a full pool
does not block it, but it still waits in ollama's queue, so a busy model can
report 503. Its own timeout is `HEALTHZ_TIMEOUT`, by default 60 s, or
`SCORE_TIMEOUT` if that is longer. A probe that took longer than
`SCORE_TIMEOUT` returns 503 even if it finished loading the model; the next one
passes if the model is fast enough. To serve v10, v9 or v7 instead,
follow the note at the top of `server/docker-compose.yml`.

Operating notes:

- **Authentication.** `POST /score` has no authentication. Compose publishes the
  API on `127.0.0.1:8080` only.
  [Docker's documentation](https://docs.docker.com/engine/network/port-publishing/) warns that in Docker Engine releases older than 28.0.0, hosts on the same network segment can still reach a port published this way.
  `127.0.0.1` is not an authentication mechanism: any process on this machine can
  call the API. To serve other machines, put your own access control in front.
  A reverse proxy running on this machine outside Docker can forward to `127.0.0.1:8080`, with the compose file unchanged. Change the `api` service's `ports` line in `server/docker-compose.yml` to `"8080:8080"` only if the control runs outside this machine: that line publishes the API on every interface of this machine, so a proxy here no longer stands in front of it.
- **Failures.** The server has no fallback of its own. On a timeout (8 s by
  default; set `SCORE_TIMEOUT` under the `api` service's `environment`) or with
  the model down, `POST /score` returns HTTP 500 with the body
  `Internal Server Error`. A reply that does not parse returns HTTP 200 with
  `scores: null`. A gate hit also has `scores: null`, with `crisis.triggered`
  true: read `crisis` first and route those to your crisis pathway. Treat the
  other two cases as skip or fallback. An invalid request gets HTTP 422 with
  `{"detail": [{"type": ..., "loc": [...], "msg": ...}]}`; the reply does not
  echo the rejected value. Invalid requests include a missing `message`, a body
  that is not valid JSON, a history turn with no `content`, a `role` other than
  `user` or `assistant` (`role` may be left out; it defaults to `user`), a
  `quadrant` other than `expert`, `supporter`, `leader`, `dreamer`
  (case-sensitive), and the cases in the next two notes. A body the server cannot
  decode, such as Chinese text sent in GBK, gets HTTP 400 instead, and its
  `detail` is a string, not a list. If the body parses and `message` is a string,
  the gate still reads it, so a gate hit gets its normal HTTP 200 reply even if
  another field is invalid.
- **`current_stress`** must be a JSON number from 0 to 10; integers are fine, and
  0 and 10 are accepted. A number string, a boolean, NaN, Infinity or a value
  outside the range gets HTTP 422.
- **Unknown fields.** The context field is `history`. An unknown field, at the
  top level or inside a history turn, gets HTTP 422, so a request that sends
  `context` is rejected, not scored with no context.
- **Chat tokens.** From 0.4.1 `build_prompt` removes `<|im_end|>` and
  `<|im_start|>` from the message and from each history `role` and `content`, so
  a message cannot close its own turn; `score_message` and `POST /score` inherit
  this. Only the markers go: the rest of the text stays in the prompt and is
  scored. Code that builds prompts without `build_prompt` must call
  `strip_turn_markers`
  ([integration guide](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/integration.md)).
  `build_prompt` does not remove the tokenizer's other added tokens, for example
  `<|endoftext|>`, `<think>`, `</think>` and `<tool_call>`. On one Apple-silicon
  Mac (Docker under Colima, arm64 CPU, ollama 0.40.13), eight of them were
  inserted one at a time into 40 synthetic messages, in the middle or before a
  following sentence, through ollama's `/api/generate`: all five scores stayed
  within ±0.5 of the same text without the token on 37–40 of 40, about the same
  as inserting the plain text `[x]` (37 and 39 of 40).
- **Stopped download.** A stopped download restarts by itself on the next run: the
  GGUF downloads to `<file>.part` and is renamed when curl succeeds, so a stop
  leaves only `.part`, which the next run replaces. If `setup` still stops after
  `uploading GGUF blob` with curl error 22, the cached GGUF does not match the
  digest in the compose file. There are two cases: a partial file under the final
  name, left by a compose file older than 0.4.1, or a digest mismatch after you
  edited the compose file for another version. `docker compose down` and a new
  clone do not clear a partial file. If you edited the file for another version, check both digests
  first. Otherwise remove the file and start again:
  `docker compose run --rm --no-deps --entrypoint rm setup -f /models/hamo-score-0.6b-v10h.q8.gguf`,
  then `docker compose up --build`.
- **Restarting.** `ollama` and `api` restart by themselves after a crash or a
  reboot, and stay stopped after `docker compose stop`. `setup` does not restart
  with them, so after a reboot or an `ollama` crash the model comes back unloaded:
  `api`'s health check reloads it, or the first request does if it loads in time.
  The check calls `/healthz` every 60 s, so when idle it adds one model call a
  minute. Docker shows `healthy`, or `unhealthy` after three failures in a row,
  and does not restart a container for that. On one Apple-silicon Mac (Docker under Colima, arm64 CPU, ollama 0.40.13)
  the reboot was a VM restart; no Linux host's reboot was tried. To restart the containers by hand,
  use `docker compose stop` then
  `start`. With the compose file unchanged, `docker compose up -d` restarts
  nothing: it re-runs `setup`, which warms the model. After you edit the compose
  file, run `docker compose up -d`: it recreates the changed services, and `stop`
  and `start` do not apply the edit. After you update the repository, run
  `docker compose up -d --build` in `server/`: compose builds the api image only
  when it is missing, so without `--build` it keeps the image it already built,
  with the old server code. That also holds after `docker compose down` and from
  a new clone on the same machine. Plain `docker compose restart` can leave
  `setup` failed and the model unloaded; `api` keeps serving, the first request
  loads the model (about 2 s on that Mac), and `docker compose up -d` repairs
  `setup`. A load slower than `SCORE_TIMEOUT` does not finish through
  `POST /score`, because ollama aborts a load when its client disconnects; the
  health check's longer limit can finish it. On that Mac we simulated this
  with a short `SCORE_TIMEOUT`; slow hardware itself was not tested (see the
  [FAQ](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/faq.md)).

## Verify your deployment

The toolkit self-check exam: 195 synthetic, teacher-labelled questions plus 10
handwritten crisis-gate cases. Run it from the repo root against your own
deployment, with the label set of the version you serve:

```bash
python eval/run_exam.py
python eval/run_exam.py --labels v10
python eval/run_exam.py --labels v9
python eval/run_exam.py --labels pre_v9
```

The first line is for a v10h deployment (its default labels are v10's set, see
below). `--labels v10` is for a v10 deployment (same labels, its own band).
`--labels v9` and `--labels pre_v9` check a v9 or v7 deployment on purpose.

`run_exam.py` calls the ollama endpoint itself (`--base-url`, default
`http://127.0.0.1:11434`), not `POST /score`, and the Docker reference server
does not publish that port. To check that server, add
`ports: ["127.0.0.1:11435:11434"]` to the `ollama` service in
`server/docker-compose.yml`, run `docker compose up -d` in `server/`, then from
the repo root pass `--base-url http://127.0.0.1:11435`. With the defaults the script fails, or
grades whatever a host ollama serves as `hamo-score-0.6b`.

Pass band for v10h: dimension-level 84–90%, each dimension ≥ 75%, **A ≥ 81**,
JSON ≥ 99%, gate 10/10 (a keyword list; it does not depend on the model).
Reference, on an M1 Pro: 86.7% for the shipped q8 GGUF (llama.cpp with Metal,
`server/Modelfile` template, neutral sampling) and 86.8% for the v10h bf16
safetensors (MLX). On one Apple-silicon Mac (Docker under Colima, arm64 CPU,
ollama 0.40.13) the exam through the reference server's ollama reads 86.7% with
the model warmed, as compose leaves it, and the script prints `A82%`, not
`A83%`; it reads 86.4% if the exam's first question is the first request after
a model load. Both are inside the band. On llama.cpp with Metal the A floor sits
above v7 weights (A 80.5 on these labels); through ollama on Docker, warmed, v7
reads A 81.0, exactly on the floor. The script prints `A81%` either way, so also check
the
dimension-level number and B
([eval/README.md](https://github.com/HamoAI/hamo-score-toolkit/blob/main/eval/README.md));
v9 weights show up as B 57.4. A v10 deployment keeps its own
band: the same lines with **A ≥ 86%**, reference 87.3%. On llama.cpp with Metal
v10 reads A 91.8 where
v10h reads 82.6, so the A line also tells the two apart. Bands for the other
label sets, trivial baselines, quantization and troubleshooting:
[eval/README.md](https://github.com/HamoAI/hamo-score-toolkit/blob/main/eval/README.md).

**A pass checks wiring, not model quality.** It shows that your deployment agrees with the exam's labels about as well as the reference does, and that `num_predict` is not too small, through the toolkit's own prompt, sampling and parser, not yours. It does not show which version you serve (v10 weights also pass v10h's band), and it does not check the chat template or `stop`: on ollama 0.40.13 tags without them read the same on 60 questions. Check those with `ollama show <tag> --template` and `--parameters`. For the v10h GGUF on ollama 0.32.5, 0.40.12 and 0.40.13, `--template` prints the GGUF's own template, not the one in `server/Modelfile` (see the [FAQ](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/faq.md)). On the Docker server, run them in `server/`, prefixed with `docker compose exec ollama`. There are no counselor labels
for this exam: v10h is graded on v10's label set, so a gap against v10's number
says nothing about which is right. Those labels come from the same teacher
prompts as v10's training labels, so for v10 the exam is in-distribution by
construction. A constant 0.5 output already scores 77.9% on these labels,
so read the per-dimension lines and the distinct-read-out count that
`run_exam.py` prints, not the headline alone.

## What's in the box

| Module | What it gives you |
|---|---|
| `hamo_score.prompt` | The exact prompt format + built-in trimming as a latency guard (3×200-char turns, 500-char message), and `strip_turn_markers`. The real final exam and old B exam figures quoted here were run on full stored context, not this trimming |
| `hamo_score.parse` | Think-block-tolerant JSON parsing, grid snapping |
| `hamo_score.client` | `OllamaClient` / `TransformersClient` (needs `pip install "hamo-score[transformers]"`) + `score_message()` safe pipeline |
| `hamo_score.stress` | Reference smoothing (`0.8·history + 0.2·message`) + energy-state buckets. Weights and cut-offs were set on legacy-rubric scores (v7 and earlier); v10's A is on a different rubric and v10h's follows the counselor review: check the buckets on your own data before they gate anything. Do not feed it v9 scores |
| `hamo_score.safety` | `CrisisGate` (zh/en word lists, extensible) + AI-disclosure texts |

The default `CrisisGate` word lists are a starting point, not coverage. On the
189 synthetic ideation-plus-help items of the old and new W safety exams the
gate fires on 107. Extend the lists for your population and language.

## Where the details live

| Doc | What's in it |
|---|---|
| [Integration guide](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/integration.md) | Correct wiring, upgrading to v10h and v10 (the full correction about v9, pins and digests), the don't list |
| [FAQ](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/faq.md) | Sampling, crisis handling, the known B sign flip |
| [Fine-tuning playbook](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/finetune.md) | Adapting the model to your own population: data red lines, the LoRA recipe, acceptance gates, and the record of fourteen adjudicated generations, six of them rejected |
| [`examples/`](https://github.com/HamoAI/hamo-score-toolkit/tree/main/examples) | Quickstart, batch CSV scoring, a session-monitor demo with the crisis short-circuit (the last two take `--mock` to run without a model) |
| Technical record: [Evaluation](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation), [Limitations](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#limitations--known-residuals) | v10h's main question, the sixteen of the 18 checks that the technical record reports, v10's verdict, what was decided after results were seen, and why passing the synthetic exams shows neither generalisation nor, for v10h, that nothing fell outside the checks |

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

> **工具包 0.4.0 转向 hamo-score-0.6b v10h。已经换到 v9 的，请先读下面的更正：当时让大家为 v9「重调阈值」，这个建议并不够。**
>
> - **v10h 是什么。** 沿用 v10 的提示词和训练配方，把合成训练行的答案换成 Hamo 请的真人咨询师复核后的分数。他们的姓名、人数和资质不公开；这份复核的限度见模型的[技术档案](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#how-it-was-trained)（模型卡里有链接）。440 轮假名化的内部员工对话（当事人已授权）沿用教师时期的标签。
> - **打的是什么。** 复核与此前的口径不同时，以复核为准。此前的口径就是 v10 的：A 按 v8 口径，B 按 v7 及更早版本所用的 **legacy 口径**（v9 那套更窄的 crisp B 两版都没有），训练标签里还有一条明确自杀意念规则（A 封顶 1.0、B 为 0，并落实 v9 已有的 W 下限 2.5），这条规则在 v10h 的合成行上不再叠加。453 轮真实终评上（假名化的内部员工对话，当事人已授权；各版本随包 q8 GGUF，llama.cpp + Metal），A、W 的读数比 v10 低（平均 A 0.43 对 0.53，平均 W 0.33 对 0.39），全零输出更少（25.6% 对 32.2%）。**各版本的分数不可相互比较**（A 的含义在 v9 改过；B 在 v9 改过，v10 又改了回来；v10h 的合成标签来自复核）：给每个分数存下模型版本，历史与报表按版本分开。v10h 的 A 没有真实对话上的测量：真实对话没有咨询师分数，真实考卷的参照标签用的是旧 A 口径。依赖它之前，请先拿你自己授权对话里一批人工打分的样本核对。
> - **关于 v9 的更正。** v9 的 B 按 crisp 口径打分，多数普通消息的 B 是 0，B 为负权重的压力公式（`hamo_score.stress` 就是一个）里减压项随之消失：真实终评上，按 v9 的分数算出的平均每轮原始压力变化是 +0.37，考卷的参照标签是 −0.68，v10 是 −0.72，v10h 是 −0.63。重调阈值或 B 的权重都修不好，因为权重乘的是 0；把 v9 的分数喂进这类公式的，请换到 v10h 或 v10，或退回 v7，也不要把按 v9 分数累积的压力值带进新的部署。
> - **验收状态。** v10h 的预注册在训练前冻结，主要问题是：它是否比 v10 更接近咨询师的复核？在 978 道留出的合成题上，答案是肯定的。预注册还沿用了 v10 的 18 项检查，v10h 过了 17 项。没过的是 G5a；G5a 和 G5b 都是危机处理的替代指标，创始人裁定危机处理不归本模型，预注册因此把这两项定为只报告。其余 16 项全过。与咨询师的比较只在合成消息上：真实对话没有咨询师分数；在真实终评上，以参照评分器为准，v10h 与 v10 打平。完整说明，以及 v10 自己的验收状态（按签字的预注册为「拒收」，由创始人决定发布），见[技术档案](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation)。
> - **已知的 B 符号翻转。** 自我消融句「行，我全听你的，你说哪天去就哪天去。」v10 打 **B 2.5**，v10h、v9 与 v7 打 0（无上下文；各版本随包 q8 GGUF，llama.cpp + Metal）。这只是一句话，也正是此前的模型卡用来说明「仪器不可把自我消融读成边界」的例句。v10h 的符号翻转条数在预注册的上限之内，但不是 0（596 道 B 应为 0 的题里有 4 道）：不要把 v10h 或 v10 给出的高 B 当成「守住了边界」的证据（详见 [FAQ](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/faq.md)）。
> - **跑哪个模型不由 pip 版本决定。** `pip install -U hamo-score` 不换任何权重：ollama 里的模型仍跑它创建时用的那个 GGUF；`TransformersClient()` 与 `from_pretrained("HamoAI/hamo-score-0.6b")` 加载的是 Hugging Face 的 `main`，它自 2026-10-31（UTC）起是 v10h，此前自 2026-10-06（UTC）起是 v10，再之前自 2026-09-30 起是 v9。参考服务器在 ollama 里用不带版本号的模型名 `hamo-score-0.6b`，所以用 `main` 执行 `docker compose up --build`，会把这个名字下原先的模型换成 v10h。
> - **v10、v9、v7 仍可用。** `gguf/hamo-score-0.6b-v10.q8.gguf`、`gguf/hamo-score-0.6b-v9.q8.gguf` 与 `gguf/hamo-score-0.6b-v7.q8.gguf` 和 v10h 的文件一起放在 `main` 上，三者的 safetensors 在固定版本。摘要、版本号、怎样固定或切换（ollama、Docker、transformers）以及其余升级步骤，见[集成指南·升级到 v10h](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/integration.md#升级到-v10h)。
> - **0.4.1：** 与 0.4.0 不同，这一版改变了库的行为。新增的 `strip_turn_markers` 去掉 `<|im_start|>` 和 `<|im_end|>`，嵌套形式也一样。`build_prompt` 把它用在消息和每条 history 的 `role`、`content` 上；文本里没有这两个标记时，提示词与 0.4.0 逐字节相同。`CrisisGate.check` 读的是去掉标记后的文本。`OllamaClient` 的 HTTP 错误现在带上 ollama 给出的原因（仍是 `urllib.error.HTTPError`，状态码不变，正文仍可读取）。参考服务器也有变化。端口只发布在 `127.0.0.1:8080` 上。`POST /score` 对此前接受的这些请求现在返回 HTTP 422：顶层或 history 轮次里的未知字段，history 轮次缺少 `content`，`role` 不是 `user` 或 `assistant`，`quadrant` 不是 `expert`、`supporter`、`leader`、`dreamer`，`current_stress` 是数字字符串、布尔值、NaN、Infinity 或超出 0 到 10。`/healthz` 可能返回 HTTP 503。更新仓库后要在 `server/` 下运行 `docker compose up -d --build`。权重、考卷、标签与合格带都没有变化。
> - **0.4.0：** 参考服务器改跑 v10h，它的合成标签由 Hamo 请的真人咨询师重新打分；库的行为没有变化。
> - **0.3.1：** 只改文档——危机处理不在本模型的职责范围内，文档不再拿危机处理来衡量这个模型；代码行为、权重与考卷均无变化。

**五分钟上手**：代码见上方英文段。先 `git clone` 本仓库（`server/Modelfile` 与 `eval/` 在仓库里，不在 pip 包里）；要用 v10、v9 或 v7，就改拉对应的 GGUF，并改 `server/Modelfile` 的 FROM。完整链路是 **闸门 → 评分 → 平滑 → 状态桶**；分数是逐句信号，不要凭单句原始分做任何决定。示例注释里的读数是随包 v10h q8 GGUF 的输出（llama.cpp + Metal）；同一输入，v10 q8 GGUF 给出 A 2.0、B 2.0，v9 q8 GGUF 给出 B 0.0，v7 q8 GGUF 给出 B 1.5，后两者的 W 都是 0.5。打出这些读数的，请核对模型是用哪个 GGUF 建的。`ollama create` 报 `Error: 400 Bad Request: invalid model name`（ollama 0.40.13）说明 GGUF 不在 `FROM` 写的路径上；客户端报 `HTTP Error 404: Not Found: model '<name>' not found` 说明 ollama 里没有这个名字的模型。

采样要保持中性：temperature 0、`repeat_penalty 1.0`、`top_k 0`、`top_p 1.0`。工具包的客户端与 `server/Modelfile` 已设好；用别的方式调用模型时，四项都要自己设。在 v10 上测得：`repeat_penalty` 取 1.1（ollama 0.32.9 及以前的默认值，0.32.10 起为 1.0）时，随包 v10 q8 GGUF（llama.cpp + Metal）在旧 B 卷（legacy 答案）上的造分（五类没有边界的单题与成对题的低臂被打到 B ≥ 1.0）从 3/104（2.9%）升到 15/104（14.4%）。

**一键服务器**：`cd server && docker compose up --build`，自动拉镜像和 v10h GGUF、建模型、预热。首次运行要拉约 2.9 GB 镜像和 639 MB 的 GGUF，占约 8.7 GB 磁盘（linux/arm64 实测，x86 未测）。GGUF 每个 `model-cache` 卷下载一次。请用 `main` 或 `v0.4.1`：`v0.4.0` 标签里的 compose 文件会在下载这一步失败。2026-10-31 在一台 Apple 芯片的 Mac 上实测（Colima 里的 Docker，arm64 CPU，ollama 0.40.13）：干净克隆后 `docker compose up` 不需要别的步骤，上方英文段那条示例请求返回的分数、`stress` 与 `energy_state` 与那里印的完全相同，自检卷得 86.7%，在合格带内；虚拟机是 4 核 6 GiB，镜像已提前拉好；虚拟机第一次开机时 `/healthz` 一直超时，直到重启虚拟机里空转的 `systemd-logind`，`colima stop` 再 `start` 之后没有再出现。compose 固定使用 `ollama/ollama:0.40.13` 和 `curlimages/curl:8.23.0`，就是那次运行所用的镜像；要换 ollama，就改 `image:` 并重跑自检卷。2026-11-01 在同一台 Mac 上（虚拟机配置相同，镜像已拉好），从空卷运行 `docker compose up -d --build` 约 64 秒完成（更早的一次 72 秒），那条示例请求返回的分数、`stress` 与 `energy_state` 仍与那里印的完全相同。没有 x86 上的记录。`POST localhost:8080/score` 返回危机判定与五维分，请求里带 `current_stress` 时另返回压力值与状态桶；危机命中的请求不会送到模型；`GET /healthz` 给一条短探测打分：只有回复能在 `SCORE_TIMEOUT` 内解析成分数时，才返回 HTTP 200 和 `ok: true`；否则返回 HTTP 503，带 `ok: false` 和 `error`。它不走 `/score` 的工作线程池，线程池占满也挡不住它，但它仍要在 ollama 的队列里排队，所以模型忙时可能报 503。它自己的超时是 `HEALTHZ_TIMEOUT`，默认 60 秒，`SCORE_TIMEOUT` 更长时取后者。探测耗时超过 `SCORE_TIMEOUT` 时，即使它已把模型加载完也返回 503；模型够快的话，下一次就能通过。想改跑 v10、v9 或 v7，见 `server/docker-compose.yml` 顶部的说明。

运行时要注意：

- **认证。** `POST /score` 没有认证。compose 只把 API 发布在 `127.0.0.1:8080` 上。[Docker 文档](https://docs.docker.com/engine/network/port-publishing/)提醒：在 Docker Engine 28.0.0 之前的版本上，同一网段的主机仍能访问这样发布的端口。`127.0.0.1` 不是认证手段：这台机器上的任何进程都能调用 API。要给其他机器用，先在前面放上你自己的访问控制。运行在这台机器上、Docker 之外的反向代理可以转发到 `127.0.0.1:8080`，compose 文件不用改。只有访问控制在这台机器之外时，才把 `server/docker-compose.yml` 里 `api` 服务的 `ports` 改成 `"8080:8080"`：这样 API 会发布在这台机器的每个网卡上，本机的代理就不再挡在它前面了。
- **失败。** 服务本身没有回落。超时（默认 8 秒；要改就在 `api` 服务的 `environment` 里设 `SCORE_TIMEOUT`）或模型不在时，`POST /score` 返回 HTTP 500，正文是 `Internal Server Error`。回复解析不出来时返回 HTTP 200，`scores` 为 null。闸门命中时 `scores` 同样是 null，但 `crisis.triggered` 为 true：要先读 `crisis`，命中的转入你的危机处理路径。其余两种情况按跳过或回落处理。无效请求得到 HTTP 422，正文是 `{"detail": [{"type": ..., "loc": [...], "msg": ...}]}`，不回显被拒的值。无效请求包括缺少 `message`、请求体不是合法 JSON、history 轮次缺少 `content`、`role` 不是 `user` 或 `assistant`（`role` 可以省略，默认 `user`）、`quadrant` 不是 `expert`、`supporter`、`leader`、`dreamer`（区分大小写），以及下面两条说的情况。服务器解码不了的请求体（比如用 GBK 发送的中文）得到的是 HTTP 400，这时 `detail` 是字符串，不是列表。请求体能解析且 `message` 是字符串时闸门照样读它，所以即使别的字段无效，闸门命中也照常返回 HTTP 200。
- **`current_stress`** 必须是 0 到 10 之间的 JSON 数字；整数可以，0 和 10 都接受。数字字符串、布尔值、NaN、Infinity 或超出范围的值都会得到 HTTP 422。
- **未知字段。** 上下文字段叫 `history`。顶层或 history 轮次里的未知字段会得到 HTTP 422，所以写成 `context` 的请求会被拒绝，不会在没有上下文的情况下评分。
- **聊天标记。** 从 0.4.1 起，`build_prompt` 会从消息和每条 history 的 `role`、`content` 里去掉 `<|im_end|>` 和 `<|im_start|>`，所以消息不能结束自己这一轮；`score_message` 与 `POST /score` 都继承这一点。去掉的只有标记：其余文字仍留在提示词里，照常评分。不经 `build_prompt` 自己拼提示词的代码，必须调用 `strip_turn_markers`（见[集成指南](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/integration.md)）。`build_prompt` 不去掉分词器里其他附加标记，例如 `<|endoftext|>`、`<think>`、`</think>`、`<tool_call>`。在一台 Apple 芯片的 Mac 上（Colima 里的 Docker，arm64 CPU，ollama 0.40.13），把其中 8 个逐个插入 40 条合成消息，插在中间或下一句之前，经 ollama 的 `/api/generate` 打分：40 条里有 37–40 条，五个分数都在不插入时的 ±0.5 内，与插入普通文字 `[x]`（40 条里 37 条和 39 条）差不多。
- **下载中断。** 下载被中断后，下次运行会自动重新开始：GGUF 先下载成 `<file>.part`，curl 成功后才改名，中断只留下 `.part`，下次运行会替换它。如果 `setup` 仍在 `uploading GGUF blob` 之后以 curl 错误 22 退出，说明缓存的 GGUF 与 compose 文件里的摘要对不上。有两种情况：早于 0.4.1 的 compose 文件在最终文件名下留下的不完整文件，或者你为别的版本改过 compose 文件后摘要对不上。`docker compose down` 和重新克隆都清不掉不完整的文件。如果你为别的版本改过这个文件，先核对两处摘要。否则删掉这个文件再启动：`docker compose run --rm --no-deps --entrypoint rm setup -f /models/hamo-score-0.6b-v10h.q8.gguf`，然后 `docker compose up --build`。
- **重启。** 崩溃或机器重启后，`ollama` 和 `api` 会自动重启，`docker compose stop` 之后则保持停止。`setup` 不会跟着重跑，所以机器重启或 `ollama` 崩溃后，模型回来时是未加载的：`api` 的健康检查会重新加载它，第一条请求来得及加载的话也行。健康检查每 60 秒调用一次 `/healthz`，所以空闲时每分钟多一次模型调用。Docker 显示 `healthy`，连续失败三次后显示 `unhealthy`，不会因此重启容器。在一台 Apple 芯片的 Mac 上（Colima 里的 Docker，arm64 CPU，ollama 0.40.13），机器重启指重启虚拟机，没有试过 Linux 主机重启。手动重启容器，用 `docker compose stop` 再 `start`。compose 文件没改时，`docker compose up -d` 不重启任何东西，只重跑 `setup` 并预热模型。改过 compose 文件后要运行 `docker compose up -d`：它会重建改动的服务，`stop` 和 `start` 不会应用改动。更新仓库后要在 `server/` 下运行 `docker compose up -d --build`：compose 只在 api 镜像缺失时才构建，不加 `--build` 就继续用已经构建好的镜像，也就是旧的服务代码；`docker compose down` 之后、在同一台机器上重新克隆之后也是这样。直接 `docker compose restart` 可能让 `setup` 失败、模型未加载；`api` 仍在服务，第一条请求会加载模型（那台 Mac 上约 2 秒），运行一次 `docker compose up -d` 能修复 `setup`。客户端断开时 ollama 会中止加载，所以比 `SCORE_TIMEOUT` 更慢的加载走 `POST /score` 完不成；健康检查的时限更长，可以把它加载完。这是在那台 Mac 上用很短的 `SCORE_TIMEOUT` 模拟的，慢硬件本身没有测过（见 [FAQ](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/faq.md)）。

**部署自检**：工具包自检卷是 195 道合成题（教师标注）加 10 条手写危机闸门用例。在仓库根目录跑 `python eval/run_exam.py`，部署哪个版本就按哪套标签判卷：默认 `--labels v10h`（v10 那套标签的默认名字，这份考卷没有咨询师标签），v10 用 `--labels v10`（同一套标签，按 v10 自己的合格带），v9 用 `--labels v9`，v7 用 `--labels pre_v9`。`run_exam.py` 直接调用 ollama 接口（`--base-url`，默认 `http://127.0.0.1:11434`），不走 `POST /score`，而 Docker 参考服务器没有把这个端口映射到宿主机：要考它，先在 `server/docker-compose.yml` 的 `ollama` 服务下加 `ports: ["127.0.0.1:11435:11434"]`，在 `server/` 下运行 `docker compose up -d`，再回到仓库根目录，带上 `--base-url http://127.0.0.1:11435`。按默认参数，脚本要么报错，要么考到宿主机 ollama 里名为 `hamo-score-0.6b` 的模型。v10h 的合格带：维度级 84–90%、各维 ≥ 75%、**A ≥ 81**、JSON ≥ 99%、闸门 10/10（闸门是关键词表，与模型无关）。参考值（M1 Pro）：随包 q8 GGUF（llama.cpp + Metal，`server/Modelfile` 的模板加中性采样）86.7%，v10h bf16 safetensors（MLX）86.8%。在一台 Apple 芯片的 Mac 上（Colima 里的 Docker，arm64 CPU，ollama 0.40.13），经参考服务器的 ollama 考这份卷：模型已预热（compose 启动后的状态）时得 86.7%，脚本打印 `A82%`，不是 `A83%`；如果第一题就是模型加载后的第一条请求，得 86.4%。两者都在带内。在 llama.cpp + Metal 上，A 的下限高于 v7 权重（这套标签上 A 为 80.5）；经 Docker 里的 ollama，模型已预热时，v7 的 A 是 81.0，正好压线。两种情况脚本都打印 `A81%`，所以还要看维度级和 B（见 [eval/README.md](https://github.com/HamoAI/hamo-score-toolkit/blob/main/eval/README.md)）；拿成 v9 的权重，B 只有 57.4。部署 v10 的沿用 v10 的合格带：其余各条相同，**A ≥ 86%**，参考值 87.3%。在 llama.cpp + Metal 上，v10 的 A 是 91.8，v10h 是 82.6，看 A 这一行也能分出跑的是哪一版。其余标签的合格带、平凡基线、量化与排查办法见 [eval/README.md](https://github.com/HamoAI/hamo-score-toolkit/blob/main/eval/README.md)。

**这份卷检查的是接线，不是模型质量。** 过关说明你的部署与考卷标签的一致程度和参考值相当、`num_predict` 没有设得过小，走的是工具包自己的提示词、采样与解析器，不是你的。它说明不了你跑的是哪个版本（v10 权重也过得了 v10h 的带），也不检查聊天模板和 `stop`：在 ollama 0.40.13 上，60 道题里缺了这两项的 ollama 标签读数相同。这两项用 `ollama show <tag> --template` 和 `--parameters` 核对。对 v10h 的 GGUF，在 ollama 0.32.5、0.40.12、0.40.13 上，`--template` 打印的是 GGUF 自带的模板，不是 `server/Modelfile` 里的（见 [FAQ](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/faq.md)）。在 Docker 服务器上，要在 `server/` 下运行，命令前面加 `docker compose exec ollama`。这份考卷没有咨询师标签：v10h 按 v10 那套标签判卷，所以它与 v10 的分数差说明不了谁对。这套标签与 v10 的训练标签出自同一套教师提示词，对 v10 天然同分布。恒定输出 0.5 在这套标签上就能得 77.9%，所以不要只看总分，还要看 `run_exam.py` 打印的分维成绩与不同读数的种数。

**模块一览**：`hamo_score.prompt`（提示词格式与 `strip_turn_markers`；内置截断作延迟保护：上下文 3 轮 × 200 字、消息 500 字；本页引用的真实终评与旧 B 卷按完整上下文跑，未经这层截断）、`hamo_score.parse`（容错解析）、`hamo_score.client`（两种客户端与 `score_message()` 安全管线；`TransformersClient` 需 `pip install "hamo-score[transformers]"`）、`hamo_score.stress`（参考平滑与状态桶；权重与阈值按 legacy 口径（v7 及更早）的分数定，而 v10 的 A 是另一套口径，v10h 的 A 跟随咨询师复核：让状态桶把关任何事之前，先用你自己的数据核对；不要把 v9 的分数喂给它）、`hamo_score.safety`（`CrisisGate` 中英词表与 AI 披露文案）。

默认的 `CrisisGate` 词表只是起点，不等于覆盖。新旧两份 W 安全卷合计 189 道合成的「想死但求助」题，闸门命中 107 题。请按你的人群与语言扩充词表。

**细节在哪里**：[集成指南](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/integration.md)（正确接线、升级到 v10h 与 v10、关于 v9 的完整更正、固定版本与摘要、禁令清单）；[FAQ](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/faq.md)（采样、危机处理、已知的 B 符号翻转）；[微调指南](https://github.com/HamoAI/hamo-score-toolkit/blob/main/docs/finetune.md)（微调到你自己的人群：数据红线、LoRA 配方、验收闸门，以及十四代经过裁定的模型的记录，其中六代拒收）；[`examples/`](https://github.com/HamoAI/hamo-score-toolkit/tree/main/examples)（快速上手、批量打分、带危机短路的会话监测演示，后两个带 `--mock`，无模型也能跑）；技术档案的 [Evaluation](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#evaluation) 与 [Limitations](https://huggingface.co/HamoAI/hamo-score-0.6b/blob/main/TECHNICAL_RECORD.md#limitations--known-residuals)（v10h 的主要问题、18 项检查里技术档案报告的 16 项、v10 的判定、哪些事是看到结果之后才定的、为什么通过合成考卷既不说明泛化，对 v10h 也不说明检查之外没有下降）。

**对某个评分不服？请告诉我们——这是我们唯一请求的贡献。** [**提一条分歧报告 →**](https://github.com/HamoAI/hamo-score-toolkit/issues/new?template=score_disagreement.md)，给出消息（可自由脱敏，我们不要可识别个人的文字）、模型版本或文件、模型给的分、你认为该给的分。我们收集这些报告，作为人工复核口径与后续版本的输入。

**许可证**：工具包代码 Apache-2.0；模型权重 HAMO-RAIL-S 1.0（自由使用，附四条限制：不得单独据以作临床判定；不得作为对可识别个人作重大决定的唯一或主要依据，也不得用于隐蔽监测他人的心理状态；面向消费者的心理健康类部署须保留独立的上游危机处理并披露 AI 身份；不得重新识别个人）。默认管线按危机处理条款的要求把闸门放在模型上游；扩充默认词表（能拦住多少见上面的实测）是你的责任。
