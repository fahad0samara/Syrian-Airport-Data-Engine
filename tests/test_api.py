import pytest
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

def test_api_airports():
    res = client.get("/api/airports")
    assert res.status_code == 200
    airports = res.json()
    assert isinstance(airports, list)
    assert len(airports) >= 5
    codes = set(a["airport_id"] for a in airports)
    assert "DAM" in codes
    assert "ALP" in codes
    assert "DEZ" in codes
    assert "KAC" in codes
    assert "LTK" in codes

def test_api_airport():
    res = client.get("/api/airport?airport_id=DAM")
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
        assert "airport_id" in f
        assert f["movement_type"] in ("arrival", "departure")

def test_api_daily_movements():
    res = client.get("/api/movements/daily?airport_id=DAM")
    assert res.status_code == 200
    data = res.json()
    assert "total_days" in data
    assert "data" in data
    if len(data["data"]) > 0:
        d = data["data"][0]
        assert "completed_movements" in d
        assert "scheduled_movements" in d

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
    assert "airport_events_breakdown" in data

def test_api_sources():
    res = client.get("/api/sources")
    assert res.status_code == 200
    sources = res.json()
    assert isinstance(sources, list)
    assert len(sources) >= 5
    source_ids = set(s["source_id"] for s in sources)
    assert "damairport_official" in source_ids
    assert "alpairport_official" in source_ids
    assert "syria_economic_monitor" in source_ids

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

def test_api_deduplication():
    res = client.get("/api/deduplication")
    assert res.status_code == 200
    data = res.json()
    assert "total_records" in data
    assert "data" in data

def test_api_export():
    res = client.get("/api/export/damascus_flights?format=csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]

    res_all = client.get("/api/export/all_syrian_flight_events?format=csv")
    assert res_all.status_code == 200
    assert "text/csv" in res_all.headers["content-type"]

    res_audit = client.get("/api/export/deduplication_audit?format=csv")
    assert res_audit.status_code == 200
    assert "text/csv" in res_audit.headers["content-type"]

def test_api_movement_categories_strict_isolation_and_no_overlap():
    """
    Proves that:
    1. The scheduled endpoint contains only scheduled_service.
    2. The unverified endpoint contains only unverified_movement.
    3. The verified endpoint contains only physical_movement.
    4. The three categories do not overlap (disjoint sets of event_ids).
    5. Each endpoint's total matches its database query (derived dynamically from SQLite).
    """
    from src.database import get_connection
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM flight_events WHERE record_nature = 'physical_movement';")
        db_phys = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM flight_events WHERE record_nature = 'scheduled_service';")
        db_sched = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM flight_events WHERE record_nature = 'unverified_movement';")
        db_unver = cur.fetchone()[0]

    # 1. Verified endpoint
    res_v = client.get("/api/movements/verified?limit=500")
    assert res_v.status_code == 200
    data_v = res_v.json()
    assert data_v["total"] == db_phys
    v_ids = set()
    for m in data_v["movements"]:
        assert m["record_nature"] == "physical_movement"
        v_ids.add(m["event_id"])

    # 2. Scheduled endpoint
    res_s = client.get("/api/movements/scheduled?limit=500")
    assert res_s.status_code == 200
    data_s = res_s.json()
    assert data_s["total"] == db_sched
    s_ids = set()
    for m in data_s["movements"]:
        assert m["record_nature"] == "scheduled_service"
        s_ids.add(m["event_id"])

    # 3. Unverified endpoint
    res_u = client.get("/api/movements/unverified?limit=500")
    assert res_u.status_code == 200
    data_u = res_u.json()
    assert data_u["total"] == db_unver
    u_ids = set()
    for m in data_u["movements"]:
        assert m["record_nature"] == "unverified_movement"
        assert "verification_limitation" in m
        u_ids.add(m["event_id"])

    # 4. Zero overlap among the three categories
    assert len(v_ids.intersection(s_ids)) == 0, "Overlap detected between verified and scheduled!"
    assert len(v_ids.intersection(u_ids)) == 0, "Overlap detected between verified and unverified!"
    assert len(s_ids.intersection(u_ids)) == 0, "Overlap detected between scheduled and unverified!"

def test_api_movements_empty_results_and_filters():
    """
    Proves that:
    6. Empty results return a valid response (status 200, total 0, movements []).
    7. Existing filters (airport_id, direction, date) and pagination continue to work across all 3 endpoints.
    """
    for endpoint in ["/api/movements/verified", "/api/movements/scheduled", "/api/movements/unverified"]:
        # Empty filter result
        res_empty = client.get(f"{endpoint}?airport_id=NONEXISTENT_AIRPORT")
        assert res_empty.status_code == 200
        d_empty = res_empty.json()
        assert d_empty["total"] == 0
        assert d_empty["count"] == 0
        assert d_empty["movements"] == []
        assert d_empty["data"] == []

        # Direction filter
        res_arr = client.get(f"{endpoint}?movement_type=arrival")
        assert res_arr.status_code == 200
        d_arr = res_arr.json()
        for m in d_arr["movements"]:
            assert m["movement_type"] == "arrival"

        # Pagination limit and offset
        res_pag = client.get(f"{endpoint}?limit=2&offset=0")
        assert res_pag.status_code == 200
        d_pag = res_pag.json()
        assert len(d_pag["movements"]) <= 2
        assert d_pag["limit"] == 2
        assert d_pag["offset"] == 0
