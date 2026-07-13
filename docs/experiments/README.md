# SkillOpt experiments

Tracking log for SkillOpt runs on the `incar_unified` env. One folder per run,
each containing:

- `initial.md` — the exact seed skill the run started from (`skill_v0000.md`)
- `best_skill.md` — the best skill the optimizer produced (best-on-val)
- `results.md` — setup, config deltas, test scores, cost, and findings

Test scores are on `valid_unseen` (29 items: 9 chat, 20 command); the headline
number is **best-on-val**, the skill you would actually deploy.

## Runs

| date | experiment | gate | chat | command | overall | note |
|---|---|---|---|---|---|---|
| 2026-07-09 | [micro-gate baseline](2026-07-09_micro-gate-collapse/results.md) | micro | 0.00 ☠️ | 0.50 | 0.345 | chat collapsed |
| 2026-07-13 | [min-gate + stratified + rebalanced seed](2026-07-13_min-gate-stratified/results.md) | min | 0.556 | 0.30 | **0.379** | collapse fixed, both quadrants alive |

(chat / command / overall = best-on-val hard accuracy.)

## How to add the next run

After a run finishes, from its `outputs/<run>/` dir:

```bash
E="docs/experiments/<date>_<slug>"
mkdir -p "$E"
cp outputs/<run>/skills/skill_v0000.md "$E/initial.md"
cp outputs/<run>/best_skill.md         "$E/best_skill.md"
# then write $E/results.md and add a row to the table above
```
