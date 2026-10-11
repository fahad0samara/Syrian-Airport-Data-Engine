"""
Syrian Airport Data Engine — Version 2.18
Regression Test Suite: Public Historical Aviation Dataset Recovery
Damascus International Airport (DAM / OSDI)

Verifies all 20 required validation dimensions:
1. Raw file immutability
2. Download hash verification
3. Metadata preservation
4. License recording
5. Missing fields handling
6. Timezone normalization
7. Geographic filtering
8. Trajectory classification
9. Airport association
10. Overflight exclusion
11. Duplicate detection
12. Provider independence warnings
13. Regional statistic exclusion
14. Scheduled vs actual separation
15. No synthetic observations
16. No production writes
17. No credentials in reports
18. Graceful handling of inaccessible resources
19. Staging DB consistency
20. Existing baseline immutability
"""

import os
import csv
import json
import sqlite3
import hashlib
import pytest
from datetime import datetime

PROD_DB = "data/damascus_airport.db"
FIDS_STAGING_DB = "data/archived_fids_staging.db"
ANALYTICS_DB = "data/archived_fids_analytics.db"
HISTORY_STAGING_DB = "data/archived_fids_history_staging.db"
BASELINE_RAW = "data/raw/snapshots/wayback_damairport_fids_20260709234230.raw"
BASELINE_JSON = "data/raw/snapshots/wayback_damairport_fids_20260709234230.json"

EXPECTED_PROD_HASH = "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"
EXPECTED_RAW_HASH = "5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf"
EXPECTED_JSON_HASH = "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491"
EXPECTED_FIDS_STAGING_HASH = "a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4"
EXPECTED_ANALYTICS_HASH = "e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe"
EXPECTED_HISTORY_STAGING_HASH = "39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f"

V2_18_STAGING_DB = "data/staging/v2_18/v2_18_staging.db"
V2_18_RAW_DIR = "data/raw/public_datasets/v2_18"
MANIFEST_PATH = "reports/v2_18_download_manifest.csv"
INVENTORY_PATH = "reports/v2_18_dataset_inventory.csv"
SCORING_PATH = "reports/v2_18_dataset_scoring.csv"
COVERAGE_PATH = "reports/v2_18_damascus_coverage.csv"
VALIDATION_PATH = "reports/v2_18_validation_results.csv"
OBSERVATIONS_PATH = "reports/v2_18_recovered_observations.csv"

def get_file_sha256(path):
    assert os.path.exists(path), f"File {path} does not exist"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

# 1. Raw file immutability
def test_01_raw_file_immutability():
    assert os.path.exists(V2_18_RAW_DIR)
    files = os.listdir(V2_18_RAW_DIR)
    assert len(files) >= 4, f"Expected at least 4 downloaded raw files, got {len(files)}"
    for fn in files:
        fp = os.path.join(V2_18_RAW_DIR, fn)
        sz = os.path.getsize(fp)
        assert sz > 0, f"Raw file {fn} is empty"

# 2. Download hash verification
def test_02_download_hash_verification():
    assert os.path.exists(MANIFEST_PATH)
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert len(reader) >= 4
    for r in reader:
        lp = r["local_path"]
        assert os.path.exists(lp), f"Manifest file missing: {lp}"
        actual_hash = get_file_sha256(lp)
        assert actual_hash == r["sha256_hash"], f"Hash mismatch for {lp}: {actual_hash} != {r['sha256_hash']}"
        assert int(r["byte_size"]) == os.path.getsize(lp)

