"""
V2.20.12  Independent Movement Resolver & Metrics Audit Test Suite

Tests:
1. Equal timestamps with different event IDs.
2. Equal timestamps with conflicting registrations.
3. Missing registration on one or multiple observations (and conflict masking protection).
4. Different operating carriers.
5. Different flight numbers sharing the same registration.
6. Multiple legs using the same callsign on the same day.
7. Multiple observations with conflicting actual timestamps (60m-180m window).
8. Different local dates around midnight.
9. A-B-C transitive chains (diameter bounding).
10. Input permutations and deterministic output.
11. Cryptographic baseline integrity across all six protected assets.
12. Reconciliation of October 9 and October 10 metrics for DAM.
"""

import hashlib
import itertools
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import pytest
from fastapi.testclient import TestClient

from src.api import app
from src.timestamp_provenance import resolve_defensible_movement_identity

client = TestClient(app)
DAMASCUS_TZ = ZoneInfo("Asia/Damascus")

PROTECTED_ASSETS = {
    "data/damascus_airport.db": "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b",
    "data/archived_fids_staging.db": "a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4",
    "data/archived_fids_analytics.db": "e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe",
    "data/archived_fids_history_staging.db": "39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f",
    "data/raw/snapshots/wayback_damairport_fids_20260709234230.raw": "5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf",
    "data/raw/snapshots/wayback_damairport_fids_20260709234230.json": "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491",
}


class TestCryptographicBaselineIntegrityV22012:
    @pytest.mark.parametrize("filepath,expected_hash", PROTECTED_ASSETS.items())
    def test_protected_asset_sha256_hash(self, filepath, expected_hash):
        with open(filepath, "rb") as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
        assert actual_hash == expected_hash, (
            f"MUTATION DETECTED in protected asset {filepath}! "
            f"Expected {expected_hash}, got {actual_hash}"
        )


