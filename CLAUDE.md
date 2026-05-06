# CLAUDE.md — deliberate-debugger

## Read PROJECT_STATE.md first
Every session, before any work, read `PROJECT_STATE.md` in this repo. It is
canonical state. When it disagrees with chat history, the file wins.

## How to work in this repo
- Python backend lives in `backend/`. Use the local venv: `backend/.venv/Scripts/python.exe` (Windows).
- Install deps: `backend/.venv/Scripts/pip install -r backend/requirements.txt`.
- Run tests: `cd backend && .venv/Scripts/python -m pytest`.
- Run server: `cd backend && .venv/Scripts/uvicorn main:app --reload`.
- Required env: `SOLVER_PROVIDER` (`anthropic` or `openai`) plus the matching API key.

## Precedence
`PROJECT_STATE.md` > per-project `CLAUDE.md` > chat history. If anything I claim
in chat contradicts the file, ask before acting.

## When to update PROJECT_STATE.md
Edit in the same turn when:
- A decision lands → new Decision Log row (newest first).
- Thesis or pivot status changes → rewrite Thesis.
- A "What's next" item finishes → move it to "What's done".
- A new trap is found → add to "Known traps and lessons".
- ~20 turns since last touch → re-read, trim bloat, verify Thesis still matches reality.

Show the diff before saving. Don't commit unless asked.

## House style
- No new dependencies without flagging first. Current set: fastapi, uvicorn, pydantic, anthropic, openai, pytest, pytest-asyncio, httpx.
- Don't create README/CHANGELOG/docs unless explicitly asked. `PROJECT_STATE.md` and this file are the exception.
- No emojis in code or docs.
- Prefer editing existing files over creating new ones.
- The solver call in `main.py` MUST be a module-level function named `run_solver` — tests patch it by string path.
- Keep judge thresholds (70 / 40) and the response shape (`mode`, `response`, `judge`, `handoff`) stable; the skill manifest documents these as the public contract.
