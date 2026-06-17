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
        for utterance, raw in self._responses.items():
            if utterance in prompt:
                return raw
        raise KeyError(f"FakeModelClient has no canned response for prompt: {prompt!r}")
