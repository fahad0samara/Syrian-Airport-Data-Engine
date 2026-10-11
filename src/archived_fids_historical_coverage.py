"""
Syrian Airport Data Engine — Version 2.16
Historical FIDS Archive Coverage Analysis Engine

Analyzes coverage at two distinct, strictly segregated dimensions:
1. Snapshot Capture Coverage:
   Independent archive captures per month and year (Internet Archive crawl frequency).
2. Scheduled Service Date Coverage:
   Actual scheduled flight dates represented inside each snapshot.

Guarantees:
- Never sums overlapping schedules across snapshots to report false "monthly flights".
- Distinguishes between snapshot record observations and deduplicated flight identities.
- Reports capture timeline and schedule changes.
- Generates:
  * reports/v2_16_capture_timeline.csv
  * reports/v2_16_monthly_archive_coverage.csv
  * reports/v2_16_snapshot_comparison.csv
  * reports/v2_16_schedule_changes.csv
  * reports/v2_16_historical_coverage.json
"""

import os
import csv
import json
import sqlite3
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Any, Optional

HISTORY_DB_PATH = "data/archived_fids_history_staging.db"
DISCOVERY_CACHE = "data/raw/wayback_cdx_cache.json"

def analyze_historical_coverage(db_path: str = HISTORY_DB_PATH) -> Dict[str, Any]:
    """
    Computes capture coverage, scheduled date coverage, and deduplicated record counts.
    """
    if not os.path.exists(db_path):
        from src.archived_fids_snapshot_comparison import init_history_database
        init_history_database(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Fetch all registered snapshots
    cur.execute("SELECT * FROM archived_snapshot_registry ORDER BY wayback_timestamp ASC")
    snapshots = [dict(r) for r in cur.fetchall()]

    # 2. Fetch all snapshot records
    cur.execute("""
    SELECT snapshot_id, source_uuid, flight_number, original_date, original_time,
           direction, origin, destination, displayed_airline, displayed_status
    FROM archived_snapshot_records
    ORDER BY snapshot_id, original_date, original_time
    """)
    records = [dict(r) for r in cur.fetchall()]

    # 3. Fetch comparison results
    cur.execute("SELECT * FROM snapshot_comparison_results ORDER BY comparison_id")
    comparisons = [dict(r) for r in cur.fetchall()]
    conn.close()

    # Read CDX discovery cache for total discovered timeline
    discovered_timeline = []
    if os.path.exists(DISCOVERY_CACHE):
        try:
            with open(DISCOVERY_CACHE, "r", encoding="utf-8") as f:
                d = json.load(f)
                discovered_timeline = d.get("captures", [])
        except Exception:
            pass

    # A. Snapshot Capture Coverage (by month of capture)
    capture_monthly = defaultdict(lambda: {
        "year_month": "",
        "capture_count": 0,
        "unique_digests": set(),
        "local_downloaded_count": 0
    })

    for c in discovered_timeline:
        ts = c.get("timestamp") or c.get("wayback_timestamp") or ""
        ym = f"{ts[:4]}-{ts[4:6]}" if len(ts) >= 6 else "Unknown"
        b = capture_monthly[ym]
        b["year_month"] = ym
        b["capture_count"] += 1
        dig = c.get("digest") or c.get("content_digest")
        if dig:
            b["unique_digests"].add(dig)

    for s in snapshots:
        ts = s["wayback_timestamp"]
        ym = f"{ts[:4]}-{ts[4:6]}" if len(ts) >= 6 else "Unknown"
        capture_monthly[ym]["local_downloaded_count"] += 1

    # B. Scheduled Service Date Coverage (by scheduled flight date month)
    sched_monthly = defaultdict(lambda: {
        "scheduled_month": "",
        "snapshots_representing": set(),
        "total_record_observations": 0,
        "unique_source_uuids": set(),
        "unique_flight_slots": set(),
        "arrivals": 0,
        "departures": 0,
        "displayed_airlines": set(),
        "dates_represented": set()
    })

    for r in records:
        fdate = r["original_date"]
        ym = fdate[:7] if len(fdate) >= 7 else "Unknown"
        b = sched_monthly[ym]
        b["scheduled_month"] = ym
        b["snapshots_representing"].add(r["snapshot_id"])
        b["total_record_observations"] += 1
        b["unique_source_uuids"].add(r["source_uuid"])
        slot = (fdate, r["original_time"], r["direction"], r["flight_number"])
        b["unique_flight_slots"].add(slot)
        if r["direction"] == "arrival":
            b["arrivals"] += 1
        elif r["direction"] == "departure":
            b["departures"] += 1
        if r["displayed_airline"]:
            b["displayed_airlines"].add(r["displayed_airline"])
        b["dates_represented"].add(fdate)

    sorted_capture_months = sorted(capture_monthly.keys())
    sorted_sched_months = sorted(sched_monthly.keys())

    # Format monthly summary for report
    coverage_summary_rows = []
    for ym in sorted_sched_months:
        sm = sched_monthly[ym]
        cm = capture_monthly.get(ym, {"capture_count": 0, "unique_digests": set()})
        dates_sorted = sorted(sm["dates_represented"])
        date_range_str = f"{dates_sorted[0]} to {dates_sorted[-1]}" if dates_sorted else "N/A"
        coverage_summary_rows.append({
            "month": ym,
            "snapshot_capture_count": cm.get("capture_count", 0),
            "unique_snapshot_digests_count": len(cm.get("unique_digests", set())),
            "scheduled_service_date_range": date_range_str,
            "distinct_scheduled_dates_count": len(dates_sorted),
            "total_fids_record_observations": sm["total_record_observations"],
            "deduplicated_source_uuids_count": len(sm["unique_source_uuids"]),
            "deduplicated_flight_slots_count": len(sm["unique_flight_slots"]),
            "scheduled_arrivals_observations": sm["arrivals"],
            "scheduled_departures_observations": sm["departures"],
            "displayed_airlines_count": len(sm["displayed_airlines"])
        })

    # C. Schedule Changes Table (from comparisons)
    schedule_changes = [c for c in comparisons if c["comparison_category"] != "same_uuid_identical"]

    payload = {
        "metadata": {
            "version": "2.16",
            "generated_at": datetime.now().isoformat(),
            "target_aerodrome": "DAM / OSDI (Damascus International Airport)",
            "api_endpoint": "https://damairport.gov.sy/api/flights.php",
            "governance_rule": "These records represent historical FIDS timetable display schedules, not verified physical radar touchdowns."
        },
        "snapshot_capture_coverage": {
            "total_snapshots_discovered": len(discovered_timeline),
            "total_snapshots_registered": len(snapshots),
            "monthly_breakdown": [
                {
                    "month": ym,
                    "captures_discovered": capture_monthly[ym]["capture_count"],
                    "unique_digests": len(capture_monthly[ym]["unique_digests"]),
                    "locally_preserved": capture_monthly[ym]["local_downloaded_count"]
                }
                for ym in sorted_capture_months
            ]
        },
        "scheduled_service_coverage": coverage_summary_rows,
        "cross_snapshot_comparisons": {
            "total_comparisons": len(comparisons),
            "identical_records": sum(1 for c in comparisons if c["comparison_category"] == "same_uuid_identical"),
            "changed_or_new_records": len(schedule_changes),
            "change_categories_distribution": dict(Counter([c["comparison_category"] for c in comparisons]))
        }
    }

    return payload

def export_coverage_reports(coverage_payload: Dict[str, Any]):
    os.makedirs("reports", exist_ok=True)

    # 1. reports/v2_16_capture_timeline.csv
    timeline_path = "reports/v2_16_capture_timeline.csv"
    with open(timeline_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["capture_month", "captures_discovered", "unique_digests_count", "locally_preserved_snapshots"])
        for cm in coverage_payload["snapshot_capture_coverage"]["monthly_breakdown"]:
            writer.writerow([cm["month"], cm["captures_discovered"], cm["unique_digests"], cm["locally_preserved"]])
    print(f"Generated {timeline_path}", flush=True)

    # 2. reports/v2_16_monthly_archive_coverage.csv
    monthly_path = "reports/v2_16_monthly_archive_coverage.csv"
    with open(monthly_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "month",
            "snapshot_capture_count",
            "unique_snapshot_digests_count",
            "scheduled_service_date_range",
            "distinct_scheduled_dates_count",
            "total_fids_record_observations",
            "deduplicated_source_uuids_count",
            "deduplicated_flight_slots_count",
            "scheduled_arrivals_observations",
            "scheduled_departures_observations",
            "displayed_airlines_count"
        ])
        for r in coverage_payload["scheduled_service_coverage"]:
            writer.writerow([
                r["month"],
                r["snapshot_capture_count"],
                r["unique_snapshot_digests_count"],
                r["scheduled_service_date_range"],
                r["distinct_scheduled_dates_count"],
                r["total_fids_record_observations"],
                r["deduplicated_source_uuids_count"],
                r["deduplicated_flight_slots_count"],
                r["scheduled_arrivals_observations"],
                r["scheduled_departures_observations"],
                r["displayed_airlines_count"]
            ])
    print(f"Generated {monthly_path}", flush=True)

    # 3. reports/v2_16_schedule_changes.csv
    changes_path = "reports/v2_16_schedule_changes.csv"
    with open(changes_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "comparison_id",
            "baseline_snapshot_id",
            "comparison_snapshot_id",
            "source_uuid",
            "change_category",
            "changed_fields",
            "review_status",
            "details"
        ])
        # Read from history staging DB
        if os.path.exists(HISTORY_DB_PATH):
            conn = sqlite3.connect(HISTORY_DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT * FROM snapshot_comparison_results WHERE comparison_category != 'same_uuid_identical'")
            for row in cur.fetchall():
                writer.writerow(row)
            conn.close()
    print(f"Generated {changes_path}", flush=True)

    # 4. reports/v2_16_snapshot_comparison.csv
    comp_path = "reports/v2_16_snapshot_comparison.csv"
    with open(comp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "comparison_id",
            "baseline_snapshot_id",
            "comparison_snapshot_id",
            "source_uuid",
            "comparison_category",
            "changed_fields",
            "review_status",
            "details"
        ])
        if os.path.exists(HISTORY_DB_PATH):
            conn = sqlite3.connect(HISTORY_DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT * FROM snapshot_comparison_results")
            for row in cur.fetchall():
                writer.writerow(row)
            conn.close()
    print(f"Generated {comp_path}", flush=True)

    # 5. reports/v2_16_historical_coverage.json
    json_path = "reports/v2_16_historical_coverage.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(coverage_payload, f, indent=2, ensure_ascii=False)
    print(f"Generated {json_path}", flush=True)

if __name__ == "__main__":
    cov = analyze_historical_coverage()
    export_coverage_reports(cov)
