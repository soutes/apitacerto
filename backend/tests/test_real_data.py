"""Testa app/queries.py (Fase 5: dado real via SQLAlchemy) fim a fim pela
API, sem tocar rede -- semeia o banco de teste (conftest.py) direto com os
models. Cenario desenhado pra sinalizar favorecimento de verdade: Time A
ganha tudo e nao toma cartao sob o Arbitro X, mas e parelho e toma cartao
normal sob o Arbitro Y.
"""
from fastapi.testclient import TestClient

from app.main import app
from app.models import Fixture, IngestionLog, MatchEvent, Referee, Team

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

    # contagens do par vem direto do banco: A ganha os 6 sob X, 3 de 6 sob Y
    assert a_under_x["n"] == 6 and a_under_x["wins"] == 6 and a_under_x["yellow"] == 0
    assert a_under_y["n"] == 6 and a_under_y["wins"] == 3 and a_under_y["yellow"] == 6

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


def test_season_overview_kpis_and_referee_rankings(db_session):
    """Design handoff 2026-09-14 (Dashboard novo): KPIs de temporada +
    ranking de arbitro por cartao/jogo e vies de mandante. Cenario: 8 jogos
    (piso REFEREE_SAMPLE_FLOOR), mandante sempre leva 1 amarelo, visitante
    sempre leva 3 -- vies de mandante tem que sair negativo (visitante leva
    mais), cardsPerGame = 4.0 exato."""
    home = Team(api_id=101, name="Time Mandante")
    away = Team(api_id=102, name="Time Visitante")
    ref = Referee(name="Arbitro Oito Jogos")
    db_session.add_all([home, away, ref])
    db_session.flush()

    for i in range(8):
        fx = Fixture(
            source="cbf", api_id=9000 + i, season=SEASON, round=f"Regular Season - {i + 1}",
            date="2023-01-01", home_team_id=home.id, away_team_id=away.id,
            referee_id=ref.id, home_score=2, away_score=1, events_ingested=True,
        )
        db_session.add(fx)
        db_session.flush()
        db_session.add(MatchEvent(fixture_id=fx.id, team_id=home.id, type="YELLOW_CARD"))
        for _ in range(3):
            db_session.add(MatchEvent(fixture_id=fx.id, team_id=away.id, type="YELLOW_CARD"))
    db_session.commit()

    res = client.get("/season-overview", params={"season": SEASON})
    assert res.status_code == 200
    body = res.json()

    assert body["gamesPlayed"] == 8
    assert body["homeWinPct"] == 100.0  # mandante venceu os 8 (2x1)
    assert body["goalsPerGame"] == 3.0  # (2+1) por jogo
    assert body["cardsPerGame"] == 4.0  # (1+3) por jogo

    assert len(body["mostCardsReferees"]) == 1
    top = body["mostCardsReferees"][0]
    assert top["name"] == "Arbitro Oito Jogos"
    assert top["games"] == 8
    assert top["cardsPerGame"] == 4.0
    assert top["barPct"] == 100.0  # unico da lista, normalizado no proprio maximo

    assert len(body["homeBiasReferees"]) == 1
    bias = body["homeBiasReferees"][0]
    assert bias["name"] == "Arbitro Oito Jogos"
    assert bias["bias"] == -2.0  # mandante 1 cartao, visitante 3 -> 1-3

    # allReferees: lista completa (tela Arbitros), nao so o top 5/4
    assert len(body["allReferees"]) == 1
    assert body["allReferees"][0]["cardsPerGame"] == 4.0
    assert body["allReferees"][0]["bias"] == -2.0


def test_season_overview_excludes_referee_below_sample_floor(db_session):
    home = Team(api_id=103, name="Time C")
    away = Team(api_id=104, name="Time D")
    ref = Referee(name="Arbitro Poucos Jogos")
    db_session.add_all([home, away, ref])
    db_session.flush()

    for i in range(3):  # abaixo do piso de 8
        db_session.add(Fixture(
            source="cbf", api_id=9100 + i, season=SEASON, round=f"Regular Season - {i + 1}",
            date="2023-02-01", home_team_id=home.id, away_team_id=away.id,
            referee_id=ref.id, home_score=1, away_score=0, events_ingested=True,
        ))
    db_session.commit()

    body = client.get("/season-overview", params={"season": SEASON}).json()
    names = [r["name"] for r in body["mostCardsReferees"]] + [r["name"] for r in body["homeBiasReferees"]]
    names += [r["name"] for r in body["allReferees"]]
    assert "Arbitro Poucos Jogos" not in names
    assert body["gamesPlayed"] == 3  # conta pro KPI de temporada mesmo assim


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

    # sem IngestionLog gravado ainda pra essa temporada -- nao inventa data
    assert body["dataCompleteness"]["lastUpdated"] is None


def test_last_updated_reflects_latest_ingestion_log(db_session):
    team = Team(api_id=777, name="Time E")
    db_session.add(team)
    db_session.flush()
    db_session.add_all([
        IngestionLog(source="cbf", season=SEASON, round=1, finished_at="2026-09-01T10:00:00+00:00", matches=10, events=50),
        IngestionLog(source="cbf", season=SEASON, round=2, finished_at="2026-09-08T10:00:00+00:00", matches=10, events=45),
        Fixture(source="cbf", api_id=5001, season=SEASON, home_team_id=team.id, away_team_id=team.id,
                home_score=1, away_score=0, events_ingested=True),
    ])
    db_session.commit()

    res = client.get("/dashboard", params={"season": SEASON})
    assert res.json()["dataCompleteness"]["lastUpdated"] == "2026-09-08T10:00:00+00:00"
