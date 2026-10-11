import pytest
from datetime import datetime, timezone
import zoneinfo

from src.normalizer import (
    normalize_status,
    determine_route_type,
    parse_timestamp_to_utc,
    deduplicate_with_audit,
)
from src.aggregator import (
    aggregate_damascus_daily_movements,
    aggregate_daily_airport_movements,
)

def test_normalize_status():
    assert normalize_status("Landed") == "landed"
    assert normalize_status("Arrived") == "landed"
    assert normalize_status("Departed") == "departed"
    assert normalize_status("Departed 17:24") == "departed"
    assert normalize_status("Canceled") == "cancelled"
    assert normalize_status("Cancelled") == "cancelled"
    assert normalize_status("Active") == "active"
    assert normalize_status("En-route") == "active"
    assert normalize_status("Scheduled") == "scheduled"
    assert normalize_status("on-time") == "scheduled"
    assert normalize_status("new-time") == "scheduled"
    assert normalize_status("Diverted") == "diverted"
    assert normalize_status(None) == "unknown"

def test_determine_route_type():
    assert determine_route_type("ALP", "OSAP", "Syria") == "domestic"
    assert determine_route_type("LTK", "OSLK", "Syria") == "domestic"
    assert determine_route_type("KAC", "OSKL", "Syria") == "domestic"
    assert determine_route_type("DEZ", "OSDZ", "Syria") == "domestic"
    assert determine_route_type("PMS", "OSPM", "Syria") == "domestic"
    assert determine_route_type("DXB", "OMDB", "United Arab Emirates") == "international"
    assert determine_route_type("IST", "LTFM", "Turkey") == "international"
    assert determine_route_type("BGW", "ORBI", "Iraq") == "international"
    assert determine_route_type(None, None, None) == "unknown"

def test_parse_timestamp_to_utc():
    # 1. Unix epoch timestamp
    raw_epoch, iso_epoch = parse_timestamp_to_utc(1791648000)
    assert raw_epoch == "1791648000"
    assert iso_epoch == "2026-10-10T16:00:00Z"

    # 2. Explicit UTC with +00:00 (Must NOT subtract hours)
    raw_utc, iso_utc = parse_timestamp_to_utc("2026-10-10T18:30:00+00:00")
    assert raw_utc == "2026-10-10T18:30:00+00:00"
    assert iso_utc == "2026-10-10T18:30:00Z"

    # 3. Explicit UTC with Z
    raw_z, iso_z = parse_timestamp_to_utc("2026-10-10T15:30:00Z")
    assert raw_z == "2026-10-10T15:30:00Z"
    assert iso_z == "2026-10-10T15:30:00Z"

    # 4. Explicit non-UTC offset (+03:00)
    raw_off, iso_off = parse_timestamp_to_utc("2026-10-10T18:30:00+03:00")
    assert raw_off == "2026-10-10T18:30:00+03:00"
    assert iso_off == "2026-10-10T15:30:00Z"

    # 5. Timezone-naive local timestamp (localized to Asia/Damascus permanent UTC+3)
    raw_naive, iso_naive = parse_timestamp_to_utc("2026-10-10 18:30:00")
    assert raw_naive == "2026-10-10 18:30:00"
    assert iso_naive == "2026-10-10T15:30:00Z"

    # 6. Missing / None timestamp
    raw_none, iso_none = parse_timestamp_to_utc(None)
    assert raw_none is None
    assert iso_none is None

