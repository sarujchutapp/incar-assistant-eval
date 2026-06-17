"""Core data shapes for the benchmark.

A structured tool call, a gold record (the answer key), the per-case routing
outcome, and the per-case / aggregate grades. Later slices extend these
(ambiguity, expected mode, car_state).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

#: The six command intents (benchmark_spec.md §6.1). Kept here in the base module
#: so both the schema and the scorer can depend on it without an import cycle;
#: schema.py asserts SCHEMA's keys match this set.
COMMAND_INTENTS: frozenset[str] = frozenset(
    {"set_climate", "navigate", "call_contact", "play_media", "adjust_volume", "send_message"}
)

#: Abstention gold labels. `none` = no actionable command (chit-chat / ambient);
#: `out_of_scope` = a real command for an absent capability.
ABSTENTION_LABELS: frozenset[str] = frozenset({"none", "out_of_scope"})


class RoutingOutcome(Enum):
    """Act-vs-abstain result for one case — where the safety failures live."""

    CORRECT_ACTION = "correct_action"
    CORRECT_ABSTENTION = "correct_abstention"
    FALSE_ACTIVATION = "false_activation"          # acted on a non-command (gold `none`)
    FALSE_REJECTION = "false_rejection"            # ignored a clear command
    CAPABILITY_HALLUCINATION = "capability_hallucination"  # acted on `out_of_scope`


@dataclass(frozen=True)
class ToolCall:
    """A structured action the assistant emitted (intent + parameters).

    An intent in ``ABSTENTION_LABELS`` means the assistant declined to act.
    """

    intent: str
    slots: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GoldRecord:
    """A test case with its expected action — the objective answer key."""

    utterance: str
    expected_intent: str
    expected_slots: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CaseOutcome:
    """Deterministic grade for one case."""

    gold: GoldRecord
    emitted: ToolCall
    routing: RoutingOutcome
    intent_ok: bool
    slots_exact: bool
    slot_f1: float

    @property
    def success(self) -> bool:
        """Task success: command cases need right action + right params; abstention
        cases need a correct abstention."""
        if self.gold.expected_intent in COMMAND_INTENTS:
            return self.routing is RoutingOutcome.CORRECT_ACTION and self.intent_ok and self.slots_exact
        return self.routing is RoutingOutcome.CORRECT_ABSTENTION


@dataclass(frozen=True)
class BenchmarkResult:
    """Aggregate result over a dataset run for one model."""

    outcomes: list[CaseOutcome]

    @property
    def tsr(self) -> float:
        """Task Success Rate — the headline number."""
        if not self.outcomes:
            return 0.0
        return sum(o.success for o in self.outcomes) / len(self.outcomes)
