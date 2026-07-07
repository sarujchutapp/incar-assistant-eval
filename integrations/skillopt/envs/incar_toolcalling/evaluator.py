"""Scoring for the in-car tool-calling env — wraps the project's own verifier.

``evaluate`` turns one (item, raw model output) pair into SkillOpt's required
``{id, hard, soft}`` result:

    hard = 1.0 if outcome.success else 0.0        # the success gate (accept/reject)
    soft = 0.5 * intent_ok + 0.5 * slot_f1        # continuous signal

The success gate is the reward semantics we chose; ``soft`` is the continuous
fallback SkillOpt uses for gradient / mixed-gate, which the docs recommend when
the selection (val) split is small — as ours is — so a pure hard gate doesn't
reject every candidate.
"""

from __future__ import annotations

import json

from incar_eval.adapter import parse_tool_call
from incar_eval.loader import _to_gold  # rebuild + validate a GoldRecord from a case dict
from incar_eval.scorer import score_case


def evaluate(item: dict, raw: str) -> dict:
    try:
        emitted = parse_tool_call(raw)
    except (json.JSONDecodeError, KeyError, TypeError):
        # Unparseable output is a failed command, not a crash — score it 0.
        return {"id": item["id"], "hard": 0.0, "soft": 0.0, "response": raw, "fail_reason": "parse_error"}
    outcome = score_case(_to_gold(item), emitted)
    return {
        "id": item["id"],
        "hard": 1.0 if outcome.success else 0.0,
        "soft": 0.5 * float(outcome.intent_ok) + 0.5 * outcome.slot_f1,
        "response": raw,
        "intent_ok": outcome.intent_ok,
        "slots_exact": outcome.slots_exact,
        "routing": outcome.routing.value,
    }
