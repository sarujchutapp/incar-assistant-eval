Status: ready-for-agent

# Unified v1 scorecard report (command + chat + cost + calibration)

## Parent

PRD #1 · roadmap item #4 (`reserch/roadmap.md`)

**GitLab:** #12

## What to build

Today the command-side report (`report.format_report`: TSR+CI, routing/intent/slot, McNemar) and the chat-side Bradley-Terry ranking are produced separately. Assemble the single per-model **scorecard** the PRD promises: headline TSR + Wilson CI, decomposed command metrics, confirmation calibration, JGA, safety-cost summary, chat faithfulness/relevancy + BT ranking, and McNemar significance vs a baseline — one report object + a readable rendering.

## Acceptance criteria

- [ ] One entry point produces a combined per-model scorecard from a command run + a chat run
- [ ] Renders TSR±CI, decomposed metrics, cost summary, calibration, and chat BT in one view
- [ ] Covered by a test over fixtures

## Blocked by

- Chat dataset ([10-chat-informational-dataset.md](./10-chat-informational-dataset.md) / #11) for the chat half — the command half can start now.
