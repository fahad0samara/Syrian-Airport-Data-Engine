import pytest
import sqlite3
from typing import Dict, Any, List
from datetime import datetime, timezone

from src.normalizer import evaluate_cross_source_match, deduplicate_with_audit, generate_event_id
from src.aggregator import reconcile_monotonic_events, persist_all_to_database_and_exports
from src.database import init_db

def make_test_record(**kwargs) -> Dict[str, Any]:
    base = {
        "event_id": kwargs.get("event_id") or "test_ev_01",
        "airport_id": kwargs.get("airport_id", "ALP"),
        "source": kwargs.get("source", "alpairport_official"),
        "source_record_id": kwargs.get("source_record_id", "rec_001"),
        "movement_type": kwargs.get("movement_type", "arrival"),
        "airport_iata": kwargs.get("airport_id", "ALP"),
        "airport_icao": f"OS{kwargs.get('airport_id', 'ALP')}",
        "connected_airport_iata": "JED",
        "connected_airport_icao": "OEJN",
        "connected_airport_name": "King Abdulaziz International Airport",
        "connected_country": "Saudi Arabia",
        "connected_city": "Jeddah",
        "route_type": "international",
        "airline_name": kwargs.get("airline_name", "Flynas"),
        "airline_iata": "XY",
        "airline_icao": "KNE",
        "flight_number": kwargs.get("flight_number", "XY559"),
        "flight_date": kwargs.get("flight_date", "2026-10-11"),
        "local_operational_date": kwargs.get("flight_date", "2026-10-11"),
        "flight_status": kwargs.get("flight_status", "scheduled"),
        "scheduled_dep_time": kwargs.get("scheduled_dep_time", "2026-10-11T10:40:00Z"),
        "actual_dep_time": kwargs.get("actual_dep_time", None),
        "scheduled_arr_time": kwargs.get("scheduled_arr_time", "2026-10-11T13:00:00Z"),
        "actual_arr_time": kwargs.get("actual_arr_time", None),
        "raw_scheduled_dep_time": kwargs.get("raw_scheduled_dep_time", "1791715200"),
        "raw_actual_dep_time": kwargs.get("raw_actual_dep_time", None),
        "raw_scheduled_arr_time": kwargs.get("raw_scheduled_arr_time", "16:00"),
        "raw_actual_arr_time": kwargs.get("raw_actual_arr_time", None),
        "aircraft_model": kwargs.get("aircraft_model", "32N"),
        "aircraft_registration": kwargs.get("aircraft_registration", None),
        "aircraft_icao24": kwargs.get("aircraft_icao24", None),
        "record_nature": kwargs.get("record_nature", "scheduled_service"),
        "operating_flight_number": kwargs.get("operating_flight_number", kwargs.get("flight_number", "XY559")),
        "operating_carrier": kwargs.get("operating_carrier", kwargs.get("airline_name", "Flynas")),
        "observed_or_derived": "observed",
        "quality_flags": "test_record",
        "normalization_version": "2.1",
        "raw_json": "{}"
    }
    return base

# -------------------------------------------------------------------
# Mandatory Scenarios (1 to 10)
# -------------------------------------------------------------------

def test_scenario_1_xy559_ten_minute_difference():
    """
    Scenario 1: XY559 with a 10-minute difference between sources (13:00 vs 13:10).
    Must evaluate to CONFIRMED_MATCH, merge into a single canonical event,
    and inherit the existing event ID during monotonic reconciliation without creating duplicates.
    """
    rec_official = make_test_record(
        event_id="ae574f20e1161b44",
        source="alpairport_official",
        scheduled_arr_time="2026-10-11T13:00:00Z",
        raw_scheduled_arr_time="16:00"
    )
    rec_fr24 = make_test_record(
        event_id="e17945b69ee79cfa",
        source="flightradar24",
        scheduled_arr_time="2026-10-11T13:10:00Z",
        raw_scheduled_arr_time="1791724200"
    )

    # 1. Match evaluation
    res = evaluate_cross_source_match(rec_official, rec_fr24)
    assert res["can_merge"] is True
    assert res["match_status"] == "CONFIRMED_MATCH"
    assert res["time_diff_minutes"] == 10.0
    assert res["confidence_score"] >= 0.95

    # 2. Normalization deduplication
    events, audit_log, stats = deduplicate_with_audit([rec_official, rec_fr24])
    assert len(events) == 1
    assert stats["merged_verified_count"] == 1
    assert "alpairport_official+flightradar24" in events[0]["source"]

    # 3. Monotonic database reconciliation: Existing DB has e17945b69ee79cfa
    existing_db_record = dict(rec_fr24)
    incoming_cluster = dict(events[0]) # has event_id ae574f20e1161b44

    reconciled = reconcile_monotonic_events([incoming_cluster], [existing_db_record])
    assert len(reconciled) == 1
    # Must inherit the existing DB event ID to prevent duplicate UPSERT rows
    assert reconciled[0]["event_id"] == "e17945b69ee79cfa"

