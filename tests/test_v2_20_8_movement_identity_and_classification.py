"""
Tests for Version 2.20.8 — Movement Identity & Classification Integrity
Syrian Airport Data Engine

Verifies:
1. Separation of the three distinct concepts:
   - unique_operating_flight_count (operating service callsigns)
   - resolved_commercial_movement_count (resolved operational movement legs)
   - ambiguous_movement_identity_count (unresolved candidate movements)
2. Two separate movements with the same flight number (e.g. split distinct legs).
3. One movement represented by multiple provider observations (merged into 1 canonical leg).
4. Codeshare and operating flight representing one movement (codeshare does not inflate counts).
5. Two aircraft operating the same callsign (conflict registration prevents merging).
6. Conflicting carrier prevents merging without verified codeshare.
7. Missing actual timestamps remain null and excluded from resolved movement counts.
8. Ambiguous identity remaining excluded from resolved counts.
9. Classification consistency: event_classification exposes commercially_reported_operational_event
   while preserving physical_movement in database layer.
10. Invariance of all six protected baseline SHA-256 hashes.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import sqlite3
import hashlib
import pytest
from fastapi.testclient import TestClient

from src.api import app
from src.normalizer import evaluate_cross_source_match
from src.timestamp_provenance import correct_flight_record_semantics

client = TestClient(app)

PROTECTED_BASELINE_HASHES = {
    "data/damascus_airport.db": "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b",
    "data/archived_fids_staging.db": "a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4",
    "data/archived_fids_analytics.db": "e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe",
    "data/archived_fids_history_staging.db": "39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f",
    "data/raw/snapshots/wayback_damairport_fids_20260709234230.raw": "5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf",
    "data/raw/snapshots/wayback_damairport_fids_20260709234230.json": "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491",
}


def get_file_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class TestCryptographicBaselineIntegrityV2208:
    """Verifies all 6 protected baseline database and raw snapshot files remain strictly untouched."""

    @pytest.mark.parametrize("filepath,expected_hash", list(PROTECTED_BASELINE_HASHES.items()))
    def test_protected_asset_sha256_hash(self, filepath, expected_hash):
        assert Path(filepath).exists(), f"Protected file {filepath} not found!"
        actual_hash = get_file_sha256(filepath)
        assert actual_hash == expected_hash, (
            f"Cryptographic hash invariant violation on {filepath}!\n"
            f"Expected: {expected_hash}\n"
            f"Actual:   {actual_hash}"
        )


class TestMovementIdentityAndMultiFactorMatchingV2208:
    """Validates movement identity rules, cross-source matching, and conflict handling."""

    def test_two_separate_movements_with_same_flight_number(self):
        """Verifies that two operations sharing the same callsign >180m apart split into distinct legs."""
        leg1 = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "RB100", "airline_name": "Syrian Air",
            "actual_dep_time": "2026-10-10T06:00:00Z"
        }
        leg2 = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "RB100", "airline_name": "Syrian Air",
            "actual_dep_time": "2026-10-10T18:00:00Z"
        }
        result = evaluate_cross_source_match(leg1, leg2)
        assert result["can_merge"] is False
        assert result["match_status"] == "SPLIT_DISTINCT_LEG"
        assert result["time_diff_minutes"] == 720.0

    def test_one_movement_represented_by_multiple_provider_observations(self):
        """Verifies multiple provider observations within tolerance merge into a single canonical event."""
        obs_fr24 = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "FZ1114", "airline_name": "flydubai",
            "actual_dep_time": "2026-10-10T13:54:16Z", "aircraft_registration": "A6-FEC"
        }
        obs_avstack = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "FZ1114", "airline_name": "flydubai",
            "actual_dep_time": "2026-10-10T13:54:00Z", "aircraft_registration": "A6-FEC"
        }
        result = evaluate_cross_source_match(obs_fr24, obs_avstack)
        assert result["can_merge"] is True
        assert result["match_status"] == "CONFIRMED_MATCH"
        assert result["confidence_score"] == 1.0

    def test_codeshare_and_operating_flight_representing_one_movement(self):
        """Verifies codeshare matches operating flight and is identified as marketing partner listing."""
        operating_flight = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "RJ438", "operating_flight_number": "RJ438", "airline_name": "Royal Jordanian",
            "actual_dep_time": "2026-10-10T09:00:00Z"
        }
        codeshare_flight = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "QR6118", "operating_flight_number": "RJ438", "airline_name": "Qatar Airways",
            "actual_dep_time": "2026-10-10T09:00:00Z"
        }
        result = evaluate_cross_source_match(operating_flight, codeshare_flight)
        assert result["can_merge"] is True
        assert result["match_status"] == "CONFIRMED_MATCH"

    def test_two_aircraft_operating_same_callsign_prevents_merge(self):
        """Verifies conflicting aircraft registrations prevent merging even with identical flight number."""
        event_a = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "RB441", "airline_name": "Syrian Air",
            "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T14:24:38Z"
        }
        event_b = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "RB441", "airline_name": "Syrian Air",
            "aircraft_registration": "YK-AKH", "actual_dep_time": "2026-10-10T14:24:38Z"
        }
        result = evaluate_cross_source_match(event_a, event_b)
        assert result["can_merge"] is False
        assert result["match_status"] == "CONFLICT_REGISTRATION"
        assert "Conflicting aircraft registrations" in result["conflict_reason"]

    def test_conflicting_carrier_prevents_merge(self):
        """Verifies conflicting operating carriers prevent merging without codeshare link."""
        event_a = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "RB441", "airline_name": "Syrian Air",
            "actual_dep_time": "2026-10-10T14:24:38Z"
        }
        event_b = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "RB441", "airline_name": "Pegasus Airlines",
            "actual_dep_time": "2026-10-10T14:24:38Z"
        }
        result = evaluate_cross_source_match(event_a, event_b)
        assert result["can_merge"] is False
        assert result["match_status"] == "CONFLICT_CARRIER"
        assert "Conflicting operating carriers" in result["conflict_reason"]

    def test_missing_actual_timestamps_cannot_merge_or_qualify_as_operational(self):
        """Verifies that missing timestamps cannot form confirmed cross-source operational merges."""
        event_a = {
            "airport_id": "DAM", "movement_type": "arrival", "flight_date": "2026-10-10",
            "flight_number": "3L456", "airline_name": "Air Arabia",
            "scheduled_arr_time": None, "actual_arr_time": None
        }
        event_b = {
            "airport_id": "DAM", "movement_type": "arrival", "flight_date": "2026-10-10",
            "flight_number": "3L456", "airline_name": "Air Arabia",
            "scheduled_arr_time": None, "actual_arr_time": None
        }
        result = evaluate_cross_source_match(event_a, event_b)
        assert result["can_merge"] is False
        assert result["match_status"] == "POTENTIAL_MATCH_LACKS_TIME"


class TestMetricSeparationAndCountingSemanticsV2208:
    """Verifies distinct definitions and counting behavior for the three core concepts."""

    def test_comparison_endpoint_separates_flight_services_from_movements(self):
        """Verifies that /api/movements/comparison distinguishes unique operating services from resolved movement legs."""
        res = client.get("/api/movements/comparison?airport_id=DAM")
        assert res.status_code == 200
        data = res.json()

        fdefs = data["field_definitions"]
        assert "unique_operating_flight_count" in fdefs
        assert "resolved_commercial_movement_count" in fdefs
        assert "ambiguous_movement_identity_count" in fdefs

        # Verify definitions document counting units
        assert "service callsigns" in fdefs["unique_operating_flight_count"]
        assert "resolved operational flight legs" in fdefs["resolved_commercial_movement_count"]
        assert "candidate movements" in fdefs["ambiguous_movement_identity_count"]

        # Check deduplication rules explain repeated flight numbers
        dd_rules = " ".join(data["deduplication_rules"])
        assert "Operating Flight Services" in dd_rules
        assert "Repeated Flight Numbers" in dd_rules

    def test_ambiguous_identity_remaining_excluded_from_resolved_counts(self):
        """Verifies ambiguous codeshares remain strictly excluded from resolved commercial movement counts."""
        res = client.get("/api/movements/comparison?airport_id=DAM")
        assert res.status_code == 200
        data = res.json()

        peak_day = next((r for r in data["comparison"] if r["flight_date"] == "2026-10-10"), None)
        assert peak_day is not None
        assert peak_day["ambiguous_movement_identity_count"] == 1
        assert peak_day["matched_codeshare_record_count"] == 14
        assert peak_day["resolved_commercial_movement_count"] == 47

        # Total records = scheduled (37) + commercial operational (47) + codeshares (15) = 99
        assert peak_day["total_records"] == 99
        assert peak_day["resolved_commercial_movement_count"] + peak_day["ambiguous_movement_identity_count"] <= peak_day["total_records"]


class TestClassificationConsistencyV2208:
    """Verifies classification consistency and event_classification exposure."""

    def test_flights_endpoint_exposes_event_classification(self):
        """Verifies /api/flights exposes event_classification and supports filtering."""
        res = client.get("/api/flights?airport_id=DAM&limit=10")
        assert res.status_code == 200
        flights = res.json()["flights"]
        for f in flights:
            assert "event_classification" in f
            if f["record_nature"] == "physical_movement":
                assert f["event_classification"] == "commercially_reported_operational_event"
            elif f["record_nature"] == "scheduled_service":
                assert f["event_classification"] == "scheduled_service"

    def test_filter_by_commercially_reported_operational_event(self):
        """Verifies querying /api/flights with record_nature=commercially_reported_operational_event works."""
        res = client.get("/api/flights?airport_id=DAM&record_nature=commercially_reported_operational_event&limit=20")
        assert res.status_code == 200
        flights = res.json()["flights"]
        assert len(flights) > 0
        for f in flights:
            assert f["record_nature"] == "physical_movement"
            assert f["event_classification"] == "commercially_reported_operational_event"
            assert f["evidence_level"] == "commercial_status_corroborated"
            assert f["runway_movement_evidence"] is None

    def test_single_event_endpoint_exposes_classification_and_evidence(self):
        """Verifies /api/events/{event_id} exposes event_classification and non-runway evidence."""
        res = client.get("/api/events/ca726fcf8dc8a9df")
        assert res.status_code == 200
        data = res.json()
        assert data["flight_number"] == "FZ1114"
        assert data["record_nature"] == "physical_movement"
        assert data["event_classification"] == "commercially_reported_operational_event"
        assert data["runway_movement_evidence"] is None
