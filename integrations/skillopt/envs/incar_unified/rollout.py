"""SkillOpt rollout for the unified in-car assistant env.

Every case presents the SAME environment — the available intents are always in
context — so the model must *decide* whether to act (tool call) or answer
(prose). Command cases add car-state; chat cases add the grounding context.

Each item's trajectory is written to ``<out_root>/predictions/<id>/conversation.json``
(the format SkillOpt's reflect stage reads to build the analyst prompt); the
result dict is enriched with task/expected/fail-reason so the analyst has context.
"""

from __future__ import annotations

import json
import os
from typing import Any

from skillopt.model import chat_target

from incar_eval.schema import schema_text

from .evaluator import evaluate


def _user_content(item: dict[str, Any]) -> str:
    intents = f"Available intents:\n{schema_text()}\n\n"
    if item["case_type"] == "command":
        cs = item.get("car_state")
        ctx = f"Vehicle is {cs.get('vehicle_motion', 'parked')}.\n" if cs else ""
        return f'{intents}{ctx}Driver said: "{item["utterance"]}"'
    ctx = f"Context:\n{item['context']}\n\n" if item.get("context") else ""
    return f'{intents}{ctx}Driver asks: "{item["question"]}"'


def _expected(item: dict[str, Any]) -> str:
    if item["case_type"] == "command":
        return f'intent={item["expected_intent"]} slots={item.get("expected_slots", {})}'
    return f'answer must contain: {item["fact"]}'


def process_one(item: dict[str, Any], skill_content: str, out_root: str, max_completion_tokens: int = 1024) -> dict[str, Any]:
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
    result["task_description"] = item.get("utterance") or item.get("question") or ""
    result["task_type"] = item["case_type"]
    result["reference_text"] = _expected(item)
    if not result.get("hard") and not result.get("fail_reason"):
        result["fail_reason"] = f"scored 0 — expected {_expected(item)}"
    return result


def run_batch(
    items: list[dict[str, Any]],
    out_root: str,
    skill_content: str,
    *,
    workers: int = 8,  # noqa: ARG001 — serial rollout; kept for signature parity
    max_completion_tokens: int = 1024,
    **_kwargs: Any,
) -> list[dict[str, Any]]:
    os.makedirs(out_root, exist_ok=True)
    results = [process_one(item, skill_content, out_root, max_completion_tokens) for item in items]
    with open(os.path.join(out_root, "results.jsonl"), "w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r) + "\n")
    return results
