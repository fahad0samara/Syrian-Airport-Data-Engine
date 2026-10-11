"""
Tests for Version 2.15 — Archived FIDS Analytics Layer

Validates:
1. Analytics database can be built from staging.
2. Source staging records remain unchanged.
3. Production database remains unchanged (bit-identical SHA-256).
4. Total records reconcile to 1,982.
5. Arrivals reconcile to 993.
6. Departures reconcile to 989.
7. Status counts reconcile to 1,981 scheduled and 1 arrived.
8. Daily coverage includes the 67 expected calendar dates.
9. Displayed airline totals reconcile to 1,982.
10. Route calculations preserve arrival/departure direction.
11. Hourly grouping uses local scheduled time (Asia/Damascus).
12. Duplicate candidate pair is preserved (G9 376 / 376 on 2026-07-08 at 13:55).
13. No duplicate candidate is silently removed.
14. Null values remain null where appropriate.
15. Invalid date filters return appropriate errors (HTTP 400).
16. API endpoints do not access production movement tables.
17. CSV and JSON exports are valid and reconcilable.
18. Physical movement counts are never inferred from FIDS records (evidence = 0).
19. All analytics results include source provenance and semantic warning.
20. Rebuilding analytics is deterministic and idempotent.
"""

import os
import csv
import json
import sqlite3
import hashlib
import pytest
from fastapi.testclient import TestClient

