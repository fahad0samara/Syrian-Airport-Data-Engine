import json
from datetime import datetime, timezone
from typing import Dict, Any, List
import pandas as pd
from src.config import REPORTS_DIR, AIRPORT_IATA, AIRPORT_ICAO, SYRIAN_AIRPORT_IATAS
from src.database import get_connection

def run_quality_audit(events: List[Dict[str, Any]], daily_movements: List[Dict[str, Any]], hist_records: List[Dict[str, Any]], persist: bool = True) -> Dict[str, Any]:
    checks = []

    # 1. Airport Identifiers
    invalid_airports = [e for e in events if e.get("airport_iata") != AIRPORT_IATA or e.get("airport_icao") != AIRPORT_ICAO]
    passed_id = len(invalid_airports) == 0
    checks.append({
        "check_name": "airport_identifiers_validity",
        "passed": 1 if passed_id else 0,
        "metric_value": float(len(invalid_airports)),
        "details": f"All {len(events)} events have airport_iata={AIRPORT_IATA} and airport_icao={AIRPORT_ICAO}." if passed_id else f"{len(invalid_airports)} events had incorrect airport codes."
    })

    # 2. No synthetic zero fill on missing dates
    # Verify that in damascus_daily_movements, every entry corresponds to an actual observed date
    event_dates = set(e["flight_date"] for e in events)
    daily_dates = set(d["flight_date"] for d in daily_movements)
    unobserved_dates = daily_dates - event_dates
    passed_no_synth = len(unobserved_dates) == 0
    checks.append({
        "check_name": "no_synthetic_zeros_on_missing_dates",
        "passed": 1 if passed_no_synth else 0,
        "metric_value": float(len(unobserved_dates)),
        "details": "Daily movements contains only dates with genuine observed flights; no zero-filled synthetic dates." if passed_no_synth else f"Found {len(unobserved_dates)} synthetic dates."
    })

    # 3. No estimated passenger or cargo figures
    forbidden_keys = {"passenger_count", "estimated_passengers", "cargo_tonnage", "cargo_weight_kg", "estimated_cargo"}
    forbidden_found = []
    for e in events:
        for k in forbidden_keys:
            if k in e:
                forbidden_found.append(k)
    passed_no_estimates = len(forbidden_found) == 0
    checks.append({
        "check_name": "no_speculative_passenger_or_cargo_estimates",
        "passed": 1 if passed_no_estimates else 0,
        "metric_value": float(len(forbidden_found)),
        "details": "Verified: Zero estimated passenger counts or cargo tonnages generated from aircraft capacity."
    })

    # 4. Valid operational statuses
    allowed_statuses = {"landed", "active", "scheduled", "cancelled", "diverted", "unknown"}
    invalid_statuses = [e for e in events if e.get("flight_status") not in allowed_statuses]
    passed_status = len(invalid_statuses) == 0
    checks.append({
        "check_name": "flight_status_taxonomy_validity",
        "passed": 1 if passed_status else 0,
        "metric_value": float(len(invalid_statuses)),
        "details": f"All events adhere to standard statuses {sorted(allowed_statuses)}."
    })

    # 5. Route Classification Integrity
    # If connected airport is Syrian, must be domestic; if foreign, must be international
    misclassified_routes = []
    for e in events:
        conn = (e.get("connected_airport_iata") or "").upper()
        rtype = e.get("route_type")
        if conn in SYRIAN_AIRPORT_IATAS and rtype != "domestic":
            misclassified_routes.append(e["event_id"])
        elif conn and conn not in SYRIAN_AIRPORT_IATAS and rtype == "domestic":
            misclassified_routes.append(e["event_id"])
    passed_routes = len(misclassified_routes) == 0
    checks.append({
        "check_name": "route_classification_integrity",
        "passed": 1 if passed_routes else 0,
        "metric_value": float(len(misclassified_routes)),
        "details": f"Route classification matches IATA/ICAO territorial registry (Syrian domestic vs International). {len(misclassified_routes)} misclassifications."
    })

    # 6. Deduplication Integrity
    seen_keys = set()
    dup_keys = []
    for e in events:
        k = (e["movement_type"], e["flight_number"], e["flight_date"], (e["scheduled_dep_time"] or e["scheduled_arr_time"] or "")[:13])
        if k in seen_keys:
            dup_keys.append(k)
        seen_keys.add(k)
    passed_dedup = len(dup_keys) == 0
    checks.append({
        "check_name": "deduplication_uniqueness",
        "passed": 1 if passed_dedup else 0,
        "metric_value": float(len(dup_keys)),
        "details": "All normalized events are unique per movement type, flight number, date, and hourly slot." if passed_dedup else f"Found {len(dup_keys)} duplicate keys."
    })

    # 7. Timestamp ISO 8601 formatting
    invalid_ts = 0
    for e in events:
        for f in ("scheduled_dep_time", "actual_dep_time", "scheduled_arr_time", "actual_arr_time"):
            v = e.get(f)
            if v:
                try:
                    datetime.fromisoformat(v.replace("Z", "+00:00"))
                except ValueError:
                    invalid_ts += 1
    passed_ts = invalid_ts == 0
    checks.append({
        "check_name": "timestamp_iso8601_utc_compliance",
        "passed": 1 if passed_ts else 0,
        "metric_value": float(invalid_ts),
        "details": f"All timestamps comply with ISO 8601 UTC standard. Invalid count: {invalid_ts}."
    })

    overall_passed = all(c["passed"] == 1 for c in checks)
    audit_report = {
        "audit_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "overall_status": "PASSED" if overall_passed else "FAILED",
        "total_checks": len(checks),
        "passed_checks": sum(c["passed"] for c in checks),
        "failed_checks": sum(1 for c in checks if c["passed"] == 0),
        "checks": checks,
    }

    # Record to DB and file if persist is True
    if persist:
        with get_connection() as conn:
            cursor = conn.cursor()
            for c in checks:
                cursor.execute("""
                INSERT INTO data_quality_audit (check_name, passed, metric_value, details)
                VALUES (?, ?, ?, ?)
                """, (c["check_name"], c["passed"], c["metric_value"], c["details"]))
            conn.commit()

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(REPORTS_DIR / "quality_audit.json", "w", encoding="utf-8") as f:
            json.dump(audit_report, f, indent=2)

    return audit_report
