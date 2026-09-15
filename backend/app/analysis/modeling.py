"""Modelos de 'esperado' por jogo (spec 9.1), ajustados temporada a temporada
-- cada jogo e comparado com o esperado da propria temporada."""
from __future__ import annotations

import math
import warnings
from functools import reduce

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats as st

from app.analysis import inference as inf
from app.analysis.data import MISSING_REF

MAX_GOALS = 10
# Penalidade dos efeitos de clube, adversario e interacoes ja sinalizadas: DP
# 1 na escala log. Desprezivel com 38 jogos; so impede coeficiente infinito
# quando sobra pouco dado (comeco de temporada, par grande demais).
WEAK_PRIOR = 1.0
PAIR_COLS = ["team", "ref", "n", "o_cards", "e_cards", "v_cards", "o_opp", "e_opp", "v_opp",
             "o_pts", "e_pts", "v_pts", "ve_pts", "pmf_pts"]
SUM_COLS = PAIR_COLS[2:-1]
ANALYSES = {"cards": ("o_cards", "e_cards", "v_cards"), "opp": ("o_opp", "e_opp", "v_opp"),
            "pts": ("o_pts", "e_pts", "v_pts")}


def poisson_fit(formula: str, data: pd.DataFrame):
    """Regressao de Poisson (Nelder & Wedderburn, 1972)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return smf.glm(formula, data=data, family=sm.families.Poisson()).fit()


def factors(data: pd.DataFrame, names: list[str]) -> list[str]:
    # fator com um nivel so (inicio de temporada, dado de teste) nao entra
    return [f"C({n})" for n in names if data[n].nunique() > 1]


def outcome_probs(lam_for, lam_against) -> tuple[np.ndarray, np.ndarray]:
    """P(vitoria), P(empate) com gols independentes de Poisson (Maher, 1982)."""
    g = np.arange(MAX_GOALS + 1)
    pf = st.poisson.pmf(g[None, :], np.asarray(lam_for, dtype=float)[:, None])
    pa = st.poisson.pmf(g[None, :], np.asarray(lam_against, dtype=float)[:, None])
    joint = pf[:, :, None] * pa[:, None, :]
    p_win = (joint * np.tril(np.ones((g.size, g.size)), -1)).sum(axis=(1, 2))
    p_draw = np.einsum("nii->n", joint)
    return p_win, p_draw


def expected_points(lam_for, lam_against) -> tuple[np.ndarray, np.ndarray]:
    p_win, p_draw = outcome_probs(lam_for, lam_against)
    xp = 3 * p_win + p_draw
    return xp, 9 * p_win + p_draw - xp**2


def fit_season(rows: pd.DataFrame) -> pd.DataFrame:
    """Linhas clube-jogo de UMA temporada -> mesmas linhas com:
    mu_cards     cartoes esperados (clube + adversario + arbitro + mando)
    mu_noref     cartoes esperados SEM o arbitro (base do 'rigor do arbitro')
    mu_opp_cards cartoes esperados do adversario no mesmo jogo
    lam/lam_opp  gols esperados pro/contra (ataque x defesa x mando)
    xpts, v_pts  pontos esperados e sua variancia (facilidade do jogo)."""
    out = rows.reset_index(drop=True).copy()
    who = factors(out, ["team", "opp"])
    rhs = " + ".join(who + ["home"])
    rhs_ref = " + ".join(who + factors(out, ["ref"]) + ["home"])
    out["mu_cards"] = poisson_fit(f"cards ~ {rhs_ref}", out).fittedvalues.to_numpy()
    out["mu_noref"] = poisson_fit(f"cards ~ {rhs}", out).fittedvalues.to_numpy()
    out["lam"] = poisson_fit(f"gf ~ {rhs}", out).fittedvalues.to_numpy()

    me = pd.MultiIndex.from_arrays([out.fid, out.team])
    other = pd.MultiIndex.from_arrays([out.fid, out.opp])
    out["lam_opp"] = pd.Series(out.lam.to_numpy(), index=me).reindex(other).to_numpy()
    out["mu_opp_cards"] = pd.Series(out.mu_cards.to_numpy(), index=me).reindex(other).to_numpy()
    out["xpts"], out["v_pts"] = expected_points(out.lam, out.lam_opp)
    return out


def fit_all(rows: pd.DataFrame) -> pd.DataFrame:
    return pd.concat([fit_season(g) for _, g in rows.groupby("season", sort=True)], ignore_index=True)


# ---------------------------------------------------------------- pares: deixar o par de fora
def irls_poisson(X: np.ndarray, y: np.ndarray, beta: np.ndarray | None = None, pen: np.ndarray | None = None,
                 max_iter: int = 60, tol: float = 1e-9) -> tuple[np.ndarray, np.ndarray]:
    """Poisson por Newton-Raphson (= minimos quadrados reponderados, Nelder &
    Wedderburn, 1972). Enxuto porque roda centenas de vezes por temporada.
    pen = penalidade quadratica por coeficiente: minuscula so segura coluna
    sem dado; grande num grupo = efeito aleatorio, encolhe pra media.
    Devolve (beta, covariancia)."""
    p = X.shape[1]
    if pen is None:
        pen = np.full(p, 1e-6)
        pen[0] = 0.0
    if beta is None:
        beta = np.zeros(p)
        beta[0] = math.log(max(float(y.mean()), 1e-6))
    for _ in range(max_iter):
        mu = np.exp(np.clip(X @ beta, -30, 30))
        info = (X.T * mu) @ X + np.diag(pen)
        step = np.linalg.solve(info, X.T @ (y - mu) - pen * beta)
        beta = beta + step
        if np.max(np.abs(step)) < tol:
            break
    mu = np.exp(np.clip(X @ beta, -30, 30))
    return beta, np.linalg.inv((X.T * mu) @ X + np.diag(pen))


def _dummies(values: np.ndarray, levels: list) -> np.ndarray:
    if not levels:
        return np.zeros((len(values), 0))
    return (values[:, None] == np.array(levels, dtype=object)[None, :]).astype(float)


def _designs(r: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    """Um coeficiente por nivel (clube, adversario, arbitro), sem nivel de
    referencia: a penalidade centra cada grupo, entao coeficiente 0 = nivel
    medio -- quem tem pouco dado fica perto do medio, nao de um clube
    arbitrario. Devolve (X cartoes, X gols, indices dos grupos)."""
    team = _dummies(r.team.to_numpy(dtype=object), sorted(r.team.unique()))
    opp = _dummies(r.opp.to_numpy(dtype=object), sorted(r.opp.unique()))
    refs = _dummies(r.ref.to_numpy(dtype=object), sorted(r.ref.unique()))
    one, home = np.ones((len(r), 1)), r.home.to_numpy(float)[:, None]
    clubs = team.shape[1] + opp.shape[1]
    idx = {"clubs": np.arange(1, 1 + clubs), "ref": np.arange(1 + clubs, 1 + clubs + refs.shape[1])}
    return np.hstack([one, team, opp, refs, home]), np.hstack([one, team, opp, home]), idx


def _indicators(r: pd.DataFrame, pairs, side: str) -> list[np.ndarray]:
    """Coluna 0/1 de uma interacao ja sinalizada (busca progressiva): linhas
    em que o clube (side='team') ou o adversario do clube (side='opp') joga
    com aquele arbitro."""
    who, ref = r[side].to_numpy(dtype=object), r.ref.to_numpy(dtype=object)
    return [((who == t) & (ref == rf)).astype(float) for t, rf in sorted(pairs)]


def _penalty(n_cols: int, weak: np.ndarray, ref: np.ndarray | None = None, lam_ref: float = 0.0) -> np.ndarray:
    pen = np.full(n_cols, 1e-6)
    pen[0] = 0.0
    pen[weak] = WEAK_PRIOR
    if ref is not None:
        pen[ref] = lam_ref
    return pen


def _referee_penalty(r: pd.DataFrame, x_noref: np.ndarray, pen: np.ndarray, y: np.ndarray) -> float:
    """Quanto os arbitros variam de verdade entre si, descontado o acaso
    (mesmo Bayes empirico do ranking de rigor). Vira a 'prior' de cada
    arbitro: quem tem pouco jogo fica perto do medio -- sem isso, arbitro com
    2 jogos restantes ganha rigor extremo e cria falso sinal nos pares."""
    b0, _ = irls_poisson(x_noref, y, pen=pen)
    per_ref = (pd.DataFrame({"ref": r.ref.to_numpy(), "o": y, "e": np.exp(x_noref @ b0)})
               .groupby("ref").sum())
    per_ref = per_ref[(per_ref.index != MISSING_REF) & (per_ref.e > 0)]
    tau2_log = 0.0
    if len(per_ref) >= 3:
        _, _, tau2, mean = inf.gamma_poisson_shrink(per_ref.o, per_ref.e)
        tau2_log = tau2 / mean**2 if mean > 0 else 0.0
    return 1.0 / min(max(tau2_log, 0.03**2), 0.6**2)


def _stack(base: np.ndarray, cols: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    extra = np.arange(base.shape[1], base.shape[1] + len(cols))
    return (np.hstack([base, np.column_stack(cols)]) if cols else base), extra


def season_pair_table(rows: pd.DataFrame, flagged: dict | None = None) -> pd.DataFrame:
    """Observado vs esperado de cada par clube x arbitro de UMA temporada, com
    o esperado ajustado SEM os jogos do proprio par (ideia do jackknife --
    Quenouille, 1949; Tukey, 1958). Sem isso, o efeito do par entra no 'rigor
    geral' do arbitro e no 'estilo' do clube: o sinal some e aparece
    espelhado em pares inocentes. A variancia soma a incerteza do proprio
    esperado. flagged = interacoes ja sinalizadas, que entram no modelo como
    termos proprios pra nao contaminar o esperado dos outros pares."""
    flagged = flagged or {k: frozenset() for k in ANALYSES}
    r = rows.reset_index(drop=True)
    xc0, xg0, idx = _designs(r)
    ind_c = _indicators(r, flagged["cards"], "team") + _indicators(r, flagged["opp"], "opp")
    ind_g = _indicators(r, flagged["pts"], "team") + _indicators(r, flagged["pts"], "opp")
    xc, extra_c = _stack(xc0, ind_c)
    xg, extra_g = _stack(xg0, ind_g)
    # coluna de cada interacao sinalizada -- no teste do PROPRIO par ela sai
    # da previsao (a pergunta e 'contra o modelo sem a interacao dele')
    col_c = dict(zip([("cards", p) for p in sorted(flagged["cards"])]
                     + [("opp", p) for p in sorted(flagged["opp"])], extra_c))
    col_g = dict(zip([("team", p) for p in sorted(flagged["pts"])]
                     + [("opp", p) for p in sorted(flagged["pts"])], extra_g))
    yc, yg = r.cards.to_numpy(float), r.gf.to_numpy(float)
    fid, pts = r.fid.to_numpy(), r.pts.to_numpy(float)

    x_noref, extra_n = _stack(xg0, ind_c)
    lam_ref = _referee_penalty(r, x_noref, _penalty(x_noref.shape[1], np.concatenate([idx["clubs"], extra_n])), yc)
    pen_c = _penalty(xc.shape[1], np.concatenate([idx["clubs"], extra_c]), idx["ref"], lam_ref)
    pen_g = _penalty(xg.shape[1], np.concatenate([idx["clubs"], extra_g]))
    bc, _ = irls_poisson(xc, yc, pen=pen_c)
    bg, _ = irls_poisson(xg, yg, pen=pen_g)
    where = {(f, t): i for i, (f, t) in enumerate(zip(fid, r.team))}
    opp_idx = np.array([where[(f, o)] for f, o in zip(fid, r.opp)])

    out = []
    for (team, ref), members in r.groupby(["team", "ref"]).indices.items():
        if ref == MISSING_REF:
            continue
        own = np.asarray(members)
        opp = opp_idx[own]
        keep = ~np.isin(fid, fid[own])
        # arbitro sem nenhum outro jogo cai sozinho no 'arbitro medio' (a
        # penalidade manda o coeficiente pra zero) com variancia = a prior
        b1, c1 = irls_poisson(xc[keep], yc[keep], bc.copy(), pen=pen_c)
        b2, c2 = irls_poisson(xg[keep], yg[keep], bg.copy(), pen=pen_g)
        mine_c = [col_c[k] for k in (("cards", (team, ref)), ("opp", (team, ref))) if k in col_c]
        mine_g = [col_g[k] for k in (("team", (team, ref)), ("opp", (team, ref))) if k in col_g]
        xo_c, xp_c, xo_g, xp_g = xc[own].copy(), xc[opp].copy(), xg[own].copy(), xg[opp].copy()
        xo_c[:, mine_c] = xp_c[:, mine_c] = 0.0
        xo_g[:, mine_g] = xp_g[:, mine_g] = 0.0

        mu_own, mu_opp = np.exp(xo_c @ b1), np.exp(xp_c @ b1)
        g_own, g_opp = xo_c.T @ mu_own, xp_c.T @ mu_opp
        var_own = float(g_own @ c1 @ g_own)
        var_opp = float(g_opp @ c1 @ g_opp)

        lam_own, lam_opp = np.exp(xo_g @ b2), np.exp(xp_g @ b2)
        p_win, p_draw = outcome_probs(lam_own, lam_opp)
        xp, vp = 3 * p_win + p_draw, 9 * p_win + p_draw - (3 * p_win + p_draw) ** 2
        eps = 1e-4  # derivada numerica do xPts pro metodo delta
        d_own = (expected_points(lam_own * math.exp(eps), lam_opp)[0]
                 - expected_points(lam_own * math.exp(-eps), lam_opp)[0]) / (2 * eps)
        d_opp = (expected_points(lam_own, lam_opp * math.exp(eps))[0]
                 - expected_points(lam_own, lam_opp * math.exp(-eps))[0]) / (2 * eps)
        g_pts = xo_g.T @ d_own + xp_g.T @ d_opp
        var_pts = float(g_pts @ c2 @ g_pts)

        out.append((team, ref, len(own),
                    yc[own].sum(), mu_own.sum(), mu_own.sum() + var_own,
                    yc[opp].sum(), mu_opp.sum(), mu_opp.sum() + var_opp,
                    pts[own].sum(), xp.sum(), vp.sum() + var_pts, var_pts, inf.points_pmf(p_win, p_draw)))
    return pd.DataFrame(out, columns=PAIR_COLS)


def pair_tests(table: pd.DataFrame) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """(z, p) de cada par nas 3 analises, com teste exato (inference.count_test
    e points_test) -- nunca aproximacao normal de contagem pequena."""
    if table.empty:
        empty = np.zeros(0)
        return {k: (empty, empty) for k in ANALYSES}
    out = {"cards": inf.count_test(table.o_cards, table.e_cards, table.v_cards),
           "opp": inf.count_test(table.o_opp, table.e_opp, table.v_opp)}
    zp = [inf.points_test(o, pmf, ve) for o, pmf, ve in zip(table.o_pts, table.pmf_pts, table.ve_pts)]
    out["pts"] = (np.array([z for z, _ in zp]), np.array([p for _, p in zp]))
    return out


def pool_pairs(pairs: pd.DataFrame) -> pd.DataFrame:
    """Soma as temporadas do recorte por par; a distribuicao de pontos das
    temporadas se convolui (somas independentes)."""
    if pairs.empty:
        return pairs.reindex(columns=PAIR_COLS)
    g = pairs.groupby(["team", "ref"], sort=True)
    pooled = g[SUM_COLS].sum()
    pooled["pmf_pts"] = g.pmf_pts.agg(lambda s: reduce(np.convolve, s))
    return pooled.reset_index()


def _strong(table: pd.DataFrame, floor: int) -> dict[str, frozenset]:
    tested = table[table.n >= floor]
    tests = pair_tests(tested)
    out = {}
    for key in ANALYSES:
        hit = inf.bh_qvalues(tests[key][1]) <= inf.STRONG_Q if len(tested) else np.zeros(0, dtype=bool)
        out[key] = frozenset(zip(tested.team[hit], tested.ref[hit]))
    return out


def pair_table(rows: pd.DataFrame, floor: int = 3, max_rounds: int = 3) -> pd.DataFrame:
    """Busca progressiva (Atkinson & Riani, 2000): par com sinal forte vira
    termo proprio no modelo e tudo e recalculado, ate o conjunto parar de
    mudar -- um caso extremo nao pode contaminar o esperado de pares
    inocentes (nem vazar pro adversario de quem ele atinge)."""
    used = {k: frozenset() for k in ANALYSES}
    for _ in range(max_rounds):
        table = season_pair_table(rows, used)
        new = _strong(table, floor)
        if new == used:
            break
        used = new
    else:
        table = season_pair_table(rows, used)
    aside = set().union(*used.values())
    table["setAside"] = [(t, r) in aside for t, r in zip(table.team, table.ref)]
    return table


def pair_tables(rows: pd.DataFrame) -> pd.DataFrame:
    parts = [pair_table(g).assign(season=int(s)) for s, g in rows.groupby("season", sort=True)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=[*PAIR_COLS, "setAside", "season"])
