# ApitaCerto

*English below.*

Dashboard interativo do Brasileirão Série A segmentado por árbitro — gols,
cartões, V/E/D, classificação — com uma aba de **Favorecimento** que
testa, com o método explicado embaixo de cada gráfico, se algum árbitro
favorece ou persegue algum clube. Sem Power BI, sem Looker: frontend próprio
(React) consumindo um backend próprio (FastAPI), dados persistidos em banco
(SQLAlchemy — SQLite local, Postgres/Neon em produção).

Feito para o [HW2 do AI Dev Tools Zoomcamp](https://courses.datatalks.club/ai-dev-tools-2026/homework/hw2)
— opção "Sports-league scoreboard".

Ver spec completa em [`_docs/specs.md`](_docs/specs.md).

## Telas

- **Dashboard** — visão da temporada: KPIs, prévia da classificação,
  árbitros que mais punem.
- **Classificação** — tabela oficial (vitória×3 + empate×1).
- **Árbitros** — ranking por rigor (cartões/jogo) e viés de mandante.
- **Clubes** — matriz clube × árbitro com seletor de indicador.
- **Favorecimento** — observado vs. esperado com teste estatístico, ver
  abaixo. Substituiu em 21/09/2026 o antigo Índice de Favorecimento (spec
  seção 6), retirado porque o diagnóstico de 14/09/2026 mostrou que ele não
  se distingue do acaso.

Clicar numa célula da matriz de Clubes abre o detalhe do par (KPIs e séries).

## Favorecimento — como funciona

Tudo compara **observado com esperado**. O esperado de cada jogo considera
mando, força e estilo de cada clube na temporada, adversário e rigor do
árbitro (regressão de Poisson). Embaixo de cada gráfico, a tela explica como
o dado foi construído, o método, quem criou e como ler.

- **Árbitro × clube** — cartões ao clube ("implicância"), cartões ao
  adversário, pontos acima do esperado e escala favorável ("o mesmo árbitro
  nos jogos mais fáceis"). O esperado de cada par é calculado *sem os jogos
  do próprio par* (jackknife), com teste exato (Poisson / binomial negativa;
  distribuição exata da soma de pontos), correção de múltiplas comparações
  (Benjamini-Hochberg) e gráfico de funil (Spiegelhalter).
- **Repetição entre temporadas** — o mesmo árbitro favorece o mesmo clube em
  anos diferentes?
- **Escala da CBF** — regra de federação, árbitro FIFA × tamanho do jogo e
  concentração árbitro × clube contra sorteios que respeitam as regras.
- **Hipóteses pré-registradas** (H1–H4), fixadas em commit público antes do
  código de análise existir ([`85e9b06`](https://github.com/soutes/apitacerto/commit/85e9b06)).

**Calibração**: em ligas simuladas *sem* nenhum favorecimento, o "sinal
forte" falso fica no nível que a régua promete (≤ ~10% das ligas), inclusive
em começo de temporada — `backend/scripts/calibrate_stats.py`. Efeitos
plantados de propósito são achados — `backend/tests/test_analysis.py`.

**Achados em 15/09/2026** (2018–2026, 3.305 jogos): nenhum par árbitro ×
clube com sinal forte; nenhum árbitro mais duro com o mesmo clube em mais de
uma temporada; a vantagem do mandante em cartões quase some em 2020, jogado
sem público (H2 apoiada, p = 0,018); a escala da CBF concentra alguns pares
além do que as regras explicam — pergunta sobre a escala, não prova sobre o
árbitro.

## Arquitetura

```
navegador ──HTTP──> FastAPI (backend/app) ──SQLAlchemy──> Postgres / SQLite
  React                  │  só lê o banco                     ▲
  (frontend/)            └─ GET /health: API + banco ok?       │
                                                               │
             scripts offline (scrape_cbf.py, compute_stats.py) ┘
             buscam a CBF e gravam no banco; nunca rodam dentro de um request
```

- O navegador só mostra: pede dados à API por HTTP e desenha os gráficos.
- A API só lê do banco. Nada no caminho do request chama a CBF.
- A ingestão (scraping + estatística pesada) é um passo separado, que grava
  no banco o que a API depois lê pronto.
- `GET /health` responde `200 {"status": "ok", "database": "ok"}` quando a
  API e o banco estão de pé, e `503` quando o banco não responde. É a
  readiness do Kubernetes e o smoke test do CI.

## Estrutura

- `frontend/` — React + Vite + Recharts
- `backend/` — FastAPI + uv + SQLAlchemy (SQLite local; Postgres/Neon via
  `DATABASE_URL=postgresql+psycopg://...`)
  - `app/analysis/` — cálculo estatístico **offline** (numpy, scipy, pandas,
    statsmodels). A API só lê o resultado pronto (tabela `stat_reports`), pra
    função serverless da Vercel ficar leve.
- `openapi.yaml` — contrato entre frontend e backend

## Rodando

- Frontend: `cd frontend && npm run dev` — http://localhost:5173
- Backend: `cd backend && uv run uvicorn app.main:app --port 8000` — http://localhost:8000
- Testes: `cd backend && uv run pytest` (48 passando)
- Testes de integração (Postgres real + API real por HTTP): ver
  [`_docs/acceptance.md`](_docs/acceptance.md)
- Estatísticas: `cd backend && uv run python scripts/compute_stats.py`
  (também roda sozinho ao fim do scraping)
- Calibração: `cd backend && uv run python scripts/calibrate_stats.py`

Frontend fala com o backend em `http://localhost:8000` (configurável via
`VITE_BACKEND_URL`, ver `frontend/src/api.js`).

### Com Docker

Uma imagem só: o Node monta o front, e a API (FastAPI) serve o front e os
dados na mesma porta.

```bash
docker build -t apitacerto:local .
docker run --rm -p 8000:8000 apitacerto:local
```

Abre em http://localhost:8000. Sem `DATABASE_URL`, o container usa um SQLite
vazio e mostra o mock. Para apontar para um Postgres:
`-e DATABASE_URL=postgresql+psycopg://usuario:senha@host:5432/banco`.
`-p 8000:8000` publica a porta 8000 do container na sua máquina. A imagem
roda sem root, sem Node, sem uv e sem numpy/scipy, e tem `HEALTHCHECK`
em `/health`.

## Dados

Cobertura: 2018–2026 (2026 é a temporada em andamento). Fonte primária:
scraping da API JSON pública da CBF (sem limite diário — ver
`_docs/specs.md` seção 3):

```bash
cd backend
uv run python scripts/scrape_cbf.py --season 2018 --season 2019 --season 2020 --season 2021 --season 2022 --season 2023 --season 2024 --season 2025 --season 2026
```

Grava placar, árbitro (com federação e categoria), VAR, gols e cartões com o
tempo de jogo (1º/2º tempo, acréscimos, intervalo, pós-jogo). Idempotente —
roda de novo sem medo. Limitação da fonte: em 2018 a CBF só publicou a escala
de árbitro das rodadas 33–38.

**Cron semanal**: scheduled task do Claude Code (`apitacerto-cbf-refresh`,
toda terça 23:59 horário do Brasil) reprocessa só o ano atual
automaticamente (temporada fechada não muda mais, não vale reprocessar).
Só dispara com o app aberto — ver seção 3.1 do spec pra alternativa real
(GitHub Actions / Task Scheduler) quando isso for pra produção.

`GET /dashboard` retorna `dataCompleteness.lastUpdated` (data/hora da
última rodada processada) — o dashboard mostra isso no rodapé.

Fonte secundária (fallback, caso a API da CBF pare de funcionar):
API-Football, `uv run python scripts/ingest.py --max-requests 90` — precisa
de `API_FOOTBALL_KEY` no `.env` e é bem mais lenta (limite de request/dia).

Temporada/time/árbitro sem dado real ainda ingerido cai automaticamente no
mock determinístico (não quebra o dashboard enquanto a ingestão progride).

---

# ApitaCerto (English)

Interactive dashboard of Brasileirão Série A broken down by referee — goals,
cards, W/D/L, standings — with a **Favoritism** tab that tests, with the
method explained under every chart, whether any referee favors or targets any
club. No Power BI, no Looker: a custom React frontend talking to a custom
FastAPI backend, data persisted in a database (SQLAlchemy — SQLite locally,
Postgres/Neon in production).

Built for [HW2 of the AI Dev Tools Zoomcamp](https://courses.datatalks.club/ai-dev-tools-2026/homework/hw2)
— "Sports-league scoreboard" option.

Full spec in [`_docs/specs.md`](_docs/specs.md) (Portuguese).

## Screens

- **Dashboard** — season overview: KPIs, standings preview, strictest
  referees.
- **Standings** — official table (win×3 + draw×1).
- **Referees** — ranking by strictness (cards/game) and home bias.
- **Clubs** — club × referee matrix with a metric picker.
- **Favoritism** — observed vs. expected with statistical tests, see below.
  On 2026-09-21 it replaced the old Favoritism Index (spec section 6),
  removed because the 2026-09-14 diagnosis showed it is indistinguishable
  from chance.

Clicking a cell in the Clubs matrix opens the pair detail (KPIs and time series).

## Favoritism — how it works

Everything compares **observed with expected**. Each match's expected value
accounts for home advantage, each club's strength and style that season, the
opponent and the referee's strictness (Poisson regression). Under every
chart, the screen explains how the data was built, the method, who created it
and how to read it.

- **Referee × club** — cards to the club ("targeting"), cards to the
  opponent, points above expectation and favorable assignment ("the same
  referee in the easiest games"). Each pair's expectation is computed
  *without that pair's own games* (jackknife), with exact tests (Poisson /
  negative binomial; exact distribution of summed points), multiple-testing
  correction (Benjamini-Hochberg) and a funnel plot (Spiegelhalter).
- **Repetition across seasons** — does the same referee favor the same club
  in different years?
- **CBF assignment** — home-federation rule, FIFA referees × match size, and
  referee × club concentration against draws that respect the real rules.
- **Pre-registered hypotheses** (H1–H4), fixed in a public commit before any
  analysis code existed ([`85e9b06`](https://github.com/soutes/apitacerto/commit/85e9b06)).

**Calibration**: on simulated leagues with *no* favoritism at all, false
"strong signals" stay at the level the rule promises (≤ ~10% of leagues),
early season included — `backend/scripts/calibrate_stats.py`. Deliberately
planted effects are found — `backend/tests/test_analysis.py`.

**Findings as of 2026-09-15** (2018–2026, 3,305 matches): no referee × club
pair with a strong signal; no referee harsher on the same club in more than
one season; home teams' card advantage nearly vanished in 2020, played
behind closed doors (H2 supported, p = 0.018); CBF's assignment concentrates
some pairs beyond what the rules explain — a question about assignment, not
proof about the referee.

## Architecture

```
browser ──HTTP──> FastAPI (backend/app) ──SQLAlchemy──> Postgres / SQLite
  React                │  read-only on the database         ▲
  (frontend/)          └─ GET /health: API + database up?    │
                                                             │
           offline scripts (scrape_cbf.py, compute_stats.py) ┘
           fetch from the CBF and write to the database; never inside a request
```

- The browser only displays: it asks the API for data over HTTP and draws
  the charts.
- The API only reads from the database. Nothing in the request path calls
  the CBF.
- Ingestion (scraping + heavy statistics) is a separate step that writes to
  the database what the API later reads ready-made.
- `GET /health` returns `200 {"status": "ok", "database": "ok"}` when the
  API and the database are up, and `503` when the database does not answer.
  It is the Kubernetes readiness check and the CI smoke test.

## Structure

- `frontend/` — React + Vite + Recharts
- `backend/` — FastAPI + uv + SQLAlchemy (SQLite locally; Postgres/Neon via
  `DATABASE_URL=postgresql+psycopg://...`)
  - `app/analysis/` — **offline** statistics (numpy, scipy, pandas,
    statsmodels). The API only reads the precomputed result (`stat_reports`
    table), keeping the Vercel serverless function small.
- `openapi.yaml` — contract between frontend and backend

## Running it

- Frontend: `cd frontend && npm run dev` — http://localhost:5173
- Backend: `cd backend && uv run uvicorn app.main:app --port 8000` — http://localhost:8000
- Tests: `cd backend && uv run pytest` (48 passing)
- Integration tests (real Postgres + real API over HTTP): see
  [`_docs/acceptance.md`](_docs/acceptance.md) (Portuguese)
- Statistics: `cd backend && uv run python scripts/compute_stats.py`
  (also runs automatically at the end of scraping)
- Calibration: `cd backend && uv run python scripts/calibrate_stats.py`

The frontend talks to the backend at `http://localhost:8000` (configurable
via `VITE_BACKEND_URL`, see `frontend/src/api.js`).

### With Docker

One image: Node builds the frontend, and the API (FastAPI) serves both the
frontend and the data on the same port.

```bash
docker build -t apitacerto:local .
docker run --rm -p 8000:8000 apitacerto:local
```

Open http://localhost:8000. Without `DATABASE_URL` the container uses an
empty SQLite and shows mock data. To point it at Postgres:
`-e DATABASE_URL=postgresql+psycopg://user:password@host:5432/db`.
`-p 8000:8000` publishes the container's port 8000 on your machine. The
image runs as non-root, without Node, uv or numpy/scipy, and has a
`HEALTHCHECK` on `/health`.

## Data

Coverage: 2018–2026 (2026 is the current season). Primary source: scraping
the CBF's public JSON API (no daily rate limit — see `_docs/specs.md`
section 3, Portuguese):

```bash
cd backend
uv run python scripts/scrape_cbf.py --season 2018 --season 2019 --season 2020 --season 2021 --season 2022 --season 2023 --season 2024 --season 2025 --season 2026
```

Stores score, referee (with federation and category), VAR, goals and cards
with the match period (1st/2nd half, stoppage time, half-time, post-match).
Idempotent — safe to re-run. Source limitation: for 2018 the CBF only
published the referee assignment for rounds 33–38.

**Weekly cron**: a Claude Code scheduled task (`apitacerto-cbf-refresh`,
every Tuesday 23:59 Brazil time) re-scrapes only the current year
automatically (a closed season never changes again, so re-scraping it would
be wasted work). It only fires while the app is open — see spec section 3.1
for the real alternative (GitHub Actions / Task Scheduler) for a deployed
setup.

`GET /dashboard` returns `dataCompleteness.lastUpdated` (timestamp of the
last round processed) — the dashboard shows it in the footer.

Secondary source (fallback, in case the CBF endpoint stops working):
API-Football, `uv run python scripts/ingest.py --max-requests 90` — needs
`API_FOOTBALL_KEY` in `.env` and is much slower (daily request limit).

A season/team/referee with no real data ingested yet automatically falls
back to deterministic mock data (the dashboard never breaks while ingestion
is in progress).
