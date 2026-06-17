import pytest

from incar_eval.models import ABSTENTION_LABELS, COMMAND_INTENTS, GoldRecord
from incar_eval.schema import SCHEMA, validate_record


def test_six_command_intents_present() -> None:
    assert COMMAND_INTENTS == frozenset(
        {"set_climate", "navigate", "call_contact", "play_media", "adjust_volume", "send_message"}
    )


def test_schema_keys_match_command_intents() -> None:
    assert frozenset(SCHEMA) == COMMAND_INTENTS


def test_abstention_labels() -> None:
    assert ABSTENTION_LABELS == frozenset({"none", "out_of_scope"})


def test_stakes_tagged() -> None:
    assert SCHEMA["call_contact"].stakes == "high"
    assert SCHEMA["send_message"].stakes == "high"
    assert SCHEMA["set_climate"].stakes == "low"
    assert SCHEMA["adjust_volume"].stakes == "low"


def test_validate_accepts_known_records() -> None:
    validate_record(GoldRecord("call mom", "call_contact", {"name": "mom"}))
    validate_record(GoldRecord("nice day", "none", {}))
    validate_record(GoldRecord("open the sunroof", "out_of_scope", {}))


def test_validate_rejects_unknown_intent() -> None:
    with pytest.raises(ValueError):
        validate_record(GoldRecord("open the sunroof", "open_sunroof", {}))


def test_validate_rejects_unknown_slot() -> None:
    with pytest.raises(ValueError):
        validate_record(GoldRecord("call mom", "call_contact", {"nickname": "mom"}))
