"""Tests for the state/handoff utilities."""

from state import build_handoff


def _solver_resp():
    return {
        "summary": "Something is broken.",
        "facts": ["fact A", "fact B"],
        "hypotheses": [
            {"cause": "cause X", "confidence": 0.8},
            {"cause": "cause Y", "confidence": 0.2},
        ],
        "tests": ["test step 1", "test step 2"],
        "fixes": ["fix 1"],
    }


def test_handoff_keys():
    handoff = build_handoff(_solver_resp(), {})
    assert set(handoff.keys()) == {
        "goal",
        "confirmed_facts",
        "dead_ends",
        "open_hypotheses",
        "next_steps",
        "frozen_decisions",
    }


def test_handoff_goal_from_summary():
    handoff = build_handoff(_solver_resp(), {})
    assert handoff["goal"] == "Something is broken."


def test_handoff_facts():
    handoff = build_handoff(_solver_resp(), {})
    assert handoff["confirmed_facts"] == ["fact A", "fact B"]


def test_handoff_dead_ends_from_state():
    state = {"attempted_fixes": ["tried X", "tried Y"]}
    handoff = build_handoff(_solver_resp(), state)
    assert handoff["dead_ends"] == ["tried X", "tried Y"]


def test_handoff_open_hypotheses_extracts_causes():
    handoff = build_handoff(_solver_resp(), {})
    assert "cause X" in handoff["open_hypotheses"]
    assert "cause Y" in handoff["open_hypotheses"]


def test_handoff_next_steps_from_tests():
    handoff = build_handoff(_solver_resp(), {})
    assert handoff["next_steps"] == ["test step 1", "test step 2"]


def test_handoff_missing_summary():
    resp = {}
    handoff = build_handoff(resp, {})
    assert handoff["goal"] == "No summary available."


def test_handoff_hypothesis_without_cause_skipped():
    resp = _solver_resp()
    resp["hypotheses"] = [{"confidence": 0.5}]  # no 'cause' key
    handoff = build_handoff(resp, {})
    assert handoff["open_hypotheses"] == []
