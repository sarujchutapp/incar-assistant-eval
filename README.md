# In-Car Voice Assistant — LLM Evaluation Benchmark

A benchmark for answering a practical question: **what is the cheapest LLM that is still good
enough to run an in-car voice assistant?** It scores what the model actually *does* — the
structured tool call it emits — not what it claims to have done, weighs errors by how
dangerous they are to the driver, and reports every number with a confidence interval so
real differences can be told apart from noise.

> Built during my Data Scientist internship at **Toyota Tsusho Mobility Informatics Pte. Ltd.**
> (Jun–Jul 2026). I designed the benchmark from a survey of current evaluation practice and
> implemented it end to end.

## What it measures

Test cases fall into a 2×2 grid:

| | Single turn | Context-based (car state, earlier turns) |
|---|---|---|
| **Commands** — "turn up the AC" | Task success, routing (false activation / false rejection), intent accuracy, slot F1 | Joint goal accuracy across the dialogue, per-turn accuracy, blocked-while-moving handling |
| **Chat** — weather, ETA, small talk | Faithfulness to a provided fact, answer relevancy | Open-ended answers ranked by a guarded LLM judge |

## Design highlights

- **Judge actions, not claims.** Models answer by emitting a tool call such as
  `set_climate(temp, zone)` against a fixed ontology, scored against gold; a small simulated
  `car_state` covers commands that depend on the situation.
- **Safety-weighted errors.** Each case has stakes and ambiguity; the expected behaviour
  (execute, confirm first, or ask a clarifying question) follows from them, and mistakes are
  ranked by severity — from an unnecessary confirmation (mildest) up to silently doing the
  wrong irreversible thing (worst).
- **Statistics that respect small samples.** Wilson intervals on every proportion, McNemar
  for paired model comparisons, Bradley–Terry with bootstrap intervals for the open-ended tail.
- **A guarded LLM judge** for open-ended chat: critique before verdict, length normalization,
  position swapping, and a judge from a different model family than the one being judged.
- **Cheaper gold labels.** Several models from different families label each new case;
  agreement from at least two families auto-accepts, and only disagreements and
  safety-critical cases go to a human. The human-satisfaction check is deliberately *not*
  automated — an LLM grading an LLM is the weakness it exists to guard against.
- **Tested and typed.** 147 offline tests (pytest); `src/` passes strict mypy.

The full design — and why each metric was chosen or dropped — is in
[`research/benchmark_spec.md`](research/benchmark_spec.md), with a plain-language version in
[`research/benchmark_spec_summary.md`](research/benchmark_spec_summary.md).

## Demo

`python -m incar_eval.demo` runs the benchmark on recorded responses from a strong and a weak
model (excerpt):

```
== strong (n=7) ==
  TSR:               100.0%  [64.6%, 100.0%]
  slot_f1:           1.00
  mean safety cost:  0.29
== weak (n=7) ==
  TSR:               42.9%  [15.8%, 75.0%]
  capability_hallucination_rate  100.0%  [20.7%, 100.0%]
  slot_f1:           0.62
  mean safety cost:  10.57
  vs strong: McNemar p=0.1336 (not significant)

Bradley-Terry (chat open tail):
  strong 0.81  [0.56, 1.00]
  weak   0.19  [0.00, 0.50]
```

Seven cases are enough to see the weak model's safety cost jump, and the McNemar test is
honest that they are not yet enough to call the difference significant.

## Getting started

Python 3.12+.

```
python -m pip install -e ".[dev]"
```

| Command | What it does |
| --- | --- |
| `python -m pytest` | Run the test suite |
| `python -m mypy` | Type-check `src/` and `tests/` (strict) |
| `python -m incar_eval.demo` | Run the recorded-fixtures demo shown above |
| `python -m incar_eval.cli --cases C --responses R` | Run the benchmark on your own JSON cases and responses (see [docs/runbook.md](docs/runbook.md)) |

Live model runs use the optional `live` extra (`pip install -e ".[live]"`); the tests never
need it.

## Repository layout

| Path | What it is |
|---|---|
| `src/incar_eval/` | The benchmark: schema and loader, scorer and metrics, safety model, statistics, LLM judge, auto-verification, corpus synthesis, scorecard |
| `fixtures/`, `examples/` | Test cases and recorded model responses |
| `tests/` | Offline test suite |
| `integrations/skillopt/` | Adapter for running Microsoft's SkillOpt prompt optimizer against this benchmark — analysis in [skillopt](https://github.com/sarujchutapp/skillopt) |
| `research/` | Benchmark spec, evaluation-landscape survey, corpus design, standards alignment, roadmap |
| `docs/runbook.md` | How to author cases and run the benchmark |
| `issues/` | The implementation plan as vertical slices (`done/` for completed) |

## Status

The benchmark, its statistics, the chat track, the LLM judge, auto-verification, and a live
model client are complete. Two tasks remain open because they need people, not code: the
human-satisfaction validation anchor and authoring the case corpus at scale
([`issues/`](issues/)).
