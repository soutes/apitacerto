"""Secoes da aba Dados estatisticos (spec secoes 9.3 e 9.4). Cada funcao
devolve um dict pronto pra JSON -- o frontend so desenha e explica."""
from __future__ import annotations

import math
import warnings
from collections import Counter

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats as st

from app.analysis import inference as inf
from app.analysis.data import MISSING_REF
from app.analysis.modeling import ANALYSES, pair_tests

REGION = {**{u: "Norte" for u in "AC AP AM PA RO RR TO".split()},
          **{u: "Nordeste" for u in "AL BA CE MA PB PE PI RN SE".split()},
          **{u: "Centro-Oeste" for u in "DF GO MT MS".split()},
          **{u: "Sudeste" for u in "ES MG RJ SP".split()},
          **{u: "Sul" for u in "PR RS SC".split()}}


def _f(x, nd: int = 3):
    """float JSON-safe: NaN/inf viram None."""
    if x is None:
        return None
    x = float(x)
    return round(x, nd) if math.isfinite(x) else None


def _with_ref(df: pd.DataFrame) -> pd.DataFrame:
    return df[df.ref != MISSING_REF]


def _evidence(z, p, q) -> dict:
    return {"z": _f(z, 2), "p": _f(p, 4), "q": _f(q, 4), "level": inf.evidence_level(float(p), float(q))}


def _summary(tested: pd.DataFrame) -> dict:
    n = len(tested)
    levels = Counter(inf.evidence_level(p, q) for p, q in zip(tested.p, tested.q)) if n else Counter()
    above95 = int((np.abs(tested.z) >= inf.Z95).sum()) if n else 0
    return {"tested": n, "strong": levels["forte"], "weak": levels["fraco"],
            "expectedWeakByChance": _f(inf.WEAK_P * n, 1),
            "above95": above95, "expectedAbove95": _f(0.05 * n, 1)}


def overview(f: pd.DataFrame, m: pd.DataFrame, floor: int) -> dict:
    pairs = _with_ref(f).groupby(["team", "ref"]).size()
    tested = pairs[pairs >= floor]
    return {"matches": int(len(m)), "matchesWithReferee": int((m.ref != MISSING_REF).sum()),
            "teams": int(f.team.nunique()), "referees": int(_with_ref(f).ref.nunique()),
            "pairs": int(len(pairs)), "pairsTested": int(len(tested)), "floor": floor,
            "medianPairGames": _f(pairs.median(), 1) if len(pairs) else 0,
            "maxPairGames": int(pairs.max()) if len(pairs) else 0,
            "teamGamesCoveredPct": _f(tested.sum() / pairs.sum() * 100, 1) if len(pairs) else 0}


# ---------------------------------------------------------------- A1-A3
def pair_analysis(pooled: pd.DataFrame, analysis: str, floor: int) -> dict:
    """Par clube x arbitro: observado vs esperado (esperado sem os jogos do
    proprio par -- modeling.season_pair_table), somado nas temporadas do
    recorte (modeling.pool_pairs). Teste exato, nao normal."""
    obs, exp, var = ANALYSES[analysis]
    kind = "mean" if analysis == "pts" else "count"
    sel = pooled[pooled.n >= floor]
    tested = sel[["team", "ref", "n"]].assign(o=sel[obs], e=sel[exp], v=sel[var])
    if tested.empty:
        return {"floor": floor, "points": [], "funnel": [], "summary": _summary(tested)}
    z, p = pair_tests(sel)[analysis]
    tested["z"], tested["p"] = z, p
    tested["q"] = inf.bh_qvalues(tested.p)
    points = [{"team": r.team, "referee": r.ref, "n": int(r.n), "observed": _f(r.o, 2), "expected": _f(r.e, 2),
               "ratio": _f(r.o / r.e) if r.e > 0 else None, "perGame": _f((r.o - r.e) / r.n),
               **_evidence(r.z, r.p, r.q)}
              for r in tested.itertuples(index=False)]
    points.sort(key=lambda d: -abs(d["z"] or 0))
    if kind == "count":
        # a variancia inclui a incerteza do esperado: funil um pouco mais largo que o de Poisson puro
        inflation = float(np.median(tested.v / tested.e.clip(lower=1e-9)))
        funnel = inf.funnel_ratio_lines(float(tested.e.max()), scale=math.sqrt(max(inflation, 1.0)))
    else:
        sigma = math.sqrt(float(np.median(tested.v / tested.n)))
        funnel = inf.funnel_mean_lines(int(tested.n.min()), int(tested.n.max()), lambda n: sigma / math.sqrt(n))
    return {"floor": floor, "points": points, "funnel": funnel, "summary": _summary(tested)}


