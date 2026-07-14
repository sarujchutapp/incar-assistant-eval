# SkillOpt experiments

**→ [FINDINGS.md](FINDINGS.md) — the cross-cutting lessons (read this first).**

Tracking log for SkillOpt runs on the `incar_unified` env. One folder per run,
each containing:

- `initial.md` — the exact seed skill the run started from (`skill_v0000.md`)
- `best_skill.md` — the best skill the optimizer produced (best-on-val)
- `results.md` — setup, config deltas, test scores, cost, and findings

Test scores are on `valid_unseen`; the headline number is **best-on-val**, the
skill you would actually deploy. Test size differs by corpus version — **v1** =
29 items (9 chat, 20 command); **v2** = 41 items (21 chat, 20 command) — so
`overall` is **not comparable across corpus versions**.

## Runs

| date | experiment | corpus | chat | command | overall | note |
|---|---|---|---|---|---|---|
| 2026-07-09 | [micro-gate baseline](2026-07-09_micro-gate-collapse/results.md) | v1 | 0.00 ☠️ | 0.50 | 0.345 | chat collapsed |
| 2026-07-13 | [min-gate + stratified + rebalanced seed](2026-07-13_min-gate-stratified/results.md) | v1 | 0.556 | 0.30 | 0.379 | collapse fixed, both quadrants alive |
| 2026-07-13 pm | [seed format fix + corpus v2 + temp-0](2026-07-13_seed-fix-corpus-v2/results.md) | v2 | 0.810 | 0.600 | 0.707 | **seed fix baseline=0.756; optimizer no gain (overfit −0.05)** |

(chat / command / overall = best-on-val hard accuracy. For the v2 run the **baseline seed (0.756) beat best-on-val (0.707)** — the seed format fix was the real win; SkillOpt added nothing on top.)

## How to add the next run

After a run finishes, from its `outputs/<run>/` dir:

```bash
E="docs/experiments/<date>_<slug>"
mkdir -p "$E"
cp outputs/<run>/skills/skill_v0000.md "$E/initial.md"
cp outputs/<run>/best_skill.md         "$E/best_skill.md"
# then write $E/results.md and add a row to the table above
```
