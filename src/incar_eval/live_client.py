"""Live ModelClient backed by the Anthropic API — real candidate models.

The benchmark depends only on the ``ModelClient`` port (``client.py``); this is
the production implementation that calls a real LLM, for runs against actual
target models rather than ``FakeModelClient`` / recorded fixtures.

The ``anthropic`` SDK is an **optional** dependency (the ``live`` extra) and is
imported lazily, so the core package and the deterministic test suite never need
it and CI stays offline. To make a live run reproducible (and free to re-run),
freeze it with :func:`record_responses` and replay via ``FakeModelClient``.
"""

import os
from typing import Any

from .client import ModelClient

#: Tier name -> Claude model id, so the discrimination demo can run the same
#: dataset across model tiers. Model ids per the claude-api reference.
MODEL_TIERS: dict[str, str] = {
    "opus": "claude-opus-4-8",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5",
}


class LiveModelClient:
    """Calls a real Anthropic model and returns its raw text response.

    Implements the ``ModelClient`` protocol. ``_client`` is injectable so tests
    can supply a stub; in production it is constructed lazily from the SDK,
    resolving the key from ``api_key`` or ``ANTHROPIC_API_KEY``.
    """

    def __init__(
        self,
        model: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        api_key: str | None = None,
        _client: Any = None,
    ) -> None:
        self.model = model
        self.system = system
        self.max_tokens = max_tokens
        if _client is not None:
            self._client: Any = _client
        else:
            import anthropic  # lazy: optional `live` dependency, never imported in CI

            self._client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def complete(self, prompt: str) -> str:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self.system is not None:
            kwargs["system"] = self.system
        message = self._client.messages.create(**kwargs)
        return "".join(block.text for block in message.content if block.type == "text")


def live_client_for_tier(tier: str, **kwargs: Any) -> LiveModelClient:
    """Build a live client for a named tier (``opus`` / ``sonnet`` / ``haiku``)."""
    return LiveModelClient(MODEL_TIERS[tier], **kwargs)


def record_responses(client: ModelClient, prompts: dict[str, str]) -> dict[str, str]:
    """Call ``client`` for each ``{key: prompt}`` and capture the raw response.

    Keys (utterances / questions) are what ``FakeModelClient`` matches on at
    replay, so the returned ``{key: raw_response}`` mapping can be saved as a
    fixture and replayed deterministically with no API access.
    """
    return {key: client.complete(prompt) for key, prompt in prompts.items()}
