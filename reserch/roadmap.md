# Roadmap to v1

Where the benchmark stands and what's left to ship a credible v1. The engineering is essentially done; most of what remains is **content** (the dataset) plus assembly and one irreducibly-human pass.

_Last updated: 2026-06-22._

## Done (banked)

- All 7 AFK engineering slices (GitLab #2–#8, closed): scorer, full ontology + routing/abstention, safety cost model + calibration, context/`car_state`/JGA/blocked-while-moving, statistics (Wilson + McNemar + report), chat objective-by-construction, guarded pairwise LLM-judge + Bradley-Terry + role adherence.
- Cross-family **auto-verification** pipeline (`verify.py`) — agreement auto-accepts, the rest is flagged.
- **JSON loader + CLI + runbook** (`incar_eval.cli`, `docs/runbook.md`) — author cases/responses as JSON, run from the command line, no API.
- **Standards adoptions** (see `standards_alignment.md`): SGD/MultiWOZ slot matching, acceptable-value lists, categorical `possible_values` + validation, normalized JGA, value canonicalization; plus range-relative intensity and the schema clarifications in `schema_clarifications.md`.
- **52-case verified command/control dataset**; flagged queue empty.

## Remaining for v1

| # | Work | Why | How | Tracking |
| --- | --- | --- | --- | --- |
| 1 | Scale command/control cases 52 → ~400 | §5.1: ±5% CI on headline TSR; resolve model tiers | subagent synth→verify loop + light human spot-check | #10 |
| 2 | Author the chat/informational dataset | chat scorer + judge exist but there are **no chat cases** | same loop for verifiable-answer cases; small open-tail set for the judge | #11 |
| 3 | Wire real target models | targets are subagents/fixtures; a real run needs candidate models | subagents now (no API) or a live `ModelClient` when API is available | #13 |
| 4 | Assemble the unified scorecard | command report + chat BT exist separately; deliverable is one combined report | AFK | #12 |
| 5 | Human-satisfaction anchor (slice 8) | the Type-C trust defense (§9); cannot be automated | one-time ~50–100 human ratings + correlation report | #9 |
| 6 | Demonstration run across model tiers | §1/§10: show the benchmark discriminates | AFK once 1–4 exist | #10 |
| 7 | CI wiring (`.gitlab-ci.yml`: pytest + mypy) | reproducibility / final-stage polish | AFK | #14 |

**Minimum to credibly ship v1:** 1 → 4 → 5 → 6 (dataset at power → unified report → one human anchor pass → tiered demo). #2 is needed for the chat quadrant to actually run; #3/#7 are realism + polish.

## Needs a human (not automatable)

- **#5** — the one-time human ratings (a couple of people, an afternoon).
- **#3 live models** — only if/when API access is available; otherwise subagents stand in.
- Occasional product calls when a flagged case exposes a convention gap (as the Netflix/intensity/genre ones did).

## Intentionally out of v1 (parked, per spec §12)

Latency & cost; non-English locale & cultural style; NLU robustness-to-noise track. Decided out, each with a documented trigger to revisit — not pending work.

## Optional deepenings (not blocking)

Standards `standards_alignment.md` gaps #4 (SLURP SLU-F1 partial-credit value scoring), #5 (`requested_slots` for clarify), #6 (span grounding).
