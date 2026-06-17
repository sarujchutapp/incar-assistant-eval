import pytest

from incar_eval.stats import mcnemar, wilson_interval


# --- Wilson score intervals ---


def test_wilson_half_half() -> None:
    lo, hi = wilson_interval(50, 100)
    assert lo == pytest.approx(0.4038, abs=1e-3)
    assert hi == pytest.approx(0.5962, abs=1e-3)


def test_wilson_near_one_does_not_exceed_one() -> None:
    lo, hi = wilson_interval(99, 100)
    assert hi < 1.0  # the normal approximation would give > 1.0 here
    assert hi == pytest.approx(0.9982, abs=1e-3)
    assert lo == pytest.approx(0.9455, abs=1e-3)


def test_wilson_perfect_score_upper_is_one_but_lower_below() -> None:
    lo, hi = wilson_interval(20, 20)
    assert hi == 1.0
    assert lo < 1.0


def test_wilson_empty_is_full_range() -> None:
    assert wilson_interval(0, 0) == (0.0, 1.0)


# --- McNemar's paired test ---


def test_mcnemar_significant_difference() -> None:
    result = mcnemar(b=15, c=5)
    assert result.statistic == pytest.approx(4.05)  # (|15-5|-1)^2 / 20
    assert result.p_value < 0.05


def test_mcnemar_no_difference_is_not_significant() -> None:
    result = mcnemar(b=10, c=10)
    assert result.p_value > 0.5


def test_mcnemar_empty_discordant_is_p_one() -> None:
    result = mcnemar(b=0, c=0)
    assert result.p_value == 1.0
