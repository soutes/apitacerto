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

## Rodando (preencher conforme cada fase é implementada)

- Frontend: _TBD_
- Backend: _TBD_
- Testes: _TBD_
