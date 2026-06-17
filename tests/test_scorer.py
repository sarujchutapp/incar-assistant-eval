from incar_eval.models import GoldRecord, RoutingOutcome, ToolCall
from incar_eval.scorer import score_case


def test_correct_command_action() -> None:
    gold = GoldRecord("warm up", "set_climate", {"temp": 22, "zone": "all"})
    outcome = score_case(gold, ToolCall("set_climate", {"temp": 22, "zone": "all"}))
    assert outcome.routing is RoutingOutcome.CORRECT_ACTION
    assert outcome.intent_ok
    assert outcome.slots_exact
    assert outcome.slot_f1 == 1.0
    assert outcome.success


def test_wrong_slot_gives_partial_f1_and_fails() -> None:
    gold = GoldRecord("warm up", "set_climate", {"temp": 22, "zone": "all"})
    outcome = score_case(gold, ToolCall("set_climate", {"temp": 22, "zone": "driver"}))
    assert outcome.routing is RoutingOutcome.CORRECT_ACTION
    assert not outcome.slots_exact
    assert outcome.slot_f1 == 0.5  # one of two slots correct
    assert not outcome.success


def test_wrong_intent_given_it_acted() -> None:
    gold = GoldRecord("turn up the AC", "set_climate", {"temp": 22})
    outcome = score_case(gold, ToolCall("navigate", {"destination": "home"}))
    assert outcome.routing is RoutingOutcome.CORRECT_ACTION  # it acted
    assert not outcome.intent_ok  # but on the wrong action
    assert not outcome.success


def test_false_rejection_when_command_ignored() -> None:
    gold = GoldRecord("call mom", "call_contact", {"name": "mom"})
    outcome = score_case(gold, ToolCall("none", {}))
    assert outcome.routing is RoutingOutcome.FALSE_REJECTION
    assert not outcome.success


def test_false_activation_on_none() -> None:
    gold = GoldRecord("nice weather huh", "none", {})
    outcome = score_case(gold, ToolCall("set_climate", {"temp": 22, "zone": "all"}))
    assert outcome.routing is RoutingOutcome.FALSE_ACTIVATION
    assert not outcome.success


def test_correct_abstention_on_none() -> None:
    gold = GoldRecord("nice weather huh", "none", {})
    outcome = score_case(gold, ToolCall("none", {}))
    assert outcome.routing is RoutingOutcome.CORRECT_ABSTENTION
    assert outcome.success


def test_capability_hallucination_on_out_of_scope() -> None:
    gold = GoldRecord("open the sunroof", "out_of_scope", {})
    outcome = score_case(gold, ToolCall("set_climate", {"temp": 22}))
    assert outcome.routing is RoutingOutcome.CAPABILITY_HALLUCINATION
    assert not outcome.success


def test_correct_abstention_on_out_of_scope() -> None:
    gold = GoldRecord("open the sunroof", "out_of_scope", {})
    outcome = score_case(gold, ToolCall("out_of_scope", {}))
    assert outcome.routing is RoutingOutcome.CORRECT_ABSTENTION
    assert outcome.success


def test_scorer_is_pure() -> None:
    gold = GoldRecord("warm up", "set_climate", {"temp": 22, "zone": "all"})
    emitted = ToolCall("set_climate", {"temp": 22, "zone": "all"})
    assert score_case(gold, emitted) == score_case(gold, emitted)
