"""Motor da aba Dados estatisticos (spec secao 9) -- sem rede, sem banco real.

Liga sintetica em TAMANHO REAL (20 clubes, 38 rodadas) com dois efeitos
PLANTADOS: um arbitro implicante com um clube e um arbitro que sempre pega os
jogos faceis de outro clube. O metodo tem que achar exatamente o que foi
plantado e nao acusar inocente. (Uma liga de 8 clubes foi usada antes e
mostrou que o metodo quebra com amostra minuscula -- ver calibracao na spec
9.8; tamanho real e o que representa o dado.)
"""
import itertools
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.analysis import inference as inf
from app.analysis import modeling
from app.analysis.data import load_matches, team_rows
from app.analysis.report import build_reports, compute_and_store
from app.db import Base, ensure_schema
from app.main import app
from app.models import Fixture, MatchEvent, Referee, Team

client = TestClient(app)

TEAMS = [f"Time {c}" for c in "ABCDEFGHIJKLMNOPQRST"]
WEAK = set(TEAMS[-5:])
REFS = [f"Ref {i:02d}" for i in range(1, 19)]
ALL_REFS = [*REFS, "Arbitro Implicante", "Arbitro Facil"]
FIFA = {*REFS[:6], "Arbitro Implicante", "Arbitro Facil"}
PLANTED = ("Time A", "Arbitro Implicante")


