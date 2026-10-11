import pytest
from src.quality_checker import run_quality_audit

def test_quality_audit_clean_data():
    events = [
        {
            "event_id": "e1",
            "airport_id": "DAM",
            "source": "aviationstack",
            "movement_type": "departure",
            "airport_iata": "DAM",
            "airport_icao": "OSDI",
            "connected_airport_iata": "DXB",
            "route_type": "international",
            "flight_number": "RB443",
            "flight_date": "2026-10-10",
            "flight_status": "landed",
            "scheduled_dep_time": "2026-10-10T15:00:00Z",
            "actual_dep_time": "2026-10-10T15:10:00Z",
            "scheduled_arr_time": None,
            "actual_arr_time": None,
        }
    ]
    daily = [
        {"airport_id": "DAM", "flight_date": "2026-10-10", "total_movements": 1}
    ]
    hist = [
        {"flight_date": "2024-01-01", "movement_type": "departure", "scope": "DAM_ALP_LTK", "total_recorded_operations": 10}
    ]
    audit = run_quality_audit(events, daily, hist, persist=False)
    assert audit["overall_status"] == "PASSED"
    assert audit["failed_checks"] == 0

def test_quality_audit_catches_synthetic_dates():
    events = [
        {
            "event_id": "e1",
            "airport_id": "DAM",
            "source": "aviationstack",
            "movement_type": "departure",
            "airport_iata": "DAM",
            "airport_icao": "OSDI",
            "connected_airport_iata": "DXB",
            "route_type": "international",
            "flight_number": "RB443",
            "flight_date": "2026-10-10",
            "flight_status": "landed",
            "scheduled_dep_time": "2026-10-10T15:00:00Z",
            "actual_dep_time": None,
            "scheduled_arr_time": None,
            "actual_arr_time": None,
        }
    ]
    # Injected synthetic date 2026-10-11 with zero observed events
    daily = [
        {"airport_id": "DAM", "flight_date": "2026-10-10", "total_movements": 1},
        {"airport_id": "DAM", "flight_date": "2026-10-11", "total_movements": 0}
    ]
    audit = run_quality_audit(events, daily, [], persist=False)
    assert audit["overall_status"] == "FAILED"
    failed_names = [c["check_name"] for c in audit["checks"] if c["passed"] == 0]
    assert "no_synthetic_zeros_on_missing_dates" in failed_names

def test_quality_audit_catches_speculative_passenger_estimates():
    events = [
        {
            "event_id": "e1",
            "airport_id": "DAM",
            "source": "aviationstack",
            "movement_type": "departure",
            "airport_iata": "DAM",
            "airport_icao": "OSDI",
            "connected_airport_iata": "DXB",
            "route_type": "international",
            "flight_number": "RB443",
            "flight_date": "2026-10-10",
            "flight_status": "landed",
            "scheduled_dep_time": "2026-10-10T15:00:00Z",
            "actual_dep_time": None,
            "scheduled_arr_time": None,
            "actual_arr_time": None,
            "estimated_passengers": 150 # Forbidden speculative metric
        }
    ]
    daily = [{"airport_id": "DAM", "flight_date": "2026-10-10", "total_movements": 1}]
    audit = run_quality_audit(events, daily, [], persist=False)
    assert audit["overall_status"] == "FAILED"
    failed_names = [c["check_name"] for c in audit["checks"] if c["passed"] == 0]
    assert "no_speculative_passenger_or_cargo_estimates" in failed_names

def test_quality_audit_catches_mislabelled_scope():
    events = [
        {
            "event_id": "e1",
            "airport_id": "DAM",
            "source": "aviationstack",
            "movement_type": "departure",
            "airport_iata": "DAM",
            "airport_icao": "OSDI",
            "connected_airport_iata": "DXB",
            "route_type": "international",
            "flight_number": "RB443",
            "flight_date": "2026-10-10",
            "flight_status": "landed",
            "scheduled_dep_time": "2026-10-10T15:00:00Z",
            "actual_dep_time": None,
            "scheduled_arr_time": None,
            "actual_arr_time": None,
        }
    ]
    daily = [{"airport_id": "DAM", "flight_date": "2026-10-10", "total_movements": 1}]
    # Mislabelled scope: should be DAM_ALP_LTK, but falsely claimed to be DAM
    hist = [
        {"flight_date": "2024-01-01", "movement_type": "departure", "scope": "DAM", "total_recorded_operations": 10}
    ]
    audit = run_quality_audit(events, daily, hist, persist=False)
    assert audit["overall_status"] == "FAILED"
    failed_names = [c["check_name"] for c in audit["checks"] if c["passed"] == 0]
    assert "multi_airport_scope_isolation" in failed_names
