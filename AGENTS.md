`apitacerto` is a dashboard showing Brasileirão Série A team performance
broken down by referee (goals, cards, W/D/L, win rate). See
[_docs/specs.md](_docs/specs.md) for the full spec.

This folder is independent from the rest of this repo (the `weekly` app at
repo root) — separate stack, separate deps, separate AGENTS.md.

## Commands

- Frontend: _TBD once `frontend/` exists_
- Backend: _TBD once `backend/` exists_
- Tests: _TBD_

## Rules

- Follow HW2 build order exactly: frontend prototype with mocked backend
  first, then `openapi.yaml`, then FastAPI backend with a mock store and
  tests, then connect frontend↔backend, then swap the mock store for
  SQLAlchemy + SQLite.
- The dashboard reads only from the database. Nothing in the request path
  calls the API-Football API directly — ingestion is a separate script/job.
- `API_FOOTBALL_KEY` comes from the environment only. Never commit it, never
  hardcode it.
- Keep the backend database-agnostic (SQLAlchemy), per HW2 Question 7.
- Do not add dependencies without asking.
