import sys
import argparse
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.database import init_db
from src.normalizer import load_and_normalize_all_events
from src.aggregator import (
    aggregate_damascus_daily_movements,
    aggregate_daily_airport_movements,
    load_historical_sem_series,
    persist_all_to_database_and_exports,
)
from src.quality_checker import run_quality_audit
from src.coverage import build_coverage_reports

def run_backfill(force_drop: bool = False):
    print("=" * 60)
    print("RUNNING SYRIAN AIRPORTS DATA ENGINE BACKFILL & POPULATION")
    print("Scope: All Syrian Aerodromes + Damascus Deep-Dive")
    print("=" * 60)

    # 1. Initialize SQLite Database & Registry
    if force_drop:
        print("\n[Step 1] Initializing SQLite Database (FORCE DROP requested)...")
        init_db(drop_existing=True)
    else:
        print("\n[Step 1] Initializing SQLite Database (Non-destructive init/migration)...")
        init_db(drop_existing=False)

    # 2. Normalize Flight Events
    print("\n[Step 2] Normalizing & Deduplicating Raw Flight Events Across All Syrian Airports...")
    events, audit_log, audit_summary = load_and_normalize_all_events()
    print(f" -> Raw events ingested: {audit_summary['total_raw_events']}")
    print(f" -> Verified merged duplicates: {audit_summary['merged_verified_count']}")
    print(f" -> Flagged ambiguous comparisons (kept separate): {audit_summary['flagged_ambiguous_count']}")
    print(f" -> Distinct flight legs / operations: {audit_summary['split_distinct_leg_count']}")
    print(f" -> Total canonical flight events: {len(events)}")

    # 3. Aggregate Daily Movements
    print("\n[Step 3] Aggregating Independent Daily Movements Per Airport...")
    all_daily_movements = aggregate_daily_airport_movements(events)
    dam_daily_movements = aggregate_damascus_daily_movements(events)
    print(f" -> All Syrian airports daily movement records: {len(all_daily_movements)}")
    print(f" -> Damascus specific daily movement records: {len(dam_daily_movements)}")

    # 4. Load Historical 2024 Series (Syria Economic Monitor)
    print("\n[Step 4] Loading Historical 2024 Multi-Airport Gateway Time Series (DAM_ALP_LTK)...")
    hist_records = load_historical_sem_series()
    print(f" -> Historical 2024 operations records (DAM_ALP_LTK combined): {len(hist_records)}")

    # 5. Persist to DB and Generate CSV/JSON Exports
    print("\n[Step 5] Persisting to SQLite and Exporting CSV/JSON...")
    summary = persist_all_to_database_and_exports(
        events=events,
        dam_daily_movements=dam_daily_movements,
        all_daily_movements=all_daily_movements,
        hist_records=hist_records,
        audit_log=audit_log
    )
    print(" -> Database and exports updated successfully:")
    for k, v in summary.items():
        print(f"    * {k}: {v}")

    # 6. Run Quality Audit
    print("\n[Step 6] Running Data Quality & Integrity Audit...")
    quality = run_quality_audit(
        events=events,
        dam_daily_movements=dam_daily_movements,
        hist_records=hist_records,
        all_daily_movements=all_daily_movements,
        persist=True
    )
    print(f" -> Overall Status: {quality['overall_status']}")
    print(f" -> Passed checks: {quality['passed_checks']}/{quality['total_checks']}")

    # 7. Build Coverage Reports
    print("\n[Step 7] Generating Evidence-Based Coverage Reports...")
    build_coverage_reports()

    print("\n" + "=" * 60)
    print("BACKFILL COMPLETED SUCCESSFULLY")
    print("=" * 60)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Syrian Airport Data Engine backfill pipeline.")
    parser.add_argument(
        "--force-drop",
        action="store_true",
        help="Explicitly allow dropping and recreating existing database tables. Without this flag, backfill operates non-destructively."
    )
    args = parser.parse_args()
    run_backfill(force_drop=args.force_drop)