# ---------------------------------------------------------------- A4
def ease_analysis(f: pd.DataFrame, floor: int) -> dict:
    """Escala favoravel: os jogos do clube apitados por aquele arbitro sao
    mais 'faceis' (xPts maior) do que um sorteio sem reposicao entre os
    jogos do clube na temporada daria? Versao 2 sorteia so entre os jogos
    apitados por arbitros da MESMA categoria (a CBF escala FIFA pra jogo
    grande -- sem isso, categoria vira falso sinal)."""
    f = _with_ref(f)
    x = "xpts"
    ts = f.groupby(["season", "team"])[x].agg(N="size", mu="mean", var=lambda s: s.var(ddof=0))
    pair = (f.groupby(["season", "team", "ref"]).agg(n=("fid", "size"), s=(x, "sum")).reset_index()
             .join(ts, on=["season", "team"]))
    pair["D"], pair["VD"] = inf.finite_population_d(pair.s, pair.n, pair.mu, pair["var"], pair.N)

    tc = f.groupby(["season", "team", "ref_cat"])[x].agg(Nc="size", muc="mean", varc=lambda s: s.var(ddof=0))
    pc = (f.groupby(["season", "team", "ref", "ref_cat"]).agg(nc=("fid", "size"), sc=(x, "sum")).reset_index()
           .join(tc, on=["season", "team", "ref_cat"]))
    pc["Dc"], pc["VDc"] = inf.finite_population_d(pc.sc, pc.nc, pc.muc, pc.varc, pc.Nc)
    pair = pair.join(pc.groupby(["season", "team", "ref"])[["Dc", "VDc"]].sum(), on=["season", "team", "ref"])

    agg = (pair.groupby(["team", "ref"])
           .agg(n=("n", "sum"), s=("s", "sum"), D=("D", "sum"), VD=("VD", "sum"), Dc=("Dc", "sum"), VDc=("VDc", "sum"))
           .reset_index())
    tested = agg[agg.n >= floor].copy()
    if tested.empty:
        return {"floor": floor, "points": [], "funnel": [], "summary": _summary(tested)}
    tested["z"] = inf.safe_z(tested.D, tested.VD)
    tested["p"] = inf.two_sided_p(tested.z)
    tested["q"] = inf.bh_qvalues(tested.p)
    has_c = tested.VDc > 1e-12
    tested["zc"] = np.where(has_c, inf.safe_z(tested.Dc, tested.VDc), np.nan)
    tested["pc"] = np.where(has_c, inf.two_sided_p(tested.zc.fillna(0)), np.nan)
    tested["qc"] = np.nan
    if has_c.any():
        tested.loc[has_c, "qc"] = inf.bh_qvalues(tested.loc[has_c, "pc"])

    points = []
    for r in tested.itertuples(index=False):
        cat = (_evidence(r.zc, r.pc, r.qc) if math.isfinite(r.zc)
               else {"z": None, "p": None, "q": None, "level": "sem comparação"})
        points.append({"team": r.team, "referee": r.ref, "n": int(r.n),
                       "easeWithReferee": _f(r.s / r.n), "easeTeam": _f((r.s - r.D) / r.n),
                       "perGame": _f(r.D / r.n), **_evidence(r.z, r.p, r.q),
                       "sameCategory": cat})
    points.sort(key=lambda d: -abs(d["z"] or 0))
    sigma = math.sqrt(float(ts["var"].median()))
    big_n = float(ts.N.median())
    funnel = inf.funnel_mean_lines(
        int(tested.n.min()), int(min(tested.n.max(), big_n - 1)),
        lambda n: sigma * math.sqrt(max(big_n - n, 0) / ((big_n - 1) * n)))
    return {"floor": floor, "points": points, "funnel": funnel, "summary": _summary(tested)}


