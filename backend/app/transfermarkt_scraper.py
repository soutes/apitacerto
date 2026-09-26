"""Scraper do Transfermarkt pras temporadas que a API da CBF nao tem
(2007-2017) e pros arbitros que ela nao publicou em 2018 (rodadas 1-32).

Paginas usadas (HTML, sem API):
  tabela da temporada: /campeonato-brasileiro-serie-a/gesamtspielplan/wettbewerb/BRA1?saison_id={ano-1}
  ficha do jogo:       /spielbericht/index/spielbericht/{id}

Atencao: o saison_id do Transfermarkt e o ano em que a temporada COMECA no
calendario europeu -- o Brasileirao 2017 e saison_id=2016.

Cada pagina baixada fica gravada em disco (CACHE_DIR): rodar de novo nao
baixa nada que ja veio, entao da pra interromper e continuar, e ajustar o
mapa de nomes sem refazer as ~4.500 requisicoes. Como no cbf_scraper, parse
(puro, testavel sem rede) fica separado do fetch.
"""
from __future__ import annotations

import html as html_lib
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

BASE_URL = "https://www.transfermarkt.com"
# o site devolve pagina vazia/bloqueio pra user-agent de robo generico
USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "transfermarkt"
RETRY_WAITS = (10, 30, 90)


def tm_season_id(season: int) -> int:
    return season - 1


def schedule_path(season: int) -> str:
    return (f"/campeonato-brasileiro-serie-a/gesamtspielplan/wettbewerb/BRA1"
            f"?saison_id={tm_season_id(season)}&spieltagVon=1&spieltagBis=38")


def match_path(match_id: int) -> str:
    return f"/spielbericht/index/spielbericht/{match_id}"


# --- rede --------------------------------------------------------------------

def make_client() -> httpx.Client:
    return httpx.Client(base_url=BASE_URL, headers={"User-Agent": USER_AGENT, "Accept-Language": "en"},
                        timeout=30, follow_redirects=True)


class Fetcher:
    """GET com cache em disco + pausa antes de cada requisicao de verdade
    (leitura do cache nao espera). Falha passageira (5xx, 429, rede) tenta de
    novo; outro 4xx nao -- e pedido errado, repetir nao resolve."""

    def __init__(self, client: httpx.Client, cache_dir: Path = CACHE_DIR, delay: float = 3.0,
                 waits: tuple[float, ...] = RETRY_WAITS):
        self.client, self.cache_dir, self.delay, self.waits = client, cache_dir, delay, waits
        self.downloaded = 0

    def get(self, path: str, cache_key: str) -> str:
        file = self.cache_dir / f"{cache_key}.html"
        if file.exists():
            return file.read_text(encoding="utf-8")
        text = self._download(path)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8")
        return text

    def read_cached(self, cache_keys: list[str], workers: int = 16) -> dict[str, str]:
        """Le do cache, em paralelo, as chaves que ja estao em disco. No
        Windows o antivirus confere cada arquivo aberto (~1 s por ficha);
        em paralelo cai pra ~0,3 s -- 4.500 fichas em minutos, nao horas."""
        files = {k: self.cache_dir / f"{k}.html" for k in cache_keys}
        present = [k for k, f in files.items() if f.exists()]
        with ThreadPoolExecutor(workers) as ex:
            texts = ex.map(lambda k: files[k].read_text(encoding="utf-8"), present)
            return dict(zip(present, texts))

    def _download(self, path: str) -> str:
        for attempt, wait in enumerate((*self.waits, None)):
            time.sleep(self.delay)
            try:
                resp = self.client.get(path)
                if resp.status_code < 500 and resp.status_code != 429:
                    resp.raise_for_status()
                    self.downloaded += 1
                    return resp.text
                error: Exception = httpx.HTTPStatusError(
                    f"{resp.status_code} em {path}", request=resp.request, response=resp)
            except httpx.TransportError as exc:
                error = exc
            if wait is None:
                raise error
            print(f"  [aviso] {error} -- tentando de novo em {wait}s ({attempt + 1}/{len(self.waits)})")
            time.sleep(wait)
        raise AssertionError("inalcancavel")


# --- parse -------------------------------------------------------------------

def _text(s: str) -> str:
    return html_lib.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def parse_schedule(page: str) -> list[dict]:
    """Tabela da temporada -> [{tm_id, round}]. Cada rodada e uma caixa
    'N.Matchday'; cada jogo tem um link 'ergebnis-link' pra ficha."""
    matches = []
    boxes = re.split(r'<div class="content-box-headline">\s*(\d+)\.\s*Matchday\s*</div>', page)
    # re.split com grupo: [antes, n1, bloco1, n2, bloco2, ...]
    for i in range(1, len(boxes) - 1, 2):
        rnd = int(boxes[i])
        for mid in re.findall(r'class="ergebnis-link"[^>]*href="[^"]*/spielbericht/(\d+)"', boxes[i + 1]):
            matches.append({"tm_id": int(mid), "round": rnd})
    return matches


def parse_schedule_clubs(page: str) -> dict[int, str]:
    """{id do clube no Transfermarkt: nome curto} -- pra montar TM_CLUBS e
    avisar de clube ainda nao mapeado antes de baixar as fichas."""
    return {int(cid): html_lib.unescape(name).strip() for cid, name in re.findall(
        r'<td class="[^"]*hauptlink"><a title="[^"]*" href="/[^"]+/spielplan/verein/(\d+)/[^"]*">([^<]+)</a>',
        page)}


_CLOCK = re.compile(
    r'sb-sprite-uhr-klein" style="background-position:\s*-?(\d+)px\s+-?(\d+)px;">(.*?)</span>', re.S)


