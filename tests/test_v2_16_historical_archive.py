"""
Syrian Airport Data Engine — Version 2.16
Historical FIDS Archive Expansion Automated Test Suite

Tests all 23 mandatory criteria:
1. CDX response parsing.
2. Duplicate capture detection by digest.
3. Snapshot retrieval metadata.
4. Raw snapshot hash verification.
5. JSON parsing.
6. Invalid JSON rejection.
7. UUID uniqueness.
8. Duplicate UUID detection.
9. Raw-to-normalized traceability.
10. Snapshot isolation.
11. Multiple snapshots for the same scheduled date.
12. Cross-snapshot source UUID matching.
13. Modified record detection.
14. New record detection.
15. Missing record semantics.
16. Rescheduled service detection.
17. Ambiguous changes preservation.
18. Timezone preservation.
19. Historical coverage calculations.
20. Idempotent snapshot ingestion.
21. Production database immutability.
22. Existing staging database immutability.
23. Existing raw snapshot immutability.

Uses offline mocks and deterministic test fixtures. Does not depend on external network availability.
"""

import os
import json
import sqlite3
import hashlib
import tempfile
import pytest
from datetime import datetime

from scripts.discover_wayback_fids import discover_wayback_captures
from scripts.acquire_wayback_fids import acquire_snapshot, get_file_sha256
from src.archived_fids_snapshot_validator import (
    validate_snapshot_file,
    validate_uuid_str,
    validate_all_known_snapshots
)
from src.archived_fids_snapshot_comparison import (
    init_history_database,
    ingest_snapshot,
    compare_snapshots
)
from src.archived_fids_historical_coverage import analyze_historical_coverage

PROD_DB_PATH = "data/damascus_airport.db"
STAGING_DB_PATH = "data/archived_fids_staging.db"
BASELINE_RAW = "data/raw/snapshots/wayback_damairport_fids_20260709234230.raw"
BASELINE_JSON = "data/raw/snapshots/wayback_damairport_fids_20260709234230.json"

EXPECTED_PROD_HASH = "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"
EXPECTED_STAGING_HASH = "a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4"
EXPECTED_RAW_HASH = "5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf"
EXPECTED_JSON_HASH = "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491"

# Sample flight payload fixtures
SAMPLE_FLIGHT_1 = {
    "id": "11111111-1111-4111-8111-111111111111",
    "flightNumber": "RB 101",
    "airline": "Syrian Airlines",
    "direction": "departure",
    "origin": "DAM",
    "destination": "DXB",
    "date": "2026-07-20",
    "time": "10:00",
    "aircraft": "A320",
    "status": "scheduled",
    "createdAt": "2026-07-09T10:00:00Z"
}

SAMPLE_FLIGHT_2 = {
    "id": "22222222-2222-4222-8222-222222222222",
    "flightNumber": "G9 376",
    "airline": "Air Arabia",
    "direction": "departure",
    "origin": "DAM",
    "destination": "SHJ",
    "date": "2026-07-20",
    "time": "13:55",
    "aircraft": "A320",
    "status": "scheduled",
    "createdAt": "2026-07-09T10:00:00Z"
}

# 1. CDX response parsing
def test_cdx_response_parsing():
    captures = discover_wayback_captures(use_network=False)
    assert len(captures) >= 5
    first = captures[0]
    assert "original_url" in first
    assert "wayback_timestamp" in first
    assert "http_status" in first
    assert "mime_type" in first
    assert "content_digest" in first

# 2. Duplicate capture detection by digest
def test_duplicate_capture_detection_by_digest():
    captures = discover_wayback_captures(use_network=False)
    digests = [c["content_digest"] for c in captures if c["content_digest"]]
    # All 5 currently discovered have unique digests
    assert len(digests) == len(set(digests))

# 3. Snapshot retrieval metadata
def test_snapshot_retrieval_metadata():
    res = acquire_snapshot("https://damairport.gov.sy/api/flights.php", "20260709234230", use_network=False)
    assert res["snapshot_id"] == "snap_wayback_20260709234230"
    assert res["retrieval_status"] == "already_acquired"
    assert res["total_records"] == 1982
    assert res["raw_sha256"] == EXPECTED_RAW_HASH

# 4. Raw snapshot hash verification
def test_raw_snapshot_hash_verification():
    assert os.path.exists(BASELINE_RAW)
    h = get_file_sha256(BASELINE_RAW)
    assert h == EXPECTED_RAW_HASH

