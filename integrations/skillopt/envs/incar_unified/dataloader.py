"""SkillOpt dataloader for the unified in-car assistant env.

One pool mixing command/control cases and grounded chat cases. Each item carries
a ``case_type`` ("command" | "chat") that the evaluator dispatches on. Command
items carry utterance/expected_intent/expected_slots/ambiguity/car_state; chat
items carry question/context/fact.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from skillopt.datasets.base import SplitDataLoader


class IncarUnifiedDataLoader(SplitDataLoader):
    def load_split_items(self, split_path: str) -> list[dict[str, Any]]:
        files = sorted(Path(split_path).glob("*.json"))
        if not files:
            raise FileNotFoundError(f"No .json file found in {split_path}")
        with files[0].open(encoding="utf-8") as fh:
            payload = json.load(fh)
        if not isinstance(payload, list):
            raise ValueError(f"Expected a JSON array at top level of {files[0]}")
        return [{**row, "id": str(row.get("id") or f"item_{i}")} for i, row in enumerate(payload)]
