"""Testa app/cbf_scraper.parse_round contra um payload real (trimmado, sem
os elencos que o parser nao usa) da API publica da CBF -- sem tocar rede,
ver tests/fixtures/cbf_rodada_sample.json."""
import json
from pathlib import Path

from app.cbf_scraper import (
    _canonical_team_name,
    _club_state,
    _parse_date,
    _parse_event_time,
    _split_local,
    parse_round,
)

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "cbf_rodada_sample.json").read_text(encoding="utf-8")
)


def test_canonical_team_name_merges_known_aliases():
    # mesmo clube, nome diferente entre temporadas na CBF (spec secao 3) --
    # sem isso o clube vira dois Team distintos.
    assert _canonical_team_name("Atlético") == "Atlético Goianiense"
    assert _canonical_team_name("Coritiba SAF") == "Coritiba"
    assert _canonical_team_name("Vasco da Gama Saf") == "Vasco da Gama"
    assert _canonical_team_name("Atlético Goianiense Saf") == "Atlético Goianiense"
    assert _canonical_team_name("Fortaleza SAF") == "Fortaleza Esporte Clube"
    # nomes de 2018-2021 (razao social / sem acento) caem no mesmo clube de hoje
    assert _canonical_team_name("America") == "América"
    assert _canonical_team_name("Botafogo de Futebol E Regatas") == "Botafogo"
    assert _canonical_team_name("Cruzeiro Esporte Clube") == "Cruzeiro"
    assert _canonical_team_name("Esporte Clube Bahia") == "Bahia"
    # time sem alias conhecido fica igual (so tira sufixo " Saf" generico)
    assert _canonical_team_name("Flamengo") == "Flamengo"
    assert _canonical_team_name("Botafogo Saf") == "Botafogo"


def test_split_local():
    assert _split_local("Couto Pereira - Curitiba - PR") == ("Couto Pereira", "Curitiba", "PR")
    assert _split_local(None) == (None, None, None)


def test_parse_date():
    assert _parse_date(" 11/09/2026") == "2026-09-11"
    assert _parse_date(None) is None


def test_parse_round_extracts_two_matches():
    matches = parse_round(FIXTURE, season=2026)
    assert len(matches) == 2
    m = matches[0]
    assert m["cbf_id"] == 832158
    assert m["season"] == 2026
    assert m["date"] == "2026-09-11"
    assert m["venue_stadium"] == "Couto Pereira"
    assert m["venue_city"] == "Curitiba"
    assert m["venue_state"] == "PR"
    assert m["home_team"]["name"] == "Coritiba"  # normalizado, ver _canonical_team_name
    assert m["away_team"]["name"] == "Athletico Paranaense"
    assert m["home_score"] == 3
    assert m["away_score"] == 3


def test_parse_round_picks_only_main_referee():
    m = parse_round(FIXTURE, season=2026)[0]
    assert m["referee"]["name"] == "Wagner do Nascimento Magalhaes"
    # nao pode vir assistente/quarto arbitro/VAR/assessor -- so um arbitro
    assert m["referee"] is not None


def test_parse_round_maps_card_types():
    m = parse_round(FIXTURE, season=2026)[0]
    types = {e["type"] for e in m["events"]}
    assert "YELLOW_CARD" in types
    assert "RED_CARD" in types  # vem de VERMELHO2AMARELO
    # nenhum evento de cartao deveria ter sobrado sem mapear pra um dos dois
    for e in m["events"]:
        assert e["type"] in ("GOAL", "YELLOW_CARD", "RED_CARD")


def test_parse_round_maps_goal_detail():
    m = parse_round(FIXTURE, season=2026)[0]
    goal_details = {e["detail"] for e in m["events"] if e["type"] == "GOAL"}
    # a rodada de exemplo tem gol normal e penalti nesse jogo
    assert "normal" in goal_details or "penalti" in goal_details


def test_parse_round_event_team_is_home_or_away():
    m = parse_round(FIXTURE, season=2026)[0]
    valid_ids = {m["home_team"]["cbf_id"], m["away_team"]["cbf_id"]}
    for e in m["events"]:
        assert e["team_cbf_id"] in valid_ids


def test_parse_event_time_handles_every_period():
    # minuto da CBF e relativo a cada tempo; acrescimo vem colado no 45
    # (spec 9.5) -- antes, todo acrescimo/intervalo/pos-jogo virava 45
    assert _parse_event_time("1", "13:00") == ("1T", 13)
    assert _parse_event_time("TN1", "39:00") == ("1T", 39)
    assert _parse_event_time("TN2", "13:00") == ("2T", 58)
    assert _parse_event_time("2", "45:00") == ("2T", 90)
    assert _parse_event_time("AC1", "45:003:00") == ("AC1", 48)
    assert _parse_event_time("AC2", "45:006:00") == ("AC2", 96)
    assert _parse_event_time("INT", "45:0000:00") == ("INT", 45)
    assert _parse_event_time("PJ", "45:0000:00") == ("PJ", 90)
    assert _parse_event_time(None, None) == (None, None)


