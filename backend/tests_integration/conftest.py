"""Integracao contra Postgres de verdade e a API de verdade, por HTTP.

Diferente de tests/ (SQLite em memoria, TestClient), aqui:
- o banco e o Postgres apontado por INTEGRATION_DATABASE_URL;
- a API roda como servidor uvicorn num processo separado, ou, se
  APITACERTO_API_URL estiver definido, e uma API ja no ar (Docker Compose,
  kind) que usa esse mesmo banco.

Sem INTEGRATION_DATABASE_URL tudo aqui e pulado, entao `uv run pytest`
continua rodando sem Docker. O banco e apagado e recriado a cada teste: por
seguranca, so aceita banco com "test" no nome.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.db import Base, ensure_schema

BACKEND_DIR = Path(__file__).resolve().parents[1]
DB_URL = os.environ.get("INTEGRATION_DATABASE_URL")
EXTERNAL_API = os.environ.get("APITACERTO_API_URL")

pytestmark = pytest.mark.skipif(not DB_URL, reason="INTEGRATION_DATABASE_URL nao definido")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_healthy(base_url: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            res = httpx.get(f"{base_url}/health", timeout=2)
            if res.status_code == 200:
                return
            last = res.status_code
        except httpx.HTTPError as exc:
            last = exc
        time.sleep(0.5)
    raise RuntimeError(f"API em {base_url} nao ficou saudavel: {last}")


@pytest.fixture(scope="session")
def engine():
    if not DB_URL:
        pytest.skip("INTEGRATION_DATABASE_URL nao definido")
    url = make_url(DB_URL)
    if "test" not in (url.database or ""):
        pytest.exit(f"recusado: banco '{url.database}' nao tem 'test' no nome e seria apagado")
    eng = create_engine(DB_URL)
    yield eng
    eng.dispose()


@pytest.fixture(scope="session")
def api_url(engine):
    if EXTERNAL_API:
        base = EXTERNAL_API.rstrip("/")
        _wait_healthy(base)
        yield base
        return

    ensure_schema(bind=engine)  # a API nova sobe com o schema pronto
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": DB_URL},
    )
    base = f"http://127.0.0.1:{port}"
    try:
        _wait_healthy(base)
        yield base
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.fixture
def db_session(engine):
    # banco zerado a cada teste: cada cenario parte do vazio
    Base.metadata.drop_all(bind=engine)
    ensure_schema(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def api(api_url):
    with httpx.Client(base_url=api_url, timeout=10) as client:
        yield client
