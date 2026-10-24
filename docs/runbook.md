# Runbook — running the benchmark by hand (no live API)

This is the by-hand path: author cases and record model responses as JSON, then
run the benchmark and report from the command line. No API access required.

## 1. Author gold cases — `cases.json`

A list of cases. `expected_slots`, `ambiguity` (`clear` | `defaultable` |
`ambiguous`, default `clear`), and `car_state` are optional. See
`examples/cases.example.json`.

```json
[
  {"utterance": "bump the temp up to 23", "expected_intent": "set_climate", "expected_slots": {"temp": 23, "zone": "all"}},
  {"utterance": "play the movie", "expected_intent": "play_media", "expected_slots": {"title": "Dune", "media_type": "video"}, "car_state": {"vehicle_motion": "moving"}}
]
```

Cases are validated against the frozen schema on load — an unknown intent, an
unknown slot, or a bad ambiguity label raises immediately.

**Tip — let cross-family auto-verification draft the gold:** instead of writing
every `expected_intent`/`expected_slots` by hand, collect tool-call proposals from
≥2 different-family models, run them through `incar_eval.verify.verify_batch`, and
only hand-check the flagged remainder (disagreements + safety/ambiguous/out_of_scope
cells). See `research/hitl_handling_decision.md`.

## 2. Record model responses — `responses.json`

One block per model, mapping each utterance to the tool call that model emitted.
`mode` (`execute` | `confirm` | `clarify` | `warn_alternative`) and `eyes_free`
are optional. See `examples/responses.example.json`.

```json
{
  "model-a": {
    "bump the temp up to 23": {"intent": "set_climate", "slots": {"temp": 23, "zone": "all"}, "mode": "execute"},
    "play the movie": {"intent": "play_media", "slots": {}, "mode": "warn_alternative"}
  }
}
```

When you have API access, generate these by calling each model; until then, paste
in answers by hand. Either way they become reproducible fixtures.

## 3. Run it

```
python -m incar_eval.cli --cases cases.json --responses responses.json --baseline model-a
```

Prints a per-model scorecard: TSR with a Wilson interval, the decomposed routing /
intent / slot metrics, the mean safety cost, and a McNemar significance verdict
for each other model vs the baseline.

Try it on the bundled examples:

```
python -m incar_eval.cli --cases examples/cases.example.json --responses examples/responses.example.json --baseline strong
```

## What still needs a human

- The **safety / ambiguous / out_of_scope** cells (hand-authored; auto-verification
  always flags these).
- The **slice-8 human-satisfaction anchor** — a one-time ~50–100 case pass. This
  stays human on purpose; see `research/hitl_handling_decision.md`.
