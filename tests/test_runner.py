import json

import pytest

from incar_eval.adapter import parse_tool_call, run_case
from incar_eval.client import FakeModelClient
from incar_eval.models import GoldRecord, ToolCall
from incar_eval.runner import run_benchmark


def _raw(intent: str, **slots: object) -> str:
    return json.dumps({"intent": intent, "slots": slots})


def test_parse_tool_call() -> None:
    call = parse_tool_call('{"intent": "set_climate", "slots": {"temp": 21, "zone": "all"}}')
    assert call == ToolCall("set_climate", {"temp": 21, "zone": "all"})


def test_parse_tool_call_tolerates_unknown_mode() -> None:
    # Real models emit e.g. mode "none" on abstentions; ingestion must not crash.
    from incar_eval.models import ResponseMode

    call = parse_tool_call('{"intent": "none", "slots": {}, "mode": "none"}')
    assert call.mode is ResponseMode.EXECUTE


def test_run_case_goes_through_the_client() -> None:
    record = GoldRecord("make it 21", "set_climate", {"temp": 21, "zone": "all"})
    client = FakeModelClient({"make it 21": _raw("set_climate", temp=21, zone="all")})
    assert run_case(record, client) == ToolCall("set_climate", {"temp": 21, "zone": "all"})


def test_end_to_end_tsr_with_fake_client() -> None:
    dataset = [
        GoldRecord("make it 21", "set_climate", {"temp": 21, "zone": "all"}),
        GoldRecord("warm up the driver side", "set_climate", {"temp": 23, "zone": "driver"}),
        GoldRecord("set it to 20", "set_climate", {"temp": 20, "zone": "all"}),
    ]
    # third canned response has a wrong temp -> 2/3 success
    client = FakeModelClient(
        {
            "make it 21": _raw("set_climate", temp=21, zone="all"),
            "warm up the driver side": _raw("set_climate", temp=23, zone="driver"),
            "set it to 20": _raw("set_climate", temp=18, zone="all"),
        }
    )
    result = run_benchmark(dataset, client)
    assert len(result.outcomes) == 3
    assert result.tsr == pytest.approx(2 / 3)


def test_empty_dataset_tsr_is_zero() -> None:
    result = run_benchmark([], FakeModelClient({}))
    assert result.tsr == 0.0
