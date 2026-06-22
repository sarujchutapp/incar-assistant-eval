import json
from pathlib import Path

import pytest

from incar_eval.loader import (
    load_cases,
    load_chat_cases,
    load_chat_clients,
    load_clients,
    run_chat_from_files,
    run_from_files,
    run_open_tail,
)


def _verdict(winner: str) -> dict[str, object]:
    return {
        "critique": "Answer is more faithful, relevant, and concise.",
        "dimensions": {"faithfulness": winner, "relevancy": winner, "conciseness": winner},
        "winner": winner,
    }


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


def test_load_chat_cases_builds_chat_cases(tmp_path: Path) -> None:
    path = Path(_write(tmp_path / "chat_cases.json", [
        {"question": "what's my ETA?", "fact": "25 minutes"},
        {"question": "how much fuel is left?", "fact": "low"},
    ]))
    cases = load_chat_cases(path)
    assert len(cases) == 2
    assert cases[0].question == "what's my ETA?"
    assert cases[0].fact == "25 minutes"


def test_load_chat_clients_builds_callable_models(tmp_path: Path) -> None:
    path = Path(_write(tmp_path / "chat_responses.json", {
        "strong": {"what's my ETA?": "Your ETA is about 25 minutes."},
    }))
    clients = load_chat_clients(path)
    assert "strong" in clients
    assert "25 minutes" in clients["strong"].complete('Driver asks: "what\'s my ETA?"')


def test_run_chat_from_files_scores_each_model(tmp_path: Path) -> None:
    cases = Path(_write(tmp_path / "chat_cases.json", [
        {"question": "what's my ETA?", "fact": "25 minutes"},
        {"question": "how much fuel is left?", "fact": "low"},
    ]))
    responses = Path(_write(tmp_path / "chat_responses.json", {
        "strong": {
            "what's my ETA?": "About 25 minutes.",
            "how much fuel is left?": "Fuel is running low.",
        },
        "weak": {
            "what's my ETA?": "About 25 minutes.",
            "how much fuel is left?": "Plenty of fuel, tank is high.",  # unfaithful
        },
    }))
    metrics = run_chat_from_files(cases, responses)
    assert metrics["strong"].faithfulness_rate == 1.0
    assert metrics["weak"].faithfulness_rate == 0.5


def test_run_open_tail_ranks_consistent_winner_higher(tmp_path: Path) -> None:
    # strong wins both directions of the swap -> consistent winner; weak loses.
    path = Path(_write(tmp_path / "open_tail.json", {
        "models": [
            {"name": "strong", "family": "anthropic"},
            {"name": "weak", "family": "openai"},
        ],
        "judge_family": "google",
        "questions": [
            {
                "question": "Highway or surface streets downtown right now?",
                "answers": {
                    "strong": "Highway — clear and about 12 minutes faster right now.",
                    "weak": "Either one is fine, up to you.",
                },
                "pairs": [
                    # forward: strong in slot A -> winner A; reverse: strong in slot B -> winner B.
                    {"a": "strong", "b": "weak", "forward": _verdict("A"), "reverse": _verdict("B")},
                ],
            },
        ],
    }))
    strengths = run_open_tail(path)
    assert strengths["strong"].value > strengths["weak"].value


# --- shipped fixtures (fixtures/chat_*.json) ----------------------------------

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_shipped_chat_dataset_runs_and_discriminates() -> None:
    metrics = run_chat_from_files(_FIXTURES / "chat_cases.json", _FIXTURES / "chat_responses.json")
    # objective-by-construction: faithfulness separates the tiers.
    assert metrics["strong"].faithfulness_rate > metrics["mid"].faithfulness_rate
    assert metrics["mid"].faithfulness_rate > metrics["weak"].faithfulness_rate


def test_shipped_open_tail_ranks_tiers() -> None:
    strengths = run_open_tail(_FIXTURES / "chat_open_tail.json")
    assert strengths["strong"].value > strengths["mid"].value > strengths["weak"].value
