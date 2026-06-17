# In-Car Voice Assistant — Internal Evaluation Benchmark Spec (v1 draft)

**Status:** Design frozen. Intent ontology and statistical rigor now resolved into the body (§6.1, §5.1, §11, §8). Remaining scope items — latency, non-English locale, robustness track — are *decided as parked*, not open (§12, Future work). No open blockers.
**Date:** 2026-06-17
**Companion doc:** `recent_trend.md` (the modern-eval survey this spec draws on). Section references like *(trend §LLM-as-judge)* point there.

---

## 1. Goal & deliverable

Build an **internal** evaluation benchmark for an in-car voice assistant, plus a small demonstration of it running.

**Why internal, not public:** public benchmarks are either Type A (saturate in <2 yrs) or Type D (high overhead, external dependency), and are contaminated/too general for this product. An internal benchmark is **Type C (vendor-controlled)** *(trend §Saturation table)*.

**Known weakness of going internal (Type C):** "high risk of over-fitting; lack of independent verification." We design explicitly against this — see §9 (human-satisfaction validation anchor) and the multi-model discrimination check (§10).

---

## 2. System under test (SUT) & scope

- **Primary axis: command/control** ("mess with the car") — turn up AC, navigate, call, play music. Chosen because it is safety-relevant *and* yields **objective, verifiable ground truth** (right action+parameters or not).
- **Secondary axis: informational/chat** — weather, ETA, chit-chat. A wrong answer here does not endanger the driver, so it is lower priority.
- **Target = an off-the-shelf LLM wrapped in a car-assistant system prompt** (a proxy). No real vehicle required. Benchmarking *several* models also demonstrates the benchmark discriminates — partial defense against the "no independent verification" weakness.
- **Run across model *tiers*, not just frontier.** The shipped model is likely a cheaper/smaller one (frontier is expensive in production), so the benchmark's real job includes finding the smallest/cheapest model that still passes. Accuracy across tiers is measurable today; cost/latency tradeoffs are the eventual selection axis (latency itself parked — see §12).

---

## 3. Action representation & correctness (the agentic core)

Per *(trend §Agentic AI)*: task success must be verified by objective state, **not** model self-report ("state-outcome disconnect").

- **(B) Structured tool-call output** is the backbone: the model is given a fixed tool/intent schema and must emit a structured call (e.g. `set_climate(temp, zone)`). Scoring = compare emitted call to expected call.
- **(C) Thin simulated `car_state`** layered on **only** for context-dependent / multi-step cases (e.g. "make it warmer" depends on current temp; "play this video" depends on `vehicle_motion`). This is the post-condition-verification idea (Truveil-style) without building a real vehicle sim.

---

## 4. Test matrix (2×2)

|                         | **Single command**                      | **Context-based**                                    |
| ----------------------- | --------------------------------------- | ---------------------------------------------------- |
| **Command/control**     | one-shot action; intent+slot exact-match | depends on `car_state`/prior turns; **Joint Goal Accuracy** + per-turn |
| **Chat/informational**  | one-shot Q&A; faithfulness/relevancy     | follow-ups & references; completeness, retention, turn relevancy |

The matrix tooling is **asymmetric**: strong prior art exists for the command side (intent/slot schemas), little for the chat side (falls back to RAG + conversational metrics).

---

## 5. Metrics (command/control)

Decomposed, with redundancy removed (intent accuracy == tool-selection accuracy in a 1:1 intent→tool mapping, so only "intent accuracy" is kept):

- **Routing accuracy** — act vs. abstain. Reported with **false-activation rate** (acts on a non-command) and **false-rejection rate** (ignores a clear command) broken out. This is *not* the same as intent accuracy; it is where the safety failures live.
- **Intent accuracy** — right action, given it acted (exact match).
- **Slot accuracy** — right parameters (slot-level F1 / all-slots exact match).
- **Task Success Rate (TSR)** — all of the above correct end-to-end. **Headline number.**
- **Context-based cases** additionally use **Joint Goal Accuracy (JGA)** (MultiWOZ-style: entire accumulated state correct at each turn).

### 5.1 Statistical rigor

