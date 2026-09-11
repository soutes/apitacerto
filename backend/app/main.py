from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app import mock_store

app = FastAPI(title="ApitaCerto API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/filters")
def get_filters():
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
):
    heatmap = mock_store.build_heatmap(season)
    kpis = mock_store.kpis_for(heatmap, team, referee)
    timeseries = mock_store.timeseries_for(team, season)
    return {"kpis": kpis, "timeseries": timeseries, "heatmap": heatmap}
