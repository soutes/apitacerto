"""Ingestao via scraping da API JSON publica da CBF (ver app/cbf_scraper.py
e _docs/specs.md secao 3). Substitui a API-Football como fonte primaria:
sem limite diario, 1 request por rodada ja traz time + placar + arbitro
principal + gols + cartoes de todas as partidas daquela rodada.

Uso:
    uv run python scripts/scrape_cbf.py --season 2024
    uv run python scripts/scrape_cbf.py --season 2022 --season 2023 --season 2024
    uv run python scripts/scrape_cbf.py --season 2024 --start-round 30 --end-round 38
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ no path

from app.cbf_scraper import COMPETITION_IDS, scrape_season  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import Fixture, MatchEvent, Referee, Team  # noqa: E402

SOURCE = "cbf"


def _get_or_create_team(db: Session, cbf_id: int, name: str) -> Team:
    # o mesmo clube pode ter cod_time diferente entre temporadas na CBF
    # (ex.: Atletico Mineiro em 2022 vs 2024) -- nome e a identidade estavel,
    # api_id so serve pra resolver o time de um evento dentro da MESMA
    # partida (sempre e o mandante ou o visitante daquele jogo).
    team = db.scalar(select(Team).where(Team.name == name))
    if team:
        return team
    team = db.scalar(select(Team).where(Team.api_id == cbf_id))
    if team:
        return team
    team = Team(api_id=cbf_id, name=name)
    db.add(team)
    db.flush()
    return team


def _get_or_create_referee(db: Session, cbf_id: int, name: str) -> Referee:
    referee = db.scalar(select(Referee).where(Referee.name == name))
    if referee:
        return referee
    referee = db.scalar(select(Referee).where(Referee.cbf_id == cbf_id))
    if referee:
        return referee
    referee = Referee(cbf_id=cbf_id, name=name)
    db.add(referee)
    db.flush()
    return referee


def _upsert_fixture(db: Session, match: dict, home: Team, away: Team, referee: Referee | None) -> Fixture:
    fixture = db.scalar(
        select(Fixture).where(Fixture.source == SOURCE, Fixture.api_id == match["cbf_id"])
    )
    if not fixture:
        fixture = Fixture(source=SOURCE, api_id=match["cbf_id"])
        db.add(fixture)

    fixture.season = match["season"]
    fixture.round = match["round"]
    fixture.date = match["date"]
    fixture.home_team_id = home.id
    fixture.away_team_id = away.id
    fixture.referee_id = referee.id if referee else None
    fixture.home_score = match["home_score"]
    fixture.away_score = match["away_score"]
    fixture.venue_stadium = match["venue_stadium"]
    fixture.venue_city = match["venue_city"]
    fixture.venue_state = match["venue_state"]
    fixture.events_ingested = True  # a CBF ja manda os eventos nesta mesma chamada
    db.flush()
    return fixture


def _replace_events(db: Session, fixture: Fixture, match: dict, home: Team, away: Team) -> None:
    db.query(MatchEvent).filter(MatchEvent.fixture_id == fixture.id).delete()
    # usa o cbf_id DESTA partida (nao o Team.api_id salvo, que pode ser de
    # outra temporada pro mesmo clube -- ver _get_or_create_team) pra
    # resolver a qual dos dois lados um evento pertence.
    team_by_cbf_id = {
        match["home_team"]["cbf_id"]: home.id,
        match["away_team"]["cbf_id"]: away.id,
    }
    for ev in match["events"]:
        team_id = team_by_cbf_id.get(ev["team_cbf_id"])
        if team_id is None:
            continue  # nao deveria acontecer -- time do evento sempre e mandante ou visitante
        db.add(MatchEvent(
            fixture_id=fixture.id, team_id=team_id,
            player_name=ev["player_name"], minute=ev["minute"],
            type=ev["type"], detail=ev["detail"],
        ))


def ingest_matches(db: Session, matches: list[dict]) -> None:
    for match in matches:
        home = _get_or_create_team(db, match["home_team"]["cbf_id"], match["home_team"]["name"])
        away = _get_or_create_team(db, match["away_team"]["cbf_id"], match["away_team"]["name"])
        referee = None
        if match["referee"]:
            referee = _get_or_create_referee(db, match["referee"]["cbf_id"], match["referee"]["name"])

        fixture = _upsert_fixture(db, match, home, away, referee)
        _replace_events(db, fixture, match, home, away)
    db.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, action="append", required=True,
                         help="pode repetir --season varias vezes")
    parser.add_argument("--start-round", type=int, default=1)
    parser.add_argument("--end-round", type=int, default=38)
    parser.add_argument("--delay", type=float, default=1.0, help="segundos entre requests")
    args = parser.parse_args()

    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        for season in args.season:
            competition_id = COMPETITION_IDS.get(season)
            if not competition_id:
                print(f"season {season}: sem competitionId conhecido (ver COMPETITION_IDS), pulando")
                continue

            print(f"season {season} (competitionId={competition_id}): rodadas {args.start_round}-{args.end_round}")
            total_matches = total_events = 0
            for round_num, matches in scrape_season(
                competition_id, season, range(args.start_round, args.end_round + 1), args.delay
            ):
                ingest_matches(db, matches)
                total_matches += len(matches)
                total_events += sum(len(m["events"]) for m in matches)
                print(f"  rodada {round_num}: {len(matches)} partidas gravadas")
            print(f"season {season}: {total_matches} partidas, {total_events} eventos (gol+cartao)")


if __name__ == "__main__":
    main()
