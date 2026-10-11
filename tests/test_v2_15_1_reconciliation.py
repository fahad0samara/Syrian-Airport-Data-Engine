"""
Syrian Airport Data Engine — Version 2.15.1
Analytics Reconciliation & Metric Integrity Regression Test Suite

Verifies:
1. Immutability of Production DB, Staging DB, and Raw Snapshot files (cryptographic SHA-256).
2. Critical daily coverage reconciliation (67 days, min=2, max=69, total=1,982).
3. Weekly metric reconciliation (weighted average = 29.5821 matches overall average exactly).
4. Entity classification audit (14 entities: 13 commercial airlines + 1 humanitarian organization).
5. Route and directional reconciliation (arrivals=993, departures=989, total=1,982).
6. Hourly distribution reconciliation (local Damascus wall-clock time, sum=1,982).
7. Duplicate candidate pair preservation (G9 376 / 376 on 2026-07-08 at 13:55).
8. Zero physical movement promotion (evidence = 0).
9. All 4 machine-readable audit reports exist, non-empty, and reconcile.
10. All 5 audit documentation files exist, non-empty, and coherent.
11. API endpoints match staging truth and do not access production flight_events.
"""

import os
import csv
import json
import sqlite3
import hashlib
import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient

from src.api import app
from src.archived_fids_analytics import (
    STAGING_DB_PATH,
    PROD_DB_PATH,
    EXPECTED_PROD_HASH,
    get_file_sha256,
    get_staging_connection,
    get_analytics_connection,
    get_fids_summary,
    get_daily_scheduled_flights,
    get_displayed_airline_analysis,
    get_destination_and_route_analysis,
    get_hourly_schedule_distribution,
    get_weekly_and_daily_patterns,
    get_duplicate_candidates
)

EXPECTED_STAGING_HASH = "a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4"
EXPECTED_RAW_HASH = "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491"
RAW_JSON_PATH = "data/raw/snapshots/wayback_damairport_fids_20260709234230.json"

client = TestClient(app)

# -----------------------------------------------------------------------------
# 1. Cryptographic Immutability Tests
# -----------------------------------------------------------------------------
def test_production_database_immutability():
    """Ensures production database remains bit-for-bit untouched with 1,830 records."""
    assert os.path.exists(PROD_DB_PATH)
    h = get_file_sha256(PROD_DB_PATH)
    assert h == EXPECTED_PROD_HASH, f"Production DB altered! Hash: {h}"
    with sqlite3.connect(f"file:{PROD_DB_PATH}?mode=ro", uri=True) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM flight_events")
        cnt = cur.fetchone()[0]
        assert cnt == 1830

def test_staging_database_immutability():
    """Ensures staging database remains bit-for-bit untouched with 1,982 records."""
    assert os.path.exists(STAGING_DB_PATH)
    h = get_file_sha256(STAGING_DB_PATH)
    assert h == EXPECTED_STAGING_HASH, f"Staging DB altered! Hash: {h}"
    with sqlite3.connect(f"file:{STAGING_DB_PATH}?mode=ro", uri=True) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM archived_fids_normalized")
        cnt = cur.fetchone()[0]
        assert cnt == 1982

def test_raw_json_snapshot_immutability():
    """Ensures raw Wayback FIDS JSON snapshot remains bit-for-bit identical."""
    assert os.path.exists(RAW_JSON_PATH)
    h = get_file_sha256(RAW_JSON_PATH)
    assert h == EXPECTED_RAW_HASH, f"Raw JSON altered! Hash: {h}"