def _event_time(li: str) -> tuple[str | None, int | None]:
    """O minuto vem desenhado num sprite: grade de celulas de 36px, 10 por
    linha (celula 0 = minuto 1). O acrescimo vem como texto dentro do mesmo
    span ('+3'). Devolve (periodo, minuto absoluto) no formato do
    cbf_scraper: 45+2 -> ('AC1', 47), 90+3 -> ('AC2', 93)."""
    m = _CLOCK.search(li)
    if not m:
        return None, None
    x, y, inner = int(m.group(1)), int(m.group(2)), _text(m.group(3))
    base = (y // 36) * 10 + (x // 36) + 1
    extra = re.search(r"\+\s*(\d+)", inner)
    if extra:
        add = int(extra.group(1))
        return ("AC1", 45 + add) if base <= 45 else ("AC2", 90 + add)
    return ("1T" if base <= 45 else "2T"), base


def _section_items(page: str, section_id: str) -> list[tuple[str, str]]:
    """[(lado 'heim'|'gast', html do <li>)] de uma secao sb-tore / sb-karten."""
    m = re.search(rf'id="{section_id}">(.*?)</ul>', page, re.S)
    if not m:
        return []
    parts = re.split(r'<li class="sb-aktion-(heim|gast)">', m.group(1))
    return [(parts[i], parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


def _player(li: str) -> str | None:
    m = re.search(r'<div class="sb-aktion-aktion">.*?<a title="([^"]*)"', li, re.S)
    return html_lib.unescape(m.group(1)).strip() if m else None


def _goal_detail(li: str) -> str:
    m = re.search(r'<div class="sb-aktion-aktion">(.*?)(?:<br|</div>)', li, re.S)
    desc = _text(m.group(1)).lower() if m else ""
    if "own-goal" in desc or "own goal" in desc:
        return "contra"
    if "penalty" in desc:
        return "penalti"
    if "direct free kick" in desc:
        return "falta"
    return "normal"


# rotulos iguais aos da CBF (detail so e informativo; o que conta e o type)
CARD_SPRITES = {"sb-gelb": ("YELLOW_CARD", "AMARELO"),
                "sb-gelbrot": ("RED_CARD", "VERMELHO2AMARELO"),
                "sb-rot": ("RED_CARD", "VERMELHO")}


def _team_block(page: str, side: str) -> tuple[int, str]:
    m = re.search(rf'<div class="sb-team sb-{side}">.*?class="sb-vereinslink" href="/[^"]+/verein/(\d+)/[^"]*">([^<]+)</a>',
                  page, re.S)
    if not m:
        raise ValueError(f"time '{side}' nao encontrado na ficha")
    return int(m.group(1)), html_lib.unescape(m.group(2)).strip()


def parse_match(page: str) -> dict:
    """Ficha do jogo -> dict com ids e nomes ainda do Transfermarkt (quem
    traduz pra nome canonico e o script de ingestao). Gol contra fica com o
    time do AUTOR, como na CBF; o Transfermarkt lista no lado de quem se
    beneficiou, entao o lado e invertido."""
    home_id, home_name = _team_block(page, "heim")
    away_id, away_name = _team_block(page, "gast")
    datum_m = re.search(r'class="sb-datum.*?</p>', page, re.S)
    datum = datum_m.group(0) if datum_m else ""
    rnd = re.search(r'/spieltag/(\d+)"', datum)
    date = re.search(r"datum/(\d{4}-\d{2}-\d{2})", datum)
    score = re.search(r'class="sb-endstand">\s*(\d+):(\d+)', page)
    ref = re.search(r'href="/[^"]+/profil/schiedsrichter/(\d+)">([^<]+)</a>', page)
    stadium = re.search(r'href="/stadion/stadion/[^"]*">([^<]+)</a>', page)

    side_team = {"heim": home_id, "gast": away_id}
    other = {"heim": "gast", "gast": "heim"}
    events = []
    for side, li in _section_items(page, "sb-tore"):
        detail = _goal_detail(li)
        period, minute = _event_time(li)
        team = side_team[other[side]] if detail == "contra" else side_team[side]
        events.append({"type": "GOAL", "team_tm_id": team, "player_name": _player(li),
                       "minute": minute, "period": period, "detail": detail})
    for side, li in _section_items(page, "sb-karten"):
        sprite = re.search(r'class="sb-sprite (sb-gelbrot|sb-gelb|sb-rot)"', li)
        if not sprite:
            continue
        typ, detail = CARD_SPRITES[sprite.group(1)]
        period, minute = _event_time(li)
        events.append({"type": typ, "team_tm_id": side_team[side], "player_name": _player(li),
                       "minute": minute, "period": period, "detail": detail})

    return {
        "round": int(rnd.group(1)) if rnd else None,
        "date": date.group(1) if date else None,
        "home": {"tm_id": home_id, "name": home_name},
        "away": {"tm_id": away_id, "name": away_name},
        "home_score": int(score.group(1)) if score else None,
        "away_score": int(score.group(2)) if score else None,
        "referee": ({"tm_id": int(ref.group(1)), "name": html_lib.unescape(ref.group(2)).strip()}
                    if ref else None),
        "venue_stadium": html_lib.unescape(stadium.group(1)).strip() if stadium else None,
        "events": events,
    }


def normalize_name(name: str) -> str:
    """Chave de comparacao de nome: sem acento, sem caixa, sem pontuacao --
    a CBF e o Transfermarkt nao escrevem igual ("D Alonso" x "D'Alonso")."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s.lower())).strip()
