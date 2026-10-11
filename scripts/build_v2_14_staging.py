"""
Syrian Airport Data Engine — Version 2.14
Historical FIDS Snapshot Extraction, Staging, Validation & Report Generator

Extracts and validates the verified Wayback Machine snapshot of damairport.gov.sy/api/flights.php
captured on 2026-07-09T23:42:30Z.

Builds:
- data/archived_fids_staging.db (5 tables: snapshots, raw, normalized, issues, daily coverage)
- reports/v2_14_archived_fids_records.csv
- reports/v2_14_archived_fids_records.json
- reports/v2_14_daily_coverage.csv
- reports/v2_14_airline_summary.csv
- reports/v2_14_status_summary.csv
- reports/v2_14_validation_issues.csv

Strict Safety:
- Never touches data/damascus_airport.db.
- Verifies production hash before and after.
"""

import os
import csv
import json
import sqlite3
import hashlib
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Tuple

PROD_DB_PATH = "data/damascus_airport.db"
STAGING_DB_PATH = "data/archived_fids_staging.db"
EXPECTED_PROD_HASH = "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"

RAW_SNAPSHOT_PATH = "data/raw/snapshots/wayback_damairport_fids_20260709234230.raw"
JSON_SNAPSHOT_PATH = "data/raw/snapshots/wayback_damairport_fids_20260709234230.json"

SNAPSHOT_URL = "https://web.archive.org/web/20260709234230id_/https://damairport.gov.sy/api/flights.php"
SNAPSHOT_TIMESTAMP = "2026-07-09T23:42:30Z"

def get_file_sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

# Standard airline mapping: Arabic name -> (English Name, IATA code)
AIRLINE_MAP = {
    "طيران العربية": ("Air Arabia", "G9"),
    "العربية للطيران": ("Air Arabia", "G9"),
    "فلاي ناس": ("Flynas", "XY"),
    "طيران ناس": ("Flynas", "XY"),
    "فلاي دبي": ("flydubai", "FZ"),
    "الخطوط التركية": ("Turkish Airlines", "TK"),
    "الخطوط الجوية التركية": ("Turkish Airlines", "TK"),
    "أناضول جت": ("AJet", "VF"),
    "إيه جيت": ("AJet", "VF"),
    "الخطوط القطرية": ("Qatar Airways", "QR"),
    "الخطوط الجوية القطرية": ("Qatar Airways", "QR"),
    "الاتحاد": ("Etihad Airways", "EY"),
    "الاتحاد للطيران": ("Etihad Airways", "EY"),
    "فلاي شام": ("Fly Cham", "XH"),
    "السورية للطيران": ("Syrian Airlines", "RB"),
    "دان أير": ("Dan Air", "DN"),
    "دان إير": ("Dan Air", "DN"),
    "طيران الجزيرة": ("Jazeera Airways", "J9"),
    "الملكية الأردنية": ("Royal Jordanian", "RJ"),
    "فلاي إديل": ("Flyadeal", "F3"),
    "طيران أديل": ("Flyadeal", "F3"),
    "الأمم المتحدة": ("United Nations", "UN"),
    "الخطوط الجوية الكويتية": ("Kuwait Airways", "KU"),
}

def normalize_flight_number(raw_fn: str) -> str:
    if not raw_fn:
        return ""
    # Remove excessive spaces e.g. "XH  728" -> "XH728" or "RB 444" -> "RB444"
    cleaned = "".join(raw_fn.split()).upper()
    return cleaned