- **Power the headline, sample the sub-cells.** Target **~400 command/control cases** for the headline TSR → ±5% CI at p≈0.5 — enough to resolve model tiers, which typically differ 10–15% TSR. Per-intent / per-`ambiguity`-class / context sub-cells run **wide and descriptive** (~30–50 cases, ±~14%, flagged directional); scarce *hand-authored* budget goes to the high-value safety / `ambiguous` / `out_of_scope` cells, not happy-path padding. The 400-case human-verified authoring bill is a stated limit, not hidden.
- **Wilson score intervals** for every proportion (TSR, routing, false-activation/false-rejection) — good models sit at TSR ≈ 0.9+, where the normal approximation misbehaves (can exceed 1.0).
- **Model comparison is paired** — every model runs the identical case set. Command/control: compare TSR directly; significance via **McNemar's test** on the paired per-case outcomes. **No ranking model (no Elo / Bradley-Terry) on the objective quadrant** — it would discard the per-case ground truth we paid to author.
- **Chat/informational quadrant** is sized separately and smaller (judge cost), tied to the §9 human-validation sample (50–100). Its ranking uses Bradley-Terry — see §8.

---

## 6. Schema & data sourcing

- **Borrow the *schema design and ontology*, author *fresh* data.** This resolves a tension: importing public test *cases* (MASSIVE, MultiWOZ) would re-import the very contamination we went internal to avoid.
  - **Schema contract format:** Schema-Guided Dialogue (SGD) style — each domain = a schema of intents + slots with NL descriptions.
  - **Intent/slot ontology:** SLURP/MASSIVE (general assistant) ∩ MAC-SLU / AMIE (automotive: car control, navigation, music, climate, calls).
  - **Metric conventions:** intent acc + slot F1 (SLURP), JGA (MultiWOZ).
- **Case generation:**
  - **LLM-synthesized, human-verified** — generate utterance variations against the frozen schema. **Must use a different model family than the target** (avoids self-preference bias leaking into the data).
  - **Hand-authored** for adversarial / safety / ambiguous cases.
  - **No pure templating** — produces phrasing no real driver uses; makes the benchmark unrealistically easy.

### 6.1 Concrete v1 ontology (frozen)

Six command intents + two abstention labels. Exactly one schema tag — `stakes ∈ {low, high}`. Ambiguity is **not** in the schema; it is a per-case label (see §11).

| intent | slots | `stakes` | notes |
| --- | --- | --- | --- |
| `set_climate` | `temp` (°C; "warmer/cooler" → `defaultable` ±2°), `zone` (driver \| passenger \| all; default all) | low | silent-execute |
| `navigate` | `destination` | low | drastic reroute is **not** here — it depends on prior route/turns, so it lives in the context-based quadrant (§4), where `stakes` may escalate from `car_state` |
| `call_contact` | `name` | high | confirm-with-cancel |
| `play_media` | `title`, `artist`, `media_type` (audio \| video; default audio) | low | `media_type: video` + `vehicle_motion: moving` = hard-block case (warn + offer audio) |
| `adjust_volume` | `direction` (up \| down \| set), `amount` (`defaultable`) | low | silent-execute |
| `send_message` | `contact`, `body` | high | the **lone irreversible** intent → silent + wrong = worst cost cell (§11) |
| `none` | — | — | no actionable command (chit-chat, passenger talk, ambient); acting = **false activation** |
| `out_of_scope` | — | — | real command for an absent capability ("open sunroof"); acting = **capability hallucination** — a distinct gold label from `none` |

The two soft "high-attention" cases §11 once listed (read a long email, list many results) are **not** new intents — they fall to the chat quadrant's **conciseness** dimension (summarize / give top 3), and become context-based chat cases where `vehicle_motion: moving` raises conciseness weight over completeness. Only the **hard** blocks (video while moving, needs-visual-selection → defer to parked) remain genuinely safety-specific.

---

## 7. Input conditions (testing NLU, not ASR)

Three distinct things, kept separate:

1. **ASR quality** (speech→text, WER, audio) — **out of scope**, a separate benchmark.
2. **NLU accuracy** (clean text in) — **the core benchmark.** The 2×2 lives here. Primary, unconfounded numbers.
3. **NLU robustness to noisy input** (error recovery from imperfect transcripts) — **optional, separately reported track.** Same cases, perturbed input, scored as a **delta** from the clean baseline. Never blended into core numbers.

Robustness track, if built, borrows the **Noise-LLM** perturbation taxonomy (character / word / sentence level; single + mixed) — pure text transforms, no audio. Justification for having it at all: recent SLU work shows clean-only scores **overstate** real-world reliability.

