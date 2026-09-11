"""Pure math for the Indice de Favorecimento (spec _docs/specs.md secao 6).

Shared by app/mock_store.py (synthetic demo data) and app/queries.py (real
data from the database) so the two never drift like they briefly did before
this module existed.
"""
from __future__ import annotations

from statistics import mean, pstdev

SAMPLE_FLOOR = 5


def _win_rate(row: dict) -> float:
    return row["wins"] / row["n"] if row["n"] else 0.0


def _cards_per_game(yellow: int, red: int, n: int) -> float:
    return (yellow * 1 + red * 3) / n if n else 0.0


def _std(values: list[float]) -> float:
    return pstdev(values) if len(values) > 1 else 0.0


def favoritism_index(raw_rows: list[dict]) -> list[dict]:
    """raw_rows: one dict per (team, referee) pair with keys team, referee,
    n, wins, draws, losses, goalsFor, goalsAgainst, yellow, red, yellowRival,
    redRival. Returns the same pairs enriched with insufficientSample and
    index, using leave-one-out baselines (team vs every OTHER referee)."""

    deltas = []
    for row in raw_rows:
        others = [r for r in raw_rows if r["team"] == row["team"] and r["referee"] != row["referee"]]
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
    return {
        "games": n, "wins": wins, "draws": draws, "losses": losses,
        "winRatePct": round((wins / n) * 100, 1) if n else 0.0,
        "goalsFor": sum(r["goalsFor"] for r in rows),
        "goalsAgainst": sum(r["goalsAgainst"] for r in rows),
        "yellow": sum(r["yellow"] for r in rows),
        "red": sum(r["red"] for r in rows),
    }
