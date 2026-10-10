import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.database import init_db
from src.normalizer import load_and_normalize_all_events
from src.aggregator import (
    aggregate_damascus_daily_movements,
    load_historical_sem_series,
    persist_all_to_database_and_exports,
)
from src.quality_checker import run_quality_audit
from src.coverage import build_coverage_reports

def run_backfill():
    print("=" * 60)
    print("RUNNING HISTORICAL BACKFILL & DATA ENGINE POPULATION")
    print("Target: Damascus International Airport (IATA: DAM, ICAO: OSDI)")
    print("=" * 60)

    # 1. Initialize SQLite Database
    print("\n[Step 1] Initializing SQLite Database...")
    init_db()

    # 2. Normalize Flight Events
    print("\n[Step 2] Normalizing & Deduplicating Raw Flight Events...")
    events, audit = load_and_normalize_all_events()
    print(f" -> Raw events ingested: {audit['total_raw_events']}")
    print(f" -> Duplicates pruned & merged: {audit['duplicates_pruned']}")
    print(f" -> Normalized Damascus flight events: {len(events)}")

    # 3. Aggregate Damascus Daily Movements
    print("\n[Step 3] Aggregating Damascus Daily Movements...")
    daily_movements = aggregate_damascus_daily_movements(events)
    print(f" -> Damascus daily movement records: {len(daily_movements)}")

    # 4. Load Historical 2024 Series (Syria Economic Monitor)
    print("\n[Step 4] Loading Historical 2024 Time Series (Syria Economic Monitor)...")
    hist_records = load_historical_sem_series()
    print(f" -> Historical 2024 operations records: {len(hist_records)}")

    # 5. Persist to DB and Generate CSV/JSON Exports
    print("\n[Step 5] Persisting to SQLite and Exporting CSV/JSON...")
    summary = persist_all_to_database_and_exports(events, daily_movements, hist_records)
    print(" -> Database and exports updated successfully:")
    for k, v in summary.items():
        print(f"    * {k}: {v}")

    # 6. Run Quality Audit
    print("\n[Step 6] Running Data Quality & Integrity Audit...")
    quality = run_quality_audit(events, daily_movements, hist_records)
    print(f" -> Overall Status: {quality['overall_status']}")
    print(f" -> Passed checks: {quality['passed_checks']}/{quality['total_checks']}")

    # 7. Build Coverage Reports
    print("\n[Step 7] Generating Evidence-Based Coverage Reports...")
    build_coverage_reports()

    print("\n" + "=" * 60)
    print("BACKFILL COMPLETED SUCCESSFULLY")
    print("=" * 60)

if __name__ == '__main__':
    run_backfill()
