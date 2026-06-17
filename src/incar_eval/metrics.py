"""Aggregate the decomposed metrics from a list of per-case outcomes.

Slice 5 adds confidence intervals and paired model comparison on top of these.
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


def _rate(numerator: float, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def compute_metrics(outcomes: list[CaseOutcome]) -> Metrics:
    # Hard-blocks are play_media commands but are scored entirely by the cost
    # model, so they're excluded from routing / intent / slot metrics.
    command = [o for o in outcomes if o.gold.expected_intent in COMMAND_INTENTS and not is_hard_block(o.gold)]
    routable = [o for o in outcomes if not is_hard_block(o.gold)]
    # routing metrics also exclude ambiguous commands (scored by the cost model).
    routable_command = [o for o in command if o.gold.ambiguity != "ambiguous"]
    none_cases = [o for o in outcomes if o.gold.expected_intent == "none"]
    oos_cases = [o for o in outcomes if o.gold.expected_intent == "out_of_scope"]
    acted_command = [o for o in command if o.routing is RoutingOutcome.CORRECT_ACTION]
    routing_correct = sum(
        o.routing in (RoutingOutcome.CORRECT_ACTION, RoutingOutcome.CORRECT_ABSTENTION)
        for o in routable
    )
    high_stakes = [o for o in routable_command if SCHEMA[o.gold.expected_intent].stakes == "high"]
    low_stakes = [o for o in routable_command if SCHEMA[o.gold.expected_intent].stakes == "low"]
    return Metrics(
        n=len(outcomes),
        tsr=_rate(sum(o.success for o in outcomes), len(outcomes)),
        routing_accuracy=_rate(routing_correct, len(routable)),
        false_activation_rate=_rate(
            sum(o.routing is RoutingOutcome.FALSE_ACTIVATION for o in none_cases), len(none_cases)
        ),
        false_rejection_rate=_rate(
            sum(o.routing is RoutingOutcome.FALSE_REJECTION for o in routable_command),
            len(routable_command),
        ),
        intent_accuracy=_rate(sum(o.intent_ok for o in acted_command), len(acted_command)),
        slot_f1=_rate(sum(o.slot_f1 for o in acted_command), len(acted_command)),
        slots_exact_rate=_rate(sum(o.slots_exact for o in acted_command), len(acted_command)),
        capability_hallucination_rate=_rate(
            sum(o.routing is RoutingOutcome.CAPABILITY_HALLUCINATION for o in oos_cases), len(oos_cases)
        ),
        mean_cost=_rate(sum(cost_of(o.cost) for o in outcomes), len(outcomes)),
        under_confirm_rate=_rate(
            sum(o.cost is CostCategory.UNDER_CONFIRM for o in high_stakes), len(high_stakes)
        ),
        over_confirm_rate=_rate(
            sum(o.cost is CostCategory.OVER_CONFIRM_TRIVIAL for o in low_stakes), len(low_stakes)
        ),
        eyes_free_rate=_rate(sum(o.emitted.eyes_free for o in outcomes), len(outcomes)),
    )
