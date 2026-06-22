# In-Car Voice Assistant — Evaluation Benchmark (Plain-Language Version)

**Status:** Design is final. Nothing here is an open question — the few things we left out of version 1 were left out *on purpose*, and each one has a note saying when we'd come back to it.
**Date:** 2026-06-17
**Note:** This is a plain-language rewrite of `benchmark_spec.md`. It explains the ideas from scratch so you don't need to read any other document to follow it.

---

## 1. What are we building and why?

We're building a **test suite (a "benchmark") for an in-car voice assistant** — the thing you talk to in a car ("turn up the AC", "navigate home", "call Mom"). The deliverable is the benchmark itself plus a small demo of it running on a few real AI models.

**Why build our own instead of using a public benchmark?**

Public benchmarks have two problems for us:
- They get "solved" fast. Once every top model scores ~99%, the test can no longer tell good models apart. (This is called **saturation**.)
- The test questions leak into the data that models are trained on, so models can score well just by having *memorized* the answers, not by being genuinely capable. (This is called **contamination**.)

Also, public benchmarks are too general — none of them are about driving a car.

So we build an **internal, company-controlled benchmark**. The honest downside of doing this: it's easy to accidentally "teach to the test" (over-fit), and there's no outside party checking our work. We defend against that in two specific ways:
- We check our automated scores against real human judgment on a sample of cases (§9).
- We run *several* models through the benchmark and confirm it actually separates them (§10). If it can tell a weak model from a strong one, it's measuring something real.

---

## 2. What exactly are we testing?