def test_parse_round_events_carry_period_and_absolute_minute():
    events = [e for m in parse_round(FIXTURE, season=2026) for e in m["events"]]
    periods = {e["period"] for e in events}
    assert periods <= {"1T", "2T", "AC1", "AC2", "INT", "PJ"}
    assert {"AC1", "AC2"} & periods  # o exemplo tem cartao em acrescimo
    for e in events:
        if e["period"] == "1T":
            assert 0 <= e["minute"] <= 45
        elif e["period"] == "2T":
            assert 45 <= e["minute"] <= 90
        elif e["period"] == "AC1":
            assert 45 < e["minute"] < 60
        elif e["period"] == "AC2":
            assert e["minute"] > 90


def test_club_state():
    assert _club_state("Athletico Paranaense - PR") == "PR"
    assert _club_state("Coritiba SAF - PR") == "PR"
    assert _club_state("sem uf") is None
    assert _club_state(None) is None


def test_parse_round_referee_federation_category_and_var():
    m = parse_round(FIXTURE, season=2026)[0]
    assert m["referee"] == {"cbf_id": 885, "name": "Wagner do Nascimento Magalhaes",
                            "uf": "RJ", "category": "MASTER-PRO"}
    assert m["var_referee"] == {"cbf_id": 883, "name": "Rodrigo Nunes de Sa",
                                "uf": "RJ", "category": "VAR-FIFA-PRO"}
    assert m["home_team"]["state"] == "PR"
    assert m["away_team"]["state"] == "PR"


def test_new_alias_renames_club_found_by_cbf_id(db_session):
    from app.models import Team
    from scripts.scrape_cbf import _get_or_create_team

    db_session.add(Team(api_id=7, name="Csa"))
    db_session.flush()
    team = _get_or_create_team(db_session, 7, "CSA", "AL")
    assert team.name == "CSA" and team.state == "AL"
    assert db_session.query(Team).count() == 1  # renomeou, nao duplicou


def test_ingest_stores_federation_category_var_and_period(db_session):
    from app.models import Fixture, MatchEvent, Referee, Team
    from scripts.scrape_cbf import ingest_matches

    ingest_matches(db_session, parse_round(FIXTURE, season=2026))

    coritiba = db_session.query(Team).filter_by(name="Coritiba").one()
    assert coritiba.state == "PR"
    fx = db_session.query(Fixture).filter_by(api_id=832158).one()
    assert fx.referee.name == "Wagner do Nascimento Magalhaes"
    assert fx.referee.uf == "RJ"
    assert fx.referee_category == "MASTER-PRO"
    assert fx.var_referee.name == "Rodrigo Nunes de Sa"
    assert fx.var_category == "VAR-FIFA-PRO"
    periods = {e.period for e in db_session.query(MatchEvent).filter_by(fixture_id=fx.id)}
    assert periods and None not in periods
    # VAR tambem e arbitro -- mesma tabela, sem duplicar ninguem
    assert db_session.query(Referee).filter_by(name="Rodrigo Nunes de Sa").count() == 1


def _client(responses):
    import httpx

    calls = iter(responses)

    def handler(request):
        item = next(calls)
        if isinstance(item, Exception):
            raise item
        return httpx.Response(item, json={"jogos": []}, request=request)

    return httpx.Client(base_url="https://cbf.test", transport=httpx.MockTransport(handler))


def test_fetch_round_retries_transient_server_errors():
    import httpx

    from app.cbf_scraper import fetch_round

    client = _client([502, httpx.ConnectTimeout("lento"), 200])
    assert fetch_round(client, 1, 6, waits=(0, 0, 0)) == {"jogos": []}


def test_fetch_round_gives_up_after_the_last_retry():
    import httpx
    import pytest

    from app.cbf_scraper import fetch_round

    client = _client([502, 503, 502])
    with pytest.raises(httpx.HTTPStatusError):
        fetch_round(client, 1, 6, waits=(0, 0))


def test_fetch_round_does_not_retry_client_errors():
    import httpx
    import pytest

    from app.cbf_scraper import fetch_round

    client = _client([404])  # uma resposta so: se tentar de novo, StopIteration
    with pytest.raises(httpx.HTTPStatusError):
        fetch_round(client, 1, 99, waits=(0, 0))