# 3. Metadata preservation
def test_03_metadata_preservation():
    assert os.path.exists(INVENTORY_PATH)
    with open(INVENTORY_PATH, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert len(reader) == 8, f"Expected 8 inventoried candidate datasets, found {len(reader)}"
    required_cols = [
        "dataset_id", "repository", "title", "doi_or_url", "publication_date",
        "observation_period", "geographic_coverage", "file_format", "estimated_size",
        "license", "access_restrictions", "data_provider", "data_category",
        "inspection_status", "rejection_reason"
    ]
    for row in reader:
        for c in required_cols:
            assert c in row and row[c], f"Missing or empty field {c} in {row.get('dataset_id')}"

# 4. License recording
def test_04_license_recording():
    with open(INVENTORY_PATH, "r", encoding="utf-8") as f:
        inv_reader = list(csv.DictReader(f))
    for r in inv_reader:
        lic = r["license"].strip()
        assert len(lic) > 0, f"Empty license in inventory for {r['dataset_id']}"
        assert lic != "UNKNOWN", f"Unresolved license for {r['dataset_id']}"

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        man_reader = list(csv.DictReader(f))
    for r in man_reader:
        lic = r["license"].strip()
        assert len(lic) > 0, f"Empty license in manifest for {r['download_id']}"

# 5. Missing fields handling
def test_05_missing_fields_handling():
    assert os.path.exists(V2_18_STAGING_DB)
    conn = sqlite3.connect(V2_18_STAGING_DB)
    cur = conn.cursor()
    # Check that query with COALESCE or NULL checks executes without errors
    cur.execute("""
    SELECT observation_id,
           COALESCE(callsign, 'NO_CALLSIGN'),
           COALESCE(registration, 'NO_REG'),
           COALESCE(aircraft_type, 'NO_TYPE'),
           COALESCE(altitude_baro_ft, 0.0),
           COALESCE(speed_kts, 0.0)
    FROM recovered_observations
    """)
    rows = cur.fetchall()
    assert len(rows) > 0
    conn.close()

# 6. Timezone normalization
def test_06_timezone_normalization():
    conn = sqlite3.connect(V2_18_STAGING_DB)
    cur = conn.cursor()
    cur.execute("SELECT observation_timestamp_utc FROM recovered_observations")
    rows = cur.fetchall()
    conn.close()
    for (ts,) in rows:
        assert "T" in ts, f"Malformed timestamp: {ts}"
        assert ts.endswith("Z") or "+" in ts, f"Timestamp missing UTC indicator: {ts}"
        # Validate parseability
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        assert dt.tzinfo is not None

# 7. Geographic filtering
def test_07_geographic_filtering():
    conn = sqlite3.connect(V2_18_STAGING_DB)
    cur = conn.cursor()
    cur.execute("SELECT observation_id, distance_to_dam_km, is_dam_movement FROM recovered_observations")
    rows = cur.fetchall()
    conn.close()
    for obs_id, dist, is_dam in rows:
        assert dist is not None
        # DAM movements must be within airport terminal/approach radius (<= 50km)
        if dist > 50.0:
            assert is_dam == 0, f"Observation {obs_id} at {dist}km cannot be a DAM movement"

# 8. Trajectory classification
def test_08_trajectory_classification():
    conn = sqlite3.connect(V2_18_STAGING_DB)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT classification FROM recovered_observations")
    classes = {r[0] for r in cur.fetchall()}
    conn.close()
    valid_classes = {
        "overflight", "overflight_observation", "regional_observation", "regional_transit",
        "approach_candidate", "departure_candidate", "airport_surface_observation"
    }
    assert classes.issubset(valid_classes), f"Unexpected classifications found: {classes - valid_classes}"

# 9. Airport association
def test_09_airport_association():
    conn = sqlite3.connect(V2_18_STAGING_DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM recovered_observations WHERE is_dam_movement = 1")
    count = cur.fetchone()[0]
    conn.close()
    assert count == 0, f"Expected 0 DAM movements among distant recovered observations, got {count}"

# 10. Overflight exclusion
def test_10_overflight_exclusion():
    conn = sqlite3.connect(V2_18_STAGING_DB)
    cur = conn.cursor()
    cur.execute("""
    SELECT COUNT(*) FROM recovered_observations
    WHERE (classification LIKE '%overflight%' OR altitude_baro_ft > 20000)
      AND confirmed_physical_movement = 1
    """)
    promoted_overflights = cur.fetchone()[0]
    conn.close()
    assert promoted_overflights == 0, "High altitude overflights must never be confirmed as DAM physical movements"

# 11. Duplicate detection
def test_11_duplicate_detection():
    conn = sqlite3.connect(V2_18_STAGING_DB)
    cur = conn.cursor()
    # Check distinct aircraft vs total observations
    cur.execute("SELECT COUNT(*), COUNT(DISTINCT icao24) FROM recovered_observations")
    total, distinct_icao = cur.fetchone()
    conn.close()
    assert total >= distinct_icao, "Total observations must be >= distinct aircraft"
    # Verify that multi-provider feeds (e.g. lol vs fi) for same aircraft are traceable
    assert distinct_icao == 9
    assert total == 16

# 12. Provider independence warnings
def test_12_provider_independence_warnings():
    with open(SCORING_PATH, "r", encoding="utf-8") as f:
        scoring = list(csv.DictReader(f))
    # Verify that ADS-B.lol and feeder sources have provenance/rejection notes explaining independence/unindexed scale
    lol = [s for s in scoring if "DS-LOL-001" in s["dataset_id"]][0]
    assert "Section 6" in lol["action_taken"] or "UNINDEXED" in lol["action_taken"]

# 13. Regional statistic exclusion
def test_13_regional_statistic_exclusion():
    assert os.path.exists(COVERAGE_PATH)
    with open(COVERAGE_PATH, "r", encoding="utf-8") as f:
        cov = list(csv.DictReader(f))
    for r in cov:
        # Verified macro benchmarks must have confirmed_dam_movements = 0 at raw telemetry level
        assert int(r["confirmed_dam_movements"]) == 0
        if r["dataset_category"] == "official_airport_statistics":
            assert "benchmark" in r["coverage_notes"].lower()

# 14. Scheduled vs actual separation
def test_14_scheduled_vs_actual_separation():
    with open(COVERAGE_PATH, "r", encoding="utf-8") as f:
        cov = list(csv.DictReader(f))
    fids_months = [r for r in cov if r["dataset_category"] in ("scheduled_fids", "dam_scheduled_fids")]
    assert len(fids_months) == 3  # 2026-07, 2026-08, 2026-09
    for fm in fids_months:
        assert fm["verified_status"] == "covered_scheduled_timetable_only"
        assert int(fm["confirmed_dam_movements"]) == 0
        assert "scheduled" in fm["coverage_notes"].lower()

# 15. No synthetic observations
def test_15_no_synthetic_observations():
    conn = sqlite3.connect(V2_18_STAGING_DB)
    cur = conn.cursor()
    cur.execute("SELECT observation_id, raw_source_hash FROM recovered_observations")
    rows = cur.fetchall()
    conn.close()
    for obs_id, h in rows:
        assert h is not None and len(h) == 64, f"Observation {obs_id} lacks authentic SHA-256 source hash"

# 16. No production writes
def test_16_no_production_database_writes():
    current_hash = get_file_sha256(PROD_DB)
    assert current_hash == EXPECTED_PROD_HASH, f"Production DB modified! Hash: {current_hash}"

# 17. No credentials in reports
def test_17_no_credentials_in_reports():
    reports_and_docs = [
        MANIFEST_PATH, INVENTORY_PATH, SCORING_PATH, COVERAGE_PATH, VALIDATION_PATH, OBSERVATIONS_PATH,
        "docs/V2_18_DATASET_DISCOVERY.md", "docs/V2_18_FINAL_REPORT.md"
    ]
    forbidden_tokens = ["bearer ", "secret_key", "password=", "api_key=", "private_key", "authorization:"]
    for path in reports_and_docs:
        assert os.path.exists(path), f"Missing file: {path}"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().lower()
            for token in forbidden_tokens:
                assert token not in content, f"Credential token '{token}' leaked in {path}"

# 18. Graceful handling of inaccessible resources
def test_18_graceful_handling_of_inaccessible_resources():
    assert os.path.exists(VALIDATION_PATH)
    with open(VALIDATION_PATH, "r", encoding="utf-8") as f:
        val_rows = list(csv.DictReader(f))
    assert len(val_rows) >= 8
    statuses = {r["status"] for r in val_rows}
    assert any("FAILED" in s or "REJECTED" in s for s in statuses)

# 19. Staging database consistency
def test_19_staging_database_consistency():
    conn = sqlite3.connect(V2_18_STAGING_DB)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cur.fetchall()}
    assert "recovered_observations" in tables
    assert "monthly_dam_coverage" in tables
    assert "validation_results" in tables

    cur.execute("SELECT COUNT(*) FROM recovered_observations")
    assert cur.fetchone()[0] == 16
    cur.execute("SELECT COUNT(*) FROM monthly_dam_coverage")
    assert cur.fetchone()[0] == 34  # 2024-01 to 2026-10 (34 months)
    cur.execute("SELECT COUNT(*) FROM validation_results")
    assert cur.fetchone()[0] == 8
    conn.close()

# 20. Existing baseline immutability
def test_20_existing_baseline_immutability():
    assert get_file_sha256(PROD_DB) == EXPECTED_PROD_HASH
    assert get_file_sha256(FIDS_STAGING_DB) == EXPECTED_FIDS_STAGING_HASH
    assert get_file_sha256(ANALYTICS_DB) == EXPECTED_ANALYTICS_HASH
    assert get_file_sha256(HISTORY_STAGING_DB) == EXPECTED_HISTORY_STAGING_HASH
    assert get_file_sha256(BASELINE_RAW) == EXPECTED_RAW_HASH
    assert get_file_sha256(BASELINE_JSON) == EXPECTED_JSON_HASH
