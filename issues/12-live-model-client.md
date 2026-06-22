Status: ready-for-agent

# Live ModelClient for real target models (API-backed run)

## Parent

PRD #1 · roadmap item #3 (`reserch/roadmap.md`)

**GitLab:** #13

## What to build

A real implementation of the `ModelClient` port that calls an actual LLM API, so the benchmark can run against real candidate models (not just `FakeModelClient` / subagent-recorded fixtures). Record responses to fixtures for reproducibility.

## Acceptance criteria

- [ ] A live `ModelClient` calls a real API and returns the raw tool-call text
- [ ] Responses can be recorded to a `responses.json` fixture for deterministic replay
- [ ] Selectable across model tiers for the discrimination demo

## Notes

**Blocked on API access** (none available yet). Until then, in-session subagents stand in as targets and produce recorded fixtures. The code can be written against a stub + env-var key now.

## Blocked by

None to write; blocked on API credentials to run.