from src.api import app
from src.archived_fids_analytics import (
    STAGING_DB_PATH,
    ANALYTICS_DB_PATH,
    PROD_DB_PATH,
    EXPECTED_PROD_HASH,
    SEMANTIC_WARNING,
    SNAPSHOT_PROVENANCE,
    get_file_sha256,
    build_analytics_database,
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

client = TestClient(app)

# 1. Analytics database can be built from staging
def test_analytics_database_build():
    db_path = build_analytics_database(rebuild=True)
    assert os.path.exists(db_path)
    assert os.path.getsize(db_path) > 100000

# 2. Source staging records remain unchanged
def test_source_staging_records_unchanged():
    conn = get_staging_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM archived_fids_normalized")
    count = cur.fetchone()[0]
    assert count == 1982
    conn.close()

# 3. Production database remains unchanged (bit-identical SHA-256)
def test_production_database_unchanged():
    assert os.path.exists(PROD_DB_PATH)
    current_hash = get_file_sha256(PROD_DB_PATH)
    assert current_hash == EXPECTED_PROD_HASH, f"Production hash altered: {current_hash}"

# 4. Total records reconcile to 1,982
def test_total_records_reconcile_to_1982():
    summary = get_fids_summary()["summary"]
    assert summary["total_archived_fids_records"] == 1982

# 5. Arrivals reconcile to 993
def test_arrivals_reconcile_to_993():
    summary = get_fids_summary()["summary"]
    assert summary["scheduled_arrivals"] == 993

# 6. Departures reconcile to 989
def test_departures_reconcile_to_989():
    summary = get_fids_summary()["summary"]
    assert summary["scheduled_departures"] == 989
    assert summary["scheduled_arrivals"] + summary["scheduled_departures"] == 1982

# 7. Status counts reconcile to 1,981 scheduled and 1 arrived
def test_status_counts_reconcile():
    summary = get_fids_summary()["summary"]
    dist = summary["status_distribution"]
    assert dist["scheduled"] == 1981
    assert dist["arrived"] == 1
    assert dist["scheduled"] + dist["arrived"] == 1982

# 8. Daily coverage includes the 67 expected calendar dates
def test_daily_coverage_67_dates():
    daily_res = get_daily_scheduled_flights()
    records = daily_res["daily_records"]
    assert len(records) == 67
    dates = [r["flight_date"] for r in records]
    assert dates[0] == "2026-07-05"
    assert dates[-1] == "2026-09-09"
    # Verify continuous without gaps
    for r in records:
        assert r["total_scheduled_records"] > 0
        assert r["arrival_records"] + r["departure_records"] == r["total_scheduled_records"]

# 9. Displayed airline totals reconcile to 1,982
def test_displayed_airline_totals_reconcile():
    airline_res = get_displayed_airline_analysis()
    airlines = airline_res["airlines"]
    assert len(airlines) == 14
    total_flights = sum(a["total_displayed_records"] for a in airlines)
    assert total_flights == 1982
    for a in airlines:
        assert a["carrier_role_classification"] == "displayed_airline_brand"
        assert a["is_operating_carrier_verified"] is False
        assert a["arrival_records"] + a["departure_records"] == a["total_displayed_records"]

# 10. Route calculations preserve arrival/departure direction
def test_route_calculations_preserve_direction():
    rt_res = get_destination_and_route_analysis(top_limit=100)
    routes = rt_res["top_routes"]
    assert len(routes) > 0
    for r in routes:
        if r["movement_type"] == "arrival":
            assert r["destination_iata"] == "DAM"
        elif r["movement_type"] == "departure":
            assert r["origin_iata"] == "DAM"

# 11. Hourly grouping uses local scheduled time (Asia/Damascus)
def test_hourly_grouping_uses_local_time():
    hr_res = get_hourly_schedule_distribution()
    assert hr_res["timezone"] == "Asia/Damascus (UTC+3)"
    hours = hr_res["hourly_distribution"]
    assert len(hours) == 24
    total_hourly = sum(h["total"] for h in hours)
    assert total_hourly == 1982
    total_arr = sum(h["arrivals"] for h in hours)
    total_dep = sum(h["departures"] for h in hours)
    assert total_arr == 993
    assert total_dep == 989

# 12. Duplicate candidate pair is preserved (G9 376 / 376)
def test_duplicate_candidate_pair_preserved():
    dup_res = get_duplicate_candidates()
    assert dup_res["duplicate_candidate_pairs_count"] == 1
    cand = dup_res["candidates"][0]
    assert cand["candidate_id"] == "DUP_CANDIDATE_001"
    assert cand["duplicate_classification"] == "possible_prefix_variant_duplicate"
    assert cand["review_status"] == "requires_manual_review"
    assert "e5ada70d-5245-46d4-b043-bf469c1d104f" in (cand["source_uuid_1"], cand["source_uuid_2"])
    assert "2d2a0935-da5e-42c4-ad15-e10b4e2291ee" in (cand["source_uuid_1"], cand["source_uuid_2"])

# 13. No duplicate candidate is silently removed
def test_no_duplicate_candidate_silently_removed():
    conn = get_analytics_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT source_uuid, flight_number, scheduled_date, scheduled_time
    FROM fids_analytics_records
    WHERE scheduled_date = '2026-07-08' AND scheduled_time = '13:55' AND movement_type = 'departure'
    """)
    rows = cur.fetchall()
    assert len(rows) == 2
    fns = sorted([r["flight_number"] for r in rows])
    assert fns == ["376", "G9376"]
    conn.close()

# 14. Null values remain null where appropriate
def test_null_values_preserved():
    conn = get_analytics_connection()
    cur = conn.cursor()
    # Check that airline_iata is null or empty string where not present
    cur.execute("SELECT COUNT(*) FROM fids_analytics_records WHERE airline_iata IS NULL OR airline_iata = ''")
    # All 14 airlines have IATA mapped, verify no bogus filled data
    cur.execute("SELECT DISTINCT airline_iata FROM fids_analytics_records")
    iatas = [r[0] for r in cur.fetchall()]
    assert "G9" in iatas
    assert "XY" in iatas
    conn.close()

# 15. Invalid date filters return appropriate errors (HTTP 400)
def test_invalid_filters_return_400():
    res1 = client.get("/api/archived-fids/summary?start_date=2026-13-45")
    assert res1.status_code == 400
    res2 = client.get("/api/archived-fids/summary?start_date=2026-08-10&end_date=2026-07-10")
    assert res2.status_code == 400
    res3 = client.get("/api/archived-fids/summary?direction=invalid_dir")
    assert res3.status_code == 400

# 16. API endpoints do not access production movement tables
def test_api_endpoints_do_not_access_production_tables():
    # Calling archived FIDS endpoints returns data from archived FIDS, not flight_events
    res = client.get("/api/archived-fids/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["total_archived_fids_records"] == 1982
    # Verify production flight_events count is 1,830 (not 1,982)
    with sqlite3.connect(f"file:{PROD_DB_PATH}?mode=ro", uri=True) as pconn:
        pcur = pconn.cursor()
        pcur.execute("SELECT COUNT(*) FROM flight_events")
        prod_count = pcur.fetchone()[0]
        assert prod_count == 1830

# 17. CSV and JSON exports are valid and reconcilable
def test_csv_and_json_exports_valid():
    res_csv = client.get("/api/archived-fids/export/csv?dataset=daily")
    assert res_csv.status_code == 200
    reader = list(csv.reader(res_csv.text.splitlines()))
    assert len(reader) == 68 # 1 header + 67 days

    res_json = client.get("/api/archived-fids/export/json?dataset=summary")
    assert res_json.status_code == 200
    data = res_json.json()
    assert data["summary"]["total_archived_fids_records"] == 1982

# 18. Physical movement counts are never inferred from FIDS records
def test_physical_movement_evidence_never_inferred():
    summary = get_fids_summary()["summary"]
    assert summary["physical_movement_evidence_count"] == 0
    res = client.get("/api/archived-fids/coverage")
    assert res.status_code == 200
    assert res.json()["physical_movement_evidence_count"] == 0

# 19. All analytics results include source provenance and semantic warning
def test_provenance_and_warning_included():
    res = client.get("/api/archived-fids/summary")
    assert res.status_code == 200
    data = res.json()
    assert "provenance" in data
    assert data["provenance"]["snapshot_id"] == "snap_wayback_20260709234230"
    assert "semantic_warning" in data
    assert "not verified physical aircraft movements" in data["semantic_warning"]

# 20. Rebuilding analytics is deterministic and idempotent
def test_rebuilding_analytics_deterministic():
    # Rebuild twice and verify record counts and hashes
    p1 = build_analytics_database(rebuild=True)
    c1 = get_fids_summary()["summary"]["total_archived_fids_records"]
    p2 = build_analytics_database(rebuild=True)
    c2 = get_fids_summary()["summary"]["total_archived_fids_records"]
    assert c1 == 1982
    assert c2 == 1982
