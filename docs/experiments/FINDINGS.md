# Findings — SkillOpt on the in-car benchmark

Cross-cutting lessons from optimizing a single portable skill (system prompt)
for a small in-car voice assistant, using SkillOpt (Bedrock Sonnet optimizer,
local Ollama target) against our two-track benchmark (command = tool call,
chat = grounded prose). Per-run detail lives in the sibling folders; this is the
synthesis.

## TL;DR

1. **The seed prompt mattered more than the optimizer.** A single format fix to
   the starting prompt moved baseline overall **0.24 → 0.76**; SkillOpt then
   added **nothing** on top (and slightly overfit). Prompt engineering beat
   text-space optimization on this setup.
2. **Aggregate scores hide mode collapse.** A flat "overall" concealed chat
   cratering 0.78 → 0.00 while command rose. Per-quadrant reporting + a
   min-of-quadrants gate were needed to see and stop it.
3. **The target model is a hard ceiling.** No prompt got llama3's command track
   much past ~0.55. Optimizing a weak target is optimizing against a wall.
4. **Tiny eval sets make results untrustworthy.** At 9 items/quadrant, one item
   = 11%; most deltas were inside the noise. Growing the corpus was foundational.

---

## 1. The seed prompt dominated the optimizer

The biggest single lever in the whole project was **rewriting the starting
skill**, not running the optimizer:

| | baseline (seed) | best-on-val (SkillOpt) |
|---|---|---|
| overall | **0.756** | 0.707 (**−0.05**) |
| command | 0.55 | 0.60 |
| chat | 0.95 | 0.81 |

Once the seed was good, SkillOpt's best candidate generalized *worse* than the
untouched seed. **Text-space optimization helps most when the starting prompt is
poor; with a well-engineered seed there is little headroom to recover.** The
deployable artifact here is the seed itself.

## 2. Diagnose failures from real outputs, don't guess

The seed fix only happened because we read the actual model outputs. Baseline
command was 0/20 — easy to misread as "the model can't do tool calls." The
prediction files showed the real cause: `answered_not_acted` — llama3 emitted
**correct** JSON wrapped in prose and code fences, which the parser rejected:

> `"I understand the driver wants... Here's my response: \`{"intent": ...}\`"`

The fix was a prompt change (silent routing + "your entire reply is the JSON
object"), not a modelling change. **Score the trajectories, then look at them.**

## 3. Aggregate scores hide mode collapse

The first unified run improved command (+233%) but drove chat to zero; "overall"
stayed flat (0.345 → 0.345) purely because the gains offset the losses. A single
scalar reward is **blind to trading one behavior mode for another**. Two fixes:

- **Per-quadrant reporting** — always break the score down by behavior mode.
- **min-of-quadrants gate** — gate on the *worst* quadrant, not the pooled
  average, so the reward is monotonic in the weakest mode and a candidate can't
  be accepted by sacrificing a quadrant.
- **Stratified reflection** — give each mode its own reflection minibatch, so the
  optimizer even *sees* minority-mode failures instead of drowning them.

This is a benchmark-design lesson as much as an optimizer one: **the "overall"
number is the one most likely to lie to you.**

## 4. Generalization: val, test, best, and final are four different things

- **best-on-val ≠ best-on-test.** The optimizer maximizes a *validation* score;
  on a small val set it can fit noise. We saw best-on-val score −0.05 vs the seed
  on held-out test (it traded test-chat 0.95 → 0.81 for val gains that didn't
  transfer). The **val→test gap is the overfitting signal** to watch.
- **best ≠ final by design.** SkillOpt's end-of-run "final" skill includes
  force-accepted slow-update / meta phases that bypass the gate, so it can be
  worse than the best gated skill. Deploy `best_skill`, not the last one.

## 5. Statistical power comes from items, not re-splitting

At 29 test items (9 chat), one item ≈ 11% and deltas were inside the noise band.
You **cannot** manufacture power by re-splitting a fixed corpus — the minority
quadrant is needed in *all* splits (including train, so the optimizer can learn
it). The only fix is **more cases**: we grew chat 44 → 103 (generate → grounding/
leak/dedup filter → human review → seeded, representative split), taking test-chat
to 21 (~5%/item). **Until the eval is powerful, no optimization result is
trustworthy** — including the "no gain" finding above, which is why we grew it.

## 6. The target model is a hard ceiling

llama3's command track sat ~0.50–0.60 regardless of the skill. Prompt work moves
*format adherence and routing*; it cannot give a weak model tool-calling
competence it lacks. **Absolute scores are capped by the target**, so a fair read
of any prompt-optimization result requires a target with headroom.

## 7. Deterministic scoring of natural language: harsh but deliberate

- **Command** scoring is structured (parse JSON → intent/slot match) — robust,
  the "executable check" case SkillOpt is built for.
- **Chat** scoring is faithfulness (the grounded fact appears in the answer) —
  deterministic substring matching, which false-negatives on valid paraphrases.
  That harshness is a **deliberate contamination defense** (answers derivable
  only from provided context, never world knowledge). The SkillOpt paper scopes
  itself the same way: reliable automatic verifiers for closed tasks; human/
  model judges for open-ended ones.
- **temp = 0 on the target** made eval reproducible and improved format
  consistency (greedy decoding wanders into prose less).

## 8. When does text-space optimization actually help?

Synthesizing the above with the paper's own limitations, it needs roughly all of:

1. **Headroom** — a genuinely suboptimal starting prompt.
2. **A reliable signal** — an automatic verifier the gate can trust.
3. **Enough validation data** — or it overfits the selection set.
4. **A capable target** — or the ceiling caps any gain.

Our setup violated (1), (3), and (4) at once — good seed, ~40-item val, weak
target — so the honest result is **no gain**, and prompt engineering won. This is
not "SkillOpt doesn't work"; it's "these are the conditions under which it does."

## Cost

Whole investigation ≈ **$6.50** of Bedrock spend (three runs). The target (Ollama)
is free; only the optimizer is billed, ~28–80 calls per run. **Output tokens
dominate cost** (the skill rewrites) — cap `rewrite_max_completion_tokens` if
budget matters.

## Open questions

- **Stronger target (headroom test).** Re-run with a capable tool-caller
  (qwen2.5 / llama3.1) — the one experiment that would tell us whether "no gain"
  is fundamental or just the weak-target wall.
- **Read-tool category.** The benchmark models informational queries as grounded
  prose; a real assistant would invoke getters. A third `case_type` is possible
  but only worth it if getter-invocation is a deployment requirement.
- **Scorer strictness.** Decide deliberately whether the chat faithfulness check
  should accept paraphrases (recall vs reproducibility trade-off).
