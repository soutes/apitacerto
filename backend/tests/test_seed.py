from sqlalchemy import create_engine, func, select

from app.models import Fixture, MatchEvent, Referee, StatReport, Team
from scripts.seed import export_seed, load_seed


def _populate(engine):
    from sqlalchemy.orm import Session

    from app.db import ensure_schema

    ensure_schema(bind=engine)
    with Session(engine) as db:
        a, b = Team(api_id=1, name="Time A", state="SP"), Team(api_id=2, name="Time B")
        ref = Referee(name="Arbitro X", cbf_id=9, uf="RJ")
        db.add_all([a, b, ref])
        db.flush()
        fx = Fixture(api_id=10, source="cbf", season=2025, round="1", home_team_id=a.id,
                     away_team_id=b.id, referee_id=ref.id, home_score=2, away_score=1,
                     events_ingested=True)
        db.add(fx)
        db.flush()
        db.add(MatchEvent(fixture_id=fx.id, team_id=b.id, type="YELLOW_CARD", minute=30, period="1T"))
        db.add(StatReport(key="all", method_version=1, data_version="v", computed_at="t",
                          payload={"pares": [{"z": 1.5, "nome": "São Paulo"}]}))
        db.commit()


def test_export_then_load_reproduces_the_database(tmp_path):
    source = create_engine(f"sqlite:///{tmp_path / 'src.db'}")
    _populate(source)
    seed_file = tmp_path / "seed.json.gz"

    exported = export_seed(source, seed_file)
    assert exported["fixtures"] == 1 and exported["match_events"] == 1

    target = create_engine(f"sqlite:///{tmp_path / 'dst.db'}")
    assert load_seed(target, seed_file) == exported

    with target.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(Fixture.__table__)) == 1
        payload = conn.execute(select(StatReport.__table__.c.payload)).scalar_one()
    assert payload == {"pares": [{"z": 1.5, "nome": "São Paulo"}]}


def test_load_does_not_touch_a_database_that_already_has_games(tmp_path):
    source = create_engine(f"sqlite:///{tmp_path / 'src.db'}")
    _populate(source)
    seed_file = tmp_path / "seed.json.gz"
    export_seed(source, seed_file)

    assert load_seed(source, seed_file) is None  # ja tem jogo: idempotente
    with source.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(Fixture.__table__)) == 1


def test_export_is_deterministic(tmp_path):
    source = create_engine(f"sqlite:///{tmp_path / 'src.db'}")
    _populate(source)
    export_seed(source, tmp_path / "a.json.gz")
    export_seed(source, tmp_path / "b.json.gz")
    assert (tmp_path / "a.json.gz").read_bytes() == (tmp_path / "b.json.gz").read_bytes()
