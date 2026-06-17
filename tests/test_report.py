import json

import incar_eval.stats as stats
from incar_eval.client import FakeModelClient
from incar_eval.models import GoldRecord, ToolCall
from incar_eval.report import compare_tsr, format_report, model_report, run_models
from incar_eval.scorer import score_case


def _raw(intent: str, **slots: object) -> str:
    return json.dumps({"intent": intent, "slots": slots})


def _outcome(success: bool) -> object:
    # an outcome that succeeds or fails on a simple climate command
    emitted = ToolCall("set_climate", {"temp": 22} if success else {"temp": 0})
    return score_case(GoldRecord("warm up", "set_climate", {"temp": 22}), emitted)


def test_model_report_has_tsr_with_ci() -> None:
    outcomes = [_outcome(True), _outcome(True), _outcome(False)]
    report = model_report("model-a", outcomes)  # type: ignore[arg-type]
    tsr = report.proportions["tsr"]
    assert tsr.k == 2 and tsr.n == 3
    assert tsr.lo < tsr.value < tsr.hi
    assert tsr.hi <= 1.0


def test_paired_comparison_via_mcnemar() -> None:
    # baseline fails the cases model-b passes -> all discordant in model-b's favour
    baseline = [_outcome(False) for _ in range(12)]
    model_b = [_outcome(True) for _ in range(12)]
    result = compare_tsr(baseline, model_b)  # type: ignore[arg-type]
    assert result.b == 12 and result.c == 0
    assert result.p_value < 0.05


def test_run_models_uses_identical_dataset() -> None:
    dataset = [
        GoldRecord("turn it up to 22", "set_climate", {"temp": 22}),
        GoldRecord("navigate home", "navigate", {"destination": "home"}),
    ]
    strong = FakeModelClient({
        "turn it up to 22": _raw("set_climate", temp=22),
        "navigate home": _raw("navigate", destination="home"),
    })
    weak = FakeModelClient({
        "turn it up to 22": _raw("set_climate", temp=22),
        "navigate home": _raw("navigate", destination="work"),  # wrong
    })
    results = run_models(dataset, {"strong": strong, "weak": weak})
    assert results["strong"].tsr == 1.0
    assert results["weak"].tsr == 0.5
    # same case set, paired
    assert len(results["strong"].outcomes) == len(results["weak"].outcomes) == 2


def test_format_report_renders_tsr_ci_and_significance() -> None:
    outcomes = [_outcome(True), _outcome(True), _outcome(False)]
    reports = [model_report("baseline", outcomes), model_report("challenger", outcomes)]  # type: ignore[arg-type]
    comparisons = {"challenger": compare_tsr(outcomes, outcomes)}  # type: ignore[arg-type]
    text = format_report(reports, "baseline", comparisons)
    assert "TSR:" in text
    assert "McNemar" in text


def test_no_elo_or_ranking_model_on_objective_quadrant() -> None:
    # the objective quadrant must not rank models — only paired per-case McNemar
    assert not hasattr(stats, "elo")
    assert not hasattr(stats, "bradley_terry")
