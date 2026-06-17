"""The scorer — a pure, deterministic function with no I/O.

Slice 2 grades routing (act vs abstain), intent, and slots (F1 + exact match).
The safety cost model (slice 3) extends this.
"""

from typing import Any

from .models import (
    ABSTENTION_LABELS,
    COMMAND_INTENTS,
    CaseOutcome,
    GoldRecord,
    RoutingOutcome,
    ToolCall,
)


def _acted(emitted: ToolCall) -> bool:
    """The assistant acted unless it emitted an abstention label."""
    return emitted.intent not in ABSTENTION_LABELS


def classify_routing(expected_intent: str, emitted: ToolCall) -> RoutingOutcome:
    acted = _acted(emitted)
    if expected_intent in COMMAND_INTENTS:
        return RoutingOutcome.CORRECT_ACTION if acted else RoutingOutcome.FALSE_REJECTION
    if expected_intent == "none":
        return RoutingOutcome.FALSE_ACTIVATION if acted else RoutingOutcome.CORRECT_ABSTENTION
    # out_of_scope: acting means inventing a capability we don't have
    return RoutingOutcome.CAPABILITY_HALLUCINATION if acted else RoutingOutcome.CORRECT_ABSTENTION


def slot_f1(gold_slots: dict[str, Any], pred_slots: dict[str, Any]) -> float:
    """F1 over (slot, value) pairs — both name and value must match."""
    gold_pairs = set(gold_slots.items())
    pred_pairs = set(pred_slots.items())
    if not gold_pairs and not pred_pairs:
        return 1.0
    tp = len(gold_pairs & pred_pairs)
    if tp == 0:
        return 0.0
    precision = tp / len(pred_pairs)
    recall = tp / len(gold_pairs)
    return 2 * precision * recall / (precision + recall)


def score_case(gold: GoldRecord, emitted: ToolCall) -> CaseOutcome:
    return CaseOutcome(
        gold=gold,
        emitted=emitted,
        routing=classify_routing(gold.expected_intent, emitted),
        intent_ok=emitted.intent == gold.expected_intent,
        slots_exact=emitted.slots == gold.expected_slots,
        slot_f1=slot_f1(gold.expected_slots, emitted.slots),
    )
