# How People Evaluate LLMs and Chatbots Today (Plain-Language Survey)

A plain-language, condensed version of `recent_trend.md`. It covers the same ideas without the dense academic phrasing.

**The big shift:** evaluating an LLM used to be like a simple software test — run fixed questions, check the score. That no longer works well. Models now act as agents (call tools, take multi-step actions), hold long conversations, and look things up in databases (RAG). So evaluation has become a *measurement-design problem*: you have to watch behavior over time, test for safety, and check that actions actually happened — not just that the text sounds right.

Three recurring headaches:
- **Everything is coupled.** The prompt, the retrieval database, and the model weights all affect each other. Changing one can silently break the others in unpredictable ways.
- **Data ≠ insight.** Teams collect tons of eval data but still can't pinpoint *why* something failed or how to fix it. (Called the "actionability gap.")
- **It's expensive.** Running many models continuously costs real compute, money, and energy.

---

## 1. Old benchmarks are wearing out

Classic academic tests (MMLU, GSM8K, HumanEval) are losing their usefulness for two reasons:

- **Saturation:** top models all score near 100%, so the test can no longer tell them apart — the differences are just noise.
- **Contamination:** the test questions leak into training data, so models score well by *memorizing* answers, not by reasoning.

The fix is harder, fresher, and constantly-updated tests. People sort benchmarks into four types:

| Type | Examples | What it measures | Main weakness |
| --- | --- | --- | --- |
| **A — Independent academic** | GPQA Diamond, MMLU-Pro, HLE | Hard reasoning, PhD-level knowledge | Saturates fast (useful <2 yrs) |
| **B — Crowd preference** | LMArena | Open-ended quality, human votes | Gameable; biased toward formatting |
| **C — Vendor / in-house** | Custom internal suites | Narrow, product-specific tasks | Easy to over-fit; no outside check |
| **D — Dynamic / refreshed** | LiveBench, LiveCodeBench, SWE-bench | Contamination-resistant coding | Expensive; needs constant upkeep |

(For reference, recent top models cluster tightly: GPT-5.5, Claude Opus 4.7, and Gemini 3.1 Pro all sit around ~1505 Elo on LMArena, with open-weight models like DeepSeek-V4 and Llama 4 close behind at lower cost.)

---

## 2. Two capabilities that fail differently: code and long documents

- **Code generation:** modern tests don't just check if the code matches a string. They run it and check four things: does it compile, does it crash, does it give the right answer, and is it efficient? A big finding: the *scaffold* around the model (retry loops, compiler feedback) matters as much as the model itself.
- **Long documents (9,000+ tokens):** short-answer tests can't catch the problems here. Long-form writing is judged on structure, logical consistency across sections, coverage, depth, and insight. Tools like LongJudgeBench check whether an *automated judge* can score long text reliably without getting distracted by formatting.

---

## 3. The "conversation tax": chatbots get worse over multiple turns

Early evals only tested single, fully-specified questions. But real conversations are multi-turn, and models degrade as the conversation grows.

The key number: splitting one complex request across several turns causes an **average 39% accuracy drop** and **~112% more unreliability**. Put the *same* info in one big prompt and performance recovers to 95%. So it's not a knowledge gap — it's a conversation-handling gap.

Four failure patterns:
- **Answering too early:** the model guesses a final answer in the first ~20% of the chat, before it has the full picture. These early guesses are right only ~31% of the time vs. ~64% when it waits.
- **Answer bloat:** responses balloon 20–300% over turns as the model piles on restatements instead of starting clean.
- **Lost in the middle:** the model pays attention to the first and last turns and forgets the middle (recall there drops below 20%).
- **Doubling down on mistakes:** once it commits to a wrong assumption early, it rarely backs out — it builds on the bad premise.

Also: under pressure, models **cave to user suggestions** even when they were right — and they do this *equally* for good and bad suggestions, so it's conformity, not genuine correction. Bigger models don't fix this; it comes from training (RLHF), not model size.

**Metrics used for multi-turn chat:**

| Level | Metric | What it checks |
| --- | --- | --- |
| Conversation | Completeness | Did it satisfy all the user's intentions across the whole chat? |
| Conversation | Knowledge Retention | Did it remember earlier facts without re-asking? |
| Conversation | Role Adherence | Did it stay in its assigned persona? |
| Turn | Turn Relevancy | Is this reply on-topic for the last few messages? |
| Turn | Consistency | Does this reply contradict something it said earlier? |

To cope, systems summarize/compress the history periodically instead of feeding the whole raw transcript back in.

---

## 4. LLM-as-a-judge: useful, but biased

Using one LLM to grade another's open-ended output scales well — but judges have systematic biases:

- **Formatting bias:** prefers rich markdown and fancy language regardless of correctness. (The strongest bias — correlation 0.76–0.92.)
- **Verbosity bias:** prefers longer answers, even when short was requested.
- **Self-preference:** rates its *own* outputs higher. Even the smartest models do this.
- **Position bias:** in A-vs-B comparisons, position (first vs. second) sways the verdict.
- **CoT / sentiment bias:** favors step-by-step or overly polite, agreeable answers.
- **Authority bias:** swayed by citations and official-sounding references — even fake ones.

