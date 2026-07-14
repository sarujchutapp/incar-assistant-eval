from pathlib import Path

from incar_eval.chat import (
    ChatCase,
    build_chat_prompt,
    run_chat_benchmark,
    score_chat_case,
)
from incar_eval.client import FakeModelClient
from incar_eval.loader import load_chat_cases

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


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


def test_faithful_tolerates_number_word_and_unit_variants() -> None:
    case = ChatCase("how long is traffic adding?", fact="12 minutes")
    assert score_chat_case(case, "It's adding about twelve minutes.").faithful
    assert score_chat_case(case, "Traffic is adding 12 min to your trip.").faithful
    # a genuinely different number still fails
    assert not score_chat_case(case, "Traffic is adding 20 minutes.").faithful


def test_faithful_folds_percent_symbol() -> None:
    # "48%" and "48 percent" are spoken identically -> must score the same
    case = ChatCase("what's the battery level?", fact="48 percent")
    assert score_chat_case(case, "You're at 48%.").faithful
    assert score_chat_case(case, "Battery is 48 percent.").faithful
    assert not score_chat_case(case, "You're at 60%.").faithful


def test_off_topic_answer_has_low_relevancy() -> None:
    case = ChatCase("what's my ETA?", fact="25 minutes")
    on_topic = score_chat_case(case, "Your ETA is 25 minutes.")
    off_topic = score_chat_case(case, "The weather is sunny today.")
    assert on_topic.relevancy > off_topic.relevancy


def test_unanswerable_case_passes_when_model_abstains() -> None:
    # context does not support an answer -> the honest response is to decline
    case = ChatCase("what's the tire pressure?", context="Fuel range: 210 miles.", answerable=False)
    assert score_chat_case(case, "I don't have the tire pressure right now.").success
    assert score_chat_case(case, "Sorry, that's not available to me.").success


def test_unanswerable_case_fails_when_model_hallucinates() -> None:
    # answering anyway (any confident number) is a hallucination -> failure
    case = ChatCase("what's the tire pressure?", context="Fuel range: 210 miles.", answerable=False)
    assert not score_chat_case(case, "Your tire pressure is 32 psi.").success
    assert not score_chat_case(case, "It's 210 miles.").success


def test_prompt_feeds_context_to_the_model() -> None:
    grounded = ChatCase("what's my ETA?", fact="25 minutes", context="ETA: 25 minutes.")
    prompt = build_chat_prompt(grounded)
    assert "ETA: 25 minutes." in prompt  # grounding context is shown
    assert "what's my ETA?" in prompt
    # a case without context keeps the closed-book prompt (no empty Context block)
    assert "Context" not in build_chat_prompt(ChatCase("what's my ETA?", fact="25 minutes"))


def test_shipped_grounded_corpus_is_grounded_and_contamination_proof() -> None:
    cases = load_chat_cases(_FIXTURES / "chat_grounded.json")
    assert cases  # a grounded corpus ships
    for case in cases:
        assert case.context  # every grounded case carries context
        if not case.answerable:
            # unanswerable-by-construction: the context deliberately does NOT
            # contain the answer (hallucination check), so the grounded invariant
            # below doesn't apply — success is abstention, tested separately.
            continue
        # the answer is derivable from the context ...
        assert score_chat_case(case, case.context).faithful, case.question
        # ... and NOT given away by the question alone (memorization can't help)
        assert not score_chat_case(ChatCase(case.question, case.fact), case.question).faithful, case.question


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