# ---------------------------------------------------------------- A5
def cross_season(pairs: pd.DataFrame) -> dict:
    """Mesmo arbitro x mesmo clube em temporadas diferentes."""
    per = pairs[pairs.n >= 2].copy()
    if per.empty:
        return {"available": False}
    tests = pair_tests(per)
    z1, z2, z3 = tests["cards"][0], tests["opp"][0], tests["pts"][0]
    fav = (-z1 + z2 + z3) / math.sqrt(3)
    per["favor"] = fav / (np.std(fav) or 1.0)  # padroniza: os componentes nao sao independentes
    per["harsh"] = z1

    scatter, xs, ys = [], [], []
    for (team, ref), g in per.groupby(["team", "ref"]):
        by_season = dict(zip(g.season, g.favor))
        for s, v in sorted(by_season.items()):
            if s + 1 in by_season:
                xs.append(v)
                ys.append(by_season[s + 1])
                scatter.append({"team": team, "referee": ref, "season": int(s),
                                "x": _f(v, 2), "y": _f(by_season[s + 1], 2)})
    corr = inf.pearson_with_ci(xs, ys)

    def repeats(col: str, both: bool) -> dict:
        obs, expected, rows = 0, 0.0, []
        for (team, ref), g in per.groupby(["team", "ref"]):
            expected += inf.prob_repeat(len(g), 0.025, both)
            up = g[g[col] >= inf.Z95]
            down = g[g[col] <= -inf.Z95] if both else g.iloc[0:0]
            for side_rows, direction in ((up, "+"), (down, "-")):
                if len(side_rows) >= 2:
                    obs += 1
                    rows.append({"team": team, "referee": ref, "direction": direction,
                                 "seasons": [{"season": int(s), "z": _f(z, 2), "n": int(n)}
                                             for s, z, n in zip(side_rows.season, side_rows[col], side_rows.n)]})
        p = float(st.poisson.sf(obs - 1, expected)) if obs > 0 and expected > 0 else 1.0
        return {"observed": obs, "expected": _f(expected, 2), "p": _f(p, 4), "pairs": rows}

    return {"available": True, "pairSeasons": int(len(per)),
            "correlation": {k: _f(v, 3) for k, v in corr.items()} if corr else None,
            "scatter": scatter, "favorRepeats": repeats("favor", True), "harshRepeats": repeats("harsh", False)}


# ---------------------------------------------------------------- L1-L2
def _mean_ci(x: pd.Series) -> tuple[float, float, float]:
    n = len(x)
    if n < 2:
        return float(x.mean()), float("nan"), float("nan")
    half = st.t.ppf(0.975, n - 1) * x.std(ddof=1) / math.sqrt(n)
    return float(x.mean()), float(x.mean() - half), float(x.mean() + half)


def league_baseline(m: pd.DataFrame) -> dict:
    out = []
    for s, g in m.groupby("season", sort=True):
        c, clo, chi = _mean_ci(g.h_cards - g.a_cards)
        p, plo, phi = _mean_ci(g.h_pen - g.a_pen)
        res = np.sign(g.hs - g.as_)
        out.append({"season": int(s), "matches": int(len(g)),
                    "homeCards": _f(g.h_cards.mean(), 2), "awayCards": _f(g.a_cards.mean(), 2),
                    "cardsDiff": _f(c), "cardsDiffCi": [_f(clo), _f(chi)],
                    "pensDiff": _f(p), "pensDiffCi": [_f(plo), _f(phi)],
                    "homeWinPct": _f((res > 0).mean() * 100, 1), "drawPct": _f((res == 0).mean() * 100, 1),
                    "awayWinPct": _f((res < 0).mean() * 100, 1)})
    return {"seasons": out}


