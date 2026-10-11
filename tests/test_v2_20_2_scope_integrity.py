import os
import csv
import hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api import app, normalize_timestamp_to_utc

client = TestClient(app)

PROTECTED_HASHES = {
    "data/damascus_airport.db": "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b",
    "data/archived_fids_staging.db": "a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4",
    "data/archived_fids_analytics.db": "e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe",
    "data/archived_fids_history_staging.db": "39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f",
    "data/raw/snapshots/wayback_damairport_fids_20260709234230.raw": "5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf",
    "data/raw/snapshots/wayback_damairport_fids_20260709234230.json": "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491",
}


class TestTimestampNormalizationAndSeparation:
    """Verifies Unix timestamp detection, UTC ISO-8601 normalization, and strict separation from ingestion time."""

    def test_normalize_timestamp_helper(self):
        # 10-digit Unix seconds
        assert normalize_timestamp_to_utc("1791638817") == "2026-10-10T13:26:57Z"
        assert normalize_timestamp_to_utc(1791638817) == "2026-10-10T13:26:57Z"

        # 13-digit Unix milliseconds
        assert normalize_timestamp_to_utc("1791638817000") == "2026-10-10T13:26:57Z"
        assert normalize_timestamp_to_utc(1791638817000) == "2026-10-10T13:26:57Z"

        # ISO string with UTC offset
        assert normalize_timestamp_to_utc("2026-10-10T16:26:57+03:00") == "2026-10-10T13:26:57Z"
        assert normalize_timestamp_to_utc("2026-10-10T13:26:57Z") == "2026-10-10T13:26:57Z"

        # Missing / None
        assert normalize_timestamp_to_utc(None) is None
        assert normalize_timestamp_to_utc("") is None
        assert normalize_timestamp_to_utc("None") is None

    def test_flight_endpoints_contain_normalized_and_raw_timestamps(self):
        endpoints = [
            "/api/flights?limit=25",
            "/api/movements/verified?limit=25",
            "/api/movements/scheduled?limit=25",
            "/api/movements/unverified?limit=25",
        ]
        for ep in endpoints:
            res = client.get(ep)
            assert res.status_code == 200
            data = res.json()
            records = data.get("flights") or data.get("movements") or []
            assert len(records) > 0

            for r in records:
                assert "source_observed_at" in r
                assert "source_observed_at_raw" in r
                assert "ingested_at" in r
                assert "actual_timestamp" in r

                # Ingestion timestamp must never replace source observation timestamp
                if r.get("source_observed_at"):
                    assert r["source_observed_at"] != r["ingested_at"]
                    # Normalized timestamp must end with Z
                    assert r["source_observed_at"].endswith("Z")

    def test_xy592_october_10_timestamp_provenance(self):
        res = client.get("/api/flights?date=2026-10-10&airport_id=DAM&limit=100")
        assert res.status_code == 200
        flights = res.json().get("flights", [])
        xy592 = [f for f in flights if f.get("flight_number") == "XY592"]
        assert len(xy592) == 1
        record = xy592[0]

        # Verify timestamp matches October 2026, NOT 2024
        assert record["flight_date"] == "2026-10-10"
        assert "2026-10-10" in record["source_observed_at"]
        assert record["source_observed_at"].startswith("2026-10-10T")
        assert record["record_nature"] == "physical_movement"

    def test_timestamp_audit_csv_integrity(self):
        csv_path = Path("reports/v2_20_2_timestamp_audit.csv")
        assert csv_path.exists(), "Timestamp audit CSV reports/v2_20_2_timestamp_audit.csv missing"
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1830, f"Expected 1,830 rows in audit CSV, found {len(rows)}"

        # Validate headers
        expected_cols = [
            "event_id", "flight_number", "flight_date", "airport_id", "record_nature",
            "raw_source_timestamp", "normalized_utc_timestamp", "airport_local_date",
            "date_matches_flight_date", "discrepancy_reason", "timestamp_validity"
        ]
        for col in expected_cols:
            assert col in reader.fieldnames

        # Check XY592 on 2026-10-10
        xy_row = [r for r in rows if r["flight_number"] == "XY592" and r["flight_date"] == "2026-10-10"][0]
        assert xy_row["date_matches_flight_date"] == "True"
        assert xy_row["discrepancy_reason"] == "none"
        assert xy_row["timestamp_validity"] == "valid"

        # Check cross-midnight discrepancies exist and are documented
        discrepancies = [r for r in rows if r["date_matches_flight_date"] == "False"]
        assert len(discrepancies) == 4
        reasons = {r["discrepancy_reason"] for r in discrepancies}
        assert "cross_midnight_local_shift" in reasons
        assert "operational_delay_next_day" in reasons