def build_staging():
    # 1. Verify production database hash before
    hash_before = get_file_sha256(PROD_DB_PATH)
    assert hash_before == EXPECTED_PROD_HASH, f"Production hash mismatch before: {hash_before}"
    print(f"Production DB Hash BEFORE: {hash_before}")

    # 2. Verify snapshot files exist
    assert os.path.exists(RAW_SNAPSHOT_PATH), f"Missing raw snapshot: {RAW_SNAPSHOT_PATH}"
    assert os.path.exists(JSON_SNAPSHOT_PATH), f"Missing JSON snapshot: {JSON_SNAPSHOT_PATH}"

    raw_bytes_size = os.path.getsize(RAW_SNAPSHOT_PATH)
    raw_sha256 = get_file_sha256(RAW_SNAPSHOT_PATH)
    decomp_bytes_size = os.path.getsize(JSON_SNAPSHOT_PATH)
    decomp_sha256 = get_file_sha256(JSON_SNAPSHOT_PATH)

    with open(JSON_SNAPSHOT_PATH, "r", encoding="utf-8") as f:
        payload = json.load(f)

    raw_flights = payload.get("flights", [])
    raw_airlines = payload.get("airlines", [])
    settings = payload.get("settings", {})

    print(f"Snapshot verified: {len(raw_flights)} flights, {len(raw_airlines)} airlines")

    # 3. Initialize staging database
    if os.path.exists(STAGING_DB_PATH):
        os.remove(STAGING_DB_PATH)

    conn = sqlite3.connect(STAGING_DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE archived_snapshots (
        snapshot_id TEXT PRIMARY KEY,
        archive_provider TEXT NOT NULL,
        original_url TEXT NOT NULL,
        archive_url TEXT NOT NULL,
        snapshot_timestamp TEXT NOT NULL,
        http_status INTEGER NOT NULL,
        content_type TEXT NOT NULL,
        content_encoding TEXT NOT NULL,
        raw_bytes_size INTEGER NOT NULL,
        raw_sha256 TEXT NOT NULL,
        decompressed_bytes_size INTEGER NOT NULL,
        decompressed_sha256 TEXT NOT NULL,
        raw_file_path TEXT NOT NULL,
        json_file_path TEXT NOT NULL,
        flight_objects_count INTEGER NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE archived_fids_raw_records (
        raw_record_id TEXT PRIMARY KEY,
        snapshot_id TEXT NOT NULL,
        source_id TEXT NOT NULL,
        raw_flight_number TEXT,
        raw_airline TEXT,
        raw_direction TEXT,
        raw_origin TEXT,
        raw_origin_text TEXT,
        raw_destination TEXT,
        raw_destination_text TEXT,
        raw_date TEXT,
        raw_time TEXT,
        raw_gate TEXT,
        raw_aircraft TEXT,
        raw_status TEXT,
        raw_created_at TEXT,
        raw_json TEXT NOT NULL,
        record_hash TEXT NOT NULL,
        FOREIGN KEY (snapshot_id) REFERENCES archived_snapshots(snapshot_id)
    );
    """)

    cur.execute("""
    CREATE TABLE archived_fids_normalized (
        normalized_id TEXT PRIMARY KEY,
        raw_record_id TEXT NOT NULL,
        snapshot_id TEXT NOT NULL,
        airport_iata TEXT NOT NULL,
        airport_icao TEXT NOT NULL,
        flight_number TEXT NOT NULL,
        airline_name_ar TEXT NOT NULL,
        airline_name_en TEXT NOT NULL,
        airline_iata TEXT,
        movement_type TEXT NOT NULL,
        origin_iata TEXT NOT NULL,
        destination_iata TEXT NOT NULL,
        scheduled_date TEXT NOT NULL,
        scheduled_time TEXT NOT NULL,
        scheduled_datetime_utc TEXT,
        scheduled_datetime_local TEXT,
        flight_status TEXT NOT NULL,
        classification TEXT NOT NULL,
        is_duplicate INTEGER NOT NULL,
        composite_key TEXT NOT NULL,
        has_actual_timestamp INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (raw_record_id) REFERENCES archived_fids_raw_records(raw_record_id),
        FOREIGN KEY (snapshot_id) REFERENCES archived_snapshots(snapshot_id)
    );
    """)

    cur.execute("""
    CREATE TABLE archived_fids_validation_issues (
        issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
        raw_record_id TEXT NOT NULL,
        normalized_id TEXT NOT NULL,
        issue_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        field_name TEXT NOT NULL,
        field_value TEXT,
        description TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE archived_fids_daily_coverage (
        flight_date TEXT PRIMARY KEY,
        total_records INTEGER NOT NULL,
        arrival_count INTEGER NOT NULL,
        departure_count INTEGER NOT NULL,
        unique_airlines INTEGER NOT NULL,
        unique_flight_numbers INTEGER NOT NULL,
        scheduled_count INTEGER NOT NULL,
        arrived_count INTEGER NOT NULL,
        cancelled_count INTEGER NOT NULL,
        unknown_count INTEGER NOT NULL,
        coverage_classification TEXT NOT NULL
    );
    """)

    now_iso = datetime.utcnow().isoformat() + "Z"

    # Insert Snapshot Metadata
    snap_id = "snap_wayback_20260709234230"
    cur.execute("""
    INSERT INTO archived_snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        snap_id,
        "wayback_machine",
        "https://damairport.gov.sy/api/flights.php",
        SNAPSHOT_URL,
        SNAPSHOT_TIMESTAMP,
        200,
        "application/json; charset=utf-8",
        "gzip",
        raw_bytes_size,
        raw_sha256,
        decomp_bytes_size,
        decomp_sha256,
        RAW_SNAPSHOT_PATH,
        JSON_SNAPSHOT_PATH,
        len(raw_flights),
        now_iso
    ))

    # Process Flight Records
    seen_composite_keys = set()
    normalized_records = []
    raw_records_to_insert = []
    validation_issues = []

    for idx, raw in enumerate(raw_flights):
        source_id = raw.get("id", f"missing_id_{idx}")
        raw_rec_id = f"raw_{idx+1:05d}_{source_id[:8]}"
        norm_id = f"norm_{idx+1:05d}_{source_id[:8]}"

        raw_str = json.dumps(raw, sort_keys=True, ensure_ascii=False)
        rec_hash = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

        fn_raw = raw.get("flightNumber", "")
        fn_norm = normalize_flight_number(fn_raw)

        airline_ar = raw.get("airline", "")
        airline_en, airline_iata = AIRLINE_MAP.get(airline_ar, ("Unknown Airline", None))

        direction = raw.get("direction", "").lower()
        origin = raw.get("origin", "")
        destination = raw.get("destination", "")

        f_date = raw.get("date", "")
        f_time = raw.get("time", "")

        gate = raw.get("gate", "")
        aircraft = raw.get("aircraft", "")
        status_raw = raw.get("status", "").lower()

        # Validation issues
        if not gate:
            validation_issues.append((
                raw_rec_id, norm_id, "missing_gate", "INFO", "gate", "",
                "Gate assignment field is empty in source payload"
            ))
        if not aircraft:
            validation_issues.append((
                raw_rec_id, norm_id, "missing_aircraft", "INFO", "aircraft", "",
                "Aircraft equipment/registration field is empty in source payload"
            ))
        if not raw.get("originText") and direction == "arrival":
            validation_issues.append((
                raw_rec_id, norm_id, "missing_origin_text", "INFO", "originText", "",
                "Origin descriptive city text is empty in source payload"
            ))
        if not raw.get("destinationText") and direction == "departure":
            validation_issues.append((
                raw_rec_id, norm_id, "missing_destination_text", "INFO", "destinationText", "",
                "Destination descriptive city text is empty in source payload"
            ))

        # Check date validity
        try:
            parsed_date = datetime.strptime(f_date, "%Y-%m-%d").date()
            if f_date < "2026-07-05" or f_date > "2026-09-09":
                validation_issues.append((
                    raw_rec_id, norm_id, "date_out_of_reported_range", "WARNING", "date", f_date,
                    "Flight scheduled date falls outside reported July 5 - Sept 9 window"
                ))
        except Exception:
            validation_issues.append((
                raw_rec_id, norm_id, "invalid_date_format", "ERROR", "date", f_date,
                "Scheduled date could not be parsed as YYYY-MM-DD"
            ))

        # Check time validity
        sched_dt_utc = None
        sched_dt_local = None
        try:
            # Time format expected "HH:MM"
            if len(f_time) == 5 and ":" in f_time:
                sched_dt_local = f"{f_date}T{f_time}:00+03:00"
                # Damascus is UTC+3 in summer
                dt_obj = datetime.strptime(f"{f_date} {f_time}", "%Y-%m-%d %H:%M")
                utc_dt = dt_obj - timedelta(hours=3)
                sched_dt_utc = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                validation_issues.append((
                    raw_rec_id, norm_id, "malformed_time", "WARNING", "time", f_time,
                    "Scheduled time format is not standard HH:MM"
                ))
        except Exception as e:
            validation_issues.append((
                raw_rec_id, norm_id, "invalid_time_calc", "ERROR", "time", f_time,
                f"Error converting time to UTC: {e}"
            ))

        # Check actual timestamps
        has_actual = 0
        # Classification rules
        if status_raw == "arrived":
            classification = "archived_actual_movement_candidate"
            validation_issues.append((
                raw_rec_id, norm_id, "status_arrived_without_sensor_ts", "WARNING", "status", status_raw,
                "Record status is 'arrived' but payload contains no transponder/radar timestamp; cannot promote to physical movement"
            ))
        elif status_raw == "cancelled":
            classification = "archived_cancelled_service"
        elif status_raw == "scheduled":
            classification = "archived_scheduled_service"
        else:
            classification = "archived_status_unknown"
            validation_issues.append((
                raw_rec_id, norm_id, "unknown_status", "WARNING", "status", status_raw,
                f"Status '{status_raw}' is unrecognized"
            ))

        # Composite key for deduplication
        comp_key = f"{fn_norm}_{direction}_{f_date}_{f_time}"
        is_dup = 1 if comp_key in seen_composite_keys else 0
        if is_dup:
            validation_issues.append((
                raw_rec_id, norm_id, "semantic_duplicate", "WARNING", "composite_key", comp_key,
                "Duplicate flight number, direction, date, and scheduled time detected"
            ))
        seen_composite_keys.add(comp_key)

        raw_records_to_insert.append((
            raw_rec_id,
            snap_id,
            source_id,
            fn_raw,
            airline_ar,
            direction,
            origin,
            raw.get("originText", ""),
            destination,
            raw.get("destinationText", ""),
            f_date,
            f_time,
            gate,
            aircraft,
            status_raw,
            raw.get("createdAt", ""),
            raw_str,
            rec_hash
        ))

        normalized_records.append((
            norm_id,
            raw_rec_id,
            snap_id,
            "DAM",
            "OSDI",
            fn_norm,
            airline_ar,
            airline_en,
            airline_iata,
            direction,
            origin,
            destination,
            f_date,
            f_time,
            sched_dt_utc,
            sched_dt_local,
            status_raw,
            classification,
            is_dup,
            comp_key,
            has_actual,
            now_iso
        ))

    cur.executemany("""
    INSERT INTO archived_fids_raw_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, raw_records_to_insert)

    cur.executemany("""
    INSERT INTO archived_fids_normalized VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, normalized_records)

    cur.executemany("""
    INSERT INTO archived_fids_validation_issues (raw_record_id, normalized_id, issue_type, severity, field_name, field_value, description)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, validation_issues)

    # 4. Populate Daily Coverage Matrix for all calendar days from 2026-07-05 to 2026-09-09
    start_dt = date(2026, 7, 5)
    end_dt = date(2026, 9, 9)
    cur_dt = start_dt

    daily_rows = []
    while cur_dt <= end_dt:
        dt_str = cur_dt.strftime("%Y-%m-%d")
        day_records = [r for r in normalized_records if r[12] == dt_str]
        
        tot = len(day_records)
        arr = sum(1 for r in day_records if r[9] == "arrival")
        dep = sum(1 for r in day_records if r[9] == "departure")
        uniq_air = len(set(r[7] for r in day_records))
        uniq_fn = len(set(r[5] for r in day_records))
        sched = sum(1 for r in day_records if r[16] == "scheduled")
        arrived = sum(1 for r in day_records if r[16] == "arrived")
        canc = sum(1 for r in day_records if r[16] == "cancelled")
        unk = sum(1 for r in day_records if r[16] not in ("scheduled", "arrived", "cancelled"))
        
        cov_class = "archived_schedule_present" if tot > 0 else "no_observation"

        daily_rows.append((
            dt_str, tot, arr, dep, uniq_air, uniq_fn, sched, arrived, canc, unk, cov_class
        ))
        cur_dt += timedelta(days=1)

    cur.executemany("""
    INSERT INTO archived_fids_daily_coverage VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, daily_rows)

    conn.commit()
    conn.close()
    print(f"Staging database built: {STAGING_DB_PATH}")

    # 5. Export Reports
    os.makedirs("reports", exist_ok=True)

    # Report 1: All Records (CSV & JSON)
    rec_csv_path = "reports/v2_14_archived_fids_records.csv"
    rec_json_path = "reports/v2_14_archived_fids_records.json"

    fieldnames = [
        "normalized_id", "raw_record_id", "snapshot_id", "airport_iata", "airport_icao",
        "flight_number", "airline_name_ar", "airline_name_en", "airline_iata", "movement_type",
        "origin_iata", "destination_iata", "scheduled_date", "scheduled_time",
        "scheduled_datetime_utc", "scheduled_datetime_local", "flight_status",
        "classification", "is_duplicate", "composite_key", "has_actual_timestamp", "created_at"
    ]

    records_dicts = [dict(zip(fieldnames, r)) for r in normalized_records]

    with open(rec_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records_dicts)
    print(f"Exported: {rec_csv_path} ({len(records_dicts)} rows)")

    with open(rec_json_path, "w", encoding="utf-8") as f:
        json.dump(records_dicts, f, indent=2, ensure_ascii=False)
    print(f"Exported: {rec_json_path}")

    # Report 2: Daily Coverage CSV
    daily_csv_path = "reports/v2_14_daily_coverage.csv"
    daily_fields = [
        "flight_date", "total_records", "arrival_count", "departure_count",
        "unique_airlines", "unique_flight_numbers", "scheduled_count",
        "arrived_count", "cancelled_count", "unknown_count", "coverage_classification"
    ]
    daily_dicts = [dict(zip(daily_fields, r)) for r in daily_rows]
    with open(daily_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=daily_fields)
        writer.writeheader()
        writer.writerows(daily_dicts)
    print(f"Exported: {daily_csv_path} ({len(daily_dicts)} days)")

    # Report 3: Airline Summary CSV
    airline_csv_path = "reports/v2_14_airline_summary.csv"
    conn = sqlite3.connect(STAGING_DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    SELECT 
        airline_name_en,
        airline_name_ar,
        airline_iata,
        COUNT(*) as total_flights,
        SUM(CASE WHEN movement_type = 'arrival' THEN 1 ELSE 0 END) as arrivals,
        SUM(CASE WHEN movement_type = 'departure' THEN 1 ELSE 0 END) as departures,
        COUNT(DISTINCT flight_number) as unique_flight_numbers,
        MIN(scheduled_date) as earliest_date,
        MAX(scheduled_date) as latest_date
    FROM archived_fids_normalized
    GROUP BY airline_name_en, airline_name_ar, airline_iata
    ORDER BY total_flights DESC
    """)
    airline_summary_rows = [
        {
            "airline_name_en": r[0],
            "airline_name_ar": r[1],
            "airline_iata": r[2] or "",
            "total_flights": r[3],
            "arrivals": r[4],
            "departures": r[5],
            "unique_flight_numbers": r[6],
            "earliest_date": r[7],
            "latest_date": r[8]
        }
        for r in cur.fetchall()
    ]
    with open(airline_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(airline_summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(airline_summary_rows)
    print(f"Exported: {airline_csv_path} ({len(airline_summary_rows)} airlines)")

    # Report 4: Status Summary CSV
    status_csv_path = "reports/v2_14_status_summary.csv"
    cur.execute("""
    SELECT 
        flight_status,
        classification,
        COUNT(*) as record_count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM archived_fids_normalized), 2) as percentage,
        SUM(has_actual_timestamp) as with_actual_timestamps
    FROM archived_fids_normalized
    GROUP BY flight_status, classification
    ORDER BY record_count DESC
    """)
    status_summary_rows = [
        {
            "flight_status": r[0],
            "classification": r[1],
            "record_count": r[2],
            "percentage": r[3],
            "with_actual_timestamps": r[4]
        }
        for r in cur.fetchall()
    ]
    with open(status_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(status_summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(status_summary_rows)
    print(f"Exported: {status_csv_path} ({len(status_summary_rows)} statuses)")

    # Report 5: Validation Issues CSV
    issues_csv_path = "reports/v2_14_validation_issues.csv"
    cur.execute("""
    SELECT issue_id, raw_record_id, normalized_id, issue_type, severity, field_name, field_value, description
    FROM archived_fids_validation_issues
    ORDER BY issue_id
    """)
    issue_rows = [
        {
            "issue_id": r[0],
            "raw_record_id": r[1],
            "normalized_id": r[2],
            "issue_type": r[3],
            "severity": r[4],
            "field_name": r[5],
            "field_value": r[6] or "",
            "description": r[7]
        }
        for r in cur.fetchall()
    ]
    with open(issues_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(issue_rows[0].keys()))
        writer.writeheader()
        writer.writerows(issue_rows)
    print(f"Exported: {issues_csv_path} ({len(issue_rows)} issues)")

    conn.close()

    # 6. Verify production database hash after
    hash_after = get_file_sha256(PROD_DB_PATH)
    assert hash_after == EXPECTED_PROD_HASH, f"Production hash mismatch after: {hash_after}"
    print(f"\nProduction DB Hash AFTER:  {hash_after}")
    print(f"Production DB Untouched:   {hash_before == hash_after}")

if __name__ == "__main__":
    build_staging()
