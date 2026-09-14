"""Real data access -- replaces app.mock_store once a season has ingested
data (see app/main.py, which falls back to mock_store when the DB is empty
for the requested season). Same output shape as mock_store on purpose, so
main.py and the OpenAPI contract don't change between Fase 3/4 and Fase 5.
"""
from __future__ import annotations

import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Fixture, MatchEvent, Referee, Team
from app.stats import favoritism_index, kpis_for  # re-exported for main.py

CARD_TYPES = ("YELLOW_CARD", "RED_CARD")


def get_filter_options(db: Session) -> dict:
    teams = db.scalars(select(Team.name).order_by(Team.name)).all()
    referees = db.scalars(select(Referee.name).order_by(Referee.name)).all()
    seasons = db.scalars(select(Fixture.season).distinct().order_by(Fixture.season)).all()
    return {"teams": list(teams), "referees": list(referees), "seasons": list(seasons)}


def _round_number(round_label: str | None) -> int:
    if not round_label:
        return 0
    m = re.search(r"(\d+)", round_label)
    return int(m.group(1)) if m else 0


def _scored_fixtures(db: Session, season: int) -> list[Fixture]:
    """Fixtures com placar (vem de /fixtures, 1 request pra temporada
    inteira) -- V/E/D/gols usam isso, independente de cartao ja ter sido
    buscado ou nao. So CARTAO depende de events_ingested (spec secao 8:
    /fixtures/events e 1 request por partida, ingestao e gradual)."""
    stmt = (
        select(Fixture)
        .where(Fixture.season == season, Fixture.home_score.is_not(None), Fixture.away_score.is_not(None))
    )
    return list(db.scalars(stmt).unique())


def ingestion_progress(db: Session, season: int) -> dict:
    total = db.scalar(
        select(func.count()).select_from(Fixture).where(Fixture.season == season)
    ) or 0
    with_cards = db.scalar(
        select(func.count()).select_from(Fixture)
        .where(Fixture.season == season, Fixture.events_ingested.is_(True))
    ) or 0
    return {"fixtures": total, "fixturesWithCards": with_cards}


def _card_counts(db: Session, fixture_ids: list[int]) -> dict[tuple[int, int], tuple[int, int]]:
    """(fixture_id, team_id) -> (yellow, red) count, for the given fixtures."""
    if not fixture_ids:
        return {}
    stmt = select(MatchEvent).where(
        MatchEvent.fixture_id.in_(fixture_ids), MatchEvent.type.in_(CARD_TYPES)
    )
    counts: dict[tuple[int, int], list[int]] = {}
    for ev in db.scalars(stmt):
        key = (ev.fixture_id, ev.team_id)
        counts.setdefault(key, [0, 0])
        if ev.type == "YELLOW_CARD":
            counts[key][0] += 1
        else:
            counts[key][1] += 1
    return {k: (v[0], v[1]) for k, v in counts.items()}


def has_ingested_data(db: Session, season: int) -> bool:
    return db.scalar(
        select(Fixture.id)
        .where(Fixture.season == season, Fixture.home_score.is_not(None))
        .limit(1)
    ) is not None


def build_heatmap(db: Session, season: int) -> list[dict]:
    fixtures = _scored_fixtures(db, season)
    if not fixtures:
        return []
    cards = _card_counts(db, [f.id for f in fixtures])

    raw_by_pair: dict[tuple[str, str], dict] = {}

    def add(pair_key, **kw):
        row = raw_by_pair.setdefault(pair_key, {
            "team": pair_key[0], "referee": pair_key[1], "n": 0,
            "wins": 0, "draws": 0, "losses": 0,
            "goalsFor": 0, "goalsAgainst": 0, "yellow": 0, "red": 0,
            "yellowRival": 0, "redRival": 0,
        })
        row["n"] += 1
        row["wins"] += kw["wins"]
        row["draws"] += kw["draws"]
        row["losses"] += kw["losses"]
        row["goalsFor"] += kw["goalsFor"]
        row["goalsAgainst"] += kw["goalsAgainst"]
        row["yellow"] += kw["yellow"]
        row["red"] += kw["red"]
        row["yellowRival"] += kw["yellowRival"]
        row["redRival"] += kw["redRival"]

    for f in fixtures:
        if f.referee is None or f.home_score is None or f.away_score is None:
            continue
        ref_name = f.referee.name
        hy, hr = cards.get((f.id, f.home_team_id), (0, 0))
        ay, ar = cards.get((f.id, f.away_team_id), (0, 0))

        if f.home_score > f.away_score:
            home_res, away_res = "W", "L"
        elif f.home_score < f.away_score:
            home_res, away_res = "L", "W"
        else:
            home_res = away_res = "D"

        add((f.home_team.name, ref_name),
            wins=1 if home_res == "W" else 0, draws=1 if home_res == "D" else 0,
            losses=1 if home_res == "L" else 0,
            goalsFor=f.home_score, goalsAgainst=f.away_score,
            yellow=hy, red=hr, yellowRival=ay, redRival=ar)

        add((f.away_team.name, ref_name),
            wins=1 if away_res == "W" else 0, draws=1 if away_res == "D" else 0,
            losses=1 if away_res == "L" else 0,
            goalsFor=f.away_score, goalsAgainst=f.home_score,
            yellow=ay, red=ar, yellowRival=hy, redRival=hr)

    return favoritism_index(list(raw_by_pair.values()))


def timeseries_for(db: Session, team: str | None, season: int) -> list[dict]:
    fixtures = _scored_fixtures(db, season)
    if team:
        fixtures = [f for f in fixtures if f.home_team.name == team or f.away_team.name == team]
    if not fixtures:
        return []
    cards = _card_counts(db, [f.id for f in fixtures])

    per_round: dict[int, dict] = {}
    for f in fixtures:
        if f.home_score is None or f.away_score is None:
            continue
        rnd = _round_number(f.round)
        bucket = per_round.setdefault(rnd, {"wins": 0, "games": 0, "yellow": 0, "red": 0})
        bucket["games"] += 1

        if team:
            is_home = f.home_team.name == team
            my_score, other_score = (f.home_score, f.away_score) if is_home else (f.away_score, f.home_score)
            if my_score > other_score:
                bucket["wins"] += 1
            team_id = f.home_team_id if is_home else f.away_team_id
            y, r = cards.get((f.id, team_id), (0, 0))
        else:
            if f.home_score > f.away_score:
                bucket["wins"] += 1  # aproveitamento do mandante, visao liga
            hy, hr = cards.get((f.id, f.home_team_id), (0, 0))
            ay, ar = cards.get((f.id, f.away_team_id), (0, 0))
            y, r = hy + ay, hr + ar
        bucket["yellow"] += y
        bucket["red"] += r

    out = []
    wins_acc = games_acc = 0
    for rnd in sorted(per_round):
        b = per_round[rnd]
        wins_acc += b["wins"]
        games_acc += b["games"]
        out.append({
            "round": rnd,
            "winRatePct": round((wins_acc / games_acc) * 100, 1) if games_acc else 0.0,
            "yellow": b["yellow"],
            "red": b["red"],
        })
    return out
