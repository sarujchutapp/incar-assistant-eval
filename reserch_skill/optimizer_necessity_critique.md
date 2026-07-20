# Is Prompt/Skill Optimization Worth It? — A Skeptical Case

A debate log. The skeptic's argument (that tools like SkillOpt / DSPy optimizers are unnecessary and sub-optimal for our setting) followed by the assessment — where the argument holds, where it overreaches, and the experiment that would settle it. Grew out of the framing in `slm_agent_research_directions.md` and `dspy_overview.md`.

_Last updated: 2026-07-17._

## The thesis

> The meta-prompts in SkillOpt and every DSPy optimizer are **hand-crafted by researchers**. Given that, using these tools is largely **unnecessary and sub-optimal** — for a single-domain product you're better off hand-writing one controllable skill with community guidance (e.g. Matt Pocock's *writing-great-skill*).

## The argument (skeptic's case)

1. **Static meta-prompt vs moving models.** Target and optimizer models upgrade constantly, but the hand-written meta-prompt stays static — so the "how to improve" never adapts to the models it drives.
2. **Score-only, benchmark-bound.** It optimizes purely on a score, and that score is dictated by a benchmark — which goes stale quickly (saturation, contamination, drift).
3. **Blind to model-specific limits.** It doesn't really understand compact wording, the target's context window, or token budget for a given model.
4. **Seed-bound.** The result is limited by the initial seed, which is human-written. (Proven here: a seed change flipped our run verdict — see `docs/experiments/`.)
5. **Marginal, with collateral risk.** If you already have a really good prompt, the tool only squeezes a fraction of a percent — and that squeeze can cost length or generalization.
6. **Circularity.** If the meta-prompt is ultimately human-authored anyway, why not just write the skill ourselves with a good guide?
7. **Seed-blindness cuts both ways.** The "humans don't hold the failure distribution" defense of optimization applies equally to writing the initial seed — the seed is written blind to failures too.
8. **The untested regime** (stated precisely — the imprecise version is wrong). It is **not** true that these tests only compare against an empty prompt: SkillOpt reports *seven* baselines (`no-skill`, `human-skill`, `one-shot LLM-skill`, `Trace2Skill`, `TextGrad`, `GEPA`, `EvoSkill`), and even `no-skill` is *"the frozen target model run with the benchmark's **default system prompt**,"* not a blank. The defensible gap is narrower and airtight: **the optimizer is never *seeded* from a strong human prompt.** The expert prompt appears only as a *separate standalone baseline*, so there is no result of the form *"take a good prompt → optimize → show it improved."* That specific cell is missing.
9. **Rebuttal to the claimed use cases:**
   - *Reproducibility / fair comparison* → weak-to-no impact.
   - *Cheap re-adaptation on drift* → barely happens; hand-tuning suffices.
   - *Scale / many tasks* → irrelevant for a single-domain product.
   - *Rule discovery* → a community writing guide does it as well or better.
   - *SLM limits humans can't grasp* → conceded as a plausible use case.
10. **Complexity / controllability.** One version-controlled hand-crafted artifact beats a pipeline of {seed + meta-prompt + target model + optimizer model + gate + splits + rejected buffer}. (Aligns with our own `CLAUDE.md` "Simplicity First".)
11. **Few-shot is an unreliable lever on SLMs.** DSPy's demo-based optimizers (`BootstrapFewShot`, MIPROv2's demo half) lean on in-context learning, whose reliability *scales with model size* — small models do ICL worse and noisier. So the demo machinery is a weak, context-expensive lever exactly where we care (SLM), reinforcing that the tools' general-agent value is thin.

**Conclusion of the case:** these tools are **unnecessary for a general AI-agent** you author and maintain by hand; the only regime that genuinely survives is **SLM**, where some limitations are hard for a human to grasp.

## Assessment — where it holds, where it overreaches

**Conceded (the argument is right):**

