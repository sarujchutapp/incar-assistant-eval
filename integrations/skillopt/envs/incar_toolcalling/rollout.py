"""SkillOpt rollout for the in-car tool-calling env.

The optimized skill (``skill_content``) is passed as the system prompt; the
per-case schema + car-state + utterance is the user message. Scoring is
delegated to ``evaluator.evaluate``. Returns SkillOpt's ``{id, hard, soft}`` dicts.

Each item's trajectory is written to ``<out_root>/predictions/<id>/conversation.json``
(the format SkillOpt's reflect stage reads to build the analyst prompt); the
result dict is enriched with task/expected/fail-reason so the analyst has context.
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


def process_one(item: dict, skill_content: str, out_root: str, max_completion_tokens: int = 4096) -> dict:
    user = _user_content(item)
    raw, _meta = chat_target(skill_content, user, max_completion_tokens=max_completion_tokens)
    result = evaluate(item, raw)

    # Trajectory for the analyst (reflect reads <out_root>/predictions/<id>/conversation.json)
    pred_dir = os.path.join(out_root, "predictions", str(item["id"]))
    os.makedirs(pred_dir, exist_ok=True)
    conversation = [
        {"type": "message", "turn": 1, "content": f"PROMPT:\n{user}"},
        {"type": "message", "turn": 2, "content": f"MODEL OUTPUT:\n{raw}"},
    ]
    with open(os.path.join(pred_dir, "conversation.json"), "w", encoding="utf-8") as fh:
        json.dump(conversation, fh, ensure_ascii=False, indent=2)

    # Context the analyst header shows (task / expected / why it failed)
    expected = f'intent={item["expected_intent"]} slots={item.get("expected_slots", {})}'
    result["task_description"] = item.get("utterance", "")
    result["task_type"] = "command"
    result["reference_text"] = expected
    if not result.get("hard") and not result.get("fail_reason"):
        result["fail_reason"] = f"scored 0 — expected {expected}"
    return result


def run_batch(
    items: list[dict],
    out_root: str,
    skill_content: str,
    *,
    workers: int = 8,  # noqa: ARG001 — serial rollout; kept for signature parity
    max_completion_tokens: int = 4096,
    **_kwargs,
) -> list[dict]:
    os.makedirs(out_root, exist_ok=True)
    results = [process_one(item, skill_content, out_root, max_completion_tokens) for item in items]
    with open(os.path.join(out_root, "results.jsonl"), "w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r) + "\n")
    return results
