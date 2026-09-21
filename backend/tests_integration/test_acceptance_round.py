"""Cenario de aceitacao 1 (_docs/acceptance.md): uma rodada da CBF entra no
banco e aparece na API.

Fluxo real de ponta a ponta, sem rede externa: payload da CBF (fixture
gravado) -> parse_round -> ingest_matches (o mesmo codigo do scraper) ->
Postgres -> API por HTTP.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.cbf_scraper import parse_round
from app.models import IngestionLog
from scripts.scrape_cbf import ingest_matches

SEASON = 2026
ROUND = 27
PAYLOAD = json.loads(
    (Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "cbf_rodada_sample.json").read_text(
        encoding="utf-8"
    )
)


def _ingest_round(db) -> list[dict]:
    """Mesmo passo a passo do scripts/scrape_cbf.py para uma rodada."""
    matches = parse_round(PAYLOAD, SEASON)
    ingest_matches(db, matches)
    db.add(IngestionLog(
        source="cbf", season=SEASON, round=ROUND,
        finished_at=datetime.now(timezone.utc).isoformat(),
        matches=len(matches), events=sum(len(m["events"]) for m in matches),
    ))
    db.commit()
    return matches


def _cards(match: dict, side: str) -> tuple[int, int]:
    team_id = match[side]["cbf_id"]
    evs = [e for e in match["events"] if e["team_cbf_id"] == team_id]
    return (
        sum(e["type"] == "YELLOW_CARD" for e in evs),
        sum(e["type"] == "RED_CARD" for e in evs),
    )


def test_empty_database_is_healthy_and_has_no_real_season(db_session, api):
    assert api.get("/health").json() == {"status": "ok", "database": "ok"}
    overview = api.get("/season-overview", params={"season": SEASON}).json()
    assert overview["gamesPlayed"] == 0


def test_ingested_round_shows_up_in_the_api(db_session, api):
    matches = _ingest_round(db_session)
    assert len(matches) == 2

    # 1. filtros: os 4 clubes e os 2 arbitros da rodada aparecem
    filters = api.get("/filters").json()
    for m in matches:
        assert m["home_team"]["name"] in filters["teams"]
        assert m["away_team"]["name"] in filters["teams"]
        assert m["referee"]["name"] in filters["referees"]
    assert SEASON in filters["seasons"]

    # 2. dashboard: dado real, nao o mock
    dash = api.get("/dashboard", params={"season": SEASON}).json()
    assert dash["dataCompleteness"]["isReal"] is True
    assert dash["dataCompleteness"]["fixtures"] == 2
    assert dash["dataCompleteness"]["lastUpdated"] is not None

    # 3. cada clube, com o arbitro do seu jogo, tem o placar e os cartoes da CBF
    cells = {(c["team"], c["referee"]): c for c in dash["heatmap"]}
    for m in matches:
        ref = m["referee"]["name"]
        for side, other, gf, ga in (
            ("home_team", "away_team", m["home_score"], m["away_score"]),
            ("away_team", "home_team", m["away_score"], m["home_score"]),
        ):
            cell = cells[(m[side]["name"], ref)]
            yellow, red = _cards(m, side)
            assert cell["n"] == 1
            assert (cell["goalsFor"], cell["goalsAgainst"]) == (gf, ga)
            assert (cell["yellow"], cell["red"]) == (yellow, red)
            assert (cell["wins"], cell["draws"], cell["losses"]) == (
                int(gf > ga), int(gf == ga), int(gf < ga),
            )

    # 4. KPIs da temporada: 2 jogos = 4 "jogos-time"
    assert dash["kpis"]["games"] == 4
    overview = api.get("/season-overview", params={"season": SEASON}).json()
    assert overview["gamesPlayed"] == 2
    total_goals = sum(m["home_score"] + m["away_score"] for m in matches)
    assert overview["goalsPerGame"] == round(total_goals / 2, 2)

    # 5. filtro por clube: so o jogo daquele clube
    home = matches[0]["home_team"]["name"]
    one = api.get("/dashboard", params={"season": SEASON, "team": home}).json()
    assert one["kpis"]["games"] == 1
    assert one["kpis"]["goalsFor"] == matches[0]["home_score"]


def test_reingesting_the_same_round_does_not_duplicate(db_session, api):
    # o cron semanal reprocessa a temporada atual: rodar de novo nao pode dobrar
    _ingest_round(db_session)
    first = api.get("/dashboard", params={"season": SEASON}).json()
    _ingest_round(db_session)
    second = api.get("/dashboard", params={"season": SEASON}).json()
    assert second["kpis"] == first["kpis"]
    assert second["heatmap"] == first["heatmap"]
