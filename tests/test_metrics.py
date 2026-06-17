from incar_eval.metrics import compute_metrics
from incar_eval.models import CaseOutcome, GoldRecord, ToolCall
from incar_eval.scorer import score_case


def _o(g_intent: str, g_slots: dict[str, object], e_intent: str, e_slots: dict[str, object]) -> CaseOutcome:
    return score_case(GoldRecord("u", g_intent, g_slots), ToolCall(e_intent, e_slots))


def test_metrics_breakdown() -> None:
    outcomes = [
        _o("set_climate", {"temp": 22}, "set_climate", {"temp": 22}),  # correct action
        _o("call_contact", {"name": "mom"}, "none", {}),               # false rejection
        _o("none", {}, "set_climate", {"temp": 20}),                   # false activation
        _o("none", {}, "none", {}),                                    # correct abstention
        _o("out_of_scope", {}, "navigate", {"destination": "x"}),      # capability hallucination
    ]
    m = compute_metrics(outcomes)
    assert m.n == 5
    assert m.routing_accuracy == 2 / 5            # correct action + correct abstention
    assert m.false_rejection_rate == 1 / 2        # over the 2 command cases
    assert m.false_activation_rate == 1 / 2        # over the 2 none cases
    assert m.capability_hallucination_rate == 1.0  # over the 1 oos case
    assert m.tsr == 2 / 5


def test_intent_and_slot_metrics_over_acted_commands() -> None:
    outcomes = [
        _o("set_climate", {"temp": 22, "zone": "all"}, "set_climate", {"temp": 22, "zone": "all"}),  # f1 1.0
        _o("set_climate", {"temp": 22, "zone": "all"}, "set_climate", {"temp": 22, "zone": "driver"}),  # f1 0.5
        _o("navigate", {"destination": "home"}, "play_media", {"title": "x"}),  # acted, wrong intent
        _o("call_contact", {"name": "mom"}, "none", {}),  # false rejection -> excluded from slot/intent
    ]
    m = compute_metrics(outcomes)
    # acted commands: first three. intent correct on 2 of 3.
    assert m.intent_accuracy == 2 / 3
    # slot f1 averaged over acted commands: (1.0 + 0.5 + 0.0) / 3
    assert m.slot_f1 == (1.0 + 0.5 + 0.0) / 3


def test_empty_outcomes_are_zero_not_error() -> None:
    m = compute_metrics([])
    assert m.n == 0
    assert m.routing_accuracy == 0.0
    assert m.slot_f1 == 0.0
