# SkillOpt core patches

SkillOpt is a vendored clone (Microsoft's repo), so changes to its *core* can't
live in this tree. Each `.diff` here is a `git diff` taken in the clone; apply it
there.

## `per-quadrant-gate.diff`

Adds an opt-in `evaluation.gate_aggregation` config key (`micro` | `min`).

- `micro` (default): stock behavior — gate on the pooled per-item average.
- `min`: gate on the **worst** `case_type`'s (hard, soft). The unified env's
  gate score becomes monotonic in the weakest quadrant, so a candidate that
  sacrifices chat to boost command (what we observed) can no longer be accepted.

Touches `skillopt/engine/trainer.py` (baseline + candidate gate sites, `_gate_scores`
helper) and `skillopt/config.py` (key registration). Stock runs that don't set
`gate_aggregation` are unaffected.

Apply in the clone:

```bash
cd <skillopt-clone>
git apply /path/to/per-quadrant-gate.diff
```

The paired change — stratified reflect (one analyst minibatch per `case_type`) —
lives in this repo at `envs/incar_unified/adapter.py` (`reflect()` override), so
it needs no core patch; just keep the clone's copy of that file in sync.
