"""
Syrian Airport Data Engine — Version 2.15
Archived FIDS Analytics Layer

Exclusively queries the archived Damascus International Airport (DAM / OSDI)
FIDS snapshot dataset covering 2026-07-05 to 2026-09-09 (1,982 records).

Strict Architectural Invariants:
1. Operates on data/archived_fids_staging.db (READ-ONLY) or builds
   data/archived_fids_analytics.db.
2. NEVER modifies data/damascus_airport.db (SHA-256 protected).
3. NEVER promotes archived FIDS records to physical_movement.
4. Segregates scheduled_record_count, displayed_status_count, and physical_movement_evidence_count (= 0).
5. Uses Displayed Airline Distribution semantics (never Operating Airline Distribution).
6. Preserves the candidate duplicate pair G9 376 / 376 without deletion or suppression.
7. Groups hourly distribution by original local Damascus wall-clock time (Asia/Damascus).
"""

import os
import io
import csv
import json
import sqlite3
import hashlib
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple
from fastapi import APIRouter, Query, HTTPException, Response

STAGING_DB_PATH = "data/archived_fids_staging.db"
ANALYTICS_DB_PATH = "data/archived_fids_analytics.db"
PROD_DB_PATH = "data/damascus_airport.db"
EXPECTED_PROD_HASH = "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"

SEMANTIC_WARNING = "These records represent archived scheduled/displayed flight information, not verified physical aircraft movements."

