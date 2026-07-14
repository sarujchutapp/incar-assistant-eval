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

*Caveat (v3): the min-gate protects the worst **val** quadrant, not test.* In the
v3 run the accepted skill held command on val but collapsed it on test (0.55 →
0.30) — the optimizer, pulled toward the newly-added chat/abstain cases, rewrote
the skill so the model prefixed commands with `**Question**` and answered in prose,
re-introducing the `answered_not_acted` format bug the seed had cured. The gate
can't see a val→test drop; only a larger val set narrows it. Note the collapse
direction is not fixed: v1 sacrificed chat, v3 sacrificed command — whichever
quadrant the current emphasis pulls away from.

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

## 9. On a weak target, the ceiling is *compliance*, not rule generation

Worked example — the command `"call him back"` (ambiguous: no referent). Gold =
`call_contact, slots={}, clarify`. llama3 emitted:

```json
{"intent": "call_contact", "slots": {"name": "him"}, "mode": "execute"}
```

It copied the pronoun as a slot value and executed → `hard=0` (soft=0.5, intent
was right). **This failed identically under the seed *and* the best_skill.**

The tempting reading is "SkillOpt can't generate the obvious rule." The evidence
says the opposite: the rule was present the whole time (seed: *"names a target
only by pronoun ('her') → omit that slot"*), **and the optimizer *added* a
reinforcing correctness rule** during the run (*"never emit null/unknown/empty —
leave the key out"*). So the optimizer *did* produce the right guidance; the weak
target simply **did not comply**.

**Lesson: text-space optimization can only help to the extent the target follows
instructions.** On a weak model the optimizer can propose correct rules that the
model ignores — so neither hand-writing nor optimizing the prompt moves the
needle. The limit is model capability/compliance, not rule generation. *(Shown at
1 epoch on a weak target; a capable target is the clean test.)*

**Corollary (v3): the weak target also over-applies rules it *does* follow.**
Adding one abstain rule to the seed ("if Context lacks the fact, say you don't
have it") made llama3 refuse **6 answerable** questions whose fact was in context
— baseline chat 0.95 → 0.625, entirely over-abstention, not hallucination. A rule
precise enough to fix one failure mode blunt-forces the opposite one on a model
that can't calibrate when it applies. Rules for weak targets need *both* sides
stated ("if the fact IS present, always answer it") — and even then compliance is
the ceiling.

**Shots.** Everything here is **zero-shot** — the skill carries instructions + one
format example, no per-case demonstrations. SkillOpt edits the skill *text*, so it
*can* add worked examples (**static few-shot in the system prompt**); it just
mostly wrote rules. Dynamic per-query retrieval few-shot is outside its scope. If
a model ignores a rule, a seeded example is the cheap test of whether it needs
demonstrations rather than instructions.

## 10. SkillOpt's real payoff here: it upgraded the *benchmark*

SkillOpt didn't improve the prompt (§1) — but **running it, and reading its saved
trajectories, surfaced a series of benchmark defects and gaps that inspection
alone would have missed.** It functioned as a **stress-test / QA harness**:

- **Format bug found** → the seed fix. `answered_not_acted`: correct JSON wrapped
  in prose was being rejected. Fixing it lifted baseline 0.24 → 0.76.
- **Misleading logs found & fixed.** The result `reference_text`/`fail_reason`
  printed `intent+slots` for *every* command — but the scorer checks different
  things per case type (below). The log helper now shows the true criterion.
- **Scorer semantics clarified** (resolved two apparent "anomalies"). Command
  `hard` (success) depends on the case:
  - `clear`/`defaultable` → intent **and** slots **and** the stakes-derived mode
    (`confirm` for high-stakes like `send_message`/`call_contact`, else `execute`);
  - `ambiguous` → **`mode=clarify` only** — intent/slots are *not* scored, so a
    right-intent-but-executed answer FAILS (`u_6` "call him back"), while a
    clarify with a *wrong* intent PASSES (the climate `intent="clarify"` case);
  - abstention (`none`/`out_of_scope`) → must not act.
  `soft` is always intent+slot F1, computed independently — which is why hard/soft
  fully diverge on ambiguous cases.
- **Coverage gaps identified:** chat has no clarify/abstain path (so hallucination
  is undetectable); commands carry no resolving context (fill-from-context
  untested).
- **Corpus grown & split hardened:** chat 44 → 103, seeded representative split.

So the honest answer to *"does SkillOpt help build a benchmark?"* is **yes — as a
QA harness, not as an optimizer.** The value came from exercising the benchmark at
scale and reading the outputs, not from the optimized skill.

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
- **Fill-from-context (command coverage gap).** Command cases carry no resolving
  `context` — only `car_state` + an `ambiguity` label. So we test fill-from-
  utterance (`clear`), fill-from-default (`defaultable`), and omit+clarify
  (`ambiguous`), but **not** "utterance under-specified BUT context resolves it →
  fill from context" (e.g. `context: "him" = last caller` → fill the name). The
  `ambiguity` field is a difficulty *label*, not a resolving context; this fourth
  scenario needs a context field commands lack (overlaps the read-tool idea).
- **Scorer strictness.** Decide deliberately whether the chat faithfulness check
  should accept paraphrases (recall vs reproducibility trade-off).
- **Ambiguous scoring ignores intent** — *resolved 2026-07-14.* `is_success` now
  requires `mode=clarify` **and** the correct intent for ambiguous commands (the
  intent is always knowable across our corpus; only a slot is missing, which
  stays unscored). A clarify with the wrong intent no longer passes. The cost
  model is deliberately left as-is — a harmless clarify still scores CORRECT on
  the *safety* axis even when it's not a task success.
- **Chat clarify/abstain path** — *resolved 2026-07-14.* `ChatCase` gained an
  `answerable` flag; when False the context deliberately doesn't support an
  answer and success = the model abstains (deterministic marker-phrase check,
  same spirit as `_faithful`). Added 10 unanswerable cases (distractor context)
  to `chat_grounded.json`, stratified as their own split group so every split
  holds some. Answering anyway now registers as a hallucination failure.
