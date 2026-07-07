"""Build SkillOpt train/val/test splits from the benchmark fixtures.

Split policy (see the corpus-fit discussion): the hand-authored cases are held
out as the test set so we validate against human-written items, while the
synthetic cases carry train/val.

    test  = cases.json (6) + hard_cases.json (12)   = 18   (hand-authored, held out)
    train = first 40 of synth_cases.json                    (synthetic)
    val   = remaining 12 of synth_cases.json                (synthetic)

Run from the SkillOpt repo root:

    python build_splits.py --fixtures ../ai-evaluation/fixtures --out data/incar_toolcalling_split
"""

from __future__ import annotations

import argparse
import json
import os


def _read(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _write(items: list[dict], out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "items.json"), "w", encoding="utf-8") as fh:
        json.dump(items, fh, ensure_ascii=False, indent=2)


def _with_ids(items: list[dict], prefix: str) -> list[dict]:
    return [{"id": f"{prefix}_{i}", **item} for i, item in enumerate(items)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", required=True, help="Path to the ai-evaluation/fixtures dir")
    ap.add_argument("--out", default="data/incar_toolcalling_split")
    args = ap.parse_args()

    hand = _with_ids(_read(os.path.join(args.fixtures, "cases.json")), "case")
    hard = _with_ids(_read(os.path.join(args.fixtures, "hard_cases.json")), "hard")
    synth = _with_ids(_read(os.path.join(args.fixtures, "synth_cases.json")), "synth")

    _write(synth[:40], os.path.join(args.out, "train"))
    _write(synth[40:], os.path.join(args.out, "val"))
    _write(hand + hard, os.path.join(args.out, "test"))

    print(f"train={len(synth[:40])}  val={len(synth[40:])}  test={len(hand) + len(hard)}  ->  {args.out}")


if __name__ == "__main__":
    main()
