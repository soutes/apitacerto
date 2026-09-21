import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import mock_store, queries
from app.db import ensure_schema, get_db
from app.models import StatReport

MIN_SEASON = 2018  # primeira temporada com competitionId conhecido (cbf_scraper.COMPETITION_IDS)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_schema()
    yield


app = FastAPI(title="ApitaCerto API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    # readiness do Kubernetes e smoke test do CI: so fica pronto quando o
    # banco responde, entao o pod nao recebe trafego antes do Postgres subir
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "error", "database": "unreachable"})
    return {"status": "ok", "database": "ok"}


@app.get("/filters")
def get_filters(season: Optional[int] = None, db: Session = Depends(get_db)):
    real = queries.get_filter_options(db, season)
    if real["seasons"]:
        # une o que ja foi ingerido com as temporadas que o free tier cobre,
        # pra o filtro de temporada nao encolher enquanto a ingestao roda
        seasons = sorted(set(real["seasons"]) | set(mock_store.SEASONS))
        teams = real["teams"] or mock_store.TEAMS
        referees = real["referees"] or mock_store.REFEREES
        return {"teams": teams, "referees": referees, "seasons": seasons}
    return {
        "teams": mock_store.TEAMS,
        "referees": mock_store.REFEREES,
        "seasons": mock_store.SEASONS,
    }


@app.get("/season-overview")
def get_season_overview(season: int = Query(..., ge=MIN_SEASON, le=2100), db: Session = Depends(get_db)):
    # KPIs de temporada + rankings de arbitro (mais cartao, vies de mandante)
    # pra tela Dashboard do redesign (design_handoff 2026-09-14). Sem dado
    # real ainda pra essa temporada -> tudo zerado, nao inventa ranking.
    if queries.has_ingested_data(db, season):
        return queries.season_overview(db, season)
    return {
        "currentRound": 0, "gamesPlayed": 0, "cardsPerGame": 0.0,
        "homeWinPct": 0.0, "goalsPerGame": 0.0,
        "mostCardsReferees": [], "homeBiasReferees": [], "allReferees": [],
    }


@app.get("/statistics")
def get_statistics(season: Optional[int] = None, db: Session = Depends(get_db)):
    # aba Favorecimento (spec secao 9): so LE o JSON que
    # scripts/compute_stats.py calculou offline. Importar app.analysis aqui
    # levaria numpy/statsmodels pro pacote da funcao serverless (spec 9.6).
    key = str(season) if season is not None else "all"
    report = db.get(StatReport, key)
    if report is None:
        raise HTTPException(status_code=404,
                            detail="Estatísticas ainda não calculadas para esse recorte (rode scripts/compute_stats.py)")
    return {**report.payload, "computedAt": report.computed_at, "dataVersion": report.data_version}


@app.get("/dashboard")
def get_dashboard(
    season: int = Query(..., ge=MIN_SEASON, le=2100),
    team: Optional[str] = None,
    referee: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if queries.has_ingested_data(db, season):
        heatmap = queries.build_heatmap(db, season)
        timeseries = queries.timeseries_for(db, team, season)
        progress = queries.ingestion_progress(db, season)
        data_completeness = {
            "isReal": True,
            "fixtures": progress["fixtures"],
            "fixturesWithCards": progress["fixturesWithCards"],
            "lastUpdated": queries.last_updated(db, season),
        }
    else:
        # ainda sem dado real ingerido pra essa temporada (spec secao 8:
        # ingestao e limitada por request/dia) -- cai pro mock deterministico
        # ao inves de devolver dashboard vazio.
        heatmap = mock_store.build_heatmap(season)
        timeseries = mock_store.timeseries_for(team, season)
        data_completeness = {
            "isReal": False, "fixtures": 0, "fixturesWithCards": 0, "lastUpdated": None,
        }

    kpis = queries.kpis_for(heatmap, team, referee)
    return {
        "kpis": kpis, "timeseries": timeseries, "heatmap": heatmap,
        "dataCompleteness": data_completeness,
    }


def mount_frontend(target: FastAPI, static_dir: str | Path) -> None:
    # Na imagem Docker a API tambem serve o build do React (mesma origem,
    # sem CORS). Montado por ultimo: as rotas da API acima tem prioridade.
    target.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")


if os.environ.get("STATIC_DIR"):
    mount_frontend(app, os.environ["STATIC_DIR"])
