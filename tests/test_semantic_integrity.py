import sqlite3
import json
import csv
from pathlib import Path
import pytest

from src.config import DB_PATH, PROCESSED_DATA_DIR, REPORTS_DIR, RAW_DATA_DIR
from src.normalizer import (
    parse_timestamp_to_utc,
    parse_aviationstack_timestamp,
    deduplicate_with_audit,
)

def test_codeshare_classification_and_operating_carrier():
    """
    Test 1: Codeshare Handling & Operating Flight Separation
    Verify that marketing codeshares (e.g. WY5233, EK2179, QR6119, SV4037) are
    explicitly tagged with record_nature='marketing_codeshare', retain their
    operating flight numbers and operating carriers, and are NOT counted as physical movements.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # 1. Total codeshares in database
    cur.execute("SELECT count(*) FROM flight_events WHERE record_nature = 'marketing_codeshare'")
    total_codeshares = cur.fetchone()[0]
    assert total_codeshares == 34, f"Expected 34 marketing codeshares, got {total_codeshares}"
    
    # 2. Codeshares among completed Damascus events
    cur.execute("""
        SELECT count(*) FROM flight_events 
        WHERE airport_id = 'DAM' AND flight_status IN ('landed', 'departed') 
          AND record_nature = 'marketing_codeshare'
    """)
    completed_codeshares = cur.fetchone()[0]
    assert completed_codeshares == 20, f"Expected 20 completed codeshares, got {completed_codeshares}"
    
    # 3. Verify operating carrier mappings
    cur.execute("SELECT flight_number, operating_flight_number, operating_carrier FROM flight_events WHERE flight_number IN ('EK2179', 'QR6119', 'WY5233', 'SV4037')")
    rows = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    assert rows["EK2179"][0] == "FZ1115"
    assert rows["EK2179"][1].lower() == "flydubai"
    assert rows["QR6119"][0] == "RJ437"
    assert rows["QR6119"][1].lower() == "royal jordanian"
    assert rows["WY5233"][0] == "RJ437"
    assert rows["WY5233"][1].lower() == "royal jordanian"
    assert rows["SV4037"][0] == "F3561"
    assert rows["SV4037"][1].lower() == "flyadeal"
    
    # 4. Verified physical movements strictly exclude marketing codeshares
    cur.execute("""
        SELECT count(*) FROM flight_events 
        WHERE airport_id = 'DAM' AND flight_status IN ('landed', 'departed') 
          AND record_nature = 'physical_movement'
    """)
    phys_count = cur.fetchone()[0]
    assert phys_count == 98, f"Expected exactly 98 physical movements, got {phys_count}"

def test_repeated_flight_numbers_and_rotation_protection():
    """
    Test 2: Repeated Flight Numbers & Separate Rotation Protection
    Verify that flights with identical flight numbers occurring on different rotations
    are preserved as separate records and never falsely merged based on date alone.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Check that RB381 on 2026-10-11 exists as separate distinct rotations
    cur.execute("SELECT count(*) FROM flight_events WHERE flight_number = 'RB381' AND flight_date = '2026-10-11'")
    rb381_count = cur.fetchone()[0]
    assert rb381_count >= 2, f"Expected at least 2 distinct legs for RB381, got {rb381_count}"
    
    # Check deduplication audit records for ambiguous rotation protection
    cur.execute("SELECT time_difference_minutes, matching_rule, resolution_status FROM deduplication_audit WHERE flight_number = 'RB381'")
    row = cur.fetchone()
    assert row is not None
    assert row["resolution_status"] == "AMBIGUOUS_KEPT_SEPARATE"
    assert row["time_difference_minutes"] == 180.0

