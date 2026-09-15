`apitacerto` is a dashboard showing Brasileirão Série A team performance
broken down by referee (goals, cards, W/D/L, win rate, favoritism index).
See [_docs/specs.md](_docs/specs.md) for the full spec.

This folder is independent from the rest of this repo (the `weekly` app at
repo root) — separate stack, separate deps, separate AGENTS.md.

## Commands

- Frontend: `cd frontend && npm run dev` — http://localhost:5173
- Backend: `cd backend && uv run uvicorn app.main:app --port 8000` — http://localhost:8000
- Tests: `cd backend && uv run pytest`
- Ingest (primary, CBF scraper, no daily limit): `cd backend && uv run python scripts/scrape_cbf.py --season 2018 --season 2019 --season 2020 --season 2021 --season 2022 --season 2023 --season 2024 --season 2025 --season 2026`
- Ingest (fallback, API-Football, rate-limited): `cd backend && uv run python scripts/ingest.py --max-requests 90`

## Rules

- The dashboard reads only from the database. Nothing in the request path
  scrapes/calls an external source directly — ingestion is a separate
  script/job (`scripts/scrape_cbf.py`, `scripts/ingest.py`).
- Match a Team by **name**, not by the source's numeric id — the CBF
  assigns different ids/names to the same club across seasons (SAF
  conversion, truncated names some years). See `TEAM_NAME_ALIASES` in
  `app/cbf_scraper.py` before assuming a "new" club is real.
- `API_FOOTBALL_KEY` comes from the environment only. Never commit it, never
  hardcode it.
- Keep the backend database-agnostic (SQLAlchemy), per HW2 Question 7.
  Deploy target is Vercel (Python functions) + Neon (Postgres).
- Dependencies are fine as long as they run on that target. Heavy analysis
  libraries (numpy/scipy/pandas/statsmodels) live in the `analysis`
  dependency group and are imported only by offline scripts
  (`scripts/compute_stats.py`), never by the request path — the API only
  reads precomputed JSON from `stat_reports`, keeping the serverless bundle
  small.
