"""Integration tests for the /debug endpoint.

The solver's LLM call is mocked so tests run without a real API key.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

# A solver response that the judge will score 100 (pass).
GOOD_SOLVER_RESP = {
    "summary": "Import error in module X.",
    "facts": ["Python 3.11", "module X not installed"],
    "hypotheses": [
        {"cause": "missing package", "confidence": 0.8},
        {"cause": "wrong import path", "confidence": 0.2},
    ],
    "tests": ["check pip list", "verify import path"],
    "fixes": ["pip install module-x"],
}

# A solver response that the judge will score 40 (replan boundary).
WEAK_SOLVER_RESP = {
    "summary": "Unclear error.",
    "facts": [],
    "hypotheses": [],       # -30
    "tests": [],            # -30
    "fixes": [],
}


def test_debug_pass_mode():
    with patch("main.run_solver", return_value=GOOD_SOLVER_RESP):
        resp = client.post("/debug", json={"problem": "ImportError on startup"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "normal"
    assert "response" in body
    assert body["judge"]["action"] == "pass"


def test_debug_replan_mode():
    with patch("main.run_solver", return_value=WEAK_SOLVER_RESP):
        resp = client.post("/debug", json={"problem": "Something is wrong"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "replan"
    assert body["judge"]["action"] == "replan"


def test_debug_handoff_mode():
    # Score < 40: no hypotheses (-30), no tests (-30), reused fix (-40) = 0
    bad_resp = {
        **WEAK_SOLVER_RESP,
        "fixes": ["the same fix"],
    }
    state_with_attempted = {"attempted_fixes": ["the same fix"]}
    with patch("main.run_solver", return_value=bad_resp):
        resp = client.post(
            "/debug",
            json={
                "problem": "Still broken",
                "attempted_fixes": ["the same fix"],
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "handoff"
    assert "handoff" in body


def test_debug_with_code_and_attempted_fixes():
    with patch("main.run_solver", return_value=GOOD_SOLVER_RESP):
        resp = client.post(
            "/debug",
            json={
                "problem": "TypeError",
                "code": "def foo(x): return x + 1",
                "attempted_fixes": ["added type hint"],
            },
        )
    assert resp.status_code == 200
    assert resp.json()["mode"] == "normal"


def test_debug_missing_problem_returns_422():
    resp = client.post("/debug", json={})
    assert resp.status_code == 422


def test_api_key_required_when_env_set(monkeypatch):
    monkeypatch.setenv("DEBUGGER_API_KEY", "secret")
    with patch("main.run_solver", return_value=GOOD_SOLVER_RESP):
        resp = client.post("/debug", json={"problem": "x"})
    assert resp.status_code == 401


def test_api_key_accepted_when_header_matches(monkeypatch):
    monkeypatch.setenv("DEBUGGER_API_KEY", "secret")
    with patch("main.run_solver", return_value=GOOD_SOLVER_RESP):
        resp = client.post(
            "/debug",
            json={"problem": "x"},
            headers={"X-API-Key": "secret"},
        )
    assert resp.status_code == 200
    assert resp.json()["mode"] == "normal"


def test_api_key_disabled_when_env_blank(monkeypatch):
    monkeypatch.setenv("DEBUGGER_API_KEY", "")
    with patch("main.run_solver", return_value=GOOD_SOLVER_RESP):
        resp = client.post("/debug", json={"problem": "x"})
    assert resp.status_code == 200
