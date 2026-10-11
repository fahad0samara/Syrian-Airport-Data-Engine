import sqlite3
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import sys

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.config import DB_PATH, RAW_DATA_DIR, PROCESSED_DATA_DIR
from scripts.daily_refresh import run_daily_refresh

def get_db_snapshot():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM flight_events")
    total_events = cur.fetchone()[0]

    cur.execute("SELECT airport_id, COUNT(*) FROM flight_events GROUP BY airport_id ORDER BY airport_id")
    by_airport = dict(cur.fetchall())

    cur.execute("SELECT record_nature, COUNT(*) FROM flight_events GROUP BY record_nature ORDER BY record_nature")
    by_nature = dict(cur.fetchall())

    cur.execute("SELECT airport_id, COUNT(*) FROM flight_events WHERE record_nature = 'physical_movement' GROUP BY airport_id ORDER BY airport_id")
    phys_by_airport = dict(cur.fetchall())

    cur.execute("SELECT event_id, airport_id, flight_number, movement_type, flight_date, flight_status, record_nature, source FROM flight_events")
    events_map = {r["event_id"]: dict(r) for r in cur.fetchall()}

    cur.execute("SELECT MAX(run_timestamp) FROM ingestion_runs WHERE status IN ('SUCCESS', 'EMPTY')")
    latest_ingest = cur.fetchone()[0]

    cur.execute("SELECT source_id, provider_name, freshness_indicator, last_successful_retrieval FROM source_registry")
    sources = [dict(r) for r in cur.fetchall()]

    conn.close()

    raw_hashes = {}
    for p in sorted(RAW_DATA_DIR.glob("*.json")):
        raw_hashes[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()

    return {
        "total_events": total_events,
        "by_airport": by_airport,
        "by_nature": by_nature,
        "phys_by_airport": phys_by_airport,
        "events_map": events_map,
        "latest_ingest": latest_ingest,
        "sources": sources,
        "raw_hashes": raw_hashes
    }

def run_monitored_trial_step(run_number: int):
    print("=" * 70)
    print(f"STARTING MONITORED OPERATIONS TRIAL — RUN {run_number} (DAY {run_number})")
    print("=" * 70)

    # 1. Capture Pre-Run State
    print("\n[1] Capturing Pre-Run Baseline State...")
    pre = get_db_snapshot()
    print(f"  Pre-run events: {pre['total_events']}")
    print(f"  Pre-run categories: {pre['by_nature']}")
    print(f"  Pre-run physical movements: {pre['phys_by_airport']}")
    print(f"  Latest ingestion timestamp: {pre['latest_ingest']}")
    print(f"  Tracked raw files: {len(pre['raw_hashes'])}")

    # 2. Execute Refresh
    start_utc = datetime.now(timezone.utc)
    start_local = datetime.now()
    start_t = time.time()
    print(f"\n[2] Executing Daily Refresh at {start_local.isoformat()} ({start_utc.isoformat()})...")

    exit_code = 0
    err_msg = None
    try:
        success = run_daily_refresh()
        exit_code = 0 if success else 1
    except Exception as e:
        exit_code = 1
        err_msg = str(e)

    duration = round(time.time() - start_t, 2)
    end_utc = datetime.now(timezone.utc)
    end_local = datetime.now()
    print(f"  Refresh finished in {duration}s with exit code {exit_code} (Error: {err_msg})")

    # 3. Capture Post-Run State
    print("\n[3] Capturing Post-Run State and Evaluating Deltas...")
    post = get_db_snapshot()
    print(f"  Post-run events: {post['total_events']} (delta: {post['total_events'] - pre['total_events']:+d})")
    print(f"  Post-run categories: {post['by_nature']}")
    print(f"  Post-run physical movements: {post['phys_by_airport']}")

    # Added / Removed / Changed
    added_ids = set(post["events_map"].keys()) - set(pre["events_map"].keys())
    removed_ids = set(pre["events_map"].keys()) - set(post["events_map"].keys())
    common_ids = set(pre["events_map"].keys()) & set(post["events_map"].keys())

    changed_events = []
    for eid in common_ids:
        b = pre["events_map"][eid]
        a = post["events_map"][eid]
        diff = {k: (b[k], a[k]) for k in b if b[k] != a[k]}
        if diff:
            changed_events.append({"event_id": eid, "flight": b["flight_number"], "diff": diff})

    print(f"  Added canonical events: {len(added_ids)}")
    for eid in sorted(added_ids)[:5]:
        e = post["events_map"][eid]
        print(f"    + Added {eid}: {e['flight_number']} ({e['airport_id']}) {e['movement_type']} {e['flight_date']} [{e['record_nature']}]")

    print(f"  Removed canonical events: {len(removed_ids)}")
    for eid in sorted(removed_ids):
        e = pre["events_map"][eid]
        print(f"    - Removed {eid}: {e['flight_number']} ({e['airport_id']})")

    print(f"  Modified canonical events: {len(changed_events)}")
    for c in changed_events[:5]:
        print(f"    ~ Modified {c['event_id']} ({c['flight']}): {c['diff']}")

    # Ingestion runs from this execution
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
    SELECT run_id, run_timestamp, source_id, airport_id, status, records_fetched, payload_hash, http_status, duration_seconds
    FROM ingestion_runs
    WHERE run_timestamp >= ?
    ORDER BY run_timestamp ASC
    """, (start_utc.isoformat(),))
    current_runs = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT check_name, passed, details FROM data_quality_audit ORDER BY rowid DESC LIMIT 10")
    qa_checks = [dict(r) for r in cur.fetchall()]
    conn.close()

    print(f"\n[4] Logged Ingestion Runs ({len(current_runs)} runs in this execution):")
    for r in current_runs:
        print(f"  {r['source_id']} ({r['airport_id']}): {r['status']} | {r['records_fetched']} records | HTTP {r['http_status']} | hash: {r['payload_hash'][:12] if r['payload_hash'] else 'None'} | {r['duration_seconds']}s")

    # Exports check
    exports_ok = (
        (PROCESSED_DATA_DIR / "all_syrian_flight_events.csv").exists() and
        (PROCESSED_DATA_DIR / "all_syrian_flight_events.json").exists() and
        (PROCESSED_DATA_DIR / "damascus_daily_movements.csv").exists() and
        (Path("reports/coverage_report.csv")).exists()
    )
    print(f"\n[5] Exports generation status: {'SUCCESS (All files updated)' if exports_ok else 'FAILED'}")

    res = {
        "run_number": run_number,
        "start_local": start_local.isoformat(),
        "start_utc": start_utc.isoformat(),
        "end_local": end_local.isoformat(),
        "end_utc": end_utc.isoformat(),
        "duration_seconds": duration,
        "exit_code": exit_code,
        "pre_state": pre,
        "post_state": post,
        "added_events": [post["events_map"][eid] for eid in sorted(added_ids)],
        "removed_events": [pre["events_map"][eid] for eid in sorted(removed_ids)],
        "changed_events": changed_events,
        "ingestion_runs": current_runs,
        "qa_checks": qa_checks,
        "exports_ok": exports_ok
    }
    return res

if __name__ == '__main__':
    res = run_monitored_trial_step(1)
    print("\nMonitored Trial Step 1 finished successfully.")
