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
3. **Baseline chat fell 0.95→0.625 because the abstain rule backfired, NOT
   because the benchmark caught hallucination.** Per-case: baseline chat = 13/21
   answerable + 2/3 unanswerable. Command baseline is *identical* to v2 (11/20),
   so the whole overall drop is this chat quadrant. Of the 8 answerable failures,
   **6 are over-abstention** — llama3 over-generalized the new seed rule ("if
   Context lacks the fact, say you don't have it") and refused questions whose
   fact was sitting in context ("I don't have that information" for pharmacy=9 PM,
   toll=$12.30, battery=40 min, …). The other 2 are scorer paraphrase
   false-negatives ("level 2"→"2", "currently on"→"on", §7). The 3 abstain cases
   themselves passed 2/3 and are irrelevant to the drop. This is the same
   compliance ceiling (§9): a weak target applies an instruction too bluntly —
   here trading hallucination for over-refusal.
4. **The optimizer delta is actually SMALLER than v2, not larger.** best-on-val
   −0.0227 here vs −0.0488 in v2. The run looks "worse" only because the *baseline*
   dropped (finding 3); the optimizer did slightly less damage.
5. **Abstain cases too few in test (3) to measure.** baseline 2/3 → best 1/3,
   flipped both directions = noise. Mechanically correct; needs more cases to read.

## Isolation: v2 seed as control (what actually caused the drop)

To attribute the 0.756→0.591 fall, we re-ran the **v2 seed** (run #3's, no abstain
rule) on the v3 test split via the local target (no Bedrock), and re-scored the
command track under both the old and new `is_success` rule. The two benchmark
changes are independent — scoring touches only command, corpus only chat — so
attribution is clean:

| factor (v2 seed held fixed) | measured effect |
|---|---|
| **hard-scoring change** (ambiguous → clarify **+** correct intent) | **0** — command 12/20 under *both* rules, **0 cases flipped** (no model ever clarified with a wrong intent) |
| **corpus change** (+3 abstain cases in test) | **−3 items** (v2 seed scores 0/3 raw, ≈ −0.03 overall) |
| **seed change** (v2 → v4 seed, same corpus) | **−0.136** (0.727 → 0.591): the abstain rule refused 7 answerable questions |

**v2 seed on v3 test = 0.727** (chat answerable **20/21**, abstain 0/3, command
12/20) vs the v4 seed's 0.591. So **~80% of the drop was the seed I added**, not
the benchmark changes. The scoring change is a correct-but-inert loophole close;
the corpus change costs only −0.03.

**Bonus defect found:** 2 of the v2 seed's 3 abstain "failures" were actually
abstentions the detector missed — *"the weather is unknown"*, *"the traffic is
unclear"*. `_abstains` didn't list `unknown`/`unclear`. Widened it (only the
fabricated *"68 mph"* still fails), so the v2 seed's true abstain is **2/3** and
its corrected overall is **~0.773**.

## Honest conclusion

The run only *looked* worse; the diagnosis is the opposite of alarming. **The
initial seed was the whole story** — a one-sided abstain rule made the weak target
over-refuse (−0.136), while the two benchmark changes were near-free (scoring
inert, corpus −0.03). Reverted the seed to v2 (the confirmed-best artifact,
0.727 / ~0.773 with the detector fix) and kept both benchmark changes. And, third
time confirmed: on this setup (good seed + weak target + small val) **SkillOpt
overfits val and hurts test** — v1 it sacrificed chat, here command. The one lever
that could flip the verdict remains a **stronger target**.

## Not comparable to v1/v2

Corpus v3 (test 44, chat 24 incl. 15 abstain corpus-wide). Command track (20) is
unchanged from v2 (baseline 11/20). Chat baselines look lower, but the isolation
above shows that's almost entirely the (now-reverted) seed abstain rule, not the
corpus.
