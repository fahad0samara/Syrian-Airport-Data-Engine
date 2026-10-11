"""
Tests for Version 2.14.1 — Archived FIDS Semantic Audit & Data Integrity

Validates:
1. Production database immutability (SHA-256 unchanged).
2. Source UUID completeness and uniqueness (1,982 unique UUIDs).
3. Raw-to-normalized 1:1 mapping with no silent record loss.
4. Semantic duplicate audit (exact duplicates = 0, composite key dups = 0, candidate pair G9 376 / 376 identified and preserved).
5. Airline role semantics (displayed_airline_brand, no operating carrier inference, 14 brands).
6. Flight status semantics (segregation of scheduled_status, displayed_status, actual_movement_evidence = 0, arrived != physical_movement).
7. Date & local time preservation (67 dates, Asia/Damascus UTC+3, UTC rollover math).
8. Existence of all 6 documentation files and 5 machine-readable reports.
"""

import os
import csv
import json
import sqlite3
import hashlib
import pytest
from datetime import datetime, timedelta

PROD_DB_PATH = "data/damascus_airport.db"
STAGING_DB_PATH = "data/archived_fids_staging.db"
BACKUP_DB_PATH = "data/backup_archived_fids_staging_v2_14.db"
EXPECTED_PROD_HASH = "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"
RAW_SNAPSHOT_JSON = "data/raw/snapshots/wayback_damairport_fids_20260709234230.json"

REQUIRED_DOCS = [
    "docs/V2_14_1_RECORD_IDENTITY_AUDIT.md",
    "docs/V2_14_1_SEMANTIC_DUPLICATE_AUDIT.md",
    "docs/V2_14_1_AIRLINE_SEMANTICS.md",
    "docs/V2_14_1_STATUS_SEMANTICS.md",
    "docs/V2_14_1_TIMEZONE_AUDIT.md",
    "docs/V2_14_1_FINAL_DECISION.md"
]

REQUIRED_REPORTS = [
    "reports/v2_14_1_record_identity.csv",
    "reports/v2_14_1_duplicate_candidates.csv",
    "reports/v2_14_1_airline_distribution.csv",
    "reports/v2_14_1_daily_coverage.csv",
    "reports/v2_14_1_status_distribution.csv"
]

def get_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def test_production_database_immutability_v2_14_1():
    """Verify production database remains strictly untouched and bit-identical."""
    assert os.path.exists(PROD_DB_PATH), "Production DB missing"
    current_hash = get_hash(PROD_DB_PATH)
    assert current_hash == EXPECTED_PROD_HASH, f"Production DB hash changed: {current_hash}"

def test_source_uuid_uniqueness_and_completeness():
    """Verify all 1,982 records have valid, unique source UUIDs."""
    assert os.path.exists(STAGING_DB_PATH), "Staging DB missing"
    conn = sqlite3.connect(f"file:{STAGING_DB_PATH}?mode=ro", uri=True)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*), COUNT(source_uuid), COUNT(DISTINCT source_uuid) FROM archived_fids_normalized")
    total, non_null, distinct = cur.fetchone()

    assert total == 1982
    assert non_null == 1982
    assert distinct == 1982

    # Verify UUID format (length 36, contains 4 hyphens)
    cur.execute("SELECT source_uuid FROM archived_fids_normalized")
    for (uuid_val,) in cur.fetchall():
        assert len(uuid_val) == 36
        assert uuid_val.count("-") == 4

    conn.close()

def test_raw_to_normalized_one_to_one_mapping_and_no_silent_loss():
    """Verify exact 1:1 mapping between raw JSON objects and normalized records."""
    with open(RAW_SNAPSHOT_JSON, "r", encoding="utf-8") as f:
        payload = json.load(f)
    raw_flights = payload.get("flights", [])
    assert len(raw_flights) == 1982

    conn = sqlite3.connect(f"file:{STAGING_DB_PATH}?mode=ro", uri=True)
    cur = conn.cursor()

    # Raw table count
    cur.execute("SELECT COUNT(*) FROM archived_fids_raw_records")
    assert cur.fetchone()[0] == 1982

    # Normalized table count
    cur.execute("SELECT COUNT(*) FROM archived_fids_normalized")
    assert cur.fetchone()[0] == 1982

    # 1:1 Foreign Key Join
    cur.execute("""
    SELECT COUNT(*)
    FROM archived_fids_raw_records r
    JOIN archived_fids_normalized n ON r.raw_record_id = n.raw_record_id
    WHERE r.source_id = n.source_uuid
    """)
    assert cur.fetchone()[0] == 1982

    conn.close()

def test_duplicate_classification_and_candidates():
    """Verify duplicate candidate detection and preservation of all records."""
    conn = sqlite3.connect(f"file:{STAGING_DB_PATH}?mode=ro", uri=True)
    cur = conn.cursor()

    # 1. Zero exact duplicate composite keys
    cur.execute("SELECT COUNT(DISTINCT composite_key) FROM archived_fids_normalized")
    assert cur.fetchone()[0] == 1982

    # 2. Check the candidate duplicate pair (G9 376 vs 376 on 2026-07-08 at 13:55)
    cur.execute("""
    SELECT source_uuid, flight_number, movement_type, origin_iata, destination_iata, scheduled_date, scheduled_time
    FROM archived_fids_normalized
    WHERE scheduled_date = '2026-07-08' AND scheduled_time = '13:55' AND movement_type = 'departure'
    """)
    dup_pair = cur.fetchall()
    assert len(dup_pair) == 2, "Expected candidate pair G9 376 / 376"

    fns = sorted([r[1] for r in dup_pair])
    assert fns == ["376", "G9376"]

    # Verify both records are preserved in database without silent deletion
    uuids = [r[0] for r in dup_pair]
    assert "e5ada70d-5245-46d4-b043-bf469c1d104f" in uuids
    assert "2d2a0935-da5e-42c4-ad15-e10b4e2291ee" in uuids

    conn.close()