def test_scenario_2_two_distinct_flights_same_number_same_day():
    """
    Scenario 2: Two distinct flights with the same flight number on the same day (e.g. morning vs evening, diff > 180m).
    Must evaluate to SPLIT_DISTINCT_LEG and remain completely separate.
    """
    rec_morning = make_test_record(
        event_id="ev_morning",
        scheduled_arr_time="2026-10-11T06:00:00Z"
    )
    rec_evening = make_test_record(
        event_id="ev_evening",
        scheduled_arr_time="2026-10-11T18:00:00Z"
    )

    res = evaluate_cross_source_match(rec_morning, rec_evening)
    assert res["can_merge"] is False
    assert res["match_status"] == "SPLIT_DISTINCT_LEG"
    assert res["time_diff_minutes"] == 720.0

    events, audit_log, stats = deduplicate_with_audit([rec_morning, rec_evening])
    assert len(events) == 2
    assert stats["split_distinct_leg_count"] == 1

def test_scenario_3_same_flight_number_different_directions():
    """
    Scenario 3: Same flight number on the same day but opposite directions (arrival vs departure).
    Must evaluate to MISMATCH_DIRECTION and never merge.
    """
    rec_arr = make_test_record(event_id="ev_arr", movement_type="arrival")
    rec_dep = make_test_record(event_id="ev_dep", movement_type="departure")

    res = evaluate_cross_source_match(rec_arr, rec_dep)
    assert res["can_merge"] is False
    assert res["match_status"] == "MISMATCH_DIRECTION"

    events, audit_log, stats = deduplicate_with_audit([rec_arr, rec_dep])
    assert len(events) == 2

def test_scenario_4_same_flight_number_different_airports():
    """
    Scenario 4: Same flight number on the same day at different airports (e.g. DAM vs ALP).
    Must evaluate to MISMATCH_AIRPORT and never merge.
    """
    rec_alp = make_test_record(event_id="ev_alp", airport_id="ALP")
    rec_dam = make_test_record(event_id="ev_dam", airport_id="DAM")

    res = evaluate_cross_source_match(rec_alp, rec_dam)
    assert res["can_merge"] is False
    assert res["match_status"] == "MISMATCH_AIRPORT"

    events, audit_log, stats = deduplicate_with_audit([rec_alp, rec_dam])
    assert len(events) == 2

def test_scenario_5_codeshare_and_operating_flight_number():
    """
    Scenario 5: Marketing codeshare matched to operating flight number.
    Recognizes operational relationship without conflicting.
    """
    rec_operating = make_test_record(
        event_id="ev_op",
        flight_number="FZ1115",
        airline_name="flydubai",
        operating_flight_number="FZ1115",
        operating_carrier="flydubai"
    )
    rec_marketing = make_test_record(
        event_id="ev_mkt",
        flight_number="EK2179",
        airline_name="Emirates",
        record_nature="marketing_codeshare",
        operating_flight_number="FZ1115",
        operating_carrier="flydubai"
    )

    res = evaluate_cross_source_match(rec_operating, rec_marketing)
    assert res["can_merge"] is True
    assert res["match_status"] == "CONFIRMED_MATCH"

def test_scenario_6_different_operating_carrier_conflict():
    """
    Scenario 6: Same flight number and time but conflicting carriers with no codeshare link.
    Must evaluate to CONFLICT_CARRIER and remain separate.
    """
    rec_flynas = make_test_record(event_id="ev_fn", airline_name="Flynas", operating_carrier="Flynas")
    rec_syrian = make_test_record(event_id="ev_syr", airline_name="Syrian Air", operating_carrier="Syrian Air")

    res = evaluate_cross_source_match(rec_flynas, rec_syrian)
    assert res["can_merge"] is False
    assert res["match_status"] == "CONFLICT_CARRIER"

    events, audit_log, stats = deduplicate_with_audit([rec_flynas, rec_syrian])
    assert len(events) == 2

