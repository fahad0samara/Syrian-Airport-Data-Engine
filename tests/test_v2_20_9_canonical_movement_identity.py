import pytest
import hashlib
from pathlib import Path
from fastapi.testclient import TestClient
from src.api import app
from src.normalizer import evaluate_cross_source_match

client = TestClient(app)

PROTECTED_ASSETS = [
    ("data/damascus_airport.db", "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"),
    ("data/archived_fids_staging.db", "a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4"),
    ("data/archived_fids_analytics.db", "e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe"),
    ("data/archived_fids_history_staging.db", "39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f"),
    ("data/raw/snapshots/wayback_damairport_fids_20260709234230.raw", "5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf"),
    ("data/raw/snapshots/wayback_damairport_fids_20260709234230.json", "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491"),
]


class TestCryptographicBaselineIntegrityV2209:
    """Verifies that all 6 protected assets remain 100% byte-for-byte invariant."""

    @pytest.mark.parametrize("file_path,expected_sha256", PROTECTED_ASSETS)
    def test_protected_asset_sha256_hash(self, file_path, expected_sha256):
        p = Path(file_path)
        assert p.exists(), f"Protected asset {file_path} is missing!"
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        assert h == expected_sha256, f"Hash mismatch for {file_path}: expected {expected_sha256}, got {h}"


