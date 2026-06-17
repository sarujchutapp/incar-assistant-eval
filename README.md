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

Slice 1 (tracer bullet) is in place: a single intent (`set_climate`) walked
end-to-end through schema → adapter → model-client port → scorer → runner,
producing a Task Success Rate from recorded fixtures with no network calls.