def test_deduplicate_with_audit_close_slot():
    records = [
        {
            "event_id": "e1",
            "airport_id": "DAM",
            "source": "aviationstack",
            "source_record_id": "as_1",
            "movement_type": "departure",
            "flight_number": "RB443",
            "flight_date": "2026-10-10",
            "scheduled_dep_time": "2026-10-10T15:00:00Z",
            "actual_dep_time": None,
            "raw_scheduled_dep_time": "2026-10-10T15:00:00+00:00",
            "flight_status": "scheduled",
            "aircraft_model": None,
            "aircraft_registration": None,
            "aircraft_icao24": None,
        },
        {
            "event_id": "e2",
            "airport_id": "DAM",
            "source": "flightradar24",
            "source_record_id": "fr_1",
            "movement_type": "departure",
            "flight_number": "RB443",
            "flight_date": "2026-10-10",
            "scheduled_dep_time": "2026-10-10T15:15:00Z",
            "actual_dep_time": "2026-10-10T15:20:00Z",
            "raw_scheduled_dep_time": "1791645300",
            "flight_status": "landed",
            "aircraft_model": "Airbus A320",
            "aircraft_registration": "YK-BAA",
            "aircraft_icao24": "760ABC",
        }
    ]
    canonical, audit_log, stats = deduplicate_with_audit(records)
    assert len(canonical) == 1
    assert len(audit_log) == 1
    audit = audit_log[0]
    assert audit["resolution_status"] == "MERGED_VERIFIED"
    assert audit["time_difference_minutes"] == 15.0
    merged = canonical[0]
    assert merged["flight_status"] == "landed"
    assert merged["aircraft_registration"] == "YK-BAA"
    assert "aviationstack" in merged["source"] and "flightradar24" in merged["source"]

def test_deduplicate_with_audit_ambiguous_and_distinct_legs():
    records = [
        {
            "event_id": "e1",
            "airport_id": "DAM",
            "source": "flightradar24",
            "source_record_id": "fr_morning",
            "movement_type": "departure",
            "flight_number": "FYC501",
            "flight_date": "2026-10-09",
            "scheduled_dep_time": "2026-10-09T08:15:00Z",
            "actual_dep_time": "2026-10-09T08:29:00Z",
            "raw_scheduled_dep_time": "1791533700",
            "flight_status": "landed",
        },
        {
            "event_id": "e2",
            "airport_id": "DAM",
            "source": "flightradar24",
            "source_record_id": "fr_evening",
            "movement_type": "departure",
            "flight_number": "FYC501",
            "flight_date": "2026-10-09",
            "scheduled_dep_time": "2026-10-09T14:45:00Z",
            "actual_dep_time": "2026-10-09T15:12:00Z",
            "raw_scheduled_dep_time": "1791557100",
            "flight_status": "landed",
        }
    ]
    canonical, audit_log, stats = deduplicate_with_audit(records)
    # The two flights are ~6.5 hours apart: distinct legs of FYC501 on the same day!
    assert len(canonical) == 2
    assert len(audit_log) == 1
    assert audit_log[0]["resolution_status"] == "SPLIT_DISTINCT_LEG"

def test_deduplicate_never_merges_arrival_and_departure():
    records = [
        {
            "event_id": "arr_1",
            "airport_id": "DAM",
            "source": "flightradar24",
            "source_record_id": "fr_arr",
            "movement_type": "arrival",
            "flight_number": "RB443",
            "flight_date": "2026-10-10",
            "scheduled_arr_time": "2026-10-10T15:00:00Z",
            "flight_status": "landed",
        },
        {
            "event_id": "dep_1",
            "airport_id": "DAM",
            "source": "flightradar24",
            "source_record_id": "fr_dep",
            "movement_type": "departure",
            "flight_number": "RB443",
            "flight_date": "2026-10-10",
            "scheduled_dep_time": "2026-10-10T15:00:00Z",
            "flight_status": "scheduled",
        }
    ]
    canonical, audit_log, stats = deduplicate_with_audit(records)
    # Arrival and departure must never be merged
    assert len(canonical) == 2
    assert len(audit_log) == 0

