# In-Car Voice Assistant — Internal Evaluation Benchmark

Internal (Type C) evaluation benchmark for an in-car voice assistant. Full design
is in [`reserch/benchmark_spec.md`](reserch/benchmark_spec.md); the PRD and
implementation issues live on GitLab (issue #1 and the [`issues/`](issues/) folder).

## Setup

```
python -m pip install -e ".[dev]"
```

## Dev commands

| Command | What it does |
| --- | --- |
| `python -m pytest` | Run the test suite |
| `python -m mypy` | Type-check `src/` and `tests/` (strict) |
| `python -m incar_eval.demo` | Run the recorded-fixtures demo and print a TSR |

## Status

Slices 1–4 are in place:

1. Tracer bullet — one intent walked end-to-end (schema → adapter → model-client
   port → scorer → runner) to a Task Success Rate from recorded fixtures.
2. Full v1 ontology (six intents + `none`/`out_of_scope`) with routing accuracy
   (false-activation / false-rejection) and slot-F1.
3. Safety model — `expected_mode(stakes, ambiguity)`, the §11 cost cells with
   ordering invariants, and confirmation calibration.
4. Context-based cases — `car_state`/`vehicle_motion`, multi-turn Joint Goal
   Accuracy + per-turn, and blocked-while-moving (warn+alternative) scoring.
5. Statistics & paired comparison — Wilson intervals on every proportion,
   McNemar on the paired objective quadrant (no Elo), and a report card.
6. Chat quadrant (objective-by-construction) — verifiable-answer cases scored by
   faithfulness vs a provided fact, with answer relevancy reported.
7. LLM-as-judge for the open chat tail — guarded pairwise judging (CoT critique,
   length normalization, position swap, cross-family), Bradley-Terry with
   bootstrap CIs, and rule-based Role Adherence to the fixed persona.

Slices 8–9 (human-satisfaction validation anchor; case authoring at scale +
recorded-fixtures demo run) are HITL and tracked on GitLab.
