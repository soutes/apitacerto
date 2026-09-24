from fastapi.testclient import TestClient

from app.club_insights import build_club_insights
from app.main import app
from app.models import Fixture, MatchEvent, Team

client = TestClient(app)


def _league(db, season, team_ids, skip=0):
    """Turno e returno completos em que o time de indice menor sempre vence
    por 1 a 0 -- a classificacao final e conhecida de antemao. skip tira os
    ultimos jogos (temporada em andamento)."""
    fixtures = []
    n = 0
    for leg in (0, 1):
        for i, a in enumerate(team_ids):
            for b in team_ids[i + 1:]:
                home, away = (a, b) if leg == 0 else (b, a)
                strong_home = team_ids.index(home) < team_ids.index(away)
                n += 1
                fixtures.append(Fixture(
                    api_id=season * 1000 + n, source="cbf", season=season, round=str(leg * 19 + 1),
                    date=f"{season}-{(n // 30) + 1:02d}-{(n % 28) + 1:02d}",
                    home_team_id=home, away_team_id=away,
                    home_score=1 if strong_home else 0, away_score=0 if strong_home else 1,
                ))
    if skip:
        fixtures = fixtures[:-skip]
    db.add_all(fixtures)
    db.commit()
    return fixtures


def _teams(db, names):
    teams = [Team(api_id=i + 1, name=name) for i, name in enumerate(names)]
    db.add_all(teams)
    db.commit()
    return {t.name: t.id for t in teams}


def test_final_table_fates_and_trajectories(db_session):
    ids = _teams(db_session, [f"Clube {i:02d}" for i in range(24)])
    first20 = [ids[f"Clube {i:02d}"] for i in range(20)]
    _league(db_session, 2024, first20)

    body = build_club_insights(db_session)
    season = body["seasons"][0]
    assert season["complete"] is True
    teams = {t["team"]: t for t in season["teams"]}
    assert teams["Clube 00"]["position"] == 1 and teams["Clube 00"]["fate"] == "champion"
    assert [teams[f"Clube {i:02d}"]["fate"] for i in (1, 5, 6, 15, 16, 19)] == [
        "top6", "top6", "mid", "mid", "relegated", "relegated"
    ]
    # trajetoria: pontos acumulados jogo a jogo, 38 jogos
    assert len(teams["Clube 00"]["points"]) == 38
    assert teams["Clube 00"]["points"][-1] == 114
    assert teams["Clube 19"]["points"][-1] == 0
    assert teams["Clube 00"]["homePoints"] + teams["Clube 00"]["awayPoints"] == 114
    assert all(b >= a for a, b in zip(teams["Clube 07"]["points"], teams["Clube 07"]["points"][1:]))
    assert teams["Clube 00"]["promoted"] is False  # primeira temporada do banco: sem referencia


def test_promoted_flag_and_incomplete_season(db_session):
    ids = _teams(db_session, [f"Clube {i:02d}" for i in range(24)])
    _league(db_session, 2024, [ids[f"Clube {i:02d}"] for i in range(20)])
    # sobem 20-23, caem 16-19; temporada nova pela metade
    next_ids = [ids[f"Clube {i:02d}"] for i in list(range(16)) + [20, 21, 22, 23]]
    _league(db_session, 2025, next_ids, skip=100)

    seasons = {s["season"]: s for s in build_club_insights(db_session)["seasons"]}
    current = seasons[2025]
    assert current["complete"] is False
    assert all(t["fate"] is None for t in current["teams"])
    promoted = sorted(t["team"] for t in current["teams"] if t["promoted"])
    assert promoted == ["Clube 20", "Clube 21", "Clube 22", "Clube 23"]


def test_first_goal_counts_own_goal_for_the_other_side(db_session):
    ids = _teams(db_session, ["Casa", "Fora"])
    game = Fixture(api_id=1, source="cbf", season=2024, round="1", date="2024-04-01",
                   home_team_id=ids["Casa"], away_team_id=ids["Fora"], home_score=1, away_score=2)
    db_session.add(game)
    db_session.commit()
    db_session.add_all([
        # gol contra de jogador da Casa aos 10': o primeiro gol e do visitante
        MatchEvent(fixture_id=game.id, team_id=ids["Casa"], minute=10, period="1T", type="GOAL", detail="contra"),
        MatchEvent(fixture_id=game.id, team_id=ids["Casa"], minute=30, period="1T", type="GOAL", detail="normal"),
        MatchEvent(fixture_id=game.id, team_id=ids["Fora"], minute=80, period="2T", type="GOAL", detail="normal"),
    ])
    db_session.commit()

    body = build_club_insights(db_session)
    fg = body["firstGoal"]
    assert fg["games"] == 1 and fg["awayFirst"] == 1 and fg["awayFirstWins"] == 1 and fg["firstWins"] == 1
    assert body["comebacks"] == [{"team": "Casa", "games": 1, "pointsPerGame": 0.0, "wins": 0}]


def test_club_insights_endpoint_shape(db_session):
    ids = _teams(db_session, [f"Clube {i:02d}" for i in range(20)])
    _league(db_session, 2024, list(ids.values()))
    res = client.get("/club-insights")
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"seasons", "firstGoal", "comebacks"}
    assert set(body["seasons"][0]) >= {"season", "complete", "teams", "goalsPerGame", "homeWinPct", "zeroZeroPct"}
