"""Build SkillOpt train/val/test splits from the benchmark fixtures.

Split policy: the hand-authored cases are held out as the test set (so we
validate against human-written items); the synthetic cases carry train/val,
**stratified by category** so val mirrors the corpus mix (clear / defaultable /
ambiguous / none / out_of_scope) rather than over-representing one type.

    test  = cases.json + hard_cases.json           (hand-authored, held out)
    train = ~80% of synth per category
    val   = ~20% of synth per category

Run from the SkillOpt repo root:

    python build_splits.py --fixtures ../ai-evaluation/fixtures --out data/incar_toolcalling_split
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict

VAL_FRACTION = 0.2
ABSTENTION = {"none", "out_of_scope"}


def _read(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _write(items: list[dict], out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "items.json"), "w", encoding="utf-8") as fh:
        json.dump(items, fh, ensure_ascii=False, indent=2)


def _with_ids(items: list[dict], prefix: str) -> list[dict]:
    return [{"id": f"{prefix}_{i}", **item} for i, item in enumerate(items)]


def _category(case: dict) -> str:
    """Stratification key: intent for abstention, ambiguity for commands."""
    intent = case["expected_intent"]
    return intent if intent in ABSTENTION else case.get("ambiguity", "clear")


def _stratify(synth: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split synth into (train, val), ~VAL_FRACTION of each category into val."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for case in synth:
        groups[_category(case)].append(case)
    train: list[dict] = []
    val: list[dict] = []
    for key in sorted(groups):  # sorted -> deterministic
        g = groups[key]
        n_val = round(len(g) * VAL_FRACTION)
        val += g[:n_val]
        train += g[n_val:]
    return train, val


def _breakdown(items: list[dict]) -> str:
    return ", ".join(f"{k}={v}" for k, v in sorted(Counter(_category(c) for c in items).items()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", required=True, help="Path to the ai-evaluation/fixtures dir")
    ap.add_argument("--out", default="data/incar_toolcalling_split")
    args = ap.parse_args()

    hand = _with_ids(_read(os.path.join(args.fixtures, "cases.json")), "case")
    hard = _with_ids(_read(os.path.join(args.fixtures, "hard_cases.json")), "hard")
    synth = _with_ids(_read(os.path.join(args.fixtures, "synth_cases.json")), "synth")

    train, val = _stratify(synth)
    test = hand + hard

    _write(train, os.path.join(args.out, "train"))
    _write(val, os.path.join(args.out, "val"))
    _write(test, os.path.join(args.out, "test"))

    print(f"train={len(train)}  val={len(val)}  test={len(test)}  ->  {args.out}")
    print(f"  train: {_breakdown(train)}")
    print(f"  val:   {_breakdown(val)}")
    print(f"  test:  {_breakdown(test)}")


if __name__ == "__main__":
    main()
