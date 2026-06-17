Status: ready-for-agent

# Slice 1 — Tracer bullet: one-intent end-to-end TSR

## Parent

PRD #1

**Type:** AFK  ·  **GitLab:** #2  ·  **PRD user stories covered:** 1, 5, 11, 14, 15, 17, 22, 23

## What to build

The thinnest possible end-to-end path through the benchmark, exercising every seam for a single intent (`set_climate`). A minimal SGD-style schema entry, a gold-record loader, a target adapter that builds the car-assistant prompt and calls the model through an injected model-client port, a deterministic scorer comparing the emitted tool-call to the gold (intent + slot exact match), and a runner that executes a tiny fixture dataset and reports a Task Success Rate. The model-client port has a fake/recorded implementation for tests and demos; a live implementation is allowed but not exercised in CI.

## Acceptance criteria

- [ ] Running the runner over a small fixture dataset prints a TSR for one model with no network calls
- [ ] The scorer is a pure function `(gold_record, emitted_call) -> per-case outcome` with no I/O
- [ ] The model-client port is injectable; the fake implementation returns canned tool-calls
- [ ] A correct emission scores pass; an incorrect slot scores fail
- [ ] pytest covers the scorer and an end-to-end runner test using the fake client

## Blocked by

None - can start immediately
