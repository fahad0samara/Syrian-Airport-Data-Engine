import logging
import time
from typing import Dict, Any, List
from datetime import datetime, timezone

from src.adapters.official_portal import OfficialAirportAdapter, OFFICIAL_PORTAL_CONFIGS
from src.adapters.flightradar24 import Flightradar24Adapter
from src.adapters.aviationstack import AviationStackAdapter
from src.adapters.restricted_sources import get_restricted_sources

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def run_ingestion_pipeline(airports: List[str] = None) -> Dict[str, Any]:
    """
    Executes idempotent multi-source aviation data ingestion workflow across Syrian aerodromes.
    Collects official flight boards, live ADS-B radar, and commercial feeds.
    Preserves all raw responses with SHA-256 payload hashes and timestamped snapshots.
    Retries transient failures with exponential backoff and never fabricates records.
    """
    start_time = time.time()
    if airports is None:
        airports = ["DAM", "ALP", "KAC", "DEZ"]

    summary = {
        "pipeline_started_at": datetime.now(timezone.utc).isoformat(),
        "airports_targeted": airports,
        "runs": [],
        "sources_succeeded": 0,
        "sources_failed": 0,
        "sources_empty": 0,
        "total_records_fetched": 0,
        "duration_seconds": 0.0
    }

    logging.info(f"Starting Ingestion Pipeline for aerodromes: {airports}")

    # 1. Official Airport Portals
    for aid in airports:
        if aid.upper() in OFFICIAL_PORTAL_CONFIGS:
            adapter = OfficialAirportAdapter(aid)
            logging.info(f"Polling official portal for {aid} ({adapter.default_url})...")
            res = adapter.fetch_and_save()
            summary["runs"].append({"adapter": adapter.source_id, "airport_id": aid, **res})
            if res["status"] == "SUCCESS":
                summary["sources_succeeded"] += 1
                summary["total_records_fetched"] += res["records_fetched"]
            elif res["status"] == "EMPTY":
                summary["sources_empty"] += 1
            else:
                summary["sources_failed"] += 1

    # 2. Flightradar24 Live Ground Radar Feeds
    fr24 = Flightradar24Adapter()
    for aid in ["DAM", "ALP", "LTK", "KAC", "DEZ"]:
        logging.info(f"Querying Flightradar24 radar feed for {aid}...")
        res = fr24.fetch_airport_movements(aid)
        summary["runs"].append({"adapter": "flightradar24", "airport_id": aid, **res})
        if res["status"] == "SUCCESS":
            summary["sources_succeeded"] += 1
            summary["total_records_fetched"] += res["records_fetched"]
        elif res["status"] == "EMPTY":
            summary["sources_empty"] += 1
        else:
            summary["sources_failed"] += 1

    # 3. AviationStack Feed (if key configured)
    avstack = AviationStackAdapter()
    for aid in ["DAM"]:
        res = avstack.fetch_airport_flights(aid)
        summary["runs"].append({"adapter": "aviationstack_live", "airport_id": aid, **res})
        if res["status"] == "SUCCESS":
            summary["sources_succeeded"] += 1
            summary["total_records_fetched"] += res["records_fetched"]
        elif res["status"] == "EMPTY":
            summary["sources_empty"] += 1
        elif res["status"] == "FAILED":
            summary["sources_failed"] += 1

    # 4. Formally Log Restricted Source Checks
    for rsrc in get_restricted_sources():
        info = rsrc.check_access_status()
        summary["runs"].append({"adapter": rsrc.source_id, "status": "COMPLIANT_RESTRICTED", **info})

    summary["duration_seconds"] = round(time.time() - start_time, 2)
    summary["pipeline_finished_at"] = datetime.now(timezone.utc).isoformat()
    logging.info(f"Ingestion pipeline finished in {summary['duration_seconds']}s. "
                 f"Succeeded: {summary['sources_succeeded']}, Empty: {summary['sources_empty']}, Failed: {summary['sources_failed']}.")
    return summary

if __name__ == "__main__":
    res = run_ingestion_pipeline()
    print(f"Ingestion result: {res['sources_succeeded']} succeeded, {res['total_records_fetched']} records fetched.")
