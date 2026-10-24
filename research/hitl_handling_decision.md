# Decision record — handling the HITL slices (8 & 9) under no-human-review / no-API constraints

**Date:** 2026-06-22
**Status:** Decided.
**Context docs:** `benchmark_spec.md` (§6 data sourcing, §9 validation anchor), the implementation issues (`issues/`, GitLab #9–#10).

## Problem

Two slices are human-in-the-loop:

- **Slice 9 — case authoring at scale** (~400 human-verified command/control cases).
- **Slice 8 — human-satisfaction validation anchor** (~50–100 human ratings).

The team has **little human-review capacity** and, currently, **no live LLM API access**. Question raised: is there a way to do this without a full human review pass — e.g. spawning LLM subagents?

## Decisions

### 1. Slice 9 verification → cross-family auto-verification, humans review only the remainder

Built `src/incar_eval/verify.py`. Several **different-family** models independently map each synthesized utterance to a tool call through the model-client port. Policy chosen: **agreement auto-accepts** — if ≥2 distinct families agree on `(intent, slots)`, the gold is auto-accepted; everything else is flagged:

- `flagged_disagreement` — the families did not reach consensus.
- `flagged_manual` — hand-authored **safety / `out_of_scope`** cells, and **all `ambiguous`** cells (their gold is the *clarify* behaviour, which content-consensus cannot establish).

The human queue shrinks from "review ~400" to "review the flagged remainder." `verify_batch` reports an `auto_accept_rate`.

### 2. Slice 8 human-satisfaction anchor → NOT automated (stays human)

We deliberately do **not** substitute an LLM (or subagent) for the human raters here. The anchor's entire purpose (§9) is *independent* verification that the automated scores track human judgment. Generating those ratings with an LLM validates an LLM-judge with an LLM — which **reintroduces the exact Type-C "no independent verification" weakness** the benchmark exists to defend against. Automating it removes the value, not the cost.

Mitigation instead of automation: the anchor is **one-time and small**, and its dominant command/control half is **correctness-gated** ("right action: yes/no"), so it is fast in-house — not an ongoing burden.

### 3. Subagents are valid verifiers, with a family caveat

A demonstration spawned **Sonnet + Haiku** subagents as the verifier panel over 6 real utterances: **4 of 6 auto-accepted**, and the disagreement correctly surfaced the genuinely ambiguous case ("play something" — `title: null` vs `""`). This proves the mechanism on real model output.

Caveat recorded: **Sonnet and Haiku are the same family (Anthropic).** Self-preference bias is a *family* property, so a same-family panel does not provide true cross-family independence. For the shipping benchmark:
- include **≥1 non-Anthropic vendor** in the panel, and
- **do not** use Claude verifiers at all if the car's target model is itself Claude.

A same-family panel is fine only for mechanism demonstrations.

### 4. Live-model parts deferred to manual work

With no API access, the live-model steps are done **by hand** later: utterance synthesis, the real cross-family panel run, the §9 multi-tier demonstration run, and the §8 anchor pass. The implemented pipeline runs deterministically on **recorded fixtures / `FakeModelClient`** with no network, so all logic is testable today and a JSON loader (`incar_eval.loader` / `incar_eval.cli`) lets cases and recorded responses be authored by hand and run from the command line.

## Net effect on the human budget

| Task | Before | After this decision |
| --- | --- | --- |
| Slice 9 case verification | review ~400 | review only the flagged remainder (disagreements + safety/ambiguous/oos cells) |
| Slice 8 validation anchor | ~50–100 ratings | unchanged, but one-time and mostly objective yes/no |

## What stays HITL

Slices 8 and 9 remain HITL issues on the tracker. The automation reduces the slice-9 human load to a spot-check; it does **not** eliminate slice 8.
