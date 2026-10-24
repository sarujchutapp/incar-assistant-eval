Status: done

# Unified v1 scorecard report (command + chat + cost + calibration)

## Parent

PRD #1 · roadmap item #4 (`research/roadmap.md`)

**GitLab:** #12

## What to build

Today the command-side report (`report.format_report`: TSR+CI, routing/intent/slot, McNemar) and the chat-side Bradley-Terry ranking are produced separately. Assemble the single per-model **scorecard** the PRD promises: headline TSR + Wilson CI, decomposed command metrics, confirmation calibration, JGA, safety-cost summary, chat faithfulness/relevancy + BT ranking, and McNemar significance vs a baseline — one report object + a readable rendering.

## Acceptance criteria

- [ ] One entry point produces a combined per-model scorecard from a command run + a chat run
- [ ] Renders TSR±CI, decomposed metrics, cost summary, calibration, and chat BT in one view
- [ ] Covered by a test over fixtures

## Blocked by

- Chat dataset ([10-chat-informational-dataset.md](./10-chat-informational-dataset.md) / #11) for the chat half — the command half can start now.

## Comments

### Done — 2026-06-23

New `src/incar_eval/scorecard.py` (`tests/test_scorecard.py`, 3 tests). The two
halves already existed (command `ModelReport` + chat `ChatMetrics`/Bradley-Terry);
the gap was a single view that assembles them.

- `Scorecard` dataclass + `build_scorecards(command_results, baseline, *,
  chat_metrics?, chat_bt?, jga?)` — a **pure assembler** over already-computed run
  outputs (no re-running). Builds the command `ModelReport` + McNemar vs baseline,
  attaches chat metrics / open-tail BT / JGA when supplied (all optional per model).
- `format_scorecards` renders one block per model: TSR±Wilson CI, decomposed
  routing/intent/slot, confirmation calibration (under/over-confirm), mean safety
  cost, JGA, chat faithfulness/relevancy, chat BT±CI, McNemar verdict vs baseline.

**Acceptance:** [x] one entry point combines a command run + a chat run
[x] renders TSR±CI, decomposed, cost, calibration, chat BT in one view
[x] tested over the shipped chat fixtures (`test_scorecard_combines_command_run_with_shipped_chat_run`).

**Notes for next iteration:** the assembler takes computed pieces, not raw
datasets — wiring it to a single CLI/demo command (command run + chat run + render)
is a natural follow-up; pairs with the slice-9 multi-tier demonstration once
real-model wiring (#12) lands.
