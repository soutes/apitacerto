"""Ferramentas de inferencia da aba Dados estatisticos (spec secao 9.2).

Funcoes puras (sem banco). Cada uma corresponde a um metodo citado na nota
que aparece embaixo do grafico no frontend -- se mudar aqui, mudar la.
"""
from __future__ import annotations

import math
import random
from collections import Counter
from typing import Callable

import numpy as np
from scipy import stats as st

Z95 = 1.959963984540054
Z998 = 3.090232306167813
STRONG_Q = 0.10  # Benjamini-Hochberg: "sinal forte" (spec 9.2)
WEAK_P = 0.01  # "sinal fraco -- acompanhar"


def two_sided_p(z) -> np.ndarray:
    return 2.0 * st.norm.sf(np.abs(np.asarray(z, dtype=float)))


def safe_z(diff, var) -> np.ndarray:
    """(O - E) / sqrt(V); variancia ~0 (nada a testar) vira z = 0."""
    diff = np.asarray(diff, dtype=float)
    var = np.asarray(var, dtype=float)
    ok = var > 1e-12
    return np.where(ok, diff / np.sqrt(np.where(ok, var, 1.0)), 0.0)


def bh_qvalues(p) -> np.ndarray:
    """q-valor de Benjamini & Hochberg (1995): controla a PROPORCAO de
    falsos alarmes entre os sinalizados, nao a chance de 1 alarme so."""
    p = np.asarray(p, dtype=float)
    m = len(p)
    if m == 0:
        return p
    order = np.argsort(p)
    scaled = p[order] * m / np.arange(1, m + 1)
    q_sorted = np.minimum.accumulate(scaled[::-1])[::-1]
    q = np.empty(m)
    q[order] = np.minimum(q_sorted, 1.0)
    return q


def evidence_level(p: float, q: float) -> str:
    """Regua fixada no pre-registro (spec 9.2)."""
    if q <= STRONG_Q:
        return "forte"
    if p < WEAK_P:
        return "fraco"
    return "acaso"


def poisson_ratio_ci(o, e, level: float = 0.95) -> tuple[np.ndarray, np.ndarray]:
    """IC exato da razao O/E de uma contagem de Poisson (Garwood, 1936)."""
    o = np.asarray(o, dtype=float)
    e = np.asarray(e, dtype=float)
    a = (1 - level) / 2
    lo = np.where(o > 0, st.chi2.ppf(a, np.maximum(2 * o, 1e-9)) / 2, 0.0)
    hi = st.chi2.ppf(1 - a, 2 * o + 2) / 2
    safe_e = np.where(e > 0, e, np.nan)
    return lo / safe_e, hi / safe_e


