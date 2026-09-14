"""Testa app/cbf_scraper.parse_round contra um payload real (trimmado, sem
os elencos que o parser nao usa) da API publica da CBF -- sem tocar rede,
ver tests/fixtures/cbf_rodada_sample.json."""
import json
from pathlib import Path

from app.cbf_scraper import _canonical_team_name, _parse_date, _split_local, parse_round

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
