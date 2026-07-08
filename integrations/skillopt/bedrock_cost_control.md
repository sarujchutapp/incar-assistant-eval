# Capping AWS Bedrock cost for the SkillOpt optimizer

Discussion note — 2026-07-08. Concern: using **AWS Bedrock as the optimizer
model** and keeping the bill bounded. AWS billing-alert emails are not enough.

## The core problem

The AWS "email trigger" (a CloudWatch billing alarm / AWS Budgets alert) is
**notify-only** — it fires *after* spend has happened and never blocks a request.
For an optimizer loop that can issue thousands of calls, that lag is exactly the
failure mode. AWS's better option, **Budgets *Actions*** (auto-attach a deny
IAM policy / SCP at a threshold), still evaluates cost data only a few times a
day, so you can overshoot substantially before it fires. Neither is a real-time
hard cap.

## Options, from "real cap" to "backstop"

| Control | What it does | Good for | Limitation |
| --- | --- | --- | --- |
| **App-/proxy-level budget** (in the request path) | Meter `usage` tokens → cost → refuse at a cap | **The actual hard cap** — real-time, deterministic | You have to run/write it |
| `maxTokens` per request | Caps output cost per call | Bounding worst-case per call | Doesn't bound number of calls |
| Model choice + IAM deny by model id | Force Haiku, deny Opus/Sonnet | Cutting unit cost ~10×+ | Not a total cap |
| Bedrock RPM/TPM quotas | Throttle throughput | Ceiling on $/hour rate | Rate limit, not total |
| **AWS Budgets *Actions*** | Auto-apply deny IAM policy/SCP at threshold | Account-level backstop | Cost data lags → overshoot |
| Isolated AWS account + SCP | Blast-radius containment | "Can't spend beyond this account" | Setup overhead |
| Billing alarm email | Notifies you | Awareness | **Never stops anything** |

## Key architectural finding — where the cost actually flows

The optimizer model is called **inside SkillOpt**, *not* through this repo's
`ModelClient` port. Evidence:

- `config/default.yaml`: the backend inherits `openai_chat` pointed at an
  OpenAI-compatible `base_url` (`AZURE_OPENAI_ENDPOINT=localhost:11434/v1` for
  the Ollama target); models come from `--target_model` / `--optimizer_model`.
- `README.md`: optimizer/target use `claude_chat` + `ANTHROPIC_API_KEY`.

So `incar_eval.LiveModelClient` only covers the **benchmark's** target calls.
Wrapping that port would cap the wrong thing — it never sees the optimizer's
Bedrock spend. **This rules out an in-repo `ModelClient` wrapper for this goal.**

## Recommendation: a metering proxy in front of Bedrock

Because SkillOpt already targets an OpenAI-compatible `base_url`, the natural
insertion point is a proxy — no SkillOpt patching, just a `base_url` + model-alias
change.

```
SkillOpt (optimizer_model → openai_chat, base_url = proxy)
        → LiteLLM proxy   ← hard $ cap + RPM/TPM enforced here, in-request, real-time
        → AWS Bedrock (anthropic.claude-…)
```

**LiteLLM proxy** is the pragmatic pick: speaks Bedrock, exposes an
OpenAI-compatible endpoint, and enforces a per-key **`max_budget`** that returns a
hard error the instant cumulative spend crosses the cap — before Bedrock is
billed. Also does RPM/TPM limits and per-key spend logging. Everything AWS
Budgets can't do in real time.

**Alternative** if avoiding third-party deps: a ~40-line FastAPI
OpenAI-compatible shim that calls Bedrock via boto3 and meters `usage` itself —
more control, more code to own.

**Backstop under either:** AWS Budgets Actions + a sandbox AWS account with an
SCP. The proxy is what *stops* the run; these contain the blast radius if it's
misconfigured.

## Open decisions (before implementing)

1. **Scope of the cap:** optimizer only, or target rollouts too? The optimizer is
   the strong/expensive model, so capping just it is usually enough — but target
   rollouts × many cases can add up.
2. **Proxy vs self-owned shim:** LiteLLM proxy (fast, batteries-included) vs the
   FastAPI/boto3 shim (zero third-party deps, more code).

## Next steps (once decided)

- Write a LiteLLM proxy config: Bedrock model → alias, `max_budget`, RPM/TPM,
  plus a `.env`/README snippet.
- Edit the SkillOpt config: `optimizer_model` → proxy alias, `base_url` → proxy,
  so only the optimizer routes through the cap (target rollouts can stay on
  Ollama/cheap).
