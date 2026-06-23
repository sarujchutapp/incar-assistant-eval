Status: done

# Chat/informational dataset (objective-by-construction + open tail)

## Parent

PRD #1 · roadmap item #2 (`reserch/roadmap.md`)

**GitLab:** #11

## What to build

The chat scorer (slice 6, `chat.py`) and the guarded pairwise judge (slice 7, `judge.py`) exist, but there are **no chat cases authored yet**. Build the dataset so the chat quadrant actually runs:

- An **objective-by-construction** set: verifiable-answer questions (ETA, fuel, factual lookup) each with a provided `fact`, scored by faithfulness + relevancy.
- A small **open-tail** set for the pairwise Bradley-Terry judge.

Use the same subagent synth → cross-family verify loop as the command dataset; sized smaller (judge cost), tied to the §9 validation sample.

## Acceptance criteria

- [ ] A `fixtures/chat_cases.json` (verifiable-answer) loads and runs through `run_chat_benchmark`
- [ ] A small open-tail set runs through the pairwise judge → Bradley-Terry ranking
- [ ] Cases authored via cross-family proposal + human spot-check of disagreements (no pure templating)

## Blocked by

None — can start immediately.

## Comments

### Done — 2026-06-22

Built the load path + authored the dataset (the scorer/judge already existed; the
gap was data + a way to load it).

**Code (`src/incar_eval/loader.py`, `tests/test_loader.py`):**
- `load_chat_cases` / `load_chat_clients` / `run_chat_from_files` — mirror the
  command loader; run the verifiable set through `run_chat_benchmark`.
- `run_open_tail` — loads questions + per-model answers + recorded judge verdicts,
  replays the judge via `FakeModelClient` keyed by the exact judge prompt, and runs
  the **real** `compare_pair` (position-swap + cross-family guard) → `bradley_terry_with_ci`.
  No new judge class needed — reused `FakeModelClient`.

**Fixtures (cross-family synth, no templating):** authored by a Sonnet
"synthesizer" (≠ targets), judged by a Haiku judge (≠ targets, ≠ synthesizer),
then spot-checked by hand against the actual faithfulness rule.
- `fixtures/chat_cases.json` (12 verifiable) + `fixtures/chat_responses.json`
  (strong/mid/weak): faithfulness 1.00 / 0.67 / 0.42.
- `fixtures/chat_open_tail.json` (6 advisory questions × 3 tiers + verdicts):
  Bradley-Terry strong > mid > weak.

**Acceptance:** [x] chat_cases loads + runs through run_chat_benchmark
[x] open-tail runs through pairwise judge → BT [x] cross-family proposal + spot-check.

**Notes for next iteration:** open-tail BT spread is lopsided (strong undefeated
12/12) — a larger/closer set would exercise ties + position-bias paths more. These
fixtures are the chat half the unified scorecard (#11) needs.
