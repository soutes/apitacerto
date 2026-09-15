"""Banco -> DataFrames: uma linha por jogo e uma por clube-jogo."""
from __future__ import annotations

import re
from collections import Counter

import numpy as np
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Fixture, MatchEvent, Referee, Team

# Jogo sem arbitro na fonte (a CBF nao publicou a escala de boa parte de 2018)
# ainda serve pra linha de base mandante x visitante e pro H4 (penaltis sem
# VAR); so as analises de arbitro filtram esse nivel fora.
MISSING_REF = "(sem árbitro)"

MATCH_COLS = ["fid", "season", "round", "home", "away", "home_state", "away_state", "ref", "ref_uf",
              "ref_cat", "hs", "as_", "h_cards", "a_cards", "h_pen", "a_pen"]
ROW_COLS = ["fid", "season", "round", "team", "opp", "home", "team_state", "opp_state", "ref", "ref_uf",
            "ref_cat", "gf", "ga", "cards", "opp_cards", "pen", "opp_pen", "pts", "draw"]


def _round_number(label: str | None) -> int:
    m = re.search(r"(\d+)", label or "")
    return int(m.group(1)) if m else 0


def load_matches(db: Session) -> pd.DataFrame:
    """Jogos com placar. Cartao = amarelo + vermelho (contagem, que e o que
    o modelo de Poisson modela); penalti = gol de penalti."""
    teams = {t.id: t for t in db.scalars(select(Team))}
    refs = {r.id: r for r in db.scalars(select(Referee))}
    fixtures = db.scalars(
        select(Fixture).where(Fixture.home_score.is_not(None), Fixture.away_score.is_not(None))
    ).all()
    cards, pens = Counter(), Counter()
    for fid, tid, typ, detail in db.execute(
        select(MatchEvent.fixture_id, MatchEvent.team_id, MatchEvent.type, MatchEvent.detail)
    ):
        if typ in ("YELLOW_CARD", "RED_CARD"):
            cards[(fid, tid)] += 1
        elif typ == "GOAL" and detail == "penalti":
            pens[(fid, tid)] += 1

    recs = []
    for f in fixtures:
        h, a = teams[f.home_team_id], teams[f.away_team_id]
        r = refs.get(f.referee_id) if f.referee_id else None
        recs.append((f.id, f.season, _round_number(f.round), h.name, a.name, h.state, a.state,
                     r.name if r else MISSING_REF, r.uf if r else None, f.referee_category or "",
                     f.home_score, f.away_score,
                     cards[(f.id, h.id)], cards[(f.id, a.id)], pens[(f.id, h.id)], pens[(f.id, a.id)]))
    return pd.DataFrame.from_records(recs, columns=MATCH_COLS)


def season_in_progress(db: Session) -> dict[int, bool]:
    """temporada -> True se ainda tem jogo sem placar."""
    stmt = select(Fixture.season, func.count(), func.count(Fixture.home_score)).group_by(Fixture.season)
    return {int(s): scored < total for s, total, scored in db.execute(stmt)}


def team_rows(matches: pd.DataFrame) -> pd.DataFrame:
    """Duas linhas por jogo, cada uma na perspectiva de um dos clubes."""
    if matches.empty:
        return pd.DataFrame(columns=ROW_COLS)

    def side(me: str, op: str, home: int) -> pd.DataFrame:
        mine, theirs = ("h", "a") if home else ("a", "h")
        return pd.DataFrame({
            "fid": matches.fid, "season": matches.season, "round": matches["round"],
            "team": matches[me], "opp": matches[op], "home": home,
            "team_state": matches[f"{me}_state"], "opp_state": matches[f"{op}_state"],
            "ref": matches.ref, "ref_uf": matches.ref_uf, "ref_cat": matches.ref_cat,
            "gf": matches["hs" if home else "as_"], "ga": matches["as_" if home else "hs"],
            "cards": matches[f"{mine}_cards"], "opp_cards": matches[f"{theirs}_cards"],
            "pen": matches[f"{mine}_pen"], "opp_pen": matches[f"{theirs}_pen"],
        })

    rows = pd.concat([side("home", "away", 1), side("away", "home", 0)], ignore_index=True)
    rows["pts"] = np.select([rows.gf > rows.ga, rows.gf == rows.ga], [3, 1], 0)
    rows["draw"] = (rows.gf == rows.ga).astype(int)
    return rows[ROW_COLS]
