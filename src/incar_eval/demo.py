"""Recorded-fixtures demo: run the benchmark and print metrics, no network.

    python -m incar_eval.demo
"""

import json

from .client import FakeModelClient
from .metrics import compute_metrics
from .models import GoldRecord
from .runner import run_benchmark


def _raw(intent: str, **slots: object) -> str:
    return json.dumps({"intent": intent, "slots": slots})


DATASET = [
    GoldRecord("turn the temperature up to 22", "set_climate", {"temp": 22, "zone": "all"}),
    GoldRecord("call mom", "call_contact", {"name": "mom"}),
    GoldRecord("nice weather we're having", "none", {}),
    GoldRecord("open the sunroof", "out_of_scope", {}),
    GoldRecord("navigate to the office", "navigate", {"destination": "office"}),
]

# Recorded model responses: the last navigate is ignored (false rejection),
# and the sunroof request is hallucinated as a climate action.
RESPONSES = {
    "turn the temperature up to 22": _raw("set_climate", temp=22, zone="all"),
    "call mom": _raw("call_contact", name="mom"),
    "nice weather we're having": _raw("none"),
    "open the sunroof": _raw("set_climate", temp=21, zone="all"),
    "navigate to the office": _raw("none"),
}


def main() -> None:
    result = run_benchmark(DATASET, FakeModelClient(RESPONSES))
    m = compute_metrics(result.outcomes)
    print(f"n={m.n}")
    print(f"TSR:                 {m.tsr:.1%}")
    print(f"routing accuracy:    {m.routing_accuracy:.1%}")
    print(f"  false-activation:  {m.false_activation_rate:.1%}")
    print(f"  false-rejection:   {m.false_rejection_rate:.1%}")
    print(f"  capability-halluc: {m.capability_hallucination_rate:.1%}")
    print(f"intent accuracy:     {m.intent_accuracy:.1%}")
    print(f"slot F1:             {m.slot_f1:.2f}")
    print(f"slots exact:         {m.slots_exact_rate:.1%}")
    for o in result.outcomes:
        print(f"  [{o.routing.value}] {o.gold.utterance!r}")


if __name__ == "__main__":
    main()
