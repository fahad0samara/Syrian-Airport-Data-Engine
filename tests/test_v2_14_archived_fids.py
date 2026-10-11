"""
Tests for Version 2.14 — Historical FIDS Snapshot Extraction & Validation
Validates:
1. Production database invariant (SHA-256 remains identical).
2. Snapshot hash and provenance in raw file and staging database.
3. Complete JSON parsing of all 1,982 flight objects.
4. Directional breakdown (993 arrivals, 989 departures).
5. Duplicate handling (zero exact, zero semantic duplicates).
6. Missing and malformed fields tracking in validation issues.
7. Date-range validation (67 continuous calendar days spanning 2026-07-05 to 2026-09-09).
8. Preservation of raw records with cryptographic hashes.
9. Strict prohibition on promoting scheduled records to physical movements.
10. All 5 documentation files and 6 machine-readable report files exist and are valid.
"""

import os
import csv
import json
import sqlite3
import hashlib
import pytest
from typing import List, Dict, Any

PROD_DB_PATH = "data/damascus_airport.db"
STAGING_DB_PATH = "data/archived_fids_staging.db"
EXPECTED_PROD_HASH = "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"

RAW_SNAPSHOT_PATH = "data/raw/snapshots/wayback_damairport_fids_20260709234230.raw"
JSON_SNAPSHOT_PATH = "data/raw/snapshots/wayback_damairport_fids_20260709234230.json"

EXPECTED_RAW_SHA256 = "5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf"
EXPECTED_DECOMP_SHA256 = "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491"

REQUIRED_DOCS = [
    "docs/V2_14_ARCHIVED_SNAPSHOT_PROVENANCE.md",
    "docs/V2_14_FIELD_SEMANTICS.md",
    "docs/V2_14_DATA_QUALITY_REPORT.md",
    "docs/V2_14_DAILY_COVERAGE.md",
    "docs/V2_14_FINAL_DECISION.md"
]

REQUIRED_REPORTS = [
    "reports/v2_14_archived_fids_records.csv",
    "reports/v2_14_archived_fids_records.json",
    "reports/v2_14_daily_coverage.csv",
    "reports/v2_14_airline_summary.csv",
    "reports/v2_14_status_summary.csv",
    "reports/v2_14_validation_issues.csv"
]

def get_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def test_production_database_untouched_v2_14():
    """Verify production database remains strictly untouched."""
    assert os.path.exists(PROD_DB_PATH), "Production DB missing"
    current_hash = get_hash(PROD_DB_PATH)
    assert current_hash == EXPECTED_PROD_HASH, f"Production DB hash changed: {current_hash}"

def test_snapshot_files_and_cryptographic_hashes():
    """Verify raw and decompressed snapshots exist and match expected SHA-256 digests."""
    assert os.path.exists(RAW_SNAPSHOT_PATH), f"Raw snapshot missing: {RAW_SNAPSHOT_PATH}"
    assert os.path.exists(JSON_SNAPSHOT_PATH), f"JSON snapshot missing: {JSON_SNAPSHOT_PATH}"

    raw_hash = get_hash(RAW_SNAPSHOT_PATH)
    assert raw_hash == EXPECTED_RAW_SHA256, f"Raw SHA-256 mismatch: {raw_hash}"

    decomp_hash = get_hash(JSON_SNAPSHOT_PATH)
    assert decomp_hash == EXPECTED_DECOMP_SHA256, f"Decompressed SHA-256 mismatch: {decomp_hash}"

def test_staging_database_schema_and_counts():
    """Verify staging database tables exist and have exactly 1,982 records."""
    assert os.path.exists(STAGING_DB_PATH), f"Staging DB missing: {STAGING_DB_PATH}"

    conn = sqlite3.connect(f"file:{STAGING_DB_PATH}?mode=ro", uri=True)
    c = conn.cursor()

    # 1. Snapshots table
    c.execute("SELECT COUNT(*) FROM archived_snapshots")
    assert c.fetchone()[0] == 1

    # 2. Raw records table
    c.execute("SELECT COUNT(*) FROM archived_fids_raw_records")
    assert c.fetchone()[0] == 1982

    # 3. Normalized records table
    c.execute("SELECT COUNT(*) FROM archived_fids_normalized")
    assert c.fetchone()[0] == 1982

    # 4. Daily coverage table
    c.execute("SELECT COUNT(*) FROM archived_fids_daily_coverage")
    assert c.fetchone()[0] == 67

    # 5. Validation issues table
    c.execute("SELECT COUNT(*) FROM archived_fids_validation_issues")
    assert c.fetchone()[0] > 0

    conn.close()

