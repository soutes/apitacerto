# ApitaCerto

Dashboard interativo do desempenho de times do Brasileirão Série A,
segmentado por árbitro — gols, cartões, V/E/D, aproveitamento %. Sem Power
BI, sem Looker: frontend próprio (React) consumindo um backend próprio
(FastAPI), dados persistidos em banco (SQLite via SQLAlchemy) alimentados
pela API-Football.

Feito para o [HW2 do AI Dev Tools Zoomcamp](https://courses.datatalks.club/ai-dev-tools-2026/homework/hw2)
— opção "Sports-league scoreboard".

Ver spec completa em [`_docs/specs.md`](_docs/specs.md).

## Estrutura

- `frontend/` — React + Vite + Recharts
- `backend/` — FastAPI + uv + SQLAlchemy + SQLite
- `openapi.yaml` — contrato entre frontend e backend

## Rodando

- Frontend: `npm --prefix frontend run dev` (ou `cd frontend && npm run dev`) — http://localhost:5173
- Backend: `cd backend && uv run uvicorn app.main:app --port 8000` — http://localhost:8000
- Testes: `cd backend && uv run pytest`

Frontend fala com o backend em `http://localhost:8000` (configurável via
`VITE_BACKEND_URL`, ver `frontend/src/api.js`).

Dados: SQLAlchemy + SQLite (Fase 5), populado por
`cd backend && uv run python scripts/ingest.py --max-requests 90`. Respeita
o limite de 100 req/dia (e um limite por minuto do free tier) da
API-Football — rodar 1x/dia até completar as 3 temporadas (2022-2024).
Temporada/time/árbitro sem dado real ainda ingerido cai automaticamente no
mock determinístico (não quebra o dashboard enquanto a ingestão progride).
