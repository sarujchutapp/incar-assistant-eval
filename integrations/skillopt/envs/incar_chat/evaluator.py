"""Scoring for the in-car chat env — wraps the project's faithfulness verifier.

``hard`` is the faithfulness gate (the answer contains the grounded fact);
``soft`` is answer relevancy, a continuous signal for the optimizer.
"""

from __future__ import annotations

from typing import Any

from incar_eval.chat import ChatCase, score_chat_case


def evaluate(item: dict[str, Any], raw: str) -> dict[str, Any]:
    case = ChatCase(question=item["question"], fact=item["fact"], context=item.get("context", ""))
    outcome = score_chat_case(case, raw)
    return {
        "id": item["id"],
        "hard": 1.0 if outcome.faithful else 0.0,
        "soft": outcome.relevancy,
        "answer": raw,
        "faithful": outcome.faithful,
    }
