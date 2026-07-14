# Exp 2026-07-14 — abstain cases + corpus v3 (hallucination coverage)

First run on **corpus v3**: added a chat clarify/abstain path (unanswerable
cases + an abstain scorer) and tightened ambiguous-command scoring. Same headline
as v2 — **the seed wins, best-on-val overfits** — but this time the optimizer
collapsed the *command* quadrant by regressing output format, the mirror image of
the very first run's chat collapse.

## Setup

| | |
|---|---|
| Env | `incar_unified` |
| Optimizer | Bedrock Claude Sonnet (LiteLLM proxy) |
| Target | `llama3-t0` (llama3 + `temperature 0`) |
| Gate | `metric=mixed aggregation=min` (unchanged) |
| Reflect | stratified per case_type (unchanged) |
| Seed | v2 seed + a worked answerable/unanswerable (abstain) example |
| Corpus | **v3** — chat 103→118 (+15 unanswerable: 10 distractor-context, 5 no-context); split train 132 / val 44 / test 44 (24 chat + 20 command), seeded shuffle, `chat/unanswerable` its own stratum |
| Scoring | ambiguous commands now require `mode=clarify` **and** correct intent; chat `answerable=False` → success = abstain |
| Steps | 7, epoch 1 · seed 42 |
| Run dir | `outputs/skillopt_incar_unified_bedrock-sonnet_20260714_154816` |

## Test scores (valid_unseen, 44 items)

| skill | chat (24) | command (20) | overall (44) |
|---|---|---|---|
| **baseline S₀** | 0.625 | **0.550** | **0.591** |
| best-on-val (step 7) | 0.792 | **0.300** | 0.568 |
| final | 0.792 | 0.300 | 0.568 |

- best-on-val `val` score 0.5500 (step 7) · accept=2 reject=5 · epoch best 0.5208
- wall 3565s · tokens 1,641,768 (prompt 1,474,525 / completion 167,243 / 672 calls) · cost input-heavy, confirm via CloudWatch (~$3–4 est.)

## Findings

1. **Command collapsed via a format/routing regression, not lost capability.**
   7 command cases flipped pass→fail; ≥4 are the *reintroduced* `answered_not_acted`
   bug the seed fix had cured — the optimizer's rewrite made the model wrap JSON in
   fences/backticks and, tellingly, prefix replies with `**Question**` / `**QUESTION**`
   and answer commands in prose. Pulled toward the new chat/abstain emphasis, it
   damaged command routing. The other 3 flips are genuine content errors (executed
   on ambiguous, dropped a `body` slot, "some jazz" vs "jazz").
2. **The min-gate can't stop a val→test drop.** It gates on the worst *val*
   quadrant; command held on val but cratered on test. Same overfit signal as v2,
   louder. best-on-val = −0.0227 vs seed; final = same.
3. **Baseline chat 0.625 (vs v2's 0.95) is the benchmark working, not a regression.**
   The 15 abstain cases now count and the baseline model hallucinates on some
   unanswerable questions — exactly the failure the new cases were built to catch.
4. **Abstain cases too few in test (3) to measure.** baseline 2/3 → best 1/3,
   flipped both directions = noise. Mechanically correct; needs more cases to read.

## Honest conclusion

Third confirmation of the v2 verdict: on this setup (good seed + weak `llama3`
target + ~44-item val) **SkillOpt overfits val and hurts test every time** — v1 it
sacrificed chat, here it sacrificed command. **Deploy the seed (0.591).** The
benchmark got better (hallucination coverage, stricter ambiguous scoring); the
optimizer still added nothing. The one lever that could flip the verdict remains a
**stronger target** with real command-format headroom.

## Not comparable to v1/v2

Corpus v3 (test 44, chat 24 incl. 15 abstain corpus-wide) — chat baselines reset
downward because abstain cases now count. Command track (20) is unchanged from v2.
