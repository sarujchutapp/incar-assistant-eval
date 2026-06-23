from incar_eval.client import FakeModelClient
from incar_eval.live_client import (
    MODEL_TIERS,
    LiveModelClient,
    live_client_for_tier,
    record_responses,
)


# --- minimal stand-in for anthropic.Anthropic (no SDK, no network) ------------


class _Block:
    def __init__(self, type: str, text: str = "") -> None:
        self.type = type
        self.text = text


class _Message:
    def __init__(self, content: list[_Block]) -> None:
        self.content = content


class _Messages:
    def __init__(self, reply: list[_Block], calls: list[dict[str, object]]) -> None:
        self._reply = reply
        self._calls = calls

    def create(self, **kwargs: object) -> _Message:
        self._calls.append(kwargs)
        return _Message(self._reply)


class _StubAnthropic:
    def __init__(self, reply: list[_Block]) -> None:
        self.calls: list[dict[str, object]] = []
        self.messages = _Messages(reply, self.calls)


def test_complete_returns_concatenated_text() -> None:
    stub = _StubAnthropic([_Block("text", '{"intent": "set_climate"}')])
    client = LiveModelClient("claude-opus-4-8", _client=stub)

    assert client.complete("turn up the heat") == '{"intent": "set_climate"}'
    sent = stub.calls[0]
    assert sent["model"] == "claude-opus-4-8"
    assert sent["messages"] == [{"role": "user", "content": "turn up the heat"}]
    assert "system" not in sent  # omitted when no system prompt


def test_complete_skips_non_text_blocks_and_passes_system() -> None:
    stub = _StubAnthropic([_Block("thinking", "hmm"), _Block("text", "answer")])
    client = LiveModelClient("claude-haiku-4-5", system="be concise", _client=stub)

    assert client.complete("q") == "answer"
    assert stub.calls[0]["system"] == "be concise"


def test_tier_selection_maps_to_model_ids() -> None:
    assert MODEL_TIERS == {
        "opus": "claude-opus-4-8",
        "sonnet": "claude-sonnet-4-6",
        "haiku": "claude-haiku-4-5",
    }
    c = live_client_for_tier("haiku", _client=_StubAnthropic([_Block("text", "x")]))
    assert c.model == "claude-haiku-4-5"


def test_record_responses_round_trips_via_fake_client() -> None:
    # A live run records raw responses keyed by utterance...
    live = LiveModelClient(
        "claude-opus-4-8", _client=_StubAnthropic([_Block("text", '{"intent":"navigate"}')])
    )
    recorded = record_responses(live, {"take me home": "...prompt embedding take me home..."})
    assert recorded == {"take me home": '{"intent":"navigate"}'}

    # ...and replays deterministically with no client / no network.
    replay = FakeModelClient(recorded)
    assert replay.complete('Driver said: "take me home"') == '{"intent":"navigate"}'
