import json
from pathlib import Path

from incar_eval.chat import ChatMetrics
from incar_eval.client import FakeModelClient
from incar_eval.judge import Strength
from incar_eval.loader import run_chat_from_files, run_open_tail
from incar_eval.models import GoldRecord
from incar_eval.report import run_models
from incar_eval.scorecard import build_scorecards, format_scorecards

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _raw(intent: str, mode: str = "execute", **slots: object) -> str:
    return json.dumps({"intent": intent, "mode": mode, "slots": slots})


DATASET = [
    GoldRecord("turn the temperature up to 22", "set_climate", {"temp": 22, "zone": "all"}, "clear"),
    GoldRecord("navigate to the airport", "navigate", {"destination": "airport"}, "clear"),
]


def _client(temp: int, dest: str) -> FakeModelClient:
    return FakeModelClient({
        "turn the temperature up to 22": _raw("set_climate", temp=temp, zone="all"),
        "navigate to the airport": _raw("navigate", destination=dest),
    })


def test_scorecard_carries_command_report_and_mcnemar() -> None:
    results = run_models(DATASET, {"strong": _client(22, "airport"), "weak": _client(0, "home")})
    cards = build_scorecards(results, baseline="strong")

    assert cards["strong"].command.proportions["tsr"].value == 1.0
    assert cards["weak"].command.proportions["tsr"].value == 0.0
    assert cards["strong"].vs_baseline is None       # baseline has no self-comparison
    assert cards["weak"].vs_baseline is not None

    text = format_scorecards(cards, "strong")
    assert "strong" in text and "weak" in text
    assert "TSR" in text and "McNemar" in text


def test_scorecard_includes_chat_bt_jga_when_provided() -> None:
    results = run_models(DATASET, {"strong": _client(22, "airport"), "weak": _client(0, "home")})
    cards = build_scorecards(
        results, "strong",
        chat_metrics={"strong": ChatMetrics(2, 1.0, 0.5), "weak": ChatMetrics(2, 0.5, 0.3)},
        chat_bt={"strong": Strength(0.8, 0.7, 0.9), "weak": Strength(0.2, 0.1, 0.3)},
        jga={"strong": 1.0, "weak": 0.5},
    )
    assert cards["strong"].chat is not None and cards["strong"].chat.faithfulness_rate == 1.0
    assert cards["strong"].chat_bt is not None and cards["strong"].chat_bt.value == 0.8
    assert cards["strong"].jga == 1.0

    text = format_scorecards(cards, "strong")
    for token in ("faithfulness", "BT", "JGA", "calibration"):
        assert token in text


def test_scorecard_combines_command_run_with_shipped_chat_run() -> None:
    # A command run + the real shipped chat run, assembled into one view (acceptance).
    results = run_models(
        DATASET,
        {"strong": _client(22, "airport"), "mid": _client(22, "home"), "weak": _client(0, "home")},
    )
    chat = run_chat_from_files(_FIXTURES / "chat_cases.json", _FIXTURES / "chat_responses.json")
    bt = run_open_tail(_FIXTURES / "chat_open_tail.json")

    cards = build_scorecards(results, "strong", chat_metrics=chat, chat_bt=bt)

    # one combined object per model, command + chat both present
    assert set(cards) == {"strong", "mid", "weak"}
    strong_chat, weak_chat = cards["strong"].chat, cards["weak"].chat
    strong_bt, weak_bt = cards["strong"].chat_bt, cards["weak"].chat_bt
    assert strong_chat is not None and weak_chat is not None
    assert strong_bt is not None and weak_bt is not None
    # discrimination carried through from both quadrants
    assert strong_chat.faithfulness_rate > weak_chat.faithfulness_rate
    assert strong_bt.value > weak_bt.value

    text = format_scorecards(cards, "strong")
    assert sum(1 for ln in text.splitlines() if ln.startswith("== ")) == 3  # a block per model
    assert "chat faithfulness" in text and "chat BT" in text
