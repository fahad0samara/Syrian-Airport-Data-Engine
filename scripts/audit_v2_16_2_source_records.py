"""
Syrian Airport Data Engine — Version 2.16.2
Source-of-Truth Record Audit Script

Directly inspects all 1,982 records in:
data/raw/snapshots/wayback_damairport_fids_20260709234230.json

Produces:
- reports/v2_16_2_record_level_audit.csv
- reports/v2_16_2_record_level_audit.json

Guarantees:
- Reads original raw snapshot directly without database intermediate.
- Deterministic, repeatable SHA-256 calculation per record.
- Complete field integrity checks.
"""

import os
import json
import csv
import re
import hashlib
from datetime import datetime
from collections import Counter

RAW_JSON_PATH = "data/raw/snapshots/wayback_damairport_fids_20260709234230.json"
OUTPUT_CSV = "reports/v2_16_2_record_level_audit.csv"
OUTPUT_JSON = "reports/v2_16_2_record_level_audit.json"

def compute_record_hash(record_dict: dict) -> str:
    canonical = json.dumps(record_dict, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def audit_source_records(json_path: str = RAW_JSON_PATH):
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Snapshot JSON not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_flights = data.get("flights", [])
    total_objects = len(raw_flights)

    records_audit = []
    seen_uuids = set()
    duplicate_uuids = []
    missing_uuids = 0
    missing_dates = 0
    missing_times = 0
    invalid_dates = 0
    invalid_times = 0
    unexpected_directions = 0
    missing_routes = 0
    exact_duplicate_objects = 0
    seen_hashes = set()

    date_regex = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    time_regex = re.compile(r"^\d{2}:\d{2}$")

    for idx, flight in enumerate(raw_flights):
        rec_hash = compute_record_hash(flight)
        if rec_hash in seen_hashes:
            exact_duplicate_objects += 1
        seen_hashes.add(rec_hash)

        uid = flight.get("id")
        if not uid:
            missing_uuids += 1
        elif uid in seen_uuids:
            duplicate_uuids.append(uid)
        else:
            seen_uuids.add(uid)

        fnum = flight.get("flightNumber", "")
        fdate = flight.get("date", "")
        ftime = flight.get("time", "")
        direction = flight.get("direction", "")
        origin = flight.get("origin", "")
        dest = flight.get("destination", "")
        airline = flight.get("airline", "")
        status = flight.get("status", "")
        created_at = flight.get("createdAt", "")

        if not fdate:
            missing_dates += 1
        elif not date_regex.match(fdate):
            invalid_dates += 1

        if not ftime:
            missing_times += 1
        elif not time_regex.match(ftime):
            invalid_times += 1

        if direction not in ("arrival", "departure"):
            unexpected_directions += 1

        if not origin or not dest:
            missing_routes += 1

        records_audit.append({
            "record_index": idx,
            "source_uuid": uid,
            "flight_number": fnum,
            "original_scheduled_date": fdate,
            "original_scheduled_time": ftime,
            "direction": direction,
            "origin_airport": origin,
            "destination_airport": dest,
            "displayed_airline": airline,
            "displayed_status": status,
            "created_at": created_at,
            "raw_record_hash": rec_hash
        })

    # Summary statistics
    summary = {
        "audit_timestamp": datetime.now().isoformat(),
        "source_file": json_path,
        "total_source_objects": total_objects,
        "total_unique_uuids": len(seen_uuids),
        "missing_uuids_count": missing_uuids,
        "duplicate_uuids_count": len(duplicate_uuids),
        "missing_scheduled_dates_count": missing_dates,
        "missing_scheduled_times_count": missing_times,
        "invalid_date_formats_count": invalid_dates,
        "invalid_time_formats_count": invalid_times,
        "unexpected_directions_count": unexpected_directions,
        "missing_routes_count": missing_routes,
        "exact_duplicate_objects_count": exact_duplicate_objects,
        "scheduled_date_range": {
            "min_date": min(r["original_scheduled_date"] for r in records_audit) if records_audit else None,
            "max_date": max(r["original_scheduled_date"] for r in records_audit) if records_audit else None,
            "distinct_dates_count": len(set(r["original_scheduled_date"] for r in records_audit))
        },
        "directional_breakdown": dict(Counter(r["direction"] for r in records_audit)),
        "status_breakdown": dict(Counter(r["displayed_status"] for r in records_audit)),
        "displayed_airline_count": len(set(r["displayed_airline"] for r in records_audit))
    }

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

    # Write CSV
    fieldnames = [
        "record_index", "source_uuid", "flight_number",
        "original_scheduled_date", "original_scheduled_time",
        "direction", "origin_airport", "destination_airport",
        "displayed_airline", "displayed_status", "created_at",
        "raw_record_hash"
    ]
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as cf:
        writer = csv.DictWriter(cf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records_audit)

    # Write JSON
    full_output = {
        "summary": summary,
        "records": records_audit
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as jf:
        json.dump(full_output, jf, indent=2, ensure_ascii=False)

    print(f"Record-level audit complete: {total_objects} records processed.")
    print(f"Summary: {json.dumps(summary, indent=2)}")
    return full_output

if __name__ == "__main__":
    audit_source_records()
