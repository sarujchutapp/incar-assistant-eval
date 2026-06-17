"""Aggregate the decomposed metrics from a list of per-case outcomes.

Slice 5 adds confidence intervals and paired model comparison on top of these.
"""

from dataclasses import dataclass

from .models import COMMAND_INTENTS, CaseOutcome, RoutingOutcome


@dataclass(frozen=True)
class Metrics:
    n: int
    tsr: float
    routing_accuracy: float
    false_activation_rate: float           # over gold `none` cases
    false_rejection_rate: float            # over gold command cases
    intent_accuracy: float                 # right action, over cases where it acted
    slot_f1: float                         # mean, over acted command cases
    slots_exact_rate: float                # over acted command cases
    capability_hallucination_rate: float   # over gold `out_of_scope` cases


def _rate(numerator: float, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def compute_metrics(outcomes: list[CaseOutcome]) -> Metrics:
    command = [o for o in outcomes if o.gold.expected_intent in COMMAND_INTENTS]
    none_cases = [o for o in outcomes if o.gold.expected_intent == "none"]
    oos_cases = [o for o in outcomes if o.gold.expected_intent == "out_of_scope"]
    acted_command = [o for o in command if o.routing is RoutingOutcome.CORRECT_ACTION]
    routing_correct = sum(
        o.routing in (RoutingOutcome.CORRECT_ACTION, RoutingOutcome.CORRECT_ABSTENTION)
        for o in outcomes
    )
    return Metrics(
        n=len(outcomes),
        tsr=_rate(sum(o.success for o in outcomes), len(outcomes)),
        routing_accuracy=_rate(routing_correct, len(outcomes)),
        false_activation_rate=_rate(
            sum(o.routing is RoutingOutcome.FALSE_ACTIVATION for o in none_cases), len(none_cases)
        ),
        false_rejection_rate=_rate(
            sum(o.routing is RoutingOutcome.FALSE_REJECTION for o in command), len(command)
        ),
        intent_accuracy=_rate(sum(o.intent_ok for o in acted_command), len(acted_command)),
        slot_f1=_rate(sum(o.slot_f1 for o in acted_command), len(acted_command)),
        slots_exact_rate=_rate(sum(o.slots_exact for o in acted_command), len(acted_command)),
        capability_hallucination_rate=_rate(
            sum(o.routing is RoutingOutcome.CAPABILITY_HALLUCINATION for o in oos_cases), len(oos_cases)
        ),
    )
