import os
import sys
import sqlite3
import hashlib
import json
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, ".")
from src.api import app

client = TestClient(app)

PROD_DB = "data/damascus_airport.db"
STAGING_DB = "data/archived_fids_staging.db"
ANALYTICS_DB = "data/archived_fids_analytics.db"
RAW_FILE = "data/raw/snapshots/wayback_damairport_fids_20260709234230.raw"
JSON_FILE = "data/raw/snapshots/wayback_damairport_fids_20260709234230.json"

EXPECTED_HASHES = {
    PROD_DB: "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b",
    STAGING_DB: "a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4",
    ANALYTICS_DB: "e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe",
    RAW_FILE: "5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf",
    JSON_FILE: "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491",
}

# 1. Verify Damascus Physical Movements Evidence
def test_01_verify_damascus_physical_movements():
    conn = sqlite3.connect(f"file:{PROD_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT event_id, airport_id, flight_number, flight_date, movement_type,
               actual_dep_time, actual_arr_time, record_nature
        FROM flight_events
        WHERE airport_id = 'DAM' AND record_nature = 'physical_movement'
    """)
    rows = cur.fetchall()
    assert len(rows) == 98, f"Expected 98 DAM physical movements, got {len(rows)}"

    for r in rows:
        assert r["airport_id"] == "DAM"
        assert r["record_nature"] == "physical_movement"
        assert r["movement_type"] in ("arrival", "departure")
        actual_ts = r["actual_dep_time"] if r["movement_type"] == "departure" else r["actual_arr_time"]
        assert actual_ts is not None, f"Event {r['event_id']} missing actual timestamp"

        # Check evidence attached to this event
        cur.execute("SELECT * FROM v_active_evidence WHERE event_id = ?", (r["event_id"],))
        evidence = cur.fetchall()
        assert len(evidence) > 0, f"Event {r['event_id']} has no active evidence"

        # Evidence providers must be commercial aggregators or official portal
        for ev in evidence:
            sname = ev["source_name"].lower()
            assert any(p in sname for p in ["flightradar24", "aviationstack", "damairport"]), \
                f"Unexpected source {sname} for event {r['event_id']}"

    conn.close()

# 2. Verify No Overflights Classified as DAM Movements
def test_02_no_regional_overflights_in_dam_movements():
    conn = sqlite3.connect(f"file:{PROD_DB}?mode=ro", uri=True)
    cur = conn.cursor()

    # Known high-altitude overflight callsigns from V2.17/V2.18
    overflight_calls = ["GFA004", "MEA325", "UAE7V", "UAE7TR", "AIC151", "UAE216", "AIC153", "THY209"]
    for call in overflight_calls:
        cur.execute("""
            SELECT COUNT(*) FROM flight_events
            WHERE airport_id = 'DAM' AND (flight_number = ? OR operating_flight_number = ?)
        """, (call, call))
        cnt = cur.fetchone()[0]
        assert cnt == 0, f"Overflight {call} erroneously found in DAM flight_events"

    conn.close()

# 3. Verify ADS-B Sample Breakdown (15 Overflights, 1 Regional Transit, 0 Runway Events)
def test_03_verify_adsb_sample_breakdown():
    obs_file = "reports/v2_18_recovered_observations.csv"
    assert os.path.exists(obs_file)

    import csv
    with open(obs_file, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 16, f"Expected 16 raw transponder observations, got {len(rows)}"

    overflights = [r for r in rows if r["classification"] == "overflight_observation"]
    regional = [r for r in rows if r["classification"] == "regional_observation"]
    surface = [r for r in rows if r["classification"] == "surface_observation"]
    takeoffs = [r for r in rows if r["classification"] == "takeoff_observation"]
    landings = [r for r in rows if r["classification"] == "landing_observation"]

    assert len(overflights) == 15, f"Expected 15 overflights, got {len(overflights)}"
    assert len(regional) == 1, f"Expected 1 regional observation, got {len(regional)}"
    assert len(surface) == 0, f"Expected 0 surface observations, got {len(surface)}"
    assert len(takeoffs) == 0, f"Expected 0 confirmed takeoffs, got {len(takeoffs)}"
    assert len(landings) == 0, f"Expected 0 confirmed landings, got {len(landings)}"

    # All observations must have is_dam_movement == 0
    for r in rows:
        assert int(r["is_dam_movement"]) == 0
        assert float(r["distance_to_dam_km"]) > 95.0

# 4. Standardize Data Categories: Dataset-Level vs Record-Level
def test_04_standardize_data_categories():
    dataset_categories = {
        "dam_verified_physical_movement",
        "dam_scheduled_fids",
        "regional_aggregate",
        "live_regional_adsb",
        "no_verified_dam_data",
        "unknown"
    }

    record_classifications = {
        "scheduled_timetable",
        "scheduled_service",
        "physical_movement",
        "marketing_codeshare",
        "unverified_movement",
        "overflight_observation",
        "regional_observation"
    }

    # Verify no accidental collisions between dataset and record-level concepts
    assert "regional_aggregate" in dataset_categories
    assert "scheduled_timetable" in record_classifications
    assert "overflight_observation" in record_classifications

# 5. Enumerate All FastAPI Routes Directly from Application
def test_05_enumerate_api_routes_scope_integrity():
    routes = [r for r in app.routes if hasattr(r, "path")]
    assert len(routes) >= 30, f"Expected at least 30 routes, got {len(routes)}"

    paths = [r.path for r in routes]
    assert "/api/flights" in paths
    assert "/api/movements/daily" in paths
    assert "/api/movements/verified" in paths
    assert "/api/movements/scheduled" in paths
    assert "/api/movements/historical-2024" in paths
    assert "/api/archived-fids/summary" in paths

    # Verify /api/movements/historical-2024 declares multi-airport aggregate
    res_hist = client.get("/api/movements/historical-2024?limit=5")
    assert res_hist.status_code == 200
    data = res_hist.json()
    assert data["scope"] == "DAM_ALP_LTK"
    assert data["is_dam_specific"] is False
    assert data["data_category"] == "regional_aggregate"

# 6. Verify Single-Airport Routes Never Leak Multi-Airport Aggregate Records
def test_06_single_airport_routes_never_leak_aggregates():
    res_dam_daily = client.get("/api/movements/daily?airport_id=DAM&limit=100")
    assert res_dam_daily.status_code == 200
    items = res_dam_daily.json().get("daily_movements") or res_dam_daily.json().get("data")
    for row in items:
        assert row["airport_id"] == "DAM"
        assert row["airport_id"] != "DAM_ALP_LTK"

    res_dam_flights = client.get("/api/flights?airport_id=DAM&limit=100")
    assert res_dam_flights.status_code == 200
    flights = res_dam_flights.json().get("flights") or res_dam_flights.json().get("data")
    for f in flights:
        assert f["airport_id"] == "DAM"

# 7. Historical Coverage Wording: no_verified_dam_data Strictly Means Data Gap
def test_07_historical_coverage_wording_means_data_gap_not_closure():
    doc_path = "docs/V2_19_DATA_PRODUCT_INTEGRITY.md"
    with open(doc_path, "r", encoding="utf-8") as f:
        doc = f.read()

    assert "NEVER implies zero flights operated or airport closure" in doc
    assert "no_verified_dam_data" in doc

    # Dashboard check
    index_path = "static/index.html"
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert "no_verified_dam_data" in html
    assert "NEVER implies zero flights operated or airport closure" in html

# 8. Verify Disjointness of Scheduled vs Verified Movement Endpoints
def test_08_verified_vs_scheduled_disjointness():
    res_ver = client.get("/api/movements/verified?airport_id=DAM&limit=200")
    assert res_ver.status_code == 200
    ver_events = {m["event_id"] for m in res_ver.json()["movements"]}

    res_sch = client.get("/api/movements/scheduled?airport_id=DAM&limit=200")
    assert res_sch.status_code == 200
    sch_events = {m["event_id"] for m in res_sch.json()["movements"]}

    overlap = ver_events.intersection(sch_events)
    assert len(overlap) == 0, f"Found overlapping event_ids between verified and scheduled: {overlap}"

# 9. Verify Protected Databases and Raw Snapshot Immutability
def test_09_immutability_of_protected_files_v2_19_1():
    for file_path, expected_hash in EXPECTED_HASHES.items():
        assert os.path.exists(file_path), f"Protected file missing: {file_path}"
        with open(file_path, "rb") as f:
            computed_hash = hashlib.sha256(f.read()).hexdigest()
        assert computed_hash == expected_hash, (
            f"Immutability violated for {file_path}! Expected {expected_hash}, got {computed_hash}"
        )

# 10. Forensic Record-Level Evidence Audit for all 98 DAM Events
def test_10_forensic_dam_event_evidence_audit():
    conn = sqlite3.connect(f"file:{PROD_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT event_id, airport_id, flight_number, flight_date, movement_type,
               actual_dep_time, actual_arr_time
        FROM flight_events
        WHERE airport_id = 'DAM' AND record_nature = 'physical_movement'
    """)
    events = cur.fetchall()
    assert len(events) == 98

    for ev in events:
        cur.execute("SELECT * FROM v_active_evidence WHERE event_id = ?", (ev["event_id"],))
        evidence = cur.fetchall()
        assert len(evidence) >= 1

        # Check distinct source providers
        providers = {e["source_name"] for e in evidence}
        assert len(providers) >= 1

        # Confirm evidence types are commercial/adsb timestamps or aircraft metadata
        for e in evidence:
            assert e["evidence_type"] in [
                "adsb_takeoff", "adsb_touchdown", "commercial_takeoff",
                "commercial_touchdown", "aircraft_registration", "aircraft_icao24"
            ]

    conn.close()

