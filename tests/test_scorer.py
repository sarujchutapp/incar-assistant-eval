from incar_eval.models import GoldRecord, ToolCall
from incar_eval.scorer import score_case


def _gold(temp: int = 21, zone: str = "all") -> GoldRecord:
    return GoldRecord(
        utterance="set the temperature",
        expected_intent="set_climate",
        expected_slots={"temp": temp, "zone": zone},
    )


def test_exact_match_is_success() -> None:
    outcome = score_case(_gold(), ToolCall("set_climate", {"temp": 21, "zone": "all"}))
    assert outcome.intent_ok
    assert outcome.slots_ok
    assert outcome.success


def test_wrong_slot_fails() -> None:
    outcome = score_case(_gold(temp=21), ToolCall("set_climate", {"temp": 19, "zone": "all"}))
    assert outcome.intent_ok
    assert not outcome.slots_ok
    assert not outcome.success


def test_wrong_intent_fails() -> None:
    outcome = score_case(_gold(), ToolCall("navigate", {"temp": 21, "zone": "all"}))
    assert not outcome.intent_ok
    assert not outcome.success


def test_scorer_is_pure() -> None:
    gold = _gold()
    emitted = ToolCall("set_climate", {"temp": 21, "zone": "all"})
    assert score_case(gold, emitted) == score_case(gold, emitted)
