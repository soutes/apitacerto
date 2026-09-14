"""Scraper da API JSON publica da CBF (nao documentada, achada inspecionando
a rede da pagina de tabelas -- ver _docs/specs.md secao 3).

Endpoint por rodada:
  GET https://www.cbf.com.br/api/cbf/jogos/campeonato/{competition_id}/rodada/{n}/fase

Um unico request por rodada ja traz times, placar, arbitro (com funcao,
filtramos por "Arbitro" -- ignora assistente/quarto arbitro/VAR/assessor) e
os eventos de gol/cartao ("penalidades") de todas as partidas daquela
rodada. Sem limite diario conhecido (ao contrario da API-Football) -- ainda
assim, throttle entre requests por educacao com o servidor de terceiro.

Este modulo separa fetch (rede) de parse (puro, testavel sem rede) --
convention do projeto: testes nunca tocam rede.
"""
from __future__ import annotations

import re
import ssl
import time

import httpx
import truststore

BASE_URL = "https://www.cbf.com.br"
USER_AGENT = "Mozilla/5.0 (compatible; ApitaCertoBot/1.0; +https://github.com/soutes/apitacerto)"

# year -> competitionId, extraido do payload SSR de
# https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-a/{year}
# (chave "years" do componente de selecao de temporada). Series A only.
COMPETITION_IDS = {
    2018: 12414, 2019: 12430, 2020: 12464, 2021: 12487, 2022: 12518,
    2023: 12555, 2024: 12584, 2025: 12606, 2026: 1260611,
}

CARD_RESULT_MAP = {
    "AMARELO": "YELLOW_CARD",
    # "VERMELHO2AMARELO" e o rotulo que a CBF usa pra QUALQUER expulsao, nao
    # so pra segundo amarelo -- varrendo 150 jogos de 2022-2026 nao aparece
    # nenhum "VERMELHO" avulso, e 669 expulsoes na base sao todas desse
    # rotulo. Ou seja: NAO da pra separar vermelho direto de segundo amarelo
    # com esta fonte. "VERMELHO" fica mapeado como rede de seguranca caso a
    # CBF passe a distinguir.
    "VERMELHO": "RED_CARD",
    "VERMELHO2AMARELO": "RED_CARD",
}

GOAL_DETAIL_MAP = {
    "NR": "normal",
    "PN": "penalti",
    "CT": "contra",  # gol contra -- o autor e do time que SOFREU o gol
    # "FT" nao esta documentado pela CBF; inferido como falta direta pela
    # frequencia (82 de 4395 gols = 1,9%, compativel com gol de falta) e
    # pelo padrao de sigla de 2 letras das outras chaves.
    "FT": "falta",
}

# A CBF nao usa o mesmo nome pro mesmo clube em todas as temporadas (virou
# SAF, ou o campo "nome" veio truncado num ano especifico) -- sem isso o
# mesmo clube vira dois Team distintos entre temporadas. Achado inspecionando
# o dado real; adicionar aqui qualquer nova inconsistencia que apareca.
TEAM_NAME_ALIASES = {
    "Atlético": "Atlético Goianiense",  # 2022: "nome" veio truncado (venue = Goiania-GO)
    "Coritiba SAF": "Coritiba",
    "Vasco da Gama Saf": "Vasco da Gama",
    "Atlético Goianiense Saf": "Atlético Goianiense",
    "Fortaleza SAF": "Fortaleza Esporte Clube",  # 2025: virou SAF
}


_warned_unknown: set[tuple[str, str | None]] = set()


def _warn_unknown(tipo: str, resultado: str | None) -> None:
    """Avisa uma vez por valor novo de 'resultado' vindo da CBF. Sem isso um
    rotulo novo (ex.: a CBF passar a distinguir vermelho direto) entraria
    cru no banco -- ou sumiria -- sem ninguem notar, ja que o scraper roda
    num cron semanal sem supervisao."""
    key = (tipo, resultado)
    if key in _warned_unknown:
        return
    _warned_unknown.add(key)
    print(f"  [aviso] resultado '{resultado}' desconhecido em {tipo} "
          f"(confira CARD_RESULT_MAP/GOAL_DETAIL_MAP em app/cbf_scraper.py)")


def _canonical_team_name(name: str) -> str:
    if name in TEAM_NAME_ALIASES:
        return TEAM_NAME_ALIASES[name]
    stripped = re.sub(r"\s+Saf$", "", name, flags=re.IGNORECASE)
    if stripped != name:
        # rede de seguranca generica pra sufixo "Saf" nao mapeado ainda --
        # avisa pra revisar se "stripped" bate com um clube ja conhecido ou
        # se e um clube novo de verdade (rodando sem supervisao no cron).
        print(f"  [aviso] '{name}' sem alias explicito, usando '{stripped}' "
              f"(confira TEAM_NAME_ALIASES em app/cbf_scraper.py)")
    return stripped


