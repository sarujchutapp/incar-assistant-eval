"""Aggregate the decomposed metrics from a list of per-case outcomes.

``proportion_counts`` returns (numerator, denominator) for each proportion so the
rates here and the Wilson intervals in the report share a single source.
"""

from dataclasses import dataclass

from .models import COMMAND_INTENTS, CaseOutcome, CostCategory, RoutingOutcome
from .safety import cost_of, is_hard_block
from .schema import SCHEMA


@dataclass(frozen=True)
class Metrics:
    n: int
    tsr: float
    routing_accuracy: float
    false_activation_rate: float           # over gold `none` cases
    false_rejection_rate: float            # over non-ambiguous command cases
    intent_accuracy: float                 # right action, over cases where it acted
    slot_f1: float                         # mean, over acted command cases
    slots_exact_rate: float                # over acted command cases
    capability_hallucination_rate: float   # over gold `out_of_scope` cases
    mean_cost: float                       # mean safety cost over all cases
    under_confirm_rate: float              # over high-stakes non-ambiguous command cases
    over_confirm_rate: float               # over low-stakes non-ambiguous command cases
    eyes_free_rate: float                  # over all emitted responses


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def proportion_counts(outcomes: list[CaseOutcome]) -> dict[str, tuple[int, int]]:
    """For each proportion metric, the (successes, total) pair."""
    # Hard-blocks are play_media commands but scored by the cost model, so they're
    # excluded from routing / intent / slot metrics. Ambiguous commands likewise.
    command = [o for o in outcomes if o.gold.expected_intent in COMMAND_INTENTS and not is_hard_block(o.gold)]
    routable = [o for o in outcomes if not is_hard_block(o.gold)]
    routable_command = [o for o in command if o.gold.ambiguity != "ambiguous"]
    none_cases = [o for o in outcomes if o.gold.expected_intent == "none"]
    oos_cases = [o for o in outcomes if o.gold.expected_intent == "out_of_scope"]
    acted_command = [o for o in command if o.routing is RoutingOutcome.CORRECT_ACTION]
    high_stakes = [o for o in routable_command if SCHEMA[o.gold.expected_intent].stakes == "high"]
    low_stakes = [o for o in routable_command if SCHEMA[o.gold.expected_intent].stakes == "low"]
    return {
        "tsr": (sum(o.success for o in outcomes), len(outcomes)),
        "routing_accuracy": (
            sum(o.routing in (RoutingOutcome.CORRECT_ACTION, RoutingOutcome.CORRECT_ABSTENTION) for o in routable),
            len(routable),
        ),
        "false_activation_rate": (
            sum(o.routing is RoutingOutcome.FALSE_ACTIVATION for o in none_cases), len(none_cases)
        ),
        "false_rejection_rate": (
            sum(o.routing is RoutingOutcome.FALSE_REJECTION for o in routable_command), len(routable_command)
        ),
        "intent_accuracy": (sum(o.intent_ok for o in acted_command), len(acted_command)),
        "slots_exact_rate": (sum(o.slots_exact for o in acted_command), len(acted_command)),
        "capability_hallucination_rate": (
            sum(o.routing is RoutingOutcome.CAPABILITY_HALLUCINATION for o in oos_cases), len(oos_cases)
        ),
        "under_confirm_rate": (sum(o.cost is CostCategory.UNDER_CONFIRM for o in high_stakes), len(high_stakes)),
        "over_confirm_rate": (sum(o.cost is CostCategory.OVER_CONFIRM_TRIVIAL for o in low_stakes), len(low_stakes)),
        "eyes_free_rate": (sum(o.emitted.eyes_free for o in outcomes), len(outcomes)),
    }


def compute_metrics(outcomes: list[CaseOutcome]) -> Metrics:
    counts = proportion_counts(outcomes)
    acted_command = [
        o for o in outcomes
        if o.gold.expected_intent in COMMAND_INTENTS
        and not is_hard_block(o.gold)
        and o.routing is RoutingOutcome.CORRECT_ACTION
    ]
    return Metrics(
        n=len(outcomes),
        tsr=_rate(*counts["tsr"]),
        routing_accuracy=_rate(*counts["routing_accuracy"]),
        false_activation_rate=_rate(*counts["false_activation_rate"]),
        false_rejection_rate=_rate(*counts["false_rejection_rate"]),
        intent_accuracy=_rate(*counts["intent_accuracy"]),
        slot_f1=(sum(o.slot_f1 for o in acted_command) / len(acted_command)) if acted_command else 0.0,
        slots_exact_rate=_rate(*counts["slots_exact_rate"]),
        capability_hallucination_rate=_rate(*counts["capability_hallucination_rate"]),
        mean_cost=(sum(cost_of(o.cost) for o in outcomes) / len(outcomes)) if outcomes else 0.0,
        under_confirm_rate=_rate(*counts["under_confirm_rate"]),
        over_confirm_rate=_rate(*counts["over_confirm_rate"]),
        eyes_free_rate=_rate(*counts["eyes_free_rate"]),
    )
