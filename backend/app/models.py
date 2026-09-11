from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    api_id: Mapped[int] = mapped_column(unique=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True)


class Referee(Base):
    __tablename__ = "referees"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)


class Fixture(Base):
    __tablename__ = "fixtures"
    __table_args__ = (UniqueConstraint("api_id", name="uq_fixture_api_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    api_id: Mapped[int] = mapped_column(index=True)
    competition: Mapped[str] = mapped_column(String, default="Brasileirao Serie A")
    season: Mapped[int] = mapped_column(Integer, index=True)
    round: Mapped[str] = mapped_column(String, nullable=True)
    date: Mapped[str] = mapped_column(String, nullable=True)  # ISO yyyy-mm-dd

    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    referee_id: Mapped[int] = mapped_column(ForeignKey("referees.id"), nullable=True)

    home_score: Mapped[int] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int] = mapped_column(Integer, nullable=True)

    # true assim que a ingestao ja tentou buscar /fixtures/events para esta
    # partida (mesmo que o resultado tenha sido zero eventos) -- distingue
    # "0 cartoes de verdade" de "ainda nao ingerido" (spec secao 8).
    events_ingested: Mapped[bool] = mapped_column(Boolean, default=False)

    home_team: Mapped["Team"] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped["Team"] = relationship(foreign_keys=[away_team_id])
    referee: Mapped["Referee"] = relationship()


class MatchEvent(Base):
    __tablename__ = "match_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    player_name: Mapped[str] = mapped_column(String, nullable=True)
    minute: Mapped[int] = mapped_column(Integer, nullable=True)
    type: Mapped[str] = mapped_column(String)  # GOAL | YELLOW_CARD | RED_CARD
    detail: Mapped[str] = mapped_column(String, nullable=True)
