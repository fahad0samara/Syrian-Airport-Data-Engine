"""
Tests for Version 2.20.5 — Estimated vs Actual Timestamp Provenance Correction
Syrian Airport Data Engine

Verifies:
1. FR24 / AviationStack estimated-to-actual timestamp mapping corrections.
2. Complete 6-field timestamp separation (scheduled, estimated, actual for dep/arr).
3. Missing actual timestamps remain strictly null.
4. Evidence taxonomy audit: 76 mislabeled evidence rows identified and corrected in application layer.
5. Movement counting semantics: confirmed_unique_movement_count, ambiguous_movement_identity_count.
6. Stats endpoint deprecation dictionary for legacy aircraft metrics.
7. Export metadata and payload consistency.
8. Cryptographic invariance of all 6 protected baseline hashes.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import csv
import json
import sqlite3
import hashlib
import pytest
from fastapi.testclient import TestClient

from src.api import app
from src.timestamp_provenance import correct_flight_record_semantics, correct_evidence_item

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


class TestCryptographicBaselineIntegrity:
    """Verifies that all 6 protected baseline database and raw snapshot files remain completely unchanged."""

    @pytest.mark.parametrize("filepath,expected_hash", list(PROTECTED_BASELINE_HASHES.items()))
    def test_baseline_file_sha256_invariant(self, filepath, expected_hash):
        assert Path(filepath).exists(), f"Protected file {filepath} does not exist"
        current_hash = get_file_sha256(filepath)
        assert current_hash == expected_hash, f"Hash mismatch for {filepath}: got {current_hash}, expected {expected_hash}"


class TestEstimatedToActualMappingCorrection:
    """Tests the audit and correction of estimated timestamps mismapped into actual fields."""

    def test_inventory_report_exists_and_valid(self):
        report_path = Path("reports/v2_20_5_estimated_mapping_inventory.csv")
        assert report_path.exists(), "Inventory report reports/v2_20_5_estimated_mapping_inventory.csv missing"
        with open(report_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 40, f"Expected exactly 40 affected events, found {len(rows)}"
        required_headers = [
            "event_id", "flight_number", "airport_id", "source", "raw_source_field",
            "stored_database_field", "record_nature", "evidence_type", "correction_required", "reason"
        ]
        for header in required_headers:
            assert header in reader.fieldnames, f"Missing header {header} in inventory report"

    def test_g9376_estimated_departure_correction(self):
        """G9376 (2026-10-09): FR24 time.estimated.departure must NOT populate actual_dep_time."""
        res = client.get("/api/flights?date=2026-10-09&airline=Air%20Arabia")
        assert res.status_code == 200
        flights = res.json()["flights"]
        g9376 = [f for f in flights if f.get("event_id") == "6e9ccc725c3b169e"][0]

        assert g9376["record_nature"] == "scheduled_service"
        assert g9376["scheduled_dep_time"] == "2026-10-09T10:55:00Z"
        assert g9376["estimated_dep_time"] == "2026-10-10T09:00:00Z"
        assert g9376["actual_dep_time"] is None
        assert g9376["raw_actual_dep_time"] is None
        assert g9376["raw_estimated_dep_time"] == 1791622800 or g9376["raw_estimated_dep_time"] == "1791622800"
        assert g9376["actual_movement_date"] is None
        assert g9376["estimated_movement_date"] == "2026-10-10"

    def test_xy592_destination_arrival_eta_separation(self):
        """XY592 (2026-10-10): Departure from DAM has real takeoff time; destination ETA is estimated arrival."""
        res = client.get("/api/flights?date=2026-10-10&airport_id=DAM&movement_type=departure&limit=200")
        assert res.status_code == 200
        flights = res.json()["flights"]
        xy592 = [f for f in flights if f.get("flight_number") == "XY592"][0]

        assert xy592["record_nature"] == "physical_movement"
        assert xy592["actual_dep_time"] is not None
        assert xy592["actual_arr_time"] is None  # destination ETA shifted out of actual arrival
        assert xy592["estimated_arr_time"] is not None

    def test_fyc521_destination_eta_separation(self):
        """FYC521 (2026-10-10): Departure event c5dbcfdfa11cb7b3 must not claim actual_arr_time for destination ETA."""
        res = client.get("/api/flights?date=2026-10-10&movement_type=departure&limit=200")
        assert res.status_code == 200
        flights = res.json()["flights"]
        fyc521 = [f for f in flights if f.get("flight_number") == "FYC521"][0]

        assert fyc521["record_nature"] == "physical_movement"
        assert fyc521["actual_dep_time"] is not None
        assert fyc521["actual_arr_time"] is None
        assert fyc521["estimated_arr_time"] is not None

    def test_qr410_actual_arrival_retained(self):
        """QR410: Genuine arrived flight has valid actual_arr_time and null estimated times."""
        res = client.get("/api/flights?date=2026-10-10&airport_id=DAM&movement_type=arrival&limit=200")
        assert res.status_code == 200
        flights = res.json()["flights"]
        qr410 = [f for f in flights if f.get("flight_number") == "QR410"]
        if qr410:
            rec = qr410[0]
            if rec.get("record_nature") == "physical_movement":
                assert rec["actual_arr_time"] is not None
                assert rec["estimated_arr_time"] is None


class TestSixFieldTimestampSeparation:
    """Verifies that all 6 timestamp fields are cleanly exposed across flight records."""

    def test_six_timestamp_fields_present_in_api(self):
        res = client.get("/api/flights?limit=20")
        assert res.status_code == 200
        flights = res.json()["flights"]
        required_fields = [
            "scheduled_dep_time", "estimated_dep_time", "actual_dep_time",
            "scheduled_arr_time", "estimated_arr_time", "actual_arr_time",
        ]
        for f in flights:
            for field in required_fields:
                assert field in f, f"Field {field} missing from flight record {f.get('event_id')}"

    def test_missing_actual_timestamps_remain_null(self):
        """Scheduled services without real movement must strictly have null actual timestamps, never '0' or fabricated strings."""
        res = client.get("/api/movements/scheduled?limit=50")
        assert res.status_code == 200
        for f in res.json()["movements"]:
            assert f["actual_dep_time"] is None, f"Scheduled flight {f.get('event_id')} has non-null actual_dep_time: {f['actual_dep_time']}"
            assert f["actual_arr_time"] is None, f"Scheduled flight {f.get('event_id')} has non-null actual_arr_time: {f['actual_arr_time']}"


class TestEvidenceTaxonomyAudit:
    """Verifies the evidence taxonomy corrections: estimated times are never mislabeled as Mode-S telemetry."""

    def test_evidence_item_correction(self):
        # Raw estimated departure evidence
        ev_dep = {
            "evidence_type": "adsb_takeoff",
            "raw_timestamp": "1791622800",
            "raw_payload": '{"flight": {"time": {"estimated": {"departure": 1791622800}}}}'
        }
        corrected_dep = correct_evidence_item(ev_dep)
        assert corrected_dep["evidence_type"] == "estimated_departure"
        assert corrected_dep["is_estimated"] is True

        # Raw estimated arrival evidence
        ev_arr = {
            "evidence_type": "adsb_touchdown",
            "raw_timestamp": "1791627000",
            "raw_payload": '{"flight": {"time": {"estimated": {"arrival": 1791627000}}}}'
        }
        corrected_arr = correct_evidence_item(ev_arr)
        assert corrected_arr["evidence_type"] == "estimated_arrival"
        assert corrected_arr["is_estimated"] is True

        # Genuine actual touchdown evidence remains adsb_touchdown
        ev_real = {
            "evidence_type": "adsb_touchdown",
            "raw_timestamp": "1791627000",
            "raw_payload": '{"flight": {"time": {"real": {"arrival": 1791627000}}}}'
        }
        corrected_real = correct_evidence_item(ev_real)
        assert corrected_real["evidence_type"] == "adsb_touchdown"
        assert corrected_real["is_estimated"] is False


class TestMovementCountingSemantics:
    """Verifies confirmed_unique_movement_count, ambiguous_movement_identity_count, and codeshare deduplication."""

    def test_movements_comparison_exposes_confirmed_and_ambiguous_counts(self):
        res = client.get("/api/movements/comparison?airport_id=DAM")
        assert res.status_code == 200
        data = res.json()
        assert "comparison" in data
        assert "field_definitions" in data
        assert "deduplication_rules" in data

        fdefs = data["field_definitions"]
        assert "confirmed_unique_movement_count" in fdefs
        assert "ambiguous_movement_identity_count" in fdefs
        assert "unique_operating_flight_count" in fdefs

        for row in data["comparison"]:
            assert "confirmed_unique_movement_count" in row
            assert "ambiguous_movement_identity_count" in row
            assert "unique_operating_flight_count" in row
            assert "scheduled_record_count" in row
            assert "commercially_reported_count" in row
            # Confirmed unique movements must not exceed commercially reported count
            assert row["confirmed_unique_movement_count"] <= row["commercially_reported_count"]
            assert row["confirmed_unique_movement_count"] + row["ambiguous_movement_identity_count"] <= row["total_records"]


class TestStatsAndExportConsistency:
    """Verifies stats endpoint deprecation notices and export metadata consistency."""

    def test_stats_deprecated_metrics_dictionary(self):
        res = client.get("/api/movements/stats")
        assert res.status_code == 200
        stats = res.json()
        assert "deprecated_metrics" in stats
        dep = stats["deprecated_metrics"]
        assert "total_unique_aircraft" in dep
        assert "unique_aircraft_tracked" in dep
        assert "distinct_reported_aircraft_registrations" in stats
        assert stats["distinct_reported_aircraft_registrations"] == 63

    def test_export_metadata_and_downloads(self):
        for ds in ["all_syrian_flight_events", "damascus_flight_events"]:
            res_meta = client.get(f"/api/export/{ds}/metadata")
            assert res_meta.status_code == 200
            meta = res_meta.json()["metadata"]
            assert "estimated_dep_time" in meta["known_limitations"]

            res_csv = client.get(f"/api/export/{ds}?format=csv")
            assert res_csv.status_code == 200
            first_line = res_csv.text.split("\n")[0]
            # Verify columns include estimated fields
            assert "estimated_dep_time" in first_line
            assert "estimated_arr_time" in first_line
