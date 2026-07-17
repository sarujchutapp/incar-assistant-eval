# DSPy — Framework and Optimizer Menu

Reference for what DSPy actually is (a framework for *programming* LMs, not only a prompt optimizer) and what each of its optimizers ("teleprompters") does. Captured while scoping a GEPA-vs-SkillOpt bakeoff on `incar_unified`. Companion to `slm_agent_research_directions.md`.

_Last updated: 2026-07-17._

## 1. DSPy is a framework, not an optimizer

DSPy ("program, don't prompt"; often glossed as *Declarative Self-improving Python*) is a framework for building LM pipelines as composable code. **Optimization is one stage ("compile"), not the whole thing.** Its pillars:

| Pillar | What it is |
| --- | --- |
| **Signatures** | Declarative I/O spec (`context, intents, question -> action`). You declare *what*, DSPy compiles the actual prompt. |
| **Modules** | Strategies over a signature: `Predict` (basic), `ChainOfThought` (adds reasoning), **`ReAct`** (tool-calling agent loop), `ProgramOfThought` (writes code), `Retrieve` (RAG). Composed with plain Python control flow. |
| **Metrics / assertions** | Metric functions (can return *textual feedback*, not just a scalar); `Assert`/`Suggest` add runtime constraints with retry/backtracking. |
| **LM abstraction** | Unified interface to providers (OpenAI, Anthropic, **local via Ollama**), structured-output adapters (JSON/chat), caching. |
| **Evaluate / tracing** | `Evaluate` runs a program over a devset with a metric (parallel); traces feed both debugging and the optimizers. |
| **Optimizers** | The "compile" step that tunes prompts/demos/weights (below). |

Headline value = the **programming model**: decouple program logic from prompt wording so prompts become *compiled artifacts*. `ReAct` (agents/tool-calling) and `Retrieve` (RAG) matter for our harness / MCP / lookup-tool angles independent of optimization.

## 2. The optimizer menu, grouped by *what they change*

This grouping maps onto the external-vs-internal-state framing (see `slm_agent_research_directions.md` §3, angle E).

**Optimize the few-shot examples** — external state (which demos go in the prompt)

| Optimizer | What it does |
| --- | --- |
| `LabeledFewShot` | Drops your labeled corpus examples into the prompt as demos. No generation, no search. |
| `BootstrapFewShot` | **Runs the program to generate worked examples** (input + generated reasoning trace + output), keeps the ones that pass the metric, uses those as demos. The value is the *reasoning path*, not the raw pair. |
| `BootstrapFewShotWithRandomSearch` | Bootstraps many demo sets, evaluates different **combinations** on validation, keeps the best-scoring set (examples interact — order/diversity matter). |
| `KNNFewShot` | No fixed demos; at inference **retrieves the most similar examples** to the current input (dynamic, per-query). |

**Optimize the instruction text** — external state (wording; = "the prompt/skill")

| Optimizer | What it does |
| --- | --- |
| `COPRO` | Instruction-only. Coordinate ascent: propose new instruction → evaluate → keep best → repeat. |
| `GEPA` | Reflective evolutionary (Pareto population + reflection + merge/crossover). Strongest instruction optimizer; beats MIPROv2 ~10–13%. See `slm_agent_research_directions.md` for the exploration-vs-stability contrast with SkillOpt. |

**Optimize both instruction + demos**

| Optimizer | What it does |
| --- | --- |
| `MIPROv2` | Proposes candidate instructions *and* demo sets, then Bayesian-searches combinations for best validation score. The strong baseline GEPA beats. |
| `SIMBA` | Newer introspective mini-batch method — model reflects on batches to propose rules/demos. |

**Cross into the weights** — internal state (this is *not* prompt optimization)

| Optimizer | What it does |
| --- | --- |
| `BootstrapFinetune` | Bootstraps demos, then **fine-tunes model weights** on them — distills the prompt-based program into the model. The bridge to the internalization experiment (angle E). |

## 3. How the few-shot bootstrapping works (the non-obvious part)

`BootstrapFewShot` does **not** just select the best corpus example. It:
1. Takes a training input (gold answer known).
2. **Runs the full program** — including intermediate reasoning / tool steps → a complete trajectory.
3. Checks the output against the metric; if correct, **keeps the whole trace** (input + generated reasoning + output) as a demonstration.
4. Inserts those self-generated successful traces as few-shot examples.

"Find the best example and put it in the prompt" ≈ `LabeledFewShot` (raw pairs) + the RandomSearch selection step. The DSPy-signature move is **generating successful reasoning traces**, which raw corpus pairs don't contain.

## 4. Relevance to our bakeoff / research

- **GEPA** (instruction) ≈ the single-prompt comparison to SkillOpt → isolates *exploration (Pareto) vs stability (gate)*.
- **MIPROv2 / Bootstrap\*** add **demo optimization** — a lever **SkillOpt structurally lacks** (it only edits one instruction document, never adds worked examples). Bakeoff axis: does qwen2.5 gain more from a better *instruction* or from good *worked examples*, or both?
- **`ReAct`** — express the in-car tool-calling / lookup (3rd-category) routing as a declarative agent; relevant to the harness / tool-schema / MCP angles.
- **`BootstrapFinetune`** — the concrete DSPy path for the external-vs-internal-state experiment (prompt-skill vs distilled-into-weights).
- **Metric-with-feedback** — `score_case`/`score_chat` can return *why* a case failed, giving GEPA richer reflection material than a bare 0/1.
- Task LM = qwen2.5 via Ollama; reflection/optimizer LM = a stronger model (mirrors SkillOpt's target/optimizer split; the official GEPA+Ollama tutorial uses LLaMA-3 8B task + Qwen2.5 reflection).

## References

- DSPy GEPA optimizer overview — https://dspy.ai/api/optimizers/GEPA/overview/
- GEPA + DSPy + Ollama tutorial (local SLMs) — https://dspy.ai/tutorials/gepa_ai_program/
- GEPA paper — arXiv 2507.19457
- Standalone engine — `gepa-ai/gepa`
- Companion: `reserch/slm_agent_research_directions.md`
