# Exp 2026-07-15 — paper-faithful run (minimal seed + qwen2.5 target)

**Setup runbook — results TBD.** First run intended to be faithful to the SkillOpt
paper (2605.23904v2), after diagnosing that every prior "seed wins / SkillOpt adds
nothing" verdict came from a **non-faithful** setup. Purpose: measure the paper's
actual claim — `no-skill → optimized` — on our data, with a trustworthy test set.

## Why the prior runs weren't a fair test

Four departures from the paper, all corrected here:

| | prior runs | paper | this run |
|---|---|---|---|
| epochs | **1** (`num_epochs: 1`) — slow/meta update barely fired | 4 | **4** |
| split | 60/20/20 → test=44, SE ±0.075 (regressions inside noise) | 2:1:7 | **2:3:5** (44/65/111) |
| gate | `aggregation=min` (our patch; a departure) | strict scalar | **`micro`** (scalar) |
| seed | v2-best expert skill (zero headroom) | no-skill baseline | **minimal seed** |

The min-gate was invented to stop the unified quadrant-trade, but that trade may be
an artifact of never running the slow/meta update (epoch>1). Faithful first, patch
later only if needed.

## Split: ALFWorld-like 2:3:5, not literal 2:1:7

The paper's 2:1:7 *default* assumes a large corpus; for bounded pools it grows
*selection* instead (ALFWorld 39 train / 140 selection / 134 test). On our 220-item
corpus, literal 2:1:7 gives val=23 (too noisy to select on). 2:3:5 keeps a
trustworthy test **and** a usable selection set:

| split | command | chat | total | per-quadrant SE |
|---|---|---|---|---|
| train | 21 | 23 | 44 | — |
| val (selection) | 30 | 35 | 65 | ~±0.09 |
| test | 51 | 60 | 111 | ~±0.07 |

Builder ratios now `n_val=0.3 n_test=0.5` (`build_unified_splits.py`).

## Minimal seed (`skills/minimal.md`)

I/O protocol only — the two output forms (command→one JSON object `{intent,slots,mode}`,
question→one prose sentence) + the output vocabulary. **All discovered heuristics
stripped** (routing cues, slot grounding, pronoun rules, mode-selection logic,
numeric handling, defaults, verbatim-copy, call-and-tell) — that procedural knowledge
is what the optimizer must rediscover. The one line kept, `no code fences / entire
reply is JSON`, is format plumbing, not domain knowledge: without it the strict
parser floors commands at ~0 (`answered_not_acted`) and the run measures nothing.
`initial.md` (v2-best) is untouched — kept for the harder expert-seed condition.

## Target: qwen2.5, and the temperature fix

Switched target llama3 → **qwen2.5:7b-instruct** (paper uses Qwen; far better
JSON/instruction-following than llama3-8b — our two failure modes are
`answered_not_acted` and over-abstention).

⚠️ **Determinism gotcha (found this run):** the target backend (`azure_openai.py`,
`openai_chat`) sends **no temperature**, so Ollama uses each model's Modelfile
default. Our reproducibility came entirely from the custom **`llama3-t0`** model
(`PARAMETER temperature 0` baked in) — the `-t0` suffix *is* the convention. Stock
`qwen2.5:7b-instruct` samples at ~0.7–0.8, so using it directly reintroduces
run-to-run variance into the val gate (random accept/reject) and test. Fix: mint a
`-t0` variant.

```powershell
ollama create qwen2.5-t0 -f "integrations\skillopt\bedrock\Modelfile.qwen2.5-t0"
# Modelfile: FROM qwen2.5:7b-instruct / PARAMETER temperature 0
```

Then use `--target_model qwen2.5-t0` (NOT the stock tag).

Secondary, not fixed: the **optimizer** (Bedrock Sonnet via LiteLLM, also `openai_chat`,
no temperature sent) samples at Sonnet's default, so edit *proposals* vary run-to-run.
The paper doesn't force optimizer determinism and the gate filters proposals, so this
is acceptable — just a known source of cross-run variance in *which* edits appear.

## Config (`configs/incar_unified_bedrock/default.yaml`)

`num_epochs: 4` · `batch_size: 20` · `gate_metric: mixed` `gate_mixed_weight: 0.5`
`gate_aggregation: micro` · `skill_init: …/minimal.md` · target=Ollama `:11434`,
optimizer=LiteLLM proxy `:4000` → Bedrock Sonnet.

