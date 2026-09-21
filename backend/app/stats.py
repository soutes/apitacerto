"""Aggregation of team x referee pairs, shared by app/mock_store.py
(synthetic demo data) and app/queries.py (real data from the database) so
the two never drift.

The old Indice de Favorecimento (spec _docs/specs.md secao 6) used to live
here. It was removed on 2026-09-21 (spec 9.8): the 2026-09-14 diagnosis showed
it is indistinguishable from chance. The favoritism question is answered by
app/analysis (spec secao 9), computed offline.
"""
from __future__ import annotations


def pair_rows(raw_rows: list[dict]) -> list[dict]:
    """raw_rows: one dict per (team, referee) pair with keys team, referee,
    n, wins, draws, losses, goalsFor, goalsAgainst, yellow, red (extra keys
    such as yellowRival/redRival are dropped). Returns the public shape of
    each heatmap cell."""
    return [
        {
            "team": row["team"], "referee": row["referee"], "n": row["n"],
            "wins": row["wins"], "draws": row["draws"], "losses": row["losses"],
            "goalsFor": row["goalsFor"], "goalsAgainst": row["goalsAgainst"],
            "yellow": row["yellow"], "red": row["red"],
        }
        for row in raw_rows
    ]


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
