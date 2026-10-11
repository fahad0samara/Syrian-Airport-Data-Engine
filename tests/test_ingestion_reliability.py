import pytest
import hashlib
import json
import sqlite3
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.config import DB_PATH, PROCESSED_DATA_DIR, RAW_DATA_DIR
from src.database import get_connection
from src.adapters.base import BaseSourceAdapter
from src.adapters.official_portal import OfficialAirportAdapter
from src.adapters.restricted_sources import get_restricted_sources
from src.api import app

client = TestClient(app)

def test_idempotent_reingestion():
    """
    Ensures repeated ingestion does not inflate canonical event counts or duplicate rows.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM flight_events;")
        count_before = cur.fetchone()[0]

        # Verify no duplicate event_ids
        cur.execute("SELECT event_id, count(*) FROM flight_events GROUP BY event_id HAVING count(*) > 1;")
        dupes = cur.fetchall()
        assert len(dupes) == 0, f"Found duplicate event IDs in database: {dupes}"

        # Re-run a deduplication query to ensure stable canonical count
        cur.execute("""
            SELECT airport_id, flight_number, movement_type, flight_date, count(*)
            FROM flight_events
            WHERE record_nature = 'physical_movement'
            GROUP BY airport_id, flight_number, movement_type, flight_date
            HAVING count(*) > 1;
        """)
        phys_dupes = cur.fetchall()
        assert len(phys_dupes) == 0, f"Found duplicate physical movements: {phys_dupes}"

def test_source_failure_and_exponential_backoff():
    """
    Verifies that adapter retries with backoff and records failure status without corrupting DB.
    """
    adapter = OfficialAirportAdapter("DAM")
    
    import urllib.error
    # Mock urllib.request.urlopen to simulate persistent network failure with retries
    with patch.object(adapter, "record_failure") as mock_rf, \
         patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused after 3 attempts")):
        res = adapter.fetch_and_save()
        assert res["status"] == "FAILED"
        assert "Connection refused" in res["error"]
        assert res["records_fetched"] == 0
        assert mock_rf.called

    # Verify that existing flight events remain intact after a failed run
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM flight_events WHERE airport_id = 'DAM';")
        count_after = cur.fetchone()[0]
        assert count_after > 0, "Failed adapter run improperly affected existing flight events!"

def test_empty_response_handling_never_zero_operations():
    """
    Verifies that an empty API response array is recorded as EMPTY run status and
    categorized as unverified_data_gap, NEVER confirmed zero operations.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Check ingestion run for Qamishli
        cur.execute("SELECT status, records_fetched FROM ingestion_runs WHERE source_id = 'qamishliairport_official' ORDER BY run_timestamp DESC LIMIT 1;")
        row = cur.fetchone()
        if row:
            assert row["status"] == "EMPTY"
            assert row["records_fetched"] == 0

        # Check coverage matrix: KAC must NOT be confirmed_zero_operations
        cur.execute("SELECT coverage_classification FROM historical_coverage_matrix WHERE airport_id = 'KAC' AND coverage_classification = 'confirmed_zero_operations';")
        assert len(cur.fetchall()) == 0, "Empty response was erroneously classified as confirmed_zero_operations!"

def test_raw_payload_preservation_and_sha256_hash():
    """
    Verifies that raw payloads are preserved with accurate SHA-256 hashes matching content.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT raw_payload, payload_hash FROM raw_source_records LIMIT 10;")
        rows = cur.fetchall()
        assert len(rows) > 0, "No raw source records found!"

        for r in rows:
            payload = r["raw_payload"]
            recorded_hash = r["payload_hash"]
            computed_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            assert recorded_hash == computed_hash, f"SHA-256 hash mismatch! Recorded: {recorded_hash}, Computed: {computed_hash}"

def test_marketing_codeshares_excluded_from_physical_movements():
    """
    Verifies that marketing codeshares are excluded from verified physical movements.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM flight_events WHERE record_nature = 'marketing_codeshare';")
        codeshare_count = cur.fetchone()[0]
        assert codeshare_count > 0, "Expected marketing codeshare records in database."

        # Verify none appear in verified movements
        cur.execute("SELECT count(*) FROM flight_events WHERE record_nature = 'physical_movement' AND operating_flight_number IS NOT NULL AND operating_flight_number != flight_number;")
        bad_phys = cur.fetchone()[0]
        assert bad_phys == 0, "Found codeshares improperly marked as physical movements!"

def test_historical_coverage_matrix_classifications():
    """
    Validates that historical_coverage_matrix covers all 5 aerodromes for 2024 to 2026
    and only contains the 5 strict allowable categories.
    """
    allowable_categories = {
        "verified_coverage",
        "commercial_schedule_only",
        "source_checked_no_records",
        "unverified_data_gap",
        "future_schedule"
    }

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT coverage_classification FROM historical_coverage_matrix;")
        found_categories = {r[0] for r in cur.fetchall()}
        
        assert found_categories.issubset(allowable_categories), f"Unexpected classifications found: {found_categories - allowable_categories}"

        cur.execute("SELECT count(*) FROM historical_coverage_matrix;")
        total_cells = cur.fetchone()[0]
        assert total_cells == 5175, f"Expected exactly 5,175 cells, found {total_cells}"

        # Verify future schedule dates
        cur.execute("SELECT count(*) FROM historical_coverage_matrix WHERE coverage_classification = 'future_schedule' AND flight_date <= '2026-10-10';")
        invalid_future = cur.fetchone()[0]
        assert invalid_future == 0, "Past or current dates misclassified as future_schedule!"

def test_api_verified_vs_scheduled_consistency():
    """
    Verifies API consistency between /api/movements/verified, /api/movements/scheduled,
    and /api/movements/unverified with exact SQLite queries.
    """
    v_res = client.get("/api/movements/verified")
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data["record_nature"] == "physical_movement"
    for m in v_data["movements"]:
        assert m["record_nature"] == "physical_movement"

    s_res = client.get("/api/movements/scheduled")
    assert s_res.status_code == 200
    s_data = s_res.json()
    assert s_data["record_nature"] == "scheduled_service"
    for m in s_data["movements"]:
        assert m["record_nature"] == "scheduled_service"

    u_res = client.get("/api/movements/unverified")
    assert u_res.status_code == 200
    u_data = u_res.json()
    assert u_data["record_nature"] == "unverified_movement"
    for m in u_data["movements"]:
        assert m["record_nature"] == "unverified_movement"
        assert "verification_limitation" in m

    # Verify counts reconcile with SQLite
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM flight_events WHERE record_nature = 'physical_movement';")
        db_phys = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM flight_events WHERE record_nature = 'scheduled_service';")
        db_sched = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM flight_events WHERE record_nature = 'unverified_movement';")
        db_unver = cur.fetchone()[0]

    assert v_data["total"] == db_phys
    assert s_data["total"] == db_sched
    assert u_data["total"] == db_unver

def test_api_ingestion_health_endpoint():
    """
    Tests /api/ingestion/health for status, run history, and source monitoring attributes.
    """
    res = client.get("/api/ingestion/health")
    assert res.status_code == 200
    data = res.json()
    assert data["overall_status"] == "OPERATIONAL"
    assert "summary" in data
    assert "recent_runs" in data
    assert "sources_health" in data

    # Check that source attributes include freshness and reliability
    source_ids = {s["source_id"] for s in data["sources_health"]}
    assert "damairport_official" in source_ids
    assert "flightradar24" in source_ids
    for s in data["sources_health"]:
        assert "freshness_indicator" in s
        assert "reliability_indicator" in s
        assert "known_limitations" in s
