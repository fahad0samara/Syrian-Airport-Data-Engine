import pytest
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any

from src.normalizer import (
    normalize_flightradar24,
    deduplicate_with_audit,
    get_timestamp_priority,
    evaluate_cross_source_match,
)
from src.aggregator import (
    persist_all_to_database_and_exports,
    reconcile_monotonic_events,
)
from src.database import init_db
from tests.test_evidence_retention import make_sample_event

def make_raw_fr24_item(
    flight_number: str = "RB272",
    sched_dep: int | None = 1791642000,
    real_dep: int | None = None,
    est_dep: int | None = None,
    sched_arr: int | None = 1791660000,
    real_arr: int | None = None,
    est_arr: int | None = None,
    status_text: str = "Scheduled",
    generic_status: str = "scheduled",
    live: bool = False,
    reg: str = "LY-MAU",
    hex_code: str = "503D4D",
    row_id: int = 5873711767,
    flight_id: str | None = None,
) -> Dict[str, Any]:
    return {
        "flight": {
            "identification": {
                "id": flight_id,
                "row": row_id,
                "number": {"default": flight_number, "alternative": None},
                "callsign": f"SYR{flight_number[-3:]}",
                "codeshare": None
            },
            "status": {
                "live": live,
                "text": status_text,
                "icon": "red" if live else "gray",
                "estimated": None,
                "ambiguous": False,
                "generic": {
                    "status": {
                        "text": generic_status,
                        "type": "departure",
                        "color": "red" if live else "gray",
                        "diverted": None
                    },
                    "eventTime": {"utc": real_dep or est_dep, "local": None}
                }
            },
            "aircraft": {
                "model": {"code": "A320", "text": "Airbus A320-214"},
                "registration": reg,
                "hex": hex_code,
                "country": {"id": 127, "name": "Lithuania"}
            },
            "airline": {
                "name": "Syrian Airlines",
                "code": {"icao": "SYR"}
            },
            "airport": {
                "origin": {
                    "code": {"iata": "DAM", "icao": "OSDI"},
                    "name": "Damascus International Airport",
                    "position": {"country": {"name": "Syria"}, "region": {"city": "Damascus"}}
                },
                "destination": {
                    "code": {"iata": "AMS", "icao": "EHAM"},
                    "name": "Amsterdam Airport Schiphol",
                    "position": {"country": {"name": "Netherlands"}, "region": {"city": "Amsterdam"}}
                }
            },
            "time": {
                "scheduled": {"departure": sched_dep, "arrival": sched_arr},
                "real": {"departure": real_dep, "arrival": real_arr},
                "estimated": {"departure": est_dep, "arrival": est_arr},
                "other": {"eta": est_arr or real_arr, "duration": None}
            }
        }
    }


