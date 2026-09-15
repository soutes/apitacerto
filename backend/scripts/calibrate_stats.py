"""Calibracao dos testes par a par da aba Dados estatisticos (spec 9.8).

Simula ligas SEM nenhum favorecimento (nulo global) e conta quantas vezes o
metodo acusaria alguem. Pela regua pre-registrada (Benjamini-Hochberg,
q <= 0,10), 'algum sinal forte' numa analise deveria aparecer em no maximo
~10% das ligas; z dos pares deveria ter desvio ~1 e cauda |z| > 3 perto de
0,27%. Rodar de novo sempre que o metodo mudar.

Uso:
    uv run python scripts/calibrate_stats.py
"""
from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ no path

from app.analysis import inference as inf  # noqa: E402
from app.analysis import modeling, sections  # noqa: E402

warnings.simplefilter("ignore")


def schedule(teams):
    n, rot, rounds = len(teams), list(teams), []
    for _ in range(n - 1):
        rounds.append([(rot[i], rot[n - 1 - i]) for i in range(n // 2)])
        rot = [rot[0], rot[-1], *rot[1:-1]]
    return rounds + [[(b, a) for a, b in rnd] for rnd in rounds]


def league(rng, n_teams, n_refs, season=2023):
    """Liga sem nenhuma interacao clube x arbitro: forca, estilo e rigor
    variam como no dado real, mas ninguem favorece ninguem."""
    teams = [f"T{i:02d}" for i in range(n_teams)]
    refs = [f"R{i:02d}" for i in range(n_refs)]
    attack = dict(zip(teams, np.exp(rng.normal(0, 0.3, n_teams))))
    style = dict(zip(teams, np.exp(rng.normal(0, 0.1, n_teams))))
    strict = dict(zip(refs, np.exp(rng.normal(0, 0.13, n_refs))))
    cat = {r: "FIFA" if i % 3 == 0 else "MASTER" for i, r in enumerate(refs)}
    recs, fid = [], 0
    for rnd_i, rnd in enumerate(schedule(teams), start=1):
        chosen = rng.choice(refs, size=len(rnd), replace=False)
        for (h, a), ref in zip(rnd, chosen):
            fid += 1
            hs = rng.poisson(1.35 * attack[h] / attack[a] ** 0.8)
            as_ = rng.poisson(1.05 * attack[a] / attack[h] ** 0.8)
            hc = rng.poisson(2.5 * 0.92 * style[h] * strict[ref])
            ac = rng.poisson(2.5 * style[a] * strict[ref])
            for team, opp, home, gf, ga, c, oc in ((h, a, 1, hs, as_, hc, ac), (a, h, 0, as_, hs, ac, hc)):
                recs.append({"fid": fid, "season": season, "round": rnd_i, "team": team, "opp": opp, "home": home,
                             "ref": ref, "ref_cat": cat[ref], "gf": gf, "ga": ga, "cards": c, "opp_cards": oc,
                             "pts": 3 if gf > ga else (1 if gf == ga else 0)})
    return pd.DataFrame(recs)


def run(label, n_teams, n_refs, reps, seed, max_round=None):
    rng = np.random.default_rng(seed)
    keys = ("cards", "opp", "pts", "ease")
    any_strong = dict.fromkeys(keys, 0)
    zs = {k: [] for k in keys}
    started = time.time()
    for _ in range(reps):
        lg = league(rng, n_teams, n_refs)
        if max_round:
            lg = lg[lg["round"] <= max_round]
        tested = modeling.pair_table(lg).query("n >= 3")
        for k, (z, p) in modeling.pair_tests(tested).items():
            any_strong[k] += int((inf.bh_qvalues(p) <= inf.STRONG_Q).any())
            zs[k].extend(z)
        ease = sections.ease_analysis(modeling.fit_season(lg), 3)["points"]
        any_strong["ease"] += int(any(e["level"] == "forte" for e in ease))
        zs["ease"].extend(e["z"] for e in ease)
    print(f"{label}: {reps} ligas, {time.time() - started:.0f}s")
    for k in keys:
        z = np.array(zs[k], dtype=float)
        print(f"   {k:<5} ligas com algum 'forte': {any_strong[k]}/{reps} | DP(z) {z.std():.2f} | "
              f"|z|>1,96: {np.mean(np.abs(z) > 1.96):.1%} (~5%) | |z|>3: {np.mean(np.abs(z) > 3):.2%} (~0,27%)")


if __name__ == "__main__":
    run("liga pequena (8 clubes, 5 arbitros)", 8, 5, reps=30, seed=1)
    run("liga real (20 clubes, 25 arbitros)", 20, 25, reps=16, seed=2)
    run("comeco de temporada (20 clubes, 8 rodadas)", 20, 25, reps=20, seed=3, max_round=8)
    run("meio de temporada (20 clubes, 19 rodadas)", 20, 25, reps=30, seed=4, max_round=19)