class TestComparisonCountingIntegrity:
    """Verifies that comparison counts explicitly partition records without double counting."""

    def test_movements_comparison_explicit_fields(self):
        res = client.get("/api/movements/comparison?airport_id=DAM&start_date=2026-10-09&end_date=2026-10-10")
        assert res.status_code == 200
        data = res.json()
        assert "deduplication_rules" in data
        assert len(data["deduplication_rules"]) >= 4

        days = data["comparison"]
        assert len(days) == 2
        day1 = days[0]

        # Verify all explicit count fields are present
        required_fields = [
            "total_records",
            "scheduled_record_count",
            "commercial_operational_event_count",
            "codeshare_record_count",
            "matched_codeshare_record_count",
            "unmatched_codeshare_record_count",
            "unverified_record_count",
            "unique_operating_flight_count",
            "unique_flight_movement_count",
        ]
        for f in required_fields:
            assert f in day1, f"Missing required comparison field '{f}'"

        # Operating flights must not be inflated by codeshares
        assert day1["unique_operating_flight_count"] <= day1["commercial_operational_event_count"]
        assert day1["unique_operating_flight_count"] < (day1["commercial_operational_event_count"] + day1["codeshare_record_count"])

        # Codeshares matched + unmatched must equal total codeshares
        assert day1["matched_codeshare_record_count"] + day1["unmatched_codeshare_record_count"] == day1["codeshare_record_count"]

        # Total records is sum of all disjoint records
        assert day1["total_records"] == 113
        assert day1["scheduled_record_count"] == 40
        assert day1["commercial_operational_event_count"] == 51
        assert day1["codeshare_record_count"] == 19
        assert day1["unverified_record_count"] == 3


class TestGeographicScopeAndTimelineIntegrity:
    """Verifies that all 34 timeline months have accurate scope and October 2026 is properly classified."""

    def test_timeline_contains_dam_observation_and_scope(self):
        res = client.get("/api/historical-coverage/timeline")
        assert res.status_code == 200
        data = res.json()
        timeline = data["timeline"]
        assert len(timeline) == 34

        for m in timeline:
            assert "geographic_scope" in m
            assert "dataset_category" in m
            assert "evidence_level" in m
            assert "is_dam_specific" in m
            assert "contains_dam_observation" in m
            assert "record_count" in m
            assert "source_period" in m
            assert "explicit_warning" in m

        timeline_map = {m["source_period"]: m for m in timeline}

        # October 2026: Regional ADS-B overflight sample (16 observations)
        # MUST have is_dam_specific: False and contains_dam_observation: True
        oct_2026 = timeline_map["2026-10"]
        assert oct_2026["dataset_category"] == "live_regional_adsb"
        assert oct_2026["record_count"] == 16
        assert oct_2026["is_dam_specific"] is False, "October 2026 regional ADS-B sample must NOT be labeled DAM-specific physical movement"
        assert oct_2026["contains_dam_observation"] is True, "October 2026 contains regional transit associated with DAM"

        # July 2026: Official DAM archived FIDS
        jul_2026 = timeline_map["2026-07"]
        assert jul_2026["dataset_category"] == "dam_scheduled_fids"
        assert jul_2026["is_dam_specific"] is True
        assert jul_2026["contains_dam_observation"] is True

        # 2024-01: Regional aggregate (DAM_ALP_LTK)
        jan_2024 = timeline_map["2024-01"]
        assert jan_2024["dataset_category"] == "regional_aggregate"
        assert jan_2024["is_dam_specific"] is False
        assert jan_2024["contains_dam_observation"] is False

        # 2025-06: Data gap
        jun_2025 = timeline_map["2025-06"]
        assert jun_2025["dataset_category"] == "no_verified_dam_data"
        assert jun_2025["is_dam_specific"] is False
        assert jun_2025["contains_dam_observation"] is False
        assert jun_2025["record_count"] == 0


class TestProtectedBaselineIntegrityV2202:
    """Verifies that all 6 baseline production assets remain cryptographically intact."""

    def test_six_protected_assets_hashes(self):
        for path, expected_hash in PROTECTED_HASHES.items():
            assert os.path.exists(path), f"Protected file missing: {path}"
            with open(path, "rb") as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            assert actual_hash == expected_hash, (
                f"CRYPTO INTEGRITY FAILURE on {path}: expected {expected_hash}, got {actual_hash}"
            )
