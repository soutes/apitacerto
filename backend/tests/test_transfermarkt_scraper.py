"""Testa app/transfermarkt_scraper contra fichas reais do Transfermarkt
(recortadas: so cabecalho, gols e cartoes) -- sem tocar rede."""
from pathlib import Path

import pytest

from app.transfermarkt_scraper import (
    Fetcher,
    _event_time,
    normalize_name,
    parse_match,
    parse_schedule,
    parse_schedule_clubs,
    schedule_path,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _page(match_id: int) -> str:
    return (FIXTURES / f"transfermarkt_match_{match_id}.html").read_text(encoding="utf-8")


def test_schedule_path_uses_previous_year_as_season_id():
    # o Transfermarkt numera a temporada pelo ano em que ela comeca na Europa
    assert "saison_id=2016" in schedule_path(2017)


def test_parse_match_header():
    m = parse_match(_page(3011401))  # Cruzeiro 0x1 Gremio, rodada 1 de 2018
    assert m["round"] == 1
    assert m["date"] == "2018-04-14"
    assert m["home"] == {"tm_id": 609, "name": "Cruzeiro Esporte Clube"}
    assert m["away"]["tm_id"] == 210
    assert (m["home_score"], m["away_score"]) == (0, 1)
    assert m["referee"] == {"tm_id": 13405, "name": "Rodolpho Toski Marques"}
    assert m["venue_stadium"] == "Estádio Governador Magalhães Pinto"


def test_parse_match_events():
    events = parse_match(_page(3011401))["events"]
    goals = [e for e in events if e["type"] == "GOAL"]
    assert goals == [{"type": "GOAL", "team_tm_id": 210, "player_name": "André Felipe",
                      "minute": 55, "period": "2T", "detail": "normal"}]
    assert sum(e["type"] == "YELLOW_CARD" for e in events) == 4
    red = [e for e in events if e["type"] == "RED_CARD"]
    assert [(r["player_name"], r["team_tm_id"], r["minute"]) for r in red] == [("Walter Kannemann", 210, 73)]


def test_parse_match_2007_has_referee_and_stoppage_time():
    m = parse_match(_page(73322))  # Atletico-MG 2x1 Nautico, rodada 1 de 2007
    assert m["date"] == "2007-05-13"
    assert m["referee"]["name"] == "Elmo Alves Resende Cunha"
    goals = [(e["minute"], e["period"], e["detail"]) for e in m["events"] if e["type"] == "GOAL"]
    assert goals == [(9, "1T", "falta"), (26, "1T", "normal"), (95, "AC2", "normal")]


@pytest.mark.parametrize("pos,inner,expected", [
    ("-0px -0px", "", ("1T", 1)),
    ("-144px -180px", "", ("2T", 55)),
    ("-144px -144px", "", ("1T", 45)),
    ("-144px -144px", "+2", ("AC1", 47)),
    ("-324px -288px", "+3", ("AC2", 93)),
])
def test_event_time_reads_sprite_grid(pos, inner, expected):
    li = f'<span class="sb-sprite-uhr-klein" style="background-position: {pos};">{inner}</span>'
    assert _event_time(li) == expected


def test_own_goal_goes_to_the_scorers_team():
    # o Transfermarkt poe o gol contra no lado de quem se beneficiou; no
    # banco (como na CBF) ele fica com o time do autor
    page = _page(3011401).replace("Tap-in, 1. Goal of the Season", "Own-goal")
    goal = next(e for e in parse_match(page)["events"] if e["type"] == "GOAL")
    assert goal["detail"] == "contra"
    assert goal["team_tm_id"] == 609


def test_parse_schedule():
    page = """
      <div class="content-box-headline">1.Matchday</div>
      <td class="text-right no-border-rechts hauptlink"><a title="X" href="/corinthians-sao-paulo/spielplan/verein/199/saison_id/2006">Corinthians</a></td>
      <a title="" class="ergebnis-link" id="73323" href="/a_b/index/spielbericht/73323">1:0</a>
      <div class="content-box-headline">2.Matchday</div>
      <a title="" class="ergebnis-link" id="73400" href="/a_b/index/spielbericht/73400">-:-</a>
    """
    assert parse_schedule(page) == [{"tm_id": 73323, "round": 1}, {"tm_id": 73400, "round": 2}]
    assert parse_schedule_clubs(page) == {199: "Corinthians"}


def test_normalize_name_ignores_accent_and_case():
    assert normalize_name("Wílton  Pereira SAMPAIO") == normalize_name("Wilton Pereira Sampaio")
    assert normalize_name("Rodrigo D'Alonso Ferreira") == normalize_name("Rodrigo D Alonso Ferreira")


def test_fetcher_reads_cache_without_network(tmp_path):
    (tmp_path / "match_1.html").write_text("<html>cache</html>", encoding="utf-8")
    fetcher = Fetcher(client=None, cache_dir=tmp_path, delay=0)  # client None: rede quebraria o teste
    assert fetcher.get("/qualquer", "match_1") == "<html>cache</html>"
    assert fetcher.downloaded == 0


def test_resolver_strips_uf_suffix_and_applies_aliases(db_session):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from scrape_transfermarkt import Resolver

    from app.models import Referee

    db_session.add(Referee(name="Leandro Pedro Vuaden", cbf_id=1, uf="RS"))
    db_session.flush()
    res = Resolver(db_session, write=True)
    assert res.referee({"tm_id": 1163, "name": "Leandro Vuaden"}).name == "Leandro Pedro Vuaden"
    new = res.referee({"tm_id": 1629, "name": "Adriano de Carvalho (TO)"})
    assert (new.name, new.uf, new.cbf_id) == ("Adriano de Carvalho", "TO", None)
    # duas grafias do mesmo arbitro no Transfermarkt viram um registro so
    a = res.referee({"tm_id": 3052, "name": "Franscisco Carlos do Nascimento"})
    assert a is res.referee({"tm_id": 9, "name": "Francisco Carlos do Nascimento"})
