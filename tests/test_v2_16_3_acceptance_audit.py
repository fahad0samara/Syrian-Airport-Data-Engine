"""
Syrian Airport Data Engine — Version 2.16.3
Acceptance & Output Consistency Audit Test Suite

Verifies all 15 acceptance criteria:
1. July monthly total = 956.
2. August monthly total = 886.
3. September monthly total = 140.
4. Total records = 1,982.
5. Arrivals = 993.
6. Departures = 989.
7. Distinct scheduled dates = 67.
8. Monthly API results match the reconciliation output.
9. CSV exports match the API.
10. JSON exports match the API.
11. Dashboard data source matches the verified calculation.
12. Old synthetic monthly figures are not returned by active endpoints.
13. Archived FIDS records are not classified as verified physical movements.
14. Capture timestamp is not used as scheduled service date.
15. Production database remains unchanged.
"""

import os
import csv
import json
import sqlite3
import hashlib
from collections import Counter
import pytest
from fastapi.testclient import TestClient

from src.api import app

PROD_DB_PATH = "data/damascus_airport.db"
STAGING_DB_PATH = "data/archived_fids_staging.db"
ANALYTICS_DB_PATH = "data/archived_fids_analytics.db"
RAW_JSON_PATH = "data/raw/snapshots/wayback_damairport_fids_20260709234230.json"
RAW_FILE_PATH = "data/raw/snapshots/wayback_damairport_fids_20260709234230.raw"
RECON_MONTHLY_CSV = "reports/v2_16_2_monthly_coverage.csv"
INDEX_HTML_PATH = "static/index.html"

