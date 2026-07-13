# Exp 2026-07-13 — min-gate + stratified reflect + rebalanced seed

Fixes the chat/command collapse from the 2026-07-09 run. Three coordinated
changes, all aimed at the same failure. Committed as `af66782`.

## Setup

| | |
|---|---|
| Env | `incar_unified` |
| Optimizer | Bedrock Claude Sonnet (via LiteLLM proxy) |
| Target | llama3 (Ollama) |
| Gate | `metric=mixed`, **aggregation=min** (gate on the WORST case_type) |
| Reflect | **stratified** — one minibatch stage per case_type (adapter `reflect()` override) |
| Seed | **rebalanced** 2674-char (`initial.md`) — routing-first, "always-JSON" drumbeat cut |
| Steps | 5, epochs 1 · seed 42 |
| Run dir | `outputs/skillopt_incar_unified_bedrock-sonnet_20260713_074016` |

## Changes vs previous run

1. **min-of-quadrants gate** (`evaluation.gate_aggregation=min`; core patch in `integrations/skillopt/patches/per-quadrant-gate.diff`) — the gate score is monotonic in the weakest quadrant, so a candidate that sacrifices a quadrant can't be accepted.
2. **Stratified reflect** — chat failures get their own analyst call instead of being drowned in all-command minibatches.
3. **Rebalanced seed** — routing decided first; both branches equally prominent.

## Test scores (valid_unseen, 29 items)

| skill | chat (9) | command (20) | overall (29) |
|---|---|---|---|
| baseline S₀ | 0.7778 | 0.0000 | 0.2414 |
| **best-on-val** | **0.5556** | **0.3000** | **0.3793** |
| final | 0.5556 | 0.1000 | 0.2414 |

- best-on-val `val` score: 0.3633 (step 3) · accept=3 reject=2
- wall 2578s · tokens 878,137 (415 calls) · ~28 Bedrock calls · ≈ $2

## Verification the mechanism engaged

- Header: `[gate] metric=mixed aggregation=min mixed_weight=0.5`
- `baseline selection hard=0.0000` — min correctly reports the worst quadrant (command 0/20); micro would have shown ~0.24.
- Two `[2/6 REFLECT minibatch]` lines per step (chat group + command group).

## Outcome

**Collapse fixed.** best-on-val keeps BOTH quadrants alive (chat 0.556, command 0.30)
and beats the previous best on overall (0.379 vs 0.345). The min-gate protects the
weakest quadrant but lets the stronger slide (chat drifted 0.78→0.556 as command rose
off zero). The gate correctly kept step 3 as best and rejected the command-tanking
final skill.

## Open follow-ups

- Rebalanced seed **under-emits tool calls zero-shot** — baseline command 0/20 (old
  seed was 0.15). Restore some command assertiveness without re-imbalancing.
- llama3 is a **weak tool-calling target** — command ceiling ~0.30 regardless of skill.
- Deferred: per-role optimizer reasoning (cost/proxy caveats).
