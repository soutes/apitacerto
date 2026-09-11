import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Database-agnostic (HW2 Q7): defaults to SQLite for local dev, but any
# SQLAlchemy URL works (e.g. postgresql://...) without touching queries.py.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./apitacerto.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
