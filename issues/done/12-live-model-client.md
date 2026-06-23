Status: done

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

## Comments

### Done (code) — 2026-06-23

`src/incar_eval/live_client.py` (`tests/test_live_client.py`, 4 tests):

- `LiveModelClient(model, *, system?, max_tokens=1024, api_key?, _client?)` —
  implements the `ModelClient` port; calls Anthropic `messages.create` and returns
  the concatenated raw text of the response's text blocks. `_client` is injectable
  so tests use a stub (no SDK, no network); in production it's built lazily from
  the SDK, resolving the key from `api_key` / `ANTHROPIC_API_KEY`.
- `MODEL_TIERS` (`opus`→`claude-opus-4-8`, `sonnet`→`claude-sonnet-4-6`,
  `haiku`→`claude-haiku-4-5`) + `live_client_for_tier(tier)` — selectable across
  tiers for the discrimination demo.
- `record_responses(client, {key: prompt})` → `{key: raw_response}` — freezes a
  live run into a mapping that replays deterministically via `FakeModelClient`
  (round-trip covered by a test).

**Dependency:** `anthropic` is an optional extra (`pip install -e ".[live]"`),
imported lazily — the core package and the offline test suite never need it, and
CI stays network-free. mypy override ignores the missing import.

**Acceptance:** [x] live client returns raw tool-call text [x] responses
recordable for deterministic replay [x] selectable across tiers — all verified
against a stub (124 passed, mypy clean).

**Still blocked on credentials to actually run:** the one remaining item is an
end-to-end live call + recording a real `responses.json`, which needs an API key
(none available — see [[incar-benchmark-impl-state]]). The code path is ready;
`pip install -e ".[live]"`, set `ANTHROPIC_API_KEY`, and run. This is also the
last input the slice-9 multi-tier demonstration run is waiting on.
