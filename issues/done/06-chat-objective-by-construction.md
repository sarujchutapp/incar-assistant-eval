Status: ready-for-agent

# Slice 6 — Chat quadrant: objective-by-construction

## Parent

PRD #1

**Type:** AFK  ·  **GitLab:** #7  ·  **PRD user stories covered:** 36, 39 (partial)

## What to build

Add the chat/informational quadrant for verifiable-answer cases only. Restrict to cases with a checkable fact (ETA, fuel-low, factual lookup) and score by faithfulness/exact-match against a provided fact, plus answer relevancy. Sized smaller than the command quadrant. Reuses the runner and model-client port.

## Acceptance criteria

- [ ] Informational cases carry a provided fact and are scored by faithfulness/exact-match against it
- [ ] Answer relevancy is reported
- [ ] These cases flow through the same runner and model-client port as command cases
- [ ] Tests cover a faithful answer (pass) and an unfaithful/off-topic answer (fail)

## Blocked by

- [01-tracer-one-intent-e2e-tsr.md](./01-tracer-one-intent-e2e-tsr.md)
