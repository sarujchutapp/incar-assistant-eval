"""Tests for the SkillOpt unified-env dispatch scorer (integrations/…/evaluator.py).

Loaded by file path — the integrations tree isn't an installed package, but the
evaluator only depends on incar_eval, so it imports cleanly standalone.
"""
import importlib.util
from pathlib import Path

_EVAL = (
    Path(__file__).resolve().parent.parent
    / "integrations" / "skillopt" / "envs" / "incar_unified" / "evaluator.py"
)
_spec = importlib.util.spec_from_file_location("unified_evaluator", _EVAL)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
evaluate = _mod.evaluate


def _cmd(**kw):
    return {"id": "t", "case_type": "command", "expected_slots": {}, **kw}


def test_soft_zero_when_acting_on_ambiguous() -> None:
    # u_6: "call him back" — ambiguous, executed with a pronoun slot. Right domain,
    # wrong action -> soft must be 0 (was 0.5), or it rewards the unsafe behavior.
    item = _cmd(utterance="call him back", expected_intent="call_contact", ambiguity="ambiguous")
    r = evaluate(item, '{"intent": "call_contact", "slots": {"name": "him"}, "mode": "execute"}')
    assert r["hard"] == 0.0
    assert r["soft"] == 0.0


def test_soft_full_when_clarifying_ambiguous() -> None:
    item = _cmd(utterance="call him back", expected_intent="call_contact", ambiguity="ambiguous")
    r = evaluate(item, '{"intent": "call_contact", "slots": {}, "mode": "clarify"}')
    assert r["hard"] == 1.0
    assert r["soft"] == 1.0


def test_soft_unchanged_on_clear_command() -> None:
    # clear case: acting is correct, so soft keeps partial credit (0.5*intent+0.5*f1)
    item = _cmd(utterance="navigate home", expected_intent="navigate",
                expected_slots={"destination": "home"}, ambiguity="clear")
    r = evaluate(item, '{"intent": "navigate", "slots": {"destination": "work"}, "mode": "execute"}')
    assert r["hard"] == 0.0        # wrong slot -> not a success
    assert r["soft"] == 0.5        # but right intent still earns partial credit
