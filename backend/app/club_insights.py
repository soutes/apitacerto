"""Aba "Análises dos clubes": a campanha de cada clube em cada temporada.

Devolve, por temporada, a trajetória de pontos de cada clube (pontos
acumulados depois de cada jogo, em ordem de data), a posição final com os
critérios da CBF (pontos, vitórias, saldo, gols pró) e o destino -- campeão,
G-6, meio da tabela ou rebaixado -- quando a temporada já acabou. As réguas
que dependem da rodada escolhida na tela (linha do rebaixamento, líder que
vira campeão...) o front calcula em cima dessas trajetórias.

Conta leve, em Python puro (~3.400 jogos): cabe no caminho da request sem
numpy/pandas, como pede o AGENTS.md. Arbitragem fica de fora de propósito.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Fixture, MatchEvent, Team

RELEGATION_SPOTS = 4
TOP_SPOTS = 6  # faixa que costuma dar Libertadores (direta ou pré)
PERIOD_ORDER = {"1T": 0, "AC1": 1, "INT": 2, "2T": 3, "AC2": 4, "PJ": 5}


def _points(goals_for: int, goals_against: int) -> int:
    if goals_for > goals_against:
        return 3
    return 1 if goals_for == goals_against else 0


def _first_goal_side(goals: list[tuple[str | None, int | None, int, str, int]], home_id: int) -> str | None:
    """Lado ("H"/"A") que marcou primeiro. Gol contra conta para o outro
    lado: a CBF registra o gol contra no time de quem fez (conferido: com
    essa regra o placar reconstruído bate em 99% dos jogos)."""
    if not goals:
        return None
    period, minute, event_id, detail, team_id = min(
        goals, key=lambda g: (PERIOD_ORDER.get(g[0] or "", 9), g[1] if g[1] is not None else 999, g[2])
    )
    side = "H" if team_id == home_id else "A"
    if detail == "contra":
        side = "A" if side == "H" else "H"
    return side


def _fate(position: int, n_teams: int) -> str:
    if position == 1:
        return "champion"
    if position <= TOP_SPOTS:
        return "top6"
    if position > n_teams - RELEGATION_SPOTS:
        return "relegated"
    return "mid"


def build_club_insights(db: Session) -> dict:
    names = dict(db.execute(select(Team.id, Team.name)).all())
    fixtures = db.execute(
        select(
            Fixture.id, Fixture.season, Fixture.date, Fixture.home_team_id, Fixture.away_team_id,
            Fixture.home_score, Fixture.away_score,
        )
        .where(Fixture.home_score.is_not(None), Fixture.away_score.is_not(None))
        .order_by(Fixture.season, Fixture.date, Fixture.id)
    ).all()

    goals_by_fixture: dict[int, list] = defaultdict(list)
    for fixture_id, period, minute, event_id, detail, team_id in db.execute(
        select(
            MatchEvent.fixture_id, MatchEvent.period, MatchEvent.minute, MatchEvent.id,
            MatchEvent.detail, MatchEvent.team_id,
        ).where(MatchEvent.type == "GOAL")
    ).all():
        goals_by_fixture[fixture_id].append((period, minute, event_id, detail, team_id))

    by_season: dict[int, list] = defaultdict(list)
    for row in fixtures:
        by_season[row.season].append(row)

    seasons = []
    previous_teams: set[str] | None = None
    first_goal = {"games": 0, "firstWins": 0, "firstDraws": 0, "homeFirst": 0, "homeFirstWins": 0,
                  "awayFirst": 0, "awayFirstWins": 0}
    comebacks: dict[str, list[int]] = defaultdict(list)  # clube -> pontos nos jogos em que sofreu o 1o gol

    for season in sorted(by_season):
        games = by_season[season]
        acc: dict[str, dict] = defaultdict(lambda: {
            "points": [], "wins": 0, "draws": 0, "losses": 0, "goalsFor": 0, "goalsAgainst": 0,
            "homePoints": 0, "awayPoints": 0, "homeGames": 0, "awayGames": 0,
        })
        home_wins = draws = goals = zero_zero = 0
        for g in games:
            home, away = names[g.home_team_id], names[g.away_team_id]
            goals += g.home_score + g.away_score
            home_wins += g.home_score > g.away_score
            draws += g.home_score == g.away_score
            zero_zero += g.home_score == 0 and g.away_score == 0
            for team, gf, ga, venue in ((home, g.home_score, g.away_score, "home"),
                                        (away, g.away_score, g.home_score, "away")):
                a = acc[team]
                pts = _points(gf, ga)
                a["points"].append((a["points"][-1] if a["points"] else 0) + pts)
                a["goalsFor"] += gf
                a["goalsAgainst"] += ga
                a["wins" if pts == 3 else "draws" if pts == 1 else "losses"] += 1
                a[f"{venue}Points"] += pts
                a[f"{venue}Games"] += 1

            side = _first_goal_side(goals_by_fixture.get(g.id, []), g.home_team_id)
            if side:
                result = (g.home_score > g.away_score) - (g.home_score < g.away_score)
                scorer_result = result if side == "H" else -result
                first_goal["games"] += 1
                first_goal["firstWins"] += scorer_result > 0
                first_goal["firstDraws"] += scorer_result == 0
                first_goal[f"{'home' if side == 'H' else 'away'}First"] += 1
                first_goal[f"{'home' if side == 'H' else 'away'}FirstWins"] += scorer_result > 0
                conceded = away if side == "H" else home
                comebacks[conceded].append({1: 0, 0: 1, -1: 3}[scorer_result])

        n_teams = len(acc)
        full_length = 2 * (n_teams - 1)
        complete = n_teams > 1 and all(len(a["points"]) == full_length for a in acc.values())
        table = sorted(
            acc.items(),
            key=lambda kv: (
                -(kv[1]["points"][-1] if kv[1]["points"] else 0),
                -kv[1]["wins"],
                -(kv[1]["goalsFor"] - kv[1]["goalsAgainst"]),
                -kv[1]["goalsFor"],
                kv[0],
            ),
        )
        teams = []
        for position, (team, a) in enumerate(table, start=1):
            teams.append({
                "team": team,
                "position": position,
                "fate": _fate(position, n_teams) if complete else None,
                "promoted": previous_teams is not None and team not in previous_teams,
                **a,
            })
        seasons.append({
            "season": season,
            "complete": complete,
            "teams": teams,
            "games": len(games),
            "goalsPerGame": round(goals / len(games), 3) if games else 0,
            "homeWinPct": round(100 * home_wins / len(games), 1) if games else 0,
            "drawPct": round(100 * draws / len(games), 1) if games else 0,
            "zeroZeroPct": round(100 * zero_zero / len(games), 1) if games else 0,
        })
        previous_teams = set(acc)

    return {
        "seasons": seasons,
        "firstGoal": first_goal,
        "comebacks": sorted(
            (
                {"team": team, "games": len(pts), "pointsPerGame": round(sum(pts) / len(pts), 3),
                 "wins": sum(p == 3 for p in pts)}
                for team, pts in comebacks.items()
            ),
            key=lambda r: -r["pointsPerGame"],
        ),
    }