def referee_strictness(f: pd.DataFrame, floor_games: int) -> dict:
    """Rigor = cartoes observados / esperados pelos clubes e mando daqueles
    jogos (sem o arbitro no modelo), com encolhimento empirico-bayesiano.
    Vies de mandante do arbitro = residuo do modelo COM arbitro nos jogos
    dele, mandante menos visitante -- ja descontada a media da liga."""
    f = _with_ref(f)
    g = f.groupby("ref").agg(rows=("fid", "size"), o=("cards", "sum"), e=("mu_noref", "sum")).reset_index()
    g["games"] = g.rows // 2
    elig = g[g.games >= floor_games].copy()
    if elig.empty:
        return {"floorGames": floor_games, "referees": [], "tau": None, "typicalReliability": None}
    shrunk, rel, tau2, _ = inf.gamma_poisson_shrink(elig.o, elig.e)
    lo, hi = inf.poisson_ratio_ci(elig.o, elig.e)
    elig["z"] = inf.safe_z(elig.o - elig.e, elig.e)
    elig["p"] = inf.two_sided_p(elig.z)
    elig["q"] = inf.bh_qvalues(elig.p)

    resid = f.assign(r=(f.cards - f.mu_cards) * np.where(f.home == 1, 1.0, -1.0))
    hb = resid.groupby("ref").agg(d=("r", "sum"), v=("mu_cards", "sum")).reindex(elig.ref)
    elig["hb_z"] = inf.safe_z(hb.d.to_numpy(), hb.v.to_numpy())
    elig["hb_p"] = inf.two_sided_p(elig.hb_z)
    elig["hb_q"] = inf.bh_qvalues(elig.hb_p)
    elig["hb_per_game"] = hb.d.to_numpy() / elig.games.to_numpy()

    refs = []
    for i, r in enumerate(elig.itertuples(index=False)):
        refs.append({"referee": r.ref, "games": int(r.games), "observed": int(r.o), "expected": _f(r.e, 1),
                     "ratio": _f(r.o / r.e), "ci": [_f(lo[i]), _f(hi[i])], "shrunk": _f(shrunk[i]),
                     "reliability": _f(rel[i], 2), **_evidence(r.z, r.p, r.q),
                     "homeBias": {"perGame": _f(r.hb_per_game), **_evidence(r.hb_z, r.hb_p, r.hb_q)}})
    refs.sort(key=lambda d: -(d["shrunk"] or 0))
    median_e = float(elig.e.median())
    return {"floorGames": floor_games, "referees": refs, "tau": _f(math.sqrt(tau2)),
            "typicalReliability": _f(tau2 / (tau2 + 1 / median_e), 2) if tau2 else 0.0}


# ---------------------------------------------------------------- E1-E3
def federation(m: pd.DataFrame) -> dict:
    """% de jogos com arbitro da UF de um dos clubes vs sorteio no pool da
    temporada (cada arbitro pesando pelo tanto que apitou)."""
    out, tot_n, tot_obs, tot_exp = [], 0, 0, 0.0
    for s, g in _with_ref(m).groupby("season", sort=True):
        k = g[g.ref_uf.notna() & g.home_state.notna() & g.away_state.notna()]
        if k.empty:
            continue
        obs = (k.ref_uf == k.home_state) | (k.ref_uf == k.away_state)
        pool = k.ref_uf.value_counts(normalize=True)
        exp = [pool.get(h, 0.0) + (pool.get(a, 0.0) if a != h else 0.0) for h, a in zip(k.home_state, k.away_state)]
        out.append({"season": int(s), "matches": int(len(k)), "observedCount": int(obs.sum()),
                    "observedPct": _f(obs.mean() * 100, 1), "expectedPct": _f(np.mean(exp) * 100, 1)})
        tot_n, tot_obs, tot_exp = tot_n + len(k), tot_obs + int(obs.sum()), tot_exp + float(np.sum(exp))
    total = ({"matches": tot_n, "observedCount": tot_obs, "observedPct": _f(tot_obs / tot_n * 100, 1),
              "expectedPct": _f(tot_exp / tot_n * 100, 1)} if tot_n else None)
    return {"seasons": out, "total": total}


def _ranks(g: pd.DataFrame) -> dict[str, int]:
    pts, gd = Counter(), Counter()
    for h, a, hs, as_ in zip(g.home, g.away, g.hs, g.as_):
        pts[h] += 3 if hs > as_ else (1 if hs == as_ else 0)
        pts[a] += 3 if as_ > hs else (1 if hs == as_ else 0)
        gd[h] += hs - as_
        gd[a] += as_ - hs
    table = sorted(pts, key=lambda t: (-pts[t], -gd[t], t))
    return {t: i + 1 for i, t in enumerate(table)}


