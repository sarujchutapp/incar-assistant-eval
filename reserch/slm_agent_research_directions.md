# SLM Agent Research Directions

Where the in-car / SkillOpt work points *as a research contribution* (not a deployment). Captures the conceptual conclusions from framing SkillOpt against the prompt-optimizer landscape, the 2026 frontier scan, and candidate angles that exploit assets we already own (curated in-car toolset, a verifier, a multilingual/Thai eval, Ollama SLMs).

_Last updated: 2026-07-17._

## 1. Framing: for our case, SkillOpt is a prompt optimizer

Settled after reading the SkillOpt paper (arXiv 2605.23904, Microsoft, May 2026) and comparing to GEPA:

- **Single-domain ⇒ the optimized skill *is* the always-on system prompt.** SkillOpt inserts the skill into context before execution ("prepended to the system or developer instruction"); in our `incar_unified` env `skills/initial.md` *is* `SYSTEM_PROMPT` verbatim. There is no conditional/"invoked-per-task" loading — that is Claude-Code-style Agent Skills, a *different* system that shares the word "skill."
- **GEPA and SkillOpt are the same family**, differing in the *search algorithm* and *artifact framing*, not the deployed object. GEPA = Pareto reflective prompt evolution (an optimizer *inside* DSPy, `dspy.GEPA`, ICLR 2026). SkillOpt = bounded add/delete/replace edits under a textual learning rate + strict held-out gate + rejected-edit buffer + epoch-wise momentum. Both deploy as always-on prepended text.
- **"Reusability" ≠ task-general.** The skill is task-specific by design; reuse means the *same domain skill* survives model/harness swaps, and it **degrades with model distance** (paper Table 4a: GPT-5.4→mini retains ~82% of the gain, →nano only ~16%; only within-family shown, never GPT→Qwen). For a single deployment this is moot: set rollout/target = deploy model so the skill patches the right failures.
- **Gating matters more on SLMs.** Paper's Qwen3.5-4B row: naive optimizers (TextGrad, even hand-written human skills) *regress* the small model on several benchmarks; only the validation-gated method stays net-positive. This is the real argument for a gated optimizer on our qwen2.5 target.
- **Skills vs fine-tuning are two adaptation layers.** Skills supply "procedural knowledge small models do not yet hold in weights." A well-fine-tuned specialist shrinks in-domain skill headroom, but skills retain value for cheap iteration, drift/edge cases, and auditability. Whether a skill adds value *on top of* a fine-tuned in-car model is untested by the paper — an open question.

**Implication:** a SkillOpt-vs-GEPA bakeoff is a *benchmark row, not a thesis*. It belongs as a baseline inside a larger question, not as the contribution.

## 2. The 2026 frontier: the lever moved from model/prompt to *harness*

The field has pivoted to **"agent = model + harness,"** with the harness as the dominant reliability lever:

- **Harness-Bench** (arXiv 2605.27922): swapping only the harness — same model, same tasks — moves scores by **23.8 points**. Reliability is "determined not by the underlying model but by the agent harness." Harness = six-tuple `H = (E, T, C, S, L, V)` (execution loop, tool registry, context manager, state store, lifecycle hooks, eval interface). Prompt optimization is one knob on one component (context manager).
- **"Don't Adapt SLMs for Tools; Adapt Tool Schemas to the Models"** (arXiv 2510.07248, tests **Qwen2.5 / Llama3.2** — our exact models): the lever for SLM tool-use is the **tool schema** (parameter count, description clarity, presentation), *not* the prompt and *not* fine-tuning. Schema redesign matches or exceeds fine-tuning gains with zero training.
- **Test-time compute + verifiers** for SLMs: **T1** (arXiv 2504.04718, tool-integrated verification for test-time scaling in SLMs); "Trust but Verify" survey (arXiv 2508.16665). Consensus: scaling test-time compute *without* a verifier is suboptimal — an external/self verifier is what makes it work. **We already own a verifier.**
- **Skill internalization** (alternatives to external prompt-skill): Skill-R1 (RL, arXiv 2605.09359), Skill-SD (self-distillation, arXiv 2604.10674), Skill0.5 (internalize+utilize for OOD, arXiv 2605.28424).
- **MCP tool-use benchmarks**: MCP-Bench, MCP-Atlas, MCPMark — tool discovery/selection/calling over MCP servers.

**Our realization ("it's just a prompt optimizer") is the setup for the real question:** *for SLMs specifically, is the prompt even the lever that matters most?* Almost nobody has decomposed prompt vs harness vs schema vs test-time-verification on one SLM tool-calling task.