class TestIndependentResolverCasesV22012:
    """Independent verification of the 10 core resolver behavioral cases."""

    def test_case_1_equal_timestamps_different_event_ids(self):
        """Case 1: Equal timestamps with different event IDs merge deterministically."""
        records = [
            {"event_id": "ev_beta", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T10:00:00Z"},
            {"event_id": "ev_alpha", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T10:00:00Z"},
        ]
        res = resolve_defensible_movement_identity(records)
        assert res["resolved_commercial_movement_count"] == 1
        assert res["ambiguous_movement_identity_count"] == 0

    def test_case_2_equal_timestamps_conflicting_registrations(self):
        """Case 2: Equal timestamps with conflicting registrations -> ambiguous."""
        records = [
            {"event_id": "ev_1", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T10:00:00Z"},
            {"event_id": "ev_2", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKH", "actual_dep_time": "2026-10-10T10:00:00Z"},
        ]
        res = resolve_defensible_movement_identity(records)
        assert res["resolved_commercial_movement_count"] == 0
        assert res["ambiguous_movement_identity_count"] == 1

    def test_case_3_missing_registration_handling(self):
        """Case 3: Missing registration merges if consistent, but does not mask conflict."""
        # Subcase 3a: Both missing registrations merge safely
        c1 = [
            {"event_id": "ev_1", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": None, "actual_dep_time": "2026-10-10T10:00:00Z"},
            {"event_id": "ev_2", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": None, "actual_dep_time": "2026-10-10T10:15:00Z"},
        ]
        assert resolve_defensible_movement_identity(c1)["resolved_commercial_movement_count"] == 1

        # Subcase 3b: Missing registration does not mask conflict between two known airframes
        c2 = [
            {"event_id": "ev_1", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T10:00:00Z"},
            {"event_id": "ev_2", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": None, "actual_dep_time": "2026-10-10T10:10:00Z"},
            {"event_id": "ev_3", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKH", "actual_dep_time": "2026-10-10T10:20:00Z"},
        ]
        res2 = resolve_defensible_movement_identity(c2)
        assert res2["resolved_commercial_movement_count"] == 0
        assert res2["ambiguous_movement_identity_count"] == 1

    def test_case_4_different_operating_carriers(self):
        """Case 4: Conflicting operating carriers prevent merging."""
        records = [
            {"event_id": "ev_1", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "operating_carrier": "Cham Wings", "actual_dep_time": "2026-10-10T10:00:00Z"},
            {"event_id": "ev_2", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "operating_carrier": "Syrian Air", "actual_dep_time": "2026-10-10T10:15:00Z"},
        ]
        res = resolve_defensible_movement_identity(records)
        assert res["resolved_commercial_movement_count"] == 0
        assert res["ambiguous_movement_identity_count"] == 1

    def test_case_5_different_flight_numbers_same_registration(self):
        """Case 5: Different flight numbers sharing same registration resolve as distinct movements."""
        records = [
            {"event_id": "ev_1", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T10:00:00Z"},
            {"event_id": "ev_2", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB443", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T14:00:00Z"},
        ]
        res = resolve_defensible_movement_identity(records)
        assert res["resolved_commercial_movement_count"] == 2
        assert res["unique_operating_flight_count"] == 2
        assert res["ambiguous_movement_identity_count"] == 0

    def test_case_6_multiple_legs_same_callsign_same_day(self):
        """Case 6: Multiple legs using same callsign > 180m apart split into distinct legs."""
        records = [
            {"event_id": "ev_1", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T06:00:00Z"},
            {"event_id": "ev_2", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T18:00:00Z"},
        ]
        res = resolve_defensible_movement_identity(records)
        assert res["resolved_commercial_movement_count"] == 2
        assert res["unique_operating_flight_count"] == 1
        assert res["ambiguous_movement_identity_count"] == 0

    def test_case_7_conflicting_actual_timestamps_ambiguous_window(self):
        """Case 7: Observations with delta in 60m-180m window are flagged as ambiguous."""
        records = [
            {"event_id": "ev_1", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T10:00:00Z"},
            {"event_id": "ev_2", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T11:30:00Z"},
        ]
        res = resolve_defensible_movement_identity(records)
        assert res["resolved_commercial_movement_count"] == 0
        assert res["ambiguous_movement_identity_count"] == 1

    def test_case_8_different_local_dates_around_midnight(self):
        """Case 8: Movements around midnight resolve according to airport local timezone date."""
        # 20:30 UTC = 23:30 local on Oct 9; 21:30 UTC = 00:30 local on Oct 10
        records = [
            {"event_id": "ev_1", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-09T20:30:00Z"},
            {"event_id": "ev_2", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-09T21:30:00Z"},
        ]
        res = resolve_defensible_movement_identity(records)
        # Because local dates differ (2026-10-09 vs 2026-10-10), they form distinct operational partitions
        assert res["resolved_commercial_movement_count"] == 2
        assert res["ambiguous_movement_identity_count"] == 0

    def test_case_9_transitive_chains_diameter_bounding(self):
        """Case 9: A-B-C transitive chain (A-B=45m, B-C=30m, A-C=75m) is flagged ambiguous."""
        records = [
            {"event_id": "ev_1", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T10:00:00Z"},
            {"event_id": "ev_2", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T10:45:00Z"},
            {"event_id": "ev_3", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T11:15:00Z"},
        ]
        res = resolve_defensible_movement_identity(records)
        assert res["resolved_commercial_movement_count"] == 0
        assert res["ambiguous_movement_identity_count"] == 1

    def test_case_10_input_permutations_deterministic_output(self):
        """Case 10: All permutations of candidate list produce identical resolution results."""
        cands = [
            {"event_id": "ev_1", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T06:00:00Z"},
            {"event_id": "ev_2", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T06:20:00Z"},
            {"event_id": "ev_3", "record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T18:00:00Z"},
        ]
        baseline = resolve_defensible_movement_identity(cands)
        for p in itertools.permutations(cands):
            res = resolve_defensible_movement_identity(list(p))
            assert res == baseline