def category_importance(m: pd.DataFrame) -> dict:
    parts = []
    for _, g in m.groupby("season"):
        rk = _ranks(g)  # classificacao usa TODOS os jogos, com ou sem arbitro conhecido
        parts.append(g.assign(hr=g.home.map(rk), ar=g.away.map(rk)))
    d = _with_ref(pd.concat(parts)) if parts else m
    if d.empty:
        return {"groups": [], "fifaSharePct": None}
    fifa = d.ref_cat.fillna("").str.contains("FIFA")
    groups = {"Dois clubes do top-6": (d.hr <= 6) & (d.ar <= 6),
              "Clássico estadual (mesma UF)": d.home_state.notna() & (d.home_state == d.away_state),
              "Dois clubes do 13º ao 20º": (d.hr >= 13) & (d.ar >= 13)}
    out = []
    for label, mask in groups.items():
        a, n_in = int(fifa[mask].sum()), int(mask.sum())
        c, n_out = int(fifa[~mask].sum()), int((~mask).sum())
        if n_in == 0 or n_out == 0:
            continue
        _, p = st.fisher_exact([[a, n_in - a], [c, n_out - c]])
        out.append({"group": label, "matches": n_in, "fifaPct": _f(a / n_in * 100, 1),
                    "restPct": _f(c / n_out * 100, 1), "p": _f(p, 5)})
    return {"groups": out, "fifaSharePct": _f(fifa.mean() * 100, 1)}


def concentration_inputs(ms: pd.DataFrame, seed: int) -> dict:
    """Sorteios nulos de UMA temporada (caro: roda uma vez e reusa)."""
    ms = _with_ref(ms)
    teams = sorted(set(ms.home) | set(ms.away))
    refs = sorted(set(ms.ref))
    ti = {t: i for i, t in enumerate(teams)}
    ri = {r: i for i, r in enumerate(refs)}
    ref_uf = ms.groupby("ref").ref_uf.agg(lambda s: s.dropna().mode().iat[0] if s.notna().any() else None)
    ref_cat = ms.groupby("ref").ref_cat.agg(lambda s: s.mode().iat[0])
    h, a = ms.home.map(ti).to_numpy(), ms.away.map(ti).to_numpy()
    r0 = ms.ref.map(ri).to_numpy()
    hs, as_ = ms.home_state.to_numpy(), ms.away_state.to_numpy()
    same_uf = [[int(ref_uf[r] is not None and ref_uf[r] in (hs[i], as_[i])) for i in range(len(ms))] for r in refs]
    cats = [ref_cat[r] for r in refs]
    obs = np.zeros((len(teams), len(refs)))
    np.add.at(obs, (h, r0), 1)
    np.add.at(obs, (a, r0), 1)
    common = dict(home_idx=h, away_idx=a, ref_idx=r0, round_idx=ms["round"].to_numpy(), same_uf=same_uf,
                  ref_cat=cats, n_teams=len(teams), n_refs=len(refs))
    return {"teams": teams, "refs": refs, "obs": obs,
            "plain": inf.swap_null_samples(**common, stratify=False, seed=seed),
            "category": inf.swap_null_samples(**common, stratify=True, seed=seed + 1)}


def concentration(parts: list[dict]) -> dict:
    """Concentracao clube x arbitro vs os sorteios com regras (E3). Varias
    temporadas: soma as matrizes (temporadas sao sorteadas independentes)."""
    teams = sorted({t for p in parts for t in p["teams"]})
    refs = sorted({r for p in parts for r in p["refs"]})
    ti, ri = {t: i for i, t in enumerate(teams)}, {r: i for i, r in enumerate(refs)}
    out = {}
    for variant in ("plain", "category"):
        usable = [p for p in parts if len(p[variant])]
        k = min((len(p[variant]) for p in usable), default=0)
        if k == 0:
            out[variant] = None
            continue
        obs = np.zeros((len(teams), len(refs)))
        null = np.zeros((k, len(teams), len(refs)))
        for p in usable:
            tix = np.array([ti[t] for t in p["teams"]])
            rix = np.array([ri[r] for r in p["refs"]])
            obs[np.ix_(tix, rix)] += p["obs"]
            null[:, tix[:, None], rix[None, :]] += p[variant][:k]
        e, sd = null.mean(0), null.std(0)
        act = e > 0.05
        x2_obs = float(np.sum((obs[act] - e[act]) ** 2 / e[act]))
        x2_null = np.array([np.sum((q[act] - e[act]) ** 2 / e[act]) for q in null])
        safe_sd = np.where(sd > 0, sd, 1.0)
        z = np.where(act & (sd > 0), (obs - e) / safe_sd, 0.0)
        z_null_count = float(np.mean([np.sum(np.where(act & (sd > 0), (q - e) / safe_sd, 0.0) > 3) for q in null]))
        over = act & (obs > e)
        cells = np.argwhere(over)
        pvals = st.poisson.sf(obs[over] - 1, e[over])  # conservador: variancia de Poisson > a do sorteio
        qvals = inf.bh_qvalues(pvals)
        rows = [{"team": teams[t], "referee": refs[r], "observed": int(obs[t, r]),
                 "expected": _f(e[t, r], 1), "ratio": _f(obs[t, r] / e[t, r], 2), **_evidence(z[t, r], p, q)}
                for (t, r), p, q in zip(cells, pvals, qvals)]
        rows.sort(key=lambda d: -(d["z"] or 0))
        out[variant] = {"x2": _f(x2_obs, 1), "x2Null": _f(x2_null.mean(), 1),
                        "x2NullRange": [_f(np.percentile(x2_null, 2.5), 1), _f(np.percentile(x2_null, 97.5), 1)],
                        "p": _f((1 + np.sum(x2_null >= x2_obs)) / (k + 1), 4),
                        "excessPct": _f((x2_obs / x2_null.mean() - 1) * 100, 1) if x2_null.mean() else None,
                        "cellsZ3": int(np.sum(z > 3)), "cellsZ3Null": _f(z_null_count, 1),
                        "samples": int(k), "top": rows[:15],
                        "strong": sum(1 for d in rows if d["level"] == "forte")}
    return out


