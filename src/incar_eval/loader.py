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

from .chat import ChatCase, ChatMetrics, run_chat_benchmark
from .client import FakeModelClient
from .judge import (
    Comparison,
    Strength,
    bradley_terry_with_ci,
    build_judge_prompt,
    compare_pair,
    normalize_answer,
)
from .models import CarState, GoldRecord
from .report import compare_tsr, format_report, model_report, run_models
from .schema import validate_record


def _to_gold(raw: dict[str, Any]) -> GoldRecord:
    car_state = None
    if raw.get("car_state"):
        cs = raw["car_state"]
        car_state = CarState(
            vehicle_motion=cs.get("vehicle_motion", "parked"),
            climate_range=cs.get("climate_range"),
            volume_range=cs.get("volume_range"),
        )
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
        intensity=raw.get("intensity"),
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


# --- chat / informational quadrant --------------------------------------------
#
# chat_cases.json     : a list of {question, fact}
# chat_responses.json : {model_name: {question: answer_text}}


def load_chat_cases(path: str | Path) -> list[ChatCase]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        ChatCase(
            question=item["question"],
            fact=item.get("fact", ""),
            context=item.get("context", ""),
            answerable=item.get("answerable", True),
        )
        for item in data
    ]


def load_chat_clients(path: str | Path) -> dict[str, FakeModelClient]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {
        str(name): FakeModelClient({str(q): str(answer) for q, answer in answers.items()})
        for name, answers in data.items()
    }


def run_chat_from_files(
    cases_path: str | Path, responses_path: str | Path
) -> dict[str, ChatMetrics]:
    cases = load_chat_cases(cases_path)
    clients = load_chat_clients(responses_path)
    return {name: run_chat_benchmark(cases, client)[1] for name, client in clients.items()}


# --- open / subjective tail (pairwise judge -> Bradley-Terry) ------------------
#
# open_tail.json : {
#   "models": [{"name", "family"}, ...],
#   "judge_family": str,                       # must differ from every target
#   "questions": [{
#     "question": str,
#     "answers": {model_name: answer_text},
#     "pairs": [{"a", "b", "forward": <verdict>, "reverse": <verdict>}]
#   }]
# }
# Verdicts are recorded per swap direction (forward = a in slot A); the judge is
# replayed deterministically via a FakeModelClient keyed by the exact judge prompt.


def run_open_tail(path: str | Path) -> dict[str, Strength]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    families = {str(m["name"]): str(m["family"]) for m in data["models"]}
    models = list(families)
    judge_family = str(data["judge_family"])

    recorded: dict[str, str] = {}
    comparisons: list[Comparison] = []
    for q in data["questions"]:
        question = str(q["question"])
        answers = {str(name): str(text) for name, text in q["answers"].items()}
        for pair in q["pairs"]:
            a, b = str(pair["a"]), str(pair["b"])
            fwd = build_judge_prompt(question, normalize_answer(answers[a]), normalize_answer(answers[b]))
            rev = build_judge_prompt(question, normalize_answer(answers[b]), normalize_answer(answers[a]))
            recorded[fwd] = json.dumps(pair["forward"])
            recorded[rev] = json.dumps(pair["reverse"])

    judge = FakeModelClient(recorded)
    for q in data["questions"]:
        question = str(q["question"])
        answers = {str(name): str(text) for name, text in q["answers"].items()}
        for pair in q["pairs"]:
            a, b = str(pair["a"]), str(pair["b"])
            comparisons.append(
                compare_pair(
                    question,
                    a, answers[a], families[a],
                    b, answers[b], families[b],
                    judge, judge_family,
                )
            )
    return bradley_terry_with_ci(models, comparisons)
