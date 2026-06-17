"""Guarded pairwise LLM-as-judge for the open chat tail + Bradley-Terry ranking.

The judge is shown two answers and picks the better one. Pairwise *amplifies*
verbosity/position bias, so the guards are mandatory (benchmark_spec.md §8):

* **CoT critique before verdict** — the judge must produce a per-dimension
  critique first; a bare scalar verdict is rejected (``parse_verdict`` raises).
* **Length normalization** — answers are stripped of markdown/whitespace before
  the judge sees them.
* **Position swap** — every pair is judged twice with A/B swapped; if the two
  verdicts disagree (position bias) the result is a tie.
* **Cross-family judge** — the judge family must differ from both targets.

Head-to-heads are aggregated with Bradley-Terry (order-independent, with bootstrap
CIs) — never Elo. Role Adherence to the fixed persona is a rule-based score.
"""

import json
import random
import re
from dataclasses import dataclass

from .client import ModelClient

_DIMENSIONS = ("faithfulness", "relevancy", "conciseness")


# --- length normalization -----------------------------------------------------


def normalize_answer(text: str) -> str:
    """Strip distinctive formatting so the judge scores content, not style."""
    stripped = re.sub(r"[*_`#>]", "", text)
    return re.sub(r"\s+", " ", stripped).strip()


# --- verdict parsing (rejects bare-scalar judging) ----------------------------


@dataclass(frozen=True)
class JudgeVerdict:
    critique: str
    winner: str                  # "A" | "B" | "tie"
    dimensions: dict[str, str]   # dimension -> "A" | "B" | "tie"


def parse_verdict(raw: str) -> JudgeVerdict:
    data = json.loads(raw)
    critique = data.get("critique", "")
    if not isinstance(critique, str) or not critique.strip():
        raise ValueError("bare-scalar judging not allowed: a critique must precede the verdict")
    winner = data["winner"]
    if winner not in ("A", "B", "tie"):
        raise ValueError(f"invalid winner: {winner!r}")
    dimensions = data.get("dimensions", {})
    missing = [d for d in _DIMENSIONS if d not in dimensions]
    if missing:
        raise ValueError(f"per-dimension diagnostics missing: {missing}")
    return JudgeVerdict(critique=critique, winner=winner, dimensions=dimensions)


def build_judge_prompt(question: str, answer_a: str, answer_b: str) -> str:
    return (
        "You are an impartial evaluator of in-car voice-assistant answers.\n"
        f'Question: "{question}"\n\n'
        f"Answer A:\n{answer_a}\n\n"
        f"Answer B:\n{answer_b}\n\n"
        "First write a critique comparing the two on faithfulness, relevancy, and "
        "conciseness. Then output JSON: "
        '{"critique": ..., "dimensions": {"faithfulness": "A|B|tie", '
        '"relevancy": "A|B|tie", "conciseness": "A|B|tie"}, "winner": "A|B|tie"}'
    )


def judge_pairwise(
    question: str,
    answer_a: str,
    answer_b: str,
    judge: ModelClient,
    judge_family: str,
    family_a: str,
    family_b: str,
) -> JudgeVerdict:
    if judge_family == family_a or judge_family == family_b:
        raise ValueError("judge must be a different family than the targets it evaluates")
    prompt = build_judge_prompt(question, normalize_answer(answer_a), normalize_answer(answer_b))
    return parse_verdict(judge.complete(prompt))


# --- head-to-head with position swap ------------------------------------------


@dataclass(frozen=True)
class Comparison:
    a: str       # model name in slot A (first run)
    b: str       # model name in slot B (first run)
    winner: str  # model name or "tie"


def _winner_name(verdict_winner: str, name_a: str, name_b: str) -> str:
    if verdict_winner == "A":
        return name_a
    if verdict_winner == "B":
        return name_b
    return "tie"


def compare_pair(
    question: str,
    name_x: str, answer_x: str, family_x: str,
    name_y: str, answer_y: str, family_y: str,
    judge: ModelClient, judge_family: str,
) -> Comparison:
    """Judge x vs y twice (positions swapped); disagreement -> tie."""
    v1 = judge_pairwise(question, answer_x, answer_y, judge, judge_family, family_x, family_y)
    v2 = judge_pairwise(question, answer_y, answer_x, judge, judge_family, family_y, family_x)
    w1 = _winner_name(v1.winner, name_x, name_y)
    w2 = _winner_name(v2.winner, name_y, name_x)
    winner = w1 if w1 == w2 else "tie"
    return Comparison(a=name_x, b=name_y, winner=winner)


# --- Bradley-Terry aggregation (no Elo) ---------------------------------------


def bradley_terry(models: list[str], comparisons: list[Comparison], iters: int = 200) -> dict[str, float]:
    """MM-algorithm Bradley-Terry strengths, normalized to sum to 1. Ties = half a win each."""
    wins = {m: 0.0 for m in models}
    games = {m: {n: 0.0 for n in models} for m in models}
    for c in comparisons:
        if c.winner == "tie":
            wins[c.a] += 0.5
            wins[c.b] += 0.5
        else:
            wins[c.winner] += 1.0
        games[c.a][c.b] += 1.0
        games[c.b][c.a] += 1.0

    p = {m: 1.0 for m in models}
    for _ in range(iters):
        new_p: dict[str, float] = {}
        for i in models:
            denom = sum(games[i][j] / (p[i] + p[j]) for j in models if j != i and games[i][j] > 0)
            new_p[i] = wins[i] / denom if denom > 0 else p[i]
        total = sum(new_p.values()) or 1.0
        p = {m: new_p[m] / total for m in models}
    return p


@dataclass(frozen=True)
class Strength:
    value: float
    lo: float
    hi: float


def bradley_terry_with_ci(
    models: list[str], comparisons: list[Comparison], n_boot: int = 300, seed: int = 0
) -> dict[str, Strength]:
    base = bradley_terry(models, comparisons)
    if not comparisons:
        return {m: Strength(base[m], 0.0, 1.0) for m in models}
    rng = random.Random(seed)
    samples: dict[str, list[float]] = {m: [] for m in models}
    n = len(comparisons)
    for _ in range(n_boot):
        resample = [comparisons[rng.randrange(n)] for _ in range(n)]
        fit = bradley_terry(models, resample)
        for m in models:
            samples[m].append(fit[m])
    result: dict[str, Strength] = {}
    for m in models:
        ordered = sorted(samples[m])
        lo = ordered[int(0.025 * len(ordered))]
        hi = ordered[min(len(ordered) - 1, int(0.975 * len(ordered)))]
        result[m] = Strength(value=base[m], lo=lo, hi=hi)
    return result


# --- Role Adherence to the fixed persona (§10) --------------------------------

PERSONA_WORD_LIMIT = 30
PERSONA_WORD_LIMIT_MOVING = 15
_CHITCHAT_MARKERS = ("by the way", "fun fact", "honestly", "you know", "as an ai")


def role_adherence(answer: str, moving: bool = False) -> float:
    """Rule-based adherence to the safety-first, concise, calm persona, in [0, 1]."""
    score = 1.0
    limit = PERSONA_WORD_LIMIT_MOVING if moving else PERSONA_WORD_LIMIT
    words = len(answer.split())
    if words > limit:
        score -= min(0.5, (words - limit) / limit * 0.5)
    low = answer.lower()
    if any(marker in low for marker in _CHITCHAT_MARKERS):
        score -= 0.3
    return max(0.0, score)
