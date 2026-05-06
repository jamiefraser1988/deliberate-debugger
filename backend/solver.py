"""
Solver component for the deliberate debugger.

Supports two LLM providers, selected via the SOLVER_PROVIDER environment variable:
  - "anthropic" (default) — uses claude-opus-4-6 with adaptive thinking
  - "openai"              — uses gpt-4o with JSON response format

Set the matching API key:
  ANTHROPIC_API_KEY  for Anthropic
  OPENAI_API_KEY     for OpenAI
"""

import json
import os
import re
from typing import Any, Dict

# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------

PROVIDER = os.environ.get("SOLVER_PROVIDER", "anthropic").lower()

# Clients are constructed lazily on first call. Eager construction at import
# time required an API key just to import `main` (and therefore to collect
# tests), even though tests mock the solver.
_anthropic_client = None
_openai_client = None


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        _anthropic_client = anthropic.Anthropic()
    return _anthropic_client


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI()
    return _openai_client


# ---------------------------------------------------------------------------
# Shared prompt content
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a debugging assistant. "
    "Return ONLY valid JSON — no markdown fences, no explanation outside the JSON. "
    "The JSON must have exactly these keys: "
    "summary (string), facts (list of strings), hypotheses (list of objects with "
    "'cause' (string) and 'confidence' (float 0-1)), tests (list of strings), "
    "fixes (list of strings). "
    "Provide at least two hypotheses with different confidence scores. "
    "List tests before fixes — fixes should only be proposed after tests are outlined."
)


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> Dict[str, Any]:
    """
    Extract a JSON object from model output.

    Handles both bare JSON and output wrapped in markdown code fences.
    Raises ValueError if no valid JSON object is found.
    """
    stripped = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
    stripped = re.sub(r"\n?```$", "", stripped.strip())

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())

    raise ValueError(f"No valid JSON found in model output: {text[:200]!r}")


# ---------------------------------------------------------------------------
# Provider-specific LLM calls
# ---------------------------------------------------------------------------

def _call_anthropic(system: str, user: str) -> str:
    """Call Claude with adaptive thinking and return the text block."""
    with _get_anthropic_client().messages.stream(
        model=os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7"),
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        message = stream.get_final_message()

    return next(
        (block.text for block in message.content if block.type == "text"),
        "",
    )


def _call_openai(system: str, user: str) -> str:
    """Call gpt-4o with JSON response format and return the content string."""
    response = _get_openai_client().chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content or ""


def _call_llm(system: str, user: str) -> str:
    if PROVIDER == "openai":
        return _call_openai(system, user)
    return _call_anthropic(system, user)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_prompt(req: Any, state: Dict[str, Any], mode: str) -> str:
    """
    Build a user-turn prompt for the debugging request.

    :param req: DebugRequest instance containing problem and code.
    :param state: Current debugging state.
    :param mode: "normal" or "replan".
    :return: A prompt string.
    """
    parts = []

    if mode == "replan":
        parts.append(
            "The previous debugging plan was deemed inadequate. "
            "Produce a fresh plan based solely on the known facts and remaining hypotheses.\n"
        )

    parts.append(f"Problem description:\n{req.problem}\n")

    if getattr(req, "code", ""):
        parts.append(f"Code snippet:\n{req.code}\n")

    attempted = state.get("attempted_fixes", [])
    if attempted:
        lines = "\n".join(f"- {fix}" for fix in attempted)
        parts.append(f"Attempted fixes (already tried, do NOT repeat):\n{lines}\n")

    return "\n".join(parts)


def run_solver(req: Any, state: Dict[str, Any], mode: str = "normal") -> Dict[str, Any]:
    """
    Generate a structured debugging response using the configured LLM provider.

    :param req: DebugRequest with problem description, code, and attempted fixes.
    :param state: Current debugging state.
    :param mode: Mode of operation ("normal" or "replan").
    :return: A dictionary with structured debugging information.
    """
    prompt = build_prompt(req, state, mode)

    try:
        text = _call_llm(_SYSTEM_PROMPT, prompt)
        return _extract_json(text)
    except (ValueError, json.JSONDecodeError) as exc:
        return {
            "summary": f"Failed to parse model output: {exc}",
            "facts": [],
            "hypotheses": [],
            "tests": [],
            "fixes": [],
        }
