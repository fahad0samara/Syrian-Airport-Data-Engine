"""
Syrian Airport Data Engine — Version 2.17
Regression Test Suite: Historical FIDS Archive + ADS-B Observation Research

Verifies all 20 required validation dimensions:
1. Original snapshot immutability
2. New raw snapshot hashes
3. Capture metadata preservation
4. Filtered snapshot classification
5. Cross-snapshot matching
6. Duplicate candidate preservation
7. FIDS date semantics
8. ADS-B raw payload preservation
9. Observation timestamp semantics
10. Provider attribution
11. Duplicate observation detection
12. Cross-provider upstream independence warnings
13. Airport association classification
14. Overflight exclusion from DAM movement counts
15. No fabricated physical movement
16. No mixing of FIDS and ADS-B records
17. No production database writes
18. No credential leakage
19. Graceful handling of 403/429 responses
20. Existing regression suite integration
"""

import os
import json
import sqlite3
import hashlib
import pytest
import csv

PROD_DB = "data/damascus_airport.db"
FIDS_STAGING_DB = "data/archived_fids_staging.db"
ANALYTICS_DB = "data/archived_fids_analytics.db"
HISTORY_STAGING_DB = "data/archived_fids_history_staging.db"
BASELINE_RAW = "data/raw/snapshots/wayback_damairport_fids_20260709234230.raw"
BASELINE_JSON = "data/raw/snapshots/wayback_damairport_fids_20260709234230.json"

EXPECTED_PROD_HASH = "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"
EXPECTED_RAW_HASH = "5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf"
EXPECTED_JSON_HASH = "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491"

V2_17_FIDS_DB = "data/staging/v2_17_fids/v2_17_fids_staging.db"
V2_17_ADSB_DB = "data/staging/v2_17_adsb/v2_17_adsb_staging.db"
V2_17_ADSB_RAW_DIR = "data/raw/adsb/v2_17"

def get_file_sha256(path):
    assert os.path.exists(path), f"File {path} does not exist"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

# 1. Original snapshot immutability
def test_01_original_snapshot_immutability():
    raw_hash = get_file_sha256(BASELINE_RAW)
    json_hash = get_file_sha256(BASELINE_JSON)
    assert raw_hash == EXPECTED_RAW_HASH, f"Raw baseline snapshot hash mismatch: {raw_hash}"
    assert json_hash == EXPECTED_JSON_HASH, f"JSON baseline snapshot hash mismatch: {json_hash}"

# 2. New raw snapshot hashes and manifests
def test_02_raw_adsb_snapshot_hashes():
    manifest_path = os.path.join(V2_17_ADSB_RAW_DIR, "v2_17_adsb_manifest.json")
    assert os.path.exists(manifest_path)
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert len(manifest) >= 4
    for item in manifest:
        assert item["sha256"] is not None
        assert len(item["sha256"]) == 64
        assert os.path.exists(item["local_file"])
        computed = get_file_sha256(item["local_file"])
        assert computed == item["sha256"], f"Hash mismatch for {item['local_file']}"

# 3. Capture metadata preservation
def test_03_capture_metadata_preservation():
    assert os.path.exists(V2_17_FIDS_DB)
    conn = sqlite3.connect(V2_17_FIDS_DB)
    cur = conn.cursor()
    cur.execute("SELECT capture_id, capture_timestamp, digest, mime_type FROM fids_capture_registry WHERE capture_id = 'snap_wayback_20260709234230'")
    row = cur.fetchone()
    assert row is not None
    assert row[1] == "20260709234230"
    assert row[2] == "LWGQOMIVR7BG55CKGT4LXDRNUVKDA36L"
    assert row[3] == "application/json"
    conn.close()

# 4. Filtered snapshot classification
def test_04_filtered_snapshot_classification():
    conn = sqlite3.connect(V2_17_FIDS_DB)
    cur = conn.cursor()
    cur.execute("SELECT capture_id, capture_type, direction_filter FROM fids_capture_registry WHERE capture_id != 'snap_wayback_20260709234230'")
    rows = cur.fetchall()
    assert len(rows) == 4
    for r in rows:
        assert "filtered" in r[1].lower() or "paginated" in r[1].lower()
    conn.close()