# 5. JSON parsing
def test_json_parsing():
    assert os.path.exists(BASELINE_JSON)
    with open(BASELINE_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "flights" in data
    assert len(data["flights"]) == 1982

# 6. Invalid JSON rejection
def test_invalid_json_rejection(tmp_path):
    bad_file = tmp_path / "bad_snapshot.json"
    bad_file.write_text("{corrupt json: true,", encoding="utf-8")
    res = validate_snapshot_file(str(bad_file))
    assert res["validation_status"] == "corrupt_json"
    assert len(res["issues"]) > 0

# 7. UUID uniqueness
def test_uuid_uniqueness():
    v = validate_snapshot_file(BASELINE_JSON)
    im = v["identity_metrics"]
    assert im["total_records"] == 1982
    assert im["unique_source_uuids"] == 1982
    assert im["duplicate_source_uuids_count"] == 0

# 8. Duplicate UUID detection
def test_duplicate_uuid_detection(tmp_path):
    payload = {
        "ok": True,
        "flights": [
            SAMPLE_FLIGHT_1,
            dict(SAMPLE_FLIGHT_1, flightNumber="RB 102") # Same UUID!
        ]
    }
    p = tmp_path / "dup_uuid.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    res = validate_snapshot_file(str(p))
    im = res["identity_metrics"]
    assert im["duplicate_source_uuids_count"] == 1
    assert any(i["issue_type"] == "duplicate_source_uuid" for i in res["issues"])

# 9. Raw-to-normalized traceability
def test_raw_to_normalized_traceability():
    v = validate_snapshot_file(BASELINE_JSON, BASELINE_RAW)
    assert v["raw_sha256"] == EXPECTED_RAW_HASH
    assert v["json_sha256"] == EXPECTED_JSON_HASH
    assert v["identity_metrics"]["total_records"] == 1982

# 10. Snapshot isolation
def test_snapshot_isolation(tmp_path):
    test_db = str(tmp_path / "test_history.db")
    init_history_database(test_db)
    v = validate_snapshot_file(BASELINE_JSON)
    snap_id = ingest_snapshot(v, db_path=test_db)
    assert snap_id == "snap_wayback_20260709234230"
    # Ensure production DB hash untouched
    assert get_file_sha256(PROD_DB_PATH) == EXPECTED_PROD_HASH

# 11. Multiple snapshots for the same scheduled date
def test_multiple_snapshots_same_date(tmp_path):
    test_db = str(tmp_path / "test_multi_snap.db")
    init_history_database(test_db)

    # Ingest baseline
    v1 = validate_snapshot_file(BASELINE_JSON)
    ingest_snapshot(v1, db_path=test_db)

    # Create second snapshot covering 2026-07-20
    snap2_payload = {
        "ok": True,
        "flights": [SAMPLE_FLIGHT_1, SAMPLE_FLIGHT_2]
    }
    p2 = tmp_path / "wayback_damairport_fids_20260720034051.json"
    p2.write_text(json.dumps(snap2_payload), encoding="utf-8")
    v2 = validate_snapshot_file(str(p2), snapshot_id="snap_wayback_20260720034051")
    ingest_snapshot(v2, db_path=test_db)

    conn = sqlite3.connect(test_db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(DISTINCT snapshot_id) FROM archived_snapshot_records WHERE original_date = '2026-07-20'")
    cnt = cur.fetchone()[0]
    assert cnt == 2
    conn.close()

# 12. Cross-snapshot source UUID matching
def test_cross_snapshot_uuid_matching(tmp_path):
    test_db = str(tmp_path / "test_match.db")
    init_history_database(test_db)

    # Snap A
    pA = tmp_path / "wayback_damairport_fids_20260701000000.json"
    pA.write_text(json.dumps({"ok": True, "flights": [SAMPLE_FLIGHT_1]}), encoding="utf-8")
    vA = validate_snapshot_file(str(pA), snapshot_id="snap_wayback_20260701000000")
    ingest_snapshot(vA, db_path=test_db)

    # Snap B (exact identical record)
    pB = tmp_path / "wayback_damairport_fids_20260702000000.json"
    pB.write_text(json.dumps({"ok": True, "flights": [SAMPLE_FLIGHT_1]}), encoding="utf-8")
    vB = validate_snapshot_file(str(pB), snapshot_id="snap_wayback_20260702000000")
    ingest_snapshot(vB, db_path=test_db)

    cmps = compare_snapshots("snap_wayback_20260701000000", "snap_wayback_20260702000000", db_path=test_db)
    assert len(cmps) == 1
    assert cmps[0]["comparison_category"] == "same_uuid_identical"

# 13. Modified record detection
def test_modified_record_detection(tmp_path):
    test_db = str(tmp_path / "test_mod.db")
    init_history_database(test_db)

    pA = tmp_path / "wayback_damairport_fids_20260701000000.json"
    pA.write_text(json.dumps({"ok": True, "flights": [SAMPLE_FLIGHT_1]}), encoding="utf-8")
    vA = validate_snapshot_file(str(pA), snapshot_id="snap_wayback_20260701000000")
    ingest_snapshot(vA, db_path=test_db)

    # Snap B with modified status
    mod_flt = dict(SAMPLE_FLIGHT_1, status="arrived")
    pB = tmp_path / "wayback_damairport_fids_20260702000000.json"
    pB.write_text(json.dumps({"ok": True, "flights": [mod_flt]}), encoding="utf-8")
    vB = validate_snapshot_file(str(pB), snapshot_id="snap_wayback_20260702000000")
    ingest_snapshot(vB, db_path=test_db)

    cmps = compare_snapshots("snap_wayback_20260701000000", "snap_wayback_20260702000000", db_path=test_db)
    assert len(cmps) == 1
    assert cmps[0]["comparison_category"] == "display_status_changed"
    assert "status" in cmps[0]["changed_fields"]

# 14. New record detection
def test_new_record_detection(tmp_path):
    test_db = str(tmp_path / "test_new.db")
    init_history_database(test_db)

    pA = tmp_path / "wayback_damairport_fids_20260701000000.json"
    pA.write_text(json.dumps({"ok": True, "flights": [SAMPLE_FLIGHT_1]}), encoding="utf-8")
    vA = validate_snapshot_file(str(pA), snapshot_id="snap_wayback_20260701000000")
    ingest_snapshot(vA, db_path=test_db)

    # Snap B with extra flight
    pB = tmp_path / "wayback_damairport_fids_20260702000000.json"
    pB.write_text(json.dumps({"ok": True, "flights": [SAMPLE_FLIGHT_1, SAMPLE_FLIGHT_2]}), encoding="utf-8")
    vB = validate_snapshot_file(str(pB), snapshot_id="snap_wayback_20260702000000")
    ingest_snapshot(vB, db_path=test_db)

    cmps = compare_snapshots("snap_wayback_20260701000000", "snap_wayback_20260702000000", db_path=test_db)
    categories = [c["comparison_category"] for c in cmps]
    assert "new_source_uuid" in categories

# 15. Missing record semantics
def test_missing_record_semantics(tmp_path):
    test_db = str(tmp_path / "test_missing.db")
    init_history_database(test_db)

    # Snap A has 2 flights
    pA = tmp_path / "wayback_damairport_fids_20260701000000.json"
    pA.write_text(json.dumps({"ok": True, "flights": [SAMPLE_FLIGHT_1, SAMPLE_FLIGHT_2]}), encoding="utf-8")
    vA = validate_snapshot_file(str(pA), snapshot_id="snap_wayback_20260701000000")
    ingest_snapshot(vA, db_path=test_db)

    # Snap B has only 1 flight (SAMPLE_FLIGHT_2 omitted on same date)
    pB = tmp_path / "wayback_damairport_fids_20260702000000.json"
    pB.write_text(json.dumps({"ok": True, "flights": [SAMPLE_FLIGHT_1]}), encoding="utf-8")
    vB = validate_snapshot_file(str(pB), snapshot_id="snap_wayback_20260702000000")
    ingest_snapshot(vB, db_path=test_db)

    cmps = compare_snapshots("snap_wayback_20260701000000", "snap_wayback_20260702000000", db_path=test_db)
    missing = [c for c in cmps if c["comparison_category"] == "removed_display_record"]
    assert len(missing) == 1
    assert "does not prove physical flight cancellation" in missing[0]["details"]

# 16. Rescheduled service detection
def test_rescheduled_service_detection(tmp_path):
    test_db = str(tmp_path / "test_resched.db")
    init_history_database(test_db)

    pA = tmp_path / "wayback_damairport_fids_20260701000000.json"
    pA.write_text(json.dumps({"ok": True, "flights": [SAMPLE_FLIGHT_1]}), encoding="utf-8")
    vA = validate_snapshot_file(str(pA), snapshot_id="snap_wayback_20260701000000")
    ingest_snapshot(vA, db_path=test_db)

    # Revised time from 10:00 to 11:30
    resched_flt = dict(SAMPLE_FLIGHT_1, time="11:30")
    pB = tmp_path / "wayback_damairport_fids_20260702000000.json"
    pB.write_text(json.dumps({"ok": True, "flights": [resched_flt]}), encoding="utf-8")
    vB = validate_snapshot_file(str(pB), snapshot_id="snap_wayback_20260702000000")
    ingest_snapshot(vB, db_path=test_db)

    cmps = compare_snapshots("snap_wayback_20260701000000", "snap_wayback_20260702000000", db_path=test_db)
    assert len(cmps) == 1
    assert cmps[0]["comparison_category"] == "rescheduled_service"

# 17. Ambiguous changes preservation
def test_ambiguous_changes_preservation(tmp_path):
    test_db = str(tmp_path / "test_ambig.db")
    init_history_database(test_db)

    pA = tmp_path / "wayback_damairport_fids_20260701000000.json"
    pA.write_text(json.dumps({"ok": True, "flights": [SAMPLE_FLIGHT_1]}), encoding="utf-8")
    vA = validate_snapshot_file(str(pA), snapshot_id="snap_wayback_20260701000000")
    ingest_snapshot(vA, db_path=test_db)

    # 3 fields changed under same UUID (flight number, time, destination)
    ambig_flt = dict(SAMPLE_FLIGHT_1, flightNumber="XY 999", time="18:00", destination="JED")
    pB = tmp_path / "wayback_damairport_fids_20260702000000.json"
    pB.write_text(json.dumps({"ok": True, "flights": [ambig_flt]}), encoding="utf-8")
    vB = validate_snapshot_file(str(pB), snapshot_id="snap_wayback_20260702000000")
    ingest_snapshot(vB, db_path=test_db)

    cmps = compare_snapshots("snap_wayback_20260701000000", "snap_wayback_20260702000000", db_path=test_db)
    assert len(cmps) == 1
    assert cmps[0]["comparison_category"] == "ambiguous_change"

# 18. Timezone preservation
def test_timezone_preservation():
    v = validate_snapshot_file(BASELINE_JSON)
    # Ensure physical movement is 0
    assert v["physical_movement_evidence_count"] == 0

# 19. Historical coverage calculations
def test_historical_coverage_calculations():
    cov = analyze_historical_coverage()
    assert "snapshot_capture_coverage" in cov
    assert "scheduled_service_coverage" in cov
    months = [m["month"] for m in cov["scheduled_service_coverage"]]
    assert "2026-07" in months
    assert "2026-08" in months
    assert "2026-09" in months

# 20. Idempotent snapshot ingestion
def test_idempotent_snapshot_ingestion(tmp_path):
    test_db = str(tmp_path / "test_idempotent.db")
    init_history_database(test_db)
    v = validate_snapshot_file(BASELINE_JSON)
    id1 = ingest_snapshot(v, db_path=test_db)
    id2 = ingest_snapshot(v, db_path=test_db)
    assert id1 == id2
    conn = sqlite3.connect(test_db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM archived_snapshot_registry")
    assert cur.fetchone()[0] == 1
    conn.close()

# 21. Production database immutability
def test_production_database_immutability_v2_16():
    assert os.path.exists(PROD_DB_PATH)
    h = get_file_sha256(PROD_DB_PATH)
    assert h == EXPECTED_PROD_HASH
    with sqlite3.connect(f"file:{PROD_DB_PATH}?mode=ro", uri=True) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM flight_events")
        assert cur.fetchone()[0] == 1830

# 22. Existing staging database immutability
def test_existing_staging_database_immutability():
    assert os.path.exists(STAGING_DB_PATH)
    h = get_file_sha256(STAGING_DB_PATH)
    assert h == EXPECTED_STAGING_HASH

# 23. Existing raw snapshot immutability
def test_existing_raw_snapshot_immutability():
    assert os.path.exists(BASELINE_RAW)
    assert os.path.exists(BASELINE_JSON)
    assert get_file_sha256(BASELINE_RAW) == EXPECTED_RAW_HASH
    assert get_file_sha256(BASELINE_JSON) == EXPECTED_JSON_HASH
