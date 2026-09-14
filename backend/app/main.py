from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app import mock_store, queries
from app.db import Base, engine, get_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="ApitaCerto API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/filters")
def get_filters(db: Session = Depends(get_db)):
    real = queries.get_filter_options(db)
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


@app.get("/dashboard")
def get_dashboard(
    season: int = Query(..., ge=2022, le=2024),
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
        }
    else:
        # ainda sem dado real ingerido pra essa temporada (spec secao 8:
        # ingestao e limitada por request/dia) -- cai pro mock deterministico
        # ao inves de devolver dashboard vazio.
        heatmap = mock_store.build_heatmap(season)
        timeseries = mock_store.timeseries_for(team, season)
        data_completeness = {"isReal": False, "fixtures": 0, "fixturesWithCards": 0}

    kpis = queries.kpis_for(heatmap, team, referee)
    return {
        "kpis": kpis, "timeseries": timeseries, "heatmap": heatmap,
        "dataCompleteness": data_completeness,
    }
