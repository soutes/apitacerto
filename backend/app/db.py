import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Database-agnostic (HW2 Q7): defaults to SQLite for local dev, but any
# SQLAlchemy URL works (e.g. postgresql://...) without touching queries.py.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./apitacerto.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# Colunas criadas depois das tabelas originais. create_all nao altera tabela
# que ja existe, entao o SQLite local antigo precisa do ALTER; banco novo
# (Neon/Postgres na Vercel) ja nasce completo pelo create_all.
_ADDED_COLUMNS = {
    "teams": {"state": "VARCHAR"},
    "referees": {"uf": "VARCHAR"},
    "fixtures": {"referee_category": "VARCHAR", "var_referee_id": "INTEGER", "var_category": "VARCHAR"},
    "match_events": {"period": "VARCHAR"},
}


def ensure_schema(bind=engine) -> None:
    from app import models  # noqa: F401  (registra as tabelas no Base)

    Base.metadata.create_all(bind=bind)
    existing = {t: {c["name"] for c in inspect(bind).get_columns(t)} for t in _ADDED_COLUMNS}
    with bind.begin() as conn:
        for table, cols in _ADDED_COLUMNS.items():
            for col, ddl_type in cols.items():
                if col not in existing[table]:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl_type}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
