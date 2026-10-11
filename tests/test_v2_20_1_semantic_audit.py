"""
Tests for Version 2.20.1 — Final Semantic Consistency & Export Integrity Audit.

Covers:
1. Provider metrics distinctions (provider_count, independent_observation_count, independent_provider_count).
2. Strict timestamp semantics separation (source_observed_at, ingested_at, actual_timestamp).
3. Comparison and codeshare counting: distinguishing operating flights and codeshares without double-counting.
4. 34-month historical coverage timeline endpoint and integrity invariants.
5. Export self-describing metadata, sidecar JSON endpoint, and metadata schemas.
6. Dashboard UX elements and semantic boundary disclosures in static/index.html.
7. Cryptographic immutability of the six protected assets.
"""

import hashlib
import json
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api import app, EXPORT_METADATA

client = TestClient(app)

PROTECTED_HASHES = {
    "data/damascus_airport.db": "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b",
    "data/archived_fids_staging.db": "a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4",
    "data/archived_fids_analytics.db": "e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe",
    "data/archived_fids_history_staging.db": "39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f",
    "data/raw/snapshots/wayback_damairport_fids_20260709234230.raw": "5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf",
    "data/raw/snapshots/wayback_damairport_fids_20260709234230.json": "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491",
}


class TestProviderMetricsDistinctions:
    """Verifies strict provider metric definitions and unverified upstream infrastructure disclosure."""

    def test_provider_metric_fields_on_flight_events(self):
        res = client.get("/api/flights?limit=25")
        assert res.status_code == 200
        flights = res.json().get("flights", [])
        assert len(flights) > 0

        for f in flights:
            assert "provider_count" in f
            assert "independent_observation_count" in f
            assert "independent_provider_count" in f

            assert isinstance(f["provider_count"], int)
            assert f["provider_count"] >= 0

            assert isinstance(f["independent_observation_count"], int)
            assert f["independent_observation_count"] >= 0

            # Commercial aggregators lack verified separate sensor infrastructure
            assert f["independent_provider_count"] is None, (
                f"independent_provider_count must be None/null for unverified upstream hardware, got {f['independent_provider_count']}"
            )

    def test_provider_metrics_on_verified_movements(self):
        res = client.get("/api/movements/verified?limit=25")
        assert res.status_code == 200
        movements = res.json().get("movements", [])
        assert len(movements) > 0

        for m in movements:
            assert m["independent_provider_count"] is None
            assert m["runway_movement_evidence"] is None


class TestTimestampSemanticsSeparation:
    """Verifies strict separation of observation, ingestion, and actual operational timestamps."""

    def test_timestamp_field_separation(self):
        res = client.get("/api/flights?limit=50")
        assert res.status_code == 200
        flights = res.json().get("flights", [])
        assert len(flights) > 0

        for f in flights:
            assert "source_observed_at" in f
            assert "ingested_at" in f
            assert "actual_timestamp" in f

            # Ingestion timestamp must NOT be placed into source_observed_at
            if f.get("ingested_at") and not f.get("raw_actual_dep_time") and not f.get("raw_actual_arr_time"):
                # If there's no raw feed timestamp, source_observed_at must be None, NOT equal to ingested_at
                assert f["source_observed_at"] is None or f["source_observed_at"] != f["ingested_at"], (
                    f"Event {f.get('event_id')} erroneously placed ingested_at into source_observed_at"
                )

    def test_actual_timestamp_provenance(self):
        res = client.get("/api/movements/verified?limit=20")
        assert res.status_code == 200
        for m in res.json().get("movements", []):
            expected_actual = m.get("actual_dep_time") if m.get("movement_type") == "departure" else m.get("actual_arr_time")
            assert m["actual_timestamp"] == expected_actual


