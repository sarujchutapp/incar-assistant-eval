"""Core data shapes for the benchmark.

Kept deliberately small for the slice-1 tracer bullet: a structured tool call,
a gold record (the answer key), and the per-case / aggregate outcomes the scorer
and runner produce. Later slices extend these (abstention, ambiguity, car_state).
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    """A structured action the assistant emitted (intent + parameters)."""

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
    intent_ok: bool
    slots_ok: bool

    @property
    def success(self) -> bool:
        """Task success = right action AND right parameters end-to-end."""
        return self.intent_ok and self.slots_ok


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
