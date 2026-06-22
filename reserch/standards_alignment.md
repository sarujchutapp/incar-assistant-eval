# Standards alignment — what the SLU/DST prior art settles, and where we stand

Maps the established conventions from the datasets the spec already cites (SGD, MultiWOZ, SLURP, MASSIVE) onto our benchmark, so conventions are *looked up*, not guessed.

Sources: Schema-Guided Dialogue (arXiv 1909.05855), MultiWOZ (1810.00278) / 2.2 (2007.12720) / 2.4 (2104.00773), SLURP (2011.13205), MASSIVE (2204.08582).

## Already adopted

| Convention | Standard | Our implementation |
| --- | --- | --- |
| Schema = service interface with NL descriptions | SGD | `IntentSpec` with `description` per intent |
| Categorical vs non-categorical slot matching | SGD | `safety.slots_match` (categorical exact; non-cat normalized) |
| Acceptable-value lists ("8pm"/"20:00" both correct) | MultiWOZ 2.2 | gold non-cat slot may be a list; verifier variants merged |
| `active_intent` with a NONE value | SGD | our `none` abstention label |
| Intent accuracy + slot F1 + all-slots exact-match | SLURP / MASSIVE | `metrics.py` (intent_accuracy, slot_f1, slots_exact_rate) |
| Joint Goal Accuracy for multi-turn | MultiWOZ | `dialogue.score_dialogue` JGA (uses the normalized matcher — see log 2026-06-22 #2) |
| Categorical slots have enumerated `possible_values`, validated | SGD | `IntentSpec.categorical`; `CATEGORICAL_SLOTS` derived from the schema; `validate_record` rejects out-of-vocab (see log 2026-06-22 #1) |
| Wilson intervals + paired significance | (stats best practice) | `stats.py` |

## Gaps worth closing (prioritized)

| # | Gap | Standard says | We currently | Effort |
| --- | --- | --- | --- | --- |
| 3 | **No value canonicalization** | MultiWOZ canonicalizes numbers/times/units before matching ("8pm"→"20:00"); we saw "68°F"→20°C and "fifteen minutes" | only lowercase/punct/article strip; numerics/units uncanonicalized | medium |
| 4 | **Binary slot-value scoring** | SLURP **SLU-F1**: slot-label F1 weighted by word/char **edit distance** on the value — partial credit for near-misses | non-cat value match is all-or-nothing | medium |
| 5 | **`clarify` doesn't say which slot** | SGD `requested_slots`: the system requests the specific missing slot | `clarify` is a bare mode; we don't score *what* it should ask for | medium |
| 6 | **Span grounding** | SGD/MultiWOZ 2.2: non-cat values are spans from the utterance (limits hallucinated values) | gold non-cat values are free strings, not utterance spans | low-med |

(#1 and #2 closed — see Adoption log. Gap numbers are kept stable for reference.)

## Deliberately N/A

| Convention | Why not |
| --- | --- |
| Inform/Success split (MultiWOZ) | "Inform" presumes a DB of entities to suggest; we have no DB. Our **TSR ≈ Success** (goal achieved); the chat quadrant's faithfulness-vs-fact is the closest "inform". (Document the mapping.) |
| Unseen-service / zero-shot generalization (SGD's headline) | We benchmark one fixed schema, not transfer to unseen APIs. |
| Dialogue-act ontology (ISO 24617-2 / MultiWOZ acts) | Our response modes (execute/confirm/clarify/warn) are a safety taxonomy keyed on driver attention, not general dialogue acts. Partial mapping: clarify↔request, confirm↔confirm. |

## Recommended order

Next: **#3** (value canonicalization) since we've already hit it in real data; then #4–#6 as deepenings to weigh later.

## Adoption log

A dated record of standards adopted, so the lineage of each convention is traceable rather than folk knowledge.

- **2026-06-22 — Slot matching (SGD categorical/non-categorical + MultiWOZ acceptable-value lists).** Categorical slots exact; non-categorical normalized against an acceptable-value list; cross-family verifier surface-variants merged into the list. `safety.slots_match`, `verify._consensus_slots`. Refs: SGD 1909.05855, MultiWOZ 2.2 2007.12720. See `schema_clarifications.md` §4.
- **2026-06-22 — Range-relative intensity.** Defaultable magnitude scored as a fraction of the car's own range (`car_state.climate_range`/`volume_range`) via an intensity tier, not fixed degrees. `safety.effective_bands`. (Our extension, in the spirit of MultiWOZ value normalization.) See `schema_clarifications.md` §5.
- **2026-06-22 — #1 Categorical `possible_values` in the schema + validation.** Each command intent's `IntentSpec` declares its categorical slots and allowed values; `CATEGORICAL_SLOTS` is derived from the schema (no hardcoded set); `validate_record` rejects out-of-vocabulary categorical gold values (e.g. `zone="backseat"`). Ref: SGD `possible_values`.
- **2026-06-22 — #2 JGA uses the normalized matcher.** `dialogue.score_dialogue` scores each turn's accumulated state with `safety.slots_match` instead of raw `==`, so multi-turn JGA applies the same categorical/non-categorical rules as single-turn (no stricter-by-accident multi-turn scoring). Ref: MultiWOZ 2.2 normalized DST matching.
