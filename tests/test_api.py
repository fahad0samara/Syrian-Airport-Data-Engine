import pytest
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

def test_api_airport():
    res = client.get("/api/airport")
    assert res.status_code == 200
    data = res.json()
    assert data["iata_code"] == "DAM"
    assert data["ident"] == "OSDI"

def test_api_flights():
    res = client.get("/api/flights?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "data" in data
    assert isinstance(data["data"], list)
    if len(data["data"]) > 0:
        f = data["data"][0]
        assert f["airport_iata"] == "DAM"
        assert f["movement_type"] in ("arrival", "departure")

def test_api_daily_movements():
    res = client.get("/api/movements/daily")
    assert res.status_code == 200
    data = res.json()
    assert "total_days" in data
    assert "data" in data

def test_api_historical_2024():
    res = client.get("/api/movements/historical-2024?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0
    assert len(data["data"]) > 0
    first = data["data"][0]
    assert first["scope"] == "DAM_ALP_LTK"

def test_api_stats():
    res = client.get("/api/movements/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["iata"] == "DAM"
    assert data["total_verified_flights"] > 0
    assert "unique_aircraft_tracked" in data
    assert "top_connected_airports" in data

def test_api_coverage():
    res = client.get("/api/coverage")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0

def test_api_quality():
    res = client.get("/api/quality")
    assert res.status_code == 200
    data = res.json()
    assert data["overall_status"] == "PASSED"

def test_api_export():
    res = client.get("/api/export/damascus_flights?format=csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