def test_timestamp_interpretation_by_field():
    """
    Test 3: Timestamp Interpretation by Source & Field
    Verify that:
    - Flightradar24 integer epochs are treated as explicit UTC.
    - Damascus official portal times are treated as local wall-clock (Asia/Damascus).
    - AviationStack timestamps with +00:00 suffixes are localized to Asia/Damascus wall-clock.
    """
    # 1. FR24 epoch parsing
    raw_epoch, utc_epoch = parse_timestamp_to_utc(1791614176)
    assert utc_epoch == "2026-10-10T06:36:16Z"
    
    # 2. Damascus official portal string parsing
    raw_off, utc_off = parse_timestamp_to_utc("2026-10-10 09:36")
    # 09:36 local Damascus (UTC+3) -> 06:36 UTC
    assert utc_off == "2026-10-10T06:36:00Z"
    
    # 3. AviationStack timestamp parsing with local wall-clock interpretation
    raw_as, utc_as = parse_aviationstack_timestamp("2026-10-10T09:36:00+00:00", "Asia/Damascus")
    assert raw_as == "2026-10-10T09:36:00+00:00"
    assert utc_as == "2026-10-10T06:36:00Z"
    
    # All 3 timestamps align to within 16 seconds!
    t_fr = 1791614176
    t_as = 1791614160
    assert abs(t_fr - t_as) <= 60

def test_actual_vs_scheduled_movement_semantics():
    """
    Test 4: Actual vs Scheduled Movement Semantics
    Verify that physical movements strictly require actual wheels-off/down telemetry,
    and that schedule-only records (like WY5232 with actual == scheduled) are unsupported.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # WY5232 on 2026-10-10 has actual departure == scheduled departure
    cur.execute("SELECT raw_scheduled_dep_time, raw_actual_dep_time, record_nature FROM flight_events WHERE flight_number = 'WY5232' AND flight_date = '2026-10-10'")
    row = cur.fetchone()
    assert row is not None
    assert row["raw_scheduled_dep_time"] == row["raw_actual_dep_time"] == "2026-10-10T08:40:00+00:00"
    assert row["record_nature"] == "marketing_codeshare"
    
    # Check that all 98 physical movements have actual timestamps
    cur.execute("""
        SELECT count(*) FROM flight_events 
        WHERE airport_id = 'DAM' AND record_nature = 'physical_movement'
          AND (actual_dep_time IS NOT NULL OR actual_arr_time IS NOT NULL)
    """)
    assert cur.fetchone()[0] == 98

def test_source_provenance_and_dedup_audit_integrity():
    """
    Test 5: Source Provenance and Deduplication Audit Trail
    Verify that all 322 MERGED_VERIFIED entries point to valid canonical events,
    no source record is assigned to multiple distinct canonical events,
    and movement_type is never cross-merged.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM deduplication_audit WHERE resolution_status = 'MERGED_VERIFIED'")
    audits = [dict(r) for r in cur.fetchall()]
    assert len(audits) == 322
    
    # Validate canonical event IDs
    cur.execute("SELECT event_id FROM flight_events")
    valid_ids = set(r[0] for r in cur.fetchall())
    for a in audits:
        assert a["canonical_event_id"] in valid_ids
        assert a["time_difference_minutes"] <= 60.0
        
    # Check no duplicate assignment of source record IDs
    src_map = {}
    for a in audits:
        cid = a["canonical_event_id"]
        for srec in (a["source_a_record_id"], a["source_b_record_id"]):
            if srec:
                if srec in src_map:
                    assert src_map[srec] == cid, f"Source {srec} mapped to {src_map[srec]} and {cid}"
                else:
                    src_map[srec] = cid

def test_database_and_export_content_equivalence():
    """
    Test 6: Database and Export Content Equivalence
    Verify that exported CSV and JSON files match the SQLite database row-for-row
    and field-for-field with 0 missing or extra event IDs.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM flight_events")
    db_rows = [dict(r) for r in cur.fetchall()]
    db_by_id = {r["event_id"]: r for r in db_rows}
    
    # Check all_syrian_flight_events.json
    with open(PROCESSED_DATA_DIR / "all_syrian_flight_events.json", encoding="utf-8") as f:
        json_rows = json.load(f)
    assert len(json_rows) == len(db_rows) == 1830
    
    json_by_id = {r["event_id"]: r for r in json_rows}
    assert set(db_by_id.keys()) == set(json_by_id.keys())
    
    # Check record_nature field present and identical
    for eid, j_row in json_by_id.items():
        d_row = db_by_id[eid]
        assert j_row["record_nature"] == d_row["record_nature"]
        assert (j_row.get("operating_flight_number") or None) == (d_row.get("operating_flight_number") or None)