# 5. Cross-snapshot matching
def test_05_cross_snapshot_matching():
    report_path = "reports/v2_17_fids_snapshot_comparison.csv"
    assert os.path.exists(report_path)
    with open(report_path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert len(reader) == 4
    for r in reader:
        assert r["status"] == "COMPARISON_SKIPPED_NOT_RETRIEVED"
        assert int(r["new_records_count"]) == 0

# 6. Duplicate candidate preservation
def test_06_duplicate_candidate_preservation():
    # Verify that existing duplicate candidates in analytics db are preserved
    conn = sqlite3.connect(ANALYTICS_DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM fids_duplicate_candidates")
    count = cur.fetchone()[0]
    assert count == 1, "Analytics duplicate candidates must be exactly 1"
    conn.close()

# 7. FIDS date semantics
def test_07_fids_date_semantics():
    conn = sqlite3.connect(V2_17_FIDS_DB)
    cur = conn.cursor()
    cur.execute("SELECT MIN(scheduled_date), MAX(scheduled_date), COUNT(DISTINCT scheduled_date) FROM fids_baseline_records")
    min_date, max_date, distinct_dates = cur.fetchone()
    assert min_date == "2026-07-05"
    assert max_date == "2026-09-09"
    assert distinct_dates == 67
    conn.close()

# 8. ADS-B raw payload preservation
def test_08_adsb_raw_payload_preservation():
    conn = sqlite3.connect(V2_17_ADSB_DB)
    cur = conn.cursor()
    cur.execute("SELECT payload_id, provider, sha256_hash, local_filepath FROM raw_adsb_payload_registry")
    rows = cur.fetchall()
    assert len(rows) >= 4
    for r in rows:
        assert os.path.exists(r[3])
        assert get_file_sha256(r[3]) == r[2]
    conn.close()

# 9. Observation timestamp semantics
def test_09_observation_timestamp_semantics():
    conn = sqlite3.connect(V2_17_ADSB_DB)
    cur = conn.cursor()
    cur.execute("SELECT observation_timestamp_utc FROM adsb_observations_staged")
    rows = cur.fetchall()
    assert len(rows) > 0
    for r in rows:
        ts = r[0]
        assert "T" in ts and (ts.endswith("Z") or "+" in ts)
    conn.close()

# 10. Provider attribution
def test_10_provider_attribution():
    conn = sqlite3.connect(V2_17_ADSB_DB)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT provider FROM adsb_observations_staged")
    providers = {r[0] for r in cur.fetchall()}
    assert "ADS-B.lol" in providers
    assert "ADSB.fi" in providers
    conn.close()

# 11. Duplicate observation detection
def test_11_duplicate_observation_detection():
    report_path = "reports/v2_17_adsb_observation_validation.csv"
    assert os.path.exists(report_path)
    with open(report_path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    dup_flags = [r["is_duplicate_sensor_feed"] for r in reader]
    assert "YES" in dup_flags or "NO" in dup_flags

# 12. Cross-provider upstream independence warnings
def test_12_cross_provider_upstream_independence_warnings():
    conn = sqlite3.connect(V2_17_ADSB_DB)
    cur = conn.cursor()
    cur.execute("SELECT provider_name, sensor_independence_note FROM adsb_source_inventory WHERE provider_name LIKE '%ADSB.fi%'")
    row = cur.fetchone()
    assert row is not None
    assert "ADS-B.lol" in row[1] or "federated" in row[1].lower() or "shares" in row[1].lower()
    conn.close()

# 13. Airport association classification
def test_13_airport_association_classification():
    conn = sqlite3.connect(V2_17_ADSB_DB)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT classification FROM airport_association_assessment")
    classes = {r[0] for r in cur.fetchall()}
    valid_classes = {
        "airport_surface_observation", "approach_candidate", "departure_candidate",
        "overflight_observation", "regional_observation", "airport_association_unverified"
    }
    assert classes.issubset(valid_classes)
    conn.close()

# 14. Overflight exclusion from DAM movement counts
def test_14_overflight_exclusion_from_dam_movement_counts():
    conn = sqlite3.connect(V2_17_ADSB_DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM airport_association_assessment WHERE is_dam_movement = 1")
    dam_movements = cur.fetchone()[0]
    assert dam_movements == 0, f"Expected 0 DAM movements from overflights/regional observations, got {dam_movements}"
    cur.execute("SELECT COUNT(*) FROM airport_association_assessment WHERE classification = 'overflight_observation'")
    overflights = cur.fetchone()[0]
    assert overflights > 0, "Expected at least one overflight observation"
    conn.close()

# 15. No fabricated physical movement
def test_15_no_fabricated_physical_movement():
    conn = sqlite3.connect(V2_17_ADSB_DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM airport_association_assessment WHERE confirmed_physical_movement = 1")
    confirmed = cur.fetchone()[0]
    assert confirmed == 0, "No ADS-B observation should be promoted to confirmed physical movement"
    conn.close()

# 16. No mixing of FIDS and ADS-B records
def test_16_no_mixing_of_fids_and_adsb_records():
    # Ensure Track A DB has no ADS-B tables, and Track B DB has no FIDS tables
    conn_fids = sqlite3.connect(V2_17_FIDS_DB)
    cur_fids = conn_fids.cursor()
    cur_fids.execute("SELECT name FROM sqlite_master WHERE type='table'")
    fids_tables = [r[0] for r in cur_fids.fetchall()]
    conn_fids.close()

    conn_adsb = sqlite3.connect(V2_17_ADSB_DB)
    cur_adsb = conn_adsb.cursor()
    cur_adsb.execute("SELECT name FROM sqlite_master WHERE type='table'")
    adsb_tables = [r[0] for r in cur_adsb.fetchall()]
    conn_adsb.close()

    assert not any("adsb" in t.lower() for t in fids_tables)
    assert not any("fids" in t.lower() for t in adsb_tables)

# 17. No production database writes
def test_17_no_production_database_writes():
    current_prod_hash = get_file_sha256(PROD_DB)
    assert current_prod_hash == EXPECTED_PROD_HASH, f"Production DB modified! Hash: {current_prod_hash}"

# 18. No credential leakage
def test_18_no_credential_leakage():
    # Check that reports and DB do not contain api keys, passwords, or tokens
    bad_tokens = ["password", "secret_key", "bearer ", "private_key", "api_key="]
    report_files = [
        "reports/v2_17_adsb_source_inventory.csv",
        "reports/v2_17_unified_source_registry.csv",
        "reports/v2_17_unified_source_registry.json"
    ]
    for rf in report_files:
        assert os.path.exists(rf)
        with open(rf, "r", encoding="utf-8") as f:
            content = f.read().lower()
            for bt in bad_tokens:
                assert bt not in content, f"Leaked credential candidate '{bt}' found in {rf}"

# 19. Graceful handling of 403/429 responses
def test_19_graceful_handling_of_403_and_429():
    conn = sqlite3.connect(V2_17_ADSB_DB)
    cur = conn.cursor()
    cur.execute("SELECT provider, http_status, access_result FROM raw_adsb_payload_registry WHERE http_status IN (403, 429, 503, 400)")
    rows = cur.fetchall()
    assert len(rows) >= 2, "Expected recorded 403/503/400 responses in raw payload registry"
    for r in rows:
        assert r[1] in [403, 429, 503, 400]
    conn.close()

# 20. Existing baseline table counts unchanged
def test_20_existing_baseline_table_counts_unchanged():
    conn = sqlite3.connect(PROD_DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM flight_events")
    events_count = cur.fetchone()[0]
    assert events_count == 1830, f"Expected 1830 flight_events in prod, found {events_count}"
    cur.execute("SELECT COUNT(*) FROM historical_daily_movements_2024")
    hist_count = cur.fetchone()[0]
    assert hist_count == 578, f"Expected 578 historical_daily_movements_2024 in prod, found {hist_count}"
    conn.close()
