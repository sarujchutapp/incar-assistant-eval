"""Dispatch scorer for the unified env — grades routing AND content.

The one model must pick the right *form* per utterance: a JSON tool call for a
command, prose for a question. We detect the emitted form by trying to parse a
tool call, then grade against the case's gold type:

- command case + emitted tool call  -> score_case (routing/intent/slots)
- command case + prose              -> fail (answered instead of acting)
- chat case    + prose              -> score_chat_case (faithfulness)
- chat case    + emitted tool call  -> fail (acted instead of answering)

So a wrong-form response scores 0 even if its "content" looks fine — that is the
routing failure the separate envs can't see.
"""

from __future__ import annotations

import json
from typing import Any

from incar_eval.adapter import parse_tool_call
from incar_eval.chat import ChatCase, score_chat_case
from incar_eval.loader import _to_gold
from incar_eval.scorer import score_case


def _emitted_tool_call(raw: str) -> Any:
    """Return a parsed ToolCall if the output is a tool call, else None (prose)."""
    try:
        return parse_tool_call(raw)
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def evaluate(item: dict[str, Any], raw: str) -> dict[str, Any]:
    tool = _emitted_tool_call(raw)
    if item["case_type"] == "command":
        if tool is None:  # answered instead of acting
            return {"id": item["id"], "hard": 0.0, "soft": 0.0, "response": raw, "fail_reason": "answered_not_acted"}
        outcome = score_case(_to_gold(item), tool)
        return {
            "id": item["id"],
            "hard": 1.0 if outcome.success else 0.0,
            "soft": 0.5 * float(outcome.intent_ok) + 0.5 * outcome.slot_f1,
            "response": raw, "case_type": "command", "routing": outcome.routing.value,
        }
    # chat
    if tool is not None:  # acted instead of answering
        return {"id": item["id"], "hard": 0.0, "soft": 0.0, "response": raw, "fail_reason": "acted_not_answered"}
    case = ChatCase(
        item["question"],
        item.get("fact", ""),
        item.get("context", ""),
        answerable=item.get("answerable", True),
    )
    outcome = score_chat_case(case, raw)
    return {
        "id": item["id"],
        "hard": 1.0 if outcome.faithful else 0.0,
        "soft": outcome.relevancy,
        "response": raw, "case_type": "chat", "faithful": outcome.faithful,
    }
