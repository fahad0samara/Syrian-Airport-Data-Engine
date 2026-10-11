import os
import hashlib
from zoneinfo import ZoneInfo
from datetime import datetime, timezone
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


class TestFlightIdentityAndMovementCounting:
    """Verifies that flight numbers are not equated with airframe identities and counts are not inflated."""

    def test_comparison_endpoint_has_field_definitions(self):
        res = client.get("/api/movements/comparison?airport_id=DAM&start_date=2026-10-09&end_date=2026-10-10")
        assert res.status_code == 200
        data = res.json()
        assert "field_definitions" in data
        defs = data["field_definitions"]
        assert "total_records" in defs
        assert "scheduled_record_count" in defs
        assert "commercial_operational_event_count" in defs
        assert "codeshare_record_count" in defs
        assert "matched_codeshare_record_count" in defs
        assert "unmatched_codeshare_record_count" in defs
        assert "unique_operating_flight_count" in defs
        assert "unique_flight_movement_count" in defs

        # Explicit warning that flight numbers are not airframe identities
        assert "airline service callsigns, NOT distinct physical aircraft airframes" in defs["unique_operating_flight_count"]

    def test_deduplication_rules_document_key_separation(self):
        res = client.get("/api/movements/comparison?airport_id=DAM")
        assert res.status_code == 200
        rules = res.json().get("deduplication_rules", [])
        assert len(rules) >= 5
        rules_text = " ".join(rules)
        assert "commercial designations, NOT physical aircraft registrations" in rules_text
        assert "different directions (arrival vs departure) or at different aerodromes are never merged" in rules_text
        assert "Ambiguity Preservation" in rules_text

    def test_codeshares_remain_explicitly_ambiguous(self):
        res = client.get("/api/movements/comparison?airport_id=DAM&start_date=2026-10-09&end_date=2026-10-10")
        assert res.status_code == 200
        days = res.json()["comparison"]

        day_oct9 = days[0]
        # On Oct 9, 17 codeshares match an operating flight, 2 remain explicitly unmatched/ambiguous
        assert day_oct9["matched_codeshare_record_count"] == 17
        assert day_oct9["unmatched_codeshare_record_count"] == 2
        assert day_oct9["matched_codeshare_record_count"] + day_oct9["unmatched_codeshare_record_count"] == day_oct9["codeshare_record_count"]

        # Codeshares do NOT inflate unique operating flights
        assert day_oct9["unique_operating_flight_count"] == 51
        assert day_oct9["unique_operating_flight_count"] < (day_oct9["commercial_operational_event_count"] + day_oct9["codeshare_record_count"])

    def test_operating_flight_numbers_not_treated_as_aircraft_identities(self):
        res = client.get("/api/flights?date=2026-10-09&limit=50")
        assert res.status_code == 200
        flights = res.json()["flights"]
        for f in flights:
            # Flight number is airline flight code, registration is physical airframe
            assert "flight_number" in f
            assert "aircraft_registration" in f
            if f.get("aircraft_registration"):
                assert f["flight_number"] != f["aircraft_registration"]


class TestScheduledDateVsActualMovementDate:
    """Verifies scheduled_flight_date vs actual_movement_date vs flight_date."""

    def test_date_fields_present_in_flight_records(self):
        res = client.get("/api/flights?limit=25")
        assert res.status_code == 200
        for f in res.json()["flights"]:
            assert "flight_date" in f
            assert "scheduled_flight_date" in f
            assert "actual_movement_date" in f
            # scheduled_flight_date matches original flight_date
            assert f["scheduled_flight_date"] == f["flight_date"]

    def test_g9376_overnight_delay_date_semantics(self):
        # G9376 scheduled on 2026-10-09, departed on 2026-10-10
        res = client.get("/api/flights?date=2026-10-09&airline=Air%20Arabia")
        assert res.status_code == 200
        g9376 = [f for f in res.json()["flights"] if f.get("flight_number") == "G9376"][0]

        # Scheduled date on flight board
        assert g9376["flight_date"] == "2026-10-09"
        assert g9376["scheduled_flight_date"] == "2026-10-09"

        # Estimated movement on next calendar day; actual movement timestamp remains null
        assert g9376["actual_movement_date"] is None
        assert g9376["actual_dep_time"] is None
        assert g9376["estimated_dep_time"] == "2026-10-10T09:00:00Z"
        assert g9376["estimated_movement_date"] == "2026-10-10"
        assert g9376["source_observed_at_raw"] == "1791622800"

    def test_cross_midnight_arrivals_date_semantics(self):
        # In evidence raw timestamps, FYC522 (21:41Z), RB444 (21:46Z), RB502 (22:31Z)
        # In airport local Damascus time (UTC+3), they crossed midnight to 00:41, 00:46, 01:31 on 2026-10-10
        res = client.get("/api/flights?date=2026-10-09&airport_id=DAM&limit=200")
        assert res.status_code == 200
        flights_map = {f["flight_number"]: f for f in res.json()["flights"]}

        for flt in ["FYC522", "RB444", "RB502"]:
            f = flights_map[flt]
            assert f["scheduled_flight_date"] == "2026-10-09"
            assert f["flight_date"] == "2026-10-09"
            assert f["actual_movement_date"] == "2026-10-10"

    def test_schedule_only_flights_have_null_actual_movement_date(self):
        res = client.get("/api/movements/scheduled?date=2026-10-01&limit=10")
        assert res.status_code == 200
        for f in res.json()["movements"]:
            assert f["scheduled_flight_date"] == "2026-10-01"
            assert f["actual_movement_date"] is None


