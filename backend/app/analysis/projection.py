"""Projeção do fim da temporada em andamento (aba Análises dos clubes).

Modelo de gols de Poisson com força de ataque e de defesa de cada clube e
mando de campo (Maher, 1982; Dixon & Coles, 1997), ajustado em TODOS os
jogos do banco com peso que cai com o tempo: um jogo de `HALF_LIFE_DAYS`
atrás vale metade de um jogo de hoje (a ideia do peso exponencial é de Dixon
& Coles). Mando da liga + um ajuste de mando por clube, encolhido para zero.
Os jogos que faltam são simulados (Monte Carlo) sorteando também os
parâmetros da distribuição aproximada do ajuste, para a incerteza da força
dos times entrar nas chances.

Escolhas fixadas por backtest (2019-2025, projetando do mesmo ponto em que a
temporada atual está) -- ver `backtest_variants` e _docs:
- meia-vida de 2 anos acertou mais que meias-vidas curtas (60-365 dias) e que
  usar só a temporada atual;
- a correção de placares baixos de Dixon-Coles (rho) não melhorou e ficou de
  fora;
- o mando por clube mudou pouco, mas não piorou -- fica, com encolhimento.

Offline (numpy/scipy/pandas): roda no compute_stats, a API só lê o JSON.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats as st
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Fixture, Team

HALF_LIFE_DAYS = 730
TEAM_SIGMA = 1.0  # desvio a priori de ataque/defesa (escala log): prior fraca
HOME_SIGMA = 0.1  # desvio a priori do mando de cada clube em relação à liga
MAX_GOALS = 10
N_SIMS = 20_000
PARAM_DRAWS = 200
RELEGATION_SPOTS = 4


@dataclass
class Strengths:
    teams: list[str]
    beta: np.ndarray
    cov: np.ndarray

    @property
    def index(self) -> dict[str, int]:
        return {t: i for i, t in enumerate(self.teams)}


def load_fixtures(db: Session) -> pd.DataFrame:
    names = dict(db.execute(select(Team.id, Team.name)).all())
    rows = db.execute(
        select(Fixture.id, Fixture.season, Fixture.date, Fixture.home_team_id, Fixture.away_team_id,
               Fixture.home_score, Fixture.away_score)
        .order_by(Fixture.season, Fixture.date, Fixture.id)
    ).all()
    df = pd.DataFrame(
        [(r.id, r.season, r.date, names[r.home_team_id], names[r.away_team_id], r.home_score, r.away_score)
         for r in rows],
        columns=["id", "season", "date", "home", "away", "hs", "as_"],
    )
    df["date"] = pd.to_datetime(df.date)
    df["played"] = df.hs.notna() & df.as_.notna()
    return df


def _design(games: pd.DataFrame, teams: list[str]) -> tuple[np.ndarray, int]:
    """Uma linha por gol-de-time: [const, mando, ataque(n), defesa(n), mando do clube(n)].
    Linhas 0..m-1 = gols do mandante; m..2m-1 = gols do visitante."""
    ix = {t: i for i, t in enumerate(teams)}
    n, m = len(teams), len(games)
    h = games.home.map(ix).to_numpy()
    a = games.away.map(ix).to_numpy()
    X = np.zeros((2 * m, 2 + 3 * n))
    r = np.arange(m)
    X[:, 0] = 1.0
    X[r, 1] = 1.0
    X[r, 2 + h] = 1.0
    X[r, 2 + n + a] = -1.0
    X[r, 2 + 2 * n + h] = 1.0
    X[m + r, 2 + a] = 1.0
    X[m + r, 2 + n + h] = -1.0
    return X, n


def fit_strengths(train: pd.DataFrame, ref_date: pd.Timestamp, half_life: float | None = HALF_LIFE_DAYS,
                  team_sigma: float = TEAM_SIGMA, home_sigma: float = HOME_SIGMA,
                  team_home: bool = True) -> Strengths:
    """Poisson ponderado e penalizado (Newton-Raphson). Peso de cada jogo:
    0,5 ** (dias até ref_date / half_life)."""
    teams = sorted(set(train.home) | set(train.away))
    X, n = _design(train, teams)
    if not team_home:
        X[:, 2 + 2 * n:] = 0.0
    days = (ref_date - train.date).dt.days.clip(lower=0).to_numpy()
    w = np.ones(len(train)) if half_life is None else 0.5 ** (days / half_life)
    W = np.concatenate([w, w])
    y = np.concatenate([train.hs.to_numpy(), train.as_.to_numpy()]).astype(float)
    pen = np.concatenate([[0.0, 0.0], np.full(2 * n, 1 / team_sigma**2), np.full(n, 1 / home_sigma**2)])
    beta = np.zeros(X.shape[1])
    beta[0] = math.log(max(y.mean(), 1e-6))
    for _ in range(60):
        mu = np.exp(np.clip(X @ beta, -20, 20))
        info = (X.T * (W * mu)) @ X + np.diag(pen)
        step = np.linalg.solve(info, X.T @ (W * (y - mu)) - pen * beta)
        beta = beta + step
        if np.max(np.abs(step)) < 1e-9:
            break
    mu = np.exp(np.clip(X @ beta, -20, 20))
    cov = np.linalg.inv((X.T * (W * mu)) @ X + np.diag(pen))
    return Strengths(teams, beta, cov)


def goal_rates(model: Strengths, beta: np.ndarray, home: list[str], away: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Gols esperados de mandante e visitante; clube sem histórico = média."""
    ix = model.index
    n = len(model.teams)

    def col(block: int, names: list[str]) -> np.ndarray:
        idx = np.array([ix.get(t, -1) for t in names])
        vals = np.where(idx >= 0, beta[2 + block * n + np.clip(idx, 0, None)], 0.0)
        return vals

    lh = np.exp(beta[0] + beta[1] + col(0, home) - col(1, away) + col(2, home))
    la = np.exp(beta[0] + col(0, away) - col(1, home))
    return lh, la


