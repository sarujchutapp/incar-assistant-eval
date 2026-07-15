# SkillOpt experiments

**→ [FINDINGS.md](FINDINGS.md) — the cross-cutting lessons (read this first).**

Tracking log for SkillOpt runs on the `incar_unified` env. One folder per run,
each containing:

- `initial.md` — the exact seed skill the run started from (`skill_v0000.md`)
- `best_skill.md` — the best skill the optimizer produced (best-on-val)
- `results.md` — setup, config deltas, test scores, cost, and findings

Test scores are on `valid_unseen`; the headline number is **best-on-val**, the
skill you would actually deploy. Test size differs by corpus version — **v1** =
29 items (9 chat, 20 command); **v2** = 41 items (21 chat, 20 command); **v3** =
44 items (24 chat incl. 15 abstain corpus-wide, 20 command) — so `overall` is
**not comparable across corpus versions**.

## Runs

| date | experiment | corpus | chat | command | overall | note |
|---|---|---|---|---|---|---|
| 2026-07-09 | [micro-gate baseline](2026-07-09_micro-gate-collapse/results.md) | v1 | 0.00 ☠️ | 0.50 | 0.345 | chat collapsed |
| 2026-07-13 | [min-gate + stratified + rebalanced seed](2026-07-13_min-gate-stratified/results.md) | v1 | 0.556 | 0.30 | 0.379 | collapse fixed, both quadrants alive |
| 2026-07-13 pm | [seed format fix + corpus v2 + temp-0](2026-07-13_seed-fix-corpus-v2/results.md) | v2 | 0.810 | 0.600 | 0.707 | **seed fix baseline=0.756; optimizer no gain (overfit −0.05)** |
| 2026-07-14 | [abstain cases + corpus v3](2026-07-14_abstain-corpus-v3/results.md) | v3 | 0.792 | 0.300 ☠️ | 0.568 | **isolation: seed abstain rule caused −0.136; scoring inert, corpus −0.03. Reverted to v2 seed (0.727)** |
| 2026-07-15 | [faithful: minimal seed + qwen2.5-t0](2026-07-15_faithful-minimal-qwen/results.md) | v3† | 0.917 | 0.176 | **0.577** | **✅ VERDICT FLIPPED — first faithful run works: test +0.126 vs baseline, no overfit (test>val), both quadrants up under scalar gate** |

(chat / command / overall = best-on-val hard accuracy. For runs #1–4 the **baseline seed beat best-on-val** — seed 0.756 / 0.591 vs best 0.707 / 0.568 — and SkillOpt overfit val / hurt test (v1 sacrificed chat, v3 command). **Run #5 (2026-07-15) overturned that:** run *faithfully* — minimal seed, 4 epochs, 2:3:5 split, scalar gate, capable temp-0 target — SkillOpt lifts test +0.126 with no overfit. The earlier verdicts were setup artifacts, not the method.

† Run #5 is **not comparable** to the v3 rows above: its baseline is the *minimal* seed (not the expert v2 seed), the target is *qwen2.5-t0* (not llama3-t0), the split is *2:3:5* (test=111, not 44), so it measures no-skill→optimized rather than beat-the-expert-seed. Next condition: same setup with `skill_init=initial.md` to test whether it can beat the hand-tuned seed.)

## How to add the next run

After a run finishes, from its `outputs/<run>/` dir:

```bash
E="docs/experiments/<date>_<slug>"
mkdir -p "$E"
cp outputs/<run>/skills/skill_v0000.md "$E/initial.md"
cp outputs/<run>/best_skill.md         "$E/best_skill.md"
# then write $E/results.md and add a row to the table above
```