SNAPSHOT_PROVENANCE = {
    "snapshot_id": "snap_wayback_20260709234230",
    "memento_timestamp": "2026-07-09T23:42:30Z",
    "source_url": "https://damairport.gov.sy/api/flights.php",
    "archive_url": "https://web.archive.org/web/20260709234230id_/https://damairport.gov.sy/api/flights.php",
    "date_coverage_start": "2026-07-05",
    "date_coverage_end": "2026-09-09",
    "consecutive_days": 67,
    "physical_movement_evidence_count": 0,
    "timezone": "Asia/Damascus (UTC+3)",
    "disclaimer": SEMANTIC_WARNING
}

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def get_file_sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def get_staging_connection() -> sqlite3.Connection:
    """Returns a strictly read-only connection to the staging database."""
    if not os.path.exists(STAGING_DB_PATH):
        raise FileNotFoundError(f"Staging database missing: {STAGING_DB_PATH}")
    conn = sqlite3.connect(f"file:{STAGING_DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn

def get_analytics_connection() -> sqlite3.Connection:
    """Returns a connection to the analytics database, initializing it if needed."""
    if not os.path.exists(ANALYTICS_DB_PATH):
        build_analytics_database()
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def build_analytics_database(rebuild: bool = False) -> str:
    """
    Builds data/archived_fids_analytics.db from data/archived_fids_staging.db.
    Guaranteed deterministic and idempotent. Never modifies the staging database.
    """
    if os.path.exists(ANALYTICS_DB_PATH) and not rebuild:
        return ANALYTICS_DB_PATH

    # Verify staging DB exists
    if not os.path.exists(STAGING_DB_PATH):
        raise FileNotFoundError(f"Cannot build analytics DB: staging database missing at {STAGING_DB_PATH}")

    # Remove old analytics DB if rebuilding
    if os.path.exists(ANALYTICS_DB_PATH):
        os.remove(ANALYTICS_DB_PATH)

    conn_staging = get_staging_connection()
    cur_staging = conn_staging.cursor()

    cur_staging.execute("""
    SELECT
        normalized_id, raw_record_id, snapshot_id, source_uuid, raw_record_hash,
        airport_iata, airport_icao, flight_number, airline_name_ar, airline_name_en,
        airline_iata, airline_role, movement_type, origin_iata, destination_iata,
        scheduled_date, scheduled_time, scheduled_datetime_utc, scheduled_datetime_local,
        scheduled_status, displayed_status, actual_movement_evidence, classification,
        is_duplicate, composite_key, created_at
    FROM archived_fids_normalized
    ORDER BY scheduled_date, scheduled_time, flight_number
    """)
    records = [dict(r) for r in cur_staging.fetchall()]
    conn_staging.close()

    conn_out = sqlite3.connect(ANALYTICS_DB_PATH)
    cur_out = conn_out.cursor()

    cur_out.execute("""
    CREATE TABLE fids_analytics_records (
        record_id TEXT PRIMARY KEY,
        raw_record_id TEXT NOT NULL,
        snapshot_id TEXT NOT NULL,
        source_uuid TEXT NOT NULL,
        raw_record_hash TEXT NOT NULL,
        airport_iata TEXT NOT NULL,
        airport_icao TEXT NOT NULL,
        flight_number TEXT NOT NULL,
        airline_name_ar TEXT NOT NULL,
        airline_name_en TEXT NOT NULL,
        airline_iata TEXT,
        airline_role TEXT NOT NULL,
        movement_type TEXT NOT NULL,
        origin_iata TEXT NOT NULL,
        destination_iata TEXT NOT NULL,
        scheduled_date TEXT NOT NULL,
        scheduled_time TEXT NOT NULL,
        scheduled_datetime_utc TEXT,
        scheduled_datetime_local TEXT NOT NULL,
        scheduled_status TEXT NOT NULL,
        displayed_status TEXT NOT NULL,
        actual_movement_evidence INTEGER NOT NULL,
        classification TEXT NOT NULL,
        is_duplicate_candidate INTEGER NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    cur_out.execute("CREATE INDEX idx_fids_date ON fids_analytics_records(scheduled_date);")
    cur_out.execute("CREATE INDEX idx_fids_movement ON fids_analytics_records(movement_type);")
    cur_out.execute("CREATE INDEX idx_fids_airline ON fids_analytics_records(airline_name_en);")
    cur_out.execute("CREATE INDEX idx_fids_route ON fids_analytics_records(origin_iata, destination_iata);")

    # Table for duplicate candidates
    cur_out.execute("""
    CREATE TABLE fids_duplicate_candidates (
        candidate_id TEXT PRIMARY KEY,
        group_type TEXT NOT NULL,
        source_uuid_1 TEXT NOT NULL,
        flight_number_1 TEXT NOT NULL,
        airline_1 TEXT NOT NULL,
        source_uuid_2 TEXT NOT NULL,
        flight_number_2 TEXT NOT NULL,
        airline_2 TEXT NOT NULL,
        scheduled_date TEXT NOT NULL,
        scheduled_time TEXT NOT NULL,
        movement_type TEXT NOT NULL,
        origin_iata TEXT NOT NULL,
        destination_iata TEXT NOT NULL,
        duplicate_classification TEXT NOT NULL,
        review_status TEXT NOT NULL,
        audit_finding TEXT NOT NULL
    );
    """)

    for r in records:
        # Check if record is part of the known candidate pair G9 376 / 376 on 2026-07-08 at 13:55
        is_cand = 1 if r["source_uuid"] in ("e5ada70d-5245-46d4-b043-bf469c1d104f", "2d2a0935-da5e-42c4-ad15-e10b4e2291ee") else 0
        cur_out.execute("""
        INSERT INTO fids_analytics_records VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """, (
            r["normalized_id"], r["raw_record_id"], r["snapshot_id"], r["source_uuid"], r["raw_record_hash"],
            r["airport_iata"], r["airport_icao"], r["flight_number"], r["airline_name_ar"], r["airline_name_en"],
            r["airline_iata"], r["airline_role"] or "displayed_airline_brand", r["movement_type"],
            r["origin_iata"], r["destination_iata"], r["scheduled_date"], r["scheduled_time"],
            r["scheduled_datetime_utc"], r["scheduled_datetime_local"],
            r["scheduled_status"] or "scheduled", r["displayed_status"] or r["flight_status"],
            0, # actual_movement_evidence is strictly 0
            r["classification"], is_cand, r["created_at"]
        ))

    # Insert known duplicate candidate pair
    cur_out.execute("""
    INSERT INTO fids_duplicate_candidates VALUES (
        'DUP_CANDIDATE_001',
        'possible_prefix_variant_duplicate',
        'e5ada70d-5245-46d4-b043-bf469c1d104f',
        'G9 376',
        'طيران العربية',
        '2d2a0935-da5e-42c4-ad15-e10b4e2291ee',
        '376',
        'طيران العربية',
        '2026-07-08',
        '13:55',
        'departure',
        'DAM',
        'SHJ',
        'possible_prefix_variant_duplicate',
        'requires_manual_review',
        'Carrier code G9 omitted in second entry during 2026-07-07 batch upload; both records preserved in staging without deletion.'
    )
    """)

    conn_out.commit()
    conn_out.close()
    return ANALYTICS_DB_PATH

# -------------------------------------------------------------------------
# Filter Validation Helper
# -------------------------------------------------------------------------
def validate_filters(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    direction: Optional[str] = None,
    airline: Optional[str] = None
) -> Tuple[str, List[Any]]:
    """Validates filters and returns SQL WHERE clause and parameter list."""
    clauses = ["1=1"]
    params = []

    if start_date:
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid start_date format '{start_date}'. Expected YYYY-MM-DD.")
        clauses.append("scheduled_date >= ?")
        params.append(start_date)

    if end_date:
        try:
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid end_date format '{end_date}'. Expected YYYY-MM-DD.")
        clauses.append("scheduled_date <= ?")
        params.append(end_date)

    if start_date and end_date and start_date > end_date:
        raise ValueError(f"start_date '{start_date}' cannot be greater than end_date '{end_date}'.")

    if direction and direction.lower() not in ("all", ""):
        dir_clean = direction.lower().strip()
        if dir_clean not in ("arrival", "departure"):
            raise ValueError(f"Invalid direction '{direction}'. Allowed values: arrival, departure, all.")
        clauses.append("movement_type = ?")
        params.append(dir_clean)

    if airline and airline.strip():
        al = airline.strip()
        clauses.append("(airline_name_en = ? OR airline_name_ar = ? OR airline_iata = ?)")
        params.extend([al, al, al.upper()])

    return " AND ".join(clauses), params

# -------------------------------------------------------------------------
# A. Overall Summary Metrics
# -------------------------------------------------------------------------
def get_fids_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    direction: Optional[str] = None,
    airline: Optional[str] = None
) -> Dict[str, Any]:
    where_sql, params = validate_filters(start_date, end_date, direction, airline)
    conn = get_analytics_connection()
    cur = conn.cursor()

    cur.execute(f"""
    SELECT
        COUNT(*) as total_records,
        SUM(CASE WHEN movement_type = 'arrival' THEN 1 ELSE 0 END) as arrivals_count,
        SUM(CASE WHEN movement_type = 'departure' THEN 1 ELSE 0 END) as departures_count,
        COUNT(DISTINCT scheduled_date) as calendar_days_count,
        COUNT(DISTINCT airline_name_en) as unique_airline_brands,
        COUNT(DISTINCT flight_number) as unique_flight_numbers,
        SUM(CASE WHEN displayed_status = 'scheduled' THEN 1 ELSE 0 END) as scheduled_status_count,
        SUM(CASE WHEN displayed_status = 'arrived' THEN 1 ELSE 0 END) as arrived_status_count,
        MIN(scheduled_date) as min_date,
        MAX(scheduled_date) as max_date,
        SUM(is_duplicate_candidate) as duplicate_candidates_count
    FROM fids_analytics_records
    WHERE {where_sql}
    """, params)
    row = dict(cur.fetchone())
    conn.close()

    total = row["total_records"] or 0
    return {
        "status": "success",
        "semantic_warning": SEMANTIC_WARNING,
        "provenance": SNAPSHOT_PROVENANCE,
        "filters_applied": {
            "start_date": start_date,
            "end_date": end_date,
            "direction": direction,
            "airline": airline
        },
        "summary": {
            "total_archived_fids_records": total,
            "scheduled_arrivals": row["arrivals_count"] or 0,
            "scheduled_departures": row["departures_count"] or 0,
            "calendar_days_covered": row["calendar_days_count"] or 0,
            "date_range": {
                "earliest_scheduled_date": row["min_date"] or "2026-07-05",
                "latest_scheduled_date": row["max_date"] or "2026-09-09"
            },
            "displayed_airline_brands_count": row["unique_airline_brands"] or 0,
            "unique_scheduled_flight_numbers": row["unique_flight_numbers"] or 0,
            "status_distribution": {
                "scheduled": row["scheduled_status_count"] or 0,
                "arrived": row["arrived_status_count"] or 0
            },
            "duplicate_candidates_count": row["duplicate_candidates_count"] or 0,
            "physical_movement_evidence_count": 0
        }
    }

# -------------------------------------------------------------------------
# B. Daily Scheduled Flights
# -------------------------------------------------------------------------
def get_daily_scheduled_flights(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    direction: Optional[str] = None,
    airline: Optional[str] = None
) -> Dict[str, Any]:
    where_sql, params = validate_filters(start_date, end_date, direction, airline)
    conn = get_analytics_connection()
    cur = conn.cursor()

    cur.execute(f"""
    SELECT
        scheduled_date as flight_date,
        COUNT(*) as total_scheduled_records,
        SUM(CASE WHEN movement_type = 'arrival' THEN 1 ELSE 0 END) as arrival_records,
        SUM(CASE WHEN movement_type = 'departure' THEN 1 ELSE 0 END) as departure_records,
        COUNT(DISTINCT flight_number) as unique_displayed_flight_numbers,
        COUNT(DISTINCT airline_name_en) as unique_displayed_airline_brands,
        SUM(CASE WHEN displayed_status = 'scheduled' THEN 1 ELSE 0 END) as scheduled_status_count,
        SUM(CASE WHEN displayed_status != 'scheduled' THEN 1 ELSE 0 END) as other_display_status_count,
        SUM(is_duplicate_candidate) as duplicate_candidates_count
    FROM fids_analytics_records
    WHERE {where_sql}
    GROUP BY scheduled_date
    ORDER BY scheduled_date ASC
    """, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    return {
        "status": "success",
        "semantic_warning": SEMANTIC_WARNING,
        "provenance": SNAPSHOT_PROVENANCE,
        "total_days": len(rows),
        "daily_records": rows
    }

# -------------------------------------------------------------------------
# C. Displayed Airline Analysis
# -------------------------------------------------------------------------
def get_displayed_airline_analysis(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    direction: Optional[str] = None
) -> Dict[str, Any]:
    where_sql, params = validate_filters(start_date, end_date, direction, airline=None)
    conn = get_analytics_connection()
    cur = conn.cursor()

    cur.execute(f"SELECT COUNT(*) FROM fids_analytics_records WHERE {where_sql}", params)
    total_records = cur.fetchone()[0] or 1

    cur.execute(f"""
    SELECT
        airline_name_ar as displayed_airline_brand_ar,
        airline_name_en as displayed_airline_brand_en,
        airline_iata as source_iata_code,
        airline_role as carrier_role_classification,
        COUNT(*) as total_displayed_records,
        SUM(CASE WHEN movement_type = 'arrival' THEN 1 ELSE 0 END) as arrival_records,
        SUM(CASE WHEN movement_type = 'departure' THEN 1 ELSE 0 END) as departure_records,
        COUNT(DISTINCT flight_number) as distinct_flight_numbers,
        COUNT(DISTINCT scheduled_date) as active_days_count,
        MIN(scheduled_date) as first_active_date,
        MAX(scheduled_date) as last_active_date
    FROM fids_analytics_records
    WHERE {where_sql}
    GROUP BY airline_name_ar, airline_name_en, airline_iata, airline_role
    ORDER BY total_displayed_records DESC
    """, params)
    raw_airlines = [dict(r) for r in cur.fetchall()]
    conn.close()

    results = []
    for r in raw_airlines:
        cnt = r["total_displayed_records"]
        pct = round((cnt / total_records) * 100, 2)
        active_days = r["active_days_count"] or 1
        daily_freq_active = round(cnt / active_days, 2)
        daily_freq_overall = round(cnt / 67.0, 2)
        r["percentage_of_total"] = f"{pct:.2f}%"
        r["percentage_value"] = pct
        r["daily_frequency_active_days"] = daily_freq_active
        r["daily_frequency_67_days"] = daily_freq_overall
        r["is_operating_carrier_verified"] = False
        results.append(r)

    return {
        "status": "success",
        "metric_label": "Displayed Airline Distribution",
        "semantic_warning": SEMANTIC_WARNING,
        "provenance": SNAPSHOT_PROVENANCE,
        "total_displayed_records": total_records,
        "airline_brands_count": len(results),
        "airlines": results
    }

# -------------------------------------------------------------------------
# D. Destination and Route Analysis
# -------------------------------------------------------------------------
def get_destination_and_route_analysis(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    direction: Optional[str] = None,
    airline: Optional[str] = None,
    top_limit: int = 20
) -> Dict[str, Any]:
    where_sql, params = validate_filters(start_date, end_date, direction, airline)
    conn = get_analytics_connection()
    cur = conn.cursor()

    cur.execute(f"""
    SELECT
        origin_iata as airport_code,
        movement_type,
        COUNT(*) as scheduled_flight_count,
        COUNT(DISTINCT flight_number) as distinct_flight_numbers,
        COUNT(DISTINCT airline_name_en) as distinct_airlines
    FROM fids_analytics_records
    WHERE {where_sql}
    GROUP BY origin_iata, movement_type
    ORDER BY scheduled_flight_count DESC
    LIMIT ?
    """, params + [top_limit])
    top_origins = [dict(r) for r in cur.fetchall()]

    cur.execute(f"""
    SELECT
        destination_iata as airport_code,
        movement_type,
        COUNT(*) as scheduled_flight_count,
        COUNT(DISTINCT flight_number) as distinct_flight_numbers,
        COUNT(DISTINCT airline_name_en) as distinct_airlines
    FROM fids_analytics_records
    WHERE {where_sql}
    GROUP BY destination_iata, movement_type
    ORDER BY scheduled_flight_count DESC
    LIMIT ?
    """, params + [top_limit])
    top_destinations = [dict(r) for r in cur.fetchall()]

    cur.execute(f"""
    SELECT
        origin_iata || '-' || destination_iata as route_pair,
        origin_iata,
        destination_iata,
        movement_type,
        COUNT(*) as scheduled_records_count,
        COUNT(DISTINCT flight_number) as unique_displayed_flight_numbers,
        COUNT(DISTINCT airline_name_en) as distinct_airlines_count,
        GROUP_CONCAT(DISTINCT airline_name_en) as airlines_list
    FROM fids_analytics_records
    WHERE {where_sql}
    GROUP BY origin_iata, destination_iata, movement_type
    ORDER BY scheduled_records_count DESC
    LIMIT ?
    """, params + [top_limit])
    top_routes = [dict(r) for r in cur.fetchall()]
    conn.close()

    return {
        "status": "success",
        "semantic_warning": SEMANTIC_WARNING,
        "provenance": SNAPSHOT_PROVENANCE,
        "top_origins": top_origins,
        "top_destinations": top_destinations,
        "top_routes": top_routes
    }

# -------------------------------------------------------------------------
# E. Hourly Schedule Distribution
# -------------------------------------------------------------------------
def get_hourly_schedule_distribution(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    direction: Optional[str] = None,
    airline: Optional[str] = None
) -> Dict[str, Any]:
    where_sql, params = validate_filters(start_date, end_date, direction, airline)
    conn = get_analytics_connection()
    cur = conn.cursor()

    cur.execute(f"""
    SELECT
        SUBSTR(scheduled_time, 1, 2) as scheduled_hour_local,
        movement_type,
        COUNT(*) as records_count
    FROM fids_analytics_records
    WHERE {where_sql} AND scheduled_time != ''
    GROUP BY scheduled_hour_local, movement_type
    ORDER BY scheduled_hour_local ASC
    """, params)
    rows = cur.fetchall()
    conn.close()

    hourly_map = {
        f"{h:02d}": {
            "hour_local": f"{h:02d}",
            "hour_label": f"{h:02d}:00–{h:02d}:59",
            "arrivals": 0,
            "departures": 0,
            "total": 0
        }
        for h in range(24)
    }

    for r in rows:
        hr = r["scheduled_hour_local"]
        mtype = r["movement_type"]
        cnt = r["records_count"]
        if hr in hourly_map:
            if mtype == "arrival":
                hourly_map[hr]["arrivals"] += cnt
            elif mtype == "departure":
                hourly_map[hr]["departures"] += cnt
            hourly_map[hr]["total"] += cnt

    hourly_list = [hourly_map[f"{h:02d}"] for h in range(24)]

    return {
        "status": "success",
        "timezone": "Asia/Damascus (UTC+3)",
        "timezone_note": "Grouped strictly by local Damascus wall-clock time; not converted to UTC before grouping.",
        "semantic_warning": SEMANTIC_WARNING,
        "provenance": SNAPSHOT_PROVENANCE,
        "hourly_distribution": hourly_list
    }

# -------------------------------------------------------------------------
# F. Weekly and Daily Patterns
# -------------------------------------------------------------------------
def get_weekly_and_daily_patterns(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    direction: Optional[str] = None,
    airline: Optional[str] = None
) -> Dict[str, Any]:
    where_sql, params = validate_filters(start_date, end_date, direction, airline)
    conn = get_analytics_connection()
    cur = conn.cursor()

    cur.execute(f"""
    SELECT
        scheduled_date as flight_date,
        COUNT(*) as total_flights,
        SUM(CASE WHEN movement_type = 'arrival' THEN 1 ELSE 0 END) as arrival_count,
        SUM(CASE WHEN movement_type = 'departure' THEN 1 ELSE 0 END) as departure_count
    FROM fids_analytics_records
    WHERE {where_sql}
    GROUP BY scheduled_date
    ORDER BY scheduled_date ASC
    """, params)
    daily_rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    total_days = len(daily_rows) or 1
    total_flights = sum(r["total_flights"] for r in daily_rows)
    total_arr = sum(r["arrival_count"] for r in daily_rows)
    total_dep = sum(r["departure_count"] for r in daily_rows)

    avg_daily = round(total_flights / total_days, 2)
    avg_arr = round(total_arr / total_days, 2)
    avg_dep = round(total_dep / total_days, 2)

    weekday_stats = {
        idx: {
            "weekday_index": idx,
            "weekday_name": WEEKDAY_NAMES[idx],
            "day_occurrences": 0,
            "total_flights": 0,
            "arrival_flights": 0,
            "departure_flights": 0,
            "average_flights_per_weekday": 0.0
        }
        for idx in range(7)
    }

    for d in daily_rows:
        dt = datetime.strptime(d["flight_date"], "%Y-%m-%d").date()
        w_idx = dt.weekday()
        weekday_stats[w_idx]["day_occurrences"] += 1
        weekday_stats[w_idx]["total_flights"] += d["total_flights"]
        weekday_stats[w_idx]["arrival_flights"] += d["arrival_count"]
        weekday_stats[w_idx]["departure_flights"] += d["departure_count"]

    for w_idx in range(7):
        occ = weekday_stats[w_idx]["day_occurrences"] or 1
        weekday_stats[w_idx]["average_flights_per_weekday"] = round(
            weekday_stats[w_idx]["total_flights"] / occ, 2
        )

    weekday_list = [weekday_stats[idx] for idx in range(7)]

    sorted_by_vol = sorted(daily_rows, key=lambda x: x["total_flights"], reverse=True)
    busiest_days = sorted_by_vol[:5]
    quietest_days = sorted_by_vol[-5:][::-1]
    busiest_weekdays = sorted(weekday_list, key=lambda x: x["average_flights_per_weekday"], reverse=True)

    return {
        "status": "success",
        "semantic_warning": SEMANTIC_WARNING,
        "provenance": SNAPSHOT_PROVENANCE,
        "period_statistics": {
            "total_calendar_days": total_days,
            "total_scheduled_records": total_flights,
            "average_records_per_calendar_day": avg_daily,
            "average_arrivals_per_calendar_day": avg_arr,
            "average_departures_per_calendar_day": avg_dep
        },
        "weekday_distribution": weekday_list,
        "busiest_calendar_days": busiest_days,
        "quietest_calendar_days": quietest_days,
        "busiest_weekdays": busiest_weekdays
    }

# -------------------------------------------------------------------------
# G. Duplicate Candidate Reporting
# -------------------------------------------------------------------------
def get_duplicate_candidates() -> Dict[str, Any]:
    conn = get_analytics_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM fids_duplicate_candidates")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    return {
        "status": "success",
        "semantic_warning": SEMANTIC_WARNING,
        "provenance": SNAPSHOT_PROVENANCE,
        "duplicate_candidate_pairs_count": len(rows),
        "candidates": rows,
        "policy_note": "Both source records are preserved unaltered in the database. Neither record is deleted, merged, or suppressed."
    }

# -------------------------------------------------------------------------
# H. Machine-Readable Export Generator
# -------------------------------------------------------------------------
def export_archived_fids_reports(output_dir: str = "reports") -> Dict[str, str]:
    """Generates all 7 required V2.15 analytics report files."""
    os.makedirs(output_dir, exist_ok=True)
    exported_files = {}

    # 1. reports/v2_15_daily_schedule.csv
    daily_res = get_daily_scheduled_flights()
    path1 = os.path.join(output_dir, "v2_15_daily_schedule.csv")
    with open(path1, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "flight_date", "total_scheduled_records", "arrival_records", "departure_records",
            "unique_displayed_flight_numbers", "unique_displayed_airline_brands",
            "scheduled_status_count", "other_display_status_count", "duplicate_candidates_count"
        ])
        for r in daily_res["daily_records"]:
            writer.writerow([
                r["flight_date"], r["total_scheduled_records"], r["arrival_records"],
                r["departure_records"], r["unique_displayed_flight_numbers"],
                r["unique_displayed_airline_brands"], r["scheduled_status_count"],
                r["other_display_status_count"], r["duplicate_candidates_count"]
            ])
    exported_files["daily_schedule_csv"] = path1

    # 2. reports/v2_15_airline_distribution.csv
    al_res = get_displayed_airline_analysis()
    path2 = os.path.join(output_dir, "v2_15_airline_distribution.csv")
    with open(path2, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "displayed_airline_brand_ar", "displayed_airline_brand_en", "source_iata_code",
            "carrier_role_classification", "total_displayed_records", "percentage_of_total",
            "arrival_records", "departure_records", "distinct_flight_numbers",
            "active_days_count", "daily_frequency_active_days", "daily_frequency_67_days",
            "is_operating_carrier_verified"
        ])
        for r in al_res["airlines"]:
            writer.writerow([
                r["displayed_airline_brand_ar"], r["displayed_airline_brand_en"], r["source_iata_code"],
                r["carrier_role_classification"], r["total_displayed_records"], r["percentage_of_total"],
                r["arrival_records"], r["departure_records"], r["distinct_flight_numbers"],
                r["active_days_count"], r["daily_frequency_active_days"], r["daily_frequency_67_days"],
                "FALSE"
            ])
    exported_files["airline_distribution_csv"] = path2

    # 3. reports/v2_15_route_analysis.csv
    rt_res = get_destination_and_route_analysis(top_limit=100)
    path3 = os.path.join(output_dir, "v2_15_route_analysis.csv")
    with open(path3, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "route_pair", "origin_iata", "destination_iata", "movement_type",
            "scheduled_records_count", "unique_displayed_flight_numbers",
            "distinct_airlines_count", "airlines_list"
        ])
        for r in rt_res["top_routes"]:
            writer.writerow([
                r["route_pair"], r["origin_iata"], r["destination_iata"], r["movement_type"],
                r["scheduled_records_count"], r["unique_displayed_flight_numbers"],
                r["distinct_airlines_count"], r["airlines_list"]
            ])
    exported_files["route_analysis_csv"] = path3

    # 4. reports/v2_15_hourly_distribution.csv
    hr_res = get_hourly_schedule_distribution()
    path4 = os.path.join(output_dir, "v2_15_hourly_distribution.csv")
    with open(path4, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "hour_local", "hour_label", "arrivals_count", "departures_count", "total_records_count", "wall_clock_timezone"
        ])
        for r in hr_res["hourly_distribution"]:
            writer.writerow([
                r["hour_local"], r["hour_label"], r["arrivals"], r["departures"], r["total"], "Asia/Damascus (UTC+3)"
            ])
    exported_files["hourly_distribution_csv"] = path4

    # 5. reports/v2_15_weekly_patterns.csv
    wk_res = get_weekly_and_daily_patterns()
    path5 = os.path.join(output_dir, "v2_15_weekly_patterns.csv")
    with open(path5, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "weekday_index", "weekday_name", "day_occurrences", "total_flights",
            "arrival_flights", "departure_flights", "average_flights_per_weekday"
        ])
        for r in wk_res["weekday_distribution"]:
            writer.writerow([
                r["weekday_index"], r["weekday_name"], r["day_occurrences"], r["total_flights"],
                r["arrival_flights"], r["departure_flights"], r["average_flights_per_weekday"]
            ])
    exported_files["weekly_patterns_csv"] = path5

    # 6. reports/v2_15_duplicate_candidates.csv
    dup_res = get_duplicate_candidates()
    path6 = os.path.join(output_dir, "v2_15_duplicate_candidates.csv")
    with open(path6, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "candidate_id", "group_type", "source_uuid_1", "flight_number_1", "airline_1",
            "source_uuid_2", "flight_number_2", "airline_2", "scheduled_date", "scheduled_time",
            "movement_type", "origin_iata", "destination_iata", "duplicate_classification",
            "review_status", "audit_finding"
        ])
        for r in dup_res["candidates"]:
            writer.writerow([
                r["candidate_id"], r["group_type"], r["source_uuid_1"], r["flight_number_1"], r["airline_1"],
                r["source_uuid_2"], r["flight_number_2"], r["airline_2"], r["scheduled_date"], r["scheduled_time"],
                r["movement_type"], r["origin_iata"], r["destination_iata"], r["duplicate_classification"],
                r["review_status"], r["audit_finding"]
            ])
    exported_files["duplicate_candidates_csv"] = path6

    # 7. reports/v2_15_analytics_summary.json
    summary_data = {
        "metadata": {
            "title": "Archived FIDS Analytics Layer Summary",
            "version": "2.15.0",
            "dataset_source": "Wayback Machine Snapshot of Damascus Airport FIDS API",
            "snapshot_id": SNAPSHOT_PROVENANCE["snapshot_id"],
            "memento_timestamp": SNAPSHOT_PROVENANCE["memento_timestamp"],
            "source_url": SNAPSHOT_PROVENANCE["source_url"],
            "date_coverage": "2026-07-05 to 2026-09-09 (67 consecutive days)",
            "wall_clock_timezone": "Asia/Damascus (UTC+3)",
            "semantic_warning": SEMANTIC_WARNING,
            "physical_movement_evidence_count": 0,
            "limitations": [
                "Represents scheduled timetable displays, not verified radar touchdowns.",
                "Airline names represent displayed passenger brands, not certified AOC operators.",
                "Single 'arrived' status is an unverified display board label without sensor proof.",
                "Candidate pair G9 376 / 376 preserved as a prefix-variant duplicate candidate."
            ]
        },
        "summary": get_fids_summary()["summary"],
        "period_patterns": wk_res["period_statistics"],
        "top_airlines": al_res["airlines"][:5],
        "top_routes": rt_res["top_routes"][:5],
        "busiest_days": wk_res["busiest_calendar_days"],
        "quietest_days": wk_res["quietest_calendar_days"],
        "busiest_weekdays": wk_res["busiest_weekdays"]
    }
    path7 = os.path.join(output_dir, "v2_15_analytics_summary.json")
    with open(path7, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    exported_files["analytics_summary_json"] = path7

    return exported_files

# =========================================================================
# FASTAPI ROUTER (NAMESPACE /api/archived-fids)
# =========================================================================
router = APIRouter(prefix="/api/archived-fids", tags=["Archived FIDS Analytics"])

@router.get("/summary")
def api_get_fids_summary(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    direction: Optional[str] = Query(None, description="arrival, departure, or all"),
    airline: Optional[str] = Query(None, description="Airline name or IATA code")
):
    try:
        return get_fids_summary(start_date=start_date, end_date=end_date, direction=direction, airline=airline)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/daily")
def api_get_fids_daily(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    direction: Optional[str] = Query(None, description="arrival, departure, or all"),
    airline: Optional[str] = Query(None, description="Airline name or IATA code")
):
    try:
        return get_daily_scheduled_flights(start_date=start_date, end_date=end_date, direction=direction, airline=airline)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/airlines")
def api_get_fids_airlines(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    direction: Optional[str] = Query(None, description="arrival, departure, or all")
):
    try:
        return get_displayed_airline_analysis(start_date=start_date, end_date=end_date, direction=direction)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/routes")
def api_get_fids_routes(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    direction: Optional[str] = Query(None, description="arrival, departure, or all"),
    airline: Optional[str] = Query(None, description="Airline name or IATA code"),
    limit: int = Query(20, ge=1, le=100, description="Max routes to return")
):
    try:
        return get_destination_and_route_analysis(start_date=start_date, end_date=end_date, direction=direction, airline=airline, top_limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/hourly")
def api_get_fids_hourly(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    direction: Optional[str] = Query(None, description="arrival, departure, or all"),
    airline: Optional[str] = Query(None, description="Airline name or IATA code")
):
    try:
        return get_hourly_schedule_distribution(start_date=start_date, end_date=end_date, direction=direction, airline=airline)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/weekly")
def api_get_fids_weekly(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    direction: Optional[str] = Query(None, description="arrival, departure, or all"),
    airline: Optional[str] = Query(None, description="Airline name or IATA code")
):
    try:
        return get_weekly_and_daily_patterns(start_date=start_date, end_date=end_date, direction=direction, airline=airline)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/duplicate-candidates")
def api_get_fids_duplicate_candidates():
    return get_duplicate_candidates()

@router.get("/coverage")
def api_get_fids_coverage():
    sum_res = get_fids_summary()
    return {
        "status": "success",
        "semantic_warning": SEMANTIC_WARNING,
        "provenance": SNAPSHOT_PROVENANCE,
        "date_coverage": {
            "start_date": "2026-07-05",
            "end_date": "2026-09-09",
            "consecutive_calendar_days": 67
        },
        "records_total": sum_res["summary"]["total_archived_fids_records"],
        "arrivals": sum_res["summary"]["scheduled_arrivals"],
        "departures": sum_res["summary"]["scheduled_departures"],
        "displayed_airline_brands": sum_res["summary"]["displayed_airline_brands_count"],
        "status_distribution": sum_res["summary"]["status_distribution"],
        "physical_movement_evidence_count": 0
    }

@router.get("/export/csv")
def api_export_fids_csv(
    dataset: str = Query("daily", description="Dataset: daily, airlines, routes, hourly, weekly, duplicates, or records"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    direction: Optional[str] = Query(None, description="arrival, departure, or all"),
    airline: Optional[str] = Query(None, description="Airline name or IATA code")
):
    try:
        validate_filters(start_date, end_date, direction, airline)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    dataset_clean = dataset.lower().strip()
    output = io.StringIO()
    writer = csv.writer(output)

    if dataset_clean == "daily":
        res = get_daily_scheduled_flights(start_date, end_date, direction, airline)
        writer.writerow([
            "flight_date", "total_scheduled_records", "arrival_records", "departure_records",
            "unique_displayed_flight_numbers", "unique_displayed_airline_brands",
            "scheduled_status_count", "other_display_status_count", "duplicate_candidates_count"
        ])
        for r in res["daily_records"]:
            writer.writerow([
                r["flight_date"], r["total_scheduled_records"], r["arrival_records"],
                r["departure_records"], r["unique_displayed_flight_numbers"],
                r["unique_displayed_airline_brands"], r["scheduled_status_count"],
                r["other_display_status_count"], r["duplicate_candidates_count"]
            ])

    elif dataset_clean in ("airlines", "airline"):
        res = get_displayed_airline_analysis(start_date, end_date, direction)
        writer.writerow([
            "displayed_airline_brand_ar", "displayed_airline_brand_en", "source_iata_code",
            "carrier_role_classification", "total_displayed_records", "percentage_of_total",
            "arrival_records", "departure_records", "distinct_flight_numbers",
            "active_days_count", "daily_frequency_active_days", "daily_frequency_67_days",
            "is_operating_carrier_verified"
        ])
        for r in res["airlines"]:
            writer.writerow([
                r["displayed_airline_brand_ar"], r["displayed_airline_brand_en"], r["source_iata_code"],
                r["carrier_role_classification"], r["total_displayed_records"], r["percentage_of_total"],
                r["arrival_records"], r["departure_records"], r["distinct_flight_numbers"],
                r["active_days_count"], r["daily_frequency_active_days"], r["daily_frequency_67_days"],
                "FALSE"
            ])

    elif dataset_clean in ("routes", "route"):
        res = get_destination_and_route_analysis(start_date, end_date, direction, airline, top_limit=100)
        writer.writerow([
            "route_pair", "origin_iata", "destination_iata", "movement_type",
            "scheduled_records_count", "unique_displayed_flight_numbers",
            "distinct_airlines_count", "airlines_list"
        ])
        for r in res["top_routes"]:
            writer.writerow([
                r["route_pair"], r["origin_iata"], r["destination_iata"], r["movement_type"],
                r["scheduled_records_count"], r["unique_displayed_flight_numbers"],
                r["distinct_airlines_count"], r["airlines_list"]
            ])

    elif dataset_clean in ("hourly", "hours"):
        res = get_hourly_schedule_distribution(start_date, end_date, direction, airline)
        writer.writerow([
            "hour_local", "hour_label", "arrivals_count", "departures_count", "total_records_count", "wall_clock_timezone"
        ])
        for r in res["hourly_distribution"]:
            writer.writerow([
                r["hour_local"], r["hour_label"], r["arrivals"], r["departures"], r["total"], "Asia/Damascus (UTC+3)"
            ])

    elif dataset_clean in ("weekly", "weekdays"):
        res = get_weekly_and_daily_patterns(start_date, end_date, direction, airline)
        writer.writerow([
            "weekday_index", "weekday_name", "day_occurrences", "total_flights",
            "arrival_flights", "departure_flights", "average_flights_per_weekday"
        ])
        for r in res["weekday_distribution"]:
            writer.writerow([
                r["weekday_index"], r["weekday_name"], r["day_occurrences"], r["total_flights"],
                r["arrival_flights"], r["departure_flights"], r["average_flights_per_weekday"]
            ])

    elif dataset_clean in ("duplicates", "duplicate_candidates"):
        res = get_duplicate_candidates()
        writer.writerow([
            "candidate_id", "group_type", "source_uuid_1", "flight_number_1", "airline_1",
            "source_uuid_2", "flight_number_2", "airline_2", "scheduled_date", "scheduled_time",
            "movement_type", "origin_iata", "destination_iata", "duplicate_classification",
            "review_status", "audit_finding"
        ])
        for r in res["candidates"]:
            writer.writerow([
                r["candidate_id"], r["group_type"], r["source_uuid_1"], r["flight_number_1"], r["airline_1"],
                r["source_uuid_2"], r["flight_number_2"], r["airline_2"], r["scheduled_date"], r["scheduled_time"],
                r["movement_type"], r["origin_iata"], r["destination_iata"], r["duplicate_classification"],
                r["review_status"], r["audit_finding"]
            ])

    elif dataset_clean in ("records", "raw", "all"):
        where_sql, params = validate_filters(start_date, end_date, direction, airline)
        conn = get_analytics_connection()
        cur = conn.cursor()
        cur.execute(f"""
        SELECT
            record_id, source_uuid, flight_number, airline_name_ar, airline_name_en,
            airline_iata, airline_role, movement_type, origin_iata, destination_iata,
            scheduled_date, scheduled_time, scheduled_datetime_local, scheduled_datetime_utc,
            scheduled_status, displayed_status, actual_movement_evidence, classification
        FROM fids_analytics_records
        WHERE {where_sql}
        ORDER BY scheduled_date, scheduled_time, flight_number
        """, params)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        if rows:
            writer.writerow(list(rows[0].keys()))
            for r in rows:
                writer.writerow(list(r.values()))
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown dataset '{dataset}'. Valid options: daily, airlines, routes, hourly, weekly, duplicates, records."
        )

    content = output.getvalue()
    filename = f"archived_fids_{dataset_clean}.csv"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/export/json")
def api_export_fids_json(
    dataset: str = Query("summary", description="Dataset: summary, daily, airlines, routes, hourly, weekly, duplicates, or records"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    direction: Optional[str] = Query(None, description="arrival, departure, or all"),
    airline: Optional[str] = Query(None, description="Airline name or IATA code")
):
    try:
        validate_filters(start_date, end_date, direction, airline)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    dataset_clean = dataset.lower().strip()
    if dataset_clean == "summary":
        return get_fids_summary(start_date, end_date, direction, airline)
    elif dataset_clean == "daily":
        return get_daily_scheduled_flights(start_date, end_date, direction, airline)
    elif dataset_clean in ("airlines", "airline"):
        return get_displayed_airline_analysis(start_date, end_date, direction)
    elif dataset_clean in ("routes", "route"):
        return get_destination_and_route_analysis(start_date, end_date, direction, airline)
    elif dataset_clean in ("hourly", "hours"):
        return get_hourly_schedule_distribution(start_date, end_date, direction, airline)
    elif dataset_clean in ("weekly", "weekdays"):
        return get_weekly_and_daily_patterns(start_date, end_date, direction, airline)
    elif dataset_clean in ("duplicates", "duplicate_candidates"):
        return get_duplicate_candidates()
    elif dataset_clean in ("records", "all"):
        where_sql, params = validate_filters(start_date, end_date, direction, airline)
        conn = get_analytics_connection()
        cur = conn.cursor()
        cur.execute(f"""
        SELECT * FROM fids_analytics_records
        WHERE {where_sql}
        ORDER BY scheduled_date, scheduled_time, flight_number
        """, params)
        records = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {
            "status": "success",
            "semantic_warning": SEMANTIC_WARNING,
            "provenance": SNAPSHOT_PROVENANCE,
            "total_records": len(records),
            "records": records
        }
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown dataset '{dataset}'. Valid options: summary, daily, airlines, routes, hourly, weekly, duplicates, records."
        )

if __name__ == "__main__":
    print("Building analytics database...")
    db_path = build_analytics_database(rebuild=True)
    print(f"Analytics DB built at: {db_path}")
    print("Exporting reports...")
    files = export_archived_fids_reports()
    for k, v in files.items():
        print(f"  {k}: {v}")
