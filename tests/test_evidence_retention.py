import pytest
import sqlite3
import copy
from typing import Dict, Any, List

from src.aggregator import (
    reconcile_monotonic_events,
    persist_all_to_database_and_exports,
    aggregate_daily_airport_movements,
    aggregate_damascus_daily_movements,
)
from src.normalizer import generate_event_id

def make_sample_event(**kwargs) -> Dict[str, Any]:
    base = {
        "event_id": kwargs.get("event_id") or "sample_event_01",
        "airport_id": kwargs.get("airport_id", "DAM"),
        "source": kwargs.get("source", "damairport_official"),
        "source_record_id": kwargs.get("source_record_id", "rec_001"),
        "movement_type": kwargs.get("movement_type", "arrival"),
        "airport_iata": "DAM",
        "airport_icao": "OSDI",
        "connected_airport_iata": "AMM",
        "connected_airport_icao": "OJAI",
        "connected_airport_name": "Queen Alia International",
        "connected_country": "Jordan",
        "connected_city": "Amman",
        "route_type": "international",
        "airline_name": "Royal Jordanian",
        "airline_iata": "RJ",
        "airline_icao": "RJA",
        "flight_number": kwargs.get("flight_number", "RJ435"),
        "flight_date": kwargs.get("flight_date", "2026-10-09"),
        "local_operational_date": kwargs.get("flight_date", "2026-10-09"),
        "flight_status": kwargs.get("flight_status", "landed"),
        "scheduled_dep_time": kwargs.get("scheduled_dep_time", "2026-10-09T03:30:00Z"),
        "estimated_dep_time": kwargs.get("estimated_dep_time", None),
        "actual_dep_time": kwargs.get("actual_dep_time", None),
        "scheduled_arr_time": kwargs.get("scheduled_arr_time", "2026-10-09T04:40:00Z"),
        "estimated_arr_time": kwargs.get("estimated_arr_time", None),
        "actual_arr_time": kwargs.get("actual_arr_time", None),
        "raw_scheduled_dep_time": kwargs.get("raw_scheduled_dep_time", "2026-10-09 06:30"),
        "raw_estimated_dep_time": kwargs.get("raw_estimated_dep_time", None),
        "raw_actual_dep_time": kwargs.get("raw_actual_dep_time", None),
        "raw_scheduled_arr_time": kwargs.get("raw_scheduled_arr_time", "2026-10-09 07:40"),
        "raw_estimated_arr_time": kwargs.get("raw_estimated_arr_time", None),
        "raw_actual_arr_time": kwargs.get("raw_actual_arr_time", None),
        "aircraft_model": kwargs.get("aircraft_model", None),
        "aircraft_registration": kwargs.get("aircraft_registration", None),
        "aircraft_icao24": kwargs.get("aircraft_icao24", None),
        "record_nature": kwargs.get("record_nature", "scheduled_service"),
        "operating_flight_number": "RJ435",
        "operating_carrier": "RJ",
        "observed_or_derived": "observed",
        "quality_flags": kwargs.get("quality_flags", "clean"),
        "normalization_version": "2.0",
        "raw_json": kwargs.get("raw_json", "{}"),
    }
    return base


def test_rolling_feed_disappearance_retains_physical_evidence():
    """
    Test 1: Confirmed physical movement retains verified telemetry and classification
    when subsequent rolling feeds omit the flight after aging out of the rolling buffer.
    """
    # Previously observed and verified physical movement in database
    existing_event = make_sample_event(
        event_id="daeb7ccbd61341a2",
        flight_number="RJ435",
        flight_date="2026-10-09",
        flight_status="landed",
        record_nature="physical_movement",
        source="damairport_official+aviationstack+flightradar24",
        actual_arr_time="2026-10-09T04:11:00Z",
        raw_actual_arr_time="1791519114",
        aircraft_model="A20N",
        aircraft_registration="JY-RAL",
        aircraft_icao24="74482C",
        quality_flags="merged_cross_source_verified"
    )

    # Incoming refresh where FR24 rolled forward (flight omitted from rolling feed,
    # now only present on airport portal without actual touchdown telemetry)
    incoming_event = make_sample_event(
        event_id="daeb7ccbd61341a2",
        flight_number="RJ435",
        flight_date="2026-10-09",
        flight_status="landed",
        record_nature="unverified_movement",  # Downgraded candidate from portal-only data
        source="damairport_official",
        actual_arr_time=None,
        raw_actual_arr_time=None,
        aircraft_model=None,
        aircraft_registration=None,
        aircraft_icao24=None,
        quality_flags="unverified_portal_only"
    )

    reconciled = reconcile_monotonic_events([incoming_event], [existing_event])
    assert len(reconciled) == 1
    rec = reconciled[0]

    # Monotonic policy assertions
    assert rec["record_nature"] == "physical_movement", "Must retain physical_movement classification"
    assert rec["actual_arr_time"] == "2026-10-09T04:11:00Z", "Must retain verified actual touchdown time"
    assert rec["raw_actual_arr_time"] == "1791519114", "Must retain raw epoch telemetry"
    assert rec["aircraft_registration"] == "JY-RAL", "Must retain aircraft registration"
    assert rec["aircraft_icao24"] == "74482C", "Must retain aircraft icao24 hex identifier"
    assert rec["aircraft_model"] == "A20N", "Must retain aircraft model"
    assert "flightradar24" in rec["source"], "Must retain flightradar24 source provenance"
    assert rec["quality_flags"] == "retained_verified_evidence_monotonic"


