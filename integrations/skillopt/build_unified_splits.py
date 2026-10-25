"""Build SkillOpt splits for the unified in-car assistant env.

Pools the command corpus (cases + hard_cases + synth_cases, tagged
case_type="command") with the grounded chat corpus (chat_grounded, tagged
case_type="chat"), then stratifies 2:3:5 (train/val/test) by a routing-aware key
so every split holds both commands (across ambiguity/abstention) and chat. The
generous val/test (vs a large-corpus 2:1:7) follows the paper's bounded-pool
shape (cf. ALFWorld 39 train / 140 selection / 134 test) for a small corpus.

Run from the SkillOpt repo root:

    python build_unified_splits.py --fixtures ../incar-assistant-eval/fixtures --out data/incar_unified_split
"""

from __future__ import annotations

import argparse
import json
import os
import random
from collections import Counter, defaultdict

ABSTENTION = {"none", "out_of_scope"}


def _read(fixtures: str, name: str) -> list[dict]:
    with open(os.path.join(fixtures, name), encoding="utf-8") as fh:
        return json.load(fh)


def _write(items: list[dict], out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "items.json"), "w", encoding="utf-8") as fh:
        json.dump(items, fh, ensure_ascii=False, indent=2)


def _stratum(item: dict) -> str:
    if item["case_type"] == "chat":
        # keep unanswerable (abstention) chat its own stratum so every split holds
        # some — otherwise the minority hallucination cases could miss a split
        return "chat" if item.get("answerable", True) else "chat/unanswerable"
    intent = item["expected_intent"]
    return f"cmd/{intent if intent in ABSTENTION else item.get('ambiguity', 'clear')}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", required=True)
    ap.add_argument("--out", default="data/incar_unified_split")
    ap.add_argument("--seed", type=int, default=42, help="shuffle seed so splits are representative (not authoring-order)")
    args = ap.parse_args()

    pool: list[dict] = []
    for name in ("cases.json", "hard_cases.json", "synth_cases.json"):
        for c in _read(args.fixtures, name):
            pool.append({**c, "case_type": "command"})
    for c in _read(args.fixtures, "chat_grounded.json"):
        pool.append({**c, "case_type": "chat"})
    pool = [{"id": f"u_{i}", **c} for i, c in enumerate(pool)]

    groups: dict[str, list[dict]] = defaultdict(list)
    for item in pool:
        groups[_stratum(item)].append(item)

    rng = random.Random(args.seed)
    train: list[dict] = []
    val: list[dict] = []
    test: list[dict] = []
    for key in sorted(groups):
        g = groups[key]
        rng.shuffle(g)  # representative split, not authoring-order; seeded for reproducibility
        n_val = round(len(g) * 0.3)
        n_test = round(len(g) * 0.5)
        val += g[:n_val]
        test += g[n_val:n_val + n_test]
        train += g[n_val + n_test:]

    _write(train, os.path.join(args.out, "train"))
    _write(val, os.path.join(args.out, "val"))
    _write(test, os.path.join(args.out, "test"))

    def brk(items: list[dict]) -> str:
        c = Counter(i["case_type"] for i in items)
        return f"command={c['command']} chat={c['chat']}"

    print(f"train={len(train)} val={len(val)} test={len(test)}  ->  {args.out}")
    print(f"  train: {brk(train)}\n  val:   {brk(val)}\n  test:  {brk(test)}")


if __name__ == "__main__":
    main()
