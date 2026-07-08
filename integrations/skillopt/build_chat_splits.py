"""Build SkillOpt train/val/test splits for the chat (grounded informational) env.

Reads the grounded chat corpus (`fixtures/chat_grounded.json`) and slices it
~60/20/20 into train/val/test dirs. The grounded corpus is small (smoke-scale)
until it grows — treat results as plumbing checks, not measurements.

Run from the SkillOpt repo root:

    python build_chat_splits.py --fixtures ../ai-evaluation/fixtures --out data/incar_chat_split
"""

from __future__ import annotations

import argparse
import json
import os


def _write(items: list[dict], out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "items.json"), "w", encoding="utf-8") as fh:
        json.dump(items, fh, ensure_ascii=False, indent=2)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", required=True, help="Path to the ai-evaluation/fixtures dir")
    ap.add_argument("--out", default="data/incar_chat_split")
    args = ap.parse_args()

    with open(os.path.join(args.fixtures, "chat_grounded.json"), encoding="utf-8") as fh:
        cases = json.load(fh)
    items = [{"id": f"chat_{i}", **c} for i, c in enumerate(cases)]

    n = len(items)
    n_val = max(1, round(n * 0.2))
    n_test = max(1, round(n * 0.2))
    val, test, train = items[:n_val], items[n_val:n_val + n_test], items[n_val + n_test:]

    _write(train, os.path.join(args.out, "train"))
    _write(val, os.path.join(args.out, "val"))
    _write(test, os.path.join(args.out, "test"))
    print(f"train={len(train)}  val={len(val)}  test={len(test)}  ->  {args.out}  (smoke-scale; grow the corpus for real runs)")


if __name__ == "__main__":
    main()
