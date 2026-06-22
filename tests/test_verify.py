import json

import pytest

from incar_eval.client import FakeModelClient
from incar_eval.models import CarState, GoldRecord
from incar_eval.verify import CaseSpec, VerifierModel, verify_batch, verify_case


def _client(mapping: dict[str, tuple[str, dict[str, object]]]) -> FakeModelClient:
    return FakeModelClient(
        {u: json.dumps({"intent": intent, "slots": slots}) for u, (intent, slots) in mapping.items()}
    )


U = "make it 22 degrees"


def _verifier(label: str, family: str, intent: str, **slots: object) -> VerifierModel:
    return VerifierModel(label, family, FakeModelClient({U: json.dumps({"intent": intent, "slots": slots})}))


def test_two_of_three_agree_auto_accepts() -> None:
    verifiers = [
        _verifier("m1", "openai", "set_climate", temp=22),
        _verifier("m2", "anthropic", "set_climate", temp=22),
        _verifier("m3", "google", "navigate", destination="home"),  # the odd one out
    ]
    result = verify_case(U, verifiers)
    assert result.status == "auto_accepted"
    assert result.accepted == GoldRecord(U, "set_climate", {"temp": 22})


def test_all_disagree_is_flagged() -> None:
    verifiers = [
        _verifier("m1", "openai", "set_climate", temp=22),
        _verifier("m2", "anthropic", "set_climate", temp=21),
        _verifier("m3", "google", "navigate", destination="home"),
    ]
    result = verify_case(U, verifiers)
    assert result.status == "flagged_disagreement"
    assert result.accepted is None


def test_tie_is_flagged() -> None:
    verifiers = [
        _verifier("m1", "openai", "set_climate", temp=22),
        _verifier("m2", "anthropic", "set_climate", temp=21),
    ]
    result = verify_case(U, verifiers)
    assert result.status == "flagged_disagreement"


def test_force_manual_always_flags_even_if_agreed() -> None:
    verifiers = [
        _verifier("m1", "openai", "send_message", contact="dad", body="hi"),
        _verifier("m2", "anthropic", "send_message", contact="dad", body="hi"),
    ]
    result = verify_case(U, verifiers, force_manual=True)
    assert result.status == "flagged_manual"
    assert result.accepted is None


def test_ambiguous_cells_always_flagged() -> None:
    verifiers = [
        _verifier("m1", "openai", "call_contact", name="alex"),
        _verifier("m2", "anthropic", "call_contact", name="alex"),
    ]
    result = verify_case(U, verifiers, ambiguity="ambiguous")
    assert result.status == "flagged_manual"


def test_cross_family_guard_requires_two_families() -> None:
    verifiers = [
        _verifier("m1", "openai", "set_climate", temp=22),
        _verifier("m2", "openai", "set_climate", temp=22),  # same family
    ]
    with pytest.raises(ValueError):
        verify_case(U, verifiers)


def test_verify_batch_reports_auto_accept_rate() -> None:
    mapping: dict[str, tuple[str, dict[str, object]]] = {
        "turn it up to 22": ("set_climate", {"temp": 22}),
        "text my boss the update": ("send_message", {"contact": "boss", "body": "update"}),
    }
    verifiers = [
        VerifierModel("m1", "openai", _client(mapping)),
        VerifierModel("m2", "anthropic", _client(mapping)),
    ]
    specs = [
        CaseSpec("turn it up to 22"),                              # agreed -> auto
        CaseSpec("text my boss the update", force_manual=True),    # safety -> flagged
    ]
    report = verify_batch(specs, verifiers)
    assert len(report.accepted) == 1
    assert len(report.flagged) == 1
    assert report.auto_accept_rate == 0.5


def test_car_state_passes_through_to_accepted_gold() -> None:
    moving = CarState(vehicle_motion="moving")
    verifiers = [
        VerifierModel("m1", "openai", FakeModelClient({U: json.dumps({"intent": "set_climate", "slots": {"temp": 22}})})),
        VerifierModel("m2", "anthropic", FakeModelClient({U: json.dumps({"intent": "set_climate", "slots": {"temp": 22}})})),
    ]
    result = verify_case(U, verifiers, car_state=moving)
    assert result.accepted is not None
    assert result.accepted.car_state == moving
