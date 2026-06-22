import json
from pathlib import Path

import pytest

from incar_eval.loader import load_cases, load_clients, run_from_files


def _write(path: Path, obj: object) -> str:
    path.write_text(json.dumps(obj), encoding="utf-8")
    return str(path)


def test_load_cases_builds_gold_records(tmp_path: Path) -> None:
    path = Path(_write(tmp_path / "cases.json", [
        {"utterance": "warm it up", "expected_intent": "set_climate", "expected_slots": {"temp": 22}},
        {"utterance": "play the movie", "expected_intent": "play_media",
         "expected_slots": {"title": "Dune", "media_type": "video"},
         "ambiguity": "clear", "car_state": {"vehicle_motion": "moving"}},
    ]))
    cases = load_cases(path)
    assert len(cases) == 2
    assert cases[0].expected_intent == "set_climate"
    assert cases[1].car_state is not None
    assert cases[1].car_state.vehicle_motion == "moving"


def test_load_cases_validates_against_schema(tmp_path: Path) -> None:
    path = Path(_write(tmp_path / "bad.json", [
        {"utterance": "open the sunroof", "expected_intent": "open_sunroof", "expected_slots": {}},
    ]))
    with pytest.raises(ValueError):
        load_cases(path)


def test_load_clients_builds_callable_models(tmp_path: Path) -> None:
    path = Path(_write(tmp_path / "responses.json", {
        "strong": {"warm it up": {"intent": "set_climate", "slots": {"temp": 22}}},
    }))
    clients = load_clients(path)
    assert "strong" in clients
    raw = clients["strong"].complete('... Driver said: "warm it up"')
    assert json.loads(raw)["intent"] == "set_climate"


def test_run_from_files_produces_a_report(tmp_path: Path) -> None:
    cases = Path(_write(tmp_path / "cases.json", [
        {"utterance": "warm it up", "expected_intent": "set_climate", "expected_slots": {"temp": 22}},
    ]))
    responses = Path(_write(tmp_path / "responses.json", {
        "strong": {"warm it up": {"intent": "set_climate", "slots": {"temp": 22}}},
        "weak": {"warm it up": {"intent": "set_climate", "slots": {"temp": 0}}},
    }))
    report = run_from_files(cases, responses, baseline="strong")
    assert "strong" in report
    assert "weak" in report
    assert "TSR:" in report