def _schedule(teams):
    """Turno e returno, todos contra todos (metodo do circulo)."""
    n, rot, rounds = len(teams), list(teams), []
    for _ in range(n - 1):
        rounds.append([(rot[i], rot[n - 1 - i]) for i in range(n // 2)])
        rot = [rot[0], rot[-1], *rot[1:-1]]
    return rounds + [[(b, a) for a, b in rnd] for rnd in rounds]


def _seed_league(db, season=2024, seed=7):
    rng = np.random.default_rng(seed)
    teams = {t: Team(api_id=i, name=t, state="SP" if i % 2 else "RJ") for i, t in enumerate(TEAMS)}
    refs = {r: Referee(name=r, uf="MG") for r in ALL_REFS}
    db.add_all([*teams.values(), *refs.values()])
    db.flush()
    attack = {t: 1.6 if t == "Time B" else 0.55 if t in WEAK else float(np.exp(rng.normal(0, 0.15))) for t in TEAMS}
    style = {t: float(np.exp(rng.normal(0, 0.1))) for t in TEAMS}
    strict = {r: float(np.exp(rng.normal(0, 0.12))) for r in ALL_REFS}
    api_id = 0
    for rnd_i, rnd in enumerate(_schedule(TEAMS), start=1):
        assigned = {}
        for h, a in rnd:
            if "Time B" in (h, a) and {h, a} & WEAK:
                assigned[(h, a)] = "Arbitro Facil"  # plantado 2: escala favoravel
            elif "Time A" in (h, a) and rnd_i % 5 == 0:
                assigned[(h, a)] = "Arbitro Implicante"
        free = list(rng.permutation([r for r in ALL_REFS if r not in assigned.values()]))
        for h, a in rnd:
            ref = assigned.get((h, a)) or free.pop()
            api_id += 1
            fx = Fixture(source="cbf", api_id=api_id, season=season, round=str(rnd_i),
                         home_team_id=teams[h].id, away_team_id=teams[a].id, referee_id=refs[ref].id,
                         referee_category="FIFA-PRO" if ref in FIFA else "MASTER-PRO",
                         home_score=int(rng.poisson(1.3 * attack[h] / attack[a] ** 0.8)),
                         away_score=int(rng.poisson(1.0 * attack[a] / attack[h] ** 0.8)),
                         events_ingested=True)
            db.add(fx)
            db.flush()
            for side in (h, a):
                lam = 2.5 * style[side] * strict[ref] * (0.92 if side == h else 1.0)
                if (side, ref) == PLANTED:
                    lam *= 2.6  # plantado 1: implicancia
                for _ in range(int(rng.poisson(lam))):
                    db.add(MatchEvent(fixture_id=fx.id, team_id=teams[side].id, type="YELLOW_CARD"))
    db.commit()


@pytest.fixture(scope="module")
def league():
    """Liga montada e analisada uma vez so por modulo (build leva segundos)."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        _seed_league(db)
        return {"reports": build_reports(db), "rows": team_rows(load_matches(db))}


# ------------------------------------------------------------ inferencia pura
def test_bh_qvalues_matches_hand_computation():
    # ordenado: .01 .03 .04 .20 -> p*m/posto = .04 .06 .0533 .20 -> minimo acumulado de tras pra frente
    assert inf.bh_qvalues([0.01, 0.04, 0.03, 0.20]) == pytest.approx([0.04, 0.16 / 3, 0.16 / 3, 0.20])


def test_evidence_levels_follow_preregistered_thresholds():
    assert inf.evidence_level(0.0001, 0.05) == "forte"
    assert inf.evidence_level(0.005, 0.30) == "fraco"
    assert inf.evidence_level(0.03, 0.60) == "acaso"


def test_finite_population_variance_matches_full_enumeration():
    pop = np.array([1.0, 2.0, 3.0, 4.0])
    d, var = inf.finite_population_d(7.0, 2, pop.mean(), pop.var(), 4)
    sums = [a + b for a, b in itertools.combinations(pop, 2)]
    assert d == pytest.approx(7.0 - 2 * 2.5)
    assert var == pytest.approx(np.var(sums))  # sorteio SEM reposicao, exato


def test_shrinkage_pulls_small_samples_harder():
    o, e = np.array([30.0, 10.0, 4.0, 1.0]), np.array([20.0, 20.0, 2.0, 2.0])
    shrunk, rel, tau2, mean = inf.gamma_poisson_shrink(o, e)
    raw = o / e
    assert tau2 > 0
    kept = (shrunk - mean) / (raw - mean)  # fracao do desvio que sobra
    assert kept[0] == pytest.approx(rel[0]) and kept[2] == pytest.approx(rel[2])
    assert rel[0] > rel[2]  # 20 cartoes esperados pesam mais que 2


def test_count_test_uses_exact_poisson_tail():
    # 16 cartoes contra 7 esperados: cauda exata (mid-p) ~0,0017; a normal diria 0,0003
    _, p = inf.count_test([16], [7.0], [7.0])
    assert 0.001 < p[0] / 2 < 0.004
    _, p_uncertain = inf.count_test([16], [7.0], [14.0])  # esperado incerto: menos evidencia
    assert p_uncertain[0] > p[0]


def test_points_distribution_is_exact_convolution():
    pmf = inf.points_pmf([0.5, 0.5], [0.2, 0.2])
    assert len(pmf) == 7 and pmf.sum() == pytest.approx(1.0)
    assert pmf[6] == pytest.approx(0.25) and pmf[0] == pytest.approx(0.09)  # 2 vitorias / 2 derrotas
    z, p = inf.points_test(0, pmf, 0.0)
    assert z < 0 and 0 < p < 1


def test_irls_poisson_matches_statsmodels():
    import statsmodels.api as sm

    rng = np.random.default_rng(3)
    x = np.column_stack([np.ones(400), rng.integers(0, 2, 400), rng.normal(size=400)])
    y = rng.poisson(np.exp(x @ np.array([0.8, 0.5, -0.3]))).astype(float)
    beta, cov = modeling.irls_poisson(x, y)
    ref = sm.GLM(y, x, family=sm.families.Poisson()).fit()
    assert beta == pytest.approx(ref.params, abs=1e-5)
    assert np.sqrt(np.diag(cov)) == pytest.approx(ref.bse, rel=1e-3)


def test_swap_sampler_keeps_workload_and_federation_rule():
    # 4 clubes, 3 arbitros (A=0, B=1, C=2), 6 jogos em 3 rodadas; C nao pode apitar o clube 3
    home, away = [0, 2, 0, 1, 0, 1], [1, 3, 2, 3, 3, 2]
    refs, rounds = [0, 1, 2, 0, 1, 2], [1, 1, 2, 2, 3, 3]
    same_uf = [[0] * 6, [0] * 6, [0, 1, 0, 1, 1, 0]]
    samples = inf.swap_null_samples(home, away, refs, rounds, same_uf, [0, 0, 0], 4, 3,
                                    stratify=False, k=30, burn=5, thin=2, seed=1)
    assert len(samples) == 30
    assert np.all(samples.sum(axis=1) == 4)  # cada arbitro segue com 2 jogos (2 clubes por jogo)
    assert np.all(samples[:, 3, 2] == 0)  # regra de federacao nunca violada no sorteio
    assert len({s.tobytes() for s in samples}) > 1  # e o sorteio de fato mexe


def test_swap_sampler_with_unique_categories_cannot_move():
    samples = inf.swap_null_samples([0, 1], [1, 0], [0, 1], [1, 2], [[0, 0], [0, 0]], ["FIFA", "MASTER"], 2, 2,
                                    stratify=True, k=5, burn=1, thin=1)
    assert all(np.array_equal(s, samples[0]) for s in samples)


# ------------------------------------------------------------ relatorio
def test_leave_pair_out_keeps_the_planted_signal(league):
    # com o par dentro do ajuste, o excesso vira 'rigor do arbitro' e o sinal some
    table = modeling.pair_table(league["rows"])
    row = table[(table.team == PLANTED[0]) & (table.ref == PLANTED[1])].iloc[0]
    assert (row.o_cards - row.e_cards) / np.sqrt(row.v_cards) > 4 and bool(row.setAside)


def test_report_finds_planted_harsh_referee(league):
    pairs = league["reports"]["all"]["pairs"]
    top = pairs["cards"]["points"][0]
    assert (top["team"], top["referee"]) == PLANTED
    assert top["level"] == "forte" and top["ratio"] > 1.5
    # e nao acusa inocente: ninguem mais passa de 4 desvios, em nenhuma analise
    # (nem o adversario do Time A, que 've' o excesso do A do outro lado)
    for kind in ("cards", "rivalCards", "points"):
        others = [p for p in pairs[kind]["points"] if (p["team"], p["referee"]) != PLANTED]
        assert max(abs(p["z"]) for p in others) < 4, kind


def test_report_finds_planted_easy_assignment(league):
    top = league["reports"]["all"]["pairs"]["ease"]["points"][0]
    assert (top["team"], top["referee"]) == ("Time B", "Arbitro Facil")
    assert top["z"] > 3 and top["easeWithReferee"] > top["easeTeam"]


def test_report_sections_and_missing_hypothesis_data(league):
    reports = league["reports"]
    assert set(reports) == {"2024", "all"}
    rep = reports["2024"]
    assert rep["season"] == 2024 and rep["partialSeasons"] == []
    assert {"overview", "refereeStrictness", "pairs", "escala", "league", "crossSeason", "hypotheses"} <= set(rep)
    assert [h["id"] for h in rep["hypotheses"]] == ["H1", "H2", "H3", "H4"]
    by_id = {h["id"]: h for h in rep["hypotheses"]}
    assert by_id["H2"].get("missing") and by_id["H4"].get("missing")  # sem 2020 nem 2018 no cenario
    fed = rep["escala"]["federation"]["total"]
    assert fed["observedCount"] == 0 and fed["expectedPct"] == 0  # arbitros de MG, clubes de SP/RJ


# ------------------------------------------------------------ API
def test_statistics_endpoint_serves_precomputed_report(db_session):
    _seed_league(db_session)
    compute_and_store(db_session)
    body = client.get("/statistics", params={"season": 2024}).json()
    assert body["key"] == "2024" and body["computedAt"]
    assert client.get("/statistics").json()["key"] == "all"


def test_statistics_endpoint_404_when_not_computed():
    assert client.get("/statistics", params={"season": 2019}).status_code == 404


def test_request_path_does_not_import_analysis_libs():
    # a API roda como funcao serverless na Vercel: numpy/pandas/scipy/statsmodels
    # so no calculo offline (spec 9.6, AGENTS.md)
    code = ("import sys, app.main; "
            "print(sorted(m for m in ('numpy', 'pandas', 'scipy', 'statsmodels') if m in sys.modules))")
    out = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1],
                         capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"


def test_ensure_schema_adds_new_columns_to_old_sqlite():
    eng = create_engine("sqlite://")
    with eng.begin() as conn:
        conn.execute(text("CREATE TABLE teams (id INTEGER PRIMARY KEY, api_id INTEGER, name VARCHAR)"))
    ensure_schema(bind=eng)
    assert "state" in {c["name"] for c in inspect(eng).get_columns("teams")}
    assert "period" in {c["name"] for c in inspect(eng).get_columns("match_events")}
