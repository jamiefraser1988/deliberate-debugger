"""
Judge component for deliberate debugger.

The judge assesses the quality of the solver's output based on simple heuristic
rules. The purpose of this component is to detect shallow or repetitive answers
and decide whether the solver's response can be accepted, whether it should
replan, or whether a full handoff/reset is required.
"""
from typing import Dict, Any, List


def judge_response(resp: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate the solver response and decide on next action.

    The judge uses a simple scoring approach:
      - Check that hypotheses and tests are present.
      - Penalise responses that propose fixes before conducting tests.
      - Penalise reuse of already attempted fixes.
      - If the overall score is high, accept the response. If medium, request a replan.
        Otherwise, recommend a handoff (full restart).

    :param resp: The structured response from the solver.
    :param state: The current debugging state including attempted fixes.
    :return: Dict with 'action' key ("pass", "replan" or "handoff") and additional info.
    """
    score = 100
    issues: List[str] = []

    # Ensure there are at least two hypotheses.
    hypotheses = resp.get("hypotheses", [])
    if not isinstance(hypotheses, list) or len(hypotheses) < 2:
        score -= 30
        issues.append("Too few hypotheses provided.")

    # Tests must be provided.
    tests = resp.get("tests", [])
    if not tests:
        score -= 30
        issues.append("No tests provided to validate hypotheses.")

    # Discourage suggesting fixes prematurely.
    fixes = resp.get("fixes", [])
    if fixes and len(tests) < 2:
        score -= 20
        issues.append("Fixes suggested without adequate testing.")

    # Penalise reuse of previously attempted fixes.
    for attempted in state.get("attempted_fixes", []):
        attempted_lower = attempted.lower()
        for fix in fixes:
            if attempted_lower in str(fix).lower():
                score -= 40
                issues.append(f"Reuse of failed fix: {fix}")
                break

    # Normalise score boundaries
    if score > 100:
        score = 100
    if score < 0:
        score = 0

    # Decide action
    if score >= 70:
        return {"action": "pass", "score": score}
    elif score >= 40:
        return {
            "action": "replan",
            "score": score,
            "issues": issues,
        }
    else:
        return {
            "action": "handoff",
            "score": score,
            "issues": issues,
        }