class TestTimestampConversionRegression:
    """Verifies strict timestamp parsing, rejection of ambiguous naive strings, and timezone conversions."""

    def test_unix_seconds(self):
        assert normalize_timestamp_to_utc("1791638817") == "2026-10-10T13:26:57Z"
        assert normalize_timestamp_to_utc(1791638817) == "2026-10-10T13:26:57Z"

    def test_unix_milliseconds(self):
        assert normalize_timestamp_to_utc("1791638817000") == "2026-10-10T13:26:57Z"
        assert normalize_timestamp_to_utc(1791638817000) == "2026-10-10T13:26:57Z"

    def test_iso_with_z(self):
        assert normalize_timestamp_to_utc("2026-10-10T13:26:57Z") == "2026-10-10T13:26:57Z"

    def test_iso_with_explicit_offset(self):
        # UTC+3 offset
        assert normalize_timestamp_to_utc("2026-10-10T16:26:57+03:00") == "2026-10-10T13:26:57Z"
        # UTC+0 offset
        assert normalize_timestamp_to_utc("2026-10-10T13:26:57+00:00") == "2026-10-10T13:26:57Z"
        # UTC-4 offset
        assert normalize_timestamp_to_utc("2026-10-10T09:26:57-04:00") == "2026-10-10T13:26:57Z"

    def test_naive_timestamp_lacks_timezone_rejected(self):
        # Must NOT infer UTC or Damascus local time for ambiguous naive timestamps
        assert normalize_timestamp_to_utc("2026-10-09 13:55") is None
        assert normalize_timestamp_to_utc("2026-10-09T13:55:00") is None

    def test_invalid_timestamps(self):
        assert normalize_timestamp_to_utc("not-a-timestamp") is None
        assert normalize_timestamp_to_utc("2026-99-99") is None
        assert normalize_timestamp_to_utc(True) is None

    def test_missing_timestamps(self):
        assert normalize_timestamp_to_utc(None) is None
        assert normalize_timestamp_to_utc("") is None
        assert normalize_timestamp_to_utc("   ") is None
        assert normalize_timestamp_to_utc("None") is None
        assert normalize_timestamp_to_utc("null") is None

    def test_utc_local_date_boundary_crossings(self):
        tz_dam = ZoneInfo("Asia/Damascus")
        # 23:30 UTC on Oct 9 is 02:30 UTC+3 on Oct 10
        dt_utc = datetime(2026, 10, 9, 23, 30, 0, tzinfo=timezone.utc)
        dt_local = dt_utc.astimezone(tz_dam)
        assert dt_local.date().isoformat() == "2026-10-10"


class TestProtectedBaselineIntegrityV2203:
    """Verifies cryptographic hash invariance for all 6 protected baseline files."""

    def test_six_protected_assets_hashes(self):
        for path, expected_hash in PROTECTED_HASHES.items():
            assert os.path.exists(path), f"Protected file missing: {path}"
            with open(path, "rb") as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            assert actual_hash == expected_hash, (
                f"CRYPTO INTEGRITY FAILURE on {path}: expected {expected_hash}, got {actual_hash}"
            )