def test_scenario_7_missing_scheduled_timestamp():
    """
    Scenario 7: Record lacking scheduled or actual timestamp anchor.
    Must evaluate to POTENTIAL_MATCH_LACKS_TIME and remain separate.
    """
    rec_full = make_test_record(event_id="ev_full", scheduled_arr_time="2026-10-11T13:00:00Z")
    rec_notime = make_test_record(event_id="ev_notime", scheduled_arr_time=None, scheduled_dep_time=None)

    res = evaluate_cross_source_match(rec_full, rec_notime)
    assert res["can_merge"] is False
    assert res["match_status"] == "POTENTIAL_MATCH_LACKS_TIME"

    events, audit_log, stats = deduplicate_with_audit([rec_full, rec_notime])
    assert len(events) == 2
    assert stats["flagged_ambiguous_count"] == 1

def test_scenario_8_different_aircraft_registration_conflict():
    """
    Scenario 8: Conflicting explicit tail registrations (e.g. YK-BAA vs YK-BAB).
    Must evaluate to CONFLICT_REGISTRATION and remain separate.
    """
    rec_tail_a = make_test_record(event_id="ev_tail_a", aircraft_registration="YK-BAA", aircraft_icao24="778801")
    rec_tail_b = make_test_record(event_id="ev_tail_b", aircraft_registration="YK-BAB", aircraft_icao24="778802")

    res = evaluate_cross_source_match(rec_tail_a, rec_tail_b)
    assert res["can_merge"] is False
    assert res["match_status"] == "CONFLICT_REGISTRATION"

    events, audit_log, stats = deduplicate_with_audit([rec_tail_a, rec_tail_b])
    assert len(events) == 2

def test_scenario_9_repeated_reingestion_idempotency():
    """
    Scenario 9: Exact same record re-ingested multiple times.
    Evaluates to CONFIRMED_MATCH with diff = 0 and produces exactly 1 canonical event.
    """
    rec_a = make_test_record(event_id="ev_idemp_1")
    rec_b = make_test_record(event_id="ev_idemp_2")

    res = evaluate_cross_source_match(rec_a, rec_b)
    assert res["can_merge"] is True
    assert res["match_status"] == "CONFIRMED_MATCH"
    assert res["time_diff_minutes"] == 0.0

    events, audit_log, stats = deduplicate_with_audit([rec_a, rec_b])
    assert len(events) == 1

def test_scenario_10_ambiguous_case_kept_separate():
    """
    Scenario 10: Time difference in the ambiguous range (e.g. 120 minutes, within 60m-180m).
    Must evaluate to POTENTIAL_MATCH_AMBIGUOUS_DELTA, be logged for review, and remain separate.
    """
    rec_a = make_test_record(event_id="ev_t1", scheduled_arr_time="2026-10-11T12:00:00Z")
    rec_b = make_test_record(event_id="ev_t2", scheduled_arr_time="2026-10-11T14:00:00Z")

    res = evaluate_cross_source_match(rec_a, rec_b)
    assert res["can_merge"] is False
    assert res["match_status"] == "POTENTIAL_MATCH_AMBIGUOUS_DELTA"
    assert res["time_diff_minutes"] == 120.0

    events, audit_log, stats = deduplicate_with_audit([rec_a, rec_b])
    assert len(events) == 2
    assert stats["flagged_ambiguous_count"] == 1

# -------------------------------------------------------------------
# Data Safety & Non-Harm Verification Tests
# -------------------------------------------------------------------

def test_data_safety_no_scheduled_promoted_to_physical_by_merge_alone():
    """
    Safety check: Merging two scheduled records must NEVER promote the canonical event to physical_movement.
    """
    rec_a = make_test_record(event_id="ev_sch_1", record_nature="scheduled_service", scheduled_arr_time="2026-10-11T13:00:00Z")
    rec_b = make_test_record(event_id="ev_sch_2", record_nature="scheduled_service", scheduled_arr_time="2026-10-11T13:10:00Z")

    events, _, _ = deduplicate_with_audit([rec_a, rec_b])
    assert len(events) == 1
    assert events[0]["record_nature"] == "scheduled_service"
    assert events[0]["actual_arr_time"] is None
    assert events[0]["actual_dep_time"] is None

def test_data_safety_original_raw_timestamps_preserved():
    """
    Safety check: Original source raw timestamps are preserved without modification.
    """
    rec_a = make_test_record(
        event_id="ev_a",
        source="alpairport_official",
        raw_scheduled_arr_time="16:00",
        scheduled_arr_time="2026-10-11T13:00:00Z"
    )
    rec_b = make_test_record(
        event_id="ev_b",
        source="flightradar24",
        raw_scheduled_arr_time="1791724200",
        scheduled_arr_time="2026-10-11T13:10:00Z"
    )

    events, audit_log, _ = deduplicate_with_audit([rec_a, rec_b])
    assert len(events) == 1
    # Check that audit log recorded both original raw timestamps
    assert audit_log[0]["source_a_raw_time"] == "16:00"
    assert audit_log[0]["source_b_raw_time"] == "1791724200"

