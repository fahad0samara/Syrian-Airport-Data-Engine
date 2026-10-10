import sys
import logging
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from scripts.fetch_raw_data import main as fetch_raw
from src.normalizer import load_and_normalize_all_events
from src.aggregator import (
    aggregate_damascus_daily_movements,
    load_historical_sem_series,
    persist_all_to_database_and_exports,
)
from src.quality_checker import run_quality_audit

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def run_daily_refresh():
    logging.info("Starting Daily Flight Data Refresh for Damascus Airport (DAM/OSDI)...")
    
    # 1. Fetch live and rolling flight updates
    logging.info("Step 1: Polling live flight APIs...")
    try:
        fetch_raw()
    except Exception as e:
        logging.error(f"Error fetching live flight data: {e}")
        return False

    # 2. Normalize and deduplicate
    logging.info("Step 2: Normalizing and deduplicating flight events...")
    events, audit = load_and_normalize_all_events()
    logging.info(f"Processed {len(events)} events (pruned {audit['duplicates_pruned']} duplicates).")

    # 3. Aggregate daily movements
    logging.info("Step 3: Updating daily movement aggregates...")
    daily_movements = aggregate_damascus_daily_movements(events)

    # 4. Load historical baseline
    logging.info("Step 4: Reconciling with historical baseline...")
    hist_records = load_historical_sem_series()

    # 5. Persist to DB and refresh exports
    logging.info("Step 5: Updating database tables and exporting CSV/JSON...")
    summary = persist_all_to_database_and_exports(events, daily_movements, hist_records)
    logging.info(f"Updated: {summary['total_verified_damascus_flights']} flights, {summary['total_unique_aircraft']} unique aircraft.")

    # 6. Quality audit
    logging.info("Step 6: Running quality assurance checks...")
    quality = run_quality_audit(events, daily_movements, hist_records)
    logging.info(f"Quality Audit: {quality['overall_status']} ({quality['passed_checks']}/{quality['total_checks']} checks passed).")

    logging.info("Daily refresh completed successfully.")
    return True

if __name__ == '__main__':
    run_daily_refresh()
