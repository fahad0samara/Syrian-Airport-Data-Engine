"""
Source-Specific Timezone Handling and Deduplication Reconciliation Tests

Verifies:
1. Genuine UTC timestamps (unix epoch, 'Z', numeric offset).
2. Genuine Damascus local timestamps (timezone-naive localized to Asia/Damascus).
3. Incorrectly labelled local timestamps (AviationStack +00:00 source-specific pattern).
4. Day-boundary and date rollover cases (preserving local operational date).
5. Ambiguous timestamps (None, empty, corrupt strings).
6. Idempotent normalization and deduplication.
7. Reconciled canonical flight counts (1,830 canonical, 121 DAM completed, 98 verified ground movements).
8. Reconciled codeshare records (20 explicit marketing codeshares).
"""

import sqlite3
import json
from src.config import DB_PATH
from src.normalizer import (
    parse_timestamp_to_utc,
    parse_aviationstack_timestamp,
    load_and_normalize_all_events,
)

def test_genuine_utc_timestamps():
    """Verify genuine UTC timestamp parsing for unix epoch, 'Z', and explicit offset."""
    # 1. Unix epoch integer (Flightradar24 real touchdown timestamp)
    raw_val, utc_iso = parse_timestamp_to_utc(1791529373)
    assert utc_iso == "2026-10-09T07:02:53Z"
    assert raw_val == "1791529373"

    # 2. ISO string with explicit 'Z'
    raw_val, utc_iso = parse_timestamp_to_utc("2026-10-09T07:02:53Z")
    assert utc_iso == "2026-10-09T07:02:53Z"

    # 3. ISO string with explicit numeric UTC offset (+03:00)
    raw_val, utc_iso = parse_timestamp_to_utc("2026-10-09T10:02:53+03:00")
    assert utc_iso == "2026-10-09T07:02:53Z"

def test_genuine_damascus_local_timestamps():
    """Verify timezone-naive local timestamps from official portal are localized to Asia/Damascus."""
    raw_val, utc_iso = parse_timestamp_to_utc("2026-10-09 16:35")
    # 16:35 local Damascus (+03:00) is 13:35 UTC
    assert utc_iso == "2026-10-09T13:35:00Z"
    assert raw_val == "2026-10-09 16:35"

    raw_val, utc_iso = parse_timestamp_to_utc("2026-10-10 23:00")
    # 23:00 local Damascus (+03:00) is 20:00 UTC
    assert utc_iso == "2026-10-10T20:00:00Z"

def test_aviationstack_source_specific_timezone_pattern():
    """Verify AviationStack local wall-clock string with erroneous +00:00 suffix is properly corrected."""
    raw_str = "2026-10-09T10:02:00+00:00"
    raw_val, utc_iso = parse_aviationstack_timestamp(raw_str, "Asia/Damascus")
    # 10:02 wall clock in Asia/Damascus (+03:00) is 07:02 UTC
    assert raw_val == "2026-10-09T10:02:00+00:00"
    assert utc_iso == "2026-10-09T07:02:00Z"

    # Verify generic parser does not blindly subtract 3 hours for non-AviationStack strings
    raw_gen, utc_gen = parse_timestamp_to_utc(raw_str)
    assert utc_gen == "2026-10-09T10:02:00Z" # Standard parser preserves explicit +00:00

def test_day_boundary_and_date_rollover_cases():
    """Verify late-night departures do not roll over to the next day when localized to Damascus."""
    # Flight RB443 scheduled at 23:00 local Damascus time on 2026-10-10
    raw_str = "2026-10-10T23:00:00+00:00"
    raw_val, utc_iso = parse_aviationstack_timestamp(raw_str, "Asia/Damascus")
    assert utc_iso == "2026-10-10T20:00:00Z"

    # Early morning arrival at 01:15 local time (22:15 UTC previous day)
    raw_str_arr = "2026-10-10T01:15:00+00:00"
    raw_val, utc_iso_arr = parse_aviationstack_timestamp(raw_str_arr, "Asia/Damascus")
    assert utc_iso_arr == "2026-10-09T22:15:00Z"