def gamma_poisson_shrink(o, e) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Encolhimento empirico-bayesiano da razao O/E (Efron & Morris, 1975;
    forma Gama-Poisson): quem tem pouco jogo e puxado pra media, na medida da
    propria incerteza. Devolve (encolhido, confiabilidade, tau2, media)."""
    o = np.asarray(o, dtype=float)
    e = np.asarray(e, dtype=float)
    if len(o) == 0:
        return o, o, 0.0, 1.0
    r = o / e
    w = e / e.sum()
    mean = float(np.sum(w * r))
    # variancia total das razoes - variancia que so a amostragem ja daria
    tau2 = max(0.0, float(np.sum(w * (r - mean) ** 2) - np.sum(w * mean / e)))
    if tau2 <= 0:
        return np.full_like(r, mean), np.zeros_like(r), 0.0, mean
    shape, rate = mean**2 / tau2, mean / tau2
    return (shape + o) / (rate + e), tau2 / (tau2 + mean / e), tau2, mean


def finite_population_d(total, n, pop_mean, pop_var, pop_n) -> tuple[np.ndarray, np.ndarray]:
    """Soma de n valores sorteados SEM reposicao de uma populacao de N
    (Cochran, 1977): D = soma - n*media; Var(D) = n*var*(N-n)/(N-1)."""
    total, n, pop_mean, pop_var, pop_n = (np.asarray(v, dtype=float) for v in (total, n, pop_mean, pop_var, pop_n))
    d = total - n * pop_mean
    var = np.where(pop_n > 1, n * pop_var * (pop_n - n) / np.maximum(pop_n - 1, 1), 0.0)
    return d, var


def count_test(o, e, v) -> tuple[np.ndarray, np.ndarray]:
    """Teste exato de uma contagem O contra o esperado E. Poisson; com
    incerteza no proprio esperado (V > E) vira Poisson-Gama = binomial
    negativa com media E e variancia V. A aproximacao normal subestima muito a
    cauda de contagem pequena (16 cartoes contra 7 esperados: p ~10x maior do
    que a normal diz) -- e foi o que a calibracao da spec 9.8 pegou. p exato
    convencional (inclui a massa do proprio O), nao mid-p: conservador de
    proposito, o produto pode expor pessoas. Devolve (z equivalente, p)."""
    o, e, v = (np.atleast_1d(np.asarray(a, dtype=float)) for a in (o, e, v))
    z, p = np.zeros(len(o)), np.ones(len(o))
    for i in range(len(o)):
        if e[i] <= 0:
            continue
        extra = v[i] - e[i]
        if extra > 1e-9:
            shape = e[i] ** 2 / extra
            dist = st.nbinom(shape, shape / (shape + e[i]))
        else:
            dist = st.poisson(e[i])
        k = round(o[i])
        p[i] = min(1.0, 2 * min(dist.cdf(k), dist.sf(k - 1)))  # P(X<=O), P(X>=O)
        z[i] = math.copysign(st.norm.isf(p[i] / 2), o[i] - e[i]) if p[i] < 1 else 0.0
    return z, p


def points_pmf(p_win, p_draw) -> np.ndarray:
    """Distribuicao exata da soma de pontos de n jogos: convolucao de cada
    jogo (0, 1 ou 3 pontos)."""
    pmf = np.array([1.0])
    for w, d in zip(np.atleast_1d(p_win), np.atleast_1d(p_draw)):
        pmf = np.convolve(pmf, [max(1.0 - w - d, 0.0), d, 0.0, w])
    return pmf


def points_test(o: float, pmf: np.ndarray, extra_var: float) -> tuple[float, float]:
    """Teste da soma de pontos contra a distribuicao exata do modelo, somada a
    um ruido normal com a incerteza do proprio esperado (sem incerteza: p
    exato convencional, conservador como o de contagem)."""
    s = np.arange(len(pmf))
    mean = float(s @ pmf)
    if extra_var > 1e-9:
        sd = math.sqrt(extra_var)
        upper = float(pmf @ st.norm.sf((o - s) / sd))
        lower = float(pmf @ st.norm.cdf((o - s) / sd))
    else:
        k = int(round(o))
        upper = float(pmf[s >= k].sum())
        lower = float(pmf[s <= k].sum())
    p = min(1.0, 2 * min(lower, upper))
    return (math.copysign(st.norm.isf(p / 2), o - mean) if p < 1 else 0.0), p


def funnel_ratio_lines(e_max: float, steps: int = 60, scale: float = 1.0) -> list[dict]:
    """Limites do grafico de funil (Spiegelhalter, 2005) pra razao O/E, pela
    aproximacao de Wilson-Hilferty (1931) da Poisson -- assimetricos como a
    propria contagem. scale > 1 quando a variancia inclui a incerteza do
    esperado (contagem efetiva E/scale^2)."""
    if not e_max or e_max <= 0:
        return []

    def limit(x: float, z: float) -> float:
        eff = x / scale**2
        return round(max(0.0, 1 - 1 / (9 * eff) + z / (3 * math.sqrt(eff))) ** 3, 4)

    xs = np.linspace(max(e_max / steps, 0.5), e_max, steps)
    return [{"x": round(float(x), 3), "lo95": limit(x, -Z95), "hi95": limit(x, Z95),
             "lo998": limit(x, -Z998), "hi998": limit(x, Z998)} for x in xs]


def funnel_mean_lines(n_min: int, n_max: int, sd_of_mean: Callable[[float], float]) -> list[dict]:
    """Mesmo funil, pra diferenca media por jogo com desvio sd_of_mean(n)."""
    out = []
    for n in range(max(1, n_min), n_max + 1):
        sd = sd_of_mean(n)
        if not math.isfinite(sd):
            continue
        out.append({"x": n, "lo95": round(-Z95 * sd, 4), "hi95": round(Z95 * sd, 4),
                    "lo998": round(-Z998 * sd, 4), "hi998": round(Z998 * sd, 4)})
    return out


def pearson_with_ci(x, y) -> dict | None:
    """Correlacao de Pearson com IC pela transformacao z de Fisher (1915)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    if n < 5 or np.std(x) == 0 or np.std(y) == 0:
        return None
    r = float(np.clip(np.corrcoef(x, y)[0, 1], -0.999999, 0.999999))
    z, se = math.atanh(r), 1 / math.sqrt(n - 3)
    return {"r": r, "lo": math.tanh(z - Z95 * se), "hi": math.tanh(z + Z95 * se),
            "p": float(two_sided_p(z / se)), "n": n}


