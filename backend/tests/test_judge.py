"""Tests for the judge component."""

import pytest
from judge import judge_response


def _good_response():
    return {
        "summary": "Something is broken.",
        "facts": ["fact1"],
        "hypotheses": [
            {"cause": "cause A", "confidence": 0.7},
            {"cause": "cause B", "confidence": 0.3},
        ],
        "tests": ["check import path", "inspect network"],
        "fixes": ["apply fix A if confirmed"],
    }


# ---------------------------------------------------------------------------
# pass (score >= 70)
# ---------------------------------------------------------------------------

def test_good_response_passes():
    result = judge_response(_good_response(), {})
    assert result["action"] == "pass"
    assert result["score"] == 100


def test_pass_score_boundary():
    """Exactly 70 should still be pass."""
    # Remove 30 points: fewer than 2 hypotheses
    resp = _good_response()
    resp["hypotheses"] = [{"cause": "only one", "confidence": 0.9}]
    result = judge_response(resp, {})
    assert result["score"] == 70
    assert result["action"] == "pass"


# ---------------------------------------------------------------------------
# replan (40 <= score < 70)
# ---------------------------------------------------------------------------

def test_no_hypotheses_triggers_replan():
    resp = _good_response()
    resp["hypotheses"] = []  # -30
    result = judge_response(resp, {})
    assert result["score"] == 70
    # Drop tests too; fixes remain so premature-fix penalty applies (-20)
    # 100 - 30 (no hyps) - 30 (no tests) - 20 (premature fixes) = 20 → handoff
    resp["tests"] = []
    resp["fixes"] = []  # clear fixes to avoid -20, giving 40 → replan
    result = judge_response(resp, {})
    assert result["score"] == 40
    assert result["action"] == "replan"


def test_fixes_without_tests_penalty():
    resp = _good_response()
    resp["tests"] = ["one test"]   # only 1 test → -20 for premature fixes
    result = judge_response(resp, {})
    assert result["score"] == 80
    assert result["action"] == "pass"

    resp["hypotheses"] = []  # -30 → 50
    result = judge_response(resp, {})
    assert result["score"] == 50
    assert result["action"] == "replan"


# ---------------------------------------------------------------------------
# handoff (score < 40)
# ---------------------------------------------------------------------------

def test_reused_fix_causes_handoff():
    resp = _good_response()
    resp["fixes"] = ["apply the same old fix"]
    state = {"attempted_fixes": ["apply the same old fix"]}
    result = judge_response(resp, state)
    # 100 - 40 (reused fix) = 60  → replan
    assert result["score"] == 60
    assert result["action"] == "replan"


def test_multiple_deductions_cause_handoff():
    resp = _good_response()
    resp["hypotheses"] = []           # -30
    resp["tests"] = []                # -30
    resp["fixes"] = ["retry the same fix"]
    state = {"attempted_fixes": ["retry the same fix"]}
    # 100 - 30 - 30 - 40 = 0  → handoff
    result = judge_response(resp, state)
    assert result["score"] == 0
    assert result["action"] == "handoff"


# ---------------------------------------------------------------------------
# score clamping
# ---------------------------------------------------------------------------

def test_score_does_not_go_below_zero():
    resp = _good_response()
    resp["hypotheses"] = []  # -30
    resp["tests"] = []       # -30
    resp["fixes"] = ["fix1"]
    state = {"attempted_fixes": ["fix1", "fix1", "fix1"]}
    result = judge_response(resp, state)
    assert result["score"] >= 0


# ---------------------------------------------------------------------------
# issues list
# ---------------------------------------------------------------------------

def test_issues_populated_on_replan():
    # Score 40 → replan: no hypotheses (-30), no tests (-30), no fixes (no -20)
    resp = _good_response()
    resp["hypotheses"] = []
    resp["tests"] = []
    resp["fixes"] = []
    result = judge_response(resp, {})
    assert result["action"] == "replan"
    assert "issues" in result
    assert any("hypothesis" in i.lower() or "hypothes" in i.lower() for i in result["issues"])