def test_data_safety_database_persistence_no_duplicate_created(tmp_path, monkeypatch):
    """
    Safety check: Full database persistence test in an isolated SQLite database.
    Verifies that inserting a cycle 1 FR24 event followed by a cycle 2 official event
    updates the record in place under the canonical ID and does NOT duplicate the row.
    """
    test_db = tmp_path / "test_safety.db"
    monkeypatch.setattr("src.aggregator.DB_PATH", test_db)
    monkeypatch.setattr("src.database.DB_PATH", test_db)
    monkeypatch.setattr("src.config.DB_PATH", test_db)
    monkeypatch.setattr("src.aggregator.PROCESSED_DATA_DIR", tmp_path / "processed")
    monkeypatch.setattr("src.aggregator.REPORTS_DIR", tmp_path / "reports")

    init_db(drop_existing=True)
    conn = sqlite3.connect(test_db)
    cur = conn.cursor()

    # Cycle 1: Ingest FR24 record (event_id: e17945b69ee79cfa)
    cycle1_fr24 = make_test_record(
        event_id="e17945b69ee79cfa",
        source="flightradar24",
        scheduled_arr_time="2026-10-11T13:10:00Z"
    )
    persist_all_to_database_and_exports([cycle1_fr24], [], [], [], [])

    cur.execute("SELECT count(*) FROM flight_events")
    assert cur.fetchone()[0] == 1

    # Cycle 2: Ingest Official portal record (newly generated id: ae574f20e1161b44)
    cycle2_official = make_test_record(
        event_id="ae574f20e1161b44",
        source="alpairport_official",
        scheduled_arr_time="2026-10-11T13:00:00Z"
    )
    # Deduplicate candidate
    cycle2_events, audit_log, _ = deduplicate_with_audit([cycle2_official, cycle1_fr24])
    persist_all_to_database_and_exports(cycle2_events, [], [], [], audit_log)

    # CRITICAL VERIFICATION: Must still have exactly 1 record in flight_events!
    cur.execute("SELECT count(*) FROM flight_events")
    total_events = cur.fetchone()[0]
    assert total_events == 1, f"Duplicate created! Expected 1, found {total_events}"

    cur.execute("SELECT event_id, source FROM flight_events")
    row = cur.fetchone()
    assert row[0] == "e17945b69ee79cfa"
    assert "alpairport_official" in row[1]
    assert "flightradar24" in row[1]

    # Verify PRAGMA integrity_check and foreign_keys
    cur.execute("PRAGMA integrity_check")
    assert cur.fetchone()[0] == "ok"
    conn.close()

# -------------------------------------------------------------------
# Flight-Specific Invariant & Regression Tests (RB272, FYC501, J9178, VF318)
# -------------------------------------------------------------------

def test_regression_rb272_never_flips_direction_or_merges_arrival():
    """
    RB272 Damascus departure (LY-MAU) must NEVER merge with an arrival record
    or have its direction mutated from departure to arrival.
    """
    rec_dep = make_test_record(
        event_id="rb272_dep",
        airport_id="DAM",
        movement_type="departure",
        flight_number="RB272",
        airline_name="Syrian Air",
        aircraft_registration="LY-MAU",
        aircraft_icao24="503D4D",
        scheduled_dep_time="2026-10-10T14:00:00Z",
        actual_dep_time="2026-10-10T14:30:00Z"
    )
    rec_arr = make_test_record(
        event_id="rb272_arr",
        airport_id="DAM",
        movement_type="arrival",
        flight_number="RB272",
        airline_name="Syrian Air",
        aircraft_registration="YK-BAF",
        scheduled_arr_time="2026-10-10T14:00:00Z"
    )

    res = evaluate_cross_source_match(rec_dep, rec_arr)
    assert res["can_merge"] is False
    assert res["match_status"] == "MISMATCH_DIRECTION"

    events, audit, stats = deduplicate_with_audit([rec_dep, rec_arr])
    assert len(events) == 2
    assert {e["movement_type"] for e in events} == {"departure", "arrival"}