def test_empty_or_partial_feed_does_not_erase_historical_evidence():
    """
    Test 2: Empty or partial feed responses (e.g. portal outage or date window truncation)
    never erase or drop previously preserved historical evidence from database.
    """
    # 3 existing events across distinct airports and dates
    existing_events = [
        make_sample_event(event_id="ev_001", airport_id="DAM", flight_date="2026-10-08", record_nature="physical_movement"),
        make_sample_event(event_id="ev_002", airport_id="ALP", flight_date="2026-10-09", record_nature="physical_movement"),
        make_sample_event(event_id="ev_003", airport_id="DEZ", flight_date="2026-10-10", record_nature="physical_movement"),
    ]

    # Incoming refresh returns 0 events (e.g. complete network outage or empty portal)
    incoming_empty = []
    reconciled = reconcile_monotonic_events(incoming_empty, existing_events)
    assert len(reconciled) == 3, "Empty incoming feed must preserve all 3 existing events"

    # Incoming refresh returns only 1 event (partial feed, e.g. only ALP responded)
    incoming_partial = [
        make_sample_event(event_id="ev_002", airport_id="ALP", flight_date="2026-10-09", record_nature="physical_movement")
    ]
    reconciled_partial = reconcile_monotonic_events(incoming_partial, existing_events)
    assert len(reconciled_partial) == 3, "Partial incoming feed must retain omitted historical events"
    ids = {r["event_id"] for r in reconciled_partial}
    assert ids == {"ev_001", "ev_002", "ev_003"}


def test_explicit_source_retraction_applied_with_provenance():
    """
    Test 3: Explicit source retraction (cancellation or diversion) updates status
    and sets quality_flags='source_retraction_applied' while preserving provenance.
    """
    existing_event = make_sample_event(
        event_id="ev_retract_01",
        flight_number="RB201",
        flight_date="2026-10-10",
        flight_status="landed",
        record_nature="physical_movement",
        actual_arr_time="2026-10-10T12:00:00Z"
    )

    # Incoming feed explicitly states flight was cancelled / retracted
    incoming_event = make_sample_event(
        event_id="ev_retract_01",
        flight_number="RB201",
        flight_date="2026-10-10",
        flight_status="cancelled",
        record_nature="unverified_movement"
    )

    reconciled = reconcile_monotonic_events([incoming_event], [existing_event])
    assert len(reconciled) == 1
    rec = reconciled[0]

    assert rec["flight_status"] == "cancelled", "Must accept explicit cancellation"
    assert rec["quality_flags"] == "source_retraction_applied", "Must record source_retraction_applied"


def test_ingestion_idempotency_zero_drift():
    """
    Test 4: Running reconciliation across multiple runs with identical snapshots
    produces identical records, zero classification drift, and identical aggregates.
    """
    sample_events = [
        make_sample_event(event_id="idemp_01", airport_id="DAM", flight_number="RJ435", flight_date="2026-10-09", record_nature="physical_movement", actual_arr_time="2026-10-09T04:11:00Z"),
        make_sample_event(event_id="idemp_02", airport_id="DAM", flight_number="RB101", flight_date="2026-10-09", record_nature="scheduled_service"),
        make_sample_event(event_id="idemp_03", airport_id="ALP", flight_number="6Q511", flight_date="2026-10-09", record_nature="physical_movement", actual_arr_time="2026-10-09T08:00:00Z"),
    ]

    # Run 1: reconcile against empty
    run1 = reconcile_monotonic_events(sample_events, [])
    assert len(run1) == 3

    # Run 2: reconcile against run 1
    run2 = reconcile_monotonic_events(sample_events, run1)
    assert len(run2) == 3

    for e1, e2 in zip(run1, run2):
        assert e1["event_id"] == e2["event_id"]
        assert e1["record_nature"] == e2["record_nature"]
        assert e1["flight_status"] == e2["flight_status"]
        assert e1["actual_arr_time"] == e2["actual_arr_time"]

    # Verify aggregates are identical
    agg1 = aggregate_daily_airport_movements(run1)
    agg2 = aggregate_daily_airport_movements(run2)
    assert agg1 == agg2


def test_unsupported_scheduled_flight_never_promoted_to_physical():
    """
    Test 5: An unsupported scheduled flight is NEVER promoted to physical_movement,
    even if its status is marked landed or departed on an unverified airport portal
    without actual wheels-down / ADS-B radar telemetry.
    """
    existing_scheduled = make_sample_event(
        event_id="sched_01",
        flight_number="SYR999",
        flight_date="2026-10-15",
        flight_status="scheduled",
        record_nature="scheduled_service",
        actual_arr_time=None,
        aircraft_registration=None
    )

    # Incoming candidate with status 'landed' on portal, but NO actual telemetry
    incoming_candidate = make_sample_event(
        event_id="sched_01",
        flight_number="SYR999",
        flight_date="2026-10-15",
        flight_status="landed",
        record_nature="unverified_movement",  # Portal-only landed without telemetry
        actual_arr_time=None,
        aircraft_registration=None
    )

    reconciled = reconcile_monotonic_events([incoming_candidate], [existing_scheduled])
    assert len(reconciled) == 1
    rec = reconciled[0]

    assert rec["record_nature"] != "physical_movement", "Must NEVER promote scheduled flight without physical telemetry to physical_movement"
    assert rec["record_nature"] == "unverified_movement"
    assert rec["actual_arr_time"] is None


