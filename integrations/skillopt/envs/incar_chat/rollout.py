"""SkillOpt rollout for the in-car chat env.

The optimized skill (``skill_content``) is the system prompt; the grounding
context + the driver's question is the user message. Scoring is delegated to
``evaluator.evaluate``. Returns SkillOpt's ``{id, hard, soft}`` dicts.
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


def process_one(item: dict[str, Any], skill_content: str, max_completion_tokens: int = 1024) -> dict[str, Any]:
    raw, _meta = chat_target(skill_content, _user_content(item), max_completion_tokens=max_completion_tokens)
    return evaluate(item, raw)


def run_batch(
    items: list[dict[str, Any]],
    out_root: str,
    skill_content: str,
    *,
    workers: int = 8,  # noqa: ARG001 — serial rollout; kept for signature parity
    max_completion_tokens: int = 1024,
    **_kwargs: Any,
) -> list[dict[str, Any]]:
    results = [process_one(item, skill_content, max_completion_tokens) for item in items]
    os.makedirs(out_root, exist_ok=True)
    with open(os.path.join(out_root, "results.jsonl"), "w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r) + "\n")
    return results
