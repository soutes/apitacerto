"""Testa app/queries.py (Fase 5: dado real via SQLAlchemy) fim a fim pela
API, sem tocar rede -- semeia o banco de teste (conftest.py) direto com os
models. Cenario desenhado pra sinalizar favorecimento de verdade: Time A
ganha tudo e nao toma cartao sob o Arbitro X, mas e parelho e toma cartao
normal sob o Arbitro Y.
"""
from fastapi.testclient import TestClient

from app.main import app
from app.models import Fixture, MatchEvent, Referee, Team

client = TestClient(app)

SEASON = 2023


def _seed_favoritism_scenario(db_session):
    team_a = Team(api_id=1, name="Time A")
    team_b = Team(api_id=2, name="Time B")
    ref_x = Referee(name="Arbitro X")
    ref_y = Referee(name="Arbitro Y")
    db_session.add_all([team_a, team_b, ref_x, ref_y])
    db_session.flush()

    fixture_api_id = 1000

    # 6 jogos sob o Arbitro X: Time A ganha todos, 0 cartao pra A, 3 pra B
    for i in range(6):
        fixture_api_id += 1
        fx = Fixture(
            api_id=fixture_api_id, season=SEASON, round=f"Regular Season - {i + 1}",
            date="2023-04-15", home_team_id=team_a.id, away_team_id=team_b.id,
            referee_id=ref_x.id, home_score=2, away_score=0, events_ingested=True,
        )
        db_session.add(fx)
        db_session.flush()
        for _ in range(3):
            db_session.add(MatchEvent(fixture_id=fx.id, team_id=team_b.id, type="YELLOW_CARD"))

    # 6 jogos sob o Arbitro Y: 3 vitorias de A, 3 de B, cartoes parelhos
    for i in range(6):
        fixture_api_id += 1
        a_wins = i % 2 == 0
        fx = Fixture(
            api_id=fixture_api_id, season=SEASON, round=f"Regular Season - {i + 7}",
            date="2023-05-15", home_team_id=team_a.id, away_team_id=team_b.id,
            referee_id=ref_y.id,
            home_score=2 if a_wins else 0, away_score=0 if a_wins else 2,
            events_ingested=True,
        )
        db_session.add(fx)
        db_session.flush()
        db_session.add(MatchEvent(fixture_id=fx.id, team_id=team_a.id, type="YELLOW_CARD"))
        db_session.add(MatchEvent(fixture_id=fx.id, team_id=team_b.id, type="YELLOW_CARD"))

    db_session.commit()


def test_dashboard_uses_real_data_once_ingested(db_session):
    _seed_favoritism_scenario(db_session)

    res = client.get("/dashboard", params={"season": SEASON})
    assert res.status_code == 200
    body = res.json()

    pairs = {(c["team"], c["referee"]): c for c in body["heatmap"]}
    a_under_x = pairs[("Time A", "Arbitro X")]
    a_under_y = pairs[("Time A", "Arbitro Y")]

    # ambos tem n=6, passam o piso de amostra
    assert a_under_x["n"] == 6
    assert not a_under_x["insufficientSample"]
    assert not a_under_y["insufficientSample"]

    # Time A ganha 100% sob X, 50% sob Y -- indice de X deve ser MAIOR
    # (mais favoravel) que o de Y, refletindo o desvio real dos dados.
    assert a_under_x["index"] > a_under_y["index"]

    # KPIs sem filtro somam as DUAS perspectivas (mandante e visitante) de
    # cada um dos 12 jogos -- 24 "jogos-time". Todos os 12 jogos tem
    # vencedor (sem empate no cenario), entao 12 vitorias no total.
    assert body["kpis"]["games"] == 24
    assert body["kpis"]["wins"] == 12

    # filtrando por Time A: 12 jogos, 9 vitorias (6 sob X + 3 sob Y)
    only_a = client.get("/dashboard", params={"season": SEASON, "team": "Time A"}).json()
    assert only_a["kpis"]["games"] == 12
    assert only_a["kpis"]["wins"] == 9


def test_dashboard_falls_back_to_mock_when_season_has_no_real_data(db_session):
    # nada semeado para 2022 -- deve continuar funcionando (fallback mock),
    # nao quebrar so porque a ingestao real ainda nao chegou nessa temporada.
    res = client.get("/dashboard", params={"season": 2022})
    assert res.status_code == 200
    assert res.json()["kpis"]["games"] > 0


def test_filters_include_real_teams_once_ingested(db_session):
    _seed_favoritism_scenario(db_session)
    res = client.get("/filters")
    body = res.json()
    assert "Time A" in body["teams"]
    assert "Arbitro X" in body["referees"]
    assert SEASON in body["seasons"]


def test_scored_fixtures_count_before_cards_are_ingested(db_session):
    """Regressao: um jogo com placar real mas sem /fixtures/events buscado
    ainda (events_ingested=False) tinha sido excluido do V/E/D/gols so por
    faltar cartao -- isso fazia a temporada inteira cair no mock ate a
    ingestao de cartao terminar (bug reportado: "Sao Paulo campeao 2024"
    vinha do fallback mock, nao de dado real)."""
    team_a = Team(api_id=10, name="Time C")
    team_b = Team(api_id=20, name="Time D")
    ref = Referee(name="Arbitro Z")
    db_session.add_all([team_a, team_b, ref])
    db_session.flush()

    for i in range(6):
        db_session.add(Fixture(
            api_id=2000 + i, season=SEASON, round=f"Regular Season - {i + 1}",
            date="2023-06-01", home_team_id=team_a.id, away_team_id=team_b.id,
            referee_id=ref.id, home_score=1, away_score=0,
            events_ingested=False,  # cartao ainda nao buscado -- so o placar existe
        ))
    db_session.commit()

    res = client.get("/dashboard", params={"season": SEASON})
    assert res.status_code == 200
    body = res.json()

    # dado real (nao caiu no mock) mesmo sem nenhum cartao ainda ingerido
    assert body["dataCompleteness"]["isReal"] is True
    assert body["dataCompleteness"]["fixtures"] == 6
    assert body["dataCompleteness"]["fixturesWithCards"] == 0

    row = next(c for c in body["heatmap"] if c["team"] == "Time C" and c["referee"] == "Arbitro Z")
    assert row["n"] == 6
    assert row["wins"] == 6  # Time C venceu os 6 -- contado mesmo sem cartao
    assert row["yellow"] == 0  # cartao genuinamente desconhecido ainda, nao inventado
