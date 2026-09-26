"""Ingestao das temporadas antigas via Transfermarkt (ver
app/transfermarkt_scraper.py). Complementa a CBF, que so tem 2018 em diante
e sem arbitro nas rodadas 1-32 de 2018.

Dois modos, podem ir juntos:
  --season N          temporada inteira (jogo + placar + arbitro + gols +
                      cartoes), gravada com source="transfermarkt". Para
                      anos que a CBF nao tem (2007-2017).
  --fill-referees N   so preenche o arbitro nos jogos da CBF que vieram sem
                      (2018). Nao mexe em placar nem eventos, que a CBF tem.
                      Onde a CBF tem arbitro, compara com o do Transfermarkt
                      e avisa se o nome nao bater (pista pra TM_REFEREE_ALIASES).

Uso:
    uv run python scripts/scrape_transfermarkt.py --check --season 2007 ... --fill-referees 2018
    uv run python scripts/scrape_transfermarkt.py --season 2007 ... --fill-referees 2018

--check baixa (e guarda no cache) tudo, mas NAO grava no banco: so lista
clube sem mapa, arbitro que vai entrar como pessoa nova (com os nomes
parecidos que ja existem) e jogo com placar que nao bate com os gols.
Revise isso antes da carga de verdade. Rodar de novo usa o cache -- so
baixa o que ainda nao veio.
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ no path

from app.db import SessionLocal, ensure_schema  # noqa: E402
from app.models import Fixture, IngestionLog, MatchEvent, Referee, Team  # noqa: E402
from app.transfermarkt_scraper import (  # noqa: E402
    Fetcher, make_client, match_path, normalize_name, parse_match, parse_schedule, schedule_path,
)

SOURCE = "transfermarkt"

# id do clube no Transfermarkt -> (nome canonico ja usado no banco, UF).
# Nome igual ao que a CBF usa (ver TEAM_NAME_ALIASES em app/cbf_scraper.py):
# o Team e identificado pelo nome, entao o mesmo clube nao duplica.
TM_CLUBS: dict[int, tuple[str, str]] = {
    2863: ("América", "MG"),
    1751: ("América de Natal", "RN"),
    15172: ("Atlético Goianiense", "GO"),
    330: ("Atlético Mineiro", "MG"),
    679: ("Athletico Paranaense", "PR"),
    2035: ("Avaí", "SC"),
    8698: ("Grêmio Barueri", "SP"),  # 2010 jogou em Presidente Prudente, mesmo clube
    537: ("Botafogo", "RJ"),
    2029: ("Ceará", "CE"),
    17776: ("Chapecoense", "SC"),
    199: ("Corinthians", "SP"),
    776: ("Coritiba", "PR"),
    7178: ("Criciúma", "SC"),
    609: ("Cruzeiro", "MG"),
    10010: ("Bahia", "BA"),
    2125: ("Vitória", "BA"),
    4064: ("Figueirense", "SC"),
    614: ("Flamengo", "RJ"),
    2462: ("Fluminense", "RJ"),
    3197: ("Goiás", "GO"),
    210: ("Grêmio", "RS"),
    1755: ("Guarani", "SP"),
    6600: ("Internacional", "RS"),
    3270: ("Ipatinga", "MG"),
    3330: ("Joinville", "SC"),
    10492: ("Juventude", "RS"),
    2646: ("Náutico", "PE"),
    1023: ("Palmeiras", "SP"),
    309: ("Paraná", "PR"),
    1134: ("Ponte Preta", "SP"),
    10247: ("Portuguesa", "SP"),
    1785: ("Santa Cruz", "PE"),
    7478: ("Santo André", "SP"),
    221: ("Santos FC", "SP"),
    8718: ("Sport Recife", "PE"),
    585: ("São Paulo", "SP"),
    978: ("Vasco da Gama", "RJ"),
}

# nome do arbitro no Transfermarkt -> nome que ja esta no banco (vindo da
# CBF), quando os dois escrevem diferente. Chave: o nome do Transfermarkt
# como aparece no relatorio do --check. Acento e caixa ja sao ignorados
# (normalize_name), entao so entra aqui diferenca de verdade (nome do meio
# faltando, abreviacao...).
TM_REFEREE_ALIASES: dict[str, str] = {
    "Leandro Vuaden": "Leandro Pedro Vuaden",  # conferido em 2018: mesmos jogos nas duas fontes
    "Paulo Henrique Schleinch Vollkopf": "Paulo Henrique Schleich Vollkopf",  # erro de digitacao no TM
    # o proprio Transfermarkt tem dois cadastros (ids diferentes) pra mesma pessoa
    "Franscisco Carlos do Nascimento": "Francisco Carlos do Nascimento",
    "José Caldas de Souza": "José de Caldas Souza",
}

# homonimos o Transfermarkt desambigua com a UF: "Adriano de Carvalho (TO)"
_UF_SUFFIX = re.compile(r"\s*\(([A-Z]{2})\)$")


class Resolver:
    """Traduz clube/arbitro do Transfermarkt pro registro do banco (cria se
    preciso) e junta o que nao casou pro relatorio."""

    def __init__(self, db: Session, write: bool):
        self.db, self.write = db, write
        self.unknown_clubs: dict[int, str] = {}
        self.new_referees: Counter = Counter()
        self._refs = {normalize_name(r.name): r for r in db.scalars(select(Referee))}
        self._alias = {normalize_name(k): v for k, v in TM_REFEREE_ALIASES.items()}

    def team(self, tm: dict) -> Team | None:
        if tm["tm_id"] not in TM_CLUBS:
            self.unknown_clubs[tm["tm_id"]] = tm["name"]
            return None
        name, state = TM_CLUBS[tm["tm_id"]]
        team = self.db.scalar(select(Team).where(Team.name == name))
        if not team and self.write:
            # api_id e unico e o espaco de ids e o da CBF -- id negativo do
            # Transfermarkt nao colide (clube que so existe antes de 2018)
            team = Team(api_id=-tm["tm_id"], name=name, state=state)
            self.db.add(team)
            self.db.flush()
        if team and not team.state:
            team.state = state
        return team

    def canonical_referee_name(self, name: str) -> str:
        name = _UF_SUFFIX.sub("", name)
        return self._alias.get(normalize_name(name), name)

    def referee(self, tm: dict | None) -> Referee | None:
        if not tm:
            return None
        name = self.canonical_referee_name(tm["name"])
        key = normalize_name(name)
        ref = self._refs.get(key)
        if ref:
            return ref
        self.new_referees[name] += 1
        if not self.write:
            return None
        # sem cbf_id; UF so quando o Transfermarkt poe o sufixo (ele nao da a federacao)
        uf = _UF_SUFFIX.search(tm["name"])
        ref = Referee(name=name, uf=uf.group(1) if uf else None)
        self.db.add(ref)
        self.db.flush()
        self._refs[key] = ref
        return ref

    def report(self) -> None:
        if self.unknown_clubs:
            print("\nCLUBES SEM MAPA (adicione em TM_CLUBS):")
            for cid, name in sorted(self.unknown_clubs.items()):
                print(f"  {cid}: {name}")
        if self.new_referees:
            existing = [r.name for r in self.db.scalars(select(Referee).where(Referee.cbf_id.is_not(None)))]
            print(f"\nARBITROS QUE ENTRAM COMO PESSOA NOVA ({len(self.new_referees)}) -- "
                  "se algum for alguem que ja existe, adicione em TM_REFEREE_ALIASES:")
            for name, n in sorted(self.new_referees.items()):
                close = difflib.get_close_matches(name, existing, n=2, cutoff=0.75)
                hint = f"   <- parecido: {', '.join(close)}" if close else ""
                print(f"  {name} ({n} jogos){hint}")


def _load_season(fetcher: Fetcher, season: int) -> list[dict]:
    schedule = parse_schedule(fetcher.get(schedule_path(season), f"schedule_{season}"))
    print(f"season {season}: {len(schedule)} jogos na tabela")
    cached = fetcher.read_cached([f"match_{item['tm_id']}" for item in schedule])
    matches = []
    for i, item in enumerate(schedule, 1):
        key = f"match_{item['tm_id']}"
        page = cached.get(key) or fetcher.get(match_path(item["tm_id"]), key)
        match = parse_match(page)
        match["tm_id"], match["round"] = item["tm_id"], match["round"] or item["round"]
        matches.append(match)
        if i % 50 == 0:
            print(f"  {i}/{len(schedule)} fichas ({fetcher.downloaded} baixadas nesta execucao)")
    return matches


def _score_mismatch(m: dict) -> bool:
    if m["home_score"] is None:
        return False
    goals = Counter(e["team_tm_id"] if e["detail"] != "contra" else
                    (m["away"]["tm_id"] if e["team_tm_id"] == m["home"]["tm_id"] else m["home"]["tm_id"])
                    for e in m["events"] if e["type"] == "GOAL")
    return (goals[m["home"]["tm_id"]], goals[m["away"]["tm_id"]]) != (m["home_score"], m["away_score"])


def ingest_season(db: Session, res: Resolver, season: int, matches: list[dict]) -> None:
    n_events = 0
    for m in matches:
        home, away = res.team(m["home"]), res.team(m["away"])
        referee = res.referee(m["referee"])
        if not res.write or not home or not away:
            continue
        fixture = db.scalar(select(Fixture).where(Fixture.source == SOURCE, Fixture.api_id == m["tm_id"]))
        if not fixture:
            fixture = Fixture(source=SOURCE, api_id=m["tm_id"])
            db.add(fixture)
        fixture.season, fixture.round, fixture.date = season, str(m["round"]), m["date"]
        fixture.home_team_id, fixture.away_team_id = home.id, away.id
        fixture.referee_id = referee.id if referee else None
        fixture.home_score, fixture.away_score = m["home_score"], m["away_score"]
        fixture.venue_stadium = m["venue_stadium"]
        fixture.events_ingested = True
        db.flush()
        db.query(MatchEvent).filter(MatchEvent.fixture_id == fixture.id).delete()
        team_by_tm = {m["home"]["tm_id"]: home.id, m["away"]["tm_id"]: away.id}
        for ev in m["events"]:
            db.add(MatchEvent(fixture_id=fixture.id, team_id=team_by_tm[ev["team_tm_id"]],
                              player_name=ev["player_name"], minute=ev["minute"], period=ev["period"],
                              type=ev["type"], detail=ev["detail"]))
            n_events += 1
    if res.write:
        db.add(IngestionLog(source=SOURCE, season=season, round=None,
                            finished_at=datetime.now(timezone.utc).isoformat(),
                            matches=len(matches), events=n_events))
        db.commit()


def fill_referees(db: Session, res: Resolver, season: int, matches: list[dict]) -> None:
    filled = mismatched = missing = 0
    compare = {typ: [0, 0, 0] for typ in ("GOAL", "YELLOW_CARD", "RED_CARD")}  # CBF, TM, jogos diferentes
    for m in matches:
        home, away = res.team(m["home"]), res.team(m["away"])
        fixture = home and away and db.scalar(select(Fixture).where(
            Fixture.season == season, Fixture.source == "cbf",
            Fixture.home_team_id == home.id, Fixture.away_team_id == away.id))
        if not fixture:
            missing += 1
            continue
        # mesma partida nas duas fontes: da pra medir se o Transfermarkt conta
        # cartao/gol igual a CBF antes de confiar nele pros anos sem CBF
        ours = Counter(e.type for e in db.scalars(select(MatchEvent).where(MatchEvent.fixture_id == fixture.id)))
        theirs = Counter(e["type"] for e in m["events"])
        for typ in ("GOAL", "YELLOW_CARD", "RED_CARD"):
            compare[typ][0] += ours[typ]
            compare[typ][1] += theirs[typ]
            compare[typ][2] += ours[typ] != theirs[typ]
        if fixture.referee_id:
            ours = db.get(Referee, fixture.referee_id).name
            if m["referee"] and normalize_name(ours) != normalize_name(
                    res.canonical_referee_name(m["referee"]["name"])):
                mismatched += 1
                print(f"  [confere] rodada {fixture.round}: CBF '{ours}' x Transfermarkt '{m['referee']['name']}'")
            continue
        referee = res.referee(m["referee"])
        if referee and res.write:
            fixture.referee_id = referee.id
            filled += 1
    if res.write:
        db.commit()
    print(f"season {season}: {filled} arbitros preenchidos, {mismatched} divergencias com a CBF, "
          f"{missing} jogos sem par na base da CBF")
    print("  CBF x Transfermarkt nos mesmos jogos (total CBF / total TM / jogos com contagem diferente):")
    for typ, (a, b, diff) in compare.items():
        print(f"    {typ:12} {a:5} / {b:5} / {diff}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, action="append", default=[],
                        help="temporada inteira (anos sem CBF); pode repetir")
    parser.add_argument("--fill-referees", type=int, action="append", default=[],
                        help="so completa arbitro faltante em jogos da CBF; pode repetir")
    parser.add_argument("--check", action="store_true", help="baixa e confere, sem gravar no banco")
    parser.add_argument("--delay", type=float, default=3.0, help="segundos entre requisicoes")
    parser.add_argument("--no-stats", dest="stats", action="store_false",
                        help="nao recalcular a aba Dados estatisticos ao final")
    args = parser.parse_args()
    if not args.season and not args.fill_referees:
        parser.error("informe --season e/ou --fill-referees")

    ensure_schema()
    with make_client() as client, SessionLocal() as db:
        fetcher = Fetcher(client, delay=args.delay)
        res = Resolver(db, write=not args.check)
        cbf_seasons = set(db.scalars(select(Fixture.season).where(Fixture.source == "cbf").distinct()))

        # baixa e confere tudo antes de gravar qualquer coisa: clube sem mapa
        # derruba a carga inteira, nao so metade dela
        loaded = {s: _load_season(fetcher, s) for s in [*args.season, *args.fill_referees]}
        for s in args.season:
            bad = [m for m in loaded[s] if _score_mismatch(m)]
            if bad:
                print(f"  [aviso] season {s}: {len(bad)} jogos com gols listados != placar "
                      f"(ex.: ficha {bad[0]['tm_id']})")
            if s in cbf_seasons:
                print(f"  [aviso] season {s} ja tem jogos da CBF -- use --fill-referees {s}, nao --season")
        probe = Resolver(db, write=False)
        for ms in loaded.values():
            for m in ms:
                probe.team(m["home"]), probe.team(m["away"])
        if probe.unknown_clubs:
            probe.report()
            sys.exit("abortado: clube sem mapa")

        for s in args.season:
            if s not in cbf_seasons:
                ingest_season(db, res, s, loaded[s])
        for s in args.fill_referees:
            fill_referees(db, res, s, loaded[s])

        res.report()
        print(f"\n{fetcher.downloaded} paginas baixadas nesta execucao (o resto veio do cache)")
        if args.check:
            print("--check: nada gravado no banco")
            return

    if args.stats:
        from scrape_cbf import _recompute_stats
        _recompute_stats()


if __name__ == "__main__":
    main()
