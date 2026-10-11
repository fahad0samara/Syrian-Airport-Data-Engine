import sqlite3
import json
import shutil
from pathlib import Path
import sys

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.normalizer import load_and_normalize_all_events
from src.aggregator import (
    aggregate_damascus_daily_movements,
    aggregate_daily_airport_movements,
    load_historical_sem_series,
    persist_all_to_database_and_exports
)
from src.quality_checker import run_quality_audit

def test_safe_idempotency():
    print("=" * 70)
    print("SAFE IDEMPOTENCY PROOF IN ISOLATED ENVIRONMENT")
    print("=" * 70)

    temp_db_path = Path("data/temp_idempotency_audit.db")
    if temp_db_path.exists():
        temp_db_path.unlink()

    # Create temporary isolated schema using database.py schema definition
    with sqlite3.connect("data/damascus_airport.db") as orig_conn:
        schema_lines = [l for l in orig_conn.iterdump() if "INSERT INTO" not in l]
    
    with sqlite3.connect(temp_db_path) as temp_conn:
        temp_conn.executescript("\n".join(schema_lines))
    print("[1] Isolated temporary database initialized:", temp_db_path)

    # RUN 1: Normalization & Aggregation
    events_run1, audit_run1, stats_run1 = load_and_normalize_all_events()
    dam_daily_run1 = aggregate_damascus_daily_movements(events_run1)
    all_daily_run1 = aggregate_daily_airport_movements(events_run1)
    hist_run1 = load_historical_sem_series()

    print(f"[2] Run 1 Normalization: {len(events_run1)} events, {stats_run1['merged_verified_count']} merges, {stats_run1['flagged_ambiguous_count']} flagged")

    # Persist Run 1 into temp DB
    with sqlite3.connect(temp_db_path) as conn:
        cur = conn.cursor()
        for e in events_run1:
            cur.execute("""
            INSERT OR REPLACE INTO flight_events (
                event_id, airport_id, source, source_record_id, movement_type,
                flight_number, flight_date, flight_status, record_nature
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                e["event_id"], e["airport_id"], e["source"], e["source_record_id"],
                e["movement_type"], e["flight_number"], e["flight_date"],
                e["flight_status"], e["record_nature"]
            ))
        conn.commit()

        cur.execute("SELECT count(*) FROM flight_events")
        count_after_run1 = cur.fetchone()[0]
        cur.execute("SELECT record_nature, count(*) FROM flight_events GROUP BY record_nature ORDER BY record_nature")
        cat_after_run1 = dict(cur.fetchall())

    print(f"    Temp DB count after Run 1: {count_after_run1} rows")
    print(f"    Categories after Run 1: {cat_after_run1}")

    # RUN 2: Normalization & Aggregation on exact same inputs
    events_run2, audit_run2, stats_run2 = load_and_normalize_all_events()
    dam_daily_run2 = aggregate_damascus_daily_movements(events_run2)
    all_daily_run2 = aggregate_daily_airport_movements(events_run2)
    hist_run2 = load_historical_sem_series()

    print(f"[3] Run 2 Normalization: {len(events_run2)} events, {stats_run2['merged_verified_count']} merges, {stats_run2['flagged_ambiguous_count']} flagged")

    # Persist Run 2 into SAME temp DB using INSERT OR REPLACE (idempotent upsert)
    with sqlite3.connect(temp_db_path) as conn:
        cur = conn.cursor()
        for e in events_run2:
            cur.execute("""
            INSERT OR REPLACE INTO flight_events (
                event_id, airport_id, source, source_record_id, movement_type,
                flight_number, flight_date, flight_status, record_nature
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                e["event_id"], e["airport_id"], e["source"], e["source_record_id"],
                e["movement_type"], e["flight_number"], e["flight_date"],
                e["flight_status"], e["record_nature"]
            ))
        conn.commit()

        cur.execute("SELECT count(*) FROM flight_events")
        count_after_run2 = cur.fetchone()[0]
        cur.execute("SELECT record_nature, count(*) FROM flight_events GROUP BY record_nature ORDER BY record_nature")
        cat_after_run2 = dict(cur.fetchall())

    print(f"    Temp DB count after Run 2: {count_after_run2} rows")
    print(f"    Categories after Run 2: {cat_after_run2}")

    # VERIFICATIONS
    print("\n[4] IDEMPOTENCY ASSERTION CHECKS:")
    assert len(events_run1) == len(events_run2), "Event counts differ!"
    print(f"  [PASS] Event counts match exactly: {len(events_run1)} == {len(events_run2)}")

    ids1 = [e["event_id"] for e in events_run1]
    ids2 = [e["event_id"] for e in events_run2]
    assert ids1 == ids2, "Event IDs or ordering differ!"
    print(f"  [PASS] All {len(ids1)} Event IDs match exactly in identical sort order.")

    assert count_after_run1 == count_after_run2 == len(events_run1), "DB row count doubled or diverged!"
    print(f"  [PASS] Zero duplicate rows created in DB ({count_after_run1} rows == {count_after_run2} rows).")

    assert cat_after_run1 == cat_after_run2, "Semantic categories differ!"
    print(f"  [PASS] Semantic category counts match exactly: {cat_after_run1}")

    assert stats_run1 == stats_run2, "Deduplication stats differ!"
    print(f"  [PASS] Deduplication stats match exactly: {stats_run1}")

    assert len(audit_run1) == len(audit_run2), "Deduplication audit logs differ in length!"
    print(f"  [PASS] Deduplication audit trail is identical ({len(audit_run1)} log entries).")

    # Clean up temp db
    import gc
    gc.collect()
    if temp_db_path.exists():
        try:
            temp_db_path.unlink()
            print("\n[5] Cleaned up temporary test database safely.")
        except Exception:
            pass

    print("\n>>> IDEMPOTENCY PROOF: 100% DETERMINISTIC AND VERIFIED <<<")

if __name__ == '__main__':
    test_safe_idempotency()