Still-active non-stock element (log it, don't attribute results to "pure SkillOpt"):
**stratified reflect** (`adapter.py`, one analyst minibatch per `case_type`). It's a
fairness fix (stops minority-mode failures being drowned), not a cheat.

## Launch (from the clone `C:\path\to\SkillOpt`)

Sync repo → clone first (edits live in the repo; the run reads clone copies):

```powershell
$repo  = "C:\path\to\ai-evaluation"
$clone = "C:\path\to\SkillOpt"

Copy-Item "$repo\integrations\skillopt\config\incar_unified_bedrock.yaml" `
          "$clone\configs\incar_unified_bedrock\default.yaml" -Force
Copy-Item "$repo\integrations\skillopt\envs\incar_unified\skills\minimal.md" `
          "$clone\skillopt\envs\incar_unified\skills\minimal.md" -Force
Set-Location $clone
python "$repo\integrations\skillopt\build_unified_splits.py" --fixtures "$repo\fixtures" --out data\incar_unified_split
# expect: train=44 val=65 test=111

ollama create qwen2.5-t0 -f "$repo\integrations\skillopt\bedrock\Modelfile.qwen2.5-t0"

$env:PYTHONPATH = "C:\path\to\SkillOpt"
python scripts\train.py --config configs\incar_unified_bedrock\default.yaml --target_model qwen2.5-t0
```

Preflight: LiteLLM proxy up on `:4000` with the real key (config still shows the
`sk-litellm-CHANGEME` placeholder); Ollama up on `:11434`.

## Results — VERDICT FLIPPED: first faithful run that WORKED

Run dir: `outputs/skillopt_incar_unified_bedrock-sonnet_20260715_143958`.
12 steps (3/epoch × 4), accept=2 reject=10 skip=0, best from **step 6**, wall 7085s (~2h).

### Test scores (valid_unseen, 111 items)

| skill | chat (60) | command (51) | overall (111) |
|---|---|---|---|
| baseline S₀ (minimal seed) | 0.7167 | 0.1373 | 0.4505 |
| **best-on-val (step 6)** | **0.9167** | 0.1765 | **0.5766** |
| final/last | 0.7833 | 0.2549 | 0.5405 |

- **best-on-val vs baseline: +0.1261** (0.4505 → 0.5766). final vs baseline: +0.0901.
- **No overfit:** best-on-val scored **higher on test (0.5766) than on val (0.5472)** — the
  opposite of every prior run. The 2:3:5 split (val=65) closed the val→test gap.
- **Both quadrants beat baseline** (chat +0.20, command +0.04) under the plain **scalar/micro
  gate** — so the `min`-gate patch was treating a symptom of the non-faithful setup, not the method.
- Selection: baseline hard 0.5385 → best 0.5472 → final 0.5538. Tokens: 2.83M
  (prompt 2.61M / completion 0.22M), 1617 calls. **Verify actual $ on the proxy log —
  prompt-heavy, likely at/above the $4–7 estimate.**

### Accepts by epoch (converged early)

    epoch 1: accept=1  best=0.5179
    epoch 2: accept=1  best=0.5472   <- best-on-val (step 6)
    epoch 3: accept=0  best=0.5472
    epoch 4: accept=0  best=0.5472

All gains landed in epochs 1–2; epochs 3–4 found nothing better and the (ungated, force-inject)
slow update neither helped nor hurt the best. You still had to run 4 epochs to learn that.

### What the optimizer rediscovered (best_skill.md, 1972 chars)

From the bare I/O-protocol seed it re-derived real procedural knowledge — mostly chat-side, which
is where the gain came:
- **Format discipline** — start `{`/end `}`, never prefix a reply with the literal words "Act"/"Answer".
- **Ambiguity handling** — driver signals indifference ("anything", "whatever") → fill a generic
  value + `mode:execute`; reserve `clarify` for genuinely missing/unresolvable detail.
- **Verbatim factual answers** — copy exact value/units from context, no paraphrase.
- **Abstention** — if context lacks the fact, plainly say it's unavailable; don't guess or ask a follow-up.

### Deploy which skill

**best-on-val (step 6)** — the final skill drifted (command up, chat down) and scored lower on test
(0.5405). Gate did its job; `best_skill.md` is the artifact.

### Honest caveats

- **Easy direction.** minimal→optimized has big headroom (the paper's headline lives here). This does
  NOT show SkillOpt beating the v2-best **expert** seed — that's the next condition (`skill_init=initial.md`).
- **Command still weak (0.176).** qwen barely emits valid JSON commands from a bare seed; the optimizer
  only partially recovered the command heuristics the minimal seed stripped. Chat drove the win.

### Verdict

Prior "SkillOpt adds nothing / seed wins / overfits" verdicts (runs #1–4) were **artifacts of a
non-faithful setup** (expert seed, 1 epoch, 60/20/20, min gate), not properties of the method. Run
faithfully — minimal seed, 4 epochs, 2:3:5, scalar gate, capable temp-0 target — **SkillOpt lifts
held-out test by +12.6 points without overfitting.** The method works on this env.
