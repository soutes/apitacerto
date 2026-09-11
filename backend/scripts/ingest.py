"""Ingestao da API-Football pro banco local. Roda fora do request path
(spec secao 3/6): o dashboard so le do banco.

Respeita o limite de 100 requests/dia do free tier (spec secao 8): cada
chamada volta com um orcamento (--max-requests) e para assim que esgota,
deixando estado salvo pra continuar no proximo dia (fixtures ja gravados nao
sao buscados de novo; eventos so faltam pros fixtures com
events_ingested=False).

Uso:
    uv run python scripts/ingest.py --max-requests 90
    uv run python scripts/ingest.py --season 2023 --max-requests 50
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ no path

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import Fixture, MatchEvent, Referee, Team  # noqa: E402

LEAGUE_ID = 71  # Brasileirao Serie A
REQUEST_INTERVAL_SECONDS = 7  # free tier tambem tem limite por-minuto, alem do diario
FREE_TIER_SEASONS = [2022, 2023, 2024]  # validado em 2026-09-10, ver specs.md secao 3
API_BASE = "https://v3.football.api-sports.io"

EVENT_TYPE_MAP = {
    ("Card", "Yellow Card"): "YELLOW_CARD",
    ("Card", "Red Card"): "RED_CARD",
    ("Card", "Yellow Red Card"): "RED_CARD",
    ("Goal", None): "GOAL",
}


class Budget:
    def __init__(self, max_requests: int):
        self.remaining = max_requests
        self.used = 0

    def spend(self) -> bool:
        if self.remaining <= 0:
            return False
        self.remaining -= 1
        self.used += 1
        return True


def _client(api_key: str) -> httpx.Client:
    return httpx.Client(base_url=API_BASE, headers={"x-apisports-key": api_key}, timeout=30)


def _get_or_create_team(db: Session, api_id: int, name: str) -> Team:
    team = db.scalar(select(Team).where(Team.api_id == api_id))
    if team:
        return team
    team = Team(api_id=api_id, name=name)
    db.add(team)
    db.flush()
    return team


def _get_or_create_referee(db: Session, name: str) -> Referee:
    referee = db.scalar(select(Referee).where(Referee.name == name))
    if referee:
        return referee
    referee = Referee(name=name)
    db.add(referee)
    db.flush()
    return referee


def ingest_fixtures_for_season(db: Session, client: httpx.Client, season: int, budget: Budget) -> bool:
    already = db.scalar(select(Fixture.id).where(Fixture.season == season).limit(1))
    if already is not None:
        print(f"  season {season}: fixtures ja no banco, pulando /fixtures")
        return True

    if not budget.spend():
        print(f"  season {season}: sem orcamento pra buscar /fixtures")
        return False

    resp = client.get("/fixtures", params={"league": LEAGUE_ID, "season": season})
    data = resp.json()
    if data.get("errors"):
        print(f"  season {season}: erro da API -> {data['errors']}")
        return False

    for item in data.get("response", []):
        fx = item["fixture"]
        teams = item["teams"]
        goals = item["goals"]
        if fx["status"]["short"] != "FT":
            continue  # so partidas finalizadas entram na analise

        home = _get_or_create_team(db, teams["home"]["id"], teams["home"]["name"])
        away = _get_or_create_team(db, teams["away"]["id"], teams["away"]["name"])
        referee = _get_or_create_referee(db, fx["referee"]) if fx.get("referee") else None

        exists = db.scalar(select(Fixture).where(Fixture.api_id == fx["id"]))
        if exists:
            continue
        db.add(Fixture(
            api_id=fx["id"], season=season, round=item["league"]["round"],
            date=fx["date"][:10], home_team_id=home.id, away_team_id=away.id,
            referee_id=referee.id if referee else None,
            home_score=goals["home"], away_score=goals["away"],
        ))
    db.commit()
    print(f"  season {season}: fixtures gravados ({budget.used} req usadas ate agora)")
    return True


def ingest_events(db: Session, client: httpx.Client, budget: Budget) -> None:
    pending = db.scalars(
        select(Fixture).where(Fixture.events_ingested.is_(False)).order_by(Fixture.season, Fixture.id)
    ).all()
    print(f"  {len(pending)} fixtures pendentes de eventos")

    for fixture in pending:
        if not budget.spend():
            print(f"  orcamento esgotado ({budget.used} requests usadas nesta rodada)")
            return

        time.sleep(REQUEST_INTERVAL_SECONDS)
        resp = client.get("/fixtures/events", params={"fixture": fixture.api_id})
        data = resp.json()
        if data.get("errors"):
            errors = data["errors"]
            if isinstance(errors, dict) and "rateLimit" in errors:
                print(f"  limite por-minuto atingido, esperando 65s e tentando de novo ({fixture.api_id})")
                time.sleep(65)
                resp = client.get("/fixtures/events", params={"fixture": fixture.api_id})
                data = resp.json()
                if data.get("errors"):
                    print(f"  fixture {fixture.api_id}: erro persistente -> {data['errors']}")
                    continue
            else:
                print(f"  fixture {fixture.api_id}: erro -> {errors}")
                continue

        for ev in data.get("response", []):
            key = (ev["type"], ev.get("detail"))
            event_type = EVENT_TYPE_MAP.get(key) or EVENT_TYPE_MAP.get((ev["type"], None))
            if not event_type:
                continue  # subst, VAR, etc -- fora do escopo (spec secao 4)
            team = db.scalar(select(Team).where(Team.api_id == ev["team"]["id"]))
            if not team:
                continue
            db.add(MatchEvent(
                fixture_id=fixture.id, team_id=team.id,
                player_name=(ev.get("player") or {}).get("name"),
                minute=(ev.get("time") or {}).get("elapsed"),
                type=event_type, detail=ev.get("detail"),
            ))
        fixture.events_ingested = True
        db.commit()

    if budget.remaining == 0 and pending:
        print("  orcamento esgotado antes de terminar -- roda de novo amanha")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, choices=FREE_TIER_SEASONS, default=None)
    parser.add_argument("--max-requests", type=int, default=90)
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("API_FOOTBALL_KEY nao encontrada no ambiente / .env", file=sys.stderr)
        sys.exit(1)

    Base.metadata.create_all(engine)
    seasons = [args.season] if args.season else FREE_TIER_SEASONS
    budget = Budget(args.max_requests)

    with SessionLocal() as db, _client(api_key) as client:
        print(f"Orcamento desta rodada: {budget.remaining} requests")
        for season in seasons:
            ingest_fixtures_for_season(db, client, season, budget)
            if budget.remaining == 0:
                break
        ingest_events(db, client, budget)
        print(f"Total de requests usadas: {budget.used}")


if __name__ == "__main__":
    main()