- **#7 seed-blindness** is correct and it reframes the whole debate. The seed *is* written blind to failures, so the real axis is not *optimize vs. don't* but **automated loop vs. manual loop**. A human *can* close the loop by hand — read failures, revise, re-test — and at a small, human-tractable corpus (~70–400 cases) the manual loop is not only feasible but often *better* (judgment, taste, catching verifier-gaming). Automation only wins when the loop is too big to run by hand.
- **#8 the untested regime** — confirmed against the paper. SkillOpt is always seeded from a *generic* skill (the paper describes initial skills as "a one-liner or a paragraph"; the ALFWorld seed as "a generic household plan"). The expert **human skill is a separate standalone baseline, never SkillOpt's starting point.** So the paper shows *generic-seed→optimized* beats *human-skill-standalone*, but **never** *good-seed→optimized* vs *good-seed-as-is*. The claim the critique hinges on is an **unmet burden of proof**, not a settled win.
- **What the "expert" baseline actually is** — the paper defines `human skill` only as *"an expert-written skill document curated per benchmark"* (§4, Baselines), and separately notes *"human skills are already 145–516 tokens long ... yet they are beaten in every direct-chat model row while the learned artifacts remain compact (Table 6)"* (§4.2). No detail on who authored them, the effort, or whether any authoring methodology (à la Matt Pocock) was used. So "SkillOpt beats the expert skill" is weaker than it sounds: the baseline may be a *modest, short* expert draft, and it was never used as a seed. Beating it ≠ beating a best-effort hand-authored prompt.
- **Finding: it out-*lengths* the human skill to beat it.** Cross-referencing Table 6 (§4.4) against the human-skill range (§4.2):

  | | Tokens |
  | --- | --- |
  | Human "expert" skill (beaten) | **145–516** |
  | SkillOpt final skill | **379–1,995** (median ≈ 920): SearchQA 857, SpreadsheetBench 1,995, OfficeQA 883, DocVQA 959, LiveMath 379, ALFWorld 1,321 |

  SkillOpt's deployed skill is typically **~2–4× the length** of the expert baseline it beats (e.g. SpreadsheetBench 1,995 vs ≤516; DocVQA 959 vs ≤516). So a real part of the "win" is just **being more comprehensive** — more procedural rules, more tokens — than a short human draft. The paper hedges this as *"not simply prompt length"* (§4.2), but *"not simply length"* ≠ *"not length at all."* **Credibility consequence:** if SkillOpt wins largely by covering rules a 145–516-token draft omitted, then the "expert-written" label is doing heavy lifting for a **short, possibly strawman baseline** — and the fair comparison (a longer, best-effort, failure-annotated hand-authored skill) was never run. This *undercuts* the "beats expert" headline, not just the "optimizes-a-good-seed" one.
- **#11 few-shot on SLMs** — correct. In-context learning reliability scales with model size (the "emergent" framing was contested by Schaeffer 2023, but the *empirical* weakness holds). Demos help SLMs mainly for **format/pattern imitation**, less for abstract induction, and they **compete with the instruction for scarce context**. Testable consequence: on an SLM, instruction-only optimizers (GEPA/COPRO/SkillOpt) should beat demo-heavy ones (Bootstrap/MIPROv2) — a mark against the DSPy demo machinery for our case.
- **#5 marginal + collateral risk** — real near ceiling; the SLM regression data shows optimization can degrade other properties. Concretely (Table 1, **Qwen3.5-4B** row, deltas vs no-skill): TextGrad **−7.4** on SearchQA, **−11.8** on LiveMath, **−1.3** on DocVQA; the hand-written human skill **−1.8** SearchQA, **−4.0** LiveMath, **−2.2** ALFWorld. Only the gated SkillOpt stays positive on all six — evidence that ungated/naïve optimization *hurts* a small model.
- **#9 use cases**, for *our* setting:
  - *Reproducibility/fairness* — largely conceded: a **fixed shared human prompt across models** is also reproducible and fair. Surviving nuance only: "same prompt for all" vs "each model's best prompt" are two legitimate eval philosophies; optimization serves the second. Not decisive.
  - *Drift* — conceded for a single product.
  - *Scale* — conceded; single domain.
  - *Rule discovery* — a writing guide improves rule *clarity* but cannot *observe your data's failures* (a different activity); at small scale a human reads the failures directly, so it collapses into the manual-loop point. Conceded for us.