def test_ambiguous_and_corrupt_timestamps():
    """Verify ambiguous, corrupt, or missing timestamps return None gracefully without raising exceptions."""
    raw_val, utc_iso = parse_aviationstack_timestamp("corrupt-time-format", "Asia/Damascus")
    assert utc_iso is None
    assert raw_val == "corrupt-time-format"

    raw_val, utc_iso = parse_aviationstack_timestamp(None)
    assert utc_iso is None

    raw_val, utc_iso = parse_aviationstack_timestamp("")
    assert utc_iso is None

def test_idempotent_normalization_and_deduplication():
    """Verify repeated runs of normalization and deduplication produce identical canonical results."""
    run1_events, run1_audit, run1_stats = load_and_normalize_all_events()
    run2_events, run2_audit, run2_stats = load_and_normalize_all_events()

    assert len(run1_events) == len(run2_events) == 1830
    assert run1_stats["merged_verified_count"] == run2_stats["merged_verified_count"] == 322
    assert run1_stats["flagged_ambiguous_count"] == run2_stats["flagged_ambiguous_count"] == 15
    assert len(run1_audit) == len(run2_audit) == 337

    for idx in range(min(50, len(run1_events))):
        assert run1_events[idx]["event_id"] == run2_events[idx]["event_id"]
        assert run1_events[idx]["flight_number"] == run2_events[idx]["flight_number"]
        assert run1_events[idx]["scheduled_dep_time"] == run2_events[idx]["scheduled_dep_time"]
        assert run1_events[idx]["scheduled_arr_time"] == run2_events[idx]["scheduled_arr_time"]

def test_reconciled_canonical_counts_in_database():
    """Verify database reflects reconciled counts (1,830 canonical, 121 DAM completed, 98 verified ground)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Total canonical events
    c.execute("SELECT count(*) FROM flight_events")
    assert c.fetchone()[0] == 1830

    # Damascus completed canonical events (121)
    c.execute("""
        SELECT count(*) FROM flight_events
        WHERE airport_id = 'DAM' AND flight_status IN ('landed', 'departed')
    """)
    assert c.fetchone()[0] == 121

    # Verified ground movements with Flightradar24 radar telemetry (98: 48 arr, 50 dep)
    c.execute("""
        SELECT movement_type, count(*) FROM flight_events
        WHERE airport_id = 'DAM' AND source LIKE '%flightradar24%' AND flight_status IN ('landed', 'departed')
        GROUP BY movement_type
    """)
    by_type = dict(c.fetchall())
    assert by_type["arrival"] == 48
    assert by_type["departure"] == 50
    assert sum(by_type.values()) == 98

def test_codeshare_reconciliation():
    """Verify exactly 20 marketing codeshares are preserved and reconciled without double-counting."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        SELECT event_id, flight_number, flight_date, raw_json
        FROM flight_events
        WHERE airport_id = 'DAM' AND source = 'aviationstack' AND flight_status IN ('landed', 'departed')
    """)
    rows = c.fetchall()

    codeshare_eids = []
    for r in rows:
        raw = json.loads(r[3])
        cs = raw.get("flight", {}).get("codeshared")
        if cs:
            codeshare_eids.append((r[1], cs.get("flight_iata", "").upper()))

    # Exactly 20 marketing codeshares
    assert len(codeshare_eids) == 20

    # Ensure operating carrier flights are identified
    operating_flights = {op for _, op in codeshare_eids}
    assert "FZ1115" in operating_flights
    assert "FZ1116" in operating_flights
    assert "RJ435" in operating_flights
    assert "RJ436" in operating_flights
    assert "RJ437" in operating_flights
    assert "RJ438" in operating_flights
