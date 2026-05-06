---
name: deliberate-debugger
description: >
  Structured debugging assistant that prevents shallow "try random things" loops.
  Use this skill whenever you need to debug a bug, error, or unexpected behaviour —
  especially when stuck, when fixes have already been tried, or when you want to
  reason systematically before touching code. The skill calls the Deliberate
  Debugger API (running locally at http://localhost:8000), which generates ranked
  hypotheses, designs tests, and proposes fixes in a principled order. It
  quality-gates the response and automatically replans or hands off if the output
  is too shallow. Trigger this skill for ANY debugging task: error traces, wrong
  output, failing tests, performance regressions, "why is this broken?" questions.
---

# Deliberate Debugger Skill

You have access to the Deliberate Debugger API — a structured debugging engine
that forces hypothesis-first reasoning rather than random fix attempts. Use it
to get a grounded debugging plan, then execute that plan.

## When to use

- Any bug, error message, or unexpected behaviour
- When you've already tried a fix and it didn't work
- When you want to understand *why* something is broken before changing code
- When the problem is subtle and you don't want to thrash

## API

**Endpoint:** `POST http://localhost:8000/debug`

**Request body:**
```json
{
  "problem": "Description of the error or unexpected behaviour (required)",
  "code":    "Relevant code snippet (optional but recommended)",
  "attempted_fixes": ["List of things already tried (optional)"]
}
```

**Always include `attempted_fixes`** — even partial attempts. The judge
penalises responses that recycle already-tried fixes, so this is what prevents
going in circles.

## Response modes

The API returns one of three modes. Read the `mode` field first.

### `"normal"` — good plan, use it

```json
{
  "mode": "normal",
  "response": {
    "summary": "...",
    "facts": ["..."],
    "hypotheses": [{"cause": "...", "confidence": 0.7}, ...],
    "tests":  ["..."],
    "fixes":  ["..."]
  },
  "judge": {"action": "pass", "score": 95}
}
```

Work through `tests` in order before applying any `fixes`. The hypotheses are
ranked by confidence — start investigating the highest-confidence one first.

### `"replan"` — first attempt was shallow, try the replanned response

```json
{
  "mode": "replan",
  "response": { ... },
  "judge": {"action": "replan", "score": 55, "issues": ["..."]}
}
```

The `response` is already the second attempt. Check `judge.issues` to
understand what was weak about the first plan (e.g. too few hypotheses,
premature fixes). Use the `response` the same way as `normal`.

### `"handoff"` — session is stuck, use the summary to restart

```json
{
  "mode": "handoff",
  "handoff": {
    "goal":              "What we're trying to fix",
    "confirmed_facts":   ["Things we know to be true"],
    "dead_ends":         ["Fixes already tried that didn't work"],
    "open_hypotheses":   ["Leads still worth investigating"],
    "next_steps":        ["Concrete actions to take next"]
  },
  "judge": {"action": "handoff", "score": 20, "issues": ["..."]}
}
```

When you get a handoff, surface it to the user — tell them the session has
exhausted its current reasoning and show them `open_hypotheses` and
`next_steps`. Ask whether to continue from there or try a different angle.

## Workflow

```
1. Call POST /debug with problem + code + attempted_fixes
2. Check mode:
   - normal / replan  →  run the tests, then apply fixes
   - handoff          →  surface to user, ask how to proceed
3. Run each test step, observe results
4. Apply fixes only after tests confirm a hypothesis
5. If the fix doesn't work, call POST /debug again with the
   failed fix added to attempted_fixes
```

Resist the urge to skip tests and go straight to fixes. The whole point of
this tool is to validate hypotheses before changing code — that's what
prevents the thrash loop.

## Example call

```python
import requests

resp = requests.post("http://localhost:8000/debug", json={
    "problem": "TypeError: unsupported operand type(s) for +: 'int' and 'str'",
    "code": "total = count + label",
    "attempted_fixes": ["cast label to int — still fails"]
})
data = resp.json()
print(data["mode"], data.get("response", {}).get("summary"))
```

## Notes

- The backend must be running: `cd backend && uvicorn main:app --reload`
- Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in your environment (configure
  the provider with `SOLVER_PROVIDER=anthropic` or `SOLVER_PROVIDER=openai`)
- The judge score is visible in `judge.score` (0–100); scores ≥70 pass,
  40–69 trigger a replan, <40 trigger a handoff
