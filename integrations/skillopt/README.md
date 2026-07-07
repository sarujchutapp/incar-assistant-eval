# SkillOpt integration — in-car tool-calling

A proof-of-concept [SkillOpt](https://github.com/microsoft/SkillOpt) environment
that optimizes the assistant's system prompt (`incar_eval/adapter.py:SYSTEM_PROMPT`,
seeded here as `env/incar_toolcalling/skills/initial.md`) for a chosen small
target model, scored by the project's own `score_case` verifier.

**Goal of this PoC:** answer one question cheaply — does optimizing the skill move
the success rate on the held-out test split? It is *not* the trustworthy run: the
corpus is only ~70 cases (issue #10 grows it to ~400; issue #9 is the human anchor
that guards against the optimizer gaming the verifier).

## Contract mapping (verified against SkillOpt `main`)

| SkillOpt piece | This env |
| --- | --- |
| `adapter.py` → `EnvAdapter` subclass | `IncarToolCallingAdapter` (registered in `train.py`, see below) |
| `dataloader.py` → `load_split_items` | reads each split's `items.json`, keeps full case dicts |
| `rollout.py` → `run_batch` | `chat_target(skill, user)` per case, then delegates scoring |
| `evaluator.py` → `evaluate` | `score_case`; `hard = 1.0 if success`, `soft = 0.5*intent + 0.5*slot_f1` |
| skill being optimized | `skills/initial.md` (= current `SYSTEM_PROMPT`) |

## Setup

```bash
git clone https://github.com/microsoft/SkillOpt && cd SkillOpt
pip install -e .                                # SkillOpt
pip install -e /path/to/ai-evaluation          # makes `incar_eval` importable

# 1. Drop this env into SkillOpt's package tree
cp -r /path/to/ai-evaluation/integrations/skillopt/envs/incar_toolcalling skillopt/envs/
mkdir -p configs/incar_toolcalling
cp /path/to/ai-evaluation/integrations/skillopt/config/default.yaml configs/incar_toolcalling/default.yaml

# 2. Register the env — add this block inside _register_builtins() in scripts/train.py:
#    (SkillOpt has no auto-discovery; the registry is an explicit dict.)
#
#    try:
#        from skillopt.envs.incar_toolcalling.adapter import IncarToolCallingAdapter
#        _ENV_REGISTRY["incar_toolcalling"] = IncarToolCallingAdapter
#    except ImportError:
#        pass

# 3. Build the splits from the fixtures
python /path/to/ai-evaluation/integrations/skillopt/build_splits.py \
    --fixtures /path/to/ai-evaluation/fixtures --out data/incar_toolcalling_split

# 4. Run (models + key are set in the config; ANTHROPIC_API_KEY must be exported)
export ANTHROPIC_API_KEY=sk-...
python scripts/train.py --config configs/incar_toolcalling/default.yaml
```

## Split policy

Hand-authored cases are held out as **test** so we validate against human items;
synthetic cases carry train/val (`build_splits.py`):

    test  = cases.json (6) + hard_cases.json (12) = 18   (hand-authored, held out)
    train = first 40 of synth_cases.json                  (synthetic)
    val   = remaining 12 of synth_cases.json               (synthetic)

## Notes / decisions

- **Reward = success gate** → `hard = 1.0 if outcome.success else 0.0`. `soft` is a
  graded proxy (`0.5*intent_ok + 0.5*slot_f1`) so the gate has a continuous signal.
- **`gate_metric: mixed`** in the config: with a 12-case val split, a pure `hard`
  gate can reject every candidate (SkillOpt's own guidance). Switch to `hard`
  once the corpus grows (#10).
- `model.target` = the small model you deploy; `model.optimizer` = a strong model.
  Both use `claude_chat`; edit them + `ANTHROPIC_API_KEY` for your setup.
- `evaluator.py` imports `incar_eval.loader._to_gold` (private) to rebuild a
  validated `GoldRecord` from a case dict. If `loader` is refactored, update this.
- The seed `initial.md` deliberately matches the *current* `SYSTEM_PROMPT` verbatim,
  so the run measures improvement over the real baseline.