## 3. Candidate research angles

| # | Angle | Open question | Anchor(s) | Assets used |
| --- | --- | --- | --- | --- |
| A | **Lever decomposition** (flagship spine) | For qwen2.5 on in-car routing, how does the gain decompose across **prompt vs harness structure vs tool-schema vs inference-time verification**? Which lever actually moves an SLM? | Harness-Bench (2605.27922); Agent Harness Survey | full rig, SkillOpt/GEPA, verifier |
| B | **Schema adaptation for a curated toolset** | How to represent a *fixed, domain-specific* car API (+ a lookup escape-hatch) so an SLM routes/fills correctly — verbose-JSON vs compact vs Python-style — across locales? | Adapt-Tool-Schemas (2510.07248); SmolLM3 | command quadrant, MCP idea, Thai |
| C | **Inference-time verifier gating** (signature method) | Move the verifier from *training* gate to *inference* (best-of-N + verifier select). Does verifier-guided test-time compute close the SLM↔LLM gap more cheaply, per token, than prompt optimization? | T1 (2504.04718); Trust-but-Verify (2508.16665) | `score_case` / `score_chat` |
| D | **Locale-sensitive SLM agents** (most differentiated) | Does prompt/skill optimization transfer across locales or need per-locale skills? Is the LLM-judge biased against *correct terse* (Thai) answers? | SmolLM3 (6 languages); gap in multilingual SLM-agent work | Thai eval + LLM-judge verbosity-bias finding |
| E | **Externalize vs internalize skill** | External prompt-skill (SkillOpt) vs skill distilled/RL'd into qwen weights, incl. OOD/drift. (Answers the FT-vs-skill question.) | Skill-R1, Skill-SD, Skill0.5 | qwen2.5, corpus, verifier |
| F | **Repro / methods** | Text-space optimizer evals are *fragile* (our verdict-flip: faithful vs non-faithful runs flipped the SkillOpt conclusion). What makes a faithful SLM optimizer comparison? | field repro concerns | faithful-minimal-qwen finding (`docs/experiments/`) |

## 4. Recommended flagship framing

**A (spine) + D (hook) + C (signature method):**

> *For multilingual SLM tool-calling, which lever actually matters — prompt, harness, tool-schema, or inference-time verification? A decomposition on a verifier-gated in-car benchmark, with a locale (Thai) twist.*

Why this over a pure optimizer comparison: everyone can run a prompt optimizer. Almost nobody has (a) a **verifier** to gate at inference, (b) a **multilingual procedural** tool-calling benchmark, and (c) demonstrated **faithfulness discipline**. The field is primed for "harness > model" but has shown it mostly on *frontier* models in *English* — the **SLM × multilingual × verifier** cell is open.

## 5. Concrete bridge from here

The sharpest, cheapest next step is to turn our two-way routing into **three-way answer / fetch / execute** by adding the deferred third category:

| | Action type | How answered |
| --- | --- | --- |
| Command | execute/write (`set_temp`) | tool call, no prose |
| Chat (grounded) | answer from *given* context | prose, faithfulness-gated |
| **Lookup (3rd, deferred)** | **tool call *in service of* answering** (e.g. internet/getter) | call → read result → prose |

Three-way routing under a curated schema is a harder, more realistic version of the current routing, and it directly exercises the schema lever (does a well-designed `lookup` schema help an SLM recognize when to fetch vs answer directly vs execute vs abstain?). See the parked third-category note in the benchmark work.

## References

- SkillOpt: Executive Strategy for Self-Evolving Agent Skills — arXiv 2605.23904 (local: `2605.23904v2.pdf`, `paper_extract.txt`)
- GEPA: Reflective Prompt Evolution Can Outperform RL — arXiv 2507.19457; `dspy.GEPA`
- Harness-Bench: Measuring Harness Effects across Models — arXiv 2605.27922
- Don't Adapt SLMs for Tools; Adapt Tool Schemas to the Models — arXiv 2510.07248
- Small Language Models for Efficient Agentic Tool Calling — arXiv 2512.15943
- T1: Tool-integrated Verification for Test-time Compute Scaling in SLMs — arXiv 2504.04718
- Trust but Verify! A Survey on Verification Design for Test-time Scaling — arXiv 2508.16665
- Skill-R1 (2605.09359), Skill-SD (2604.10674), Skill0.5 (2605.28424)

Related repo docs: `reserch/recent_trend.md` (eval-landscape survey), `reserch/roadmap.md`, `reserch/corpus_design.md`, `docs/experiments/` (SkillOpt runs).
