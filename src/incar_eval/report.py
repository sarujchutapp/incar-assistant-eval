"""Per-model report card and paired model comparison.

Wraps each proportion in a Wilson interval, runs models on the identical case set
(paired), and compares them with McNemar on per-case TSR. The comparison is
paired and per-case — no Elo, no ranking model on the objective quadrant.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from .client import ModelClient
from .metrics import compute_metrics, proportion_counts
from .models import BenchmarkResult, CaseOutcome, GoldRecord
from .runner import run_benchmark
from .stats import McNemarResult, mcnemar, wilson_interval


@dataclass(frozen=True)
class Proportion:
    value: float
    lo: float
    hi: float
    k: int
    n: int


@dataclass(frozen=True)
class ModelReport:
    name: str
    n: int
    mean_cost: float
    slot_f1: float
    proportions: dict[str, Proportion]  # keyed as in metrics.proportion_counts


def model_report(name: str, outcomes: list[CaseOutcome]) -> ModelReport:
    m = compute_metrics(outcomes)
    proportions: dict[str, Proportion] = {}
    for key, (k, n) in proportion_counts(outcomes).items():
        lo, hi = wilson_interval(k, n)
        proportions[key] = Proportion(value=(k / n if n else 0.0), lo=lo, hi=hi, k=k, n=n)
    return ModelReport(name=name, n=len(outcomes), mean_cost=m.mean_cost, slot_f1=m.slot_f1, proportions=proportions)


def run_models(dataset: list[GoldRecord], clients: Mapping[str, ModelClient]) -> dict[str, BenchmarkResult]:
    """Run every model on the identical (paired) case set."""
    return {name: run_benchmark(dataset, client) for name, client in clients.items()}


def compare_tsr(baseline: list[CaseOutcome], model: list[CaseOutcome]) -> McNemarResult:
    """Paired McNemar on per-case task success. b = model wins, c = baseline wins."""
    b = sum(m.success and not bl.success for bl, m in zip(baseline, model))
    c = sum(bl.success and not m.success for bl, m in zip(baseline, model))
    return mcnemar(b, c)


def format_report(reports: list[ModelReport], baseline_name: str,
                  comparisons: dict[str, McNemarResult]) -> str:
    """Render a plain-text scorecard. TSR with CI, key metrics, McNemar vs baseline."""
    lines: list[str] = []
    for r in reports:
        tsr = r.proportions["tsr"]
        lines.append(f"== {r.name} (n={r.n}) ==")
        lines.append(f"  TSR:               {tsr.value:.1%}  [{tsr.lo:.1%}, {tsr.hi:.1%}]")
        for key in ("routing_accuracy", "false_activation_rate", "false_rejection_rate",
                    "intent_accuracy", "slots_exact_rate", "capability_hallucination_rate"):
            p = r.proportions[key]
            lines.append(f"  {key:30} {p.value:.1%}  [{p.lo:.1%}, {p.hi:.1%}]")
        lines.append(f"  slot_f1:           {r.slot_f1:.2f}")
        lines.append(f"  mean safety cost:  {r.mean_cost:.2f}")
        if r.name != baseline_name and r.name in comparisons:
            mc = comparisons[r.name]
            verdict = "significant" if mc.p_value < 0.05 else "not significant"
            lines.append(f"  vs {baseline_name}: McNemar p={mc.p_value:.4f} ({verdict})")
    return "\n".join(lines)
