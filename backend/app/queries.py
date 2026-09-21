"""Real data access -- replaces app.mock_store once a season has ingested
data (see app/main.py, which falls back to mock_store when the DB is empty
for the requested season). Same output shape as mock_store on purpose, so
main.py and the OpenAPI contract don't change between Fase 3/4 and Fase 5.
"""
from __future__ import annotations

import re
import unicodedata

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Fixture, IngestionLog, MatchEvent, Referee, Team
from app.stats import kpis_for, pair_rows  # re-exported for main.py

CARD_TYPES = ("YELLOW_CARD", "RED_CARD")


def name_sort_key(name: str) -> str:
    # ordem alfabetica igual em qualquer banco: o ORDER BY do SQLite e por
    # codigo de caractere ("CSA" antes de "Ceara", acentuado no fim) e o do
    # Postgres segue o locale -- a mesma lista saia em ordens diferentes
    decomposed = unicodedata.normalize("NFKD", name)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def get_filter_options(db: Session, season: int | None = None) -> dict:
    if season is not None:
        # so os times que de fato jogaram a temporada escolhida (evita
        # misturar time rebaixado/acessado de outro ano no slicer)
        home = select(Fixture.home_team_id).where(Fixture.season == season)
        away = select(Fixture.away_team_id).where(Fixture.season == season)
        team_ids = home.union(away).subquery()
        teams_stmt = select(Team.name).where(Team.id.in_(select(team_ids)))
    else:
        teams_stmt = select(Team.name)
    teams = sorted(db.scalars(teams_stmt).all(), key=name_sort_key)
    referees = sorted(db.scalars(select(Referee.name)).all(), key=name_sort_key)
    seasons = db.scalars(select(Fixture.season).distinct().order_by(Fixture.season)).all()
    return {"teams": teams, "referees": referees, "seasons": list(seasons)}


def _round_number(round_label: str | None) -> int:
    if not round_label:
        return 0
    m = re.search(r"(\d+)", round_label)
    return int(m.group(1)) if m else 0


def _scored_fixtures(db: Session, season: int | None) -> list[Fixture]:
    """Fixtures com placar (vem de /fixtures, 1 request pra temporada
    inteira) -- V/E/D/gols usam isso, independente de cartao ja ter sido
    buscado ou nao. So CARTAO depende de events_ingested (spec secao 8:
    /fixtures/events e 1 request por partida, ingestao e gradual).

    season=None junta todas as temporadas ja ingeridas (usado so pelo
    Indice de Favorecimento com "Todos" no slicer -- ganha amostra, mas
    so faz sentido pra pares time x arbitro, nunca pra classificacao."""
    conds = [Fixture.home_score.is_not(None), Fixture.away_score.is_not(None)]
    if season is not None:
        conds.append(Fixture.season == season)
    stmt = select(Fixture).where(*conds)
    return list(db.scalars(stmt).unique())


