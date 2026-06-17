Status: ready-for-agent

# Slice 2 — Full v1 ontology + routing/abstention

## Parent

PRD #1

**Type:** AFK  ·  **GitLab:** #3  ·  **PRD user stories covered:** 2, 3, 4, 10, 20, 21, 22

## What to build

Expand the schema to the full frozen v1 ontology (spec §6.1): six command intents (`set_climate`, `navigate`, `call_contact`, `play_media`, `adjust_volume`, `send_message`) with their slots and the single `stakes` tag, plus the two abstention labels `none` and `out_of_scope`. The scorer learns act-vs-abstain routing, reports false-activation and false-rejection separately, distinguishes `none` (chit-chat) from `out_of_scope` (capability hallucination), and computes slot-level F1 alongside all-slots-exact-match.

## Acceptance criteria

- [ ] All six intents and both abstention labels load from the schema and validate
- [ ] Routing accuracy is reported with false-activation and false-rejection broken out
- [ ] Acting on a `none` case scores as false activation; acting on `out_of_scope` scores as a distinct capability-hallucination outcome
- [ ] Slot scoring reports both F1 and all-slots-exact-match
- [ ] Tests cover routing, the none/out_of_scope distinction, and slot F1

## Blocked by

- [01-tracer-one-intent-e2e-tsr.md](./01-tracer-one-intent-e2e-tsr.md)
