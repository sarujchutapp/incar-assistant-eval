# Exp 2026-07-13 (pm) — seed format fix + corpus v2 + temp-0 target

The landmark run. Two changes on top of the min-gate setup: (1) fixed the seed's
zero-shot command output, (2) grew the eval and made the target deterministic.
Result: the **seed fix** delivered a huge baseline jump, and **SkillOpt added
nothing on top** (slight val-overfit).

## Setup

| | |
|---|---|
| Env | `incar_unified` |
| Optimizer | Bedrock Claude Sonnet (LiteLLM proxy) |
| Target | **llama3-t0** (llama3 + `temperature 0`, greedy/reproducible) |
| Gate | `metric=mixed aggregation=min` (unchanged from prev run) |
| Reflect | stratified per case_type (unchanged) |
| Seed | **format-fixed** (3207 chars): silent routing + "entire reply is the JSON, no prose/fences" + a correct/wrong example |
| Corpus | **v2** — chat 44→103; split train 123 / val 41 / test 41 (21 chat + 20 command), seeded shuffle |
| Steps | 7, epoch 1 · seed 42 |
| Run dir | `outputs/skillopt_incar_unified_bedrock-sonnet_20260713_170929` |

## Changes vs previous run

1. **Seed command-output fix** — diagnosis was `answered_not_acted`: llama3 emitted *correct* JSON wrapped in prose/backticks, which the parser rejected. Fix = make routing silent and demand the whole reply be the raw JSON object.
2. **temp-0 target** (`llama3-t0`) — greedy decoding → reproducible + more consistent format.
3. **Corpus v2** — chat 44→103 so test-chat is 21 (was 9); resolution ~4.9%/item.

## Test scores (valid_unseen, 41 items)

| skill | chat (21) | command (20) | overall (41) |
|---|---|---|---|
| **baseline S₀** | 0.952 | **0.550** | **0.756** |
| best-on-val (step 7) | 0.810 | 0.600 | 0.707 |
| final | 1.000 | 0.500 | 0.756 |

- best-on-val `val` score: 0.6028 · accept=2 reject=5
- wall 3046s · tokens 1,127,918 (661 calls) · ≈ $2.5–3

## Findings

1. **The seed format fix was the biggest lever in the whole project.** Baseline command **0.00 → 0.55**, overall to **0.756**. Confirms the `answered_not_acted` diagnosis: the model knew the answers; only the output format was wrong.
2. **SkillOpt did not improve on the good seed.** best-on-val = **−0.0488** vs baseline (it traded test-chat 0.95→0.81 for val gains that didn't generalize → val-overfit); final = **±0.0000**. The artifact to deploy is the **seed itself**.
3. **The min-gate worked but had no headroom.** `accept=2 reject=5` — correctly conservative, no quadrant collapsed; there was simply nothing to gain once the seed was good + llama3's command ceiling (~0.5–0.6) + a still-small 41-item val.

## Honest conclusion

On this configuration, **prompt engineering + a trustworthy benchmark delivered the value; text-space optimization added nothing on top.** Not a claim that SkillOpt never helps — the paper's own limitations predict this (needs headroom + reliable signal + ideally a capable target). The one lever that could change the verdict is a **stronger target model** (raises the ceiling, creates headroom); optimizing for llama3 is optimizing against a wall.

## Not comparable to v1

Prior experiments used corpus v1 (test-chat = 9). This is corpus v2 (test-chat = 21); baselines reset. The command 0→0.55 jump is too large to be test-set luck — the mechanism (format fix) is understood.
