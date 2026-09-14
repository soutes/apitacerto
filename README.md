# ApitaCerto

*English below.*

Dashboard interativo do desempenho de times do Brasileirão Série A,
segmentado por árbitro — gols, cartões, V/E/D, aproveitamento %, saldo de
gols, classificação, e um **Índice de Favorecimento** pra sinalizar
possível viés de arbitragem. Sem Power BI, sem Looker: frontend próprio
(React) consumindo um backend próprio (FastAPI), dados persistidos em banco
(SQLite via SQLAlchemy).

Feito para o [HW2 do AI Dev Tools Zoomcamp](https://courses.datatalks.club/ai-dev-tools-2026/homework/hw2)
— opção "Sports-league scoreboard".

Ver spec completa em [`_docs/specs.md`](_docs/specs.md).

## As 4 abas

1. **Visão Geral** — escolha um time e/ou árbitro e veja KPIs (jogos, V/E/D,
   aproveitamento, gols, cartões) e séries temporais desse recorte. Sem
   filtro, não mostra nada (evita somar a liga toda em dobro).
2. **Índice de Favorecimento** — heatmap time × árbitro. Slicer de
   temporada próprio, com opção "Todos" (junta as temporadas pra ganhar
   amostra nos pares com poucos jogos numa temporada só). Vermelho =
   possível favorecimento, azul = possível prejuízo, cinza = amostra
   insuficiente (menos de 5 jogos do par). Clique numa célula pra ver o
   detalhe na Visão Geral.
3. **Tabela Geral** — mesmo heatmap, com seletor de indicador (jogos,
   cartões, V/E/D, aproveitamento, saldo de gols) e gradiente de cor.
4. **Classificação** — tabela de pontos oficial (vitória×3 + empate×1),
   com filtro de árbitro pra ver como cada clube se saiu especificamente
   sob aquele árbitro.

Metodologia do Índice de Favorecimento (fórmula, piso de amostra, limitações
— não é prova de manipulação, é sinalização exploratória) está em
[`_docs/specs.md`](_docs/specs.md) seção 6.

## Estrutura

- `frontend/` — React + Vite + Recharts
- `backend/` — FastAPI + uv + SQLAlchemy + SQLite
- `openapi.yaml` — contrato entre frontend e backend

## Rodando

- Frontend: `cd frontend && npm run dev` — http://localhost:5173
- Backend: `cd backend && uv run uvicorn app.main:app --port 8000` — http://localhost:8000
- Testes: `cd backend && uv run pytest` (21 passando)

Frontend fala com o backend em `http://localhost:8000` (configurável via
`VITE_BACKEND_URL`, ver `frontend/src/api.js`).

## Dados

Cobertura: 2022-2026 (2026 é a temporada em andamento, atualizada rodada a
rodada). Fonte primária: scraping da API JSON pública da CBF (sem limite
diário — ver `_docs/specs.md` seção 3):

```bash
cd backend
uv run python scripts/scrape_cbf.py --season 2022 --season 2023 --season 2024 --season 2025 --season 2026
```

Leva poucos minutos pras 5 temporadas. Idempotente — roda de novo sem medo,
só atualiza o que mudou.

**Cron semanal**: scheduled task do Claude Code (`apitacerto-cbf-refresh`,
toda terça 23:59 horário do Brasil) reprocessa só o ano atual
automaticamente (temporada fechada não muda mais, não vale reprocessar).
Só dispara com o app aberto — ver seção 3.1 do spec pra alternativa real
(GitHub Actions / Task Scheduler) quando isso for pra produção.

`GET /dashboard` retorna `dataCompleteness.lastUpdated` (data/hora da
última rodada processada) — o dashboard mostra isso no banner do topo.

Fonte secundária (fallback, caso a API da CBF pare de funcionar):
API-Football, `uv run python scripts/ingest.py --max-requests 90` — precisa
de `API_FOOTBALL_KEY` no `.env` e é bem mais lenta (limite de request/dia).

Temporada/time/árbitro sem dado real ainda ingerido cai automaticamente no
mock determinístico (não quebra o dashboard enquanto a ingestão progride).

---

# ApitaCerto (English)

Interactive dashboard of Brasileirão Série A team performance, broken down
by referee — goals, cards, W/D/L, win rate, goal difference, standings, and
a **Favoritism Index** to flag possible referee bias. No Power BI, no
Looker: a custom React frontend talking to a custom FastAPI backend, data
persisted in a database (SQLite via SQLAlchemy).

Built for [HW2 of the AI Dev Tools Zoomcamp](https://courses.datatalks.club/ai-dev-tools-2026/homework/hw2)
— "Sports-league scoreboard" option.

Full spec in [`_docs/specs.md`](_docs/specs.md) (Portuguese).

## The 4 tabs

1. **Overview** — pick a team and/or referee to see KPIs (games, W/D/L,
   win rate, goals, cards) and time series for that slice. With no filter,
   it shows nothing (avoids double-counting the whole league).
2. **Favoritism Index** — team × referee heatmap. Has its own season
   picker, including an "All" option (pools every season to get enough
   sample size for pairs that only played a handful of games in a single
   year). Red = possible favoritism, blue = possible disadvantage, gray =
   insufficient sample (fewer than 5 games for that pair). Click a cell to
   jump to the Overview tab with that detail.
3. **Full Table** — same heatmap, with a metric picker (games, cards,
   W/D/L, win rate, goal difference) and a color gradient.
4. **Standings** — official points table (win×3 + draw×1), with a referee
   filter to see how each club fared specifically under that referee.

The Favoritism Index methodology (formula, minimum-sample floor,
limitations — this is an exploratory signal, not proof of manipulation) is
documented in [`_docs/specs.md`](_docs/specs.md) section 6 (Portuguese).

## Structure

- `frontend/` — React + Vite + Recharts
- `backend/` — FastAPI + uv + SQLAlchemy + SQLite
- `openapi.yaml` — contract between frontend and backend

## Running it

- Frontend: `cd frontend && npm run dev` — http://localhost:5173
- Backend: `cd backend && uv run uvicorn app.main:app --port 8000` — http://localhost:8000
- Tests: `cd backend && uv run pytest` (21 passing)

The frontend talks to the backend at `http://localhost:8000` (configurable
via `VITE_BACKEND_URL`, see `frontend/src/api.js`).

## Data

Coverage: 2022-2026 (2026 is the current season, updated round by round).
Primary source: scraping the CBF's public JSON API (no daily rate limit —
see `_docs/specs.md` section 3, Portuguese):

```bash
cd backend
uv run python scripts/scrape_cbf.py --season 2022 --season 2023 --season 2024 --season 2025 --season 2026
```

Takes a few minutes for all 5 seasons. Idempotent — safe to re-run, it only
updates what changed.

**Weekly cron**: a Claude Code scheduled task (`apitacerto-cbf-refresh`,
every Tuesday 23:59 Brazil time) re-scrapes only the current year
automatically (a closed season never changes again, so re-scraping it would
be wasted work). It only fires while the app is open — see spec section 3.1
for the real alternative (GitHub Actions / Task Scheduler) for a deployed
setup.

`GET /dashboard` returns `dataCompleteness.lastUpdated` (timestamp of the
last round processed) — the dashboard shows this in the top banner.

Secondary source (fallback, in case the CBF endpoint stops working):
API-Football, `uv run python scripts/ingest.py --max-requests 90` — needs
`API_FOOTBALL_KEY` in `.env` and is much slower (daily request limit).

A season/team/referee with no real data ingested yet automatically falls
back to deterministic mock data (the dashboard never breaks while ingestion
is in progress).
