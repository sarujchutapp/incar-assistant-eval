import json

import pytest

import incar_eval.judge as judge_mod
from incar_eval.judge import (
    Comparison,
    bradley_terry,
    bradley_terry_with_ci,
    compare_pair,
    judge_pairwise,
    normalize_answer,
    parse_verdict,
    role_adherence,
)

VERDICT_KEYS = {"faithfulness": "A", "relevancy": "A", "conciseness": "A"}


def _verdict_json(winner: str, critique: str = "A is more faithful and concise.") -> str:
    return json.dumps({"critique": critique, "dimensions": VERDICT_KEYS, "winner": winner})


# --- fake judges --------------------------------------------------------------


class PositionBiasedJudge:
    """Always picks whatever is in slot A — the classic position bias."""

    def complete(self, prompt: str) -> str:
        return _verdict_json("A")


class PrefersTextJudge:
    """Consistently prefers the answer containing a marker, whichever slot it's in."""

    def __init__(self, marker: str) -> None:
        self.marker = marker

    def complete(self, prompt: str) -> str:
        a_section = prompt.split("Answer A:")[1].split("Answer B:")[0]
        return _verdict_json("A" if self.marker in a_section else "B")


class BareScalarJudge:
    def complete(self, prompt: str) -> str:
        return json.dumps({"winner": "A"})  # no critique, no dimensions


# --- guards -------------------------------------------------------------------


def test_length_normalization_strips_markdown() -> None:
    assert normalize_answer("**ETA** is   `25`\n\nminutes") == "ETA is 25 minutes"


def test_bare_scalar_verdict_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_verdict(json.dumps({"winner": "A"}))


def test_missing_dimensions_rejected() -> None:
    with pytest.raises(ValueError):
        parse_verdict(json.dumps({"critique": "x", "winner": "A", "dimensions": {"faithfulness": "A"}}))


def test_cross_family_guard() -> None:
    with pytest.raises(ValueError):
        judge_pairwise("q", "a", "b", PositionBiasedJudge(), "openai", "openai", "anthropic")


def test_per_dimension_diagnostics_captured() -> None:
    verdict = judge_pairwise("q", "a", "b", PositionBiasedJudge(), "google", "openai", "anthropic")
    assert set(verdict.dimensions) == {"faithfulness", "relevancy", "conciseness"}


# --- position swap -------------------------------------------------------------


def test_position_bias_resolves_to_tie() -> None:
    result = compare_pair(
        "q", "x", "answer x", "openai", "y", "answer y", "anthropic",
        PositionBiasedJudge(), "google",
    )
    assert result.winner == "tie"


def test_consistent_preference_wins_through_swap() -> None:
    result = compare_pair(
        "q", "x", "the marker answer", "openai", "y", "other", "anthropic",
        PrefersTextJudge("the marker answer"), "google",
    )
    assert result.winner == "x"


# --- Bradley-Terry -------------------------------------------------------------


def test_bradley_terry_ranks_consistent_winner_higher() -> None:
    comps = [Comparison("x", "y", "x") for _ in range(10)]
    strengths = bradley_terry(["x", "y"], comps)
    assert strengths["x"] > strengths["y"]
    assert strengths["x"] + strengths["y"] == pytest.approx(1.0)


def test_bradley_terry_ci_brackets_estimate() -> None:
    comps = [Comparison("x", "y", "x") for _ in range(8)] + [Comparison("x", "y", "y") for _ in range(2)]
    result = bradley_terry_with_ci(["x", "y"], comps, n_boot=200, seed=1)
    assert result["x"].lo <= result["x"].value <= result["x"].hi
    assert result["x"].value > result["y"].value


def test_no_elo_path() -> None:
    assert not hasattr(judge_mod, "elo")


# --- role adherence ------------------------------------------------------------


def test_role_adherence_rewards_concise_calm() -> None:
    assert role_adherence("Your ETA is 25 minutes.") == 1.0


def test_role_adherence_penalizes_verbosity_and_chitchat() -> None:
    rambling = "By the way, " + "word " * 40
    assert role_adherence(rambling) < 1.0


def test_role_adherence_stricter_while_moving() -> None:
    answer = "word " * 20
    assert role_adherence(answer, moving=True) < role_adherence(answer, moving=False)
