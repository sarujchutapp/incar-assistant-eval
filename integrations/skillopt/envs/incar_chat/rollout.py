"""SkillOpt rollout for the in-car chat env.

The optimized skill (``skill_content``) is the system prompt; the grounding
context + the driver's question is the user message. Scoring is delegated to
``evaluator.evaluate``. Returns SkillOpt's ``{id, hard, soft}`` dicts.

Each item's trajectory is written to ``<out_root>/predictions/<id>/conversation.json``
(the format SkillOpt's reflect stage reads to build the analyst prompt); the
result dict is enriched with task/expected/fail-reason so the analyst has context.
"""

from __future__ import annotations

import json
import os
from typing import Any

from skillopt.model import chat_target

from .evaluator import evaluate


def _user_content(item: dict[str, Any]) -> str:
    context = f"Context:\n{item['context']}\n\n" if item.get("context") else ""
    return f'{context}Driver asks: "{item["question"]}"'


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
    expected = f'answer must contain: {item["fact"]}'
    result["task_description"] = item.get("question", "")
    result["task_type"] = "chat"
    result["reference_text"] = expected
    if not result.get("hard") and not result.get("fail_reason"):
        result["fail_reason"] = f"scored 0 — expected {expected}"
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
