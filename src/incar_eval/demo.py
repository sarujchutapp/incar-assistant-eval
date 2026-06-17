"""Recorded-fixtures demo: run the benchmark and print a TSR, no network.

    python -m incar_eval.demo
"""

import json

from .client import FakeModelClient
from .models import GoldRecord
from .runner import run_benchmark


def _raw(intent: str, **slots: object) -> str:
    return json.dumps({"intent": intent, "slots": slots})


DATASET = [
    GoldRecord("turn the temperature up to 22", "set_climate", {"temp": 22, "zone": "all"}),
    GoldRecord("make the driver side warmer", "set_climate", {"temp": 23, "zone": "driver"}),
    GoldRecord("set it to 19 degrees", "set_climate", {"temp": 19, "zone": "all"}),
]

# Recorded model responses (the last one gets the zone wrong).
RESPONSES = {
    "turn the temperature up to 22": _raw("set_climate", temp=22, zone="all"),
    "make the driver side warmer": _raw("set_climate", temp=23, zone="driver"),
    "set it to 19 degrees": _raw("set_climate", temp=19, zone="driver"),
}


def main() -> None:
    result = run_benchmark(DATASET, FakeModelClient(RESPONSES))
    print(f"TSR: {result.tsr:.1%} ({sum(o.success for o in result.outcomes)}/{len(result.outcomes)})")
    for outcome in result.outcomes:
        mark = "PASS" if outcome.success else "FAIL"
        print(f"  [{mark}] {outcome.gold.utterance!r} -> {outcome.emitted.slots}")


if __name__ == "__main__":
    main()