def setup_isolated_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS airports (
        airport_id TEXT PRIMARY KEY,
        iata_code TEXT,
        icao_code TEXT,
        name TEXT,
        name_ar TEXT,
        city TEXT,
        city_ar TEXT,
        country TEXT,
        timezone TEXT,
        airport_type TEXT,
        classification TEXT,
        operational_status TEXT,
        latitude REAL,
        longitude REAL
    );
    CREATE TABLE IF NOT EXISTS flight_events (
        event_id TEXT PRIMARY KEY,
        airport_id TEXT NOT NULL DEFAULT 'DAM',
        source TEXT NOT NULL,
        source_record_id TEXT,
        movement_type TEXT NOT NULL,
        airport_iata TEXT DEFAULT 'DAM',
        airport_icao TEXT DEFAULT 'OSDI',
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
        source_id TEXT NOT NULL,
        observed_or_derived TEXT DEFAULT 'derived_from_flight_events',
        coverage_status TEXT NOT NULL DEFAULT 'observed',
        quality_flags TEXT,
        methodology_version TEXT DEFAULT '2.0',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(airport_id, flight_date)
    );
    CREATE TABLE IF NOT EXISTS damascus_daily_movements (
        flight_date TEXT PRIMARY KEY,
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
        completeness_status TEXT NOT NULL DEFAULT 'complete_verified',
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
        coverage_status TEXT,
        status_note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(flight_date, movement_type, scope)
    );
    CREATE TABLE IF NOT EXISTS deduplication_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        canonical_event_id TEXT NOT NULL,
        airport_id TEXT NOT NULL,
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
        retrieved_at_utc TEXT NOT NULL,
        query_parameters TEXT,
        source_record_id TEXT,
        raw_payload TEXT,
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
    CREATE TRIGGER IF NOT EXISTS trg_prevent_evidence_update
    BEFORE UPDATE ON event_evidence
    WHEN OLD.observed_value != NEW.observed_value
      OR OLD.raw_timestamp != NEW.raw_timestamp
      OR OLD.event_id != NEW.event_id
      OR OLD.evidence_type != NEW.evidence_type
      OR OLD.source_name != NEW.source_name
    BEGIN
        SELECT RAISE(ABORT, 'event_evidence ledger core observation fields are immutable: UPDATE operations on observations are strictly prohibited');
    END;
    CREATE TRIGGER IF NOT EXISTS trg_prevent_evidence_delete
    BEFORE DELETE ON event_evidence
    BEGIN
        SELECT RAISE(ABORT, 'event_evidence ledger is append-only: DELETE operations are strictly prohibited');
    END;
    """)
    conn.commit()
    conn.close()


def test_evidence_provenance_survives_db_persistence_and_reload(tmp_path, monkeypatch):
    """
    Test 6: Evidence provenance survives database persistence and reload in an isolated environment.
    Exports retain identical evidence to the database.
    """
    import pandas as pd
    db_file = tmp_path / "test_iso.db"
    setup_isolated_db(db_file)

    proc_dir = tmp_path / "processed"
    rep_dir = tmp_path / "reports"
    raw_dir = tmp_path / "raw"
    proc_dir.mkdir(parents=True, exist_ok=True)
    rep_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("src.aggregator.get_connection", lambda: sqlite3.connect(db_file))
    monkeypatch.setattr("src.aggregator.PROCESSED_DATA_DIR", proc_dir)
    monkeypatch.setattr("src.aggregator.REPORTS_DIR", rep_dir)
    monkeypatch.setattr("src.aggregator.RAW_DATA_DIR", raw_dir)

    phys_event = make_sample_event(
        event_id="daeb7ccbd61341a2",
        flight_number="RJ435",
        flight_date="2026-10-09",
        flight_status="landed",
        record_nature="physical_movement",
        source="damairport_official+aviationstack+flightradar24",
        actual_arr_time="2026-10-09T04:11:00Z",
        raw_actual_arr_time="1791519114",
        aircraft_model="A20N",
        aircraft_registration="JY-RAL",
        aircraft_icao24="74482C",
        quality_flags="merged_cross_source_verified"
    )

    dam_daily = aggregate_damascus_daily_movements([phys_event])
    all_daily = aggregate_daily_airport_movements([phys_event])

    summary = persist_all_to_database_and_exports(
        events=[phys_event],
        dam_daily_movements=dam_daily,
        all_daily_movements=all_daily,
        hist_records=[],
        audit_log=[]
    )
    assert summary["total_canonical_events"] == 1

    # Reload directly from SQLite
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    row = dict(conn.cursor().execute("SELECT * FROM flight_events WHERE event_id='daeb7ccbd61341a2'").fetchone())
    conn.close()

    assert row["record_nature"] == "physical_movement"
    assert row["actual_arr_time"] == "2026-10-09T04:11:00Z"
    assert row["aircraft_registration"] == "JY-RAL"
    assert row["aircraft_icao24"] == "74482C"
    assert "flightradar24" in row["source"]

    # Verify exports match database
    df_csv = pd.read_csv(proc_dir / "all_syrian_flight_events.csv")
    assert len(df_csv) == 1
    assert df_csv.iloc[0]["record_nature"] == "physical_movement"
    assert df_csv.iloc[0]["aircraft_registration"] == "JY-RAL"


def test_repeated_rolling_feed_ingestion_in_isolated_environment(tmp_path, monkeypatch):
    """
    Test 7: Run ingestion repeatedly across 3 rolling cycles in an isolated environment.
    Confirms historical physical movements never disappear or lose verified evidence.
    """
    db_file = tmp_path / "rolling_iso.db"
    setup_isolated_db(db_file)

    proc_dir = tmp_path / "processed"
    rep_dir = tmp_path / "reports"
    raw_dir = tmp_path / "raw"
    proc_dir.mkdir(parents=True, exist_ok=True)
    rep_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("src.aggregator.get_connection", lambda: sqlite3.connect(db_file))
    monkeypatch.setattr("src.aggregator.PROCESSED_DATA_DIR", proc_dir)
    monkeypatch.setattr("src.aggregator.REPORTS_DIR", rep_dir)
    monkeypatch.setattr("src.aggregator.RAW_DATA_DIR", raw_dir)

    # Cycle 0: RJ435 is observed with physical telemetry from radar
    cycle0_event = make_sample_event(
        event_id="daeb7ccbd61341a2",
        flight_number="RJ435",
        flight_date="2026-10-09",
        flight_status="landed",
        record_nature="physical_movement",
        source="damairport_official+aviationstack+flightradar24",
        actual_arr_time="2026-10-09T04:11:00Z",
        aircraft_registration="JY-RAL",
        aircraft_icao24="74482C"
    )
    persist_all_to_database_and_exports([cycle0_event], [], [], [], [])

    # Cycle 1: RJ435 rolled off FR24 rolling buffer. Incoming candidate is portal-only (no telemetry)
    cycle1_candidate = make_sample_event(
        event_id="daeb7ccbd61341a2",
        flight_number="RJ435",
        flight_date="2026-10-09",
        flight_status="landed",
        record_nature="unverified_movement",
        source="damairport_official",
        actual_arr_time=None,
        aircraft_registration=None
    )
    persist_all_to_database_and_exports([cycle1_candidate], [], [], [], [])

    # Cycle 2: RJ435 completely omitted (query date window rolled forward to Oct 11-12)
    cycle2_incoming = [
        make_sample_event(
            event_id="ev_oct12_01",
            airport_id="DAM",
            flight_number="RB501",
            flight_date="2026-10-12",
            flight_status="scheduled",
            record_nature="scheduled_service"
        )
    ]
    persist_all_to_database_and_exports(cycle2_incoming, [], [], [], [])

    # Verify database after 3 cycles
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.cursor().execute("SELECT * FROM flight_events").fetchall()]
    conn.close()

    assert len(rows) == 2, "Both historical RJ435 and new RB501 must be preserved"
    rj = [r for r in rows if r["event_id"] == "daeb7ccbd61341a2"][0]
    assert rj["record_nature"] == "physical_movement", "RJ435 must retain physical_movement"
    assert rj["actual_arr_time"] == "2026-10-09T04:11:00Z", "RJ435 must retain actual touchdown"
    assert rj["aircraft_registration"] == "JY-RAL", "RJ435 must retain registration"
    assert "flightradar24" in rj["source"], "RJ435 must retain radar source provenance"


def test_explicit_retractions_distinguishable_from_feed_disappearance(tmp_path, monkeypatch):
    """
    Test 8: Confirms that explicit cancellations are clearly distinguishable from feed disappearance.
    Disappearance retains physical evidence; cancellation applies retraction with provenance.
    """
    db_file = tmp_path / "retract_iso.db"
    setup_isolated_db(db_file)

    proc_dir = tmp_path / "processed"
    rep_dir = tmp_path / "reports"
    raw_dir = tmp_path / "raw"
    proc_dir.mkdir(parents=True, exist_ok=True)
    rep_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("src.aggregator.get_connection", lambda: sqlite3.connect(db_file))
    monkeypatch.setattr("src.aggregator.PROCESSED_DATA_DIR", proc_dir)
    monkeypatch.setattr("src.aggregator.REPORTS_DIR", rep_dir)
    monkeypatch.setattr("src.aggregator.RAW_DATA_DIR", raw_dir)

    # Initial state: 2 physical flights
    flight_a = make_sample_event(event_id="flt_a", flight_number="RJ100", flight_date="2026-10-10", record_nature="physical_movement", actual_arr_time="2026-10-10T08:00:00Z")
    flight_b = make_sample_event(event_id="flt_b", flight_number="RB200", flight_date="2026-10-10", record_nature="physical_movement", actual_arr_time="2026-10-10T09:00:00Z")
    persist_all_to_database_and_exports([flight_a, flight_b], [], [], [], [])

    # Refresh:
    # Flight A disappeared from incoming feed (feed disappearance)
    # Flight B explicitly retracted / cancelled by source
    incoming_b_cancelled = make_sample_event(
        event_id="flt_b",
        flight_number="RB200",
        flight_date="2026-10-10",
        flight_status="cancelled",
        record_nature="unverified_movement"
    )
    # Incoming only contains Flight B cancelled; Flight A is omitted (disappearance)
    persist_all_to_database_and_exports([incoming_b_cancelled], [], [], [], [])

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    res_a = dict(conn.cursor().execute("SELECT * FROM flight_events WHERE event_id='flt_a'").fetchone())
    res_b = dict(conn.cursor().execute("SELECT * FROM flight_events WHERE event_id='flt_b'").fetchone())
    conn.close()

    # Flight A was merely absent -> retained monotonically as physical
    assert res_a["record_nature"] == "physical_movement"
    assert res_a["flight_status"] == "landed"

    # Flight B had explicit cancellation -> status updated, retraction flagged
    assert res_b["flight_status"] == "cancelled"
    assert res_b["quality_flags"] == "source_retraction_applied"


def test_empty_feed_cannot_erase_historical_events_in_db(tmp_path, monkeypatch):
    """
    Test 9: An empty incoming feed ([]) cannot erase historical events in the database.
    """
    db_file = tmp_path / "empty_feed_iso.db"
    setup_isolated_db(db_file)

    proc_dir = tmp_path / "processed"
    rep_dir = tmp_path / "reports"
    raw_dir = tmp_path / "raw"
    proc_dir.mkdir(parents=True, exist_ok=True)
    rep_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("src.aggregator.get_connection", lambda: sqlite3.connect(db_file))
    monkeypatch.setattr("src.aggregator.PROCESSED_DATA_DIR", proc_dir)
    monkeypatch.setattr("src.aggregator.REPORTS_DIR", rep_dir)
    monkeypatch.setattr("src.aggregator.RAW_DATA_DIR", raw_dir)

    initial_events = [
        make_sample_event(event_id="e1", airport_id="DAM", flight_date="2026-10-01"),
        make_sample_event(event_id="e2", airport_id="ALP", flight_date="2026-10-02"),
        make_sample_event(event_id="e3", airport_id="DEZ", flight_date="2026-10-03"),
    ]
    persist_all_to_database_and_exports(initial_events, [], [], [], [])

    # Re-run persist with completely empty incoming list
    persist_all_to_database_and_exports([], [], [], [], [])

    conn = sqlite3.connect(db_file)
    count = conn.cursor().execute("SELECT count(*) FROM flight_events").fetchone()[0]
    conn.close()

    assert count == 3, "All 3 historical events must survive empty feed re-ingestion"


def test_source_aware_timestamp_priority_fr24_overrides_aviationstack():
    """
    Test 10: Centralized source-aware timestamp priority.
    Tier 4 FR24 radar telemetry (2026-10-09T04:11:54Z, epoch 1791519114) must take
    precedence over Tier 3 AviationStack rounded timestamp (2026-10-09T04:11:00Z).
    Never round or infer precision from ':00'.
    """
    existing_radar_event = make_sample_event(
        event_id="daeb7ccbd61341a2",
        flight_number="RJ435",
        flight_date="2026-10-09",
        source="flightradar24",
        actual_arr_time="2026-10-09T04:11:54Z",
        raw_actual_arr_time="1791519114",
        aircraft_registration="JY-RAL",
        aircraft_icao24="74482C",
        record_nature="physical_movement"
    )

    incoming_aggregator_event = make_sample_event(
        event_id="daeb7ccbd61341a2",
        flight_number="RJ435",
        flight_date="2026-10-09",
        source="aviationstack",
        actual_arr_time="2026-10-09T04:11:00Z",
        raw_actual_arr_time="2026-10-09T07:11:00+00:00",
        record_nature="physical_movement"
    )

    reconciled = reconcile_monotonic_events([incoming_aggregator_event], [existing_radar_event])
    assert len(reconciled) == 1
    rec = reconciled[0]

    # Must preserve exact Tier 4 radar timestamp and epoch telemetry
    assert rec["actual_arr_time"] == "2026-10-09T04:11:54Z"
    assert rec["raw_actual_arr_time"] == "1791519114"
    assert rec["aircraft_registration"] == "JY-RAL"
    assert rec["aircraft_icao24"] == "74482C"


def test_upsert_preserves_historical_records_non_destructively(tmp_path, monkeypatch):
    """
    Test 11: persist_all_to_database_and_exports uses non-destructive SQLite UPSERT.
    Existing records are updated in-place without deleting or dropping other records.
    """
    db_file = tmp_path / "upsert_iso.db"
    setup_isolated_db(db_file)

    proc_dir = tmp_path / "processed"
    rep_dir = tmp_path / "reports"
    raw_dir = tmp_path / "raw"
    proc_dir.mkdir(parents=True, exist_ok=True)
    rep_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("src.aggregator.get_connection", lambda: sqlite3.connect(db_file))
    monkeypatch.setattr("src.aggregator.PROCESSED_DATA_DIR", proc_dir)
    monkeypatch.setattr("src.aggregator.REPORTS_DIR", rep_dir)
    monkeypatch.setattr("src.aggregator.RAW_DATA_DIR", raw_dir)

    initial_events = [
        make_sample_event(event_id="flt_01", airport_id="DAM", flight_number="RJ435", actual_arr_time="2026-10-09T04:11:54Z", record_nature="physical_movement", source="flightradar24"),
        make_sample_event(event_id="flt_02", airport_id="ALP", flight_number="6Q511", record_nature="scheduled_service")
    ]
    persist_all_to_database_and_exports(initial_events, [], [], [], [])

    # Update flt_02 with physical movement, flt_01 remains untouched in the DB
    updated_events = [
        make_sample_event(event_id="flt_02", airport_id="ALP", flight_number="6Q511", actual_arr_time="2026-10-09T08:15:00Z", record_nature="physical_movement", source="alpairport_official")
    ]
    persist_all_to_database_and_exports(updated_events, [], [], [], [])

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    rows = {r["event_id"]: dict(r) for r in conn.cursor().execute("SELECT * FROM flight_events").fetchall()}
    conn.close()

    assert len(rows) == 2
    assert rows["flt_01"]["actual_arr_time"] == "2026-10-09T04:11:54Z"
    assert rows["flt_01"]["record_nature"] == "physical_movement"
    assert rows["flt_02"]["actual_arr_time"] == "2026-10-09T08:15:00Z"
    assert rows["flt_02"]["record_nature"] == "physical_movement"


def test_event_evidence_ledger_immutability_and_deduplication(tmp_path, monkeypatch):
    """
    Test 12: Immutable append-only event_evidence ledger table preserves evidence rows,
    enforces deduplication via UNIQUE constraint, and accumulates evidence without deletions.
    """
    db_file = tmp_path / "evidence_iso.db"
    setup_isolated_db(db_file)

    proc_dir = tmp_path / "processed"
    rep_dir = tmp_path / "reports"
    raw_dir = tmp_path / "raw"
    proc_dir.mkdir(parents=True, exist_ok=True)
    rep_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("src.aggregator.get_connection", lambda: sqlite3.connect(db_file))
    monkeypatch.setattr("src.aggregator.PROCESSED_DATA_DIR", proc_dir)
    monkeypatch.setattr("src.aggregator.REPORTS_DIR", rep_dir)
    monkeypatch.setattr("src.aggregator.RAW_DATA_DIR", raw_dir)

    e1 = make_sample_event(
        event_id="daeb7ccbd61341a2",
        flight_number="RJ435",
        source="flightradar24",
        actual_arr_time="2026-10-09T04:11:54Z",
        raw_actual_arr_time="1791519114",
        aircraft_registration="JY-RAL",
        aircraft_icao24="74482C",
        record_nature="physical_movement"
    )

    # Persist first time
    persist_all_to_database_and_exports([e1], [], [], [], [])

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM event_evidence;")
    cnt1 = cur.fetchone()[0]
    assert cnt1 == 3 # touchdown, registration, icao24

    # Persist second time (idempotency check: should ignore duplicates and not duplicate rows)
    persist_all_to_database_and_exports([e1], [], [], [], [])
    cur.execute("SELECT count(*) FROM event_evidence;")
    cnt2 = cur.fetchone()[0]
    assert cnt2 == cnt1, "Duplicate persistence must not duplicate evidence rows"

    # Persist new flight with evidence
    e2 = make_sample_event(
        event_id="e2_phys",
        flight_number="RB201",
        source="aviationstack",
        actual_arr_time="2026-10-09T10:00:00Z",
        record_nature="physical_movement"
    )
    persist_all_to_database_and_exports([e1, e2], [], [], [], [])
    cur.execute("SELECT count(*) FROM event_evidence;")
    cnt3 = cur.fetchone()[0]
    assert cnt3 == cnt1 + 1, "New physical event must append its evidence to ledger"

    # Verify query by event_id
    cur.execute("SELECT observed_value FROM event_evidence WHERE event_id='daeb7ccbd61341a2' AND evidence_type='adsb_touchdown';")
    row = cur.fetchone()
    assert row[0] == "2026-10-09T04:11:54Z"
    conn.close()


def test_backfill_requires_force_drop_flag(tmp_path, monkeypatch):
    """
    Test 13: scripts/backfill.py safeguards tables by requiring --force-drop flag.
    Calling run_backfill(force_drop=False) calls init_db(drop_existing=False).
    """
    from scripts.backfill import run_backfill
    called = []
    def mock_init_db(drop_existing=False):
        called.append(drop_existing)

    monkeypatch.setattr("scripts.backfill.init_db", mock_init_db)
    monkeypatch.setattr("scripts.backfill.load_and_normalize_all_events", lambda: ([], [], {"total_raw_events":0, "merged_verified_count":0, "flagged_ambiguous_count":0, "split_distinct_leg_count":0}))
    monkeypatch.setattr("scripts.backfill.aggregate_daily_airport_movements", lambda e: [])
    monkeypatch.setattr("scripts.backfill.aggregate_damascus_daily_movements", lambda e: [])
    monkeypatch.setattr("scripts.backfill.load_historical_sem_series", lambda: [])
    monkeypatch.setattr("scripts.backfill.persist_all_to_database_and_exports", lambda **kwargs: {})
    monkeypatch.setattr("scripts.backfill.run_quality_audit", lambda **kwargs: {"overall_status":"PASS","passed_checks":4,"total_checks":4})
    monkeypatch.setattr("scripts.backfill.build_coverage_reports", lambda: None)

    # Without force_drop
    run_backfill(force_drop=False)
    assert called == [False]

    # With force_drop
    run_backfill(force_drop=True)
    assert called == [False, True]


def test_scenario_verified_arrival_disappears_from_fr24(tmp_path, monkeypatch):
    """
    Scenario 1: A previously verified physical arrival later disappears from FR24 rolling buffer.
    Verifies that the flight retains physical_movement, verified touchdown telemetry,
    and flightradar24 provenance.
    """
    db_file = tmp_path / "scen1.db"
    setup_isolated_db(db_file)
    monkeypatch.setattr("src.aggregator.get_connection", lambda: sqlite3.connect(db_file))
    monkeypatch.setattr("src.aggregator.PROCESSED_DATA_DIR", tmp_path / "proc")
    monkeypatch.setattr("src.aggregator.REPORTS_DIR", tmp_path / "rep")
    monkeypatch.setattr("src.aggregator.RAW_DATA_DIR", tmp_path / "raw")

    # Day 1: flight observed on FR24 with exact radar touchdown
    e1 = make_sample_event(
        event_id="flt_fr24_01",
        flight_number="RJ435",
        flight_date="2026-10-09",
        flight_status="landed",
        record_nature="physical_movement",
        source="damairport_official+flightradar24",
        actual_arr_time="2026-10-09T04:11:54Z",
        raw_actual_arr_time="1791519114",
        aircraft_registration="JY-RAL",
        aircraft_icao24="74482C"
    )
    persist_all_to_database_and_exports([e1], [], [], [], [])

    # Day 2: flight disappeared from FR24 rolling buffer, incoming feed is portal-only without telemetry
    e2 = make_sample_event(
        event_id="flt_fr24_01",
        flight_number="RJ435",
        flight_date="2026-10-09",
        flight_status="landed",
        record_nature="unverified_movement",
        source="damairport_official",
        actual_arr_time=None,
        raw_actual_arr_time=None,
        aircraft_registration=None,
        aircraft_icao24=None
    )
    persist_all_to_database_and_exports([e2], [], [], [], [])

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    res = dict(conn.cursor().execute("SELECT * FROM flight_events WHERE event_id='flt_fr24_01'").fetchone())
    ev_count = conn.cursor().execute("SELECT count(*) FROM event_evidence WHERE event_id='flt_fr24_01'").fetchone()[0]
    conn.close()

    assert res["record_nature"] == "physical_movement"
    assert res["actual_arr_time"] == "2026-10-09T04:11:54Z"
    assert res["raw_actual_arr_time"] == "1791519114"
    assert res["aircraft_registration"] == "JY-RAL"
    assert res["aircraft_icao24"] == "74482C"
    assert "flightradar24" in res["source"]
    assert ev_count >= 3


def test_scenario_verified_movement_receives_scheduled_only_update(tmp_path, monkeypatch):
    """
    Scenario 2: A previously verified movement receives a scheduled-only update.
    Verifies that flight_status remains landed and actual timestamps are preserved.
    """
    db_file = tmp_path / "scen2.db"
    setup_isolated_db(db_file)
    monkeypatch.setattr("src.aggregator.get_connection", lambda: sqlite3.connect(db_file))
    monkeypatch.setattr("src.aggregator.PROCESSED_DATA_DIR", tmp_path / "proc")
    monkeypatch.setattr("src.aggregator.REPORTS_DIR", tmp_path / "rep")
    monkeypatch.setattr("src.aggregator.RAW_DATA_DIR", tmp_path / "raw")

    e1 = make_sample_event(
        event_id="flt_sched_up_01",
        flight_number="RB101",
        flight_date="2026-10-09",
        flight_status="landed",
        record_nature="physical_movement",
        actual_arr_time="2026-10-09T14:30:00Z"
    )
    persist_all_to_database_and_exports([e1], [], [], [], [])

    # Scheduled timetable update arrives with status="scheduled" and null actual time
    e2 = make_sample_event(
        event_id="flt_sched_up_01",
        flight_number="RB101",
        flight_date="2026-10-09",
        flight_status="scheduled",
        record_nature="scheduled_service",
        scheduled_arr_time="2026-10-09T14:25:00Z",
        actual_arr_time=None
    )
    persist_all_to_database_and_exports([e2], [], [], [], [])

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    res = dict(conn.cursor().execute("SELECT * FROM flight_events WHERE event_id='flt_sched_up_01'").fetchone())
    conn.close()

    assert res["flight_status"] == "landed"
    assert res["record_nature"] == "physical_movement"
    assert res["actual_arr_time"] == "2026-10-09T14:30:00Z"


def test_scenario_explicit_cancellation_before_any_physical_movement(tmp_path, monkeypatch):
    """
    Scenario 3: A flight is explicitly cancelled before any physical movement.
    Verifies that flight_status becomes cancelled, record_nature remains scheduled_service,
    and no physical evidence is created.
    """
    db_file = tmp_path / "scen3.db"
    setup_isolated_db(db_file)
    monkeypatch.setattr("src.aggregator.get_connection", lambda: sqlite3.connect(db_file))
    monkeypatch.setattr("src.aggregator.PROCESSED_DATA_DIR", tmp_path / "proc")
    monkeypatch.setattr("src.aggregator.REPORTS_DIR", tmp_path / "rep")
    monkeypatch.setattr("src.aggregator.RAW_DATA_DIR", tmp_path / "raw")

    e1 = make_sample_event(
        event_id="flt_cancel_01",
        flight_number="XY301",
        flight_date="2026-10-10",
        flight_status="scheduled",
        record_nature="scheduled_service",
        actual_dep_time=None,
        actual_arr_time=None
    )
    persist_all_to_database_and_exports([e1], [], [], [], [])

    # Cancellation update
    e2 = make_sample_event(
        event_id="flt_cancel_01",
        flight_number="XY301",
        flight_date="2026-10-10",
        flight_status="cancelled",
        record_nature="scheduled_service",
        actual_dep_time=None,
        actual_arr_time=None
    )
    persist_all_to_database_and_exports([e2], [], [], [], [])

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    res = dict(conn.cursor().execute("SELECT * FROM flight_events WHERE event_id='flt_cancel_01'").fetchone())
    ev_count = conn.cursor().execute("SELECT count(*) FROM event_evidence WHERE event_id='flt_cancel_01'").fetchone()[0]
    conn.close()

    assert res["flight_status"] == "cancelled"
    assert res["record_nature"] == "scheduled_service"
    assert res["quality_flags"] == "source_retraction_applied"
    assert ev_count == 0


def test_scenario_verified_departure_later_reported_diverted(tmp_path, monkeypatch):
    """
    Scenario 4: A flight has verified departure telemetry and is later reported diverted.
    Verifies that flight_status reflects 'diverted' while record_nature remains
    'physical_movement' (takeoff actually occurred) and departure telemetry is preserved.
    """
    db_file = tmp_path / "scen4.db"
    setup_isolated_db(db_file)
    monkeypatch.setattr("src.aggregator.get_connection", lambda: sqlite3.connect(db_file))
    monkeypatch.setattr("src.aggregator.PROCESSED_DATA_DIR", tmp_path / "proc")
    monkeypatch.setattr("src.aggregator.REPORTS_DIR", tmp_path / "rep")
    monkeypatch.setattr("src.aggregator.RAW_DATA_DIR", tmp_path / "raw")

    # Flight physically departed Damascus
    e1 = make_sample_event(
        event_id="flt_divert_01",
        airport_id="DAM",
        flight_number="RB501",
        flight_date="2026-10-10",
        movement_type="departure",
        flight_status="departed",
        record_nature="physical_movement",
        source="damairport_official+aviationstack",
        actual_dep_time="2026-10-10T09:15:00Z",
        raw_actual_dep_time="2026-10-10T12:15:00+00:00",
        aircraft_registration="YK-BAB",
        aircraft_icao24="768001"
    )
    persist_all_to_database_and_exports([e1], [], [], [], [])

    # Next update: destination reports flight diverted
    e2 = make_sample_event(
        event_id="flt_divert_01",
        airport_id="DAM",
        flight_number="RB501",
        flight_date="2026-10-10",
        movement_type="departure",
        flight_status="diverted",
        record_nature="unverified_movement",
        source="damairport_official",
        actual_dep_time=None,
        actual_arr_time=None
    )
    persist_all_to_database_and_exports([e2], [], [], [], [])

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    res = dict(conn.cursor().execute("SELECT * FROM flight_events WHERE event_id='flt_divert_01'").fetchone())
    ev_count = conn.cursor().execute("SELECT count(*) FROM event_evidence WHERE event_id='flt_divert_01'").fetchone()[0]
    conn.close()

    # flight_status and record_nature handled independently
    assert res["flight_status"] == "diverted"
    assert res["record_nature"] == "physical_movement"
    assert res["actual_dep_time"] == "2026-10-10T09:15:00Z"
    assert res["aircraft_registration"] == "YK-BAB"
    assert res["aircraft_icao24"] == "768001"
    assert ev_count >= 1


def test_scenario_conflicting_or_lower_quality_actual_timestamp_rejected(tmp_path, monkeypatch):
    """
    Scenario 5: A source sends a conflicting or lower-quality actual timestamp.
    Verifies that Tier 4 radar timestamp is never overwritten by Tier 3 or Tier 2 timestamps.
    """
    db_file = tmp_path / "scen5.db"
    setup_isolated_db(db_file)
    monkeypatch.setattr("src.aggregator.get_connection", lambda: sqlite3.connect(db_file))
    monkeypatch.setattr("src.aggregator.PROCESSED_DATA_DIR", tmp_path / "proc")
    monkeypatch.setattr("src.aggregator.REPORTS_DIR", tmp_path / "rep")
    monkeypatch.setattr("src.aggregator.RAW_DATA_DIR", tmp_path / "raw")

    e1 = make_sample_event(
        event_id="flt_ts_prio_01",
        flight_number="RJ435",
        flight_date="2026-10-09",
        flight_status="landed",
        record_nature="physical_movement",
        source="flightradar24",
        actual_arr_time="2026-10-09T04:11:54Z",
        raw_actual_arr_time="1791519114",
        aircraft_registration="JY-RAL"
    )
    persist_all_to_database_and_exports([e1], [], [], [], [])

    # Lower quality source sends rounded or conflicting time
    e2 = make_sample_event(
        event_id="flt_ts_prio_01",
        flight_number="RJ435",
        flight_date="2026-10-09",
        flight_status="landed",
        record_nature="physical_movement",
        source="aviationstack",
        actual_arr_time="2026-10-09T04:11:00Z",
        raw_actual_arr_time="2026-10-09T07:11:00+00:00",
        aircraft_registration="JY-RAL"
    )
    persist_all_to_database_and_exports([e2], [], [], [], [])

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    res = dict(conn.cursor().execute("SELECT * FROM flight_events WHERE event_id='flt_ts_prio_01'").fetchone())
    conn.close()

    assert res["actual_arr_time"] == "2026-10-09T04:11:54Z"
    assert res["raw_actual_arr_time"] == "1791519114"


def test_scenario_transaction_failure_and_clean_rollback(tmp_path, monkeypatch):
    """
    Scenario 6: A database transaction fails midway and is rolled back.
    Verifies atomic rollback with zero partial writes and zero database corruption.
    """
    db_file = tmp_path / "scen6.db"
    setup_isolated_db(db_file)

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("INSERT INTO flight_events (event_id, flight_number, flight_date, movement_type, flight_status, source) VALUES ('base_01', 'RB101', '2026-10-01', 'arrival', 'landed', 'test');")
    conn.commit()

    # Attempt transaction that fails halfway
    try:
        cur.execute("BEGIN TRANSACTION;")
        cur.execute("INSERT INTO flight_events (event_id, flight_number, flight_date, movement_type, flight_status, source) VALUES ('base_02', 'RB102', '2026-10-02', 'arrival', 'landed', 'test');")
        # Trigger error with invalid duplicate primary key
        cur.execute("INSERT INTO flight_events (event_id, flight_number, flight_date, movement_type, flight_status, source) VALUES ('base_01', 'RB101_DUPLICATE', '2026-10-01', 'arrival', 'landed', 'test');")
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()

    cur.execute("SELECT count(*) FROM flight_events;")
    count = cur.fetchone()[0]
    cur.execute("PRAGMA integrity_check;")
    integrity = cur.fetchone()[0]
    conn.close()

    assert count == 1, "Failed transaction must roll back base_02 cleanly"
    assert integrity == "ok", "Database must remain completely healthy after rollback"


def test_scenario_event_evidence_triggers_prevent_update_and_delete(tmp_path):
    """
    Scenario 7: Verify that UPDATE and DELETE on event_evidence are prohibited by database triggers.
    """
    db_file = tmp_path / "scen7.db"
    setup_isolated_db(db_file)

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO event_evidence (evidence_id, event_id, source_name, evidence_type, observed_value)
    VALUES ('ev_test_1', 'evt_1', 'fr24', 'adsb_touchdown', '2026-10-09T04:11:54Z');
    """)
    conn.commit()

    # Test UPDATE blocked
    update_blocked = False
    try:
        cur.execute("UPDATE event_evidence SET observed_value='altered' WHERE evidence_id='ev_test_1';")
    except (sqlite3.IntegrityError, sqlite3.OperationalError):
        update_blocked = True

    # Test DELETE blocked
    delete_blocked = False
    try:
        cur.execute("DELETE FROM event_evidence WHERE evidence_id='ev_test_1';")
    except (sqlite3.IntegrityError, sqlite3.OperationalError):
        delete_blocked = True

    cur.execute("SELECT count(*) FROM event_evidence;")
    count = cur.fetchone()[0]
    conn.close()

    assert update_blocked, "UPDATE must be aborted by trigger"
    assert delete_blocked, "DELETE must be aborted by trigger"
    assert count == 1, "Evidence row must remain unchanged"


