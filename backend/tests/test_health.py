from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db import get_db
from app.main import app

client = TestClient(app)


def test_health_ok_when_database_answers():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "ok"}


class _BrokenSession:
    def execute(self, *_args, **_kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def test_health_503_when_database_is_down():
    # readiness do Kubernetes depende disso: banco fora = pod fora do Service
    original = app.dependency_overrides[get_db]
    app.dependency_overrides[get_db] = lambda: _BrokenSession()
    try:
        res = client.get("/health")
    finally:
        app.dependency_overrides[get_db] = original
    assert res.status_code == 503
    assert res.json() == {"status": "error", "database": "unreachable"}
