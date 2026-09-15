from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_filters_returns_expected_shape():
    res = client.get("/filters")
    assert res.status_code == 200
    body = res.json()
    assert set(body.keys()) == {"teams", "referees", "seasons"}
    assert "Palmeiras" in body["teams"]
    assert 2023 in body["seasons"]
    assert body["seasons"] == sorted(body["seasons"])


def test_dashboard_requires_season():
    res = client.get("/dashboard")
    assert res.status_code == 422


def test_dashboard_rejects_season_outside_supported_range():
    # COMPETITION_IDS da CBF comeca em 2018 (spec secao 9.5); antes disso, 422
    assert client.get("/dashboard", params={"season": 2017}).status_code == 422
    assert client.get("/dashboard", params={"season": 2101}).status_code == 422
    assert client.get("/dashboard", params={"season": 2018}).status_code == 200
    assert client.get("/dashboard", params={"season": 2026}).status_code == 200


def test_dashboard_shape_no_filters():
    res = client.get("/dashboard", params={"season": 2023})
    assert res.status_code == 200
    body = res.json()
    assert set(body.keys()) == {"kpis", "timeseries", "heatmap", "dataCompleteness"}

    kpis = body["kpis"]
    assert set(kpis.keys()) == {
        "games", "wins", "draws", "losses", "winRatePct",
        "goalsFor", "goalsAgainst", "yellow", "red",
    }
    assert kpis["games"] == kpis["wins"] + kpis["draws"] + kpis["losses"]

    assert len(body["timeseries"]) == 20
    assert set(body["timeseries"][0].keys()) == {"round", "winRatePct", "yellow", "red"}

    assert len(body["heatmap"]) > 0
    cell = body["heatmap"][0]
    assert set(cell.keys()) >= {
        "team", "referee", "n", "insufficientSample", "index",
    }


def test_dashboard_filters_by_team_reduces_games():
    all_teams = client.get("/dashboard", params={"season": 2023}).json()
    one_team = client.get("/dashboard", params={"season": 2023, "team": "Palmeiras"}).json()
    assert one_team["kpis"]["games"] < all_teams["kpis"]["games"]
    assert one_team["kpis"]["games"] > 0


def test_dashboard_unknown_team_returns_zeroed_kpis_not_error():
    res = client.get("/dashboard", params={"season": 2023, "team": "Time Que Nao Existe"})
    assert res.status_code == 200
    assert res.json()["kpis"]["games"] == 0


def test_heatmap_marks_low_sample_pairs_as_insufficient():
    body = client.get("/dashboard", params={"season": 2023}).json()
    for cell in body["heatmap"]:
        if cell["n"] < 5:
            assert cell["insufficientSample"] is True
            assert cell["index"] is None
        else:
            assert cell["insufficientSample"] is False
            assert cell["index"] is not None


def test_cors_allows_frontend_origin():
    res = client.get("/filters", headers={"Origin": "http://localhost:5173"})
    assert res.headers.get("access-control-allow-origin") in ("http://localhost:5173", "*")
