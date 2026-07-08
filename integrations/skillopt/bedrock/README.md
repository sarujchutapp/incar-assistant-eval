# Capped Bedrock optimizer for SkillOpt

Run the **optimizer** on AWS Bedrock (Claude Sonnet) with a **real-time hard $ cap**,
while the **target** stays on free local Ollama. Rationale + why AWS billing alerts
aren't enough: `../bedrock_cost_control.md`.

```
SkillOpt  --optimizer_model bedrock-sonnet-->  LiteLLM proxy (max_budget cap)  -->  Bedrock
          --target_model    llama3        -->  Ollama (localhost, $0)
```

Only the **proxy** holds AWS creds; SkillOpt talks to two localhost endpoints.

## Why this is cheap by construction

The optimizer (the paid model) is called only during *reflect* steps — dozens of
calls for a small run — not the thousands the **target** generates per case. Keeping
the target on Ollama means Bedrock only sees the cheap side of the loop; the proxy
cap is the backstop on top.

## Setup

```bash
# 1. Proxy venv (needs AWS creds on the boto3 chain: env vars or an AWS profile)
pip install 'litellm[proxy]'
# edit litellm_config.yaml: set the real Bedrock model id + region + master_key
#   aws bedrock list-foundation-models --query "modelSummaries[?contains(modelId,'claude')].modelId"

# 2. Start the proxy (terminal 1)
litellm --config integrations/skillopt/bedrock/litellm_config.yaml   # -> http://localhost:4000

# 3. Deploy the SkillOpt config (terminal 2, your SkillOpt clone)
mkdir -p configs/incar_unified_bedrock
cp <repo>/integrations/skillopt/config/incar_unified_bedrock.yaml configs/incar_unified_bedrock/default.yaml
# set optimizer_azure_openai_api_key to the proxy master_key

# 4. Ollama running for the target (ollama serve; ollama pull llama3)
```

## Prove the cap BEFORE trusting it

1. Leave `max_budget: 1` in the proxy config. Start the proxy.
2. Run a tiny job and **watch it hard-error** when spend crosses $1:
   ```
   python scripts/train.py --config configs/incar_unified_bedrock/default.yaml \
       --split_dir data/incar_unified_split \
       --optimizer_model bedrock-sonnet --target_model llama3 \
       --cfg-options train.num_epochs=1
   ```
3. Confirm the proxy returned a BudgetExceededError (check its spend log). **Only then**
   raise `max_budget` to your real ceiling and restart the proxy.

With `max_budget` + `max_tokens` + `num_epochs=1` + tiny splits, exposure during the
test is cents even if the cap is misconfigured — which is the point of testing it small.

## Backstop (contain blast radius if the proxy is misconfigured)

- **AWS Budgets Actions** on the account (auto-attach a deny policy at a threshold) — lags,
  so it's a backstop, not the stop.
- A **sandbox AWS account + SCP** so nothing can spend beyond it.

## Verify against your versions (placeholders in the configs)

- **Bedrock model id + region** in `litellm_config.yaml` (per-account; use the `aws bedrock`
  command above).
- **Global-budget key name**: `litellm_settings.max_budget` syntax has shifted across LiteLLM
  releases — confirm with `litellm --version` and the LiteLLM proxy budget docs.
- **`master_key`** must match `optimizer_azure_openai_api_key` in the SkillOpt config.