def prob_repeat(k: int, p_one: float, both_directions: bool) -> float:
    """P(>= 2 de k temporadas com sinal na MESMA direcao) se cada temporada e
    independente e da sinal numa direcao com prob p_one (binomial)."""
    if k < 2:
        return 0.0
    at_least_two = 1 - (1 - p_one) ** k - k * p_one * (1 - p_one) ** (k - 1)
    return at_least_two * (2 if both_directions else 1)


def swap_null_samples(home_idx, away_idx, ref_idx, round_idx, same_uf, ref_cat, n_teams: int, n_refs: int, *,
                      stratify: bool, k: int = 200, burn: int = 40, thin: int = 5, seed: int = 0) -> np.ndarray:
    """Escalas sorteadas que respeitam as regras reais (Besag & Clifford,
    1989; Diaconis & Sturmfels, 1998). Troca o arbitro de 2 jogos da mesma
    temporada so se a troca mantem: (1) quantos jogos cada arbitro apitou;
    (2) no maximo 1 jogo por arbitro por rodada; (3) no maximo o numero de
    excecoes a regra de federacao que de fato aconteceram; e, se stratify,
    (4) a categoria do arbitro de cada jogo. Devolve K matrizes clube x
    arbitro (contagem de jogos), uma por sorteio."""
    rng = random.Random(seed)
    r = [int(v) for v in ref_idx]
    rounds = [int(v) for v in round_idx]
    m = len(r)
    if m < 2:
        return np.zeros((0, n_teams, n_refs))
    occ = Counter(zip(rounds, r))
    exceptions = sum(same_uf[r[i]][i] for i in range(m))
    max_exceptions = exceptions
    home_idx, away_idx = np.asarray(home_idx), np.asarray(away_idx)
    samples = []
    for sweep in range(burn + k * thin):
        for _ in range(m):
            i, j = rng.randrange(m), rng.randrange(m)
            ri, rj = r[i], r[j]
            if ri == rj or (stratify and ref_cat[ri] != ref_cat[rj]):
                continue
            ci, cj = rounds[i], rounds[j]
            if ci != cj and (occ[(ci, rj)] or occ[(cj, ri)]):
                continue
            delta = same_uf[rj][i] + same_uf[ri][j] - same_uf[ri][i] - same_uf[rj][j]
            if exceptions + delta > max_exceptions:
                continue
            if ci != cj:
                occ[(ci, ri)] -= 1
                occ[(cj, rj)] -= 1
                occ[(ci, rj)] += 1
                occ[(cj, ri)] += 1
            r[i], r[j] = rj, ri
            exceptions += delta
        if sweep >= burn and (sweep - burn) % thin == 0:
            mat = np.zeros((n_teams, n_refs))
            ra = np.asarray(r)
            np.add.at(mat, (home_idx, ra), 1)
            np.add.at(mat, (away_idx, ra), 1)
            samples.append(mat)
    return np.asarray(samples)