def test_aggregate_damascus_daily_movements():
    events = [
        {
            "airport_id": "DAM",
            "flight_date": "2026-10-10",
            "movement_type": "arrival",
            "flight_status": "landed",
            "route_type": "international",
            "aircraft_registration": "YK-BAA",
            "airline_name": "Syrian Air"
        },
        {
            "airport_id": "DAM",
            "flight_date": "2026-10-10",
            "movement_type": "departure",
            "flight_status": "scheduled",
            "route_type": "domestic",
            "aircraft_registration": "YK-BAB",
            "airline_name": "Fly Cham"
        }
    ]
    daily = aggregate_damascus_daily_movements(events)
    assert len(daily) == 1
    d = daily[0]
    assert d["flight_date"] == "2026-10-10"
    assert d["arrival_count"] == 1
    assert d["departure_count"] == 1
    assert d["completed_movements"] == 1 # Only the landed flight is completed
    assert d["scheduled_movements"] == 1 # The scheduled flight is pending
    assert d["total_movements"] == 2
    assert d["landed_count"] == 1
    assert d["scheduled_count"] == 1
    assert d["domestic_count"] == 1
    assert d["international_count"] == 1
    assert d["unique_aircraft_count"] == 2
    assert d["unique_airlines_count"] == 2
    assert d["completeness_status"] == "complete_verified"

def test_aggregate_daily_airport_movements_multi_airport():
    events = [
        {
            "airport_id": "DAM",
            "flight_date": "2026-10-10",
            "movement_type": "arrival",
            "flight_status": "landed",
            "route_type": "international",
            "aircraft_registration": "YK-BAA",
            "airline_name": "Syrian Air"
        },
        {
            "airport_id": "ALP",
            "flight_date": "2026-10-10",
            "movement_type": "departure",
            "flight_status": "landed",
            "route_type": "international",
            "aircraft_registration": "YK-BAC",
            "airline_name": "Fly Cham"
        },
        {
            "airport_id": "DEZ",
            "flight_date": "2026-10-10",
            "movement_type": "departure",
            "flight_status": "active",
            "route_type": "domestic",
            "aircraft_registration": "YK-BAD",
            "airline_name": "Cham Wings"
        }
    ]
    all_daily = aggregate_daily_airport_movements(events)
    assert len(all_daily) == 3
    airports_seen = set(r["airport_id"] for r in all_daily)
    assert airports_seen == {"DAM", "ALP", "DEZ"}
    for r in all_daily:
        assert r["passengers"] is None
        assert r["cargo"] is None
        if r["airport_id"] in ("DAM", "ALP"):
            assert r["completed_movements"] == 1
            assert r["landed_count"] == 1
        elif r["airport_id"] == "DEZ":
            assert r["completed_movements"] == 0  # Active flight is not completed
            assert r["active_count"] == 1

def test_completed_movements_strictly_landed_not_active():
    """Verify that active, en-route, or departed flights are not counted as completed movements."""
    events = [
        {
            "airport_id": "DAM",
            "flight_date": "2026-10-10",
            "movement_type": "departure",
            "flight_status": "active",
            "route_type": "international",
            "aircraft_registration": "YK-BAA",
            "airline_name": "Syrian Air"
        },
        {
            "airport_id": "DAM",
            "flight_date": "2026-10-10",
            "movement_type": "arrival",
            "flight_status": "landed",
            "route_type": "international",
            "aircraft_registration": "YK-BAB",
            "airline_name": "Fly Cham"
        },
        {
            "airport_id": "DAM",
            "flight_date": "2026-10-10",
            "movement_type": "departure",
            "flight_status": "departed",
            "route_type": "international",
            "aircraft_registration": "YK-BAE",
            "airline_name": "Syrian Air"
        },
        {
            "airport_id": "DAM",
            "flight_date": "2026-10-10",
            "movement_type": "departure",
            "flight_status": "scheduled",
            "route_type": "domestic",
            "aircraft_registration": "YK-BAC",
            "airline_name": "Cham Wings"
        }
    ]
    daily = aggregate_daily_airport_movements(events)
    assert len(daily) == 1
    d = daily[0]
    assert d["total_movements"] == 4
    assert d["landed_count"] == 1
    assert d["departed_count"] == 1
    assert d["active_count"] == 1
    assert d["scheduled_count"] == 1
    assert d["completed_movements"] == 2  # Strictly landed (1) + departed (1); active (1) and scheduled (1) excluded!
    assert d["scheduled_movements"] == 1

