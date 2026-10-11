import pytest
import hashlib
from pathlib import Path
from fastapi.testclient import TestClient
from src.api import app
from src.timestamp_provenance import resolve_defensible_movement_identity

client = TestClient(app)

PROTECTED_ASSETS = [
    ("data/damascus_airport.db", "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"),
    ("data/archived_fids_staging.db", "a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4"),
    ("data/archived_fids_analytics.db", "e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe"),
    ("data/archived_fids_history_staging.db", "39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f"),
    ("data/raw/snapshots/wayback_damairport_fids_20260709234230.raw", "5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf"),
    ("data/raw/snapshots/wayback_damairport_fids_20260709234230.json", "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491"),
]


class TestCryptographicBaselineIntegrityV22010:
    """Verifies that all 6 protected baseline assets remain 100% byte-for-byte invariant."""

    @pytest.mark.parametrize("file_path,expected_sha256", PROTECTED_ASSETS)
    def test_protected_asset_sha256_hash(self, file_path, expected_sha256):
        p = Path(file_path)
        assert p.exists(), f"Protected asset {file_path} is missing!"
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        assert h == expected_sha256, f"Hash mismatch for {file_path}: expected {expected_sha256}, got {h}"


class TestMovementLegIdentityResolverV22010:
    """Tests the 10 synthetic regression cases for multi-factor movement leg identity resolution."""

    def test_1_same_callsign_same_airport_same_date_same_direction_two_timestamps_12h_apart(self):
        """Case 1: Same callsign, airport, date, direction, two actual timestamps 12h apart -> count 2."""
        c = [
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB100", "actual_dep_time": "2026-10-10T06:00:00Z"},
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB100", "actual_dep_time": "2026-10-10T18:00:00Z"},
        ]
        res = resolve_defensible_movement_identity(c)
        assert res["resolved_commercial_movement_count"] == 2
        assert res["unique_operating_flight_count"] == 1

    def test_2_same_movement_observed_by_multiple_providers_within_seconds(self):
        """Case 2: Same movement observed by FR24 and AviationStack within seconds -> count 1."""
        c = [
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "FZ1114", "aircraft_registration": "A6-FEC", "actual_dep_time": "2026-10-10T13:54:16Z"},
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "FZ1114", "aircraft_registration": "A6-FEC", "actual_dep_time": "2026-10-10T13:54:00Z"},
        ]
        res = resolve_defensible_movement_identity(c)
        assert res["resolved_commercial_movement_count"] == 1
        assert res["unique_operating_flight_count"] == 1

    def test_3_same_callsign_with_different_registrations_and_different_timestamps(self):
        """Case 3: Same callsign with different aircraft registrations and clearly different actual timestamps -> count 2."""
        c = [
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB100", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T06:00:00Z"},
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB100", "aircraft_registration": "YK-AKH", "actual_dep_time": "2026-10-10T18:00:00Z"},
        ]
        res = resolve_defensible_movement_identity(c)
        assert res["resolved_commercial_movement_count"] == 2
        assert res["unique_operating_flight_count"] == 1

    def test_4_same_callsign_with_conflicting_registrations_and_overlapping_timestamps(self):
        """Case 4: Same callsign with conflicting registrations and overlapping timestamps -> ambiguous, not merged."""
        c = [
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T14:24:38Z"},
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKH", "actual_dep_time": "2026-10-10T14:24:38Z"},
        ]
        res = resolve_defensible_movement_identity(c)
        assert res["resolved_commercial_movement_count"] == 0
        assert res["ambiguous_movement_identity_count"] == 1

    def test_5_same_callsign_with_missing_actual_timestamps(self):
        """Case 5: Same callsign with missing actual timestamps -> identity unresolved."""
        c = [
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB999", "actual_dep_time": None},
        ]
        res = resolve_defensible_movement_identity(c)
        assert res["resolved_commercial_movement_count"] == 0
        assert res["ambiguous_movement_identity_count"] == 1

    def test_6_same_scheduled_flight_listed_by_two_providers(self):
        """Case 6: Same scheduled flight listed by two providers -> scheduled service, not physical movement."""
        c = [
            {"record_nature": "scheduled_service", "airport_id": "DAM", "movement_type": "arrival", "flight_number": "KU551"},
            {"record_nature": "scheduled_service", "airport_id": "DAM", "movement_type": "arrival", "flight_number": "KU551"},
        ]
        res = resolve_defensible_movement_identity(c)
        assert res["resolved_commercial_movement_count"] == 0
        assert res["scheduled_service_count"] == 2

    def test_7_multiple_codeshares_pointing_to_one_operating_movement(self):
        """Case 7: Multiple codeshares pointing to one operating movement -> one movement."""
        c = [
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "arrival", "flight_number": "RJ437", "actual_arr_time": "2026-10-10T11:45:38Z"},
            {"record_nature": "marketing_codeshare", "airport_id": "DAM", "movement_type": "arrival", "flight_number": "QR6119", "operating_flight_number": "RJ437", "flight_date": "2026-10-10"},
            {"record_nature": "marketing_codeshare", "airport_id": "DAM", "movement_type": "arrival", "flight_number": "WY5233", "operating_flight_number": "RJ437", "flight_date": "2026-10-10"},
        ]
        res = resolve_defensible_movement_identity(c)
        assert res["resolved_commercial_movement_count"] == 1
        assert res["matched_codeshare_record_count"] == 2

    def test_8_two_different_operating_callsigns(self):
        """Case 8: Two different operating callsigns -> separate candidates."""
        c = [
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "actual_dep_time": "2026-10-10T14:24:38Z"},
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "FZ1114", "actual_dep_time": "2026-10-10T13:54:16Z"},
        ]
        res = resolve_defensible_movement_identity(c)
        assert res["resolved_commercial_movement_count"] == 2
        assert res["unique_operating_flight_count"] == 2

    def test_9_same_callsign_on_different_local_dates(self):
        """Case 9: Same callsign on different local dates -> separate legs."""
        c = [
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "arrival", "flight_number": "RJ437", "actual_arr_time": "2026-10-09T11:45:38Z"},
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "arrival", "flight_number": "RJ437", "actual_arr_time": "2026-10-10T11:45:38Z"},
        ]
        res = resolve_defensible_movement_identity(c)
        assert res["resolved_commercial_movement_count"] == 2

    def test_10_movement_whose_scheduled_date_differs_from_actual_local_date(self):
        """Case 10: Movement whose scheduled date differs from actual local movement date."""
        c = [
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "FYC743", "flight_date": "2026-10-09", "actual_dep_time": "2026-10-09T21:15:00Z"},
        ]
        res = resolve_defensible_movement_identity(c)
        assert res["resolved_commercial_movement_count"] == 1


class TestApiMetricSeparationV22010:
    """Verifies that the /api/movements/comparison endpoint exposes clearly separated metrics."""

    def test_comparison_endpoint_has_all_separated_metrics(self):
        """Verifies presence of scheduled_service_count, source_record_count, and distinct movement counts."""
        res = client.get("/api/movements/comparison?airport_id=DAM&start_date=2026-10-10&end_date=2026-10-10")
        assert res.status_code == 200
        data = res.json()
        assert len(data["comparison"]) == 1
        row = data["comparison"][0]

        assert "unique_operating_flight_count" in row
        assert "resolved_commercial_movement_count" in row
        assert "ambiguous_movement_identity_count" in row
        assert "scheduled_service_count" in row
        assert "source_record_count" in row

        assert row["unique_operating_flight_count"] == 47
        assert row["resolved_commercial_movement_count"] == 47
        assert row["ambiguous_movement_identity_count"] == 1
        assert row["scheduled_service_count"] == 37
        assert row["source_record_count"] == 99

        defs = data["field_definitions"]
        assert "scheduled_service_count" in defs
        assert "source_record_count" in defs
        assert "resolved_commercial_movement_count" in defs
        assert "unique_operating_flight_count" in defs
