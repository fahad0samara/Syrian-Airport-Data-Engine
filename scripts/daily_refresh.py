import sys
import logging
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from scripts.fetch_all_syrian_airports import fetch_all
from src.ingestion import run_ingestion_pipeline
from src.normalizer import load_and_normalize_all_events
from src.aggregator import (
    aggregate_damascus_daily_movements,
    aggregate_daily_airport_movements,
    load_historical_sem_series,
    persist_all_to_database_and_exports,
)
from src.quality_checker import run_quality_audit
from src.historical_coverage import build_historical_coverage_matrix
from src.coverage import build_coverage_reports

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def run_daily_refresh():
    logging.info("Starting Daily Flight Data Refresh for All Syrian Airports & Damascus Deep-Dive...")

    # 1. Fetch live and rolling flight updates using multi-source adapters
    logging.info("Step 1: Running multi-source ingestion pipeline with retry, hashing, and snapshot preservation...")
    try:
        ingest_summary = run_ingestion_pipeline()
        logging.info(f"Ingestion pipeline: {ingest_summary['sources_succeeded']} succeeded, {ingest_summary['total_records_fetched']} records fetched.")
        fetch_all()
    except Exception as e:
        logging.error(f"Error fetching live flight data: {e}")
        return False

    # 2. Normalize and deduplicate
    logging.info("Step 2: Normalizing and deduplicating flight events across all airports...")
    events, audit_log, audit_summary = load_and_normalize_all_events()
    logging.info(f"Processed {len(events)} events (merged {audit_summary['merged_verified_count']}, flagged {audit_summary['flagged_ambiguous_count']}, split legs {audit_summary['split_distinct_leg_count']}).")

    # 3. Aggregate daily movements per airport
    logging.info("Step 3: Updating daily movement aggregates per airport...")
    all_daily_movements = aggregate_daily_airport_movements(events)
    dam_daily_movements = aggregate_damascus_daily_movements(events)

    # 4. Load historical baseline
    logging.info("Step 4: Reconciling with historical gateway baseline (DAM_ALP_LTK)...")
    hist_records = load_historical_sem_series()

    # 5. Persist to DB and refresh exports
    logging.info("Step 5: Updating database tables and exporting CSV/JSON...")
    summary = persist_all_to_database_and_exports(
        events=events,
        dam_daily_movements=dam_daily_movements,
        all_daily_movements=all_daily_movements,
        hist_records=hist_records,
        audit_log=audit_log
    )
    logging.info(f"Updated: {summary['total_canonical_events']} total flights across airports.")

    # 6. Quality audit
    logging.info("Step 6: Running quality assurance checks...")
    quality = run_quality_audit(
        events=events,
        dam_daily_movements=dam_daily_movements,
        hist_records=hist_records,
        all_daily_movements=all_daily_movements,
        persist=True
    )
    logging.info(f"Quality Audit: {quality['overall_status']} ({quality['passed_checks']}/{quality['total_checks']} checks passed).")

    # 7. Historical Coverage Matrix
    logging.info("Step 7: Building evidence-backed 2024-2026 historical coverage matrix...")
    matrix_summary = build_historical_coverage_matrix()
    logging.info(f"Coverage matrix updated ({matrix_summary['total_matrix_cells']} cells).")

    # 8. Coverage reports
    logging.info("Step 8: Regenerating comprehensive coverage reports...")
    build_coverage_reports()

    logging.info("Daily refresh completed successfully.")
    return True

if __name__ == '__main__':
    run_daily_refresh()
