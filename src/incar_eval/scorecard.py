"""Unified v1 scorecard — one per-model view across the whole benchmark.

Assembles the separate report pieces the PRD promises into a single per-model
scorecard: the command-side report (TSR + Wilson CI, decomposed routing/intent/
slot metrics, confirmation calibration, safety cost, McNemar vs a baseline), the
multi-turn JGA, and the chat quadrant (faithfulness/relevancy + Bradley-Terry).

A pure assembler over already-computed run outputs — it does not re-run anything.
The command run comes from ``report.run_models``; the chat run from
``chat.run_chat_benchmark`` / ``loader.run_open_tail``. Anything chat-/dialogue-
side is optional per model (a model may appear in the command run only).
"""

from collections.abc import Mapping
from dataclasses import dataclass

from .chat import ChatMetrics
from .judge import Strength
from .models import BenchmarkResult
from .report import ModelReport, compare_tsr, model_report
from .stats import McNemarResult


@dataclass(frozen=True)
class Scorecard:
    name: str
    command: ModelReport
    vs_baseline: McNemarResult | None  # None for the baseline itself
    chat: ChatMetrics | None
    chat_bt: Strength | None
    jga: float | None


def build_scorecards(
    command_results: Mapping[str, BenchmarkResult],
    baseline: str,
    *,
    chat_metrics: Mapping[str, ChatMetrics] | None = None,
    chat_bt: Mapping[str, Strength] | None = None,
    jga: Mapping[str, float] | None = None,
) -> dict[str, Scorecard]:
    baseline_outcomes = command_results[baseline].outcomes
    cards: dict[str, Scorecard] = {}
    for name, result in command_results.items():
        vs_baseline = None if name == baseline else compare_tsr(baseline_outcomes, result.outcomes)
        cards[name] = Scorecard(
            name=name,
            command=model_report(name, result.outcomes),
            vs_baseline=vs_baseline,
            chat=chat_metrics.get(name) if chat_metrics else None,
            chat_bt=chat_bt.get(name) if chat_bt else None,
            jga=jga.get(name) if jga else None,
        )
    return cards


_COMMAND_KEYS = (
    "routing_accuracy", "false_activation_rate", "false_rejection_rate",
    "intent_accuracy", "slots_exact_rate", "capability_hallucination_rate",
)


def format_scorecards(cards: Mapping[str, Scorecard], baseline: str) -> str:
    lines: list[str] = []
    for card in cards.values():
        r = card.command
        tsr = r.proportions["tsr"]
        lines.append(f"== {card.name} (n={r.n}) ==")
        lines.append(f"  TSR:               {tsr.value:.1%}  [{tsr.lo:.1%}, {tsr.hi:.1%}]")
        for key in _COMMAND_KEYS:
            p = r.proportions[key]
            lines.append(f"  {key:30} {p.value:.1%}  [{p.lo:.1%}, {p.hi:.1%}]")
        lines.append(f"  slot_f1:           {r.slot_f1:.2f}")
        under, over = r.proportions["under_confirm_rate"], r.proportions["over_confirm_rate"]
        lines.append(f"  calibration:       under-confirm {under.value:.1%}  over-confirm {over.value:.1%}")
        lines.append(f"  mean safety cost:  {r.mean_cost:.2f}")
        if card.jga is not None:
            lines.append(f"  JGA:               {card.jga:.1%}")
        if card.chat is not None:
            lines.append(
                f"  chat faithfulness: {card.chat.faithfulness_rate:.1%}   "
                f"relevancy: {card.chat.mean_relevancy:.2f}  (n={card.chat.n})"
            )
        if card.chat_bt is not None:
            bt = card.chat_bt
            lines.append(f"  chat BT strength:  {bt.value:.2f}  [{bt.lo:.2f}, {bt.hi:.2f}]")
        if card.vs_baseline is not None:
            mc = card.vs_baseline
            verdict = "significant" if mc.p_value < 0.05 else "not significant"
            lines.append(f"  vs {baseline}: McNemar p={mc.p_value:.4f} ({verdict})")
    return "\n".join(lines)
