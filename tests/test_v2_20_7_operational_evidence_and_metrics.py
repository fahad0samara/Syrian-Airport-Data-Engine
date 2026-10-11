"""
Tests for Version 2.20.7 — Final Operational Evidence & Movement Metrics Validation
Syrian Airport Data Engine

Verifies:
1. Per-event validation of all 9 physical-movement records (provenance, explicit actual/real vs estimated).
2. Estimated timestamps rejected as actual timestamps across all events.
3. Scheduled timestamps rejected as actual timestamps across all events.
4. Explicit actual timestamps accepted with valid commercial provenance.
5. Commercial actual timestamps distinguished from runway sensor evidence (runway_movement_evidence strictly null).
6. Movement-count semantics: resolved_commercial_movement_count, unique_operating_flight_count,
   ambiguous_movement_identity_count, and distinct_reported_aircraft_registrations.
7. Codeshare listings do not inflate resolved movement counts.
8. Ambiguous identities remain strictly excluded from resolved counts.
9. Missing timestamps remain null.
10. API, dashboard, and export consistency.
11. Cryptographic baseline hash invariance across all 6 protected assets.
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
from src.timestamp_provenance import (
    correct_flight_record_semantics,
    correct_evidence_item,
    ESTIMATED_IN_ACTUAL_EVENTS,
    MISLABELED_EVIDENCE_MAP
)

client = TestClient(app)

PROTECTED_BASELINE_HASHES = {
    "data/damascus_airport.db": "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b",
    "data/archived_fids_staging.db": "a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4",
    "data/archived_fids_analytics.db": "e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe",
    "data/archived_fids_history_staging.db": "39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f",
    "data/raw/snapshots/wayback_damairport_fids_20260709234230.raw": "5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf",
    "data/raw/snapshots/wayback_damairport_fids_20260709234230.json": "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491",
}

PHYSICAL_MOVEMENT_9_EVENTS = [
    {"event_id": "6f3f3b3c16844646", "flight": "PC771", "airport": "ALP", "dir": "departure", "date": "2026-10-10", "raw_dep": "1791640807", "iso_dep": "2026-10-10T14:00:07Z", "est_arr": "2026-10-10T15:20:55Z"},
    {"event_id": "339297a946c498c3", "flight": "XY230", "airport": "ALP", "dir": "departure", "date": "2026-10-10", "raw_dep": "1791638403", "iso_dep": "2026-10-10T13:20:03Z", "est_arr": "2026-10-10T15:52:33Z"},
    {"event_id": "ed1a39d3aa27b295", "flight": "EY562", "airport": "DAM", "dir": "departure", "date": "2026-10-09", "raw_dep": "1791558501", "iso_dep": "2026-10-09T15:08:21Z", "est_arr": "2026-10-09T17:56:00Z"},
    {"event_id": "c5dbcfdfa11cb7b3", "flight": "FYC521", "airport": "DAM", "dir": "departure", "date": "2026-10-10", "raw_dep": "1791610068", "iso_dep": "2026-10-10T05:27:48Z", "est_arr": "2026-10-10T06:44:30Z"},
    {"event_id": "14175fe4b51cfa91", "flight": "FYC727", "airport": "DAM", "dir": "departure", "date": "2026-10-10", "raw_dep": "1791631856", "iso_dep": "2026-10-10T11:30:56Z", "est_arr": "2026-10-10T14:04:21Z"},
    {"event_id": "ca726fcf8dc8a9df", "flight": "FZ1114", "airport": "DAM", "dir": "departure", "date": "2026-10-10", "raw_dep": "1791640456", "iso_dep": "2026-10-10T13:54:16Z", "est_arr": "2026-10-10T16:39:35Z"},
    {"event_id": "81d8452b0a0b029f", "flight": "G9376", "airport": "DAM", "dir": "departure", "date": "2026-10-10", "raw_dep": "1791630700", "iso_dep": "2026-10-10T11:11:40Z", "est_arr": "2026-10-10T13:56:57Z"},
    {"event_id": "f6afc1b400abecc6", "flight": "RB441", "airport": "DAM", "dir": "departure", "date": "2026-10-10", "raw_dep": "1791642278", "iso_dep": "2026-10-10T14:24:38Z", "est_arr": "2026-10-10T18:17:12Z"},
    {"event_id": "85e816d0ed6253c6", "flight": "XY592", "airport": "DAM", "dir": "departure", "date": "2026-10-10", "raw_dep": "1791638817", "iso_dep": "2026-10-10T13:26:57Z", "est_arr": "2026-10-10T15:39:48Z"},
]


def get_file_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class TestCryptographicBaselineIntegrityV2207:
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


class TestOperationalEvidenceValidationV2207:
    """Validates the 9 physical-movement events and their explicit raw timestamp provenance."""

    @pytest.mark.parametrize("expected", PHYSICAL_MOVEMENT_9_EVENTS)
    def test_physical_movement_departure_actual_provenance(self, expected):
        """Validates that legitimate commercial actual departures are accepted with proper provenance."""
        res = client.get(f"/api/events/{expected['event_id']}")
        assert res.status_code == 200
        data = res.json()

        assert data["flight_number"] == expected["flight"]
        assert data["airport_id"] == expected["airport"]
        assert data["movement_type"] == expected["dir"]
        assert data["record_nature"] == "physical_movement"

        # Explicit commercial actual takeoff timestamp must match
        assert data["actual_dep_time"] == expected["iso_dep"]
        assert data["raw_actual_dep_time"] == expected["raw_dep"]

        # Destination ETA must NOT be in actual_arr_time; it must be in estimated_arr_time
        assert data["actual_arr_time"] is None
        assert data["estimated_arr_time"] == expected["est_arr"]

        # Missing actual arrival timestamp remains null
        assert data["actual_arr_time"] is None

    def test_estimated_timestamp_rejected_as_actual_in_scheduled_service(self):
        """Verifies that estimated timestamps are rejected as actual timestamps in scheduled services."""
        # G9376 on Oct 09 had estimated departure 1791622800 mapped to actual_dep_time in DB
        res = client.get("/api/events/6e9ccc725c3b169e")
        assert res.status_code == 200
        data = res.json()

        assert data["record_nature"] == "scheduled_service"
        assert data["actual_dep_time"] is None
        assert data["actual_arr_time"] is None
        assert data["estimated_dep_time"] is not None

    def test_scheduled_timestamp_rejected_as_actual(self):
        """Verifies that scheduled timetable slots never populate actual timestamps."""
        res = client.get("/api/movements/scheduled?limit=50")
        assert res.status_code == 200
        movements = res.json()["movements"]
        for m in movements:
            assert m["actual_dep_time"] is None, f"Scheduled event {m['event_id']} has non-null actual_dep_time!"
            assert m["actual_arr_time"] is None, f"Scheduled event {m['event_id']} has non-null actual_arr_time!"
            assert m["actual_timestamp"] is None, f"Scheduled event {m['event_id']} has non-null actual_timestamp!"

    def test_commercial_actual_distinguished_from_runway_sensor_evidence(self):
        """Verifies that commercial actual timestamps are not treated as direct runway sensor evidence."""
        res = client.get("/api/movements/verified?limit=50")
        assert res.status_code == 200
        movements = res.json()["movements"]
        for m in movements:
            # Direct ground runway sensor evidence is strictly null/unverified
            assert m["runway_movement_evidence"] is None, (
                f"Movement {m['event_id']} improperly claimed direct runway sensor evidence!"
            )
            # Commercial evidence level is commercial_status_corroborated, not direct sensor
            assert m["evidence_level"] == "commercial_status_corroborated"


class TestMovementMetricsSemanticsV2207:
    """Validates movement-count semantics, renaming, and deduplication rules."""

    def test_resolved_commercial_movement_count_present_and_renamed(self):
        """Verifies resolved_commercial_movement_count is present and confirmed_unique_movement_count is preserved as alias."""
        res = client.get("/api/movements/comparison?airport_id=DAM")
        assert res.status_code == 200
        data = res.json()

        assert "resolved_commercial_movement_count" in data["field_definitions"]
        assert "confirmed_unique_movement_count" in data["field_definitions"]

        # Check definition disclaims runway radar confirmation
        def_resolved = data["field_definitions"]["resolved_commercial_movement_count"]
        assert "Does NOT imply runway radar sensor confirmation" in def_resolved

        def_confirmed = data["field_definitions"]["confirmed_unique_movement_count"]
        assert "Deprecated alias" in def_confirmed
        assert "NOT ground radar or runway sensor contacts" in def_confirmed

        # Verify per-row values
        for row in data["comparison"]:
            assert "resolved_commercial_movement_count" in row
            assert "confirmed_unique_movement_count" in row
            assert row["resolved_commercial_movement_count"] == row["unique_operating_flight_count"]
            assert row["confirmed_unique_movement_count"] == row["resolved_commercial_movement_count"]

    def test_codeshares_do_not_inflate_resolved_movement_counts(self):
        """Verifies that marketing codeshares do not inflate resolved commercial movement counts."""
        res = client.get("/api/movements/comparison?airport_id=DAM")
        assert res.status_code == 200
        data = res.json()

        for row in data["comparison"]:
            resolved = row["resolved_commercial_movement_count"]
            comm_events = row["commercial_operational_event_count"]
            codeshares = row["codeshare_record_count"]
            total_recs = row["total_records"]

            # Resolved count cannot exceed commercial operational events
            assert resolved <= comm_events
            # Codeshares are separate from resolved operating movements
            if codeshares > 0:
                assert resolved <= (total_recs - codeshares)

    def test_ambiguous_identities_remain_excluded_from_resolved_counts(self):
        """Verifies that ambiguous codeshare identities remain excluded from resolved counts."""
        res = client.get("/api/movements/comparison?airport_id=DAM")
        assert res.status_code == 200
        data = res.json()

        peak_day = next((r for r in data["comparison"] if r["flight_date"] == "2026-10-10"), None)
        assert peak_day is not None
        assert peak_day["ambiguous_movement_identity_count"] == 1
        assert peak_day["matched_codeshare_record_count"] == 14
        assert peak_day["resolved_commercial_movement_count"] == 47

        # Ambiguous records must NOT be added into resolved movement counts
        assert peak_day["resolved_commercial_movement_count"] == peak_day["unique_operating_flight_count"]
        assert peak_day["resolved_commercial_movement_count"] + peak_day["ambiguous_movement_identity_count"] <= peak_day["total_records"]

    def test_distinct_reported_aircraft_registrations_semantics(self):
        """Verifies distinct_reported_aircraft_registrations calculation and deprecated aliases."""
        res = client.get("/api/movements/stats")
        assert res.status_code == 200
        stats = res.json()

        assert "distinct_reported_aircraft_registrations" in stats
        assert stats["distinct_reported_aircraft_registrations"] == 63
        assert stats["total_unique_aircraft"] == 63
        assert stats["unique_aircraft_tracked"] == 63
        assert "deprecated_metrics" in stats
        assert "total_unique_aircraft" in stats["deprecated_metrics"]
        assert "unique_aircraft_tracked" in stats["deprecated_metrics"]


class TestCrossCheckApiAndDashboardV2207:
    """Verifies consistency between API responses, dashboard markup, and export sidecars."""

    def test_movements_verified_endpoint_descriptions(self):
        """Verifies /api/movements/verified description explicitly notes ground sensor pending."""
        res = client.get("/api/movements/verified?airport_id=DAM&limit=10")
        assert res.status_code == 200
        data = res.json()
        assert "Direct on-ground runway sensor telemetry is pending" in data["description"]
        assert data["event_classification"] == "commercially_reported_operational_event"

    def test_export_metadata_sidecars_have_no_false_radar_claims(self):
        """Verifies export metadata does not claim direct runway radar contacts."""
        res = client.get("/api/export/damascus_flight_events/metadata")
        assert res.status_code == 200
        meta = res.json()["metadata"]
        assert "direct runway radar telemetry is pending" in meta["known_limitations"]
        assert meta["evidence_level"] == "multi_tier_commercial_and_timetable"

    def test_dashboard_html_contains_accurate_operational_copy(self):
        """Verifies static/index.html does not claim physical radar confirmation without sensors."""
        html_path = Path("static/index.html")
        assert html_path.exists()
        content = html_path.read_text(encoding="utf-8")
        assert "Segregated commercially reported operational events" in content
        assert "ground runway sensors pending" in content
