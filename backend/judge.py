"""
Judge component for deliberate debugger.

The judge assesses the quality of the solver's output based on simple heuristic
rules. The purpose of this component is to detect shallow or repetitive answers
and decide whether the solver's response can be accepted, whether it should
replan, or whether a full handoff/reset is required.
"""
import re
from typing import Dict, Any, List, Set

_STOPWORDS = {
    "a", "an", "the", "and", "or", "to", "of", "in", "on", "for", "with",
    "is", "it", "be", "this", "that", "by", "as", "at", "from", "if", "then",
    "try", "tried", "fix", "fixes", "issue", "bug", "problem",
}


def _tokens(text: str) -> Set[str]:
    """Normalize a fix description into a set of significant tokens."""
    return {
        t for t in re.findall(r"[a-z0-9]+", text.lower())
        if len(t) >= 3 and t not in _STOPWORDS
    }


def _is_repeated_fix(attempted: str, fix: str) -> bool:
    """True when `fix` is substantially the same as a previously attempted one.

    Uses Jaccard overlap on significant tokens (with stopwords stripped) to
    avoid the false positives of a raw substring check — e.g. attempted="fix"
    no longer matches every fix string that contains the word "fix".
    """
    a, b = _tokens(attempted), _tokens(fix)
    if not a or not b:
        # Fall back to normalized equality when there are no significant tokens.
        return attempted.strip().lower() == fix.strip().lower()
    overlap = len(a & b) / len(a | b)
    return overlap >= 0.6


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
        for fix in fixes:
            if _is_repeated_fix(str(attempted), str(fix)):
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