def test_regression_fyc501_tail_conflict_prevents_merge():
    """
    FYC501 Damascus departure with confirmed tail YK-BAC must NEVER merge
    with a conflicting tail YK-BAA.
    """
    rec_bac = make_test_record(
        event_id="fyc_bac",
        airport_id="DAM",
        movement_type="departure",
        flight_number="FYC501",
        airline_name="Fly Cham",
        aircraft_registration="YK-BAC",
        aircraft_icao24="778823",
        scheduled_dep_time="2026-10-10T15:30:00Z",
        actual_dep_time="2026-10-10T15:31:43Z"
    )
    rec_baa = make_test_record(
        event_id="fyc_baa",
        airport_id="DAM",
        movement_type="departure",
        flight_number="FYC501",
        airline_name="Fly Cham",
        aircraft_registration="YK-BAA",
        aircraft_icao24="778801",
        scheduled_dep_time="2026-10-10T15:30:00Z"
    )

    res = evaluate_cross_source_match(rec_bac, rec_baa)
    assert res["can_merge"] is False
    assert res["match_status"] == "CONFLICT_REGISTRATION"

    events, audit, stats = deduplicate_with_audit([rec_bac, rec_baa])
    assert len(events) == 2
    assert {e["aircraft_registration"] for e in events} == {"YK-BAC", "YK-BAA"}

def test_regression_j9178_direction_and_tail_protection():
    """
    J9178 Damascus departure with confirmed tail 9K-CBG must NEVER merge
    with an arrival record or a conflicting tail 9K-CAE.
    """
    rec_cbg = make_test_record(
        event_id="j9_cbg",
        airport_id="DAM",
        movement_type="departure",
        flight_number="J9178",
        airline_name="Jazeera Airways",
        aircraft_registration="9K-CBG",
        aircraft_icao24="70612D",
        scheduled_dep_time="2026-10-10T14:45:00Z",
        actual_dep_time="2026-10-10T14:47:26Z"
    )
    rec_cae_arr = make_test_record(
        event_id="j9_cae",
        airport_id="DAM",
        movement_type="arrival",
        flight_number="J9178",
        airline_name="Jazeera Airways",
        aircraft_registration="9K-CAE",
        scheduled_arr_time="2026-10-10T14:45:00Z"
    )

    res_arr = evaluate_cross_source_match(rec_cbg, rec_cae_arr)
    assert res_arr["can_merge"] is False
    assert res_arr["match_status"] == "MISMATCH_DIRECTION"

    rec_cae_dep = make_test_record(
        event_id="j9_cae_dep",
        airport_id="DAM",
        movement_type="departure",
        flight_number="J9178",
        airline_name="Jazeera Airways",
        aircraft_registration="9K-CAE",
        scheduled_dep_time="2026-10-10T14:45:00Z"
    )
    res_reg = evaluate_cross_source_match(rec_cbg, rec_cae_dep)
    assert res_reg["can_merge"] is False
    assert res_reg["match_status"] == "CONFLICT_REGISTRATION"

def test_regression_vf318_airport_and_tail_isolation():
    """
    VF318 Damascus departure with confirmed tail TC-JGY must NEVER merge
    with Aleppo (ALP) or a conflicting tail TC-CPJ.
    """
    rec_dam = make_test_record(
        event_id="vf_dam",
        airport_id="DAM",
        movement_type="departure",
        flight_number="VF318",
        airline_name="AJet",
        aircraft_registration="TC-JGY",
        aircraft_icao24="4BA8F9",
        scheduled_dep_time="2026-10-10T14:00:00Z",
        actual_dep_time="2026-10-10T14:55:00Z"
    )
    rec_alp = make_test_record(
        event_id="vf_alp",
        airport_id="ALP",
        movement_type="arrival",
        flight_number="VF318",
        airline_name="AJet",
        aircraft_registration="TC-CPJ",
        scheduled_arr_time="2026-10-10T14:00:00Z"
    )

    res_alp = evaluate_cross_source_match(rec_dam, rec_alp)
    assert res_alp["can_merge"] is False
    assert res_alp["match_status"] == "MISMATCH_AIRPORT"

    rec_dam_cpj = make_test_record(
        event_id="vf_cpj",
        airport_id="DAM",
        movement_type="departure",
        flight_number="VF318",
        airline_name="AJet",
        aircraft_registration="TC-CPJ",
        scheduled_dep_time="2026-10-10T14:00:00Z"
    )
    res_reg = evaluate_cross_source_match(rec_dam, rec_dam_cpj)
    assert res_reg["can_merge"] is False
    assert res_reg["match_status"] == "CONFLICT_REGISTRATION"