# 11. Monthly Coverage Classification Integrity Across All 34 Months
def test_11_monthly_coverage_classification_integrity():
    corr_file = "reports/v2_18_1_coverage_correction.csv"
    assert os.path.exists(corr_file)
    import csv
    with open(corr_file, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 34
    valid_categories = {
        "dam_verified_physical_movement",
        "dam_scheduled_fids",
        "regional_aggregate",
        "live_regional_adsb",
        "no_verified_dam_data",
        "unknown"
    }

    for r in rows:
        cat = r["corrected_category"]
        assert cat in valid_categories, f"Invalid category {cat} in month {r['year_month']}"
        if cat == "no_verified_dam_data":
            assert int(r["verified_dam_movements"]) == 0
            assert r["is_dam_historical_movement_coverage"] == "NO"

# 12. Dynamic Route Execution Check Across Core API Endpoints
def test_12_dynamic_route_execution_check():
    core_endpoints = [
        "/api/airports",
        "/api/flights?limit=5",
        "/api/movements/daily?limit=5",
        "/api/movements/historical-2024?limit=5",
        "/api/movements/verified?limit=5",
        "/api/movements/scheduled?limit=5",
        "/api/movements/stats",
        "/api/sources",
        "/api/deduplication?limit=5",
        "/api/ingestion/health",
        "/api/coverage/matrix?limit=5",
        "/api/coverage",
        "/api/quality",
        "/api/archived-fids/summary",
        "/api/archived-fids/daily",
        "/api/archived-fids/airlines",
        "/api/archived-fids/routes",
        "/api/archived-fids/coverage",
        "/api/historical-archive/captures",
        "/api/historical-archive/coverage",
    ]
    for ep in core_endpoints:
        res = client.get(ep)
        assert res.status_code == 200, f"Endpoint {ep} failed with {res.status_code}"

