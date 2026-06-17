"""The model-client port — the single LLM boundary.

Everything that needs an LLM (the target adapter now, the chat judge later)
depends on this Protocol. Tests and the recorded-fixtures demo inject
``FakeModelClient``; a live implementation that hits an LLM API is added when a
real run is needed, but is never exercised in CI.
"""

from typing import Protocol


class ModelClient(Protocol):
    def complete(self, prompt: str) -> str:
        """Return the model's raw text response to ``prompt``."""
        ...


class FakeModelClient:
    """Returns canned raw responses keyed by the utterance embedded in the prompt."""

    def __init__(self, responses: dict[str, str]) -> None:
        self._responses = responses

    def complete(self, prompt: str) -> str:
        # Pick the response whose utterance appears latest in the prompt, so that
        # multi-turn prompts (which embed history) resolve to the current turn.
        best_raw: str | None = None
        best_pos = -1
        for utterance, raw in self._responses.items():
            pos = prompt.rfind(utterance)
            if pos > best_pos:
                best_pos, best_raw = pos, raw
        if best_raw is None:
            raise KeyError(f"FakeModelClient has no canned response for prompt: {prompt!r}")
        return best_raw