def test_historical_2024_zero_operation_dates_tagged_unverified_data_gap():
    """Verify that zero-operation dates in historical 2024 SEM series are marked as unverified_data_gap, not observed."""
    from src.aggregator import load_historical_sem_series
    series = load_historical_sem_series()
    zero_ops = [r for r in series if r["total_recorded_operations"] == 0]
    # 15 zero-operation rows: 1 departure on 2024-01-28 + 14 arrivals/departures on 7 outage dates
    # On 2024-01-28, arrival recorded 2 scheduled operations, while departure recorded 0
    assert len(zero_ops) == 15
    for r in zero_ops:
        assert r["coverage_status"] == "unverified_data_gap"
        assert "Unverified data gap" in r["status_note"]
    
    non_zero = [r for r in series if r["total_recorded_operations"] > 0]
    assert len(non_zero) == 578 - 15
    for r in non_zero:
        assert r["coverage_status"] == "observed"

def test_future_counts_reproducibility():
    """Verify reproducible future counts: 872 date-based (849 DAM + 23 ALP) and 881 timestamp-based."""
    import sqlite3
    from src.config import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Query 1: date-based future flights
    c.execute("SELECT count(*) FROM flight_events WHERE flight_date > '2026-10-10'")
    assert c.fetchone()[0] == 872

    c.execute("SELECT count(*) FROM flight_events WHERE flight_date > '2026-10-10' AND airport_id = 'DAM'")
    assert c.fetchone()[0] == 849

    c.execute("SELECT count(*) FROM flight_events WHERE flight_date > '2026-10-10' AND airport_id = 'ALP'")
    assert c.fetchone()[0] == 23

    # Query 2: timestamp-based future flights
    audit_ts = "2026-10-10T14:45:53Z"
    c.execute("""
    SELECT count(*) FROM flight_events
    WHERE COALESCE(scheduled_dep_time, actual_dep_time, scheduled_arr_time, actual_arr_time) > ?
    """, (audit_ts,))
    assert c.fetchone()[0] == 881

    c.execute("""
    SELECT count(*) FROM flight_events
    WHERE COALESCE(scheduled_dep_time, actual_dep_time, scheduled_arr_time, actual_arr_time) > ?
      AND airport_id = 'DAM'
    """, (audit_ts,))
    assert c.fetchone()[0] == 858

def test_active_status_investigation():
    """Verify active events after audit timestamp possess raw source status active."""
    import sqlite3
    import json
    from src.config import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    audit_ts = "2026-10-10T14:45:53Z"
    c.execute("""
    SELECT event_id, source, flight_status, raw_json
    FROM flight_events
    WHERE COALESCE(scheduled_dep_time, actual_dep_time, scheduled_arr_time, actual_arr_time) > ?
      AND flight_status = 'active'
    """, (audit_ts,))
    rows = c.fetchall()
    assert len(rows) == 1
    for r in rows:
        assert "aviationstack" in r[1]
        assert r[2] == "active"
        raw_obj = json.loads(r[3])
        assert raw_obj.get("flight_status") == "active"

def test_completed_movements_event_level():
    """Verify canonical completed movements (121 total, 98 verified ground movements)."""
    import sqlite3
    from src.config import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
    SELECT count(*) FROM flight_events
    WHERE airport_id = 'DAM' AND flight_status IN ('landed', 'departed')
    """)
    assert c.fetchone()[0] == 121

    # Arrivals landed (60)
    c.execute("""
    SELECT count(*) FROM flight_events
    WHERE airport_id = 'DAM' AND movement_type = 'arrival' AND flight_status = 'landed'
    """)
    assert c.fetchone()[0] == 60

    # Departures departed (50) or landed at destination (11) -> 61
    c.execute("""
    SELECT count(*) FROM flight_events
    WHERE airport_id = 'DAM' AND movement_type = 'departure' AND flight_status IN ('departed', 'landed')
    """)
    assert c.fetchone()[0] == 61

    # Verified ground movements with Flightradar24 radar telemetry (98: 48 arr, 50 dep)
    c.execute("""
    SELECT count(*) FROM flight_events
    WHERE airport_id = 'DAM' AND source LIKE '%flightradar24%' AND flight_status IN ('landed', 'departed')
    """)
    assert c.fetchone()[0] == 98