- **#10 complexity** — real, and consistent with Simplicity First. For a single-domain deployment, one auditable artifact is easier to debug and reason about than the optimizer pipeline.

**Held (the argument overreaches):**

- **Levels, not circularity (#6).** The meta-prompt (procedure) and the skill (solution) are different levels — like SGD's update rule vs a trained network's weights. The human writes the *procedure once*; the tool produces *data-and-model-specific solutions*. That the procedure is human-authored no more makes optimization pointless than human-authored gradient-descent math makes model training pointless. But — see #7 — at small scale the human can *also* execute the procedure by hand, so this holds in principle while collapsing to the manual-loop reframe in practice.
- **Surviving use cases beyond SLM:** **(a) SLM** limits humans can't intuit [conceded by both sides], and **(b) scale of comparison** — automatically adapting *many* candidate models where manual per-model looping is infeasible. Our *product* isn't that; our *benchmark* partially is, though a fixed shared prompt is a defensible alternative even there.

## What the paper's own run actually was

From the "Default optimizer hyperparameters" text (§4) and Table 6 (§4.4), grounding the "did they just run 4 epochs and beat the expert?" question:

- **4 epochs** (default, "unless noted"), rollout batch 40/step, reflection minibatch 8 (16 parallel analyst workers), textual LR = 4 with cosine decay, held-out validation gate (strictly-greater; ties rejected), slow/meta update over 20 sampled tasks/epoch. Both teacher (optimizer) and student (target) default to **medium reasoning effort**.
- **Edit economy: gains come from only 1–4 *accepted* edits** committed to `best_skill.md` (Table 6, GPT-5.5→GPT-5.5 runs): SearchQA 4, SpreadsheetBench 4, OfficeQA 1, DocVQA 3, LiveMath 1, ALFWorld 2 — *"between 1 and 4 (median 2.5)."* Verbatim: *"LiveMath's +29.3 point gain over no skill arises from a **single** accepted edit, and OfficeQA's +39.0 point gain similarly arises from one accepted edit"* (§4.4). Caveat on interpreting this: an "edit" is a bounded **rule-block**, not a word — the seeds are near-empty (SearchQA **16 tokens**, DocVQA 81, OfficeQA 145) and each edit adds hundreds of tokens, so "1 edit" ≈ "one accepted paragraph of rules," gated on held-out gain.
- **Baseline parity — checked Appendix C ("Experimental Protocol Details"), not stated.** A targeted fetch confirms the appendix does **not** document, for the *learning* baselines (TextGrad, GEPA, Trace2Skill, EvoSkill): (1) a **shared initial seed** with SkillOpt, (2) **matched** rollout/token/step budgets, or (3) the **same optimizer/reflection model** (GPT-5.5). Budget defaults are given for SkillOpt only. The main text claims it *"isolates ... the choice of adaptation procedure rather than secondary factors such as prompt template or scoring pipeline"* (§4) — but that parity is **asserted, not evidenced**. Two caveats: *not documented ≠ unfair* (configs may live in the released code), and this is a fetch-summariser's read of the arXiv HTML, not a line-by-line pass — the definitive check is the `microsoft/SkillOpt` repo configs. **Material because** SkillOpt's own strength lever is a strong optimizer (Table 5, §4.3: target-matched optimizer recovers only 56–74% of the gain), so an unmatched optimizer/budget across baselines would be exactly the confound the paper claims to have removed.

## Landing position

> For a **single-domain product with a small, human-tractable corpus and a competent author**, these tools are **not necessary** — hand-write the skill with a good guide, loop on failures manually, keep one controllable artifact. The proven value of the tools is **concentrated in regimes we are mostly not in** (SLM limits; scale that breaks the manual loop), and the regime we *are* in — **optimizing an already-good seed** — was never tested by the literature.

This is a defensible, slightly contrarian thesis, and a better research contribution than a SkillOpt-vs-GEPA bakeoff, because it attacks an **unexamined assumption** rather than comparing two search algorithms.

## The decisive experiment (four-cell)

On our in-car SLM task, compare:

| Cell | Setup | Answers |
| --- | --- | --- |
| (i) | strong hand-authored seed, as-is | the human baseline the papers omit |
| (ii) | strong seed + SkillOpt/GEPA | does optimization add anything *over good authoring*? |
| (iii) | generic seed + optimizer | reproduces the paper's regime (our run #5 lineage) |
| (iv) | strong seed + **manual** failure-loop | is the value the *loop* or the *automation*? |

- If **(ii) ≈ (i)** → optimization adds nothing over good authoring (the critique is vindicated).
- If **(iv) ≈ (ii)** → the value is the *loop*, not the *automation* (hand-loop suffices at our scale).
- If **(ii) ≫ (i)** and **(ii) ≫ (iv)** → automated optimization earns its complexity even on a good seed (the critique fails).

No published paper reports this four-cell design. It settles the argument empirically for our regime.

## Key numbers & quotes (arXiv 2605.23904v2, verify against local `paper_extract.txt`)

| Claim | Number / quote | Where |
| --- | --- | --- |
| Baselines | 7: no-skill, human-skill, one-shot-LLM, Trace2Skill, TextGrad, GEPA, EvoSkill | §4, Baselines |
| "no-skill" is not blank | *"the frozen target model run with the benchmark's default system prompt"* | §4, Baselines |
| Comparability claim | *"isolates ... the choice of adaptation procedure rather than secondary factors such as prompt template or scoring pipeline"* | §4, Baselines |
| Main result | best or tied on **52/52** (model, benchmark, harness) cells | §4.1, Table 1 |
| Human-skill length | **145–516 tokens** | §4.2 |
| Human-skill definition | *"an expert-written skill document curated per benchmark"* | §4, Baselines |
| SkillOpt final length | 379–1,995 tok, median ≈ 920 | §4.4, Table 6 |
| SkillOpt seed length | 16–516 tok (SearchQA 16) | §4.4, Table 6 |
| Accepted edits | 1–4, median 2.5 (OfficeQA/LiveMath = **1**) | §4.4, Table 6 |
| Single-edit gains | LiveMath **+29.3** and OfficeQA **+39.0** over no-skill each from **one** edit | §4.4 |
| SLM regression | Qwen3.5-4B: TextGrad −7.4 SearchQA / −11.8 LiveMath; human −1.8 / −4.0 / −2.2 | §4.1, Table 1 |
| Run config | 4 epochs, batch 40, minibatch 8, LR=4 cosine, medium reasoning (teacher+student) | §4, hyperparameters |
| Optimizer strength | strong optimizer > target-matched; latter recovers **56–74%** of the gain | §4.3, Table 5 |
| Seed/budget/optimizer-model parity across learning baselines | **checked App. C — not stated** (no shared seed, matched budget, or shared optimizer model documented for TextGrad/GEPA/Trace2Skill/EvoSkill) | App. C |

## Related

- `slm_agent_research_directions.md` (the frontier scan + angles; this critique sharpens Angle F/G and the external-vs-internal-state fork)
- `dspy_overview.md` (framework + optimizer menu; the meta-prompt files that make #1/#3/#6 concrete)
- `docs/experiments/` (the seed-sensitivity + faithful-run findings referenced in #4, #8)
