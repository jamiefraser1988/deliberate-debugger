from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from judge import judge_response
from solver import run_solver
from state import build_handoff


app = FastAPI(
    title="Deliberate Debugger",
    description="API for a deliberate debugging assistant with quality gating and handoff support.",
    version="0.1.0",
)


class DebugRequest(BaseModel):
    """Request body for debugging endpoint.

    - problem: description of the issue or error message
    - code: optional code snippet where the problem occurs
    - attempted_fixes: list of actions that have already been tried
    """
    problem: str
    code: str | None = ""
    attempted_fixes: List[str] = Field(default_factory=list)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/debug")
async def debug_status() -> Dict[str, str]:
    """Simple health check for the local deliberate debugger service."""
    return {"status": "ok"}


@app.post("/debug")
async def debug(req: DebugRequest) -> Dict[str, Any]:
    """
    Main endpoint to debug a problem.

    This endpoint accepts a debugging request, delegates the reasoning to the solver
    and then passes the solver's response through a judge layer. Depending on the
    judgement, it may return a normal response, trigger a replan, or recommend a
    session handoff.

    :param req: DebugRequest containing problem description, code, and attempted fixes.
    :return: A dictionary containing either a structured solver response or a handoff object.
    """
    state: Dict[str, Any] = {
        "attempted_fixes": req.attempted_fixes,
    }

    solver_response = run_solver(req, state)
    judgement = judge_response(solver_response, state)

    action = judgement.get("action")
    if action == "pass":
        return {
            "mode": "normal",
            "response": solver_response,
            "judge": judgement,
        }
    if action == "replan":
        replan_response = run_solver(req, state, mode="replan")
        return {
            "mode": "replan",
            "response": replan_response,
            "judge": judgement,
        }
    handoff = build_handoff(solver_response, state)
    return {
        "mode": "handoff",
        "handoff": handoff,
        "judge": judgement,
    }
