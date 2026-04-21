---
name: deliberate-debugger
description: Structured debugging through the local Deliberate Debugger API. Use when Codex is debugging a bug, failing test, runtime error, regression, or "why is this broken?" question and should generate ranked hypotheses, validation tests, and candidate fixes before editing code. Especially use it when previous fixes have already failed or when the debugging plan needs to be systematic instead of ad hoc.
---

# Deliberate Debugger

## Overview

Use the local Deliberate Debugger service at `http://localhost:8000/debug` to force hypothesis-first debugging instead of random fix attempts. Treat the service as a planning layer: gather the problem statement, relevant code, and attempted fixes, call the API, then execute the returned tests before applying fixes.

## Quick Start

1. Ensure the service is running.
   If the deliberate-debugger repository is available, start the backend from its `backend/` directory. On Windows, prefer the project virtualenv when present:
   `.\.venv\Scripts\python -m uvicorn main:app --reload`
   Otherwise use:
   `python -m uvicorn main:app --reload`
2. Prepare the request inputs.
   - `problem`: concise description of the failure or unexpected behaviour
   - `code`: the smallest relevant snippet or stack-trace context
   - `attempted_fixes`: every fix already tried, even partial attempts
3. Prefer the bundled helper script in this skill:
   `python scripts/call_deliberate_debugger.py "TypeError: unsupported operand type(s) for +: 'int' and 'str'" --code-file path/to/snippet.py --attempted-fix "cast label to int"`
4. Read `mode` first, then follow the workflow below.

## Workflow

1. Prefer tests over fixes.
   The service ranks hypotheses and returns tests first. Run the tests in order before touching code.
2. Branch on `mode`.
   - `normal`: use `response.tests`, then apply the most justified fix
   - `replan`: treat the returned `response` as a second-pass plan and inspect `judge.issues` to see what was weak about the first one
   - `handoff`: stop guessing, surface `handoff.open_hypotheses` and `handoff.next_steps`, and ask the user whether to continue from that state
3. Re-call the service after each failed fix.
   Add the failed fix to `attempted_fixes` so the judge can penalize recycled advice.
4. Keep the code snippet focused.
   Large files dilute the hypotheses. Prefer the smallest snippet that still shows the bug.
5. Treat the output as structured guidance, not ground truth.
   Validate with local tests, logs, or a repro before claiming a fix.

## API Contract

Send a `POST` request to `http://localhost:8000/debug` with:

```json
{
  "problem": "Description of the bug or unexpected behaviour",
  "code": "Relevant snippet or trace context",
  "attempted_fixes": ["Fixes that have already failed"]
}
```

Use `GET /debug` as a lightweight health check when needed.

## Response Handling

- `mode: "normal"` means the judge accepted the plan. Work through the tests first.
- `mode: "replan"` means the first plan was too shallow. Use the returned response as the replanned version.
- `mode: "handoff"` means the session is stuck. Surface the handoff packet instead of inventing more fixes.

The judge score thresholds in this repository are:
- `>= 70`: pass
- `40-69`: replan
- `< 40`: handoff

## Local Notes

- `attempted_fixes` matters. The judge penalizes repeated fixes, so always include prior dead ends.
- Provider selection is controlled by `SOLVER_PROVIDER`.
  - `openai` requires `OPENAI_API_KEY`
  - `anthropic` requires `ANTHROPIC_API_KEY`
- If you are working inside this repository, the API entrypoint is `backend/main.py` and the browser demo lives in `frontend/index.html`.
