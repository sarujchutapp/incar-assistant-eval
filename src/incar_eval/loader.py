"""Load hand-authored gold cases and recorded model responses from JSON.

Lets the dataset and the recorded model outputs be authored by hand (two JSON
files) and run through the benchmark without editing Python — the by-hand path
when there's no live API. See docs/runbook.md.

cases.json     : a list of {utterance, expected_intent, expected_slots,
                 ambiguity?, car_state?}
responses.json : {model_name: {utterance: {intent, slots, mode?, eyes_free?}}}
"""

import json
from pathlib import Path
from typing import Any

from .client import FakeModelClient
from .models import CarState, GoldRecord
from .report import compare_tsr, format_report, model_report, run_models
from .schema import validate_record


def _to_gold(raw: dict[str, Any]) -> GoldRecord:
    car_state = None
    if raw.get("car_state"):
        car_state = CarState(vehicle_motion=raw["car_state"]["vehicle_motion"])
    slot_bands = None
    if raw.get("slot_bands"):
        slot_bands = {slot: (rng[0], rng[1]) for slot, rng in raw["slot_bands"].items()}
    record = GoldRecord(
        utterance=raw["utterance"],
        expected_intent=raw["expected_intent"],
        expected_slots=raw.get("expected_slots", {}),
        ambiguity=raw.get("ambiguity", "clear"),
        car_state=car_state,
        slot_bands=slot_bands,
    )
    validate_record(record)
    return record


def load_cases(path: str | Path) -> list[GoldRecord]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [_to_gold(item) for item in data]


def load_clients(path: str | Path) -> dict[str, FakeModelClient]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    clients: dict[str, FakeModelClient] = {}
    for name, responses in data.items():
        mapping = {str(utterance): json.dumps(call) for utterance, call in responses.items()}
        clients[str(name)] = FakeModelClient(mapping)
    return clients


def run_from_files(cases_path: str | Path, responses_path: str | Path, baseline: str | None = None) -> str:
    cases = load_cases(cases_path)
    clients = load_clients(responses_path)
    results = run_models(cases, clients)
    baseline = baseline or next(iter(results))
    reports = [model_report(name, result.outcomes) for name, result in results.items()]
    comparisons = {
        name: compare_tsr(results[baseline].outcomes, result.outcomes)
        for name, result in results.items()
        if name != baseline
    }
    return format_report(reports, baseline, comparisons)
