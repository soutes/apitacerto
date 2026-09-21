# Homework 3 — Test, Containerize and Deploy

AI Dev Tools Zoomcamp 2026, module 3. Applied to **ApitaCerto** (FastAPI +
React + Postgres) instead of the Agent Relay starter. Zero cost: everything
local (Docker, kind, act) or on free tiers (GitHub Actions, GHCR, Oracle
Cloud Always Free).

- **Live:** https://147-15-76-139.sslip.io
- **Main PR:** [#1 Homework 3](https://github.com/soutes/apitacerto/pull/1)
  · production: [#2](https://github.com/soutes/apitacerto/pull/2)

## Where each question lives in this repo

| Question | Implementation |
|---|---|
| 1. Architecture | Browser → HTTP API (FastAPI) → database; ingestion runs offline and never inside a request. Diagram in the [README](../README.md#arquitetura). `GET /health` checks the API and the database. |
| 2. Acceptance scenario + API integration test | [`acceptance.md`](acceptance.md): a real CBF round goes through the scraper code into real Postgres and is served over HTTP. Test: `backend/tests_integration/`. |
| 3. Docker (`-p`) | Multi-stage [`Dockerfile`](../Dockerfile), `docker run -p 8000:8000 apitacerto:local`. 302 MB, non-root, `HEALTHCHECK`. |
| 4. Compose + Postgres (`postgres` hostname) | [`compose.yaml`](../compose.yaml): the app reaches the database at `postgres:5432`. Offline seed with 3,420 matches. Integration tests: `docker compose --profile test run --rm --build test`. |
| 5. Kubernetes (Deployment) | [`k8s/`](../k8s): Postgres with a PVC, seed Job, API Deployment with 2 replicas and readiness on `/health`. |
| 6. CI/CD (stop on failure) | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml): `test` → `deploy` to kind only if `test` passed (`needs: test`), unique image tag. On `main`, `publish` pushes to GHCR for production. |

## Evidence

### CI/CD with act: new version deployed ("ApitaCerto v2")

```
[ci/test]   | 53 passed, 3 skipped, 2 warnings in 30.37s
[ci/test]   ✅  Success - Main Testes unitarios (backend)
[ci/test]   ✅  Success - Main Lint e build (frontend)
[ci/test]   | ============================== 3 passed in 1.79s ===============================
[ci/test]   ✅  Success - Main Testes de integracao (Postgres real, via Docker Compose)
[ci/test] 🏁  Job succeeded
[ci/deploy]   ✅  Success - Main Monta a imagem
[ci/deploy]   | deployment "apitacerto" successfully rolled out
[ci/deploy]   ✅  Success - Main Deploy
[ci/deploy]   | apitacerto:36f6750-20260921173739
[ci/deploy]   | {"status":"ok","database":"ok"}<title>ApitaCerto v2</title>
[ci/deploy] 🏁  Job succeeded
```

### CI/CD with act: test broken on purpose → deploy never starts

```
[ci/test]   | FAILED tests/test_health.py::test_health_ok_when_database_answers
[ci/test]   | 1 failed, 52 passed, 3 skipped, 2 warnings in 25.16s
[ci/test]   ❌  Failure - Main Testes unitarios (backend)
[ci/test] 🏁  Job failed
```

No `ci/deploy` line at all. The image in the cluster before and after:

```
antes:  apitacerto:36f6750-20260921173739
depois: apitacerto:36f6750-20260921173739
```

The existing version kept running.

### GitHub Actions (hosted runners)

- [main, after PR #2: test, deploy, publish](https://github.com/soutes/apitacerto/actions/runs/35660397626)
- [main, after PR #1: test, deploy](https://github.com/soutes/apitacerto/actions/runs/35640149498)
- [first hosted run failed in deploy](https://github.com/soutes/apitacerto/actions/runs/35637892936).
  The job is not root on GitHub (it is on act), so installing kind into
  `/usr/local/bin` failed. Fixed in `1b3ab7b`.

### Kubernetes (kind)

- The seed Job loaded 3,420 matches, and both API replicas became ready
  with 0 restarts.
- A deleted API pod was recreated by the Deployment.
- Deleting the Postgres pod kept the data on the PVC (3,420 matches).
- On a fresh namespace, the API waited for the seed ("aguardando carga")
  and became ready 5 s after the Job completed. This was review feedback
  on PR #1.

## What running on Postgres and Linux caught

- `/filters` returned the same names in a different order on SQLite (byte
  order) and Postgres (locale). The API now sorts them itself.
- The CBF server sends the wrong intermediate certificate. Windows repairs
  the chain on its own and Linux does not. The public Sectigo intermediate
  now ships with the scraper.
- The CBF API returned a 502 in the middle of a run. The scraper now retries
  server errors.
