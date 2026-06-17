"""Multi-turn (context-based) cases: accumulated goal state, JGA + per-turn.

The assistant emits its full accumulated belief state each turn (MultiWOZ-style
DST). Joint Goal Accuracy is the fraction of turns whose entire accumulated state
exactly matches gold; per-turn accuracy is the fraction of turns whose active
intent is correct.
"""

from dataclasses import dataclass, field
from typing import Any

from .adapter import parse_tool_call
from .client import ModelClient
from .models import CarState, ToolCall
from .schema import schema_text

SYSTEM_PROMPT = (
    "You are a safety-first in-car voice assistant. Track the conversation and, "
    "each turn, respond with a JSON tool call whose intent is the active intent "
    "and whose slots are the FULL accumulated goal state so far."
)


@dataclass(frozen=True)
class Turn:
    utterance: str
    expected_intent: str
    expected_goal: dict[str, Any] = field(default_factory=dict)  # full accumulated state after this turn


@dataclass(frozen=True)
class DialogueCase:
    turns: list[Turn]
    car_state: CarState | None = None


@dataclass(frozen=True)
class DialogueOutcome:
    jga: float                      # fraction of turns with the full state exactly right
    per_turn_accuracy: float        # fraction of turns with the active intent right
    emissions: list[ToolCall]


def build_dialogue_prompt(history: list[str], current: str, car_state: CarState | None) -> str:
    context = f"Vehicle is {car_state.vehicle_motion}.\n" if car_state is not None else ""
    history_block = "".join(f"Earlier the driver said: \"{u}\"\n" for u in history)
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Available intents:\n{schema_text()}\n\n"
        f"{context}{history_block}"
        f'Driver now says: "{current}"'
    )


def score_dialogue(turns: list[Turn], emissions: list[ToolCall]) -> DialogueOutcome:
    if not turns:
        return DialogueOutcome(jga=0.0, per_turn_accuracy=0.0, emissions=emissions)
    goal_correct = sum(e.slots == t.expected_goal for t, e in zip(turns, emissions))
    intent_correct = sum(e.intent == t.expected_intent for t, e in zip(turns, emissions))
    return DialogueOutcome(
        jga=goal_correct / len(turns),
        per_turn_accuracy=intent_correct / len(turns),
        emissions=emissions,
    )


def run_dialogue(case: DialogueCase, client: ModelClient) -> DialogueOutcome:
    emissions: list[ToolCall] = []
    history: list[str] = []
    for turn in case.turns:
        prompt = build_dialogue_prompt(history, turn.utterance, case.car_state)
        emissions.append(parse_tool_call(client.complete(prompt)))
        history.append(turn.utterance)
    return score_dialogue(case.turns, emissions)