class TestComparisonAndCodeshareCounting:
    """Verifies that comparison distinguishes operating flights and codeshares without double-counting."""

    def test_comparison_endpoint_fields(self):
        res = client.get("/api/movements/comparison?airport_id=DAM&start_date=2026-10-09&end_date=2026-10-10")
        assert res.status_code == 200
        data = res.json()
        assert "comparison" in data
        days = data["comparison"]
        assert len(days) == 2

        day_oct9 = days[0]
        assert day_oct9["flight_date"] == "2026-10-09"
        assert day_oct9["scheduled_record_count"] == 40
        assert day_oct9["commercial_operational_event_count"] == 51
        assert day_oct9["codeshare_record_count"] == 19
        assert day_oct9["unique_operating_flight_count"] == 51
        assert day_oct9["unique_event_count"] == 113

        # Matched vs ambiguous codeshare breakdown
        assert day_oct9["codeshare_matched_to_operating_flight"] == 17
        assert day_oct9["codeshare_ambiguous_or_unmatched"] == 2

        # Backward compatibility
        assert day_oct9["scheduled_count"] == 40
        assert day_oct9["commercially_reported_count"] == 51
        assert day_oct9["codeshare_count"] == 19
        assert day_oct9["total_events"] == 113

    def test_codeshares_not_added_to_operational_flight_totals(self):
        res = client.get("/api/movements/comparison?airport_id=DAM&start_date=2026-10-09&end_date=2026-10-09")
        assert res.status_code == 200
        day = res.json()["comparison"][0]

        # The unique operating flight count (51) must NOT add the 19 marketing codeshares
        assert day["unique_operating_flight_count"] == 51
        assert day["unique_operating_flight_count"] < (day["commercial_operational_event_count"] + day["codeshare_record_count"])
        assert "Marketing codeshares" in res.json()["warning"]


class TestHistoricalTimelineEndpoint:
    """Verifies the 34-month historical coverage timeline endpoint."""

    def test_timeline_endpoint_structure(self):
        res = client.get("/api/historical-coverage/timeline")
        assert res.status_code == 200
        data = res.json()
        assert data["total_months"] == 34
        timeline = data["timeline"]
        assert len(timeline) == 34

        for m in timeline:
            assert "source_period" in m
            assert "geographic_scope" in m
            assert "dataset_category" in m
            assert "evidence_level" in m
            assert "record_count" in m
            assert "explicit_warning" in m
            assert "is_dam_specific" in m

    def test_timeline_phases_and_category_semantics(self):
        res = client.get("/api/historical-coverage/timeline")
        timeline = {m["source_period"]: m for m in res.json()["timeline"]}

        # 2024-01 to 2024-10: regional_aggregate
        for month in ["2024-01", "2024-05", "2024-10"]:
            entry = timeline[month]
            assert entry["dataset_category"] == "regional_aggregate"
            assert "DAM_ALP_LTK" in entry["geographic_scope"]
            assert entry["is_dam_specific"] is False
            assert "zero DAM-specific" in entry["explicit_warning"]

        # 2024-11 to 2024-12: no_verified_dam_data
        for month in ["2024-11", "2024-12"]:
            entry = timeline[month]
            assert entry["dataset_category"] == "no_verified_dam_data"
            assert entry["record_count"] == 0
            assert "Platform historical data gap" in entry["explicit_warning"]
            assert "never zero flights" in entry["explicit_warning"]

        # 2025-01 to 2026-06: 18-month data gap
        for month in ["2025-01", "2025-06", "2026-01", "2026-06"]:
            entry = timeline[month]
            assert entry["dataset_category"] == "no_verified_dam_data"
            assert entry["record_count"] == 0
            assert "never zero flights" in entry["explicit_warning"]

        # 2026-07 to 2026-09: dam_scheduled_fids
        assert timeline["2026-07"]["dataset_category"] == "dam_scheduled_fids"
        assert timeline["2026-07"]["record_count"] == 956
        assert timeline["2026-08"]["record_count"] == 886
        assert timeline["2026-09"]["record_count"] == 140

        # 2026-10: live_regional_adsb
        assert timeline["2026-10"]["dataset_category"] == "live_regional_adsb"
        assert timeline["2026-10"]["record_count"] == 16