def ingestion_progress(db: Session, season: int) -> dict:
    # "fixtures" conta so partidas JA JOGADAS (tem placar) -- pra temporada
    # em andamento (2025/2026), rodada futura sem jogo nao deve contar como
    # "cartao faltando", ela so ainda nao aconteceu.
    total = db.scalar(
        select(func.count()).select_from(Fixture)
        .where(Fixture.season == season, Fixture.home_score.is_not(None))
    ) or 0
    with_cards = db.scalar(
        select(func.count()).select_from(Fixture)
        .where(Fixture.season == season, Fixture.events_ingested.is_(True), Fixture.home_score.is_not(None))
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


REFEREE_SAMPLE_FLOOR = 8  # jogos minimos pra entrar nos rankings por arbitro (season_overview)


def season_overview(db: Session, season: int) -> dict:
    """KPIs de temporada + rankings por arbitro pro Dashboard novo (design
    handoff 2026-09-14): rodada atual, cartoes/jogo, aproveitamento do
    mandante, gols/jogo, e os dois rankings de arbitro (mais cartao,
    vies de mandante). Nao existia antes -- so tinha o indice por par
    time x arbitro (stats.py)."""
    fixtures = _scored_fixtures(db, season)
    if not fixtures:
        return {
            "currentRound": 0, "gamesPlayed": 0, "cardsPerGame": 0.0,
            "homeWinPct": 0.0, "goalsPerGame": 0.0,
            "mostCardsReferees": [], "homeBiasReferees": [], "allReferees": [],
        }

    cards = _card_counts(db, [f.id for f in fixtures])

    current_round = max((_round_number(f.round) for f in fixtures), default=0)
    games_played = len(fixtures)
    home_wins = sum(1 for f in fixtures if f.home_score > f.away_score)
    total_goals = sum(f.home_score + f.away_score for f in fixtures)
    total_cards = 0

    # acumulador por arbitro: jogos, cartoes totais, cartoes do mandante,
    # cartoes do visitante (pra tirar cardsPerGame e o vies de mandante)
    by_ref: dict[str, dict] = {}

    for f in fixtures:
        hy, hr = cards.get((f.id, f.home_team_id), (0, 0))
        ay, ar = cards.get((f.id, f.away_team_id), (0, 0))
        home_cards, away_cards = hy + hr, ay + ar
        total_cards += home_cards + away_cards

        if f.referee is None:
            continue
        acc = by_ref.setdefault(f.referee.name, {"games": 0, "cards": 0, "homeCards": 0, "awayCards": 0})
        acc["games"] += 1
        acc["cards"] += home_cards + away_cards
        acc["homeCards"] += home_cards
        acc["awayCards"] += away_cards

    eligible = {name: a for name, a in by_ref.items() if a["games"] >= REFEREE_SAMPLE_FLOOR}

    most_cards = sorted(
        ({"name": name, "games": a["games"], "cardsPerGame": round(a["cards"] / a["games"], 2)}
         for name, a in eligible.items()),
        key=lambda r: -r["cardsPerGame"],
    )[:5]
    if most_cards:
        max_val = most_cards[0]["cardsPerGame"] or 1
        for r in most_cards:
            r["barPct"] = round(r["cardsPerGame"] / max_val * 100, 1)

    home_bias = sorted(
        ({"name": name, "games": a["games"],
          "bias": round(a["homeCards"] / a["games"] - a["awayCards"] / a["games"], 2)}
         for name, a in eligible.items()),
        key=lambda r: r["bias"],
    )[:4]

    # lista completa (nao so o top 5/4 dos destaques do Dashboard) -- pra
    # tela Arbitros, que lista TODO arbitro elegivel, nao so os extremos.
    all_referees = sorted(
        ({"name": name, "games": a["games"],
          "cardsPerGame": round(a["cards"] / a["games"], 2),
          "bias": round(a["homeCards"] / a["games"] - a["awayCards"] / a["games"], 2)}
         for name, a in eligible.items()),
        key=lambda r: -r["cardsPerGame"],
    )

    return {
        "currentRound": current_round,
        "gamesPlayed": games_played,
        "allReferees": all_referees,
        "cardsPerGame": round(total_cards / games_played, 2) if games_played else 0.0,
        "homeWinPct": round(home_wins / games_played * 100, 1) if games_played else 0.0,
        "goalsPerGame": round(total_goals / games_played, 2) if games_played else 0.0,
        "mostCardsReferees": most_cards,
        "homeBiasReferees": home_bias,
    }


def last_updated(db: Session, season: int) -> str | None:
    """Data/hora (ISO UTC) da ultima rodada de scraping processada pra essa
    temporada -- vem de IngestionLog, gravado pelo scripts/scrape_cbf.py.
    Alimenta o 'atualizado em' do dashboard e o cron semanal."""
    return db.scalar(
        select(func.max(IngestionLog.finished_at)).where(IngestionLog.season == season)
    )


def has_ingested_data(db: Session, season: int) -> bool:
    return db.scalar(
        select(Fixture.id)
        .where(Fixture.season == season, Fixture.home_score.is_not(None))
        .limit(1)
    ) is not None


def build_heatmap(db: Session, season: int | None) -> list[dict]:
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

    return pair_rows(list(raw_by_pair.values()))


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
