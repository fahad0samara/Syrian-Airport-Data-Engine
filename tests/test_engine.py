import pytest
from src.normalizer import (
    normalize_status,
    determine_route_type,
    parse_iso_or_epoch,
    deduplicate_flight_events,
)
from src.aggregator import aggregate_damascus_daily_movements

def test_normalize_status():
    assert normalize_status("Landed") == "landed"
    assert normalize_status("Arrived") == "landed"
    assert normalize_status("Canceled") == "cancelled"
    assert normalize_status("Cancelled") == "cancelled"
    assert normalize_status("Active") == "active"
    assert normalize_status("En-route") == "active"
    assert normalize_status("Scheduled") == "scheduled"
    assert normalize_status("Diverted") == "diverted"
    assert normalize_status(None) == "unknown"

def test_determine_route_type():
    # Domestic Syrian airports
    assert determine_route_type("ALP", "OSAP", "Syria") == "domestic"
    assert determine_route_type("LTK", "OSLK", "Syria") == "domestic"
    assert determine_route_type("KAC", "OSKL", "Syria") == "domestic"
    # Foreign airports
    assert determine_route_type("DXB", "OMDB", "United Arab Emirates") == "international"
    assert determine_route_type("IST", "LTFM", "Turkey") == "international"
    assert determine_route_type("BGW", "ORBI", "Iraq") == "international"
    assert determine_route_type(None, None, None) == "unknown"

def test_parse_iso_or_epoch():
    # Unix timestamp
    ts = 1791648000 # 2026-10-10T16:00:00Z
    iso = parse_iso_or_epoch(ts)
    assert iso is not None
    assert "2026-10-10" in iso

    # ISO string
    iso_in = "2026-10-10T18:30:00Z"
    assert parse_iso_or_epoch(iso_in) == "2026-10-10T18:30:00Z"

    # Damascus local wall-clock adjustment
    iso_dam = parse_iso_or_epoch("2026-10-10T18:30:00+00:00", is_damascus_local_source=True)
    assert iso_dam == "2026-10-10T15:30:00Z"

def test_deduplicate_flight_events():
    records = [
        {
            "event_id": "1",
            "source": "aviationstack",
            "movement_type": "departure",
            "flight_number": "RB443",
            "flight_date": "2026-10-10",
            "scheduled_dep_time": "2026-10-10T15:00:00Z",
            "actual_dep_time": None,
            "flight_status": "scheduled",
            "aircraft_model": None,
            "aircraft_registration": None,
            "aircraft_icao24": None,
        },
        {
            "event_id": "2",
            "source": "flightradar24",
            "movement_type": "departure",
            "flight_number": "RB443",
            "flight_date": "2026-10-10",
            "scheduled_dep_time": "2026-10-10T15:00:00Z",
            "actual_dep_time": "2026-10-10T15:10:00Z",
            "flight_status": "landed",
            "aircraft_model": "Airbus A320",
            "aircraft_registration": "YK-BAA",
            "aircraft_icao24": "760ABC",
        }
    ]
    deduped, pruned_count = deduplicate_flight_events(records)
    assert len(deduped) == 1
    assert pruned_count == 1
    m = deduped[0]
    assert m["flight_number"] == "RB443"
    assert m["actual_dep_time"] == "2026-10-10T15:10:00Z"
    assert m["flight_status"] == "landed"
    assert m["aircraft_registration"] == "YK-BAA"
    assert "aviationstack" in m["source"] and "flightradar24" in m["source"]

def test_aggregate_damascus_daily_movements():
    events = [
        {
            "flight_date": "2026-10-10",
            "movement_type": "arrival",
            "flight_status": "landed",
            "route_type": "international",
            "aircraft_registration": "YK-BAA",
            "airline_name": "Syrian Air"
        },
        {
            "flight_date": "2026-10-10",
            "movement_type": "departure",
            "flight_status": "active",
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
    assert d["total_movements"] == 2
    assert d["landed_count"] == 1
    assert d["active_count"] == 1
    assert d["domestic_count"] == 1
    assert d["international_count"] == 1
    assert d["unique_aircraft_count"] == 2
    assert d["unique_airlines_count"] == 2
    assert d["completeness_status"] == "complete_verified"
