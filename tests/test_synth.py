import json
from pathlib import Path

import pytest

from incar_eval.synth import (
    build_prompt,
    filter_candidates,
    parse_candidates,
    synthesize,
)


class _Stub:
    def __init__(self, raw: str) -> None:
        self._raw = raw

    def complete(self, prompt: str) -> str:  # noqa: ARG002
        return self._raw


def test_build_prompt_varies_by_cell() -> None:
    clear = build_prompt("call_contact", "clear", 5)
    assert "expected_slots" in clear  # slots requested for clear
    ambiguous = build_prompt("call_contact", "ambiguous", 5)
    assert "no slots" in ambiguous  # no slots for ambiguous
    assert 'intent "call_contact"' in clear


def test_build_prompt_rejects_bad_cell() -> None:
    with pytest.raises(ValueError):
        build_prompt("call_contact", None, 5)  # command needs ambiguity
    with pytest.raises(ValueError):
        build_prompt("none", "clear", 5)  # abstention takes no ambiguity


def test_parse_fixes_cell_labels() -> None:
    raw = '[{"utterance": "Call Dad", "expected_slots": {"name": "Dad"}}]'
    (case,) = parse_candidates(raw, "call_contact", "clear")
    assert case == {
        "utterance": "Call Dad",
        "expected_intent": "call_contact",
        "expected_slots": {"name": "Dad"},
        "ambiguity": "clear",
    }


def test_parse_drops_slots_for_ambiguous_and_tags_motion() -> None:
    raw = '[{"utterance": "put something on", "expected_slots": {"title": "x"}}]'
    (case,) = parse_candidates(raw, "play_media", "ambiguous", motion="moving")
    assert case["expected_slots"] == {}  # ambiguous -> slots ignored
    assert case["car_state"] == {"vehicle_motion": "moving"}


def test_filter_drops_duplicates_and_invalid() -> None:
    seen = {"call sarah"}  # already in corpus
    candidates = [
        {"utterance": "Call Dad", "expected_intent": "call_contact", "expected_slots": {"name": "Dad"}, "ambiguity": "clear"},
        {"utterance": "Call Sarah", "expected_intent": "call_contact", "expected_slots": {"name": "Sarah"}, "ambiguity": "clear"},
        {"utterance": "Cool it to backseat", "expected_intent": "set_climate", "expected_slots": {"zone": "backseat"}, "ambiguity": "clear"},
    ]
    kept, rejected = filter_candidates(candidates, seen)
    assert [c["utterance"] for c in kept] == ["Call Dad"]
    reasons = {c["utterance"]: r for c, r in rejected}
    assert reasons["Call Sarah"] == "duplicate"
    assert reasons["Cool it to backseat"].startswith("invalid:")  # zone not in possible_values


def test_synthesize_writes_survivors_to_queue(tmp_path: Path) -> None:
    (tmp_path / "cases.json").write_text(
        json.dumps([{"utterance": "Call Sarah", "expected_intent": "call_contact",
                     "expected_slots": {"name": "Sarah"}, "ambiguity": "clear"}]),
        encoding="utf-8",
    )
    raw = json.dumps([
        {"utterance": "Call Dad", "expected_slots": {"name": "Dad"}},
        {"utterance": "Call Sarah", "expected_slots": {"name": "Sarah"}},  # dup of existing
    ])
    report = synthesize(_Stub(raw), "call_contact", "clear", 2, None, tmp_path)

    assert report["kept"] == 1
    assert report["generated"] == 2
    queue = json.loads((tmp_path / "flagged_for_human.json").read_text(encoding="utf-8"))
    assert [c["utterance"] for c in queue] == ["Call Dad"]