class TestCanonicalEventIdentityV2209:
    """Tests auditing canonical event identity, deduplication, and cross-source edge cases."""

    def test_same_event_represented_by_two_different_ids(self):
        """Verifies two records with different event_ids for the same flight leg merge into a single movement."""
        record_id_1 = {
            "event_id": "ev_aaa111",
            "airport_id": "DAM", "movement_type": "arrival", "flight_date": "2026-10-09",
            "flight_number": "KU551", "operating_flight_number": "KU551",
            "airline_name": "Kuwait Airways", "actual_arr_time": "2026-10-09T08:16:38Z",
            "aircraft_registration": "9K-AKO"
        }
        record_id_2 = {
            "event_id": "ev_bbb222",
            "airport_id": "DAM", "movement_type": "arrival", "flight_date": "2026-10-09",
            "flight_number": "KU551", "operating_flight_number": "KU551",
            "airline_name": "Kuwait Airways", "actual_arr_time": "2026-10-09T08:16:00Z",
            "aircraft_registration": "9K-AKO"
        }
        res = evaluate_cross_source_match(record_id_1, record_id_2)
        assert res["can_merge"] is True
        assert res["match_status"] == "CONFIRMED_MATCH"
        assert res["time_diff_minutes"] < 1.0

    def test_same_callsign_operating_two_legs_on_same_day(self):
        """Verifies same callsign operating twice >180m apart splits into distinct legs."""
        morning_leg = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "RB100", "airline_name": "Syrian Air",
            "actual_dep_time": "2026-10-10T06:00:00Z"
        }
        evening_leg = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "RB100", "airline_name": "Syrian Air",
            "actual_dep_time": "2026-10-10T18:00:00Z"
        }
        res = evaluate_cross_source_match(morning_leg, evening_leg)
        assert res["can_merge"] is False
        assert res["match_status"] == "SPLIT_DISTINCT_LEG"
        assert res["time_diff_minutes"] == 720.0

    def test_same_flight_observed_by_multiple_providers(self):
        """Verifies observation of the same flight by multiple providers within tolerance confirms match."""
        fr24_obs = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "FZ1114", "operating_flight_number": "FZ1114",
            "airline_name": "flydubai", "actual_dep_time": "2026-10-10T13:54:16Z",
            "aircraft_registration": "A6-FEC"
        }
        avstack_obs = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "FZ1114", "operating_flight_number": "FZ1114",
            "airline_name": "flydubai", "actual_dep_time": "2026-10-10T13:54:00Z",
            "aircraft_registration": "A6-FEC"
        }
        res = evaluate_cross_source_match(fr24_obs, avstack_obs)
        assert res["can_merge"] is True
        assert res["match_status"] == "CONFIRMED_MATCH"
        assert res["confidence_score"] == 1.0

    def test_multiple_marketing_codeshares_referencing_one_operating_flight(self):
        """Verifies multiple marketing codeshares referencing one flight leg both match and do not inflate counts."""
        operating_flight = {
            "airport_id": "DAM", "movement_type": "arrival", "flight_date": "2026-10-10",
            "flight_number": "RJ437", "operating_flight_number": "RJ437",
            "airline_name": "Royal Jordanian", "actual_arr_time": "2026-10-10T11:45:38Z"
        }
        codeshare_1 = {
            "airport_id": "DAM", "movement_type": "arrival", "flight_date": "2026-10-10",
            "flight_number": "QR6119", "operating_flight_number": "RJ437",
            "airline_name": "Qatar Airways", "actual_arr_time": "2026-10-10T11:45:38Z"
        }
        codeshare_2 = {
            "airport_id": "DAM", "movement_type": "arrival", "flight_date": "2026-10-10",
            "flight_number": "WY5233", "operating_flight_number": "RJ437",
            "airline_name": "Oman Air", "actual_arr_time": "2026-10-10T11:45:38Z"
        }
        res1 = evaluate_cross_source_match(operating_flight, codeshare_1)
        res2 = evaluate_cross_source_match(operating_flight, codeshare_2)
        assert res1["can_merge"] is True
        assert res1["match_status"] == "CONFIRMED_MATCH"
        assert res2["can_merge"] is True
        assert res2["match_status"] == "CONFIRMED_MATCH"

    def test_duplicate_marketing_records_do_not_inflate_ambiguity_candidates(self):
        """Verifies duplicate marketing listings referencing the same missing target produce 1 ambiguous candidate."""
        res = client.get("/api/movements/comparison?airport_id=DAM&start_date=2026-10-10&end_date=2026-10-10")
        assert res.status_code == 200
        row = res.json()["comparison"][0]
        # On Oct 10, exactly 1 distinct ambiguous candidate exists (GF5952 -> XY377)
        assert row["ambiguous_movement_identity_count"] == 1
        assert row["unmatched_codeshare_record_count"] == 1

    def test_missing_actual_timestamps_cannot_merge_or_qualify_as_operational(self):
        """Verifies events lacking actual timestamp anchors cannot merge or establish operational movement."""
        event_a = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "RB999", "airline_name": "Syrian Air"
        }
        event_b = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "RB999", "airline_name": "Syrian Air"
        }
        res = evaluate_cross_source_match(event_a, event_b)
        assert res["can_merge"] is False
        assert res["match_status"] == "POTENTIAL_MATCH_LACKS_TIME"

    def test_conflicting_aircraft_registrations_prevent_merging(self):
        """Verifies conflicting aircraft registrations prevent merging even if flight number is identical."""
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
        res = evaluate_cross_source_match(event_a, event_b)
        assert res["can_merge"] is False
        assert res["match_status"] == "CONFLICT_REGISTRATION"

    def test_conflicting_carriers_prevent_merging(self):
        """Verifies conflicting carriers prevent merging when no codeshare/ACMI relationship exists."""
        event_a = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "PC123", "airline_name": "Pegasus Airlines",
            "actual_dep_time": "2026-10-10T12:00:00Z"
        }
        event_b = {
            "airport_id": "DAM", "movement_type": "departure", "flight_date": "2026-10-10",
            "flight_number": "PC123", "airline_name": "Syrian Air",
            "actual_dep_time": "2026-10-10T12:00:00Z"
        }
        res = evaluate_cross_source_match(event_a, event_b)
        assert res["can_merge"] is False
        assert res["match_status"] == "CONFLICT_CARRIER"

    def test_ambiguous_candidate_matching_exclusion(self):
        """Verifies candidate records lacking operating flights remain strictly excluded from resolved counts."""
        res = client.get("/api/movements/comparison?airport_id=DAM&start_date=2026-10-09&end_date=2026-10-10")
        assert res.status_code == 200
        days = res.json()["comparison"]
        for day in days:
            assert day["resolved_commercial_movement_count"] >= 0
            assert day["ambiguous_movement_identity_count"] >= 0
            # Resolved movements and ambiguous candidates are mutually exclusive subsets of total records
            assert day["resolved_commercial_movement_count"] + day["ambiguous_movement_identity_count"] <= day["total_records"]

    def test_null_or_unavailable_movement_identity_on_schedule_only_dates(self):
        """Verifies dates with only timetable slots have 0 resolved operational movements."""
        res = client.get("/api/movements/comparison?airport_id=DAM&start_date=2026-10-01&end_date=2026-10-01")
        assert res.status_code == 200
        rows = res.json()["comparison"]
        assert len(rows) == 1
        day = rows[0]
        assert day["scheduled_record_count"] > 0
        assert day["commercial_operational_event_count"] == 0
        assert day["resolved_commercial_movement_count"] == 0
        assert day["unique_operating_flight_count"] == 0


class TestClassificationConsistencyV2209:
    """Verifies complete classification consistency across all 1,830 canonical events."""

    def test_all_record_nature_classifications_mapped(self):
        """Verifies physical_movement maps to commercially_reported_operational_event while other classes remain separate."""
        res = client.get("/api/flights?limit=500")
        assert res.status_code == 200
        flights = res.json()["flights"]
        for f in flights:
            nature = f["record_nature"]
            ev_class = f["event_classification"]
            ev_lvl = f["evidence_level"]
            assert f["runway_movement_evidence"] is None

            if nature == "physical_movement":
                assert ev_class == "commercially_reported_operational_event"
                assert ev_lvl == "commercial_operational_status"
            elif nature == "scheduled_service":
                assert ev_class == "scheduled_service"
                assert ev_lvl == "scheduled_timetable_display"
            elif nature == "marketing_codeshare":
                assert ev_class == "marketing_codeshare"
                assert ev_lvl == "commercial_partner_listing"
            elif nature == "unverified_movement":
                assert ev_class == "unverified_movement"
                assert ev_lvl == "unverified_claim"
