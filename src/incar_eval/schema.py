"""The frozen v1 intent/slot schema (benchmark_spec.md §6.1).

Six command intents, each tagged with a single ``stakes`` axis, plus the two
abstention labels (`none`, `out_of_scope`) carried in ``models``. Ambiguity is a
per-case label (slice 3), not a schema axis.
"""

from typing import Literal

from .models import ABSTENTION_LABELS, AMBIGUITY_LABELS, COMMAND_INTENTS, GoldRecord

Stakes = Literal["low", "high"]


class IntentSpec:
    def __init__(self, name: str, slots: tuple[str, ...], stakes: Stakes, description: str) -> None:
        self.name = name
        self.slots = slots
        self.stakes = stakes
        self.description = description


SCHEMA: dict[str, IntentSpec] = {
    "set_climate": IntentSpec(
        "set_climate", ("temp", "zone"), "low",
        "Set cabin temperature. temp in degrees C; zone in {driver, passenger, all}.",
    ),
    "navigate": IntentSpec(
        "navigate", ("destination",), "low",
        "Start navigation to a destination.",
    ),
    "call_contact": IntentSpec(
        "call_contact", ("name",), "high",
        "Place a phone call to a named contact.",
    ),
    "play_media": IntentSpec(
        "play_media", ("title", "artist", "media_type"), "low",
        "Play media. media_type in {audio, video}, default audio.",
    ),
    "adjust_volume": IntentSpec(
        "adjust_volume", ("direction", "amount"), "low",
        "Change volume. direction in {up, down, set}.",
    ),
    "send_message": IntentSpec(
        "send_message", ("contact", "body"), "high",
        "Send a text message to a contact.",
    ),
}

# Single source of truth: the schema's command intents must match the constant.
assert frozenset(SCHEMA) == COMMAND_INTENTS


def known_labels() -> frozenset[str]:
    return COMMAND_INTENTS | ABSTENTION_LABELS


def schema_text() -> str:
    """Render the schema as the NL description block for the prompt."""
    return "\n".join(
        f"- {spec.name}({', '.join(spec.slots)}): {spec.description}"
        for spec in SCHEMA.values()
    )


def validate_record(record: GoldRecord) -> None:
    """Raise ValueError if a gold record's intent or slots aren't in the schema."""
    if record.expected_intent not in known_labels():
        raise ValueError(f"unknown intent label: {record.expected_intent!r}")
    if record.ambiguity not in AMBIGUITY_LABELS:
        raise ValueError(f"unknown ambiguity label: {record.ambiguity!r}")
    if record.expected_intent in COMMAND_INTENTS:
        allowed = set(SCHEMA[record.expected_intent].slots)
        extra = set(record.expected_slots) - allowed
        if extra:
            raise ValueError(
                f"intent {record.expected_intent!r} has no slots {sorted(extra)}; allowed: {sorted(allowed)}"
            )
    elif record.expected_slots:
        raise ValueError(f"abstention label {record.expected_intent!r} must have no slots")