class TestExportMetadataAndSidecarJSON:
    """Verifies self-describing exports, sidecar JSON endpoint, and metadata schemas."""

    def test_export_sidecar_endpoint(self):
        datasets = ["damascus_flight_events", "historical_2024", "syrian_airports"]
        for ds in datasets:
            res = client.get(f"/api/export/{ds}/sidecar")
            assert res.status_code == 200
            assert "application/json" in res.headers["content-type"]
            assert "metadata.json" in res.headers["content-disposition"]
            meta = res.json()
            assert "dataset_name" in meta
            assert "geographic_scope" in meta
            assert "dataset_category" in meta
            assert "evidence_level" in meta
            assert "source_provenance" in meta
            assert "source_observation_period" in meta
            assert "generation_timestamp" in meta
            assert "known_limitations" in meta

    def test_export_metadata_endpoint_all_8_fields(self):
        res = client.get("/api/export/damascus_flight_events/metadata")
        assert res.status_code == 200
        meta = res.json()["metadata"]
        required_keys = [
            "dataset_name",
            "geographic_scope",
            "dataset_category",
            "evidence_level",
            "source_provenance",
            "source_observation_period",
            "generation_timestamp",
            "known_limitations",
        ]
        for key in required_keys:
            assert key in meta, f"Metadata key '{key}' missing from export metadata"

    def test_export_self_describing_embedded_metadata(self):
        # CSV with embedded metadata comment header
        res_csv = client.get("/api/export/damascus_flight_events?format=csv&include_metadata=true")
        assert res_csv.status_code == 200
        text = res_csv.text
        assert text.startswith("# METADATA\n# dataset_name:")
        assert "geographic_scope:" in text
        assert "known_limitations:" in text

        # JSON with enveloped metadata
        res_json = client.get("/api/export/damascus_flight_events?format=json&include_metadata=true")
        assert res_json.status_code == 200
        payload = res_json.json()
        assert "metadata" in payload
        assert "data" in payload
        assert payload["metadata"]["dataset_name"] == "Damascus International Airport Flight Events"


class TestDashboardTransparencyElements:
    """Verifies that static/index.html includes all required semantic boundaries and disclosures."""

    @pytest.fixture(scope="class")
    def html_content(self):
        html_path = Path("static/index.html")
        assert html_path.exists()
        return html_path.read_text(encoding="utf-8")

    def test_comparison_table_headers_and_disclaimer(self, html_content):
        assert "Unique Operating" in html_content
        assert "Codeshares (Matched / Ambiguous)" in html_content
        assert "Marketing codeshares represent partner listings" in html_content

    def test_timeline_month_by_month_browser_and_semantic_boundary(self, html_content):
        assert "timeline-month-tbody" in html_content
        assert "Expand Month-by-Month Verified Timeline" in html_content
        assert "Do not display regional aggregates, archived schedules, and live regional ADS-B samples as one continuous DAM movement series" in html_content
        assert "loadTimelineMonthByMonth" in html_content

    def test_export_sidecar_buttons_present(self, html_content):
        assert "/api/export/damascus_flight_events/sidecar" in html_content
        assert "/api/export/historical_2024/sidecar" in html_content
        assert "Sidecar JSON" in html_content


class TestProtectedAssetsImmutabilityV2201:
    """Verifies that all 6 protected assets remain strictly unmodified."""

    def test_six_protected_assets_hashes(self):
        for file_path, expected_hash in PROTECTED_HASHES.items():
            assert os.path.exists(file_path), f"Protected file missing: {file_path}"
            with open(file_path, "rb") as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            assert actual_hash == expected_hash, (
                f"HASH MISMATCH on protected file {file_path}! Expected {expected_hash}, got {actual_hash}"
            )
