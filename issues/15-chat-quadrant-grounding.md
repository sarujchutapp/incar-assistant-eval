Status: ready-for-agent

# Chat quadrant: ground informational cases in context + generate the grounded corpus

## Parent

PRD #1

**Type:** AFK  ·  sibling track to the command corpus (roadmap #10)

## What to build

Make the chat / informational quadrant **context-grounded** and populate its verifiable corpus by fresh synthesis, so it measures reading + extraction (not memorized trivia) and stays contamination-proof.

### Current behavior

The chat quadrant scores an answer against a ground-truth `fact`, but the case carries only `question` + `fact` — the `fact` is used for scoring and is **never shown to the model**. So it's effectively closed-book trivia: a small model passes only if it *knows* the answer, a large model passes by *recalling* public data. No grounding context. Faithfulness is a strict normalized-substring match, so number/unit variants ("12 minutes" vs "twelve minutes" vs "12 min") wrongly fail. The open/subjective tail is a separate cross-family pairwise LLM judge (Bradley-Terry).

### Desired behavior

Verifiable cases become **grounded triples**: `question` + `context` + `answer`, where `context` is a short car-telemetry / KB snippet **fed to the model** and the `answer` is derivable **only** from that context. Because context values are freshly authored (novel ETA/fuel/weather/hours), the task is "read this context and extract the answer" — memorization/contamination can't help (the whole point). Faithfulness tolerates number-word/unit variants. Open/subjective tail unchanged (judge track).

### Key interfaces (behavioral)

- The chat case type gains a **`context`** field; the chat prompt builder includes it; the chat loader reads it from fixtures.
- **Faithfulness** canonicalizes numbers/units before matching — reuse the command side's number-word / number-coercion helpers (the `_tokens` / `_as_number` style canonicalization in the safety module), not a fresh copy.
- A **chat synthesis helper** parallel to `incar_eval.synth`: drafts `(question, context, answer)` for a question-type with a **different-family** model, checks the answer is derivable from the context, dedupes, queues for review. Uses the `ModelClient` port so the pure core is stub-testable.
- Grounded chat fixtures (`{question, context, fact}`) extend the existing seed chat cases.

## Conventions & rules (MUST follow)

See `reserch/corpus_design.md`, `reserch/benchmark_spec.md`, `reserch/standards_alignment.md`.

1. **No public-corpus import.** Author fresh (frozen decision — importing public data re-imports contamination). KVRET/SMD may inform *what questions look like*; no data imported.
2. **Grounding = contamination defense.** Every verifiable case's `answer` must be derivable **only** from its `context`; author context with fresh/novel values so nothing is answerable from memory.
3. **Different family than the target; human-verify; no pure templating** (as with the command corpus; target = llama3).
4. **Two tracks, two scorers — don't mix:** grounded/verifiable → deterministic faithfulness (script); open/subjective ("tell me a joke", opinions) → the existing cross-family pairwise LLM judge. Do NOT fact-check open questions; do NOT judge grounded ones.
5. **Judge stays cross-family:** the judge family must differ from every target; don't regress it.
6. **Faithfulness robustness:** "12 minutes" / "twelve minutes" / "about 12 min" all match fact `12 minutes`.
7. **Feedback loops green:** `python -m pytest` and `python -m mypy` (strict).

## Acceptance criteria

- [ ] The chat case type has a `context` field; the chat prompt includes it; the loader reads it
- [ ] Faithfulness matches number-word/unit variants (test: "twelve minutes" satisfies fact "12 minutes")
- [ ] A set of grounded verifiable chat cases exists with fresh synthetic `context`, each answer derivable only from its context, human-verified
- [ ] A chat synthesis path drafts `(question, context, answer)` with a different-family model and queues candidates (pure core unit-tested with a stub)
- [ ] The open/subjective tail (pairwise judge → Bradley-Terry) is unchanged and still cross-family
- [ ] `python -m pytest` and `python -m mypy` are green

## Out of scope

- The **SkillOpt chat env wrapper** (searchqa-style env optimizing a chat skill against this quadrant) — a separate follow-up, like the command env was
- The command/control quadrant (unchanged)
- New open-ended judge behavior beyond the existing track

## Blocked by

None. Depends only on the existing chat quadrant + the `ModelClient` port. Scripted synthesis needs a non-llama model + key; otherwise draft with a non-llama chat model and run through the chat filter.
