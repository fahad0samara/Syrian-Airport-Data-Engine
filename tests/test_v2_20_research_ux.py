"""
Tests for Version 2.20 Research Product UX & Evidence Transparency.

Covers:
1. Movement terminology updates, aliases, and backward compatibility.
2. Record-level evidence transparency fields (all 9 fields exposed).
3. Null handling and evidence classifications.
4. Scheduled vs. commercially reported comparison endpoint.
5. Export research metadata headers and metadata endpoint.
6. Geographic scope enforcement and regional aggregate separation.
7. Dashboard research UX elements in static/index.html.
8. Cryptographic immutability of the six protected assets.
"""

import hashlib
import os
import re
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

EXPECTED_TRANSPARENCY_FIELDS = [
    "geographic_scope",
    "record_nature",
    "evidence_level",
    "provider_count",
    "independent_observation_count",
    "runway_movement_evidence",
    "source_timestamp",
    "actual_timestamp",
    "source_snapshot",
]


class TestMovementTerminologyAndAliases:
    """Verifies terminology updates, aliases, and backward compatibility."""

    def test_movements_verified_endpoint_and_aliases(self):
        endpoints = [
            "/api/movements/verified",
            "/api/movements/operational",
            "/api/movements/commercially-reported",
        ]
        responses = [client.get(ep) for ep in endpoints]

        for res in responses:
            assert res.status_code == 200
            data = res.json()
            # Backward compatibility
            assert "record_nature" in data
            assert data["record_nature"] == "physical_movement"
            assert "total" in data
            assert "movements" in data
            assert "data" in data
            # New V2.20 clarity fields
            assert data.get("event_classification") == "commercially_reported_operational_event"
            assert "description" in data
            assert "commercially reported" in data["description"].lower()
            assert "runway" in data["description"].lower()

        # All 3 endpoints must return identical total and record counts
        counts = [r.json()["total"] for r in responses]
        assert counts[0] == counts[1] == counts[2]

    def test_verified_terminology_preserves_database_values(self):
        res = client.get("/api/movements/verified?limit=10")
        assert res.status_code == 200
        data = res.json()
        assert len(data["movements"]) > 0
        for m in data["movements"]:
            assert m["record_nature"] == "physical_movement"


class TestEvidenceTransparencyFields:
    """Verifies that all 9 transparency fields are exposed and properly populated."""

    def test_all_transparency_fields_present_in_flights(self):
        res = client.get("/api/flights?limit=25")
        assert res.status_code == 200
        flights = res.json().get("flights", [])
        assert len(flights) > 0

        for f in flights:
            for field in EXPECTED_TRANSPARENCY_FIELDS:
                assert field in f, f"Field '{field}' missing from flight record {f.get('event_id')}"

    def test_all_transparency_fields_present_in_movements(self):
        res = client.get("/api/movements/verified?limit=25")
        assert res.status_code == 200
        movements = res.json().get("movements", [])
        assert len(movements) > 0

        for m in movements:
            for field in EXPECTED_TRANSPARENCY_FIELDS:
                assert field in m, f"Field '{field}' missing from movement record {m.get('event_id')}"

    def test_runway_movement_evidence_strictly_null(self):
        res = client.get("/api/movements/verified?limit=50")
        assert res.status_code == 200
        for m in res.json().get("movements", []):
            assert m["runway_movement_evidence"] is None, (
                f"runway_movement_evidence must be None/null, got {m['runway_movement_evidence']}"
            )

    def test_evidence_level_classification_values(self):
        res = client.get("/api/flights?limit=100")
        assert res.status_code == 200
        valid_levels = {
            "commercial_status_corroborated",
            "scheduled_timetable_display",
            "commercial_partner_listing",
            "unverified_claim",
            "unknown",
        }
        for f in res.json().get("flights", []):
            assert f["evidence_level"] in valid_levels, (
                f"Invalid evidence_level '{f['evidence_level']}' in event {f.get('event_id')}"
            )

    def test_evidence_level_filter(self):
        res = client.get("/api/flights?evidence_level=commercial_status_corroborated&limit=50")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] > 0
        for f in data["flights"]:
            assert f["record_nature"] == "physical_movement"
            assert f["evidence_level"] == "commercial_status_corroborated"

    def test_date_range_filter(self):
        res = client.get("/api/flights?start_date=2026-10-01&end_date=2026-10-05&limit=50")
        assert res.status_code == 200
        flights = res.json().get("flights", [])
        for f in flights:
            assert "2026-10-01" <= f["flight_date"] <= "2026-10-05"


