"""Recorded-fixtures demo: run the benchmark and print metrics, no network.

    python -m incar_eval.demo
"""

import json

from .chat import ChatCase, run_chat_benchmark
from .client import FakeModelClient
from .dialogue import DialogueCase, Turn, run_dialogue
from .judge import Comparison, bradley_terry_with_ci, role_adherence
from .models import CarState, GoldRecord
from .report import compare_tsr, format_report, model_report, run_models
from .verify import CaseSpec, VerifierModel, verify_batch


def _raw(intent: str, mode: str = "execute", **slots: object) -> str:
    return json.dumps({"intent": intent, "mode": mode, "slots": slots})


DATASET = [
    GoldRecord("turn the temperature up to 22", "set_climate", {"temp": 22, "zone": "all"}, "clear"),
    GoldRecord("call mom", "call_contact", {"name": "mom"}, "clear"),          # high stakes -> confirm
    GoldRecord("call someone", "call_contact", {"name": "?"}, "ambiguous"),    # -> clarify
    GoldRecord("text dad I'm late", "send_message", {"contact": "dad", "body": "I'm late"}, "clear"),
    GoldRecord("nice weather we're having", "none", {}, "clear"),
    GoldRecord("open the sunroof", "out_of_scope", {}, "clear"),
    GoldRecord("play the movie", "play_media", {"title": "Dune", "media_type": "video"},
               "clear", CarState(vehicle_motion="moving")),  # hard block -> warn+alternative
]

# A "strong" model: only flaw is firing the high-stakes call silently (under-confirm).
STRONG = {
    "turn the temperature up to 22": _raw("set_climate", temp=22, zone="all"),
    "call mom": _raw("call_contact", name="mom"),
    "call someone": _raw("call_contact", mode="clarify"),
    "text dad I'm late": _raw("send_message", mode="confirm", contact="dad", body="I'm late"),
    "nice weather we're having": _raw("none"),
    "open the sunroof": _raw("out_of_scope"),
    "play the movie": _raw("play_media", mode="warn_alternative"),
}

# A "weak" model: texts the WRONG contact silently (worst cell), hallucinates the
# sunroof, and silently plays video while moving.
WEAK = {
    "turn the temperature up to 22": _raw("set_climate", temp=22, zone="all"),
    "call mom": _raw("call_contact", name="mom"),
    "call someone": _raw("call_contact", name="dad"),  # guessed an ambiguous call
    "text dad I'm late": _raw("send_message", contact="mom", body="I'm late"),
    "nice weather we're having": _raw("none"),
    "open the sunroof": _raw("set_climate", temp=21),
    "play the movie": _raw("play_media", title="Dune", media_type="video"),
}

DIALOGUE = DialogueCase(
    turns=[
        Turn("navigate to the cafe", "navigate", {"destination": "cafe"}),
        Turn("make it the downtown one", "navigate", {"destination": "downtown cafe"}),
    ]
)
DIALOGUE_RESPONSES = {
    "navigate to the cafe": _raw("navigate", destination="cafe"),
    "make it the downtown one": _raw("navigate", destination="downtown cafe"),
}


def main() -> None:
    results = run_models(DATASET, {"strong": FakeModelClient(STRONG), "weak": FakeModelClient(WEAK)})
    reports = [model_report(name, r.outcomes) for name, r in results.items()]
    comparisons = {"weak": compare_tsr(results["strong"].outcomes, results["weak"].outcomes)}
    print(format_report(reports, baseline_name="strong", comparisons=comparisons))

    dlg = run_dialogue(DIALOGUE, FakeModelClient(DIALOGUE_RESPONSES))
    print(f"\ndialogue JGA:      {dlg.jga:.1%}   per-turn: {dlg.per_turn_accuracy:.1%}")

    chat_cases = [
        ChatCase("what's my ETA?", fact="25 minutes"),
        ChatCase("how much fuel is left?", fact="low"),
    ]
    chat_client = FakeModelClient({
        "what's my ETA?": "Your ETA is about 25 minutes.",
        "how much fuel is left?": "Fuel is running low.",
    })
    _, chat_metrics = run_chat_benchmark(chat_cases, chat_client)
    print(f"chat faithfulness: {chat_metrics.faithfulness_rate:.1%}   "
          f"relevancy: {chat_metrics.mean_relevancy:.2f}")

    # Open-tail pairwise judging aggregates to a Bradley-Terry ranking (strong
    # wins 6 of 8 head-to-heads, 1 tie from position bias).
    comps = (
        [Comparison("strong", "weak", "strong") for _ in range(6)]
        + [Comparison("strong", "weak", "weak"), Comparison("strong", "weak", "tie")]
    )
    bt = bradley_terry_with_ci(["strong", "weak"], comps, n_boot=200, seed=0)
    print("\nBradley-Terry (chat open tail):")
    for name in ("strong", "weak"):
        s = bt[name]
        print(f"  {name:6} {s.value:.2f}  [{s.lo:.2f}, {s.hi:.2f}]")
    print(f"role adherence - concise: {role_adherence('Your ETA is 25 minutes.'):.2f}   "
          f"rambling: {role_adherence('By the way, ' + 'word ' * 40):.2f}")

    # Cross-family auto-verification: two different-family verifiers agree on the
    # climate gold (auto-accepted); the send_message cell is hand-authored (flagged).
    def _v(family: str, mapping: dict[str, str]) -> VerifierModel:
        return VerifierModel(family, family, FakeModelClient(mapping))

    vmap = {
        "turn it up to 22": _raw("set_climate", temp=22),
        "text my boss the update": _raw("send_message", contact="boss", body="update"),
    }
    verifiers = [_v("openai", vmap), _v("anthropic", vmap)]
    vreport = verify_batch(
        [CaseSpec("turn it up to 22"), CaseSpec("text my boss the update", force_manual=True)],
        verifiers,
    )
    print(f"\nauto-verify: {len(vreport.accepted)} auto-accepted, "
          f"{len(vreport.flagged)} flagged for human ({vreport.auto_accept_rate:.0%} auto)")


if __name__ == "__main__":
    main()
