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
| Joint Goal Accuracy for multi-turn | MultiWOZ | `dialogue.score_dialogue` JGA |
| Wilson intervals + paired significance | (stats best practice) | `stats.py` |

## Gaps worth closing (prioritized)

| # | Gap | Standard says | We currently | Effort |
| --- | --- | --- | --- | --- |
| 1 | **Categorical values not enumerated/validated** | SGD: each slot has `is_categorical` + `possible_values`; categorical values must come from that list | hardcode `CATEGORICAL_SLOTS` in code; don't reject `zone="backseat"` etc. | low |
| 2 | **JGA uses raw exact-match** | MultiWOZ 2.2: non-categorical slots in the belief state use the same normalized matching | `score_dialogue` compares dicts with `==`, *not* our `slots_match` — inconsistent with the standard we just adopted | low |
| 3 | **No value canonicalization** | MultiWOZ canonicalizes numbers/times/units before matching ("8pm"→"20:00"); we saw "68°F"→20°C and "fifteen minutes" | only lowercase/punct/article strip; numerics/units uncanonicalized | medium |
| 4 | **Binary slot-value scoring** | SLURP **SLU-F1**: slot-label F1 weighted by word/char **edit distance** on the value — partial credit for near-misses | non-cat value match is all-or-nothing | medium |
| 5 | **`clarify` doesn't say which slot** | SGD `requested_slots`: the system requests the specific missing slot | `clarify` is a bare mode; we don't score *what* it should ask for | medium |
| 6 | **Span grounding** | SGD/MultiWOZ 2.2: non-cat values are spans from the utterance (limits hallucinated values) | gold non-cat values are free strings, not utterance spans | low-med |

## Deliberately N/A

| Convention | Why not |
| --- | --- |
| Inform/Success split (MultiWOZ) | "Inform" presumes a DB of entities to suggest; we have no DB. Our **TSR ≈ Success** (goal achieved); the chat quadrant's faithfulness-vs-fact is the closest "inform". (Document the mapping.) |
| Unseen-service / zero-shot generalization (SGD's headline) | We benchmark one fixed schema, not transfer to unseen APIs. |
| Dialogue-act ontology (ISO 24617-2 / MultiWOZ acts) | Our response modes (execute/confirm/clarify/warn) are a safety taxonomy keyed on driver attention, not general dialogue acts. Partial mapping: clarify↔request, confirm↔confirm. |

## Recommended order

Close **#2 then #1** first — both low-effort and they remove real inconsistency/guesswork (JGA should use the matcher we already built; categorical values should be schema-defined and validated). Then **#3** (canonicalization) since we've already hit it in real data. #4–#6 are deepenings to weigh later.