def test_scenario_upsert_preserves_unrelated_events_and_raw_provenance(tmp_path, monkeypatch):
    """
    Scenario 8: UPSERT preserves all unrelated events, raw evidence, and source identifiers.
    """
    db_file = tmp_path / "scen8.db"
    setup_isolated_db(db_file)
    monkeypatch.setattr("src.aggregator.get_connection", lambda: sqlite3.connect(db_file))
    monkeypatch.setattr("src.aggregator.PROCESSED_DATA_DIR", tmp_path / "proc")
    monkeypatch.setattr("src.aggregator.REPORTS_DIR", tmp_path / "rep")
    monkeypatch.setattr("src.aggregator.RAW_DATA_DIR", tmp_path / "raw")

    e1 = make_sample_event(event_id="unrelated_01", airport_id="DAM", flight_number="FL1")
    e2 = make_sample_event(event_id="target_02", airport_id="ALP", flight_number="FL2", raw_json='{"orig":"payload"}')
    e3 = make_sample_event(event_id="unrelated_03", airport_id="DEZ", flight_number="FL3")
    persist_all_to_database_and_exports([e1, e2, e3], [], [], [], [])

    # Re-persist with only an update for target_02
    e2_updated = make_sample_event(
        event_id="target_02",
        airport_id="ALP",
        flight_number="FL2",
        actual_arr_time="2026-10-10T11:00:00Z",
        record_nature="physical_movement"
    )
    persist_all_to_database_and_exports([e2_updated], [], [], [], [])

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    rows = {r["event_id"]: dict(r) for r in conn.cursor().execute("SELECT * FROM flight_events").fetchall()}
    conn.close()

    assert len(rows) == 3, "All 3 events must exist"
    assert rows["unrelated_01"]["flight_number"] == "FL1"
    assert rows["unrelated_03"]["flight_number"] == "FL3"
    assert rows["target_02"]["actual_arr_time"] == "2026-10-10T11:00:00Z"
    assert rows["target_02"]["raw_json"] == '{"orig":"payload"}'



