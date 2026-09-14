"""Synthetic demo data (deterministic, seeded). Used only when the real
database has no ingested data for the requested season yet -- see
app/main.py. Math lives in app/stats.py, shared with app/queries.py (real
data) so the rule is defined once.
"""
from __future__ import annotations

import hashlib
import random

from app.stats import favoritism_index, kpis_for  # re-exported for main.py

TEAMS = [
    "Palmeiras", "Flamengo", "Atletico-MG", "Botafogo",
    "Gremio", "Fluminense", "Corinthians", "Sao Paulo",
]

REFEREES = [
    "Anderson Daronco", "Wilton Pereira Sampaio", "Raphael Claus",
    "Braulio da Silva Machado", "Edina Alves Batista", "Rodolpho Toski Marques",
]

SEASONS = [2022, 2023, 2024, 2025, 2026]


def _seeded_rng(key: str) -> random.Random:
    seed = int(hashlib.sha256(key.encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed)


def _pair_stats(team: str, referee: str, season: int) -> dict:
    rng = _seeded_rng(f"{team}|{referee}|{season}")
    n = 1 + rng.randrange(6)  # 1..6 jogos do par nesta temporada
    wins = draws = losses = 0
    goals_for = goals_against = 0
    yellow = red = yellow_rival = red_rival = 0
    for _ in range(n):
        r = rng.random()
        if r < 0.45:
            wins += 1
        elif r < 0.7:
            draws += 1
        else:
            losses += 1
        goals_for += rng.randrange(4)
        goals_against += rng.randrange(3)
        yellow += rng.randrange(3)
        red += 1 if rng.random() < 0.12 else 0
        yellow_rival += rng.randrange(3)
        red_rival += 1 if rng.random() < 0.10 else 0
    return {
        "team": team, "referee": referee, "n": n,
        "wins": wins, "draws": draws, "losses": losses,
        "goalsFor": goals_for, "goalsAgainst": goals_against,
        "yellow": yellow, "red": red,
        "yellowRival": yellow_rival, "redRival": red_rival,
    }


def build_heatmap(season: int) -> list[dict]:
    raw = [_pair_stats(t, r, season) for t in TEAMS for r in REFEREES]
    return favoritism_index(raw)


def timeseries_for(team: str | None, season: int) -> list[dict]:
    rng = _seeded_rng(f"ts|{team or 'liga'}|{season}")
    rounds = 20
    wins_acc = 0
    out = []
    for round_ in range(1, rounds + 1):
        win = rng.random() < 0.45
        if win:
            wins_acc += 1
        out.append({
            "round": round_,
            "winRatePct": round((wins_acc / round_) * 100, 1),
            "yellow": rng.randrange(5),
            "red": 1 if rng.random() < 0.15 else 0,
        })
    return out
