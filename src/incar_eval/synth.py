"""Corpus synthesis helper — draft candidate cases with an LLM for human review.

Grows the command/control corpus toward the ~400-case target (roadmap #10) by
asking a model from a **different family than the target** to draft diverse
utterances for one cell (intent x ambiguity [x motion]). Candidates are
schema-validated and deduped against the existing corpus, then appended to
``fixtures/flagged_for_human.json`` for human verification — never written
straight into the corpus (the no-pure-templating / human-verify rule, spec 5.1).

Depends only on the ``ModelClient`` port; tests inject a stub. The live path
(a Claude tier via ``live_client``) is used only from the CLI.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from .client import ModelClient
from .loader import _to_gold
from .models import ABSTENTION_LABELS, AMBIGUITY_LABELS
from .schema import SCHEMA, schema_text

_CORPUS_FILES = ("cases.json", "hard_cases.json", "synth_cases.json", "flagged_for_human.json")

_AMBIGUITY_GUIDANCE = {
    "clear": "all required slot values are stated or unambiguously inferable from the utterance",
    "defaultable": "a required slot is unstated but a safe convention exists and a wrong guess is cheap; "
    "the assistant should act on the default",
    "ambiguous": "a required slot is unstated with no safe default (unknown referent, or a wrong/irreversible "
    "guess); the assistant should ask instead of act",
}


def _validate_cell(intent: str, ambiguity: str | None) -> None:
    if intent in ABSTENTION_LABELS:
        if ambiguity is not None:
            raise ValueError(f"{intent!r} is an abstention cell; do not pass an ambiguity")
    elif intent in SCHEMA:
        if ambiguity not in AMBIGUITY_LABELS:
            raise ValueError(f"command intent {intent!r} needs ambiguity in {sorted(AMBIGUITY_LABELS)}")
    else:
        raise ValueError(f"unknown intent {intent!r}")


def build_prompt(intent: str, ambiguity: str | None, n: int, motion: str | None = None) -> str:
    _validate_cell(intent, ambiguity)
    is_command = intent in SCHEMA
    slots_requested = is_command and ambiguity in ("clear", "defaultable")
    lines = [
        "You are helping build an evaluation corpus for an in-car voice assistant.",
        "",
        "Available intents:",
        schema_text(),
        "",
        f'Generate {n} diverse, realistic driver utterances that should map to intent "{intent}".',
    ]
    if is_command:
        assert ambiguity is not None  # guaranteed by _validate_cell
        lines.append(f"Ambiguity = {ambiguity}: {_AMBIGUITY_GUIDANCE[ambiguity]}.")
    elif intent == "none":
        lines.append("These are NOT commands — ambient talk / musings the assistant should not act on.")
    else:  # out_of_scope
        lines.append(
            "These ask for a real car capability NOT in the intent list above "
            "(e.g. sunroof, windows, wipers, seat heaters) — the assistant cannot do them."
        )
    if motion:
        lines.append(f"Context: the vehicle is {motion}.")
    lines += [
        "",
        "Rules:",
        "- Vary wording, tone, filler and content. Do NOT produce templated or near-duplicate variants.",
    ]
    if slots_requested:
        lines += [
            '- For each item give "utterance" and "expected_slots" (correct slot values per the schema).',
            "- Use only that intent's slot names; categorical slots must use their allowed values.",
            "",
            'Return ONLY a JSON array: [{"utterance": "...", "expected_slots": {...}}, ...]',
        ]
    else:
        reason = "the driver must be asked to clarify" if is_command else "the assistant should not act"
        lines += [
            f'- Give only "utterance" for each ({reason}; no slots).',
            "",
            'Return ONLY a JSON array: [{"utterance": "..."}, ...]',
        ]
    return "\n".join(lines)


def parse_candidates(
    raw: str, intent: str, ambiguity: str | None, motion: str | None = None
) -> list[dict[str, Any]]:
    """Turn the model's JSON array into case dicts, with the cell's labels fixed."""
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        raise ValueError("no JSON array found in model output")
    items = json.loads(match.group(0))
    is_command = intent in SCHEMA
    slots_requested = is_command and ambiguity in ("clear", "defaultable")
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict) or not str(item.get("utterance", "")).strip():
            continue
        case: dict[str, Any] = {"utterance": str(item["utterance"]).strip(), "expected_intent": intent}
        case["expected_slots"] = dict(item.get("expected_slots", {})) if slots_requested else {}
        if is_command:
            case["ambiguity"] = ambiguity
        if motion:
            case["car_state"] = {"vehicle_motion": motion}
        out.append(case)
    return out


def _normalize(utterance: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", utterance.lower())).strip()


def existing_utterances(fixtures_dir: str | Path) -> set[str]:
    seen: set[str] = set()
    for name in _CORPUS_FILES:
        path = Path(fixtures_dir) / name
        if not path.exists():
            continue
        for case in json.loads(path.read_text(encoding="utf-8") or "[]"):
            seen.add(_normalize(case["utterance"]))
    return seen


def filter_candidates(
    candidates: list[dict[str, Any]], seen: set[str]
) -> tuple[list[dict[str, Any]], list[tuple[dict[str, Any], str]]]:
    """Drop duplicates and schema-invalid candidates. ``seen`` is updated in place."""
    kept: list[dict[str, Any]] = []
    rejected: list[tuple[dict[str, Any], str]] = []
    for case in candidates:
        norm = _normalize(case["utterance"])
        if norm in seen:
            rejected.append((case, "duplicate"))
            continue
        try:
            _to_gold(case)  # schema-validate (raises ValueError on bad intent/slots)
        except ValueError as exc:
            rejected.append((case, f"invalid: {exc}"))
            continue
        seen.add(norm)
        kept.append(case)
    return kept, rejected


def synthesize(
    client: ModelClient, intent: str, ambiguity: str | None, n: int,
    motion: str | None, fixtures_dir: str | Path,
) -> dict[str, Any]:
    """Generate → validate → dedupe → append survivors to flagged_for_human.json."""
    raw = client.complete(build_prompt(intent, ambiguity, n, motion))
    candidates = parse_candidates(raw, intent, ambiguity, motion)
    kept, rejected = filter_candidates(candidates, existing_utterances(fixtures_dir))

    flagged = Path(fixtures_dir) / "flagged_for_human.json"
    queue = json.loads(flagged.read_text(encoding="utf-8") or "[]") if flagged.exists() else []
    queue.extend(kept)
    flagged.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {"generated": len(candidates), "kept": len(kept), "rejected": rejected, "queue_size": len(queue)}


def main() -> None:
    ap = argparse.ArgumentParser(description="Draft candidate corpus cases for human review.")
    ap.add_argument("--intent", required=True, help="command intent, or none / out_of_scope")
    ap.add_argument("--ambiguity", default=None, help="clear | defaultable | ambiguous (command intents only)")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--motion", default=None, choices=["moving", "parked"])
    ap.add_argument("--tier", default="sonnet", help="Claude tier for generation (different family than the target)")
    ap.add_argument("--fixtures", default="fixtures")
    args = ap.parse_args()

    from .live_client import live_client_for_tier  # live path only

    client = live_client_for_tier(args.tier, max_tokens=2048)
    report = synthesize(client, args.intent, args.ambiguity, args.n, args.motion, args.fixtures)

    cell = args.intent + (f"/{args.ambiguity}" if args.ambiguity else "") + (f"/{args.motion}" if args.motion else "")
    print(f"[{cell}] generated={report['generated']} kept={report['kept']} "
          f"rejected={len(report['rejected'])}  queue={report['queue_size']}")
    for case, reason in report["rejected"]:
        print(f"  - dropped ({reason}): {case['utterance']!r}")


if __name__ == "__main__":
    main()