def make_client() -> httpx.Client:
    # certifi (bundle padrao do httpx) as vezes nao tem a cadeia certa pra
    # cbf.com.br neste ambiente, mesmo com curl/Windows confiando nela --
    # truststore usa o keystore nativo do SO em vez do bundle do certifi.
    ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return httpx.Client(base_url=BASE_URL, headers={"User-Agent": USER_AGENT}, timeout=30, verify=ctx)


def fetch_round(client: httpx.Client, competition_id: int, round_num: int) -> dict:
    resp = client.get(f"/api/cbf/jogos/campeonato/{competition_id}/rodada/{round_num}/fase")
    resp.raise_for_status()
    return resp.json()


def _split_local(local: str | None) -> tuple[str | None, str | None, str | None]:
    """'Couto Pereira - Curitiba - PR' -> (estadio, cidade, estado)."""
    if not local:
        return None, None, None
    parts = [p.strip() for p in local.split(" - ")]
    if len(parts) >= 3:
        return parts[0], " - ".join(parts[1:-1]), parts[-1]
    if len(parts) == 2:
        return parts[0], parts[1], None
    return local.strip(), None, None


def _parse_date(data: str | None) -> str | None:
    """'11/09/2026' -> '2026-09-11' (ISO, mesmo formato usado pela ingestao
    da API-Football -- mantem app/queries.py sem precisar saber a fonte)."""
    if not data:
        return None
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", data)
    if not m:
        return None
    d, mo, y = m.groups()
    return f"{y}-{mo}-{d}"


def _main_referee(arbitros: list[dict]) -> dict | None:
    for a in arbitros or []:
        if a.get("funcao") == "Arbitro":
            return a
    return None


def parse_round(payload: dict, season: int) -> list[dict]:
    """Payload de /rodada/{n}/fase -> lista de dicts prontos pra gravar,
    um por partida. Formato pensado pra alimentar direto os models
    (Team/Referee/Fixture/MatchEvent) sem mais nenhuma transformacao."""
    if not isinstance(payload, dict):
        return []  # rodada que nao existe (num_jogo fora do range) volta []

    matches = []
    for grupo in payload.get("jogos", []):
        for jogo in grupo.get("jogo", []):
            mandante, visitante = jogo["mandante"], jogo["visitante"]
            stadium, city, state = _split_local(jogo.get("local"))
            referee = _main_referee(jogo.get("arbitros"))

            events = []
            for p in jogo.get("penalidades") or []:
                team_id = int(p["clube_id"]) if p.get("clube_id") is not None else None
                minute = None
                if p.get("minutos"):
                    m = re.match(r"(\d+)", p["minutos"])
                    if m:
                        minute = int(m.group(1))

                resultado = p.get("resultado")
                if p["tipo"] == "GOL":
                    if resultado not in GOAL_DETAIL_MAP:
                        _warn_unknown("GOL", resultado)
                    events.append({
                        "type": "GOAL", "team_cbf_id": team_id,
                        "player_name": p.get("atleta_nome"), "minute": minute,
                        "detail": GOAL_DETAIL_MAP.get(resultado, resultado),
                    })
                elif p["tipo"] == "PENALIDADE":
                    card_type = CARD_RESULT_MAP.get(resultado)
                    if card_type:
                        events.append({
                            "type": card_type, "team_cbf_id": team_id,
                            "player_name": p.get("atleta_nome"), "minute": minute,
                            "detail": resultado,
                        })
                    else:
                        # varrendo 2022-2026 so aparecem AMARELO e
                        # VERMELHO2AMARELO -- qualquer outro valor e novidade
                        # da fonte e nao pode sumir em silencio (cron roda sem
                        # supervisao).
                        _warn_unknown("PENALIDADE", resultado)

            matches.append({
                "cbf_id": int(jogo["id_jogo"]),
                "season": season,
                "round": jogo.get("rodada"),
                "date": _parse_date(jogo.get("data")),
                "home_team": {"cbf_id": int(mandante["id"]), "name": _canonical_team_name(mandante["nome"])},
                "away_team": {"cbf_id": int(visitante["id"]), "name": _canonical_team_name(visitante["nome"])},
                "home_score": int(mandante["gols"]) if mandante.get("gols") not in (None, "") else None,
                "away_score": int(visitante["gols"]) if visitante.get("gols") not in (None, "") else None,
                "referee": (
                    {"cbf_id": int(referee["id"]), "name": referee["nome"]} if referee else None
                ),
                "venue_stadium": stadium, "venue_city": city, "venue_state": state,
                "events": events,
            })
    return matches


def scrape_season(competition_id: int, season: int, rounds: range, delay_seconds: float = 1.0):
    """Generator: rende (round_num, list[match_dict]) por rodada, com pausa
    entre requests. Rede + parse juntos -- usado pelo script de ingestao;
    testes usam parse_round() direto com payload gravado, sem chamar isso."""
    with make_client() as client:
        for n in rounds:
            payload = fetch_round(client, competition_id, n)
            yield n, parse_round(payload, season)
            time.sleep(delay_seconds)
