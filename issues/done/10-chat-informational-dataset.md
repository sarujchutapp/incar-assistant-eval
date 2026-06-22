Status: ready-for-agent

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