def test_airline_role_semantics_and_distribution():
    """Verify displayed_airline_brand role semantics and 14 airline distribution."""
    conn = sqlite3.connect(f"file:{STAGING_DB_PATH}?mode=ro", uri=True)
    cur = conn.cursor()

    # All records must have role 'displayed_airline_brand'
    cur.execute("SELECT DISTINCT airline_role FROM archived_fids_normalized")
    roles = [r[0] for r in cur.fetchall()]
    assert roles == ["displayed_airline_brand"]

    # 14 distinct displayed airline brands
    cur.execute("SELECT COUNT(DISTINCT airline_name_ar) FROM archived_fids_normalized")
    assert cur.fetchone()[0] == 14

    # Directional totals reconcile
    cur.execute("SELECT movement_type, COUNT(*) FROM archived_fids_normalized GROUP BY movement_type")
    dir_counts = dict(cur.fetchall())
    assert dir_counts["arrival"] == 993
    assert dir_counts["departure"] == 989
    assert dir_counts["arrival"] + dir_counts["departure"] == 1982

    conn.close()

def test_status_semantics_and_segregation():
    """Verify segregation of scheduled_status, displayed_status, and actual_movement_evidence."""
    conn = sqlite3.connect(f"file:{STAGING_DB_PATH}?mode=ro", uri=True)
    cur = conn.cursor()

    # actual_movement_evidence must be 0 for all records (no ADS-B/radar sensors)
    cur.execute("SELECT DISTINCT actual_movement_evidence FROM archived_fids_normalized")
    evidence_vals = [r[0] for r in cur.fetchall()]
    assert evidence_vals == [0]

    # Exactly 1 arrived status
    cur.execute("SELECT COUNT(*) FROM archived_fids_normalized WHERE displayed_status = 'arrived'")
    assert cur.fetchone()[0] == 1

    # Exactly 1981 scheduled status
    cur.execute("SELECT COUNT(*) FROM archived_fids_normalized WHERE displayed_status = 'scheduled'")
    assert cur.fetchone()[0] == 1981

    # Verify arrived record details (XH 728 on 2026-07-06)
    cur.execute("""
    SELECT source_uuid, flight_number, scheduled_date, scheduled_time, displayed_status, classification
    FROM archived_fids_normalized
    WHERE displayed_status = 'arrived'
    """)
    row = cur.fetchone()
    assert row[0] == "a3c520d5-a113-4646-bdff-c60c2e8e27b9"
    assert row[1] == "XH728"
    assert row[2] == "2026-07-06"
    assert row[3] == "00:20"
    assert row[5] != "physical_movement"

    # Strict prohibition on physical_movement
    cur.execute("SELECT COUNT(*) FROM archived_fids_normalized WHERE classification = 'physical_movement'")
    assert cur.fetchone()[0] == 0

    conn.close()

def test_date_coverage_and_local_time_preservation():
    """Verify 67 continuous days and correct Asia/Damascus local-to-UTC conversion."""
    conn = sqlite3.connect(f"file:{STAGING_DB_PATH}?mode=ro", uri=True)
    cur = conn.cursor()

    cur.execute("SELECT MIN(scheduled_date), MAX(scheduled_date), COUNT(DISTINCT scheduled_date) FROM archived_fids_normalized")
    min_date, max_date, date_count = cur.fetchone()

    assert min_date == "2026-07-05"
    assert max_date == "2026-09-09"
    assert date_count == 67

    # Verify UTC math preserves Damascus UTC+3 offset
    cur.execute("""
    SELECT scheduled_date, scheduled_time, scheduled_datetime_local, scheduled_datetime_utc
    FROM archived_fids_normalized
    WHERE scheduled_time = '00:20' AND scheduled_date = '2026-07-06'
    LIMIT 1
    """)
    r = cur.fetchone()
    # 00:20 local on July 6 is 21:20 UTC on July 5
    assert r[2] == "2026-07-06T00:20:00+03:00"
    assert r[3] == "2026-07-05T21:20:00Z"

    conn.close()

def test_machine_readable_reports_validity():
    """Verify all 5 machine-readable reports exist, are non-empty, and reconcile to 1,982."""
    for rep in REQUIRED_REPORTS:
        assert os.path.exists(rep), f"Missing report: {rep}"
        assert os.path.getsize(rep) > 100, f"Report empty: {rep}"

    # Verify report 1 row count (1,982 rows + 1 header = 1,983 lines)
    with open("reports/v2_14_1_record_identity.csv", "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        assert len(reader) == 1983

    # Verify airline distribution sum
    with open("reports/v2_14_1_airline_distribution.csv", "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 14
        total_fl = sum(int(r["total_reported_flights"]) for r in reader)
        assert total_fl == 1982
        for r in reader:
            assert r["carrier_role_classification"] == "displayed_airline_brand"
            assert r["is_operating_carrier_verified"] == "FALSE"

    # Verify status distribution sum
    with open("reports/v2_14_1_status_distribution.csv", "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 2
        total_st = sum(int(r["record_count"]) for r in reader)
        assert total_st == 1982

def test_documentation_files_exist():
    """Verify all 6 required documentation files exist and are non-empty."""
    for doc in REQUIRED_DOCS:
        assert os.path.exists(doc), f"Missing documentation: {doc}"
        assert os.path.getsize(doc) > 200, f"Documentation file too small: {doc}"
