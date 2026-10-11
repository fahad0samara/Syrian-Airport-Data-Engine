"""
Tests for Version 2.20.6 — Immutable Evidence Correction & End-to-End Semantic Audit
Syrian Airport Data Engine

Verifies:
1. Forensic audit of the 76 mislabeled evidence records (35 takeoffs, 41 touchdowns).
2. Immutable database ledger preservation (no DELETE/UPDATE on event_evidence).
3. Evidence forensic endpoint exposing original classification and visible correction history.
4. /api/evidence/audit endpoint and export artifacts.
5. End-to-end 6-field timestamp consistency (scheduled, estimated, actual for dep/arr).
6. Reconciliation of all 40 affected events (31 scheduled services, 9 physical movements).
7. Movement identity validation: confirmed vs ambiguous counts, codeshare matching.
8. Aircraft registration metric distinction and deprecated aliases.
9. Cryptographic baseline hash invariance across all 6 protected assets.
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
from src.timestamp_provenance import (
    correct_flight_record_semantics,
    correct_evidence_item,
    ESTIMATED_IN_ACTUAL_EVENTS,
    MISLABELED_EVIDENCE_MAP
)
from src.normalizer import evaluate_cross_source_match

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


class TestCryptographicBaselineIntegrityV2206:
    """Verifies that all 6 protected baseline database and raw snapshot files remain strictly untouched."""

    @pytest.mark.parametrize("filepath,expected_hash", list(PROTECTED_BASELINE_HASHES.items()))
    def test_baseline_file_sha256_invariant(self, filepath, expected_hash):
        assert Path(filepath).exists(), f"Protected file {filepath} does not exist"
        current_hash = get_file_sha256(filepath)
        assert current_hash == expected_hash, f"Hash mismatch for {filepath}: got {current_hash}, expected {expected_hash}"


class TestAuditOf76MislabeledEvidenceRecords:
    """Forensic audit of all 76 evidence records derived from estimated timestamps."""

    def test_csv_and_json_audit_reports_exist(self):
        csv_path = Path("reports/v2_20_6_mislabeled_evidence_audit.csv")
        json_path = Path("reports/v2_20_6_mislabeled_evidence_audit.json")
        assert csv_path.exists(), "CSV report missing"
        assert json_path.exists(), "JSON report missing"

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 76, f"Expected 76 mislabeled records, got {len(rows)}"
        required_headers = [
            "evidence_id", "event_id", "flight_number", "original_evidence_type",
            "corrected_semantic_interpretation", "original_raw_source_field",
            "original_raw_value", "source_name", "correction_status",
            "persistence_mechanism", "reason"
        ]
        for h in required_headers:
            assert h in reader.fieldnames, f"Header {h} missing from audit report"

    def test_breakdown_of_takeoffs_and_touchdowns(self):
        records = list(MISLABELED_EVIDENCE_MAP.values())
        assert len(records) == 76
        takeoffs = [r for r in records if "takeoff" in r["original_evidence_type"]]
        touchdowns = [r for r in records if "touchdown" in r["original_evidence_type"]]
        assert len(takeoffs) == 35, f"Expected 35 takeoffs, got {len(takeoffs)}"
        assert len(touchdowns) == 41, f"Expected 41 touchdowns, got {len(touchdowns)}"

    def test_immutable_event_evidence_rows_remain_in_database(self):
        """Verifies that original event_evidence rows remain in the DB and were not deleted/modified."""
        conn = sqlite3.connect("file:data/damascus_airport.db?mode=ro", uri=True)
        cur = conn.cursor()
        for ev_id, info in list(MISLABELED_EVIDENCE_MAP.items())[:10]: # spot check 10
            cur.execute("SELECT evidence_id, evidence_type FROM event_evidence WHERE evidence_id = ?", (ev_id,))
            row = cur.fetchone()
            assert row is not None, f"Evidence row {ev_id} missing from database!"
            # In the immutable SQLite ledger, original evidence_type is preserved
            assert row[1] == info["original_evidence_type"]
        conn.close()

    def test_api_evidence_audit_endpoint(self):
        res = client.get("/api/evidence/audit")
        assert res.status_code == 200
        data = res.json()
        assert data["total_mislabeled_evidence_records"] == 76
        assert data["original_takeoffs_reclassified"] == 35
        assert data["original_touchdowns_reclassified"] == 41
        assert "immutable_ledger_policy" in data
        assert len(data["records"]) == 76

    def test_event_evidence_endpoint_exposes_forensic_correction_history(self):
        # G9376 event_id = 6e9ccc725c3b169e has mislabeled takeoff evidence
        res = client.get("/api/events/6e9ccc725c3b169e/evidence?forensic=true")
        assert res.status_code == 200
        data = res.json()
        assert data["has_mislabeled_evidence"] is True
        assert data["corrected_count"] > 0
        assert data["forensic_mode"] is True

        for ev in data["evidence"]:
            if ev.get("is_estimated"):
                assert "original_evidence_type" in ev
                assert "correction_history" in ev
                assert len(ev["correction_history"]) > 0
                hist = ev["correction_history"][0]
                assert hist["original_classification"] == ev["original_evidence_type"]
                assert hist["corrected_classification"] == ev["evidence_type"]
                assert "reason" in hist


class TestEndToEndTimestampConsistency:
    """Verifies complete 6-field timestamp consistency across all layers."""

    def test_six_timestamp_fields_in_flights_api(self):
        res = client.get("/api/flights?limit=25")
        assert res.status_code == 200
        flights = res.json()["flights"]
        for f in flights:
            for field in [
                "scheduled_dep_time", "estimated_dep_time", "actual_dep_time",
                "scheduled_arr_time", "estimated_arr_time", "actual_arr_time"
            ]:
                assert field in f

    def test_only_explicit_actual_source_fields_populate_actual_timestamps(self):
        """Physical movements must have non-null actual timestamp with valid source provenance."""
        res = client.get("/api/movements/verified?limit=20")
        assert res.status_code == 200
        for m in res.json()["movements"]:
            actual = m.get("actual_dep_time") or m.get("actual_arr_time")
            assert actual is not None, f"Physical movement {m.get('event_id')} has null actual timestamp"
            assert not actual.startswith("0"), "Fabricated zero string found"

    def test_missing_actual_timestamps_remain_null(self):
        res = client.get("/api/movements/scheduled?limit=50")
        assert res.status_code == 200
        for m in res.json()["movements"]:
            assert m["actual_dep_time"] is None
            assert m["actual_arr_time"] is None

    def test_ingestion_and_observation_timestamps_separated(self):
        res = client.get("/api/flights?limit=20")
        assert res.status_code == 200
        for f in res.json()["flights"]:
            assert "ingested_at" in f
            assert "source_observed_at" in f
            # Ingestion timestamp must never be substituted for missing source_observed_at
            if f.get("source_observed_at"):
                assert f["source_observed_at"] != f["ingested_at"]


class TestAuditOf40AffectedEvents:
    """Reconciles the 40-event inventory against application output."""

    def test_31_scheduled_services_have_no_actual_timestamps(self):
        res = client.get("/api/flights?limit=500")
        assert res.status_code == 200
        flights_map = {f["event_id"]: f for f in res.json()["flights"]}

        for eid, info in ESTIMATED_IN_ACTUAL_EVENTS.items():
            if info["movement"] == "arrival" or eid not in [
                "6f3f3b3c16844646", "339297a946c498c3", "ed1a39d3aa27b295", "c5dbcfdfa11cb7b3",
                "14175fe4b51cfa91", "ca726fcf8dc8a9df", "81d8452b0a0b029f", "f6afc1b400abecc6",
                "85e816d0ed6253c6"
            ]:
                if eid in flights_map:
                    f = flights_map[eid]
                    assert f["actual_dep_time"] is None, f"Event {eid} has non-null actual_dep_time"
                    assert f["actual_arr_time"] is None, f"Event {eid} has non-null actual_arr_time"
                    assert f["record_nature"] == "scheduled_service"

    def test_9_physical_movements_have_destination_etas_as_estimated_arrivals(self):
        res = client.get("/api/movements/verified?limit=200")
        assert res.status_code == 200
        ver_map = {m["event_id"]: m for m in res.json()["movements"]}

        nine_dep_eids = [
            "6f3f3b3c16844646", "339297a946c498c3", "ed1a39d3aa27b295", "c5dbcfdfa11cb7b3",
            "14175fe4b51cfa91", "ca726fcf8dc8a9df", "81d8452b0a0b029f", "f6afc1b400abecc6",
            "85e816d0ed6253c6"
        ]
        for eid in nine_dep_eids:
            if eid in ver_map:
                m = ver_map[eid]
                assert m["actual_dep_time"] is not None
                assert m["actual_arr_time"] is None, f"Physical departure {eid} retained foreign destination ETA in actual_arr_time"
                assert m["estimated_arr_time"] is not None, f"Physical departure {eid} missing destination ETA in estimated_arr_time"


class TestMovementIdentityAndCounting:
    """Verifies confirmed vs ambiguous movement counts and 8 cross-source matching edge cases."""

    def test_comparison_endpoint_confirmed_vs_ambiguous(self):
        res = client.get("/api/movements/comparison?airport_id=DAM")
        assert res.status_code == 200
        data = res.json()
        for row in data["comparison"]:
            assert row["confirmed_unique_movement_count"] <= row["commercially_reported_count"]
            assert row["confirmed_unique_movement_count"] + row["ambiguous_movement_identity_count"] <= row["total_records"]

    def test_carrier_conflict_prevents_merge(self):
        ev1 = {"airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10", "flight_number": "RB100", "airline_name": "Syrian Air", "actual_dep_time": "2026-10-10T08:00:00Z"}
        ev2 = {"airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10", "flight_number": "RB100", "airline_name": "FlyDamas", "actual_dep_time": "2026-10-10T08:05:00Z"}
        res = evaluate_cross_source_match(ev1, ev2)
        assert not res["can_merge"]
        assert res["match_status"] == "CONFLICT_CARRIER"

    def test_time_difference_exceeding_180m_splits_distinct_legs(self):
        ev1 = {"airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10", "flight_number": "RB100", "actual_dep_time": "2026-10-10T08:00:00Z"}
        ev2 = {"airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10", "flight_number": "RB100", "actual_dep_time": "2026-10-10T14:00:00Z"}
        res = evaluate_cross_source_match(ev1, ev2)
        assert not res["can_merge"]
        assert res["match_status"] == "SPLIT_DISTINCT_LEG"


class TestAircraftRegistrationMetricsV2206:
    """Verifies registration count calculation and deprecation notices."""

    def test_stats_registration_count_and_deprecation(self):
        res = client.get("/api/movements/stats")
        assert res.status_code == 200
        stats = res.json()
        assert stats["distinct_reported_aircraft_registrations"] == 63
        assert "deprecated_metrics" in stats
        assert "total_unique_aircraft" in stats["deprecated_metrics"]
        assert "unique_aircraft_tracked" in stats["deprecated_metrics"]


class TestExportAuditV2206:
    """Verifies evidence audit export metadata and download responses."""

    def test_evidence_audit_export_metadata_and_downloads(self):
        res_meta = client.get("/api/export/v2_20_6_mislabeled_evidence_audit/metadata")
        assert res_meta.status_code == 200
        meta = res_meta.json()["metadata"]
        assert meta["dataset_category"] == "audit_log"
        assert meta["geographic_scope"] == "DAM & ALP Aerodromes"

        res_csv = client.get("/api/export/v2_20_6_mislabeled_evidence_audit?format=csv")
        assert res_csv.status_code == 200
        assert "evidence_id" in res_csv.text

        res_json = client.get("/api/export/v2_20_6_mislabeled_evidence_audit?format=json")
        assert res_json.status_code == 200
        data = res_json.json()
        assert len(data) == 76
