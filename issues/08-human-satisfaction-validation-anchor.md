Status: ready-for-agent

# Slice 8 — Human-satisfaction validation anchor

## Parent

PRD #1

**Type:** HITL  ·  **GitLab:** #9  ·  **PRD user stories covered:** 49, 50, 51, 52

## What to build

Build the validation anchor that defends against the Type C over-fitting weakness. Collect ~50–100 human ratings on a sample — absolute ratings for command/control (matching the objective scores) and pairwise for chat (matching the judge). Compute per-dimension correlation (correctness↔correctness, conciseness↔conciseness) and judge↔human agreement, with correctness treated as the dominating hard gate. Never use a single blended scalar.

## Acceptance criteria

- [ ] A ~50–100 case human-rating sample is collected: absolute for command, pairwise for chat
- [ ] Per-dimension correlation between automated and human scores is computed and reported
- [ ] Judge↔human agreement is computed for the chat dimension
- [ ] Correctness is enforced as a hard gate in the analysis (a wrong action cannot pass on style)
- [ ] The report states whether automated tracks human well enough to run at scale without humans

## Blocked by

- [05-statistics-paired-comparison.md](./05-statistics-paired-comparison.md)
- [07-chat-llm-judge-open-tail.md](./07-chat-llm-judge-open-tail.md)

## Comments

### Status — 2026-06-22

Still the one irreducibly-human task — **NOT** automated by design (an LLM rating an LLM would reintroduce the Type-C "no independent verification" weakness; see `reserch/hitl_handling_decision.md`). Dependencies are ready: the command scorer is absolute and the chat judge is pairwise, so the human-anchor format can match (§9). Scope: one-time ~50–100 case sample, per-dimension correlation + judge↔human agreement. Best done once the command dataset (09 / GitLab #10) and chat set (10 / GitLab #11) are at size.
