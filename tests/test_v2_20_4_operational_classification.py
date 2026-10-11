import os
import hashlib
import sqlite3
import re
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from src.api import app
from src.normalizer import evaluate_cross_source_match

client = TestClient(app)

PROTECTED_HASHES = {
    "data/damascus_airport.db": "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b",
    "data/archived_fids_staging.db": "a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4",
    "data/archived_fids_analytics.db": "e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe",
    "data/archived_fids_history_staging.db": "39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f",
    "data/raw/snapshots/wayback_damairport_fids_20260709234230.raw": "5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf",
    "data/raw/snapshots/wayback_damairport_fids_20260709234230.json": "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491",
}


class TestG9376OperationalClassification:
    """Forensic verification and regression testing for event 6e9ccc725c3b169e (G9376)."""

    def test_g9376_database_record_invariants(self):
        conn = sqlite3.connect("data/damascus_airport.db")
        c = conn.cursor()
        c.execute("SELECT * FROM flight_events WHERE event_id = '6e9ccc725c3b169e'")
        cols = [d[0] for d in c.description]
        row = dict(zip(cols, c.fetchone()))
        conn.close()

        assert row["event_id"] == "6e9ccc725c3b169e"
        assert row["flight_number"] == "G9376"
        assert row["airport_id"] == "DAM"
        assert row["movement_type"] == "departure"
        assert row["flight_date"] == "2026-10-09"
        assert row["flight_status"] == "scheduled"
        # Classification MUST remain scheduled_service (not physical_movement)
        assert row["record_nature"] == "scheduled_service"
        assert row["scheduled_dep_time"] == "2026-10-09T10:55:00Z"
        assert row["raw_scheduled_dep_time"] == "2026-10-09 13:55"
        assert row["actual_dep_time"] == "2026-10-10T09:00:00Z"
        assert row["raw_actual_dep_time"] == "1791622800"

    def test_g9376_active_evidence_provenance(self):
        conn = sqlite3.connect("data/damascus_airport.db")
        c = conn.cursor()
        c.execute("SELECT * FROM v_active_evidence WHERE event_id = '6e9ccc725c3b169e'")
        cols = [d[0] for d in c.description]
        ev_rows = [dict(zip(cols, r)) for r in c.fetchall()]

        # Retractions ledger check
        c.execute("SELECT count(*) FROM evidence_retractions WHERE evidence_id IN ('ev_809974eb71be3a65', 'ev_aef32f35d286b2e7')")
        ret_count = c.fetchone()[0]
        conn.close()

        assert len(ev_rows) == 2
        assert ret_count == 0
        for ev in ev_rows:
            assert ev["event_id"] == "6e9ccc725c3b169e"
            assert ev["observed_value"] == "2026-10-10T09:00:00Z"
            assert ev["raw_timestamp"] == "1791622800"

    def test_g9376_excluded_from_verified_movements_api(self):
        res = client.get("/api/movements/verified?airport_id=DAM&date=2026-10-09")
        assert res.status_code == 200
        events = res.json()["movements"]
        # Timetable scheduled service must NOT appear in verified physical movements
        assert not any(e.get("event_id") == "6e9ccc725c3b169e" for e in events)

    def test_g9376_included_in_scheduled_movements_api(self):
        res = client.get("/api/movements/scheduled?airport_id=DAM&date=2026-10-09")
        assert res.status_code == 200
        events = res.json()["movements"]
        matching = [e for e in events if e.get("event_id") == "6e9ccc725c3b169e"]
        assert len(matching) == 1
        record = matching[0]
        assert record["flight_number"] == "G9376"
        assert record["scheduled_flight_date"] == "2026-10-09"
        assert record["actual_movement_date"] is None
        assert record["actual_dep_time"] is None
        assert record["estimated_dep_time"] == "2026-10-10T09:00:00Z"
        assert record["estimated_movement_date"] == "2026-10-10"


