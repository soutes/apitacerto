# Cenários de aceitação

Cada cenário descreve um fluxo que precisa funcionar de ponta a ponta:
código de ingestão real, Postgres real e a API real respondendo por HTTP.
Os testes ficam em `backend/tests_integration/`.

## Cenário 1 — uma rodada da CBF entra no banco e aparece na API

**Dado** um banco Postgres vazio e a API no ar,
**quando** a rodada 27 de 2026 da CBF (payload gravado em
`backend/tests/fixtures/cbf_rodada_sample.json`, 2 jogos) passa pelo mesmo
código do scraper (`parse_round` → `ingest_matches`),
**então**:

1. `GET /health` responde `{"status": "ok", "database": "ok"}`;
2. `GET /filters` lista os 4 clubes, os 2 árbitros e a temporada 2026;
3. `GET /dashboard?season=2026` vem com dado real (`isReal: true`, 2 jogos,
   data da última atualização preenchida);
4. cada par clube × árbitro traz exatamente o placar, o resultado
   (V/E/D) e os cartões que a CBF publicou;
5. os KPIs da temporada somam 2 jogos (4 "jogos-time") e o
   `GET /season-overview` mostra gols por jogo corretos;
6. filtrar por um clube mostra só o jogo daquele clube;
7. ingerir a mesma rodada de novo não duplica nada (o cron semanal
   reprocessa a temporada atual).

Teste: `backend/tests_integration/test_acceptance_round.py`.

### Como rodar

```bash
docker run -d --name apitacerto-pg-test -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=apitacerto_test -p 5433:5432 postgres:17
```

```bash
cd backend
INTEGRATION_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/apitacerto_test uv run pytest tests_integration -v
```

O teste sobe a própria API (uvicorn) apontando para esse banco. Para testar
uma API que já está no ar (Docker Compose, Kubernetes), defina também
`APITACERTO_API_URL`. O banco é apagado a cada teste, por isso só é aceito
banco com "test" no nome. Sem `INTEGRATION_DATABASE_URL`, esses testes são
pulados e `uv run pytest` roda como antes.
