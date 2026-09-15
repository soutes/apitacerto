"""Orquestra a aba Dados estatisticos: banco -> modelos -> secoes -> JSON
gravado em stat_reports (spec 9.6). Offline; a API so le o resultado."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analysis import sections as sec
from app.analysis.data import load_matches, season_in_progress, team_rows
from app.analysis.modeling import fit_all, pair_tables, pool_pairs
from app.models import Fixture, IngestionLog, MatchEvent, StatReport

METHOD_VERSION = 1  # subir quando a metodologia mudar (spec 9: emenda datada)


def data_version(db: Session) -> str:
    n_fx = db.scalar(select(func.count()).select_from(Fixture).where(Fixture.home_score.is_not(None))) or 0
    n_ev = db.scalar(select(func.count()).select_from(MatchEvent)) or 0
    last = db.scalar(select(func.max(IngestionLog.id))) or 0
    return f"{n_fx}-{n_ev}-{last}"


def build_reports(db: Session) -> dict[str, dict]:
    """Uma entrada por temporada + "all" (todas juntas)."""
    matches = load_matches(db)
    if matches.empty:
        return {}
    rows = team_rows(matches)
    fitted = fit_all(rows)
    pairs = pair_tables(rows)  # esperado de cada par sem os jogos do proprio par
    progress = season_in_progress(db)
    seasons = sorted(int(s) for s in matches.season.unique())
    closed = [s for s in seasons if not progress.get(s, False)]
    # sorteios de escala sao a parte cara -- uma vez por temporada, reusados no "all"
    conc = {s: sec.concentration_inputs(matches[matches.season == s], seed=s) for s in seasons}
    shared = {"league": sec.league_baseline(matches),
              "crossSeason": sec.cross_season(pairs),
              "hypotheses": sec.hypotheses(fitted, closed)}

    reports = {}
    for key, sel in [(str(s), [s]) for s in seasons] + [("all", seasons)]:
        is_all = key == "all"
        f = fitted[fitted.season.isin(sel)]
        m = matches[matches.season.isin(sel)]
        p = pool_pairs(pairs[pairs.season.isin(sel)])
        floor = 5 if is_all else 3  # piso pre-registrado (spec 9.2)
        reports[key] = {
            "key": key, "season": None if is_all else sel[0], "seasons": sel,
            "partialSeasons": [s for s in sel if progress.get(s, False)],
            "methodVersion": METHOD_VERSION,
            "overview": sec.overview(f, m, floor),
            "refereeStrictness": sec.referee_strictness(f, floor_games=15 if is_all else 8),
            "pairs": {
                "cards": sec.pair_analysis(p, "cards", floor),
                "rivalCards": sec.pair_analysis(p, "opp", floor),
                "points": sec.pair_analysis(p, "pts", floor),
                "ease": sec.ease_analysis(f, floor),
            },
            "escala": {"federation": sec.federation(m), "category": sec.category_importance(m),
                       "concentration": sec.concentration([conc[s] for s in sel])},
            **shared,
        }
    return reports


def compute_and_store(db: Session) -> list[str]:
    reports = build_reports(db)
    version = data_version(db)
    now = datetime.now(timezone.utc).isoformat()
    existing = {r.key: r for r in db.scalars(select(StatReport))}
    for key, payload in reports.items():
        row = existing.get(key) or StatReport(key=key)
        row.method_version, row.data_version, row.computed_at, row.payload = METHOD_VERSION, version, now, payload
        db.add(row)
    for key in set(existing) - set(reports):
        db.delete(existing[key])
    db.commit()
    return sorted(reports)