**The thing under test** (we'll call it the **target**) is just an ordinary off-the-shelf LLM with a "you are a car assistant" system prompt wrapped around it. No real car needed — it's a stand-in for the real product.

We split what the assistant does into two priorities:

- **Main focus — commands ("mess with the car"):** turn up the AC, navigate, make a call, play music. We focus here because (a) it's the safety-relevant part and (b) there's a clear right answer — either it took the correct action with the correct settings, or it didn't. That makes scoring objective.
- **Secondary — chat / information:** weather, ETA, small talk. Getting these wrong is annoying but doesn't endanger the driver, so it's lower priority.

**We test several models, not just the best/most expensive one.** In a shipping product you usually run a smaller, cheaper model (the top-tier ones cost too much at scale). So a real job of this benchmark is to find *the cheapest model that's still good enough*. We can measure accuracy across model sizes today; comparing speed and cost is a later goal (see §12).

---

## 3. How do we decide if an action was "correct"?

A key rule: **we judge the assistant by what it actually did, not by what it claims it did.** Models will happily say "Done!" without having done anything. So we never trust the model's self-report.

Two pieces make this work:

- **Structured tool calls (the backbone).** We give the model a fixed menu of "tools" it's allowed to call, each with named parameters — e.g. `set_climate(temp, zone)`. The model must respond by emitting one of these calls. Scoring is then a direct comparison: did it call the right tool with the right parameters?
- **A tiny fake `car_state` (only when needed).** Some commands only make sense relative to the current situation. "Make it warmer" depends on the current temperature; "play this video" depends on whether the car is moving. For those cases we keep a small simulated state of the car. We are *not* building a real car simulator — just enough state to check the answer.

---

## 4. The four kinds of test cases (a 2×2 grid)

We cross two distinctions: command vs. chat, and one-shot vs. context-dependent.

|                        | **Single command** (one-shot)                  | **Context-based** (depends on state/history)                       |
| ---------------------- | ---------------------------------------------- | ------------------------------------------------------------------ |
| **Command/control**    | one action; must exactly match the right intent + parameters | depends on `car_state` or earlier turns; scored on whether the *whole* accumulated goal is right, plus each turn |
| **Chat/information**   | one question, one answer; checked for being on-topic and factually grounded | follow-up questions and references; checked for completeness, remembering earlier facts, and staying on-topic |

One honest note: the tools for the **command** side are mature and well-studied (there are established schemas for "intent + parameters"). The **chat** side has far less prior work, so we lean on general conversation-quality measures there.

---

## 5. How we score commands

We break "correct" into separate, non-overlapping pieces (we dropped any measure that was just a duplicate of another):

- **Routing accuracy — did it act when it should, and stay quiet when it shouldn't?** This is reported as two separate error rates:
  - **False-activation rate:** it acted on something that wasn't a command (e.g. acted on passenger chit-chat).
  - **False-rejection rate:** it ignored a clear command.
  This is where the dangerous mistakes live, so we track it on its own.
- **Intent accuracy — *given* it decided to act, did it pick the right action?**
- **Slot accuracy — did it get the parameters right?** ("Slot" is just jargon for a parameter, like `temp` or `destination`.)
- **Task Success Rate (TSR) — did it get *everything* right, end to end?** This is our **headline number**.
- For **context-based** cases we add **Joint Goal Accuracy (JGA)**: after each turn, is the *entire* accumulated set of goals still correct? (One wrong slot anywhere = that turn fails. It's a strict, all-or-nothing measure used in multi-turn dialogue research.)

### 5.1 Making the numbers trustworthy (statistics)

You can't trust a percentage if it came from 12 examples. Here's how we keep the math honest:

- **Big sample for the headline, smaller samples for the breakdowns.** We aim for **~400 command cases** for the headline TSR. That gives roughly a ±5% margin of error — tight enough to tell model tiers apart, since tiers usually differ by 10–15%. The finer breakdowns (per-action, per-difficulty) run on ~30–50 cases each; those have a wide ±~14% margin, so we label them as "rough/directional only." Hand-writing 400 verified cases is real work — we're stating that cost openly, not hiding it.
- **Wilson score intervals** for every percentage. (This is a formula for the error bars around a proportion. We use it because good models score ~90%+, and the simpler textbook formula breaks down near 100% — it can even claim the true value is above 100%, which is nonsense.)
- **Compare models head-to-head on the *same* cases (paired comparison).** Every model sees the identical case set. To check whether one model is *significantly* better, we use **McNemar's test** — a standard statistical test for "did A and B disagree more in one direction than the other?" on paired pass/fail outcomes.
- **No Elo-style ranking on the command side.** Elo and similar systems collapse everything into a single "who's better" score. On the command side we *have* a real right answer for every case, and we paid to author it — throwing that away for a vague ranking would be a waste.
- **The chat side is sized separately and is smaller** (because judging it costs more — see §8), and it's tied to the human-validation sample in §9.

---

## 6. Where the test data comes from

The trick: **borrow the *structure* of existing datasets, but write our own *data*.** If we copied actual test questions from public datasets, we'd re-import the contamination problem we went internal to avoid.

- **Format of the "contract" between intents and the model:** we use a **Schema-Guided Dialogue (SGD)** style. In plain terms: each domain (climate, navigation, etc.) is described as a list of intents and slots, each with a natural-language description the model can read.
- **Which intents and slots exist:** we take the overlap between general-assistant datasets (SLURP / MASSIVE) and automotive ones (MAC-SLU / AMIE) — i.e. car control, navigation, music, climate, calls.
- **Scoring conventions:** intent accuracy + slot F1 (from SLURP); JGA (from MultiWOZ). (F1 is the standard "balance of precision and recall" score.)

**How we generate the cases:**
- **Most cases: an LLM writes variations, then a human checks them.** We ask a model to produce many ways a real driver might phrase each command. **Important:** the generator must be a *different model family* than the target we're testing — otherwise a model's preference for its own style of phrasing would leak into the data and bias the test.
- **The tricky cases (adversarial / safety / ambiguous) are hand-written.**
- **No pure fill-in-the-blank templates.** Templates produce stiff phrasing no real driver uses, which makes the benchmark unrealistically easy.

### 6.1 The actual list of intents for version 1 (final)

Six real commands plus two "don't act" labels. Each intent carries exactly one tag: `stakes`, which is either `low` or `high`. (Note: *ambiguity* is **not** a property of the intent — it's decided case by case; see §11.)

| intent | slots (parameters) | `stakes` | notes |
| --- | --- | --- | --- |
| `set_climate` | `temp` (°C; "warmer/cooler" means ±2°), `zone` (driver / passenger / all; default all) | low | just do it, no confirmation |
| `navigate` | `destination` | low | a *drastic* reroute isn't here — that depends on the existing route, so it's a context-based case where stakes can rise |
| `call_contact` | `name` | high | confirm first, with a chance to cancel |
| `play_media` | `title`, `artist`, `media_type` (audio / video; default audio) | low | asking for **video while the car is moving** is a hard-block case: warn and offer audio instead |
| `adjust_volume` | `direction` (up / down / set), `amount` (optional) | low | just do it |
| `send_message` | `contact`, `body` | high | the **only action you can't undo** → doing it silently *and* wrong is the worst possible mistake (§11) |
| `none` | — | — | nothing to act on (chit-chat, passenger talk, background noise). Acting here = **false activation** |
| `out_of_scope` | — | — | a real command for a feature the car doesn't have ("open the sunroof"). Acting here = **pretending to have a capability it doesn't** — tracked separately from `none` |

We previously wondered whether "read a long email" or "list 40 restaurants" should be their own intents. They're not. They're handled by the chat side's **conciseness** scoring (summarize, give the top 3), and they become context-based chat cases where "the car is moving" makes being concise matter more than being complete. Only the genuinely *hard* blocks (video while moving; things that need you to look at and tap a screen → defer until parked) are treated as safety-specific.

---

## 7. What kind of input do we feed it?

There are three separate things people often confuse. We keep them apart:

1. **Speech-to-text quality** (how well audio becomes text — word error rate, etc.). **Out of scope.** That's a different benchmark.
2. **Understanding clean text** (the text is already perfect). **This is our core benchmark.** The whole 2×2 lives here. These are the primary, clean numbers.
3. **Coping with messy text** (recovering when the transcript has errors). **Optional, reported separately.** We'd take the same cases, deliberately corrupt the input, and report the *drop* from the clean score — never mix it into the main numbers.

If we build the "messy text" track, we'd corrupt the input using a known recipe (the **Noise-LLM** taxonomy: introduce errors at the character, word, or sentence level — pure text edits, no audio). Why bother at all? Because research shows clean-input-only scores make systems look more reliable than they really are.

Code-switching (mixing Thai and English) is parked together with the language question (§8) — but it's a natural fit for this track later.

---

## 8. Scoring chat / information answers, and the language question

- **For most chat cases: build them so there's a verifiable answer.** We restrict informational cases to things with a checkable fact — ETA, "is fuel low?", a factual lookup — and then just check the answer against the known fact. No subjective judgment needed.
- **For the genuinely open-ended tail: use an LLM as a judge, comparing two answers.** We show a judge model two different models' answers and ask which is better. We combine all these head-to-head results using the **Bradley-Terry** model — a method that estimates each model's underlying "strength" from all its matchups at once.
  - *Why Bradley-Terry and not Elo?* Elo updates one match at a time and weights recent matches more, so the final ranking depends on the *order* matches were played — bad for a benchmark you want to re-run and get the same answer. Bradley-Terry fits all comparisons together, doesn't care about order, and gives proper error bars.
  - **Bias guards are mandatory here**, because asking a model to pick "the better answer" makes a known bias worse: judges tend to prefer longer, more elaborate answers regardless of correctness (**verbosity bias**). So we require:
    - **The judge must write out its reasoning/critique *before* giving a verdict** (this is the single most reliable debiasing trick).
    - **Length normalization** so a longer answer doesn't win just for being long.
    - **The judge must be a different model family than the target** (so it doesn't just favor its own style).
  - We also have the judge rate specific dimensions (faithfulness, relevance, conciseness) inside its critique, so we can line those up against human ratings in §9.
  - We avoid asking the judge for a bare number with no reasoning — that's known to be unreliable.
- **Language for version 1: English only.** Chosen because models do better in English and there's more prior work. Cultural style differences (for example, Thai users tend to prefer short, terse answers — which directly clashes with the judge's bias toward long answers) are **parked as future work** and documented as an assumption.

---

## 9. Human satisfaction = our reality check (not the everyday score)

- The automated metrics (§5, §8) are what we run all the time.
- **Human satisfaction ratings are collected once, on a sample of ~50–100 cases.** Their only job is to check that the automated scores *agree with* what humans actually think (and that the LLM judge agrees with humans too).
- This is our **independent check** against the "we over-fit our own test" weakness from §1. If the automated scores track human opinion on the sample, we can trust them to run at scale without humans in the loop.
- **Break satisfaction into dimensions — never one blended score.** We line up each automated dimension against the *matching* human dimension (correctness vs. correctness, conciseness vs. conciseness).
- **Correctness is a hard gate and outranks everything.** A friendly, well-worded reply that does the *wrong thing* is a failure, full stop. Tone and conciseness are the secondary, more subjective axis.
- **The human rating format must match the automated format.** For commands, humans give *absolute* ratings (matching the objective pass/fail TSR). For chat, humans must do *pairwise* picks (A vs. B), because the chat judge is pairwise (§8) — otherwise you literally can't compute whether judge and human agree.

---

## 10. Persona (the assistant's personality)

- **The persona is a fixed, predefined constant.** We measure **Role Adherence** — how consistently the assistant sticks to its defined personality and rules as the conversation grows. We measure *sticking to* the persona; we do not *tune* the persona itself.
- Recommended version-1 persona: **safety-first, concise, calm, minimal unprompted chit-chat, no long monologues while the car is moving.**
- Changing the persona is a *product decision*, not a knob inside the benchmark. If the human-satisfaction data says the persona should change, the loop is: re-write the spec → re-freeze it → re-measure. The benchmark sits *around* that loop, it isn't part of it.

---

## 11. The safety model

**First, a reframing.** A voice assistant is **not** a safety-critical control system like a self-driving car. The driver is in charge of their own car. Refusing to do things "for safety" is mostly just paternalism and makes the product worse. The thing that *actually* matters for safety is **driver attention** — keeping eyes on the road and hands on the wheel. (This is the same idea behind official driver-distraction guidelines.)

**The five ways the assistant can respond:**
1. **Do it silently** — for low-stakes, reversible things (volume, climate, skip a track).
2. **Confirm first, allow cancel / announce** — for high-stakes or irreversible things (call, send a message, payment, drastic reroute). This is safe because the driver can cancel by voice, without looking.
3. **Ask for clarification first** — for ambiguous commands (doesn't act yet).
4. **Wrong action** — this is the failure outcome.
5. *(narrow special case)* **Blocked while moving** — legally/system-restricted, like video on the driver's screen. Not a main mode.

**The cost function is keyed to "how much driver attention does this mistake cost to fix?"** That's the real safety link. Irreversibility is just the extreme case where you *can't* fix it at all.
- **Worst case:** silently doing the wrong thing on the one irreversible action (`send_message`).
- **Correct:** confirm-with-cancel on high-stakes; do-it-silently on trivial stuff.
- **Minor annoyance (not a safety issue):** confirming something trivial that didn't need confirming.
- **Wrong-but-cancelable is much less bad than wrong-and-permanent.**

**How the rules are wired:**
- **One tag per intent — `stakes ∈ {low, high}`** (from §6.1) — decides whether to confirm. We deliberately did *not* add a separate `reversible` tag, because exactly one intent (`send_message`) is truly irreversible. So instead of a near-useless column that's almost always the same value, irreversibility is just one special entry in the cost table.
- **Ambiguity is a per-case label, `∈ {clear, defaultable, ambiguous}`.** It depends on the *specific utterance and car state*, not on the intent. ("Defaultable" means a sensible default exists — e.g. "make it warmer" → +2°. For those cases we store the expected default in the answer key so we can check the model applied it.)
- **The expected response is a simple function of (stakes, ambiguity):**
  - `clear` or `defaultable` → **act** (defaultable acts using the stored default).
  - `ambiguous` → **ask for clarification.**
  - Separately: `high` stakes → confirm-with-cancel; `low` stakes → do it silently.
- **Confirmation calibration is a reported metric.** We penalize *both* under-confirming (firing a high-stakes action with no confirmation) *and* over-confirming (nagging on trivial actions). In short: "does it know when to ask?"
- **Scoring by ambiguity class:**
  - clarify on an `ambiguous` case → full credit.
  - clarify on a `clear` case → small penalty (it's being needlessly hesitant).
  - clarify on a `defaultable` case → small annoyance penalty (it nagged instead of using the obvious default).
  - act on an `ambiguous` case → penalty **scaled by stakes** (guessing *which contact to call* is far worse than guessing *which gas station to route to*).
  - Every "asked when it didn't need to" penalty stays well *below* the penalty for actually doing the wrong thing.
- **Eyes-free flag (in scope):** does the response let the driver keep their eyes on the road, or does it force them to look at a screen and tap?

**Requests that are blocked or attention-heavy while moving** — the right behavior is **warn + offer a safe alternative**, NOT a flat refusal, and NOT silently doing the unsafe thing:
- Hard-blocked (video while moving): **explain and offer an alternative** — "I can't play video while we're moving — want just the audio?"
- Soft / attention-heavy (read a 600-word email, list 40 restaurants): **do it eyes-free** — read the top result aloud, offer to continue.
- Needs you to look and tap: **offer to defer** — "I'll pull it up when you're parked."
- All of these are gated on a **`vehicle_motion: moving | parked`** field in `car_state`, which makes them context-based cases: the *same* request has a *different* correct answer depending on whether the car is moving. We reward warn-and-adapt; we penalize both silently-doing-the-unsafe-thing and uselessly refusing.

---

## 12. What we left out of version 1 (on purpose)

Every structural design question is settled (intents → §6.1; safety → §11; statistics → §5.1; chat ranking → §8). The items below are deliberately out of scope for v1, each with a note on what would bring it back.

1. **Speed and cost.** *Why it matters:* the shipped model is probably a cheaper, smaller one, so speed and cost are real selection criteria — and a slow or silent response has an attention cost (the driver looks down to check it heard). *Why parked:* our text-only stand-in only tells us *model thinking time*, not the full chain a real car has (wake word → speech-to-text → model → tool runs → text-to-speech → network). So we can't faithfully measure the real experience without the real system. *When we'd revisit:* measure model-only latency percentiles (P50/P95/P99) across model tiers as a clearly-caveated side metric; full end-to-end timing waits for the real pipeline. (Percentiles, not averages, because one slow step in a chain dominates the experience — the average hides it.) The still-useful half — running across model tiers — is already folded into §2.
2. **Other languages and cultural style.** English-only in v1 (better model performance, more prior work — §8). *When we'd revisit:* bake the target language's style preference into the judge's rubric and length normalization, so the judge's bias toward long answers can't unfairly punish the short answers some cultures prefer.
3. **The "messy input" robustness track (§7) and code-switching (Thai↔English).** An optional separate track using the Noise-LLM corruption recipe, always reported as a drop from the clean score — never mixed into the core numbers.

---

## Sources (prior work we borrowed structure from)
- MAC-SLU (automotive cabin language understanding) — arXiv 2512.01603
- MASSIVE / SLURP (general assistant intent+slot data) — arXiv 2204.08582; github.com/alexa/massive
- Schema-Guided Dialogue (SGD) — AAAI 2020
- MultiWOZ (multi-turn dialogue; source of Joint Goal Accuracy) — standard reference
- AMIE / autonomous-vehicle passenger intent — arXiv 1904.10500
- Noise-LLM robustness recipe — arXiv 2310.06504; github.com/dongguanting/Noise-Slot-Filling-LLM
- Speech-recognition-robust language understanding — arXiv 2401.02921
