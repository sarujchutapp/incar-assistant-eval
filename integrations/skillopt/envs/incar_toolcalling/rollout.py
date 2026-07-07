"""SkillOpt rollout for the in-car tool-calling env.

The optimized skill (``skill_content``) is passed as the system prompt; the
per-case schema + car-state + utterance is the user message. Scoring is
delegated to ``evaluator.evaluate``. Returns SkillOpt's ``{id, hard, soft}`` dicts.
"""

from __future__ import annotations

import json
import os

from skillopt.model import chat_target

from incar_eval.schema import schema_text

from .evaluator import evaluate


def _user_content(item: dict) -> str:
    cs = item.get("car_state")
    context = f"Vehicle is {cs.get('vehicle_motion', 'parked')}.\n" if cs else ""
    return (
        f"Available intents:\n{schema_text()}\n\n"
        f"{context}"
        f'Driver said: "{item["utterance"]}"'
    )


def process_one(item: dict, skill_content: str, max_completion_tokens: int = 4096) -> dict:
    raw, _meta = chat_target(skill_content, _user_content(item), max_completion_tokens=max_completion_tokens)
    return evaluate(item, raw)


def run_batch(
    items: list[dict],
    out_root: str,
    skill_content: str,
    *,
    workers: int = 8,  # noqa: ARG001 — serial rollout; kept for signature parity
    max_completion_tokens: int = 4096,
    **_kwargs,
) -> list[dict]:
    results = [process_one(item, skill_content, max_completion_tokens) for item in items]
    os.makedirs(out_root, exist_ok=True)
    with open(os.path.join(out_root, "results.jsonl"), "w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r) + "\n")
    return results