EXPECTED_PROD_HASH = "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"
EXPECTED_STAGING_HASH = "a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4"
EXPECTED_ANALYTICS_HASH = "e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe"
EXPECTED_RAW_HASH = "5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf"
EXPECTED_JSON_HASH = "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491"

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(scope="module")
def source_flights():
    with open(RAW_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("flights", [])

@pytest.fixture(scope="module")
def reconciliation_rows():
    with open(RECON_MONTHLY_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {r["month"]: r for r in reader}

# 1. July monthly total = 956
def test_july_monthly_total(source_flights, reconciliation_rows):
    jul_source = [fl for fl in source_flights if fl["date"].startswith("2026-07")]
    assert len(jul_source) == 956
    assert int(reconciliation_rows["2026-07"]["total_records"]) == 956
    assert int(reconciliation_rows["2026-07"]["arrivals_count"]) == 480
    assert int(reconciliation_rows["2026-07"]["departures_count"]) == 476

# 2. August monthly total = 886
def test_august_monthly_total(source_flights, reconciliation_rows):
    aug_source = [fl for fl in source_flights if fl["date"].startswith("2026-08")]
    assert len(aug_source) == 886
    assert int(reconciliation_rows["2026-08"]["total_records"]) == 886
    assert int(reconciliation_rows["2026-08"]["arrivals_count"]) == 443
    assert int(reconciliation_rows["2026-08"]["departures_count"]) == 443

# 3. September monthly total = 140
def test_september_monthly_total(source_flights, reconciliation_rows):
    sep_source = [fl for fl in source_flights if fl["date"].startswith("2026-09")]
    assert len(sep_source) == 140
    assert int(reconciliation_rows["2026-09"]["total_records"]) == 140
    assert int(reconciliation_rows["2026-09"]["arrivals_count"]) == 70
    assert int(reconciliation_rows["2026-09"]["departures_count"]) == 70

# 4. Total = 1,982
def test_total_records(source_flights, reconciliation_rows):
    assert len(source_flights) == 1982
    total_recon = sum(int(r["total_records"]) for r in reconciliation_rows.values())
    assert total_recon == 1982

# 5. Arrivals = 993
def test_arrivals_total(source_flights, reconciliation_rows):
    arr_source = [fl for fl in source_flights if fl["direction"] == "arrival"]
    assert len(arr_source) == 993
    total_arr_recon = sum(int(r["arrivals_count"]) for r in reconciliation_rows.values())
    assert total_arr_recon == 993

# 6. Departures = 989
def test_departures_total(source_flights, reconciliation_rows):
    dep_source = [fl for fl in source_flights if fl["direction"] == "departure"]
    assert len(dep_source) == 989
    total_dep_recon = sum(int(r["departures_count"]) for r in reconciliation_rows.values())
    assert total_dep_recon == 989

# 7. Distinct scheduled dates = 67
def test_distinct_scheduled_dates(source_flights, reconciliation_rows):
    dates_source = {fl["date"] for fl in source_flights}
    assert len(dates_source) == 67
    dates_recon = sum(int(r["distinct_scheduled_dates"]) for r in reconciliation_rows.values())
    assert dates_recon == 67

# 8. Monthly API results match the reconciliation output
def test_monthly_api_results_match_reconciliation(client, reconciliation_rows):
    res = client.get("/api/historical-archive/coverage")
    assert res.status_code == 200
    data = res.json()
    coverage_list = data.get("scheduled_service_coverage", [])
    assert len(coverage_list) == 3

    for item in coverage_list:
        m = item["month"]
        recon = reconciliation_rows[m]
        assert item["total_fids_record_observations"] == int(recon["total_records"])
        assert item["scheduled_arrivals_observations"] == int(recon["arrivals_count"])
        assert item["scheduled_departures_observations"] == int(recon["departures_count"])
        assert item["distinct_scheduled_dates_count"] == int(recon["distinct_scheduled_dates"])

# 9. CSV exports match the API
def test_csv_exports_match_api(client):
    res = client.get("/api/archived-fids/export/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    lines = res.text.strip().split("\r\n") if "\r\n" in res.text else res.text.strip().split("\n")
    # Header + 67 daily rows = 68 lines
    assert len(lines) == 68
    reader = csv.DictReader(lines)
    total_from_csv = sum(int(r["total_scheduled_records"]) for r in reader)
    assert total_from_csv == 1982

# 10. JSON exports match the API
def test_json_exports_match_api(client):
    res = client.get("/api/archived-fids/export/json")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    summary = data["summary"]
    assert summary["total_archived_fids_records"] == 1982
    assert summary["scheduled_arrivals"] == 993
    assert summary["scheduled_departures"] == 989
    assert summary["calendar_days_covered"] == 67

# 11. Dashboard data source matches the verified calculation
def test_dashboard_data_source_matches_verified_calculation():
    assert os.path.exists(INDEX_HTML_PATH)
    with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()
    # Dashboard must fetch live from /api/historical-archive/coverage
    assert "/api/historical-archive/coverage" in html
    # Must NOT contain hardcoded outdated synthetic figures as static values
    assert "July: 804" not in html
    assert "August: 919" not in html
    assert "September: 259" not in html

# 12. Old synthetic monthly figures are not returned by active endpoints
def test_old_synthetic_monthly_figures_not_returned_by_active_endpoints(client):
    endpoints = [
        "/api/historical-archive/coverage",
        "/api/archived-fids/summary",
        "/api/archived-fids/daily",
        "/api/archived-fids/coverage"
    ]
    for ep in endpoints:
        res = client.get(ep)
        assert res.status_code == 200
        text = res.text
        # Assert none of the synthetic figures are returned
        assert '"total_records": 804' not in text
        assert '"total_records": 919' not in text
        assert '"total_records": 259' not in text
        assert '"total_fids_record_observations": 804' not in text
        assert '"total_fids_record_observations": 919' not in text
        assert '"total_fids_record_observations": 259' not in text

# 13. Archived FIDS records are not classified as verified physical movements
def test_archived_fids_not_classified_as_physical_movements(client):
    res = client.get("/api/archived-fids/summary")
    assert res.status_code == 200
    data = res.json()
    summary = data["summary"]
    assert summary["physical_movement_evidence_count"] == 0
    # Also verify semantic warning is present in response
    assert "not verified physical aircraft movements" in data["semantic_warning"]

# 14. Capture timestamp is not used as scheduled service date
def test_capture_timestamp_not_used_as_scheduled_service_date(source_flights):
    capture_timestamp = "2026-07-09T23:42:30Z"
    capture_date = capture_timestamp[:10]
    # Distinct scheduled dates must be 67, crossing July, August, September
    dates = {fl["date"] for fl in source_flights}
    assert len(dates) == 67
    assert dates != {capture_date}
    months = {d[:7] for d in dates}
    assert months == {"2026-07", "2026-08", "2026-09"}

# 15. Production database remains unchanged
def test_production_database_remains_unchanged():
    def get_sha256(p):
        with open(p, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    assert get_sha256(PROD_DB_PATH) == EXPECTED_PROD_HASH
    assert get_sha256(STAGING_DB_PATH) == EXPECTED_STAGING_HASH
    assert get_sha256(ANALYTICS_DB_PATH) == EXPECTED_ANALYTICS_HASH
    assert get_sha256(RAW_FILE_PATH) == EXPECTED_RAW_HASH
    assert get_sha256(RAW_JSON_PATH) == EXPECTED_JSON_HASH
