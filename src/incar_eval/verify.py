"""Cross-family auto-verification of synthesized gold cases.

Cuts the slice-9 human-verification bill: several *different-family* models each
independently map an utterance to a tool call. If enough of them agree, the gold
is auto-accepted; disagreements — plus any hand-authored safety / ambiguous /
out_of_scope cells (``force_manual``) — are flagged for human review.

This reuses the model-client port and the schema (so families propose against the
same frozen contract) and the cross-family principle from benchmark_spec.md §6
(a different family than the target avoids self-preference leaking into the data).
Wiring real clients is out of scope here (recorded fixtures / FakeModelClient).
"""

from collections import Counter
from dataclasses import dataclass

from .adapter import build_query_prompt, parse_tool_call
from .client import ModelClient
from .models import CarState, GoldRecord, ToolCall
from .safety import CATEGORICAL_SLOTS, NONCAT_OVERLAP, token_overlap


@dataclass(frozen=True)
class VerifierModel:
    name: str
    family: str
    client: ModelClient


@dataclass(frozen=True)
class Candidate:
    verifier: str
    family: str
    call: ToolCall


@dataclass(frozen=True)
class CaseSpec:
    utterance: str
    ambiguity: str = "clear"
    force_manual: bool = False  # safety / out_of_scope cells the author hand-writes
    car_state: CarState | None = None


@dataclass(frozen=True)
class VerificationResult:
    utterance: str
    candidates: list[Candidate]
    accepted: GoldRecord | None
    status: str  # "auto_accepted" | "flagged_disagreement" | "flagged_manual"
    reason: str


@dataclass(frozen=True)
class VerificationReport:
    results: list[VerificationResult]

    @property
    def accepted(self) -> list[GoldRecord]:
        return [r.accepted for r in self.results if r.accepted is not None]

    @property
    def flagged(self) -> list[VerificationResult]:
        return [r for r in self.results if r.accepted is None]

    @property
    def auto_accept_rate(self) -> float:
        return len(self.accepted) / len(self.results) if self.results else 0.0


def _consensus_slots(calls: list[ToolCall]) -> dict[str, object] | None:
    """Merge verifier proposals into a gold slot dict, or None if they genuinely
    disagree. Categorical/numeric slots must match exactly; non-categorical slots
    may differ in surface form (token overlap >= NONCAT_OVERLAP) and are merged into
    an acceptable-value list. A slot present in only some proposals = disagreement."""
    if len({c.intent for c in calls}) != 1:
        return None
    merged: dict[str, object] = {}
    for slot in set().union(*(set(c.slots) for c in calls)):
        present = [c.slots[slot] for c in calls if slot in c.slots]
        if len(present) != len(calls):
            return None
        first = present[0]
        if slot in CATEGORICAL_SLOTS or isinstance(first, (int, float, bool)):
            if any(v != first for v in present):
                return None
            merged[slot] = first
        else:
            if any(token_overlap(a, b) < NONCAT_OVERLAP for a in present for b in present):
                return None
            variants: list[object] = []
            for v in present:
                if v not in variants:
                    variants.append(v)
            merged[slot] = variants[0] if len(variants) == 1 else variants
    return merged


def verify_case(
    utterance: str,
    verifiers: list[VerifierModel],
    *,
    ambiguity: str = "clear",
    force_manual: bool = False,
    car_state: CarState | None = None,
    min_agreement: int = 2,
) -> VerificationResult:
    if len({v.family for v in verifiers}) < 2:
        raise ValueError("cross-family verification needs >=2 distinct families")

    # Ambiguous cells are never auto-accepted — their gold is the clarify behaviour,
    # which a content-only consensus can't establish.
    if force_manual or ambiguity == "ambiguous":
        reason = "ambiguous cell" if ambiguity == "ambiguous" else "hand-authored cell"
        return VerificationResult(utterance, [], None, "flagged_manual", reason)

    candidates = [
        Candidate(v.name, v.family, parse_tool_call(v.client.complete(build_query_prompt(utterance, car_state))))
        for v in verifiers
    ]
    # Majority by intent, then merge surface-variant slots within the winning group.
    intent_counts = Counter(c.call.intent for c in candidates)
    top_intent, top_n = intent_counts.most_common(1)[0]
    tied = sum(1 for n in intent_counts.values() if n == top_n) > 1
    group = [c.call for c in candidates if c.call.intent == top_intent]
    merged = _consensus_slots(group) if (top_n >= min_agreement and not tied) else None
    if merged is not None:
        gold = GoldRecord(utterance, top_intent, merged, ambiguity, car_state)
        return VerificationResult(
            utterance, candidates, gold, "auto_accepted", f"{top_n}/{len(verifiers)} agreed"
        )
    return VerificationResult(utterance, candidates, None, "flagged_disagreement", "no consensus")


def verify_batch(
    specs: list[CaseSpec], verifiers: list[VerifierModel], min_agreement: int = 2
) -> VerificationReport:
    return VerificationReport(
        [
            verify_case(
                s.utterance, verifiers,
                ambiguity=s.ambiguity, force_manual=s.force_manual,
                car_state=s.car_state, min_agreement=min_agreement,
            )
            for s in specs
        ]
    )