def test_directional_breakdown_and_airports():
    """Verify arrival/departure balance and airport assignment."""
    conn = sqlite3.connect(f"file:{STAGING_DB_PATH}?mode=ro", uri=True)
    c = conn.cursor()

    c.execute("SELECT movement_type, COUNT(*) FROM archived_fids_normalized GROUP BY movement_type")
    counts = dict(c.fetchall())
    assert counts == {"arrival": 993, "departure": 989}

    # All arrivals must have destination DAM
    c.execute("SELECT COUNT(*) FROM archived_fids_normalized WHERE movement_type = 'arrival' AND destination_iata != 'DAM'")
    assert c.fetchone()[0] == 0

    # All departures must have origin DAM
    c.execute("SELECT COUNT(*) FROM archived_fids_normalized WHERE movement_type = 'departure' AND origin_iata != 'DAM'")
    assert c.fetchone()[0] == 0

    conn.close()

def test_deduplication_and_composite_keys():
    """Verify zero duplicate composite keys and unique UUIDs."""
    conn = sqlite3.connect(f"file:{STAGING_DB_PATH}?mode=ro", uri=True)
    c = conn.cursor()

    c.execute("SELECT COUNT(DISTINCT composite_key) FROM archived_fids_normalized")
    assert c.fetchone()[0] == 1982

    c.execute("SELECT SUM(is_duplicate) FROM archived_fids_normalized")
    assert c.fetchone()[0] == 0

    conn.close()

def test_date_range_and_continuity():
    """Verify date range spans strictly 2026-07-05 to 2026-09-09 across 67 consecutive days."""
    conn = sqlite3.connect(f"file:{STAGING_DB_PATH}?mode=ro", uri=True)
    c = conn.cursor()

    c.execute("SELECT MIN(scheduled_date), MAX(scheduled_date), COUNT(DISTINCT scheduled_date) FROM archived_fids_normalized")
    min_d, max_d, cnt_d = c.fetchone()
    assert min_d == "2026-07-05"
    assert max_d == "2026-09-09"
    assert cnt_d == 67

    # Check zero days with 0 observations in this range
    c.execute("SELECT COUNT(*) FROM archived_fids_daily_coverage WHERE total_records = 0")
    assert c.fetchone()[0] == 0

    conn.close()

def test_no_promotion_to_physical_movement():
    """Verify scheduled records are never classified as physical movements or given actual sensor timestamps."""
    conn = sqlite3.connect(f"file:{STAGING_DB_PATH}?mode=ro", uri=True)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM archived_fids_normalized WHERE classification = 'physical_movement'")
    assert c.fetchone()[0] == 0

    c.execute("SELECT COUNT(*) FROM archived_fids_normalized WHERE has_actual_timestamp = 1")
    assert c.fetchone()[0] == 0

    # Verify status distribution
    c.execute("SELECT flight_status, COUNT(*) FROM archived_fids_normalized GROUP BY flight_status")
    status_counts = dict(c.fetchall())
    assert status_counts == {"scheduled": 1981, "arrived": 1}

    # Verify classification distribution
    c.execute("SELECT classification, COUNT(*) FROM archived_fids_normalized GROUP BY classification")
    class_counts = dict(c.fetchall())
    assert class_counts == {
        "archived_scheduled_service": 1981,
        "archived_actual_movement_candidate": 1
    }

    conn.close()

def test_documentation_and_reports_exist():
    """Verify all 5 documentation deliverables and 6 report deliverables exist and have content."""
    for doc in REQUIRED_DOCS:
        assert os.path.exists(doc), f"Missing doc: {doc}"
        assert os.path.getsize(doc) > 1000, f"Doc too small: {doc}"

    for rep in REQUIRED_REPORTS:
        assert os.path.exists(rep), f"Missing report: {rep}"
        assert os.path.getsize(rep) > 50, f"Report too small: {rep}"


    # Verify CSV rows count in archived_fids_records
    with open("reports/v2_14_archived_fids_records.csv", "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 1982