# ---------------------------------------------------------------- H1-H4
def _fit_cluster(formula: str, data: pd.DataFrame, poisson: bool):
    """Erro-padrao robusto agrupado por jogo: os dois lados do mesmo jogo
    nao sao observacoes independentes."""
    groups = pd.factorize(data.fid)[0]
    kw = {"cov_type": "cluster", "cov_kwds": {"groups": groups}}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if poisson:
            return smf.glm(formula, data=data, family=sm.families.Poisson()).fit(**kw)
        return smf.ols(formula, data=data).fit(**kw)


def _estimate(model, term: str, ratio: bool) -> dict:
    b = float(model.params[term])
    lo, hi = (float(v) for v in model.conf_int().loc[term])
    if ratio:
        b, lo, hi = math.exp(b), math.exp(lo), math.exp(hi)
    return {"estimate": _f(b), "ci": [_f(lo), _f(hi)], "p": _f(float(model.pvalues[term]), 4)}


def _verdict(est: dict, predicted_above: bool, null_value: float, alpha: float) -> str:
    if est.get("p") is None or est.get("estimate") is None:
        return "sem dado"
    if est["p"] >= alpha:
        return "sem evidência"
    return "apoia" if (est["estimate"] > null_value) == predicted_above else "contraria"


def _no_estimate(reason: str) -> dict:
    return {"estimate": None, "ci": [None, None], "p": None, "note": reason}


def _varying(data: pd.DataFrame, terms: list[str]) -> list[str]:
    # regressor sem variacao (ex.: nenhum arbitro da regiao) deixa a matriz singular
    return [t for t in terms if data[t].nunique() > 1]