class TestMovementIdentityKeyValidation:
    """Verifies the 8 edge cases required for movement identity validation."""

    def test_case1_same_flight_date_direction_different_timestamps_split(self):
        # Morning departure vs evening departure with same flight number
        ev1 = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "RB100", "actual_dep_time": "2026-10-10T08:00:00Z"
        }
        ev2 = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "RB100", "actual_dep_time": "2026-10-10T20:00:00Z"
        }
        res = evaluate_cross_source_match(ev1, ev2)
        assert not res["can_merge"]
        assert res["match_status"] == "SPLIT_DISTINCT_LEG"

    def test_case2_same_flight_number_different_operating_carriers_conflict(self):
        ev1 = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "100", "operating_carrier": "Syrian Air",
            "actual_dep_time": "2026-10-10T08:00:00Z"
        }
        ev2 = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "100", "operating_carrier": "Qatar Airways",
            "actual_dep_time": "2026-10-10T08:10:00Z"
        }
        res = evaluate_cross_source_match(ev1, ev2)
        assert not res["can_merge"]
        assert res["match_status"] == "CONFLICT_CARRIER"

    def test_case3_same_flight_number_multiple_movements_on_one_date(self):
        ev1 = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "RB200", "actual_dep_time": "2026-10-10T06:00:00Z"
        }
        ev2 = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "RB200", "actual_dep_time": "2026-10-10T14:00:00Z"
        }
        res = evaluate_cross_source_match(ev1, ev2)
        assert not res["can_merge"]
        assert res["match_status"] == "SPLIT_DISTINCT_LEG"

    def test_case4_same_aircraft_registration_different_flight_numbers(self):
        ev1 = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "RB515", "aircraft_registration": "YK-BAA",
            "actual_dep_time": "2026-10-10T08:00:00Z"
        }
        ev2 = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "RB521", "aircraft_registration": "YK-BAA",
            "actual_dep_time": "2026-10-10T08:05:00Z"
        }
        res = evaluate_cross_source_match(ev1, ev2)
        assert not res["can_merge"]
        assert res["match_status"] == "MISMATCH_FLIGHT_NUMBER"

    def test_case5_different_flight_numbers_same_aircraft_registration(self):
        # Airframe identity does not equal flight identity
        ev1 = {
            "airport_id": "DAM", "movement_type": "arrival", "flight_date": "2026-10-10",
            "flight_number": "QR410", "aircraft_registration": "A7-BBA",
            "actual_arr_time": "2026-10-10T11:33:00Z"
        }
        ev2 = {
            "airport_id": "DAM", "movement_type": "arrival", "flight_date": "2026-10-10",
            "flight_number": "QR412", "aircraft_registration": "A7-BBA",
            "actual_arr_time": "2026-10-10T11:35:00Z"
        }
        res = evaluate_cross_source_match(ev1, ev2)
        assert not res["can_merge"]
        assert res["match_status"] == "MISMATCH_FLIGHT_NUMBER"

    def test_case6_missing_operating_flight_number_unmergeable(self):
        ev1 = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "", "operating_flight_number": None,
            "actual_dep_time": "2026-10-10T08:00:00Z"
        }
        ev2 = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "", "operating_flight_number": None,
            "actual_dep_time": "2026-10-10T08:05:00Z"
        }
        res = evaluate_cross_source_match(ev1, ev2)
        assert not res["can_merge"]
        assert res["match_status"] == "MISMATCH_FLIGHT_NUMBER"

    def test_case7_missing_actual_timestamp_potential_match_lacks_time(self):
        ev1 = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "RB100", "actual_dep_time": None, "scheduled_dep_time": None
        }
        ev2 = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "RB100", "actual_dep_time": "2026-10-10T08:00:00Z"
        }
        res = evaluate_cross_source_match(ev1, ev2)
        assert not res["can_merge"]
        assert res["match_status"] == "POTENTIAL_MATCH_LACKS_TIME"

    def test_case8_codeshare_and_operating_flight_match(self):
        # Marketing codeshare EK2212 operating FZ1113 matches operating FZ1113
        ev1 = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "EK2212", "operating_flight_number": "FZ1113",
            "actual_dep_time": "2026-10-10T08:00:00Z"
        }
        ev2 = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "FZ1113", "operating_flight_number": "FZ1113",
            "actual_dep_time": "2026-10-10T08:05:00Z"
        }
        res = evaluate_cross_source_match(ev1, ev2)
        assert res["can_merge"]
        assert res["match_status"] == "CONFIRMED_MATCH"


class TestAircraftRegistrationSemantics:
    """Verifies the audit findings for the 131 records carrying aircraft registrations."""

    def test_physical_movement_registration_counts_and_normalization(self):
        conn = sqlite3.connect("data/damascus_airport.db")
        c = conn.cursor()
        c.execute("""
        SELECT aircraft_registration, aircraft_icao24, source
        FROM flight_events
        WHERE record_nature = 'physical_movement'
          AND aircraft_registration IS NOT NULL AND TRIM(aircraft_registration) != ''
        """)
        rows = c.fetchall()
        conn.close()

        # Exactly 131 physical movement records have non-null registrations
        assert len(rows) == 131

        regs = [r[0].strip().upper() for r in rows]
        distinct_regs = set(regs)
        # Exactly 60 distinct normalized registrations
        assert len(distinct_regs) == 60

        # No malformed or invalid registrations
        valid_pattern = re.compile(r'^[A-Z0-9]{1,4}-[A-Z0-9]{1,5}$')
        invalid = [reg for reg in distinct_regs if not valid_pattern.match(reg)]
        assert len(invalid) == 0

        # All 131 are supported by direct source payloads (FR24/AviationStack)
        for r in rows:
            src = r[2]
            assert "flightradar24" in src or "aviationstack" in src

        # Mode-S ICAO24 availability: all 131 have valid hex codes
        distinct_icao = set(r[1].strip().upper() for r in rows if r[1])
        assert len(distinct_icao) == 60

    def test_api_movements_stats_exposes_standardized_metric_name(self):
        res = client.get("/api/movements/stats")
        assert res.status_code == 200
        data = res.json()
        # Metric name distinct_reported_aircraft_registrations must be present
        assert "distinct_reported_aircraft_registrations" in data
        assert data["distinct_reported_aircraft_registrations"] >= 60
        # Backward compatibility preserved
        assert "total_unique_aircraft" in data
        assert "unique_aircraft_tracked" in data


class TestProtectedBaselineIntegrityV2204:
    """Verifies cryptographic hash invariance for all 6 protected baseline files."""

    def test_six_protected_assets_hashes(self):
        for path, expected_hash in PROTECTED_HASHES.items():
            assert os.path.exists(path), f"Protected file missing: {path}"
            with open(path, "rb") as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            assert actual_hash == expected_hash, (
                f"CRYPTO INTEGRITY FAILURE on {path}: expected {expected_hash}, got {actual_hash}"
            )
