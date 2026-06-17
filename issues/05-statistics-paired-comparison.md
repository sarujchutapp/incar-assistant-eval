Status: ready-for-agent

# Slice 5 — Statistics & paired multi-model comparison

## Parent

PRD #1

**Type:** AFK  ·  **GitLab:** #6  ·  **PRD user stories covered:** 12, 13, 42, 43, 45, 46, 47, 55

## What to build

Add the statistics layer and paired multi-model comparison. Wilson score intervals on every reported proportion. Run the identical case set across multiple models (paired) and compare with McNemar's test on the objective quadrant. No Elo and no ranking model on the objective quadrant. Produce a per-model report card: headline TSR with CI, decomposed routing/intent/slot/calibration metrics, cost summary, and significance vs. a chosen baseline.

## Acceptance criteria

- [ ] Every proportion is reported with a Wilson score interval, valid near 1.0
- [ ] Multiple models run the identical case set and are compared pairwise via McNemar
- [ ] No Elo / no ranking-model code path exists for the objective quadrant
- [ ] The report card renders TSR±CI, decomposed metrics, cost summary, and McNemar significance vs a baseline
- [ ] Tests check Wilson against known values (incl. the near-1.0 edge) and McNemar against a known contingency table

## Blocked by

- [02-full-ontology-routing-abstention.md](./02-full-ontology-routing-abstention.md)
