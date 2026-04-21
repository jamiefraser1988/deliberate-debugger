"""
State and handoff utilities for the deliberate debugger.

This module contains helper functions to build a handoff object, which is used
when the judge determines that continuing the current session will not be
productive. The handoff summarises the current problem, confirmed facts, dead
ends, remaining hypotheses, and next steps.
"""
from typing import Dict, Any, List


def build_handoff(resp: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Construct a handoff packet summarising the current session.

    :param resp: The last solver response.
    :param state: The current debugging state.
    :return: A dictionary containing a compressed summary of the session.
    """
    # Extract hypotheses into simple list of cause descriptions.
    hypotheses_list: List[str] = []
    for hyp in resp.get("hypotheses", []):
        # Each hypothesis is expected to be a dict with 'cause'.
        if isinstance(hyp, dict):
            cause = hyp.get("cause")
            if cause:
                hypotheses_list.append(str(cause))

    return {
        "goal": resp.get("summary", "No summary available."),
        "confirmed_facts": resp.get("facts", []),
        "dead_ends": state.get("attempted_fixes", []),
        "open_hypotheses": hypotheses_list,
        "next_steps": resp.get("tests", []),
        "frozen_decisions": [],  # Placeholder: populate as part of commit phase in future extensions.
    }
