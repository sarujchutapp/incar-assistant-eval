from incar_eval.chat import (
    ChatCase,
    run_chat_benchmark,
    score_chat_case,
)
from incar_eval.client import FakeModelClient


def test_faithful_answer_passes() -> None:
    case = ChatCase("what's my ETA?", fact="25 minutes")
    outcome = score_chat_case(case, "Your ETA is about 25 minutes.")
    assert outcome.faithful
    assert outcome.success


def test_unfaithful_answer_fails() -> None:
    case = ChatCase("what's my ETA?", fact="25 minutes")
    outcome = score_chat_case(case, "Your ETA is about 40 minutes.")
    assert not outcome.faithful
    assert not outcome.success


def test_off_topic_answer_has_low_relevancy() -> None:
    case = ChatCase("what's my ETA?", fact="25 minutes")
    on_topic = score_chat_case(case, "Your ETA is 25 minutes.")
    off_topic = score_chat_case(case, "The weather is sunny today.")
    assert on_topic.relevancy > off_topic.relevancy


def test_chat_benchmark_reuses_model_client_port() -> None:
    cases = [
        ChatCase("what's my ETA?", fact="25 minutes"),
        ChatCase("how much fuel is left?", fact="low"),
    ]
    client = FakeModelClient(
        {
            "what's my ETA?": "About 25 minutes.",
            "how much fuel is left?": "Fuel is high, plenty left.",  # wrong -> unfaithful
        }
    )
    outcomes, metrics = run_chat_benchmark(cases, client)
    assert len(outcomes) == 2
    assert metrics.faithfulness_rate == 0.5
    assert 0.0 <= metrics.mean_relevancy <= 1.0
