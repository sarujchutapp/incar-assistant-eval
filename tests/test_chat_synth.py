import json
from pathlib import Path

from incar_eval.chat_synth import (
    build_gen_prompt,
    filter_candidates,
    parse_candidates,
    synthesize,
)


class _Stub:
    def __init__(self, raw: str) -> None:
        self._raw = raw

    def complete(self, prompt: str) -> str:  # noqa: ARG002
        return self._raw


def test_parse_maps_answer_to_fact() -> None:
    raw = '[{"question": "ETA?", "context": "ETA: 25 minutes.", "answer": "25 minutes"}]'
    (case,) = parse_candidates(raw)
    assert case == {"question": "ETA?", "context": "ETA: 25 minutes.", "fact": "25 minutes"}


def test_filter_drops_ungrounded_dup_and_leak() -> None:
    seen = {"what is my eta"}  # already in corpus
    candidates = [
        # grounded, novel -> kept
        {"question": "How far to the next charger?", "context": "Next charger: 31 miles ahead.", "fact": "31 miles"},
        # duplicate question -> dropped
        {"question": "What is my ETA?", "context": "ETA: 14 minutes.", "fact": "14 minutes"},
        # answer not in context -> dropped (not grounded)
        {"question": "What's the cabin temp?", "context": "Outside: cold.", "fact": "21 degrees"},
        # answer leaks in the question -> dropped
        {"question": "Is my range really 50 miles?", "context": "Range: 50 miles.", "fact": "50 miles"},
    ]
    kept, rejected = filter_candidates(candidates, seen)
    assert [c["question"] for c in kept] == ["How far to the next charger?"]
    reasons = {c["question"]: r for c, r in rejected}
    assert reasons["What is my ETA?"] == "duplicate"
    assert reasons["What's the cabin temp?"].startswith("not grounded")
    assert reasons["Is my range really 50 miles?"].startswith("answer leaks")


def test_synthesize_writes_survivors_to_queue(tmp_path: Path) -> None:
    (tmp_path / "chat_cases.json").write_text(
        json.dumps([{"question": "What is my ETA?", "fact": "25 minutes"}]), encoding="utf-8",
    )
    raw = json.dumps([
        {"question": "How far to the next charger?", "context": "Next charger: 31 miles ahead.", "answer": "31 miles"},
        {"question": "What is my ETA?", "context": "ETA: 14 minutes.", "answer": "14 minutes"},  # dup
    ])
    report = synthesize(_Stub(raw), "fuel range", 2, tmp_path)
    assert report["generated"] == 2
    assert report["kept"] == 1
    queue = json.loads((tmp_path / "chat_flagged_for_human.json").read_text(encoding="utf-8"))
    assert [c["question"] for c in queue] == ["How far to the next charger?"]


def test_gen_prompt_steers_by_question_type_and_demands_grounding() -> None:
    prompt = build_gen_prompt("fuel range", 5)
    assert "fuel range" in prompt
    assert "context" in prompt and "question" in prompt and "answer" in prompt
    assert "FRESH" in prompt or "novel" in prompt.lower()
