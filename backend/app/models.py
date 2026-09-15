from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    api_id: Mapped[int] = mapped_column(unique=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    # UF do clube, do campo "clube" dos eventos da CBF ("Nome - UF") --
    # usado pela regra de federacao e pela afinidade regional (spec 9.3/9.4)
    state: Mapped[str] = mapped_column(String, nullable=True)


class Referee(Base):
    __tablename__ = "referees"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    cbf_id: Mapped[int] = mapped_column(Integer, nullable=True, unique=True)
    uf: Mapped[str] = mapped_column(String, nullable=True)  # federacao do arbitro (nao muda entre temporadas)


class Fixture(Base):
    __tablename__ = "fixtures"
    __table_args__ = (UniqueConstraint("source", "api_id", name="uq_fixture_source_api_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    api_id: Mapped[int] = mapped_column(index=True)
    source: Mapped[str] = mapped_column(String, default="api-football", index=True)  # "cbf" | "api-football"
    competition: Mapped[str] = mapped_column(String, default="Brasileirao Serie A")
    season: Mapped[int] = mapped_column(Integer, index=True)
    round: Mapped[str] = mapped_column(String, nullable=True)
    date: Mapped[str] = mapped_column(String, nullable=True)  # ISO yyyy-mm-dd

    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    referee_id: Mapped[int] = mapped_column(ForeignKey("referees.id"), nullable=True)
    # categoria muda de temporada pra temporada (arbitro promovido a FIFA),
    # por isso fica no jogo e nao no Referee
    referee_category: Mapped[str] = mapped_column(String, nullable=True)
    var_referee_id: Mapped[int] = mapped_column(ForeignKey("referees.id"), nullable=True)
    var_category: Mapped[str] = mapped_column(String, nullable=True)

    home_score: Mapped[int] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int] = mapped_column(Integer, nullable=True)

    venue_stadium: Mapped[str] = mapped_column(String, nullable=True)
    venue_city: Mapped[str] = mapped_column(String, nullable=True)
    venue_state: Mapped[str] = mapped_column(String, nullable=True)

    # true assim que a ingestao ja tentou buscar cartao/gol pra essa partida
    # (mesmo que o resultado tenha sido zero eventos) -- distingue "0
    # cartoes de verdade" de "ainda nao ingerido" (spec secao 8). O scraper
    # da CBF preenche isso no mesmo request que traz o resto (nao precisa de
    # segunda chamada como o ingest.py da API-Football).
    events_ingested: Mapped[bool] = mapped_column(Boolean, default=False)

    home_team: Mapped["Team"] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped["Team"] = relationship(foreign_keys=[away_team_id])
    referee: Mapped["Referee"] = relationship(foreign_keys=[referee_id])
    var_referee: Mapped["Referee"] = relationship(foreign_keys=[var_referee_id])


class IngestionLog(Base):
    """1 linha por rodada de scraping bem-sucedida. Alimenta o
    'atualizado em' mostrado no dashboard e o cron semanal sabe por onde
    parou sem precisar reprocessar tudo (spec secao 3)."""
    __tablename__ = "ingestion_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String, index=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    round: Mapped[int] = mapped_column(Integer, nullable=True)
    finished_at: Mapped[str] = mapped_column(String)  # ISO 8601 UTC
    matches: Mapped[int] = mapped_column(Integer, default=0)
    events: Mapped[int] = mapped_column(Integer, default=0)


class MatchEvent(Base):
    __tablename__ = "match_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    player_name: Mapped[str] = mapped_column(String, nullable=True)
    # minuto ABSOLUTO do jogo (2o tempo 13' = 58; acrescimo do 2o tempo +3 =
    # 93) -- com period da pra saber se 45 e fim do 1o tempo ou intervalo
    minute: Mapped[int] = mapped_column(Integer, nullable=True)
    period: Mapped[str] = mapped_column(String, nullable=True)  # 1T | 2T | AC1 | AC2 | INT | PJ
    type: Mapped[str] = mapped_column(String)  # GOAL | YELLOW_CARD | RED_CARD
    detail: Mapped[str] = mapped_column(String, nullable=True)


class StatReport(Base):
    """Resultado pronto da aba Dados estatisticos (spec secao 9.6): calculado
    offline por scripts/compute_stats.py (numpy/statsmodels, grupo
    'analysis') e so LIDO pela API -- funcao serverless leve na Vercel."""
    __tablename__ = "stat_reports"

    key: Mapped[str] = mapped_column(String, primary_key=True)  # "2025" ou "all"
    method_version: Mapped[int] = mapped_column(Integer)
    data_version: Mapped[str] = mapped_column(String)
    computed_at: Mapped[str] = mapped_column(String)  # ISO 8601 UTC
    payload: Mapped[dict] = mapped_column(JSON)