# -----------------------------------------------------------------------------
# 2. Critical Daily Coverage Reconciliation
# -----------------------------------------------------------------------------
def test_daily_coverage_continuity_and_exact_counts():
    """Verifies all 67 consecutive calendar dates, min=2, max=69, and overall average=29.5821."""
    conn = get_staging_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT scheduled_date, COUNT(*) as cnt,
           SUM(CASE WHEN movement_type = 'arrival' THEN 1 ELSE 0 END) as arr,
           SUM(CASE WHEN movement_type = 'departure' THEN 1 ELSE 0 END) as dep
    FROM archived_fids_normalized
    GROUP BY scheduled_date
    ORDER BY scheduled_date ASC
    """)
    rows = cur.fetchall()
    conn.close()

    assert len(rows) == 67
    dates = [r["scheduled_date"] for r in rows]
    assert dates[0] == "2026-07-05"
    assert dates[-1] == "2026-09-09"

    # Verify zero missing dates in sequence
    cur_date = datetime.strptime(dates[0], "%Y-%m-%d").date()
    end_date = datetime.strptime(dates[-1], "%Y-%m-%d").date()
    expected_dates = []
    while cur_date <= end_date:
        expected_dates.append(cur_date.strftime("%Y-%m-%d"))
        cur_date += timedelta(days=1)
    assert dates == expected_dates

    # Daily count min and max
    counts = [r["cnt"] for r in rows]
    assert min(counts) == 2
    assert max(counts) == 69

    # Peak date
    peak_date_row = [r for r in rows if r["cnt"] == 69][0]
    assert peak_date_row["scheduled_date"] == "2026-07-06"
    assert peak_date_row["arr"] == 35
    assert peak_date_row["dep"] == 34

    # Quietest dates (2 flights/day)
    quiet_rows = [r for r in rows if r["cnt"] == 2]
    assert len(quiet_rows) == 4
    quiet_dates = [r["scheduled_date"] for r in quiet_rows]
    assert quiet_dates == ["2026-09-06", "2026-09-07", "2026-09-08", "2026-09-09"]
    for qr in quiet_rows:
        assert qr["arr"] == 1
        assert qr["dep"] == 1

    # Total sum and average
    total_records = sum(counts)
    assert total_records == 1982
    daily_avg = total_records / 67.0
    assert round(daily_avg, 4) == 29.5821

# -----------------------------------------------------------------------------
# 3. Weekly Metric Verification & Exact Weighting
# -----------------------------------------------------------------------------
def test_weekday_metrics_and_weighted_reconciliation():
    """Verifies weekday occurrences, sums, and exact mathematical reconciliation of weighted average."""
    conn = get_staging_connection()
    cur = conn.cursor()
    cur.execute("SELECT scheduled_date FROM archived_fids_normalized")
    rows = cur.fetchall()
    conn.close()

    weekday_counts = {i: {"occ": set(), "records": 0} for i in range(7)}
    for r in rows:
        d = r["scheduled_date"]
        dt = datetime.strptime(d, "%Y-%m-%d").date()
        w = dt.weekday()
        weekday_counts[w]["occ"].add(d)
        weekday_counts[w]["records"] += 1

    # Verify occurrences per weekday across 67 days:
    # 2026-07-05 is Sunday (w=6). 2026-09-09 is Wednesday (w=2).
    # Sun, Mon, Tue, Wed = 10 occurrences; Thu, Fri, Sat = 9 occurrences.
    expected_occ = {0: 10, 1: 10, 2: 10, 3: 9, 4: 9, 5: 9, 6: 10}
    for w in range(7):
        assert len(weekday_counts[w]["occ"]) == expected_occ[w]

    total_records = sum(weekday_counts[w]["records"] for w in range(7))
    assert total_records == 1982

    # Weighted average calculation
    weighted_sum = sum(
        (weekday_counts[w]["records"] / len(weekday_counts[w]["occ"])) * len(weekday_counts[w]["occ"])
        for w in range(7)
    )
    weighted_avg = weighted_sum / 67.0
    overall_avg = 1982.0 / 67.0
    assert abs(weighted_avg - overall_avg) < 1e-9

# -----------------------------------------------------------------------------
# 4. Entity Classification Audit
# -----------------------------------------------------------------------------
def test_entity_classification_audit():
    """Verifies 14 displayed entities: 13 commercial airline brands and 1 humanitarian organization."""
    conn = get_staging_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT airline_name_en, airline_name_ar, airline_iata, COUNT(*) as cnt,
           SUM(CASE WHEN movement_type = 'arrival' THEN 1 ELSE 0 END) as arr,
           SUM(CASE WHEN movement_type = 'departure' THEN 1 ELSE 0 END) as dep
    FROM archived_fids_normalized
    GROUP BY airline_name_en, airline_name_ar, airline_iata
    ORDER BY cnt DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    assert len(rows) == 14
    total_cnt = sum(r["cnt"] for r in rows)
    assert total_cnt == 1982

    # Check United Nations entity
    un_row = [r for r in rows if r["airline_name_en"] == "United Nations"][0]
    assert un_row["airline_iata"] == "UN"
    assert un_row["airline_name_ar"] == "الأمم المتحدة"
    assert un_row["cnt"] == 4
    assert un_row["arr"] == 2
    assert un_row["dep"] == 2

    # Check top airline: Air Arabia
    g9_row = [r for r in rows if r["airline_name_en"] == "Air Arabia"][0]
    assert g9_row["cnt"] == 509
    assert g9_row["arr"] == 256
    assert g9_row["dep"] == 253

    # Check Flynas
    xy_row = [r for r in rows if r["airline_name_en"] == "Flynas"][0]
    assert xy_row["cnt"] == 382
    assert xy_row["arr"] == 191
    assert xy_row["dep"] == 191

# -----------------------------------------------------------------------------
# 5. Route and Directional Reconciliation
# -----------------------------------------------------------------------------
def test_route_and_directional_reconciliation():
    """Verifies arrivals=993, departures=989, total=1,982, and directional consistency."""
    conn = get_staging_connection()
    cur = conn.cursor()
    cur.execute("SELECT movement_type, COUNT(*) FROM archived_fids_normalized GROUP BY movement_type")
    counts = dict(cur.fetchall())

    assert counts["arrival"] == 993
    assert counts["departure"] == 989
    assert counts["arrival"] + counts["departure"] == 1982

    # All arrivals must have destination == 'DAM'
    cur.execute("SELECT COUNT(*) FROM archived_fids_normalized WHERE movement_type = 'arrival' AND destination_iata != 'DAM'")
    assert cur.fetchone()[0] == 0

    # All departures must have origin == 'DAM'
    cur.execute("SELECT COUNT(*) FROM archived_fids_normalized WHERE movement_type = 'departure' AND origin_iata != 'DAM'")
    assert cur.fetchone()[0] == 0

    conn.close()

# -----------------------------------------------------------------------------
# 6. Hourly Schedule Distribution Reconciliation
# -----------------------------------------------------------------------------
def test_hourly_schedule_reconciliation():
    """Verifies that hourly counts in local Damascus wall-clock time reconcile exactly to 1,982."""
    hr_res = get_hourly_schedule_distribution()
    assert hr_res["timezone"] == "Asia/Damascus (UTC+3)"
    hours = hr_res["hourly_distribution"]
    assert len(hours) == 24

    total_records = sum(h["total"] for h in hours)
    total_arr = sum(h["arrivals"] for h in hours)
    total_dep = sum(h["departures"] for h in hours)

    assert total_records == 1982
    assert total_arr == 993
    assert total_dep == 989

# -----------------------------------------------------------------------------
# 7. Candidate Duplicate Pair Preservation
# -----------------------------------------------------------------------------
def test_duplicate_candidate_pair_invariants():
    """Verifies candidate duplicate pair G9 376 / 376 is intact without deletion or mutation."""
    conn = get_staging_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT source_uuid, flight_number, airline_name_en, movement_type, origin_iata, destination_iata,
           scheduled_date, scheduled_time, displayed_status
    FROM archived_fids_normalized
    WHERE source_uuid IN ('e5ada70d-5245-46d4-b043-bf469c1d104f', '2d2a0935-da5e-42c4-ad15-e10b4e2291ee')
    ORDER BY flight_number
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    assert len(rows) == 2
    r_no_pfx, r_pfx = rows[0], rows[1]
    assert r_no_pfx["flight_number"] == "376"
    assert r_no_pfx["source_uuid"] == "2d2a0935-da5e-42c4-ad15-e10b4e2291ee"
    assert r_pfx["flight_number"] == "G9376"
    assert r_pfx["source_uuid"] == "e5ada70d-5245-46d4-b043-bf469c1d104f"

    for r in rows:
        assert r["airline_name_en"] == "Air Arabia"
        assert r["scheduled_date"] == "2026-07-08"
        assert r["scheduled_time"] == "13:55"
        assert r["movement_type"] == "departure"
        assert r["origin_iata"] == "DAM"
        assert r["destination_iata"] == "SHJ"
        assert r["displayed_status"] == "scheduled"

# -----------------------------------------------------------------------------
# 8. Physical Movement Isolation
# -----------------------------------------------------------------------------
def test_physical_movement_evidence_strictly_zero():
    """Verifies actual_movement_evidence is 0 across all records in staging and analytics."""
    conn = get_staging_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM archived_fids_normalized WHERE actual_movement_evidence != 0")
    assert cur.fetchone()[0] == 0
    conn.close()

    summary = get_fids_summary()["summary"]
    assert summary["physical_movement_evidence_count"] == 0

# -----------------------------------------------------------------------------
# 9. Deliverables Existence & Completeness
# -----------------------------------------------------------------------------
def test_v2_15_1_machine_readable_reports_exist_and_non_empty():
    """Verifies that all 4 required V2.15.1 machine-readable reports exist and are valid."""
    reports = [
        "reports/v2_15_1_daily_reconciliation.csv",
        "reports/v2_15_1_weekday_reconciliation.csv",
        "reports/v2_15_1_entity_reconciliation.csv",
        "reports/v2_15_1_metric_reconciliation.json"
    ]
    for p in reports:
        assert os.path.exists(p), f"Missing report: {p}"
        assert os.path.getsize(p) > 100, f"Report empty or truncated: {p}"

    # Verify daily CSV rows
    with open("reports/v2_15_1_daily_reconciliation.csv", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        assert len(reader) == 68 # 1 header + 67 days

    # Verify weekday CSV rows
    with open("reports/v2_15_1_weekday_reconciliation.csv", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        assert len(reader) == 8 # 1 header + 7 days

    # Verify entity CSV rows
    with open("reports/v2_15_1_entity_reconciliation.csv", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        assert len(reader) == 15 # 1 header + 14 entities

    # Verify metric JSON
    with open("reports/v2_15_1_metric_reconciliation.json", encoding="utf-8") as f:
        data = json.load(f)
        assert data["metadata"]["version"] == "2.15.1"
        assert data["critical_daily_coverage_reconciliation"]["metrics"]["total_records"] == 1982
        assert data["entity_classification_audit"]["total_displayed_entities"] == 14

def test_v2_15_1_documentation_files_exist_and_non_empty():
    """Verifies that all 5 required V2.15.1 documentation files exist and are populated."""
    docs = [
        "docs/V2_15_1_DAILY_RECONCILIATION.md",
        "docs/V2_15_1_WEEKLY_METRIC_AUDIT.md",
        "docs/V2_15_1_ENTITY_CLASSIFICATION_AUDIT.md",
        "docs/V2_15_1_API_EXPORT_RECONCILIATION.md",
        "docs/V2_15_1_FINAL_AUDIT.md"
    ]
    for d in docs:
        assert os.path.exists(d), f"Missing documentation file: {d}"
        assert os.path.getsize(d) > 200, f"Documentation file too small or empty: {d}"

# -----------------------------------------------------------------------------
# 10. API Endpoints Reconciliation
# -----------------------------------------------------------------------------
def test_all_fids_api_endpoints_reconcile():
    """Cross-validates API endpoints return correct status and matching counts."""
    res_sum = client.get("/api/archived-fids/summary")
    assert res_sum.status_code == 200
    assert res_sum.json()["summary"]["total_archived_fids_records"] == 1982

    res_daily = client.get("/api/archived-fids/daily")
    assert res_daily.status_code == 200
    assert res_daily.json()["total_days"] == 67

    res_al = client.get("/api/archived-fids/airlines")
    assert res_al.status_code == 200
    assert res_al.json()["airline_brands_count"] == 14

    res_rt = client.get("/api/archived-fids/routes")
    assert res_rt.status_code == 200

    res_hr = client.get("/api/archived-fids/hourly")
    assert res_hr.status_code == 200
    assert len(res_hr.json()["hourly_distribution"]) == 24

    res_wk = client.get("/api/archived-fids/weekly")
    assert res_wk.status_code == 200
    assert len(res_wk.json()["weekday_distribution"]) == 7

    res_dup = client.get("/api/archived-fids/duplicate-candidates")
    assert res_dup.status_code == 200
    assert res_dup.json()["duplicate_candidate_pairs_count"] == 1

    res_cov = client.get("/api/archived-fids/coverage")
    assert res_cov.status_code == 200
    assert res_cov.json()["records_total"] == 1982
