"""
Syrian Airport Data Engine — Version 2.16
Archived FIDS Snapshot Validation Engine

Performs independent structural, identity, semantic, timezone, and quality validation
on archived Damascus International Airport (DAM / OSDI) FIDS snapshots.

Strict Semantic Rules:
1. Validates top-level JSON structure and flight record array.
2. Audits source UUID validity, uniqueness, missing UUIDs, and duplicate records.
3. Extracts and preserves flight semantics (direction, date, time, route, airline, status).
4. Strictly interprets schedule timestamps in Asia/Damascus wall-clock time; labels any UTC conversion as derived.
5. NEVER infers physical movements, aircraft registrations, or certified AOC operating carriers.
6. Generates reports/v2_16_snapshot_validation.csv and reports/v2_16_snapshot_validation.json.
"""

import os
import re
import csv
import json
import uuid
import hashlib
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

UUID_REGEX = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.IGNORECASE)

EXPECTED_TOP_KEYS = {"ok", "flights", "settings", "airlines"}
REQUIRED_RECORD_FIELDS = {"id", "flightNumber", "direction", "date", "time"}

def get_file_sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def validate_uuid_str(val: Any) -> bool:
    if not isinstance(val, str):
        return False
    return bool(UUID_REGEX.match(val))

def validate_snapshot_file(
    json_path: str,
    raw_path: Optional[str] = None,
    snapshot_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validates a single snapshot file independently.
    Returns comprehensive validation results dictionary.
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Snapshot JSON missing at {json_path}")

    if snapshot_id is None:
        basename = os.path.basename(json_path)
        # Expecting wayback_damairport_fids_{timestamp}.json
        m = re.search(r'wayback_damairport_fids_([0-9a-zA-Z_]+)\.json', basename)
        snapshot_id = f"snap_wayback_{m.group(1)}" if m else basename

    raw_sha = get_file_sha256(raw_path) if raw_path and os.path.exists(raw_path) else None
    json_sha = get_file_sha256(json_path)
    file_size_bytes = os.path.getsize(json_path)

    issues: List[Dict[str, Any]] = []

    # 1. Structural Validation
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {
            "snapshot_id": snapshot_id,
            "json_path": json_path,
            "raw_sha256": raw_sha,
            "json_sha256": json_sha,
            "validation_status": "corrupt_json",
            "error": str(e),
            "issues": [{"issue_type": "json_parse_error", "severity": "FATAL", "details": str(e)}]
        }

    if not isinstance(data, dict):
        return {
            "snapshot_id": snapshot_id,
            "json_path": json_path,
            "validation_status": "invalid_top_level",
            "error": "Top-level JSON is not an object",
            "issues": [{"issue_type": "invalid_top_level", "severity": "FATAL", "details": "Expected JSON object"}]
        }

    top_keys = set(data.keys())
    missing_top_keys = list(EXPECTED_TOP_KEYS - top_keys)
    extra_top_keys = list(top_keys - EXPECTED_TOP_KEYS)
    flights_raw = data.get("flights")

    if not isinstance(flights_raw, list):
        return {
            "snapshot_id": snapshot_id,
            "json_path": json_path,
            "validation_status": "missing_flights_array",
            "error": "'flights' is missing or not a list",
            "issues": [{"issue_type": "missing_flights_array", "severity": "FATAL", "details": "'flights' must be an array"}]
        }

    # 2. Record Identity & Field Coverage
    total_records = len(flights_raw)
    uuids = []
    missing_uuid_count = 0
    invalid_uuid_count = 0
    missing_fields_counts = defaultdict(int)
    exact_duplicates = 0
    seen_hashes = set()

    normalized_records = []
    daily_distribution = defaultdict(int)
    direction_counts = {"arrival": 0, "departure": 0, "other": 0}
    status_counts = defaultdict(int)
    airline_counts = defaultdict(int)
    dates_seen = set()

    for idx, fobj in enumerate(flights_raw):
        if not isinstance(fobj, dict):
            issues.append({"issue_type": "invalid_record_type", "severity": "ERROR", "details": f"Record index {idx} is not an object"})
            continue

        # Exact duplicate detection
        obj_str = json.dumps(fobj, sort_keys=True)
        obj_hash = hashlib.sha256(obj_str.encode("utf-8")).hexdigest()
        if obj_hash in seen_hashes:
            exact_duplicates += 1
            issues.append({"issue_type": "exact_duplicate_object", "severity": "WARNING", "details": f"Record index {idx} is byte-identical to earlier entry"})
        seen_hashes.add(obj_hash)

        # Check required fields
        for rf in REQUIRED_RECORD_FIELDS:
            if rf not in fobj or fobj[rf] is None or fobj[rf] == "":
                missing_fields_counts[rf] += 1

        # Check optional fields
        for of in ["origin", "destination", "airline", "aircraft", "gate", "status", "createdAt"]:
            if of not in fobj or fobj[of] is None or fobj[of] == "":
                missing_fields_counts[of] += 1

        # UUID checks
        uid = fobj.get("id")
        if not uid:
            missing_uuid_count += 1
            issues.append({"issue_type": "missing_uuid", "severity": "ERROR", "details": f"Record index {idx} lacks 'id' field"})
        else:
            uuids.append(uid)
            if not validate_uuid_str(uid):
                invalid_uuid_count += 1
                issues.append({"issue_type": "invalid_uuid_format", "severity": "WARNING", "details": f"Record index {idx} UUID '{uid}' non-RFC4122 compliant"})

        # Semantics extraction
        fnum = str(fobj.get("flightNumber") or "").strip()
        fdate = str(fobj.get("date") or "").strip()
        ftime = str(fobj.get("time") or "").strip()
        fdir = str(fobj.get("direction") or "").lower().strip()
        forigin = str(fobj.get("origin") or "").strip()
        fdest = str(fobj.get("destination") or "").strip()
        fairline = str(fobj.get("airline") or "").strip()
        fstatus = str(fobj.get("status") or "").lower().strip()
        fcreated = str(fobj.get("createdAt") or "").strip()

        if fdate:
            dates_seen.add(fdate)
            daily_distribution[fdate] += 1

        if fdir in ("arrival", "departure"):
            direction_counts[fdir] += 1
        else:
            direction_counts["other"] += 1

        if fstatus:
            status_counts[fstatus] += 1
        else:
            status_counts["missing"] += 1

        if fairline:
            airline_counts[fairline] += 1
        else:
            airline_counts["unknown"] += 1

        # Derived UTC timestamp (clearly labeled)
        derived_utc = None
        if fdate and ftime:
            try:
                # Damascus is UTC+3 wall-clock time
                # Example: 2026-07-06 11:30:00 local -> 2026-07-06 08:30:00 UTC
                dt_local = datetime.strptime(f"{fdate} {ftime}", "%Y-%m-%d %H:%M")
                # Subtract 3 hours for derived UTC
                from datetime import timedelta
                dt_utc = dt_local - timedelta(hours=3)
                derived_utc = dt_utc.strftime("%Y-%m-%d %H:%M:%SZ")
            except Exception:
                derived_utc = None

        normalized_records.append({
            "source_uuid": uid,
            "flight_number": fnum,
            "original_date": fdate,
            "original_time": ftime,
            "timezone_local": "Asia/Damascus (UTC+3)",
            "derived_utc_timestamp": derived_utc,
            "direction": fdir,
            "origin": forigin,
            "destination": fdest,
            "displayed_airline": fairline,
            "displayed_status": fstatus,
            "source_created_at": fcreated,
            "actual_movement_evidence": 0 # STRICT INVARIANT
        })

    # UUID duplicate check
    uuid_counter = Counter(uuids)
    duplicate_uuids = [u for u, cnt in uuid_counter.items() if cnt > 1]
    if duplicate_uuids:
        for du in duplicate_uuids:
            issues.append({"issue_type": "duplicate_source_uuid", "severity": "ERROR", "details": f"UUID {du} appears {uuid_counter[du]} times"})

    # Semantic candidate duplicate check (e.g. prefix variants)
    # Check same date, time, direction, route with differing flight numbers
    slot_map = defaultdict(list)
    for r in normalized_records:
        slot_key = (r["original_date"], r["original_time"], r["direction"], r["origin"], r["destination"])
        slot_map[slot_key].append(r)

    duplicate_candidates = []
    for slot_key, recs in slot_map.items():
        if len(recs) > 1:
            # Check if airlines match or flight numbers share digits
            fnums = [r["flight_number"] for r in recs]
            if len(set(fnums)) > 1:
                duplicate_candidates.append({
                    "slot": f"{slot_key[0]} {slot_key[1]} ({slot_key[2]}) {slot_key[3]}->{slot_key[4]}",
                    "records": recs,
                    "classification": "possible_prefix_variant_duplicate"
                })

    sorted_dates = sorted(dates_seen)
    min_date = sorted_dates[0] if sorted_dates else None
    max_date = sorted_dates[-1] if sorted_dates else None

    # Overall validation verdict
    has_fatal = any(i["severity"] == "FATAL" for i in issues)
    has_error = any(i["severity"] == "ERROR" for i in issues)
    if has_fatal:
        val_status = "INVALID"
    elif has_error:
        val_status = "VALID_WITH_ERRORS"
    elif duplicate_candidates or exact_duplicates:
        val_status = "VALID_WITH_CANDIDATE_DUPLICATES"
    else:
        val_status = "VALID"

    return {
        "snapshot_id": snapshot_id,
        "json_path": json_path,
        "raw_path": raw_path,
        "raw_sha256": raw_sha,
        "json_sha256": json_sha,
        "file_size_bytes": file_size_bytes,
        "validation_status": val_status,
        "schema": {
            "top_level_keys": list(top_keys),
            "missing_expected_keys": missing_top_keys,
            "extra_keys": extra_top_keys
        },
        "identity_metrics": {
            "total_records": total_records,
            "unique_source_uuids": len(uuid_counter),
            "missing_uuids_count": missing_uuid_count,
            "invalid_uuid_format_count": invalid_uuid_count,
            "exact_duplicate_objects_count": exact_duplicates,
            "duplicate_source_uuids_count": len(duplicate_uuids)
        },
        "coverage_metrics": {
            "scheduled_dates_count": len(sorted_dates),
            "earliest_date": min_date,
            "latest_date": max_date,
            "daily_records_distribution": dict(daily_distribution)
        },
        "directional_metrics": direction_counts,
        "status_distribution": dict(status_counts),
        "airline_distribution": dict(airline_counts),
        "missing_fields": dict(missing_fields_counts),
        "duplicate_candidates_count": len(duplicate_candidates),
        "duplicate_candidates": duplicate_candidates,
        "issues_count": len(issues),
        "issues": issues,
        "physical_movement_evidence_count": 0,
        "validated_at": datetime.now().isoformat()
    }

def validate_all_known_snapshots(snapshots_dir: str = "data/raw/snapshots") -> List[Dict[str, Any]]:
    """Validates all wayback snapshots found in snapshots_dir."""
    results = []
    if not os.path.exists(snapshots_dir):
        return results

    for f in os.listdir(snapshots_dir):
        if f.startswith("wayback_damairport_fids_") and f.endswith(".json"):
            json_p = os.path.join(snapshots_dir, f)
            raw_p = json_p.replace(".json", ".raw")
            m = re.search(r'wayback_damairport_fids_([0-9a-zA-Z_]+)\.json', f)
            snap_id = f"snap_wayback_{m.group(1)}" if m else f
            res = validate_snapshot_file(json_p, raw_p, snap_id)
            results.append(res)

    results.sort(key=lambda x: x["snapshot_id"])
    return results

def generate_validation_reports(validation_results: List[Dict[str, Any]]):
    """Generates reports/v2_16_snapshot_validation.csv and .json."""
    os.makedirs("reports", exist_ok=True)
    csv_path = "reports/v2_16_snapshot_validation.csv"
    json_path = "reports/v2_16_snapshot_validation.json"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "snapshot_id",
            "validation_status",
            "total_records",
            "arrivals",
            "departures",
            "unique_uuids",
            "missing_uuids",
            "duplicate_uuids",
            "duplicate_candidates",
            "scheduled_dates_count",
            "earliest_date",
            "latest_date",
            "unique_airlines_count",
            "json_sha256",
            "raw_sha256",
            "issues_count"
        ])
        for v in validation_results:
            im = v.get("identity_metrics", {})
            cm = v.get("coverage_metrics", {})
            dm = v.get("directional_metrics", {})
            al = v.get("airline_distribution", {})
            writer.writerow([
                v.get("snapshot_id"),
                v.get("validation_status"),
                im.get("total_records", 0),
                dm.get("arrival", 0),
                dm.get("departure", 0),
                im.get("unique_source_uuids", 0),
                im.get("missing_uuids_count", 0),
                im.get("duplicate_source_uuids_count", 0),
                v.get("duplicate_candidates_count", 0),
                cm.get("scheduled_dates_count", 0),
                cm.get("earliest_date", ""),
                cm.get("latest_date", ""),
                len(al),
                v.get("json_sha256", ""),
                v.get("raw_sha256", ""),
                v.get("issues_count", 0)
            ])
    print(f"Generated {csv_path} ({len(validation_results)} snapshot validations)", flush=True)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "version": "2.16",
            "generated_at": datetime.now().isoformat(),
            "total_snapshots_validated": len(validation_results),
            "snapshots": validation_results
        }, f, indent=2, ensure_ascii=False)
    print(f"Generated {json_path}", flush=True)

if __name__ == "__main__":
    res = validate_all_known_snapshots()
    generate_validation_reports(res)
    for r in res:
        print(f"\nSnapshot {r['snapshot_id']}: Status={r['validation_status']}, Records={r.get('identity_metrics', {}).get('total_records')}, Range={r.get('coverage_metrics', {}).get('earliest_date')} to {r.get('coverage_metrics', {}).get('latest_date')}")
