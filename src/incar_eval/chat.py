"""Chat / informational quadrant — objective-by-construction cases.

Restricted to questions with a verifiable answer (ETA, fuel level, factual
lookup). Faithfulness (does the answer match the provided fact) is the
correctness gate; answer relevancy is reported alongside. The open/subjective
tail with an LLM judge is slice 7. Reuses the model-client port.
"""

import re
from dataclasses import dataclass

from .client import ModelClient
from .safety import _tokens  # shared number-word / value canonicalization

_STOPWORDS = frozenset(
    {"the", "a", "an", "is", "are", "my", "what", "whats", "s", "to", "of", "in",
     "how", "much", "do", "i", "me", "you", "it", "on", "for", "and"}
)

SYSTEM_PROMPT = (
    "You are a safety-first in-car voice assistant. Answer the driver's question "
    "concisely and accurately."
)


@dataclass(frozen=True)
class ChatCase:
    question: str
    fact: str  # the ground-truth fact the answer must contain
    #: A short car-telemetry / KB snippet fed to the model. When set, the answer
    #: is derivable only from here (contamination-proof grounding). Empty = the
    #: original closed-book case.
    context: str = ""


@dataclass(frozen=True)
class ChatOutcome:
    case: ChatCase
    answer: str
    faithful: bool
    relevancy: float

    @property
    def success(self) -> bool:
        return self.faithful


@dataclass(frozen=True)
class ChatMetrics:
    n: int
    faithfulness_rate: float
    mean_relevancy: float


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", text.lower())


def _content_words(text: str) -> set[str]:
    return {w for w in _normalize(text).split() if w and w not in _STOPWORDS}


#: Unit abbreviations/singulars -> a canonical form, so "12 min" / "12 minute"
#: match fact "12 minutes". Number words are already handled by safety._tokens.
_UNIT_SYNONYMS = {
    "min": "minutes", "mins": "minutes", "minute": "minutes",
    "hr": "hours", "hrs": "hours", "hour": "hours",
    "sec": "seconds", "secs": "seconds", "second": "seconds",
    "mi": "miles", "mile": "miles",
    "km": "kilometers", "kilometre": "kilometers", "kilometres": "kilometers", "kilometer": "kilometers",
    "pct": "percent", "percentage": "percent",
    "deg": "degrees", "degree": "degrees",
}


def _canon(text: str) -> list[str]:
    """Canonical token stream: number words -> digits (safety._tokens), then unit
    abbreviations/singulars folded to one form."""
    return [_UNIT_SYNONYMS.get(t, t) for t in _tokens(text)]


def _faithful(fact: str, answer: str) -> bool:
    """The fact's canonical tokens appear as a contiguous run in the answer."""
    needle, hay = _canon(fact), _canon(answer)
    if not needle:
        return True
    return any(hay[i:i + len(needle)] == needle for i in range(len(hay) - len(needle) + 1))


def _relevancy(question: str, answer: str) -> float:
    q_words = _content_words(question)
    if not q_words:
        return 0.0
    return len(q_words & _content_words(answer)) / len(q_words)


def score_chat_case(case: ChatCase, answer: str) -> ChatOutcome:
    return ChatOutcome(
        case=case,
        answer=answer,
        faithful=_faithful(case.fact, answer),
        relevancy=_relevancy(case.question, answer),
    )


def build_chat_prompt(case: ChatCase) -> str:
    context = f"Context:\n{case.context}\n\n" if case.context else ""
    return f"{SYSTEM_PROMPT}\n\n{context}Driver asks: \"{case.question}\""


def run_chat_benchmark(
    cases: list[ChatCase], client: ModelClient
) -> tuple[list[ChatOutcome], ChatMetrics]:
    outcomes = [score_chat_case(case, client.complete(build_chat_prompt(case))) for case in cases]
    n = len(outcomes)
    metrics = ChatMetrics(
        n=n,
        faithfulness_rate=(sum(o.faithful for o in outcomes) / n) if n else 0.0,
        mean_relevancy=(sum(o.relevancy for o in outcomes) / n) if n else 0.0,
    )
    return outcomes, metrics