def setup_test_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = OFF;")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS airports (
        airport_id TEXT PRIMARY KEY,
        iata_code TEXT,
        icao_code TEXT,
        name TEXT,
        city TEXT,
        country TEXT
    );
    CREATE TABLE IF NOT EXISTS flight_events (
        event_id TEXT PRIMARY KEY,
        airport_id TEXT NOT NULL DEFAULT 'DAM',
        source TEXT NOT NULL,
        source_record_id TEXT,
        movement_type TEXT NOT NULL,
        airport_iata TEXT,
        airport_icao TEXT,
        connected_airport_iata TEXT,
        connected_airport_icao TEXT,
        connected_airport_name TEXT,
        connected_country TEXT,
        connected_city TEXT,
        route_type TEXT,
        airline_name TEXT,
        airline_iata TEXT,
        airline_icao TEXT,
        flight_number TEXT,
        flight_date TEXT NOT NULL,
        local_operational_date TEXT,
        flight_status TEXT NOT NULL,
        scheduled_dep_time TEXT,
        estimated_dep_time TEXT,
        actual_dep_time TEXT,
        scheduled_arr_time TEXT,
        estimated_arr_time TEXT,
        actual_arr_time TEXT,
        raw_scheduled_dep_time TEXT,
        raw_estimated_dep_time TEXT,
        raw_actual_dep_time TEXT,
        raw_scheduled_arr_time TEXT,
        raw_estimated_arr_time TEXT,
        raw_actual_arr_time TEXT,
        aircraft_model TEXT,
        aircraft_registration TEXT,
        aircraft_icao24 TEXT,
        record_nature TEXT NOT NULL DEFAULT 'scheduled_service',
        operating_flight_number TEXT,
        operating_carrier TEXT,
        observed_or_derived TEXT DEFAULT 'observed',
        quality_flags TEXT,
        normalization_version TEXT DEFAULT '2.0',
        raw_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS daily_airport_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        airport_id TEXT NOT NULL,
        flight_date TEXT NOT NULL,
        arrival_count INTEGER DEFAULT 0,
        departure_count INTEGER DEFAULT 0,
        completed_movements INTEGER DEFAULT 0,
        scheduled_movements INTEGER DEFAULT 0,
        total_movements INTEGER DEFAULT 0,
        landed_count INTEGER DEFAULT 0,
        departed_count INTEGER DEFAULT 0,
        cancelled_count INTEGER DEFAULT 0,
        diverted_count INTEGER DEFAULT 0,
        scheduled_count INTEGER DEFAULT 0,
        active_count INTEGER DEFAULT 0,
        domestic_count INTEGER DEFAULT 0,
        international_count INTEGER DEFAULT 0,
        unique_aircraft_count INTEGER DEFAULT 0,
        unique_airlines_count INTEGER DEFAULT 0,
        passengers INTEGER,
        cargo REAL,
        source_id TEXT NOT NULL DEFAULT 'aggregator',
        observed_or_derived TEXT DEFAULT 'derived',
        coverage_status TEXT NOT NULL DEFAULT 'observed',
        quality_flags TEXT,
        methodology_version TEXT DEFAULT '2.0',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(airport_id, flight_date)
    );
    CREATE TABLE IF NOT EXISTS damascus_daily_movements (
        flight_date TEXT PRIMARY KEY,
        arrival_count INTEGER,
        departure_count INTEGER,
        completed_movements INTEGER,
        scheduled_movements INTEGER,
        total_movements INTEGER,
        landed_count INTEGER,
        departed_count INTEGER,
        cancelled_count INTEGER,
        diverted_count INTEGER,
        scheduled_count INTEGER,
        active_count INTEGER,
        domestic_count INTEGER,
        international_count INTEGER,
        unique_aircraft_count INTEGER,
        unique_airlines_count INTEGER,
        completeness_status TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS historical_daily_movements_2024 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        flight_date TEXT NOT NULL,
        movement_type TEXT NOT NULL,
        scope TEXT NOT NULL DEFAULT 'DAM_ALP_LTK',
        active INTEGER DEFAULT 0,
        cancelled INTEGER DEFAULT 0,
        diverted INTEGER DEFAULT 0,
        landed INTEGER DEFAULT 0,
        scheduled INTEGER DEFAULT 0,
        unknown INTEGER DEFAULT 0,
        total_recorded_operations INTEGER DEFAULT 0,
        data_source TEXT,
        coverage_status TEXT NOT NULL DEFAULT 'observed',
        status_note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(flight_date, movement_type, scope)
    );
    CREATE TABLE IF NOT EXISTS deduplication_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        canonical_event_id TEXT NOT NULL,
        airport_id TEXT NOT NULL DEFAULT 'DAM',
        flight_number TEXT NOT NULL,
        movement_type TEXT NOT NULL,
        flight_date TEXT NOT NULL,
        source_a TEXT NOT NULL,
        source_a_record_id TEXT,
        source_a_raw_time TEXT,
        source_b TEXT NOT NULL,
        source_b_record_id TEXT,
        source_b_raw_time TEXT,
        time_difference_minutes REAL,
        matching_rule TEXT NOT NULL,
        resolution_status TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS raw_source_records (
        raw_record_id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        airport_id TEXT,
        retrieved_at_utc TIMESTAMP NOT NULL,
        query_parameters TEXT,
        source_record_id TEXT,
        raw_payload TEXT NOT NULL,
        payload_hash TEXT NOT NULL,
        source_url TEXT,
        http_status INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS event_evidence (
        evidence_id TEXT PRIMARY KEY,
        event_id TEXT NOT NULL,
        source_name TEXT NOT NULL,
        source_record_id TEXT,
        evidence_type TEXT NOT NULL,
        observed_value TEXT NOT NULL,
        raw_timestamp TEXT,
        observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        snapshot_path TEXT,
        snapshot_sha256 TEXT,
        validity_status TEXT NOT NULL DEFAULT 'valid',
        retraction_reason TEXT,
        superseded_by TEXT,
        UNIQUE(event_id, source_name, evidence_type, observed_value)
    );
    """)
    conn.commit()
    conn.close()


# ============================================================================
# 12 REGRESSION TEST CASES
# ============================================================================

def test_fr24_actual_dep_parsed_only_from_time_real():
    """1. actual_dep_time is populated ONLY when time.real.departure is non-null."""
    item = make_raw_fr24_item(real_dep=1791645028, est_dep=1791642600, generic_status="departed", status_text="Departed 18:10")
    records = normalize_flightradar24([item], "departure", "DAM")
    assert len(records) == 1
    rec = records[0]
    assert rec["actual_dep_time"] == "2026-10-10T15:10:28Z"
    assert rec["raw_actual_dep_time"] == "1791645028"


def test_fr24_estimated_dep_stored_in_estimated_dep_time():
    """2. When real.departure is null, estimated.departure goes to estimated_dep_time and actual_dep_time is None."""
    item = make_raw_fr24_item(real_dep=None, est_dep=1791642600, generic_status="estimated", status_text="Estimated dep 17:30")
    records = normalize_flightradar24([item], "departure", "DAM")
    assert len(records) == 1
    rec = records[0]
    assert rec["actual_dep_time"] is None
    assert rec["raw_actual_dep_time"] is None
    assert rec["estimated_dep_time"] == "2026-10-10T14:30:00Z"
    assert rec["raw_estimated_dep_time"] == "1791642600"


def test_fr24_estimated_arr_never_stored_in_actual_arr_time():
    """3. estimated.arrival is never populated into actual_arr_time."""
    item = make_raw_fr24_item(real_arr=None, est_arr=1791661057)
    records = normalize_flightradar24([item], "departure", "DAM")
    assert len(records) == 1
    rec = records[0]
    assert rec["actual_arr_time"] is None
    assert rec["raw_actual_arr_time"] is None
    assert rec["estimated_arr_time"] == "2026-10-10T19:37:37Z"
    assert rec["raw_estimated_arr_time"] == "1791661057"


def test_fr24_scheduled_flight_with_estimated_dep_remains_scheduled_service():
    """4. An FR24 flight with estimated departure and status 'scheduled' remains scheduled_service."""
    item = make_raw_fr24_item(
        flight_number="RB444",
        real_dep=None,
        est_dep=1791674400,
        generic_status="scheduled",
        status_text="Scheduled",
        live=False
    )
    records = normalize_flightradar24([item], "departure", "DAM")
    assert len(records) == 1
    rec = records[0]
    assert rec["actual_dep_time"] is None
    assert rec["estimated_dep_time"] == "2026-10-10T23:20:00Z"
    assert rec["record_nature"] == "scheduled_service"


def test_fr24_real_dep_with_estimated_arr_is_physical_movement_without_touchdown_evidence(tmp_path, monkeypatch):
    """5. Departure flight with real departure and estimated arrival is physical_movement without touchdown evidence."""
    test_db = tmp_path / "test_dep_touchdown.db"
    setup_test_db(test_db)
    monkeypatch.setattr("src.aggregator.get_connection", lambda: sqlite3.connect(test_db))
    monkeypatch.setattr("src.aggregator.PROCESSED_DATA_DIR", tmp_path / "proc")
    monkeypatch.setattr("src.aggregator.REPORTS_DIR", tmp_path / "rep")

    item = make_raw_fr24_item(
        flight_number="FYC521",
        real_dep=1791610068,
        est_arr=1791614670,
        generic_status="departed",
        status_text="Departed 08:27",
        live=True
    )
    records = normalize_flightradar24([item], "departure", "DAM")
    assert len(records) == 1
    rec = records[0]
    assert rec["record_nature"] == "physical_movement"
    assert rec["actual_dep_time"] == "2026-10-10T05:27:48Z"
    assert rec["actual_arr_time"] is None
    assert rec["estimated_arr_time"] == "2026-10-10T06:44:30Z"

    persist_all_to_database_and_exports(records, [], [], [], [])

    conn = sqlite3.connect(test_db)
    cur = conn.cursor()
    cur.execute("SELECT evidence_type, observed_value FROM event_evidence WHERE event_id = ?", (rec["event_id"],))
    evs = cur.fetchall()
    conn.close()

    ev_types = [e[0] for e in evs]
    assert "adsb_takeoff" in ev_types
    assert "estimated_arrival" in ev_types
    assert "adsb_touchdown" not in ev_types


def test_rb272_dam_departure_has_actual_dep_and_estimated_arr_no_local_touchdown(tmp_path, monkeypatch):
    """6. RB272 DAM departure has verified actual dep 15:10:28Z, estimated arr 19:37:37Z, and no touchdown evidence."""
    test_db = tmp_path / "test_rb272.db"
    setup_test_db(test_db)
    monkeypatch.setattr("src.aggregator.get_connection", lambda: sqlite3.connect(test_db))
    monkeypatch.setattr("src.aggregator.PROCESSED_DATA_DIR", tmp_path / "proc")
    monkeypatch.setattr("src.aggregator.REPORTS_DIR", tmp_path / "rep")

    item = make_raw_fr24_item(
        flight_number="RB272",
        flight_id="42102941",
        row_id=5873711767,
        sched_dep=1791642000,
        real_dep=1791645028,
        est_dep=None,
        sched_arr=1791660000,
        real_arr=None,
        est_arr=1791661057,
        generic_status="departed",
        status_text="Departed 18:10",
        live=True,
        reg="LY-MAU",
        hex_code="503D4D"
    )
    records = normalize_flightradar24([item], "departure", "DAM")
    rec = records[0]

    assert rec["actual_dep_time"] == "2026-10-10T15:10:28Z"
    assert rec["actual_arr_time"] is None
    assert rec["estimated_arr_time"] == "2026-10-10T19:37:37Z"
    assert rec["record_nature"] == "physical_movement"
    assert rec["aircraft_registration"] == "LY-MAU"

    persist_all_to_database_and_exports(records, [], [], [], [])

    conn = sqlite3.connect(test_db)
    cur = conn.cursor()
    cur.execute("SELECT evidence_type, observed_value, raw_timestamp FROM event_evidence WHERE event_id = ?", (rec["event_id"],))
    evs = cur.fetchall()
    conn.close()

    ev_dict = {e[0]: e[1] for e in evs}
    assert ev_dict.get("adsb_takeoff") == "2026-10-10T15:10:28Z"
    assert ev_dict.get("estimated_arrival") == "2026-10-10T19:37:37Z"
    assert "adsb_touchdown" not in ev_dict


def test_rb444_scheduled_departure_has_estimated_dep_and_no_adsb_takeoff(tmp_path, monkeypatch):
    """7. RB444 scheduled arrival leg with estimated dep 23:20:00Z generates estimated_departure and NO adsb_takeoff."""
    test_db = tmp_path / "test_rb444.db"
    setup_test_db(test_db)
    monkeypatch.setattr("src.aggregator.get_connection", lambda: sqlite3.connect(test_db))
    monkeypatch.setattr("src.aggregator.PROCESSED_DATA_DIR", tmp_path / "proc")
    monkeypatch.setattr("src.aggregator.REPORTS_DIR", tmp_path / "rep")

    item = make_raw_fr24_item(
        flight_number="RB444",
        flight_id=None,
        row_id=5874115491,
        sched_dep=1791673200,
        real_dep=None,
        est_dep=1791674400,
        sched_arr=1791680400,
        real_arr=None,
        est_arr=None,
        generic_status="scheduled",
        status_text="Scheduled",
        live=False
    )
    records = normalize_flightradar24([item], "arrival", "DAM")
    rec = records[0]

    assert rec["actual_dep_time"] is None
    assert rec["actual_arr_time"] is None
    assert rec["estimated_dep_time"] == "2026-10-10T23:20:00Z"
    assert rec["record_nature"] == "scheduled_service"

    persist_all_to_database_and_exports(records, [], [], [], [])

    conn = sqlite3.connect(test_db)
    cur = conn.cursor()
    cur.execute("SELECT evidence_type, observed_value FROM event_evidence WHERE event_id = ?", (rec["event_id"],))
    evs = cur.fetchall()
    conn.close()

    ev_types = [e[0] for e in evs]
    assert "estimated_departure" in ev_types
    assert "adsb_takeoff" not in ev_types
    assert "adsb_touchdown" not in ev_types


def test_vf318_real_takeoff_supersedes_earlier_estimated_departure():
    """8. VF318 real takeoff (15:04:39Z) cleanly supersedes earlier estimated departure (14:55:00Z)."""
    item_est = make_raw_fr24_item(
        flight_number="VF318",
        sched_dep=1791643500,
        real_dep=None,
        est_dep=1791644100,  # 14:55:00Z
        generic_status="estimated",
        status_text="Estimated dep 17:55",
        live=False
    )
    item_real = make_raw_fr24_item(
        flight_number="VF318",
        sched_dep=1791643500,
        real_dep=1791644679,  # 15:04:39Z
        est_dep=None,
        generic_status="departed",
        status_text="Departed 18:04",
        live=True
    )
    records_est = normalize_flightradar24([item_est], "departure", "DAM")
    records_real = normalize_flightradar24([item_real], "departure", "DAM")

    canonical, _, _ = deduplicate_with_audit([records_est[0], records_real[0]])
    assert len(canonical) == 1
    final_event = canonical[0]

    assert final_event["actual_dep_time"] == "2026-10-10T15:04:39Z"
    assert final_event["raw_actual_dep_time"] == "1791644679"
    assert final_event["estimated_dep_time"] == "2026-10-10T14:55:00Z"
    assert final_event["record_nature"] == "physical_movement"
    assert final_event["flight_status"] == "departed"


def test_evidence_ledger_adsb_takeoff_requires_actual_dep_time(tmp_path, monkeypatch):
    """9. event_evidence never generates adsb_takeoff if actual_dep_time is None."""
    test_db = tmp_path / "test_no_takeoff.db"
    setup_test_db(test_db)
    monkeypatch.setattr("src.aggregator.get_connection", lambda: sqlite3.connect(test_db))
    monkeypatch.setattr("src.aggregator.PROCESSED_DATA_DIR", tmp_path / "proc")
    monkeypatch.setattr("src.aggregator.REPORTS_DIR", tmp_path / "rep")

    event = make_sample_event(
        event_id="test_ev_01",
        airport_id="DAM",
        flight_number="XY123",
        movement_type="departure",
        source="flightradar24",
        flight_date="2026-10-10",
        flight_status="scheduled",
        record_nature="scheduled_service",
        scheduled_dep_time="2026-10-10T10:00:00Z",
        estimated_dep_time="2026-10-10T10:30:00Z",
        raw_estimated_dep_time="1791628200",
        actual_dep_time=None,
        raw_actual_dep_time=None,
        actual_arr_time=None,
        raw_actual_arr_time=None,
        estimated_arr_time=None,
        raw_estimated_arr_time=None,
        scheduled_arr_time=None,
        raw_scheduled_arr_time=None,
        raw_scheduled_dep_time="1791626400",
        source_record_id="rec_01",
        route_type="international",
    )
    persist_all_to_database_and_exports([event], [], [], [], [])

    conn = sqlite3.connect(test_db)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM event_evidence WHERE evidence_type = 'adsb_takeoff'")
    assert cur.fetchone()[0] == 0
    cur.execute("SELECT count(*) FROM event_evidence WHERE evidence_type = 'estimated_departure'")
    assert cur.fetchone()[0] == 1
    conn.close()


def test_evidence_ledger_adsb_touchdown_requires_actual_arr_time(tmp_path, monkeypatch):
    """10. event_evidence never generates adsb_touchdown if actual_arr_time is None."""
    test_db = tmp_path / "test_no_touchdown.db"
    setup_test_db(test_db)
    monkeypatch.setattr("src.aggregator.get_connection", lambda: sqlite3.connect(test_db))
    monkeypatch.setattr("src.aggregator.PROCESSED_DATA_DIR", tmp_path / "proc")
    monkeypatch.setattr("src.aggregator.REPORTS_DIR", tmp_path / "rep")

    event = make_sample_event(
        event_id="test_ev_02",
        airport_id="DAM",
        flight_number="XY124",
        movement_type="arrival",
        source="flightradar24",
        flight_date="2026-10-10",
        flight_status="scheduled",
        record_nature="scheduled_service",
        scheduled_arr_time="2026-10-10T12:00:00Z",
        estimated_arr_time="2026-10-10T12:45:00Z",
        raw_estimated_arr_time="1791636300",
        actual_arr_time=None,
        raw_actual_arr_time=None,
        actual_dep_time=None,
        raw_actual_dep_time=None,
        estimated_dep_time=None,
        raw_estimated_dep_time=None,
        scheduled_dep_time=None,
        source_record_id="rec_02",
        route_type="international",
        raw_scheduled_dep_time=None,
        raw_scheduled_arr_time="1791633600",
    )
    persist_all_to_database_and_exports([event], [], [], [], [])

    conn = sqlite3.connect(test_db)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM event_evidence WHERE evidence_type = 'adsb_touchdown'")
    assert cur.fetchone()[0] == 0
    cur.execute("SELECT count(*) FROM event_evidence WHERE evidence_type = 'estimated_arrival'")
    assert cur.fetchone()[0] == 1
    conn.close()


def test_cross_source_merge_verified_actual_never_overwritten_by_estimate():
    """11. A record with verified actual timestamp is NEVER overwritten by an incoming estimated timestamp."""
    lead_event = {
        "event_id": "lead_01",
        "airport_id": "DAM",
        "flight_number": "RB272",
        "movement_type": "departure",
        "source": "flightradar24",
        "source_record_id": "fr24_01",
        "route_type": "international",
        "flight_date": "2026-10-10",
        "flight_status": "departed",
        "record_nature": "physical_movement",
        "scheduled_dep_time": "2026-10-10T14:20:00Z",
        "actual_dep_time": "2026-10-10T15:10:28Z",
        "raw_actual_dep_time": "1791645028",
        "actual_arr_time": None,
        "raw_actual_arr_time": None,
        "estimated_dep_time": None,
        "raw_estimated_dep_time": None,
    }
    candidate_event = {
        "event_id": "cand_01",
        "airport_id": "DAM",
        "flight_number": "RB272",
        "movement_type": "departure",
        "source": "damairport_official",
        "source_record_id": "off_01",
        "route_type": "international",
        "flight_date": "2026-10-10",
        "flight_status": "scheduled",
        "record_nature": "scheduled_service",
        "scheduled_dep_time": "2026-10-10T14:30:00Z",
        "estimated_dep_time": "2026-10-10T14:30:00Z",
        "raw_estimated_dep_time": "1791642600",
        "actual_dep_time": None,
        "raw_actual_dep_time": None,
        "actual_arr_time": None,
        "raw_actual_arr_time": None,
    }

    reconciled = reconcile_monotonic_events([candidate_event], [lead_event])
    assert len(reconciled) == 1
    merged = reconciled[0]

    assert merged["actual_dep_time"] == "2026-10-10T15:10:28Z"
    assert merged["raw_actual_dep_time"] == "1791645028"
    assert merged["record_nature"] == "physical_movement"
    assert merged["estimated_dep_time"] == "2026-10-10T14:30:00Z"


def test_cross_source_merge_estimate_does_not_falsely_promote_scheduled_flight():
    """12. Merging an estimated time into an official scheduled flight does NOT promote it to physical_movement."""
    portal_event = {
        "event_id": "portal_sched_01",
        "airport_id": "DAM",
        "flight_number": "XY377",
        "movement_type": "arrival",
        "source": "damairport_official",
        "source_record_id": "off_xy377",
        "route_type": "international",
        "flight_date": "2026-10-10",
        "flight_status": "scheduled",
        "record_nature": "scheduled_service",
        "scheduled_arr_time": "2026-10-10T12:00:00Z",
        "actual_dep_time": None,
        "actual_arr_time": None,
        "estimated_dep_time": None,
        "estimated_arr_time": None,
    }
    fr24_event = {
        "event_id": "fr24_est_01",
        "airport_id": "DAM",
        "flight_number": "XY377",
        "movement_type": "arrival",
        "source": "flightradar24",
        "source_record_id": "fr24_xy377",
        "route_type": "international",
        "flight_date": "2026-10-10",
        "flight_status": "scheduled",
        "record_nature": "scheduled_service",
        "scheduled_arr_time": "2026-10-10T12:00:00Z",
        "actual_dep_time": None,
        "actual_arr_time": None,
        "estimated_dep_time": "2026-10-10T12:01:00Z",
        "raw_estimated_dep_time": "1791633660",
        "estimated_arr_time": None,
    }

    canonical, _, _ = deduplicate_with_audit([portal_event, fr24_event])
    assert len(canonical) == 1
    merged = canonical[0]

    assert merged["record_nature"] == "scheduled_service"
    assert merged["actual_dep_time"] is None
    assert merged["actual_arr_time"] is None
    assert merged["estimated_dep_time"] == "2026-10-10T12:01:00Z"
