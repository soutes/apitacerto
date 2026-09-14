# ApitaCerto

Dashboard interativo do desempenho de times do Brasileirão Série A,
segmentado por árbitro — gols, cartões, V/E/D, aproveitamento %, e um
Índice de Favorecimento pra sinalizar possível viés de arbitragem. Sem
Power BI, sem Looker: frontend próprio (React) consumindo um backend
próprio (FastAPI), dados persistidos em banco (SQLite via SQLAlchemy).

Feito para o [HW2 do AI Dev Tools Zoomcamp](https://courses.datatalks.club/ai-dev-tools-2026/homework/hw2)
— opção "Sports-league scoreboard".

Ver spec completa em [`_docs/specs.md`](_docs/specs.md).

## Estrutura

- `frontend/` — React + Vite + Recharts, 4 abas (Visão Geral, Índice de
  Favorecimento, Tabela Geral, Classificação)
- `backend/` — FastAPI + uv + SQLAlchemy + SQLite
- `openapi.yaml` — contrato entre frontend e backend

## Rodando

- Frontend: `npm --prefix frontend run dev` (ou `cd frontend && npm run dev`) — http://localhost:5173
- Backend: `cd backend && uv run uvicorn app.main:app --port 8000` — http://localhost:8000
- Testes: `cd backend && uv run pytest`

Frontend fala com o backend em `http://localhost:8000` (configurável via
`VITE_BACKEND_URL`, ver `frontend/src/api.js`).

## Dados

Cobertura: 2022-2026 (2026 é a temporada em andamento). Fonte primária:
scraping da API JSON pública da CBF (sem limite diário — ver
`_docs/specs.md` seção 3):

```bash
cd backend
uv run python scripts/scrape_cbf.py --season 2022 --season 2023 --season 2024 --season 2025 --season 2026
```

Leva poucos minutos pras 5 temporadas. Idempotente — roda de novo sem medo,
só atualiza o que mudou. **Cron semanal** (`apitacerto-cbf-refresh`, scheduled
task do Claude Code, toda terça 23:59 horário do Brasil) reprocessa só o
ano atual automaticamente —
só dispara com o app aberto; ver seção 3.1 do spec pra alternativa real
(GitHub Actions / Task Scheduler) quando isso for pra produção.

`GET /dashboard` retorna `dataCompleteness.lastUpdated` (data/hora da
última rodada processada) — o dashboard mostra isso no banner do topo.

Fonte secundária (fallback, caso a API da CBF pare de funcionar):
API-Football, `uv run python scripts/ingest.py --max-requests 90` — precisa
de `API_FOOTBALL_KEY` no `.env` e é bem mais lenta (limite de request/dia).

Temporada/time/árbitro sem dado real ainda ingerido cai automaticamente no
mock determinístico (não quebra o dashboard enquanto a ingestão progride).