def outcome_probs(lh: np.ndarray, la: np.ndarray) -> np.ndarray:
    """P(mandante vence), P(empate), P(visitante vence) por jogo."""
    g = np.arange(MAX_GOALS + 1)
    ph = st.poisson.pmf(g[None, :], lh[:, None])
    pa = st.poisson.pmf(g[None, :], la[:, None])
    joint = ph[:, :, None] * pa[:, None, :]
    joint /= joint.sum(axis=(1, 2), keepdims=True)
    home = np.tril(np.ones((g.size, g.size)), -1)
    return np.stack([(joint * home).sum(axis=(1, 2)), np.einsum("nii->n", joint), (joint * home.T).sum(axis=(1, 2))], 1)


def simulate(model: Strengths, season: pd.DataFrame, n_sims: int = N_SIMS, draws: int = PARAM_DRAWS,
             seed: int = 0, cov_scale: float = 1.0) -> dict:
    """Simula os jogos sem placar de `season` e devolve, por clube, pontos
    finais simulados e contagem de posições (desempate da CBF: pontos,
    vitórias, saldo, gols pró)."""
    rng = np.random.default_rng(seed)
    teams = sorted(set(season.home) | set(season.away))
    tix = {t: i for i, t in enumerate(teams)}
    n_t = len(teams)
    done = season[season.played]
    todo = season[~season.played]

    base = np.zeros((4, n_t))  # pontos, vitórias, gols pró, gols contra
    for r in done.itertuples():
        h, a = tix[r.home], tix[r.away]
        base[2, h] += r.hs
        base[3, h] += r.as_
        base[2, a] += r.as_
        base[3, a] += r.hs
        if r.hs > r.as_:
            base[0, h] += 3
            base[1, h] += 1
        elif r.hs < r.as_:
            base[0, a] += 3
            base[1, a] += 1
        else:
            base[0, h] += 1
            base[0, a] += 1

    per_draw = max(1, n_sims // draws)
    total = per_draw * draws
    pts = np.tile(base[0], (total, 1))
    wins = np.tile(base[1], (total, 1))
    gf = np.tile(base[2], (total, 1))
    ga = np.tile(base[3], (total, 1))
    if len(todo):
        # one-hot jogo -> clube: somar resultados por clube vira produto de matrizes
        on_home = np.eye(n_t)[todo.home.map(tix).to_numpy()]
        on_away = np.eye(n_t)[todo.away.map(tix).to_numpy()]
        chol = np.linalg.cholesky(cov_scale * model.cov + 1e-10 * np.eye(len(model.beta)))
        for d in range(draws):
            beta = model.beta + chol @ rng.standard_normal(len(model.beta))
            lh, la = goal_rates(model, beta, list(todo.home), list(todo.away))
            rows = slice(d * per_draw, (d + 1) * per_draw)
            sh = rng.poisson(lh[None, :], size=(per_draw, len(todo)))
            sa = rng.poisson(la[None, :], size=(per_draw, len(todo)))
            hw, aw, dr = (sh > sa).astype(float), (sh < sa).astype(float), (sh == sa).astype(float)
            pts[rows] += (3 * hw + dr) @ on_home + (3 * aw + dr) @ on_away
            wins[rows] += hw @ on_home + aw @ on_away
            gf[rows] += sh @ on_home + sa @ on_away
            ga[rows] += sa @ on_home + sh @ on_away
    key = pts * 1e9 + wins * 1e6 + (gf - ga + 1000) * 1e2 + gf
    order = np.argsort(-key, axis=1, kind="stable")
    positions = np.empty_like(order)
    positions[np.arange(total)[:, None], order] = np.arange(n_t)[None, :]
    counts = np.stack([np.bincount(positions[:, i], minlength=n_t) for i in range(n_t)])
    return {"teams": teams, "points": pts, "positions": counts / total, "base": base, "sims": total}


def summarize(sim: dict, season: pd.DataFrame) -> list[dict]:
    n_t = len(sim["teams"])
    played = season[season.played]
    games = pd.concat([played.home, played.away]).value_counts()
    out = []
    for i, t in enumerate(sim["teams"]):
        p = sim["points"][:, i]
        pos = sim["positions"][i]
        out.append({
            "team": t,
            "points": int(sim["base"][0, i]),
            "games": int(games.get(t, 0)),
            "goalDiff": int(sim["base"][2, i] - sim["base"][3, i]),
            "expPoints": round(float(p.mean()), 1),
            "low": int(np.percentile(p, 10)),
            "high": int(np.percentile(p, 90)),
            "title": round(float(pos[0]) * 100, 1),
            "top4": round(float(pos[:4].sum()) * 100, 1),
            "top6": round(float(pos[:6].sum()) * 100, 1),
            "relegation": round(float(pos[n_t - RELEGATION_SPOTS:].sum()) * 100, 1),
            "positions": [round(float(x) * 100, 1) for x in pos],
            "expPosition": round(float((pos * np.arange(1, n_t + 1)).sum()), 1),
        })
    return sorted(out, key=lambda r: (-r["expPoints"], r["expPosition"]))


def project_season(fixtures: pd.DataFrame, season: int, cut_games: int | None = None, n_sims: int = N_SIMS,
                   draws: int = PARAM_DRAWS, seed: int = 0, cov_scale: float = 1.0) -> tuple[list[dict], pd.Timestamp]:
    """Projeta `season` a partir dos primeiros `cut_games` jogos com placar
    (em ordem de data); None = tudo que já foi jogado."""
    sea = fixtures[fixtures.season == season].sort_values(["date", "id"]).copy()
    played = sea[sea.played]
    if cut_games is not None:
        keep = set(played.id.iloc[:cut_games])
        sea["played"] = sea.id.isin(keep)
        played = sea[sea.played]
    ref = played.date.max()
    train = pd.concat([fixtures[(fixtures.season < season) & fixtures.played], played])
    model = fit_strengths(train, ref)
    sim = simulate(model, sea, n_sims=n_sims, draws=draws, seed=seed, cov_scale=cov_scale)
    return summarize(sim, sea), ref


def backtest_variants(fixtures: pd.DataFrame, cut_games: int, seasons: list[int]) -> list[dict]:
    """Log-loss e Brier dos jogos restantes, projetando cada temporada
    encerrada a partir de `cut_games` jogos. Quanto menor, melhor."""
    variants = [
        ("Só a temporada atual, todos os jogos com o mesmo peso", dict(half_life=None, only_season=True, team_home=False)),
        ("Todas as temporadas, meia-vida de 90 dias", dict(half_life=90, only_season=False, team_home=True)),
        ("Todas as temporadas, meia-vida de 1 ano", dict(half_life=365, only_season=False, team_home=True)),
        ("Todas as temporadas, meia-vida de 2 anos (escolhido)", dict(half_life=730, only_season=False, team_home=True)),
        ("Todas as temporadas, todos os jogos com o mesmo peso", dict(half_life=None, only_season=False, team_home=True)),
        ("Meia-vida de 2 anos sem mando por clube", dict(half_life=730, only_season=False, team_home=False)),
    ]
    out = []
    for label, v in variants:
        losses, briers = [], []
        for s in seasons:
            sea = fixtures[(fixtures.season == s) & fixtures.played].sort_values(["date", "id"])
            cut, rest = sea.iloc[:cut_games], sea.iloc[cut_games:]
            if rest.empty or cut.empty:
                continue
            train = cut if v["only_season"] else pd.concat([fixtures[(fixtures.season < s) & fixtures.played], cut])
            model = fit_strengths(train, cut.date.max(), half_life=v["half_life"], team_home=v["team_home"])
            lh, la = goal_rates(model, model.beta, list(rest.home), list(rest.away))
            probs = outcome_probs(lh, la)
            o = np.where(rest.hs > rest.as_, 0, np.where(rest.hs == rest.as_, 1, 2))
            losses.extend(-np.log(np.clip(probs[np.arange(len(o)), o], 1e-9, 1)))
            onehot = np.eye(3)[o]
            briers.extend(((probs - onehot) ** 2).sum(axis=1))
        out.append({"label": label, "logLoss": round(float(np.mean(losses)), 4),
                    "brier": round(float(np.mean(briers)), 4), "games": len(losses)})
    return out


def backtest_table(fixtures: pd.DataFrame, cut_games: int, seasons: list[int], n_sims: int = 4000,
                   cov_scale: float = 1.0) -> dict:
    """Tabela final projetada x real, do mesmo ponto da temporada atual.
    Compara com o 'ritmo atual' (pontos por jogo x 38)."""
    err_model, err_pace, rel, title, cases = [], [], [], [], []
    for s in seasons:
        rows, _ = project_season(fixtures, s, cut_games=cut_games, n_sims=n_sims, draws=40, seed=s,
                                 cov_scale=cov_scale)
        sea = fixtures[(fixtures.season == s) & fixtures.played]
        final = _final_table(sea)
        n_t = len(final)
        for r in rows:
            f = final[r["team"]]
            pace = r["points"] / max(r["games"], 1) * (2 * (n_t - 1))
            err_model.append(abs(r["expPoints"] - f["points"]))
            err_pace.append(abs(pace - f["points"]))
            fell = f["position"] > n_t - RELEGATION_SPOTS
            won = f["position"] == 1
            rel.append(((r["relegation"] / 100) - fell) ** 2)
            title.append(((r["title"] / 100) - won) ** 2)
            cases.append({"season": s, "team": r["team"], "relegation": r["relegation"], "fell": bool(fell),
                          "title": r["title"], "won": bool(won)})
    likely_fall = [c for c in cases if c["relegation"] >= 80]
    likely_safe = [c for c in cases if c["relegation"] <= 5]
    return {
        "seasons": seasons,
        "cutGames": cut_games,
        "pointsErrorModel": round(float(np.mean(err_model)), 2),
        "pointsErrorPace": round(float(np.mean(err_pace)), 2),
        "brierRelegation": round(float(np.mean(rel)), 4),
        "brierTitle": round(float(np.mean(title)), 4),
        "relegationCalls": {"n": len(likely_fall), "fell": sum(c["fell"] for c in likely_fall)},
        "safeCalls": {"n": len(likely_safe), "fell": sum(c["fell"] for c in likely_safe)},
        "titleFavorites": [
            {"season": s, "team": max((c for c in cases if c["season"] == s), key=lambda c: c["title"])["team"],
             "chance": max(c["title"] for c in cases if c["season"] == s),
             "won": max((c for c in cases if c["season"] == s), key=lambda c: c["title"])["won"]}
            for s in seasons
        ],
    }


def backtest_stages(fixtures: pd.DataFrame, played: int, seasons: list[int]) -> list[dict]:
    """Erro médio nos pontos finais por fase do campeonato: modelo x ritmo."""
    stages = sorted({c for c in (110, 190, played) if 0 < c <= played})
    out = []
    for c in stages:
        t = backtest_table(fixtures, c, seasons, n_sims=2000)
        out.append({"cutGames": c, "round": round(c / 10), "pointsErrorModel": t["pointsErrorModel"],
                    "pointsErrorPace": t["pointsErrorPace"]})
    return out


def _final_table(season_played: pd.DataFrame) -> dict[str, dict]:
    acc: dict[str, list[int]] = {}
    for r in season_played.itertuples():
        for t, f, a in ((r.home, r.hs, r.as_), (r.away, r.as_, r.hs)):
            x = acc.setdefault(t, [0, 0, 0, 0])
            x[0] += 3 if f > a else 1 if f == a else 0
            x[1] += f > a
            x[2] += f
            x[3] += a
    order = sorted(acc, key=lambda t: (-acc[t][0], -acc[t][1], -(acc[t][2] - acc[t][3]), -acc[t][2], t))
    return {t: {"points": acc[t][0], "position": i + 1} for i, t in enumerate(order)}


def head_to_head_check(fixtures: pd.DataFrame) -> dict:
    """O confronto direto acrescenta algo à força atual dos times? Para cada
    jogo, compara o saldo real com o esperado (modelo da própria temporada)
    e mede se o 'excesso' dos confrontos anteriores entre os mesmos dois
    clubes prevê o excesso do jogo seguinte."""
    played = fixtures[fixtures.played].sort_values(["date", "id"])
    resid = []
    for s, sea in played.groupby("season"):
        model = fit_strengths(sea, sea.date.max(), half_life=None, team_home=False)
        lh, la = goal_rates(model, model.beta, list(sea.home), list(sea.away))
        sea = sea.assign(res=(sea.hs - sea.as_) - (lh - la))
        resid.append(sea)
    df = pd.concat(resid).sort_values(["date", "id"])
    history: dict[tuple[str, str], list[float]] = {}
    xs, ys = [], []
    for r in df.itertuples():
        a, b = sorted((r.home, r.away))
        signed = r.res if r.home == a else -r.res  # excesso na perspectiva de `a`
        past = history.get((a, b))
        if past:
            xs.append(float(np.mean(past)))
            ys.append(float(signed))
        history.setdefault((a, b), []).append(float(signed))
    corr, p = st.pearsonr(xs, ys) if len(xs) > 10 else (float("nan"), float("nan"))
    return {"pairs": len(xs), "correlation": round(float(corr), 3), "p": round(float(p), 3)}


def evolution(fixtures: pd.DataFrame, season: int, step: int = 10, n_sims: int = 3000) -> list[dict]:
    """A projeção refeita a cada `step` jogos da temporada (≈ uma rodada)."""
    sea = fixtures[(fixtures.season == season) & fixtures.played]
    total = len(sea)
    cuts = list(range(5 * step, total, step))
    if not cuts or cuts[-1] != total:
        cuts.append(total)
    out = []
    for c in cuts:
        rows, ref = project_season(fixtures, season, cut_games=c, n_sims=n_sims, draws=30, seed=c)
        out.append({
            "games": c,
            "round": round(c / step),
            "date": ref.date().isoformat(),
            "teams": {r["team"]: {"title": r["title"], "top6": r["top6"], "relegation": r["relegation"],
                                  "expPoints": r["expPoints"]} for r in rows},
        })
    return out


def build_projection(db: Session) -> dict | None:
    """Projeção da temporada em andamento, com série por rodada e backtest.
    None se não houver temporada em andamento."""
    fixtures = load_fixtures(db)
    if fixtures.empty:
        return None
    open_seasons = sorted(s for s, g in fixtures.groupby("season") if (~g.played).any() and g.played.any())
    if not open_seasons:
        return None
    season = open_seasons[-1]
    rows, ref = project_season(fixtures, season)
    played = int(fixtures[(fixtures.season == season) & fixtures.played].shape[0])
    series = evolution(fixtures, season)
    # o último ponto da série é a projeção de hoje: usa a versão com mais
    # simulações, para os números baterem com a tabela projetada
    series[-1]["teams"] = {r["team"]: {"title": r["title"], "top6": r["top6"], "relegation": r["relegation"],
                                       "expPoints": r["expPoints"]} for r in rows}
    total = int(fixtures[fixtures.season == season].shape[0])
    closed = sorted(s for s, g in fixtures.groupby("season") if g.played.all() and s < season)
    backtest_seasons = [s for s in closed if (fixtures.season < s).any()]  # precisa de passado
    return {
        "season": season,
        "gamesPlayed": played,
        "gamesTotal": total,
        "asOf": ref.date().isoformat(),
        "sims": (N_SIMS // PARAM_DRAWS) * PARAM_DRAWS,
        "method": {
            "halfLifeDays": HALF_LIFE_DAYS,
            "teamSigma": TEAM_SIGMA,
            "homeSigma": HOME_SIGMA,
            "paramDraws": PARAM_DRAWS,
            "relegationSpots": RELEGATION_SPOTS,
        },
        "teams": rows,
        "evolution": series,
        "backtest": {
            "variants": backtest_variants(fixtures, played, backtest_seasons),
            "table": backtest_table(fixtures, played, backtest_seasons),
            "stages": backtest_stages(fixtures, played, backtest_seasons),
        },
        "headToHead": head_to_head_check(fixtures),
    }