**How to fight the bias:**
- **Score dimensions separately** (accuracy, format, conciseness) instead of one gut-feel number. Cuts self-preference ~31%.
- **Force the judge to write its critique *before* the verdict.** This is the single most reliable fix.
- **Swap A/B positions** and run twice to cancel position bias.
- **Strip formatting** from answers so the judge grades content, not style.
- **Use a panel of different model families** and have them reach consensus.

(You can also use purpose-built judge models — Prometheus 2, PandaLM, etc. — which have less bias but may not generalize as well.)

---

## 5. Evaluating RAG and agents (not just the final text)

If you only grade the final answer, you miss failures upstream in retrieval or tool use.

**RAG (retrieval) metrics:**
- **Context Recall:** did retrieval fetch *all* the needed info? (Low recall → the model guesses → hallucinates.)
- **Context Precision:** how much of what was fetched is actually relevant?
- **NDCG:** are the most relevant documents ranked at the top?
- **Faithfulness:** is every claim in the answer actually supported by the retrieved text? (Breaks the answer into atomic claims and checks each.)
- **Answer Relevancy:** does the answer actually address the question?

**Agent metrics:**
- **Task Success Rate (TSR):** did the agent reach the goal? **Must be verified by checking the actual environment state — never the agent's own "I did it!"**
- **Progress Score:** partial credit for multi-step tasks (weight each sub-goal).
- **Plan Optimality / Step Efficiency:** did it take a sensible path, or loop and thrash?
- **Tool Selection / Execution Accuracy:** did it pick the right tool and call it correctly?
- **Latency:** measure percentiles (P50/P95/P99), not averages — one slow step in a chain dominates the real experience, and averages hide it.

**The "state-outcome disconnect":** the #1 agent trap — the agent says "done" but nothing actually happened (or the API silently failed). The text looks fine, so normal logging marks it a success. Fix: tools like **Truveil** check the environment directly to confirm the change really happened. Related finding: tool-calling interfaces are *less* safe than the raw model (24–60% higher attack success), so safety must be tested at the action level, not just the text level.

---

## 6. Ranking models: Elo vs. Bradley-Terry

To turn many head-to-head comparisons into a leaderboard:

- **Elo** (from chess) updates ratings one match at a time and weights recent matches more. Problem: the final ranking depends on match *order* — bad for a benchmark you want to re-run reproducibly. It also assumes skill changes over time, but a deployed model is fixed.
- **Bradley-Terry** fits all comparisons at once, ignores order, and gives tighter, more stable ratings that resist gaming. **This is the modern choice.** Each model gets a "strength" number, and `P(A beats B)` is just `strengthA / (strengthA + strengthB)`.

---

## 7. Safety: red-teaming and guardrails

Static safety tests saturate too, so the focus is on **automated red-teaming** — algorithms that auto-generate jailbreak attempts and distill them into fresh safety tests (covering CBRN, cyber-offense, manipulation, privacy). Tools like the Safety Gap Toolkit measure the gap between what a model *refuses* to do and what its weights *can actually* produce.

For live protection, teams run small, fast **guardrail models** rather than a big general LLM (too slow, jailbreakable itself). Examples: WildGuard (open, English-focused), GA Guard (high accuracy, heavier), Lakera Guard (fast, prompt-injection focus, but high false positives), and Amazon Bedrock Guardrails (AWS-integrated, PII redaction).

---

## 8. After deployment: watching for drift

A good chatbot can quietly degrade in production — from API updates, database changes, or shifting user behavior. Two kinds of drift:
- **Input drift:** the prompts coming in change (new slang, or a word's meaning shifts).
- **Output drift:** the responses get worse over time (more hallucinations, tone drift).

A common monitoring setup is two layers:
- **Layer 1 (statistical):** convert prompts to embeddings and watch for distribution shift (using Wasserstein distance, since standard tests fail in high dimensions). This is the automatic alarm.
- **Layer 2 (semantic):** when Layer 1 alarms, send a sample to an LLM judge to explain *why* it drifted (new topics? harder queries? different style?).

---

## 9. The maturity ladder

Teams mature through five levels:
1. Manual spot-checks (doesn't scale).
2. Automated LLM-judge evals on a fixed test set.
3. Add operational metrics (latency, cost, faithfulness).
4. Move evaluation into production via tracing/observability.
5. **Closed loop:** production failures auto-feed back into the test set, and evals actively route traffic at runtime.

Tools that support this include MLflow, Braintrust, LangSmith, Arize Phoenix, Helicone, and SigNoz. The general pattern: instrument every step as a trace, evaluate at each step (not just the final output), verify real state changes, route around low-quality outputs live, and continuously fold production failures back into the test suite.

---

## Key takeaways for building our own benchmark

- Build internal (Type C) — but defend against over-fitting with human validation and multi-model checks.
- Verify actions by environment state, never by the model's self-report.
- Expect multi-turn degradation; test it deliberately.
- If using an LLM judge, force critique-before-verdict, normalize length, and use a different model family.
- Use Bradley-Terry, not Elo, for any preference ranking.
- Report latency as percentiles, not averages.
