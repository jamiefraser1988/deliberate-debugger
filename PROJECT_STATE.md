# PROJECT_STATE — deliberate-debugger

## Thesis
A local FastAPI service plus a Claude Code skill that forces hypothesis-first
debugging instead of "try random fixes" loops. Solver (LLM) produces ranked
hypotheses, tests, and fixes; a heuristic judge gates the response and routes
to pass / replan / handoff.

## What's done
- `backend/judge.py` — heuristic scorer (hypotheses, tests, premature-fix and reused-fix penalties) with pass/replan/handoff routing. Reused-fix detection uses Jaccard token overlap with stopword filtering.
- `backend/state.py` — `build_handoff()` assembles the session summary for handoff mode.
- `backend/main.py` — FastAPI app, `POST /debug` orchestration (solver → judge → pass/replan/handoff), CORS middleware, health-check `GET /debug`.
- `backend/solver.py` — `run_solver(req, state, mode)` for Anthropic (claude-opus-4-7 with adaptive thinking, lazy client) and OpenAI (gpt-4o JSON mode, lazy client). Model overrides via `ANTHROPIC_MODEL` / `OPENAI_MODEL` env vars. JSON extraction tolerant of code fences.
- `backend/tests/` — 23 tests, all passing.
- `skill/deliberate-debugger.md` — legacy single-file skill manifest (duplicate of the packaged one, kept until decision lands).
- `skill/deliberate-debugger/` — packaged skill: `SKILL.md`, `scripts/call_deliberate_debugger.py` (urllib-only CLI), `agents/openai.yaml`.
- `frontend/index.html` — browser demo UI for the API.

## What's next
1. Pick one canonical skill: delete `skill/deliberate-debugger.md` (single file) or delete the `skill/deliberate-debugger/` package. Two manifests with overlapping content invite drift.
2. Decide whether `frozen_decisions` in `build_handoff` is real (commit-phase placeholder) or should be removed; tests assert the key exists.
3. Review `frontend/index.html` for parity with the current API contract.
4. Consider exposing the judge thresholds (70/40) as constants or env config rather than magic numbers in `judge.py`.

## Decision Log
- 2026-05-06 — Solver clients now constructed lazily on first call, model defaults bumped to `claude-opus-4-7`, model names overridable via `ANTHROPIC_MODEL`/`OPENAI_MODEL`. Why: importing main no longer requires an API key (test suite import time dropped from ~10s to ~2.6s) and the latest Opus model is available.
- 2026-05-06 — Switched judge reused-fix detection from substring match to Jaccard token overlap (≥0.6) with a stopword-stripped vocabulary. Why: substring check false-positived on short attempted strings (e.g. "fix" matching every fix). Falls back to normalized equality when there are no significant tokens.
- 2026-05-06 — Renamed `skill/delibrate-debugger.md` → `skill/deliberate-debugger.md`. Why: typo fix; skill manifest filename should match the skill name.
- 2026-05-06 — Bootstrap `PROJECT_STATE.md` and per-project `CLAUDE.md` before further code changes. Why: align with global house rules.
- 2026-05-06 — Pass/replan/handoff thresholds set at 70 / 40 in `judge.py`. Why: matches the contract documented in the skill manifest.

## Known traps and lessons
- Tests in `backend/tests/test_api.py` patch `main.run_solver` by string path — the solver call must live as a module-level symbol in `main`, not be inlined inside the route handler, or the patch won't apply.
- Reused-fix detection is a case-insensitive substring match; short attempted strings can match unrelated fixes.

## Architecture
- Backend: FastAPI (Python 3.12). Entry point will be `backend/main.py` (not yet written). Components: `judge.py`, `state.py`.
- Solver providers: Anthropic or OpenAI, selected by `SOLVER_PROVIDER` env var; key from `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`.
- Skill: `skill/delibrate-debugger.md` calls `POST http://localhost:8000/debug`.
- Tests: pytest + `fastapi.testclient`; LLM call mocked via `unittest.mock.patch`.

## Out of scope
- Persistence / multi-session state — each `/debug` call is stateless; client passes `attempted_fixes`.
- Auth, rate limiting, deployment — local-only tool.
- Frontend / UI — the skill markdown is the only consumer surface.
