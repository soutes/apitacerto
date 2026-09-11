"""Mock data store. Same shape/logic as frontend/src/mockData.js (kept in
sync by hand for now — Fase 5 replaces this whole module with SQLAlchemy
queries against real data, without changing main.py's call sites).
"""
from __future__ import annotations

import hashlib
import random
from statistics import mean, pstdev

TEAMS = [
    "Palmeiras", "Flamengo", "Atletico-MG", "Botafogo",
    "Gremio", "Fluminense", "Corinthians", "Sao Paulo",
]

REFEREES = [
    "Anderson Daronco", "Wilton Pereira Sampaio", "Raphael Claus",
    "Braulio da Silva Machado", "Edina Alves Batista", "Rodolpho Toski Marques",
]

SEASONS = [2022, 2023, 2024]

SAMPLE_FLOOR = 5


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


def _win_rate(row: dict) -> float:
    return row["wins"] / row["n"] if row["n"] else 0.0


def _cards_per_game(yellow: int, red: int, n: int) -> float:
    return (yellow * 1 + red * 3) / n if n else 0.0


def _std(values: list[float]) -> float:
    return pstdev(values) if len(values) > 1 else 0.0


def build_heatmap(season: int) -> list[dict]:
    """Full team x referee matrix for a season, com o Indice de
    Favorecimento calculado leave-one-out (spec secao 6)."""
    raw = [_pair_stats(t, r, season) for t in TEAMS for r in REFEREES]

    deltas = []
    for row in raw:
        others = [r for r in raw if r["team"] == row["team"] and r["referee"] != row["referee"]]
        base_win_rate = mean([_win_rate(r) for r in others]) if others else 0.0
        base_cards = mean([_cards_per_game(r["yellow"], r["red"], r["n"]) for r in others]) if others else 0.0
        base_cards_rival = mean(
            [_cards_per_game(r["yellowRival"], r["redRival"], r["n"]) for r in others]
        ) if others else 0.0

        delta_win_rate = _win_rate(row) - base_win_rate
        delta_cards = base_cards - _cards_per_game(row["yellow"], row["red"], row["n"])
        delta_cards_rival = _cards_per_game(row["yellowRival"], row["redRival"], row["n"]) - base_cards_rival

        deltas.append({**row, "deltaWinRate": delta_win_rate, "deltaCards": delta_cards,
                        "deltaCardsRival": delta_cards_rival})

    eligible = [r for r in deltas if r["n"] >= SAMPLE_FLOOR]
    zw = (mean([r["deltaWinRate"] for r in eligible]) if eligible else 0.0,
          _std([r["deltaWinRate"] for r in eligible]) or 1.0)
    zc = (mean([r["deltaCards"] for r in eligible]) if eligible else 0.0,
          _std([r["deltaCards"] for r in eligible]) or 1.0)
    zr = (mean([r["deltaCardsRival"] for r in eligible]) if eligible else 0.0,
          _std([r["deltaCardsRival"] for r in eligible]) or 1.0)

    out = []
    for row in deltas:
        insufficient = row["n"] < SAMPLE_FLOOR
        index = None
        if not insufficient:
            z1 = (row["deltaWinRate"] - zw[0]) / zw[1]
            z2 = (row["deltaCards"] - zc[0]) / zc[1]
            z3 = (row["deltaCardsRival"] - zr[0]) / zr[1]
            index = (z1 + z2 + z3) / 3
        out.append({
            "team": row["team"], "referee": row["referee"], "n": row["n"],
            "wins": row["wins"], "draws": row["draws"], "losses": row["losses"],
            "goalsFor": row["goalsFor"], "goalsAgainst": row["goalsAgainst"],
            "yellow": row["yellow"], "red": row["red"],
            "insufficientSample": insufficient, "index": index,
        })
    return out


def kpis_for(heatmap_rows: list[dict], team: str | None, referee: str | None) -> dict:
    rows = [
        r for r in heatmap_rows
        if (not team or r["team"] == team) and (not referee or r["referee"] == referee)
    ]
    n = sum(r["n"] for r in rows)
    wins = sum(r["wins"] for r in rows)
    draws = sum(r["draws"] for r in rows)
    losses = sum(r["losses"] for r in rows)
    yellow = sum(r["yellow"] for r in rows)
    red = sum(r["red"] for r in rows)
    goals_for = sum(r["goalsFor"] for r in rows)
    goals_against = sum(r["goalsAgainst"] for r in rows)
    return {
        "games": n, "wins": wins, "draws": draws, "losses": losses,
        "winRatePct": round((wins / n) * 100, 1) if n else 0.0,
        "goalsFor": goals_for, "goalsAgainst": goals_against,
        "yellow": yellow, "red": red,
    }


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
