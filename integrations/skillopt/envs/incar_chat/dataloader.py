"""SkillOpt dataloader for the in-car chat (grounded informational) env.

Reads a split's ``items.json`` (a JSON array of grounded chat cases: question /
context / fact, plus an ``id``). The rollout feeds context+question to the model
and scores the answer with the project's faithfulness verifier.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from skillopt.datasets.base import SplitDataLoader


class IncarChatDataLoader(SplitDataLoader):
    def load_split_items(self, split_path: str) -> list[dict[str, Any]]:
        files = sorted(Path(split_path).glob("*.json"))
        if not files:
            raise FileNotFoundError(f"No .json file found in {split_path}")
        with files[0].open(encoding="utf-8") as fh:
            payload = json.load(fh)
        if not isinstance(payload, list):
            raise ValueError(f"Expected a JSON array at top level of {files[0]}")
        return [{**row, "id": str(row.get("id") or f"chat_{i}"), "task_type": "chat"} for i, row in enumerate(payload)]
