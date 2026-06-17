"""The scorer — a pure, deterministic function with no I/O.

Slice 1 grades intent + slot exact match. Routing/abstention (slice 2) and the
safety cost model (slice 3) extend this.
"""

from .models import CaseOutcome, GoldRecord, ToolCall


def score_case(gold: GoldRecord, emitted: ToolCall) -> CaseOutcome:
    return CaseOutcome(
        gold=gold,
        emitted=emitted,
        intent_ok=emitted.intent == gold.expected_intent,
        slots_ok=emitted.slots == gold.expected_slots,
    )
