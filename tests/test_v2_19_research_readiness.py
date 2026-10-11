"""
Syrian Airport Data Engine — Version 2.19
Regression Test Suite: Data Product Integrity & Research Readiness

Verifies all requirements of Milestone V2.19:
1. Strict data categories (never combined into a single DAM count).
2. DAM-only endpoints return DAM-only records.
3. Regional aggregates explicitly identify all included airports and are not DAM-specific.
4. FIDS records labeled as scheduled timetable data (physical movement count = 0).
5. Live ADS-B observations labeled as regional observations (0 DAM movements).
6. Missing data remains NULL or unverified gap.
7. No endpoint presents scheduled flights as completed movements (0 overlap).
8. Dashboard displays the 4 prominent research integrity warnings.
9. Export cards display full research metadata.
10. Calculation verification from raw source tables.
11. Immutability of protected databases and snapshots.
12. Platform documentation completeness.
"""

import os
import csv
import json
import sqlite3
import hashlib
import pytest
from fastapi.testclient import TestClient

from src.api import app

client = TestClient(app)

PROD_DB = "data/damascus_airport.db"
FIDS_STAGING_DB = "data/archived_fids_staging.db"
ANALYTICS_DB = "data/archived_fids_analytics.db"
HISTORY_STAGING_DB = "data/archived_fids_history_staging.db"
V2_18_STAGING_DB = "data/staging/v2_18/v2_18_staging.db"
BASELINE_RAW = "data/raw/snapshots/wayback_damairport_fids_20260709234230.raw"
BASELINE_JSON = "data/raw/snapshots/wayback_damairport_fids_20260709234230.json"
INDEX_HTML = "static/index.html"
DOC_PATH = "docs/V2_19_DATA_PRODUCT_INTEGRITY.md"

EXPECTED_PROD_HASH = "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"
EXPECTED_RAW_HASH = "5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf"
EXPECTED_JSON_HASH = "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491"
EXPECTED_FIDS_STAGING_HASH = "a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4"
EXPECTED_ANALYTICS_HASH = "e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe"
EXPECTED_HISTORY_STAGING_HASH = "39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f"

def get_file_sha256(path):
    assert os.path.exists(path), f"File {path} does not exist"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

