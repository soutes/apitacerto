import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.models import StatReport
from app.analysis.projection import fit_strengths, goal_rates, outcome_probs, project_season, simulate


def _league(n_teams=6, seasons=(2024, 2025), strength=None, played_until=None, seed=1):
    """Turno e returno sintético: gols de Poisson com força conhecida por time.
    played_until corta a última temporada (o resto fica sem placar)."""
    rng = np.random.default_rng(seed)
    teams = [f"T{i}" for i in range(n_teams)]
    strength = strength or {t: 0.5 - 0.2 * i for i, t in enumerate(teams)}
    rows, fid = [], 0
    for s in seasons:
        day = pd.Timestamp(f"{s}-04-01")
        games = [(h, a) for h in teams for a in teams if h != a]
        for k, (h, a) in enumerate(games):
            fid += 1
            lh = np.exp(0.25 + 0.3 + strength[h] - strength[a])
            la = np.exp(0.25 + strength[a] - strength[h])
            played = played_until is None or s != seasons[-1] or k < played_until
            rows.append((fid, s, day + pd.Timedelta(days=3 * k), h, a,
                         rng.poisson(lh) if played else None, rng.poisson(la) if played else None, played))
    df = pd.DataFrame(rows, columns=["id", "season", "date", "home", "away", "hs", "as_", "played"])
    return df


def test_fit_recovers_order_and_home_advantage():
    df = _league(seasons=(2021, 2022, 2023, 2024, 2025))
    model = fit_strengths(df, df.date.max())
    att = {t: model.beta[2 + i] for i, t in enumerate(model.teams)}
    assert att["T0"] > att["T3"] > att["T5"]
    assert model.beta[1] > 0.1  # mando da liga (0,3 no gerador)


def test_recent_games_weigh_more():
    """T0 era o melhor antes e o pior agora: com meia-vida curta, a força
    estimada cai mais do que sem peso nenhum."""
    old = _league(seasons=(2021, 2022, 2023), strength={f"T{i}": 0.5 - 0.2 * i for i in range(6)})
    new = _league(seasons=(2024, 2025), strength={f"T{i}": -0.5 + 0.2 * i for i in range(6)}, seed=2)
    new["id"] += 10_000
    df = pd.concat([old, new])
    flat = fit_strengths(df, df.date.max(), half_life=None)
    recent = fit_strengths(df, df.date.max(), half_life=180)
    i = flat.teams.index("T0")
    assert recent.beta[2 + i] < flat.beta[2 + i]


def test_probabilities_are_consistent():
    df = _league()
    model = fit_strengths(df, df.date.max())
    lh, la = goal_rates(model, model.beta, ["T0", "T5"], ["T5", "T0"])
    probs = outcome_probs(lh, la)
    assert np.allclose(probs.sum(axis=1), 1)
    assert probs[0, 0] > probs[0, 2]  # forte em casa contra fraco
    # clube sem histórico entra como média, sem quebrar
    lh2, la2 = goal_rates(model, model.beta, ["Novo"], ["T0"])
    assert lh2[0] > 0 and la2[0] > 0


def test_simulation_keeps_played_points_and_positions_sum_to_one():
    df = _league(played_until=20)
    season = df[df.season == 2025]
    model = fit_strengths(df[df.played], df[df.played].date.max())
    sim = simulate(model, season, n_sims=2000, draws=20, seed=3)
    assert np.allclose(sim["positions"].sum(axis=0), 1)  # cada posição tem um dono
    assert np.allclose(sim["positions"].sum(axis=1), 1)  # cada clube tem uma posição
    # pontos simulados nunca ficam abaixo do que já foi conquistado
    assert (sim["points"] >= sim["base"][0]).all()
    # total de pontos por simulação: jogados + 2 ou 3 por jogo restante
    left = int((~season.played).sum())
    totals = sim["points"].sum(axis=1) - sim["base"][0].sum()
    assert totals.min() >= 2 * left and totals.max() <= 3 * left


def test_strongest_team_is_title_favorite():
    df = _league(n_teams=6, seasons=(2023, 2024, 2025), played_until=18)
    rows, _ = project_season(df, 2025, n_sims=2000, draws=20)
    by_team = {r["team"]: r for r in rows}
    assert by_team["T0"]["title"] == max(r["title"] for r in rows)
    assert by_team["T5"]["relegation"] >= by_team["T0"]["relegation"]
    assert abs(sum(r["title"] for r in rows) - 100) < 0.5


def test_projection_endpoint_reads_stored_payload(db_session):
    client = TestClient(app)
    assert client.get("/projection").status_code == 404
    db_session.add(StatReport(key="projection", method_version=1, data_version="x", computed_at="2026-09-24T00:00:00",
                              payload={"season": 2026, "teams": []}))
    db_session.commit()
    body = client.get("/projection").json()
    assert body["season"] == 2026 and body["computedAt"] == "2026-09-24T00:00:00"