Code-switching (e.g. Thai↔English) is parked with locale (see §8) — noted as a natural fit for this track later.

---

## 8. Chat/informational scoring & locale

- **(C) Objective-by-construction for the bulk** — restrict informational cases to ones with verifiable answers (ETA, fuel low, factual lookup) → exact-match / faithfulness vs. a provided fact.
- **(B) Pairwise cross-family LLM judge for the open tail only** — the judge is shown two models' answers and picks the better; head-to-heads are aggregated with **Bradley-Terry** (not Elo — Elo's match-order dependence is a defect for a re-runnable benchmark; BT fits all comparisons jointly, order-independent, with bootstrap CIs). Guards are **mandatory** because pairwise *amplifies* verbosity bias: **CoT-forced critique before the verdict**, **length normalization**, and a judge from a **different family than the target**. Dimension-wise diagnostics (faithfulness, relevancy, conciseness) are still elicited *inside* the critique to keep the per-dimension §9 correlation alive. Avoid bare scalar judging (trend §LLM-as-judge documents why it's unreliable).
- **Locale (v1): English-only.** Chosen for better model performance and more prior art. Cultural/locale style variation (e.g. Thai users prefer terse answers — which *collides* with the judge's verbosity bias) is **parked as future work**, documented as an assumption. See memory `locale-aware-eval-style`.

---

## 9. Human satisfaction = validation anchor (not the live score)

- Automated metrics (§5, §8) are the benchmark you run constantly.
- Human satisfaction is collected **once, on a ~50–100 case sample**, and used to check the automated scores **correlate** with human judgment (and judge↔human agreement, LongJudgeBench-style).
- This is the **independent verification** that defends against the Type C over-fitting weakness. If automated tracks human, the benchmark is trusted to run at scale without humans.
- **Decompose satisfaction; never use one blended scalar.** Validate each automated dimension against the *matching* human dimension (correctness↔correctness, conciseness↔conciseness).
- **Correctness is a hard gate and dominates.** A likeable, well-toned response that performs the *wrong* action is a failure. Style/tone/conciseness are the secondary, subjective axis.
- **Human-anchor format must match the automated judge's format.** Command/control human ratings are *absolute* (matching the objective TSR scores). The chat dimension's human validation must be **pairwise** (humans pick A vs B), because the chat judge is pairwise (§8) — otherwise judge↔human agreement is uncomputable.

---

## 10. Persona

- **Persona is a fixed, predefined constant**, measured via **Role Adherence** *(trend multi-turn metrics)*. The benchmark measures *adherence*, it does not *tune* the persona.
- v1 persona spec (recommended): **safety-first, concise, calm, minimal unsolicited chit-chat, no long monologues while the car is moving.**
- Changing the persona is a **product/RLHF decision** outside the benchmark. If human-satisfaction data says the persona should change → re-spec → re-freeze → re-measure (closed loop *around* the benchmark, not a knob inside it).

---

## 11. Safety model

**Framing correction:** a voice assistant is **not** a safety-critical control system like autonomous driving. The user has authority over their own car. Broad task-**refusal is paternalism** and works against the product. The real safety axis is **driver attention** (eyes on road, hands on wheel) — the rationale behind regulatory driver-distraction guidelines (e.g. NHTSA's).

**Response-mode taxonomy (4 + 1):**
1. **Execute silently** — for low-stakes/reversible actions (volume, climate, skip track).
2. **Confirm-with-cancel / announce** — for high-stakes/irreversible actions (call, send message, payment, drastic reroute). Safe because the driver can cancel by voice, eyes-free.
3. **Clarify first** — for ambiguous commands (doesn't act yet).
4. **Wrong execution** — the failure outcome.
5. *(narrow footnote)* **Blocked-while-moving** — legally/system-restricted (e.g. video on driver screen). Not a primary mode.

**Cost function keyed on recovery / attention cost** (the real safety link = how much driver attention an error steals to fix; irreversibility is just the unrecoverable extreme):
- **Worst:** silent + wrong on the one irreversible intent (`send_message`).
- **Correct:** confirm-with-cancel on high-stakes; silent-execute on trivial.
- **Small UX penalty (not safety):** over-confirming a trivial action.
- **Wrong-but-cancelable ≪ wrong-and-irreversible.**

**Mechanisms:**
- **One schema tag — `stakes ∈ {low, high}` per intent** (§6.1) — is the sole driver of expected mode. `reversible` is **not** a schema axis: true irreversibility holds for exactly one v1 intent (`send_message`), so it is a single cost-table special case (silent + wrong on `send_message` = worst cell), not a near-constant column.
- **Ambiguity is a per-case authored label `∈ {clear, defaultable, ambiguous}`** — a property of *utterance × `car_state`*, not of the intent. For `defaultable` cases the sensible default value is stored in the gold record so slot-scoring can verify the model applied it.
- **Expected mode is a *total* function `f(stakes, ambiguity)`:** `clear` / `defaultable` → **act** (defaultable acts with the gold default); `ambiguous` → **clarify**. Orthogonally: `stakes = high` → confirm-with-cancel; `stakes = low` → silent-execute.
- **Confirmation calibration** is a reported metric — penalize both under-confirming (high-stakes fired silently) and over-confirming (nagging on trivial actions). "Knows when to ask."
- **Scoring by ambiguity class:** clarify on `ambiguous` = full credit; clarify on `clear` = soft over-abstention penalty; clarify on `defaultable` = small UX penalty (nagging on a defaultable slot); act on `ambiguous` = penalty **scaled by `stakes`** (guessing which contact to *call* ≫ which station to *route* to). Every over-abstain / over-confirm penalty stays far above a wrong execution.
- **Eyes-free / modality flag** (in scope): does the response let the driver stay eyes-free, or demand visual selection?

**Blocked-while-moving / high-attention requests — expected behavior is warn + safe alternative, NOT flat refuse and NOT silent unsafe compliance:**
- Hard-blocked (video while moving): **explain + offer alternative** ("can't play video while moving — want just the audio?").
- Soft / high-attention (read 600-word email, list 40 restaurants): **do it eyes-free** — read top result by voice, offer to continue.
- Needs visual interaction: **offer to defer** ("I'll pull it up when you're parked").
- Gated on a **`vehicle_motion: moving | parked`** field in `car_state` → these are **context-based cases** (same utterance, different correct answer per state). Reward warn+alternative/adapt; penalize silent-unsafe-comply **and** dead-end-refuse.

---

## 12. Future work (parked — *decided* out of v1, not open)

All structural design items are resolved: ontology → §6.1; safety tags / mode / ambiguity → §11; statistical rigor → §5.1; chat ranking → §8. What remains below is deliberately scoped out of v1, each with a documented trigger to revisit. **No open blockers.**

1. **Latency & cost.** *Why it matters:* the deployed model is likely a cheaper/smaller one (frontier is too expensive in production), so latency + cost are real model-selection criteria, and a slow/silent response has a driver-attention cost (driver looks down to check it heard). *Why parked:* a text-LLM proxy only yields *model-inference* latency, not end-to-end (`wake-word + ASR + LLM + tool exec + TTS + network`), so it can't faithfully represent the deployed experience without the real environment. *When revisited:* measure inference-only P50/P95/P99 *(trend §Operational envelopes)* across model tiers as a caveated component metric; full end-to-end belongs with the real-pipeline future work. The surviving actionable half — running the benchmark across model tiers — is folded into §2.
2. **Non-English locale & cultural style.** English-only in v1 (better model performance, more prior art — §8). *When revisited:* encode the target locale's style preference in the pairwise judge rubric + length normalization so the judge's verbosity bias can't penalize the terse answers some locales prefer. See memory `locale-aware-eval-style`.
3. **NLU robustness-to-noise track** (§7) and **code-switching** (Thai↔English). Optional separate track using the Noise-LLM perturbation taxonomy, reported as a delta from the clean baseline — never blended into core numbers.

---

## Sources (prior art)
- MAC-SLU (automotive cabin SLU) — arXiv 2512.01603
- MASSIVE / SLURP — arXiv 2204.08582; github.com/alexa/massive
- Schema-Guided Dialogue (SGD) — AAAI 2020
- MultiWOZ — multi-turn task-oriented dialogue (Joint Goal Accuracy)
- AMIE / AV passenger intent — arXiv 1904.10500
- Noise-LLM robustness framework — arXiv 2310.06504; github.com/dongguanting/Noise-Slot-Filling-LLM
- ASR-robust SLU (word confusion networks) — arXiv 2401.02921