class TestScheduledVsCommercialComparison:
    """Verifies the comparison endpoint between scheduled slots and commercial operational events."""

    def test_movements_comparison_endpoint(self):
        res = client.get("/api/movements/comparison?airport_id=DAM")
        assert res.status_code == 200
        data = res.json()
        assert data["airport_id"] == "DAM"
        assert "comparison" in data
        assert "warning" in data
        assert "commercially reported" in data["warning"].lower()

        assert len(data["comparison"]) > 0
        day = data["comparison"][0]
        assert "flight_date" in day
        assert "commercially_reported_count" in day
        assert "scheduled_count" in day
        assert "codeshare_count" in day
        assert "unverified_count" in day
        assert "total_events" in day

    def test_movements_comparison_date_filtering(self):
        res = client.get("/api/movements/comparison?airport_id=DAM&start_date=2026-10-01&end_date=2026-10-03")
        assert res.status_code == 200
        days = res.json()["comparison"]
        for d in days:
            assert "2026-10-01" <= d["flight_date"] <= "2026-10-03"


class TestExportResearchMetadata:
    """Verifies research metadata headers and the export metadata endpoint."""

    def test_export_headers_csv_and_json(self):
        datasets_to_test = ["damascus_flight_events", "historical_2024", "syrian_airports"]
        for ds in datasets_to_test:
            res_csv = client.get(f"/api/export/{ds}?format=csv")
            assert res_csv.status_code == 200
            assert "x-dataset-scope" in res_csv.headers
            assert "x-dataset-category" in res_csv.headers
            assert "x-evidence-level" in res_csv.headers
            assert "x-source-provenance" in res_csv.headers
            assert "x-generated-at" in res_csv.headers

            res_json = client.get(f"/api/export/{ds}?format=json")
            assert res_json.status_code == 200
            assert "x-dataset-scope" in res_json.headers

    def test_export_metadata_endpoint(self):
        res = client.get("/api/export/damascus_flight_events/metadata")
        assert res.status_code == 200
        data = res.json()
        assert data["dataset_key"] == "damascus_flight_events"
        assert "metadata" in data
        meta = data["metadata"]
        assert "scope" in meta
        assert "category" in meta
        assert "evidence_level" in meta
        assert "provenance" in meta

    def test_export_unknown_dataset_404(self):
        res = client.get("/api/export/non_existent_dataset?format=csv")
        assert res.status_code == 404

        res_meta = client.get("/api/export/non_existent_dataset/metadata")
        assert res_meta.status_code == 404


class TestGeographicScopeAndAggregateSeparation:
    """Verifies that regional aggregates are strictly isolated from single-airport outputs."""

    def test_multi_airport_2024_scope_invariants(self):
        res = client.get("/api/movements/multi-airport")
        assert res.status_code == 200
        data = res.json()
        assert data["scope"] == "DAM_ALP_LTK"
        assert data["is_dam_specific"] is False
        assert set(data["included_airports"]) == {"DAM", "ALP", "LTK"}
        assert "three-airport aggregate" in data["warning"].lower()

    def test_historical_daily_movements_2024_export_metadata(self):
        res = client.get("/api/export/historical_2024/metadata")
        assert res.status_code == 200
        meta = res.json()["metadata"]
        assert "DAM_ALP_LTK" in meta["scope"]
        assert meta["category"] == "regional_aggregate"


class TestDashboardUsabilityElements:
    """Verifies that static/index.html implements required V2.20 research controls and transparency."""

    @pytest.fixture(scope="class")
    def html_content(self):
        html_path = Path("static/index.html")
        assert html_path.exists()
        return html_path.read_text(encoding="utf-8")

    def test_airport_selector_has_all_registered_airports(self, html_content):
        for code in ["DAM", "ALP", "DEZ", "LTK", "KAC"]:
            assert f'value="{code}"' in html_content, f"Airport {code} missing from dashboard selector"

    def test_filter_controls_present(self, html_content):
        assert 'id="flight-start-date"' in html_content
        assert 'id="flight-end-date"' in html_content
        assert 'id="flight-evidence-level"' in html_content
        assert 'id="flight-nature"' in html_content

    def test_comparison_panel_present(self, html_content):
        assert 'id="comparison-table-body"' in html_content
        assert "Scheduled vs Commercially Reported Comparison" in html_content
        assert "loadComparison" in html_content

    def test_historical_coverage_timeline_present(self, html_content):
        assert "Historical Coverage Timeline" in html_content
        assert "34-month audit window" in html_content.lower()
        assert "no_verified_dam_data" in html_content

    def test_no_misleading_radar_verified_movement_claims(self, html_content):
        # Must not claim radar verified movements in UI cards
        assert "Physical Movement (Radar Verified)" not in html_content
        assert "Commercially Reported Operational Events" in html_content


class TestCryptographicIntegrityOfProtectedAssets:
    """Verifies that all 6 protected assets remain strictly unmodified."""

    def test_six_protected_assets_hashes(self):
        for file_path, expected_hash in PROTECTED_HASHES.items():
            assert os.path.exists(file_path), f"Protected file missing: {file_path}"
            with open(file_path, "rb") as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            assert actual_hash == expected_hash, (
                f"HASH MISMATCH on protected file {file_path}! Expected {expected_hash}, got {actual_hash}"
            )