def hypotheses(f: pd.DataFrame, closed_seasons: list[int]) -> list[dict]:
    """H1-H4 pre-registradas (spec 9.4). So temporadas encerradas: veredito
    oficial nao pode mudar toda semana com o cron (spec 9.2)."""
    d = f[f.season.isin(closed_seasons)].copy()
    d["ts"] = d.team + "_" + d.season.astype(str)
    seasons_txt = f"{min(closed_seasons)}–{max(closed_seasons)}" if closed_seasons else "—"
    base = "C(ts) + C(opp) + C(ref) + home"
    out = []

    # H1 -- afinidade regional (4 medidas; emenda 2026-09-14: Bonferroni dentro da hipotese)
    k = d[d.ref_uf.notna() & d.team_state.notna() & d.opp_state.notna()].copy()
    alpha1 = 0.05 / 4
    h1 = {"id": "H1", "title": "Afinidade regional",
          "prediction": "Clube leva menos cartão e faz mais ponto quando o árbitro é da mesma região "
                        "(de outro estado); o contrário quando é da região do adversário.",
          "status": "Já olhada no diagnóstico de 14/09 — registrada, mas não conta como confirmação independente.",
          "seasons": seasons_txt, "measures": [], "alpha": alpha1}
    specs = (("reg_T", "Cartões ao clube, árbitro da região do clube (razão)", True, True, False, 1.0),
             ("reg_T", "Pontos do clube, árbitro da região do clube (por jogo)", False, False, True, 0.0),
             ("reg_O", "Cartões ao clube, árbitro da região do adversário (razão)", True, True, True, 1.0),
             ("reg_O", "Pontos do clube, árbitro da região do adversário (por jogo)", False, False, False, 0.0))
    if len(k) >= 200:
        reg = k.ref_uf.map(REGION)
        k["reg_T"] = ((reg == k.team_state.map(REGION)) & (k.ref_uf != k.team_state)).astype(int)
        k["reg_O"] = ((reg == k.opp_state.map(REGION)) & (k.ref_uf != k.opp_state)).astype(int)
        k["st_T"] = (k.ref_uf == k.team_state).astype(int)
        k["st_O"] = (k.ref_uf == k.opp_state).astype(int)
        terms = _varying(k, ["reg_T", "reg_O", "st_T", "st_O"])
        rhs = " + ".join([base, *terms])
        models = {}
        for poisson in (True, False):
            try:
                models[poisson] = _fit_cluster(f"{'cards' if poisson else 'pts'} ~ {rhs}", k, poisson)
            except (np.linalg.LinAlgError, ValueError):
                models[poisson] = None
        for term, label, poisson, ratio, above, null in specs:
            if term not in terms:
                est = _no_estimate("sem variação: nenhum jogo nessa condição")
            elif models[poisson] is None:
                est = _no_estimate("modelo não ajustou")
            else:
                est = _estimate(models[poisson], term, ratio)
            h1["measures"].append({"label": label, "null": null, **est, "verdict": _verdict(est, above, null, alpha1)})
        h1["n"] = int(k.fid.nunique())
    else:
        h1["missing"] = True
    out.append(h1)

    def single(hid, title, prediction, status, data, flag, formula, term, label):
        h = {"id": hid, "title": title, "prediction": prediction, "status": status, "seasons": seasons_txt,
             "measures": [], "alpha": 0.05}
        if data.empty or data[flag].nunique() < 2:
            h["missing"] = True
            return h
        try:
            est = _estimate(_fit_cluster(formula, data, True), term, True)
        except (np.linalg.LinAlgError, ValueError):
            est = _no_estimate("modelo não ajustou")
        # as tres preveem razao > 1: efeito mandante 'menos favoravel' na condicao
        h["measures"].append({"label": label, "null": 1.0, **est, "verdict": _verdict(est, True, 1.0, 0.05)})
        h["n"] = int(data.fid.nunique())
        return h

    d["y2020"] = (d.season == 2020).astype(int)
    out.append(single(
        "H2", "Pressão da torcida (2020 sem público)",
        "A vantagem do mandante em cartões (mandante leva menos) é menor em 2020, temporada sem público.",
        "Registrada antes de ingerir 2018–2021.", d, "y2020",
        f"cards ~ {base} + home:y2020", "home:y2020", "Efeito mandante em 2020 ÷ demais temporadas (razão)"))

    # so jogo com categoria publicada: o Transfermarkt (2007-2017) nao traz a
    # categoria, e sem isso todo arbitro FIFA daquela epoca contaria como nao-FIFA
    d3 = d[(d.ref != MISSING_REF) & (d.ref_cat.fillna("") != "")].copy()
    d3["fifa"] = d3.ref_cat.fillna("").str.contains("FIFA").astype(int)
    out.append(single(
        "H3", "Categoria sob pressão (árbitro FIFA)",
        "O viés de mandante em cartões é menor com árbitro FIFA.",
        "Estimativa pontual vista no diagnóstico (especificação colinear, descartada) — registrada com a nova.",
        d3, "fifa", f"cards ~ {base} + home:fifa", "home:fifa", "Efeito mandante com FIFA ÷ sem FIFA (razão)"))

    d["pre_var"] = (d.season <= 2018).astype(int)  # VAR chegou a Serie A em 2019
    out.append(single(
        "H4", "VAR e pênaltis",
        "A vantagem do mandante em gols de pênalti é menor com VAR (2019+) do que sem (até 2018).",
        "Registrada antes de ingerir 2018; ampliada para 2007–2018 com os dados do Transfermarkt.", d, "pre_var",
        f"pen ~ {base} + home:pre_var", "home:pre_var", "Efeito mandante em pênaltis sem VAR ÷ com VAR (razão)"))
    return out
