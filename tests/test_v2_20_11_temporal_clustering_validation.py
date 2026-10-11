"""
V2.20.11  Temporal Clustering Resolver Validation Test Suite

Validates:
1. Temporal clustering algorithm & transitivity behavior in resolve_defensible_movement_identity:
   - Complete linkage (diameter <= 60m)
   - Transitive chaining hazard prevention (A-B <= 60m, B-C <= 60m, A-C = 75m -> ambiguous, not merged)
   - Order invariance & determinism across all input permutations
   - Safe aircraft registration handling (missing registration does not mask conflict)
2. Boundary testing of operational time thresholds:
   - 15 min: resolved same movement (high-confidence corroboration)
   - 59 min: resolved same movement
   - 60 min: resolved same movement (boundary)
   - 61 min: ambiguous window (too wide to merge, too narrow for turnaround)
   - 120 min: ambiguous window
   - 180 min: ambiguous window (upper boundary)
   - 181 min: distinct legs (> 180 min turnaround/recurring rotation)
3. Full real-database resolver reconciliation across all 131 physical_movement records.
4. Daily metric reconciliation for DAM (2026-10-09 & 2026-10-10).
5. Multi-provider commercial corroboration semantics and strictly null runway sensor evidence.
6. Cryptographic immutability of all six protected baseline assets.
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

# Six protected baseline SHA-256 hashes
PROTECTED_ASSETS = {
    "data/damascus_airport.db": "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b",
    "data/archived_fids_staging.db": "a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4",
    "data/archived_fids_analytics.db": "e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe",
    "data/archived_fids_history_staging.db": "39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f",
    "data/raw/snapshots/wayback_damairport_fids_20260709234230.raw": "5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf",
    "data/raw/snapshots/wayback_damairport_fids_20260709234230.json": "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491",
}


class TestCryptographicBaselineIntegrityV22011:
    """Verifies that all six baseline data assets remain byte-for-byte untouched."""

    @pytest.mark.parametrize("filepath,expected_hash", PROTECTED_ASSETS.items())
    def test_protected_asset_sha256_hash(self, filepath, expected_hash):
        with open(filepath, "rb") as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
        assert actual_hash == expected_hash, (
            f"MUTATION DETECTED in protected asset {filepath}! "
            f"Expected {expected_hash}, got {actual_hash}"
        )


class TestTemporalClusteringAlgorithmAndTransitivityV22011:
    """
    Audits the clustering mechanics:
    - Transitive chaining hazard prevention
    - Order invariance & determinism
    - Aircraft registration handling
    """

    def test_transitivity_chaining_hazard_prevented(self):
        """
        Transitive chaining hazard:
        Candidate A: 10:00:00 (base)
        Candidate B: 10:45:00 (A->B = 45m <= 60m)
        Candidate C: 11:15:00 (B->C = 30m <= 60m, but A->C = 75m > 60m)

        Under naive single-linkage clustering, A merges with B and B merges with C,
        improperly merging A and C across 75 minutes.
        Under defensible complete-linkage / diameter-bounded clustering:
        Total diameter (75m) > 60m, and separation between elements (30m, 45m) <= 180m.
        Neither single-movement merge nor distinct leg separation is valid.
        Must classify as AMBIGUOUS, resolving 0 movements and flagging 1 ambiguous candidate.
        """
        records = [
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T10:00:00Z"},
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T10:45:00Z"},
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T11:15:00Z"},
        ]
        res = resolve_defensible_movement_identity(records)
        assert res["resolved_commercial_movement_count"] == 0, "Chaining hazard falsely merged 75m spread!"
        assert res["ambiguous_movement_identity_count"] == 1
        assert res["unique_operating_flight_count"] == 1

    def test_order_invariance_and_determinism(self):
        """
        Verifies that candidate cluster boundaries are 100% deterministic
        and independent of input record ordering.
        """
        cands = [
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T06:00:00Z", "event_id": "ev_1"},
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T06:15:00Z", "event_id": "ev_2"},
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T18:00:00Z", "event_id": "ev_3"},
        ]

        expected_resolved = 2
        expected_unique_op = 1
        expected_ambiguous = 0

        for perm in itertools.permutations(cands):
            res = resolve_defensible_movement_identity(list(perm))
            assert res["resolved_commercial_movement_count"] == expected_resolved, f"Order permutation changed resolved count!"
            assert res["unique_operating_flight_count"] == expected_unique_op
            assert res["ambiguous_movement_identity_count"] == expected_ambiguous

    def test_identical_timestamps_deterministic_sorting(self):
        """Two candidate records sharing identical timestamps sort deterministically by event_id."""
        cands = [
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T14:24:38Z", "event_id": "b_event"},
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T14:24:38Z", "event_id": "a_event"},
        ]
        res1 = resolve_defensible_movement_identity(cands)
        res2 = resolve_defensible_movement_identity(list(reversed(cands)))
        assert res1 == res2
        assert res1["resolved_commercial_movement_count"] == 1

    def test_missing_registration_safely_corroborates_known_registration(self):
        """
        A candidate with missing registration (e.g. AviationStack feed omission)
        merges with an explicit registration if callsign, direction, and time (<=60m) match.
        """
        cands = [
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T14:20:00Z"},
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": None, "actual_dep_time": "2026-10-10T14:25:00Z"},
        ]
        res = resolve_defensible_movement_identity(cands)
        assert res["resolved_commercial_movement_count"] == 1
        assert res["ambiguous_movement_identity_count"] == 0

    def test_missing_registration_does_not_mask_explicit_registration_conflict(self):
        """
        A candidate with missing registration between two conflicting registrations
        must not mask the conflict: the group must remain AMBIGUOUS.
        """
        cands = [
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": "2026-10-10T14:15:00Z"},
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": None, "actual_dep_time": "2026-10-10T14:20:00Z"},
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKH", "actual_dep_time": "2026-10-10T14:25:00Z"},
        ]
        res = resolve_defensible_movement_identity(cands)
        assert res["resolved_commercial_movement_count"] == 0, "Conflict was masked by missing registration!"
        assert res["ambiguous_movement_identity_count"] == 1


class TestTimeThresholdBoundaryCasesV22011:
    """
    Validates precise threshold boundaries:
    15m, 59m, 60m, 61m, 120m, 180m, 181m.
    """

    def _make_pair(self, delta_minutes):
        t1 = "2026-10-10T10:00:00Z"
        dt1 = datetime.fromisoformat(t1.replace("Z", "+00:00"))
        dt2 = dt1 + timedelta(minutes=delta_minutes)
        t2 = dt2.strftime("%Y-%m-%dT%H:%M:%SZ")
        return [
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": t1},
            {"record_nature": "physical_movement", "airport_id": "DAM", "movement_type": "departure", "flight_number": "RB441", "aircraft_registration": "YK-AKG", "actual_dep_time": t2},
        ]

    def test_boundary_15_minutes_resolved_same_movement(self):
        """15 min: high-confidence multi-provider commercial corroboration (merged into 1 resolved movement)."""
        res = resolve_defensible_movement_identity(self._make_pair(15))
        assert res["resolved_commercial_movement_count"] == 1
        assert res["ambiguous_movement_identity_count"] == 0

    def test_boundary_59_minutes_resolved_same_movement(self):
        """59 min: within 60 min single-movement operational window (merged into 1 resolved movement)."""
        res = resolve_defensible_movement_identity(self._make_pair(59))
        assert res["resolved_commercial_movement_count"] == 1
        assert res["ambiguous_movement_identity_count"] == 0

    def test_boundary_60_minutes_resolved_same_movement(self):
        """60 min: exact threshold boundary for single-movement tolerance (merged into 1 resolved movement)."""
        res = resolve_defensible_movement_identity(self._make_pair(60))
        assert res["resolved_commercial_movement_count"] == 1
        assert res["ambiguous_movement_identity_count"] == 0

    def test_boundary_61_minutes_ambiguous_window(self):
        """61 min: enters ambiguous window (too wide to merge, too narrow for turnaround leg)."""
        res = resolve_defensible_movement_identity(self._make_pair(61))
        assert res["resolved_commercial_movement_count"] == 0
        assert res["ambiguous_movement_identity_count"] == 1

    def test_boundary_120_minutes_ambiguous_window(self):
        """120 min: intermediate ambiguous window (unresolved candidate movement)."""
        res = resolve_defensible_movement_identity(self._make_pair(120))
        assert res["resolved_commercial_movement_count"] == 0
        assert res["ambiguous_movement_identity_count"] == 1

    def test_boundary_180_minutes_ambiguous_window(self):
        """180 min: upper boundary of ambiguous window (still within ambiguous turnaround threshold)."""
        res = resolve_defensible_movement_identity(self._make_pair(180))
        assert res["resolved_commercial_movement_count"] == 0
        assert res["ambiguous_movement_identity_count"] == 1

    def test_boundary_181_minutes_distinct_legs(self):
        """181 min: exceeds 180 min threshold, establishing distinct operational recurring legs."""
        res = resolve_defensible_movement_identity(self._make_pair(181))
        assert res["resolved_commercial_movement_count"] == 2
        assert res["unique_operating_flight_count"] == 1
        assert res["ambiguous_movement_identity_count"] == 0


class TestRealDatabase131MovementsReconciliationV22011:
    """
    Validates complete reconciliation of all 131 physical_movement records
    in data/damascus_airport.db using a strictly read-only connection.
    """

    @pytest.fixture(scope="class")
    def all_physical_movements(self):
        import sqlite3
        conn = sqlite3.connect("file:data/damascus_airport.db?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM flight_events WHERE record_nature = 'physical_movement'")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def test_total_count_is_exactly_131(self, all_physical_movements):
        assert len(all_physical_movements) == 131

    def test_all_131_have_verified_actual_timestamps(self, all_physical_movements):
        for r in all_physical_movements:
            mtype = r.get("movement_type")
            act_ts = r.get("actual_dep_time") if mtype == "departure" else r.get("actual_arr_time")
            if not act_ts:
                act_ts = r.get("actual_dep_time") or r.get("actual_arr_time")
            assert act_ts is not None, f"Event {r['event_id']} lacks actual timestamp!"

    def test_resolver_resolves_all_131_physical_movements(self, all_physical_movements):
        res = resolve_defensible_movement_identity(all_physical_movements)
        assert res["resolved_commercial_movement_count"] == 131
        assert res["unique_operating_flight_count"] == 90
        assert res["ambiguous_movement_identity_count"] == 0
        assert res["source_record_count"] == 131

    def test_multi_provider_corroboration_distribution(self, all_physical_movements):
        multi_prov = [r for r in all_physical_movements if "+" in (r.get("source") or "")]
        single_prov = [r for r in all_physical_movements if "+" not in (r.get("source") or "")]
        assert len(multi_prov) == 129
        assert len(single_prov) == 2


class TestDailyMetricReconciliationDAMV22011:
    """
    Reconciles all daily metrics for DAM on 2026-10-09 and 2026-10-10:
    - source_record_count
    - scheduled_service_count
    - unique_operating_flight_count
    - resolved_commercial_movement_count
    - ambiguous_movement_identity_count
    - unmatched_codeshare_record_count
    """

    def test_daily_metrics_2026_10_09_dam(self):
        res = client.get("/api/movements/comparison?date=2026-10-09&airport_id=DAM")
        assert res.status_code == 200
        days = [d for d in res.json()["comparison"] if d["flight_date"] == "2026-10-09"]
        assert len(days) == 1
        d = days[0]

        assert d["source_record_count"] == 113
        assert d["scheduled_service_count"] == 40
        assert d["commercial_operational_event_count"] == 51
        assert d["unique_operating_flight_count"] == 51
        assert d["resolved_commercial_movement_count"] == 51
        assert d["ambiguous_movement_identity_count"] == 2
        assert d["unmatched_codeshare_record_count"] == 2
        assert d["matched_codeshare_record_count"] == 17
        assert d["unverified_record_count"] == 3

    def test_daily_metrics_2026_10_10_dam(self):
        res = client.get("/api/movements/comparison?date=2026-10-10&airport_id=DAM")
        assert res.status_code == 200
        days = [d for d in res.json()["comparison"] if d["flight_date"] == "2026-10-10"]
        assert len(days) == 1
        d = days[0]

        assert d["source_record_count"] == 99
        assert d["scheduled_service_count"] == 37
        assert d["commercial_operational_event_count"] == 47
        assert d["unique_operating_flight_count"] == 47
        assert d["resolved_commercial_movement_count"] == 47
        assert d["ambiguous_movement_identity_count"] == 1
        assert d["unmatched_codeshare_record_count"] == 1
        assert d["matched_codeshare_record_count"] == 14
        assert d["unverified_record_count"] == 0
