# Exp 2026-07-09 — micro-gate baseline (chat collapse)

First working end-to-end SkillOpt+Bedrock run on the unified env. Surfaced the
core failure: a single scalar reward lets the optimizer trade one quadrant away.

## Setup

| | |
|---|---|
| Env | `incar_unified` (command + chat in one skill) |
| Optimizer | Bedrock Claude Sonnet (via LiteLLM proxy) |
| Target | llama3 (Ollama) |
| Gate | `metric=mixed` (0.5·hard+0.5·soft), **micro** aggregation (pooled over all items) |
| Reflect | stock (pooled minibatches) |
| Seed | minimal 620-char (`initial.md`) |
| Steps | 5, epochs 1 · seed 42 |
| Run dir | `outputs/skillopt_incar_unified_bedrock-sonnet_20260709_172945` |

## Test scores (valid_unseen, 29 items)

| skill | chat (9) | command (20) | overall (29) |
|---|---|---|---|
| baseline S₀ | 0.7778 | 0.1500 | 0.3448 |
| **best-on-val** | **0.0000** ☠️ | 0.5000 | 0.3448 |
| final | 0.0000 | 0.4000 | 0.2759 |

- best-on-val `val` score: 0.4006 (step 3) · accept=2 reject=3
- wall 2821s · tokens 733,933 (406 calls) · ~28 Bedrock calls · ≈ $1.90

## Finding

The optimizer improved command (+233%) but **destroyed chat** (0.78→0.00). Overall
looks flat (0.3448→0.3448) only by coincidence — command gains exactly offset chat
losses. The micro-average gate is blind to per-quadrant collapse; the command-heavy
failure minibatches pushed the skill toward "always emit a tool call," which is
death for the informational quadrant. See `best_skill.md` — ~40 lines of forceful
command/JSON rules, ~10 lines of chat.

→ Motivated Exp 2026-07-13 (min-gate + stratified reflect + rebalanced seed).
