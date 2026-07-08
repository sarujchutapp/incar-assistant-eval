"""Grounded chat-corpus synthesis — draft (question, context, answer) triples
for human review.

The chat/informational sibling of ``incar_eval.synth``. Asks a model from a
**different family than the target** to draft grounded triples for one
question-type (ETA, fuel, weather, ...): a short car-telemetry/KB ``context``
with **fresh, novel values** plus a ``question`` whose ``answer`` is derivable
*only* from that context. Candidates are checked for grounding (the answer must
appear in the context), deduped against the existing chat corpus, and appended to
``fixtures/chat_flagged_for_human.json`` for human verification — never written
straight into the corpus (the grounding = contamination-defense rule, spec §5.1;
issue #15).

Depends only on the ``ModelClient`` port; tests inject a stub. The live path is
used only from the CLI.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from .chat import _faithful
from .client import ModelClient

_CORPUS_FILES = ("chat_cases.json", "chat_grounded.json", "chat_flagged_for_human.json")


def build_gen_prompt(question_type: str, n: int) -> str:
    return "\n".join([
        "You are helping build a grounded evaluation corpus for an in-car voice assistant.",
        "",
        f'Generate {n} diverse "{question_type}" cases. Each case is a triple:',
        "- context: a short car-telemetry / knowledge snippet the assistant can read.",
        "- question: what the driver asks.",
        "- answer: the ground-truth answer.",
        "",
        "Rules:",
        "- Use FRESH, NOVEL values (invent the numbers) so the answer cannot be guessed "
        "from world knowledge — it must be readable ONLY from the context.",
        "- The answer must appear verbatim (or as an obvious number/unit variant) in the context.",
        "- Do NOT give the answer away in the question.",
        "- Vary wording; do NOT produce templated or near-duplicate variants.",
        "",
        'Return ONLY a JSON array: [{"question": "...", "context": "...", "answer": "..."}, ...]',
    ])


def parse_candidates(raw: str) -> list[dict[str, Any]]:
    """Turn the model's JSON array into ``{question, context, fact}`` case dicts."""
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        raise ValueError("no JSON array found in model output")
    out: list[dict[str, Any]] = []
    for item in json.loads(match.group(0)):
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        context = str(item.get("context", "")).strip()
        answer = str(item.get("answer", "")).strip()
        if not (question and context and answer):
            continue
        out.append({"question": question, "context": context, "fact": answer})
    return out


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.lower())).strip()


def existing_questions(fixtures_dir: str | Path) -> set[str]:
    seen: set[str] = set()
    for name in _CORPUS_FILES:
        path = Path(fixtures_dir) / name
        if not path.exists():
            continue
        for case in json.loads(path.read_text(encoding="utf-8") or "[]"):
            seen.add(_normalize(case["question"]))
    return seen


def filter_candidates(
    candidates: list[dict[str, Any]], seen: set[str]
) -> tuple[list[dict[str, Any]], list[tuple[dict[str, Any], str]]]:
    """Drop duplicate questions and ungrounded triples. ``seen`` is updated in place.

    A triple is grounded when its answer is derivable from its context — reusing
    the chat faithfulness check (``_faithful(fact, context)``). A triple whose
    answer is already given away by the question is also dropped (not grounding-
    dependent, so contamination-vulnerable)."""
    kept: list[dict[str, Any]] = []
    rejected: list[tuple[dict[str, Any], str]] = []
    for case in candidates:
        norm = _normalize(case["question"])
        if norm in seen:
            rejected.append((case, "duplicate"))
            continue
        if not _faithful(case["fact"], case["context"]):
            rejected.append((case, "not grounded: answer not in context"))
            continue
        if _faithful(case["fact"], case["question"]):
            rejected.append((case, "answer leaks in question"))
            continue
        seen.add(norm)
        kept.append(case)
    return kept, rejected


def synthesize(
    client: ModelClient, question_type: str, n: int, fixtures_dir: str | Path
) -> dict[str, Any]:
    """Generate → parse → ground-check/dedupe → append survivors to the queue."""
    raw = client.complete(build_gen_prompt(question_type, n))
    candidates = parse_candidates(raw)
    kept, rejected = filter_candidates(candidates, existing_questions(fixtures_dir))

    flagged = Path(fixtures_dir) / "chat_flagged_for_human.json"
    queue = json.loads(flagged.read_text(encoding="utf-8") or "[]") if flagged.exists() else []
    queue.extend(kept)
    flagged.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {"generated": len(candidates), "kept": len(kept), "rejected": rejected, "queue_size": len(queue)}


def main() -> None:
    ap = argparse.ArgumentParser(description="Draft grounded chat cases for human review.")
    ap.add_argument("--question-type", required=True, help="e.g. 'ETA', 'fuel range', 'weather'")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--tier", default="sonnet", help="Claude tier (different family than the target)")
    ap.add_argument("--fixtures", default="fixtures")
    args = ap.parse_args()

    from .live_client import live_client_for_tier  # live path only

    client = live_client_for_tier(args.tier, max_tokens=2048)
    report = synthesize(client, args.question_type, args.n, args.fixtures)

    print(f"[{args.question_type}] generated={report['generated']} kept={report['kept']} "
          f"rejected={len(report['rejected'])}  queue={report['queue_size']}")
    for case, reason in report["rejected"]:
        print(f"  - dropped ({reason}): {case['question']!r}")


if __name__ == "__main__":
    main()