# 1. Strict data categories
def test_01_strict_data_categories():
    valid_categories = {
        "dam_verified_physical_movement",
        "dam_scheduled_fids",
        "regional_aggregate",
        "live_regional_adsb",
        "no_verified_dam_data",
        "unknown"
    }
    # Verify monthly coverage uses only valid categories
    with open("reports/v2_18_1_coverage_correction.csv", "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        cat = r["corrected_category"]
        assert cat in valid_categories, f"Invalid category '{cat}' found"
        # Never combine into a single DAM movement count:
        if cat != "dam_verified_physical_movement":
            assert int(r["verified_dam_movements"]) == 0

# 2. DAM-only endpoints return DAM-only records
def test_02_dam_only_endpoints_return_dam_only():
    # /api/flights?airport_id=DAM
    res_flights = client.get("/api/flights?airport_id=DAM&limit=100")
    assert res_flights.status_code == 200
    flights = res_flights.json().get("flights") or res_flights.json().get("data")
    assert len(flights) > 0
    for ev in flights:
        assert ev["airport_id"] == "DAM"

    # /api/movements/daily?airport_id=DAM
    res_daily = client.get("/api/movements/daily?airport_id=DAM&limit=100")
    assert res_daily.status_code == 200
    daily_items = res_daily.json().get("movements") or res_daily.json().get("daily_movements") or res_daily.json().get("data")
    assert len(daily_items) > 0
    for m in daily_items:
        assert m["airport_id"] == "DAM"

    # /api/movements/verified?airport_id=DAM
    res_ver = client.get("/api/movements/verified?airport_id=DAM&limit=100")
    assert res_ver.status_code == 200
    for v in res_ver.json()["movements"]:
        assert v["airport_id"] == "DAM"
        assert v["record_nature"] == "physical_movement"

# 3. Regional aggregates explicitly identify all included airports and are not DAM-specific
def test_03_regional_aggregates_explicit_scope():
    res = client.get("/api/movements/historical-2024?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["scope"] == "DAM_ALP_LTK"
    assert data["included_airports"] == ["DAM", "ALP", "LTK"]
    assert data["data_category"] == "regional_aggregate"
    assert data["is_dam_specific"] is False
    assert "three-airport aggregate" in data["warning"].lower()
    for row in data["records"]:
        assert row["scope"] == "DAM_ALP_LTK"

# 4. FIDS records labeled as scheduled timetable data
def test_04_fids_records_labeled_as_scheduled_timetable():
    res = client.get("/api/archived-fids/summary")
    assert res.status_code == 200
    data = res.json()
    summary = data["summary"]
    assert summary["physical_movement_evidence_count"] == 0
    assert "scheduled" in data["semantic_warning"].lower() or "physical" in data["semantic_warning"].lower()
    assert summary["total_archived_fids_records"] == 1982
    assert summary["scheduled_arrivals"] == 993
    assert summary["scheduled_departures"] == 989

# 5. Live ADS-B observations labeled as regional observations
def test_05_live_adsb_observations_labeled_as_regional():
    conn = sqlite3.connect(V2_18_STAGING_DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), SUM(is_dam_movement), SUM(confirmed_physical_movement) FROM recovered_observations")
    total, dam_mov, conf_mov = cur.fetchone()
    conn.close()
    assert total == 16
    assert dam_mov == 0
    assert conf_mov == 0

# 6. Missing data remains NULL or unverified gap
def test_06_missing_data_remains_null_or_gap():
    conn = sqlite3.connect(PROD_DB)
    cur = conn.cursor()
    # Check that over 1,600 flight_events have NULL actual times (never synthetically filled)
    cur.execute("SELECT COUNT(*) FROM flight_events WHERE actual_arr_time IS NULL")
    null_arr = cur.fetchone()[0]
    assert null_arr >= 1600, f"Expected >= 1600 NULL actual arrival timestamps, found {null_arr}"

    # Check that SEM outage dates in 2024 are marked unverified_data_gap
    cur.execute("SELECT COUNT(*) FROM historical_daily_movements_2024 WHERE coverage_status = 'unverified_data_gap'")
    gap_count = cur.fetchone()[0]
    assert gap_count > 0, "Outage dates must remain marked as unverified_data_gap"
    conn.close()

# 7. No endpoint presents scheduled flights as completed movements
def test_07_no_scheduled_flights_presented_as_completed():
    res_sched = client.get("/api/movements/scheduled?limit=500")
    assert res_sched.status_code == 200
    sched_ids = {m["event_id"] for m in res_sched.json()["movements"]}

    res_ver = client.get("/api/movements/verified?limit=500")
    assert res_ver.status_code == 200
    ver_ids = {m["event_id"] for m in res_ver.json()["movements"]}

    overlap = sched_ids.intersection(ver_ids)
    assert len(overlap) == 0, f"Overlap detected between scheduled and verified movements: {overlap}"

# 8. Dashboard displays the 4 prominent research integrity warnings
def test_08_dashboard_displays_prominent_warnings():
    assert os.path.exists(INDEX_HTML)
    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    # Warning 1: 2024 DAM_ALP_LTK is three-airport aggregate
    assert "DAM_ALP_LTK" in html
    assert "three-airport aggregate" in html.lower()

    # Warning 2: Archived FIDS contains scheduled records, not verified physical movements
    assert "scheduled" in html.lower() and "physical movements" in html.lower()

    # Warning 3: October 2026 ADS-B sample is regional and limited
    assert "16" in html and "overflights" in html.lower()

    # Warning 4: No verified DAM-specific historical physical movements for 2024
    assert "No verified DAM-specific historical physical movements" in html

# 9. Export cards display full research metadata
def test_09_export_cards_display_research_metadata():
    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    assert "Geographic Scope:" in html
    assert "Date Horizon:" in html
    assert "Record Count:" in html
    assert "Data Category:" in html
    assert "Provenance:" in html
    assert "Limitations:" in html

    # Verify export endpoint returns newly added datasets
    for exp in ["coverage_correction", "damascus_coverage", "dataset_scope_audit", "dataset_scoring"]:
        res = client.get(f"/api/export/{exp}?format=csv")
        assert res.status_code == 200, f"Export for {exp} failed"
        assert len(res.content) > 0

# 10. Calculation verification from raw source tables
def test_10_calculation_verification_from_source_tables():
    conn = sqlite3.connect(PROD_DB)
    cur = conn.cursor()

    # Canonical flight events sum check
    cur.execute("SELECT COUNT(*) FROM flight_events")
    total_events = cur.fetchone()[0]
    cur.execute("""
    SELECT
      SUM(CASE WHEN record_nature = 'physical_movement' THEN 1 ELSE 0 END),
      SUM(CASE WHEN record_nature = 'scheduled_service' THEN 1 ELSE 0 END),
      SUM(CASE WHEN record_nature = 'marketing_codeshare' THEN 1 ELSE 0 END),
      SUM(CASE WHEN record_nature = 'unverified_movement' THEN 1 ELSE 0 END)
    FROM flight_events
    """)
    phys, sched, code, unver = cur.fetchone()
    assert total_events == (phys + sched + code + unver)
    assert total_events == 1830
    assert phys == 131
    assert sched == 1662
    assert code == 34
    assert unver == 3

    # Historical 2024 arithmetic
    cur.execute("SELECT COUNT(*), SUM(CASE WHEN movement_type = 'arrival' THEN 1 ELSE 0 END), SUM(CASE WHEN movement_type = 'departure' THEN 1 ELSE 0 END) FROM historical_daily_movements_2024")
    tot_hist, arr_hist, dep_hist = cur.fetchone()
    assert tot_hist == 578
    assert arr_hist == 289
    assert dep_hist == 289
    conn.close()

    # FIDS staging arithmetic
    conn_fids = sqlite3.connect(FIDS_STAGING_DB)
    cur_fids = conn_fids.cursor()
    cur_fids.execute("SELECT COUNT(*), SUM(CASE WHEN movement_type = 'arrival' THEN 1 ELSE 0 END), SUM(CASE WHEN movement_type = 'departure' THEN 1 ELSE 0 END) FROM archived_fids_normalized")
    tot_fids, arr_fids, dep_fids = cur_fids.fetchone()
    conn_fids.close()
    assert tot_fids == 1982
    assert arr_fids == 993
    assert dep_fids == 989

# 11. Immutability of protected databases and snapshots
def test_11_immutability_of_protected_files():
    assert get_file_sha256(PROD_DB) == EXPECTED_PROD_HASH
    assert get_file_sha256(FIDS_STAGING_DB) == EXPECTED_FIDS_STAGING_HASH
    assert get_file_sha256(ANALYTICS_DB) == EXPECTED_ANALYTICS_HASH
    assert get_file_sha256(HISTORY_STAGING_DB) == EXPECTED_HISTORY_STAGING_HASH
    assert get_file_sha256(BASELINE_RAW) == EXPECTED_RAW_HASH
    assert get_file_sha256(BASELINE_JSON) == EXPECTED_JSON_HASH

# 12. Platform documentation completeness
def test_12_platform_documentation_completeness():
    assert os.path.exists(DOC_PATH)
    with open(DOC_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    required_sections = [
        "1. Executive Mission & Integrity Invariants",
        "2. Core Data Categories",
        "3. Dataset Inventory & Provenance Catalog",
        "4. Geographic & Temporal Coverage Matrix",
        "5. API & Export Behavioral Semantics",
        "6. What the Platform Can and Cannot Currently Claim"
    ]
    for sec in required_sections:
        assert sec in content, f"Missing section '{sec}' in {DOC_PATH}"
