"""SkillOpt dataloader for the in-car tool-calling env.

Overrides ``load_split_items`` (the split_dir-mode hook). Each split dir holds
one ``items.json`` (a JSON array of case dicts: utterance / expected_intent /
expected_slots / ambiguity? / car_state?). We keep the full case dict so the
rollout can reconstruct a GoldRecord and score with the project's verifier; the
only fields SkillOpt itself needs are ``id`` and ``task_type`` (stratification).
"""

from __future__ import annotations

import json
from pathlib import Path

from skillopt.datasets.base import SplitDataLoader


def _normalize_item(raw: dict, idx: int) -> dict:
    return {
        **raw,
        "id": str(raw.get("id") or f"item_{idx}"),
        "task_type": str(raw.get("ambiguity") or "clear"),
    }


class IncarToolCallingDataLoader(SplitDataLoader):
    def load_split_items(self, split_path: str) -> list[dict]:
        files = sorted(Path(split_path).glob("*.json"))
        if not files:
            raise FileNotFoundError(f"No .json file found in {split_path}")
        with files[0].open(encoding="utf-8") as fh:
            payload = json.load(fh)
        if not isinstance(payload, list):
            raise ValueError(f"Expected a JSON array at top level of {files[0]}")
        return [_normalize_item(row, i) for i, row in enumerate(payload)]
