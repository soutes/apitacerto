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
from pathlib import Path

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

# "tempo_jogo" da CBF: gol usa "1"/"2"; cartao usa TN1/TN2 (tempo normal),
# AC1/AC2 (acrescimo), INT (intervalo) e PJ (pos-jogo).
PERIOD_MAP = {"1": "1T", "TN1": "1T", "2": "2T", "TN2": "2T",
              "AC1": "AC1", "AC2": "AC2", "INT": "INT", "PJ": "PJ"}
PERIOD_OFFSET = {"1T": 0, "2T": 45, "AC1": 45, "AC2": 90, "INT": 45, "PJ": 90}

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
    # 2018-2021: a CBF mandava razao social completa ou nome sem acento
    "America": "América",
    "Botafogo de Futebol E Regatas": "Botafogo",
    "Cruzeiro Esporte Clube": "Cruzeiro",
    "Esporte Clube Bahia": "Bahia",
    "Csa": "CSA",
    "Parana": "Paraná",
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


# O servidor da CBF manda a cadeia errada: o certificado dela e emitido por
# "Sectigo Public Server Authentication CA OV R36", mas o intermediario
# enviado e outro (Sectigo RSA OV Secure Server CA). O Windows baixa o certo
# sozinho (AIA); o Linux (servidor, Docker, CI) nao, e a conexao falha com
# "unable to get local issuer certificate". O intermediario publico da
# Sectigo vai junto (http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR36.crt,
# assinado pela raiz Sectigo Public Server Authentication Root R46, valido
# ate 2036).
CBF_INTERMEDIATE_CA = Path(__file__).parent / "certs" / "sectigo-public-server-authentication-ca-ov-r36.pem"


def make_client() -> httpx.Client:
    # truststore usa o keystore nativo do SO em vez do bundle do certifi
    ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_verify_locations(cafile=str(CBF_INTERMEDIATE_CA))
    return httpx.Client(base_url=BASE_URL, headers={"User-Agent": USER_AGENT}, timeout=30, verify=ctx)


RETRY_WAITS = (5, 15, 45)  # segundos entre tentativas; a ultima falha propaga


def fetch_round(client: httpx.Client, competition_id: int, round_num: int,
                waits: tuple[float, ...] = RETRY_WAITS) -> dict:
    # a API da CBF devolve 502/503 de vez em quando; o job semanal roda sem
    # ninguem olhando, entao falha passageira (5xx, timeout, conexao) tenta
    # de novo. Erro 4xx nao: e pedido errado, repetir nao resolve.
    url = f"/api/cbf/jogos/campeonato/{competition_id}/rodada/{round_num}/fase"
    for attempt, wait in enumerate((*waits, None)):
        try:
            resp = client.get(url)
            if resp.status_code < 500:
                resp.raise_for_status()
                return resp.json()
            error: Exception = httpx.HTTPStatusError(
                f"{resp.status_code} em {url}", request=resp.request, response=resp)
        except httpx.TransportError as exc:
            error = exc
        if wait is None:
            raise error
        print(f"  [aviso] rodada {round_num}: {error} -- tentando de novo em {wait}s "
              f"({attempt + 1}/{len(waits)})")
        time.sleep(wait)
    raise AssertionError("inalcancavel")


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


def _staff_member(arbitros: list[dict], funcao: str) -> dict | None:
    for a in arbitros or []:
        if a.get("funcao") == funcao:
            return a
    return None


def _main_referee(arbitros: list[dict]) -> dict | None:
    return _staff_member(arbitros, "Arbitro")


def _staff_dict(a: dict | None) -> dict | None:
    if not a:
        return None
    return {"cbf_id": int(a["id"]), "name": a["nome"], "uf": a.get("uf"), "category": a.get("categoria")}


def _club_state(clube: str | None) -> str | None:
    """'Athletico Paranaense - PR' -> 'PR' (UF do clube, nao do estadio)."""
    m = re.search(r"\s-\s([A-Z]{2})$", clube or "")
    return m.group(1) if m else None


def _parse_event_time(tempo_jogo: str | None, minutos: str | None) -> tuple[str | None, int | None]:
    """(periodo, minuto absoluto). A CBF manda o minuto relativo a cada tempo
    ("13:00" no 2o tempo = 58') e o acrescimo colado no 45 ("45:003:00" =
    45+3); intervalo e pos-jogo vem "45:0000:00". Pegar so o primeiro numero
    (como antes) fazia todo cartao de acrescimo/intervalo/pos-jogo virar 45."""
    period = PERIOD_MAP.get(str(tempo_jogo)) if tempo_jogo is not None else None
    if tempo_jogo is not None and period is None:
        _warn_unknown("tempo_jogo", str(tempo_jogo))
    nums = re.findall(r"\d+", minutos or "")
    if not nums:
        return period, None
    if period in ("AC1", "AC2"):
        return period, PERIOD_OFFSET[period] + (int(nums[1]) if len(nums) > 1 else 0)
    if period in ("INT", "PJ"):
        return period, PERIOD_OFFSET[period]
    return period, PERIOD_OFFSET.get(period, 0) + int(nums[0])


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
            var = _staff_member(jogo.get("arbitros"), "VAR")

            events = []
            club_states: dict[int, str] = {}
            for p in jogo.get("penalidades") or []:
                team_id = int(p["clube_id"]) if p.get("clube_id") is not None else None
                period, minute = _parse_event_time(p.get("tempo_jogo"), p.get("minutos"))
                uf = _club_state(p.get("clube"))
                if team_id is not None and uf:
                    club_states[team_id] = uf

                resultado = p.get("resultado")
                if p["tipo"] == "GOL":
                    if resultado not in GOAL_DETAIL_MAP:
                        _warn_unknown("GOL", resultado)
                    events.append({
                        "type": "GOAL", "team_cbf_id": team_id,
                        "player_name": p.get("atleta_nome"), "minute": minute, "period": period,
                        "detail": GOAL_DETAIL_MAP.get(resultado, resultado),
                    })
                elif p["tipo"] == "PENALIDADE":
                    card_type = CARD_RESULT_MAP.get(resultado)
                    if card_type:
                        events.append({
                            "type": card_type, "team_cbf_id": team_id,
                            "player_name": p.get("atleta_nome"), "minute": minute, "period": period,
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
                "home_team": {"cbf_id": int(mandante["id"]), "name": _canonical_team_name(mandante["nome"]),
                              "state": club_states.get(int(mandante["id"]))},
                "away_team": {"cbf_id": int(visitante["id"]), "name": _canonical_team_name(visitante["nome"]),
                              "state": club_states.get(int(visitante["id"]))},
                "home_score": int(mandante["gols"]) if mandante.get("gols") not in (None, "") else None,
                "away_score": int(visitante["gols"]) if visitante.get("gols") not in (None, "") else None,
                "referee": _staff_dict(referee),
                "var_referee": _staff_dict(var),
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
