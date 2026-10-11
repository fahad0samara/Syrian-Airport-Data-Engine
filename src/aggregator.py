import json
import sqlite3
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any
from pathlib import Path
import pandas as pd
from src.config import (
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    REPORTS_DIR,
    DB_PATH,
    SYRIAN_AIRPORTS_REGISTRY,
)
from src.database import get_connection
from src.normalizer import get_timestamp_priority, determine_evidence_source, evaluate_cross_source_match

def aggregate_daily_airport_movements(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Computes daily arrival and departure movement metrics for each Syrian airport independently.
    Never fills missing dates with zeros.
    Clearly separates completed physical movements (landed/active) from scheduled flights.
    """
    if not events:
        return []

    df = pd.DataFrame(events)
    df = df[df["flight_date"].notnull() & (df["flight_date"] != "")]

    daily_records = []
    grouped = df.groupby(["airport_id", "flight_date"])

    for (airport_id, date_str), group in grouped:
        arr_df = group[group["movement_type"] == "arrival"]
        dep_df = group[group["movement_type"] == "departure"]

        arr_count = len(arr_df)
        dep_count = len(dep_df)

        landed_count = int((group["flight_status"] == "landed").sum())
        departed_count = int((group["flight_status"] == "departed").sum())
        cancelled_count = int((group["flight_status"] == "cancelled").sum())
        diverted_count = int((group["flight_status"] == "diverted").sum())
        scheduled_count = int((group["flight_status"] == "scheduled").sum())
        active_count = int((group["flight_status"] == "active").sum())

        completed_movements = landed_count + departed_count
        scheduled_movements = scheduled_count

        if arr_count > 0 and dep_count > 0:
            total_movements = arr_count + dep_count
            coverage_status = "observed"
        elif arr_count > 0:
            total_movements = arr_count
            coverage_status = "incomplete"
        elif dep_count > 0:
            total_movements = dep_count
            coverage_status = "incomplete"
        else:
            continue

        domestic_count = int((group["route_type"] == "domestic").sum())
        international_count = int((group["route_type"] == "international").sum())

        aircraft_ids = set()
        for _, row in group.iterrows():
            reg = row.get("aircraft_registration")
            hex_id = row.get("aircraft_icao24")
            if reg and str(reg).strip():
                aircraft_ids.add(str(reg).strip().upper())
            elif hex_id and str(hex_id).strip():
                aircraft_ids.add(str(hex_id).strip().upper())

        airlines = set()
        for _, row in group.iterrows():
            al = row.get("airline_name") or row.get("airline_iata") or row.get("airline_icao")
            if al and str(al).strip():
                airlines.add(str(al).strip())

        daily_records.append({
            "airport_id": airport_id,
            "flight_date": date_str,
            "arrival_count": arr_count,
            "departure_count": dep_count,
            "completed_movements": completed_movements,
            "scheduled_movements": scheduled_movements,
            "total_movements": total_movements,
            "landed_count": landed_count,
            "departed_count": departed_count,
            "cancelled_count": cancelled_count,
            "diverted_count": diverted_count,
            "scheduled_count": scheduled_count,
            "active_count": active_count,
            "domestic_count": domestic_count,
            "international_count": international_count,
            "unique_aircraft_count": len(aircraft_ids),
            "unique_airlines_count": len(airlines),
            "passengers": None,  # Strictly null: no speculative capacity guessing
            "cargo": None,       # Strictly null: no speculative capacity guessing
            "source_id": "unified_events_aggregator",
            "observed_or_derived": "derived_from_flight_events",
            "coverage_status": coverage_status,
            "quality_flags": "independently_computed_per_airport",
            "methodology_version": "2.0",
        })

    daily_records.sort(key=lambda x: (x["airport_id"], x["flight_date"]))
    return daily_records

def aggregate_damascus_daily_movements(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Backward-compatible Damascus deep-dive movements aggregator.
    Filters specifically for airport_id == 'DAM'.
    """
    dam_events = [e for e in events if e.get("airport_id") == "DAM"]
    all_daily = aggregate_daily_airport_movements(dam_events)
    # Format for damascus_daily_movements table
    dam_daily = []
    for r in all_daily:
        dam_daily.append({
            "flight_date": r["flight_date"],
            "arrival_count": r["arrival_count"],
            "departure_count": r["departure_count"],
            "completed_movements": r["completed_movements"],
            "scheduled_movements": r["scheduled_movements"],
            "total_movements": r["total_movements"],
            "landed_count": r["landed_count"],
            "departed_count": r["departed_count"],
            "cancelled_count": r["cancelled_count"],
            "diverted_count": r["diverted_count"],
            "scheduled_count": r["scheduled_count"],
            "active_count": r["active_count"],
            "domestic_count": r["domestic_count"],
            "international_count": r["international_count"],
            "unique_aircraft_count": r["unique_aircraft_count"],
            "unique_airlines_count": r["unique_airlines_count"],
            "completeness_status": "complete_verified" if r["coverage_status"] == "observed" else "incomplete",
        })
    return dam_daily

def load_historical_sem_series() -> List[Dict[str, Any]]:
    """
    Loads historical daily operations from the Syria Economic Monitor (World Bank / Data Partnership).
    CRITICAL DISTINCTION: Scope is explicitly DAM_ALP_LTK (combined Syrian gateways).
    Missing dates are preserved as gaps (never zero-filled).
    """
    records = []
    dep_file = RAW_DATA_DIR / "daily_departures_from_dam__alp_and_ltk.json"
    arr_file = RAW_DATA_DIR / "daily_arrivals_to_dam__alp_and_ltk.json"

    if dep_file.exists():
        with open(dep_file, "r", encoding="utf-8") as f:
            dep_data = json.load(f)
            for item in dep_data:
                total_ops = (
                    item.get("active", 0) +
                    item.get("cancelled", 0) +
                    item.get("diverted", 0) +
                    item.get("landed", 0) +
                    item.get("scheduled", 0) +
                    item.get("unknown", 0)
                )
                date_iso = item.get("flight_date_iso")
                if not date_iso and isinstance(item.get("flight_date"), (int, float)):
                    date_iso = datetime.fromtimestamp(item["flight_date"] / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")

                records.append({
                    "flight_date": date_iso or str(item.get("flight_date")),
                    "movement_type": "departure",
                    "scope": "DAM_ALP_LTK",
                    "active": item.get("active", 0),
                    "cancelled": item.get("cancelled", 0),
                    "diverted": item.get("diverted", 0),
                    "landed": item.get("landed", 0),
                    "scheduled": item.get("scheduled", 0),
                    "unknown": item.get("unknown", 0),
                    "total_recorded_operations": total_ops,
                    "data_source": "Syria Economic Monitor (AviationStack purchase, DAM_ALP_LTK)",
                    "coverage_status": "unverified_data_gap" if total_ops == 0 else "observed",
                    "status_note": (
                        "Unverified data gap in source series: 0 recorded operations across all status categories"
                        if total_ops == 0
                        else "Aggregated gateway departure operations across Syria (Damascus, Aleppo, Latakia)"
                    ),
                })

    if arr_file.exists():
        with open(arr_file, "r", encoding="utf-8") as f:
            arr_data = json.load(f)
            for item in arr_data:
                total_ops = (
                    item.get("active", 0) +
                    item.get("cancelled", 0) +
                    item.get("diverted", 0) +
                    item.get("landed", 0) +
                    item.get("scheduled", 0) +
                    item.get("unknown", 0)
                )
                date_iso = item.get("flight_date_iso")
                if not date_iso and isinstance(item.get("flight_date"), (int, float)):
                    date_iso = datetime.fromtimestamp(item["flight_date"] / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")

                records.append({
                    "flight_date": date_iso or str(item.get("flight_date")),
                    "movement_type": "arrival",
                    "scope": "DAM_ALP_LTK",
                    "active": item.get("active", 0),
                    "cancelled": item.get("cancelled", 0),
                    "diverted": item.get("diverted", 0),
                    "landed": item.get("landed", 0),
                    "scheduled": item.get("scheduled", 0),
                    "unknown": item.get("unknown", 0),
                    "total_recorded_operations": total_ops,
                    "data_source": "Syria Economic Monitor (AviationStack purchase, DAM_ALP_LTK)",
                    "coverage_status": "unverified_data_gap" if total_ops == 0 else "observed",
                    "status_note": (
                        "Unverified data gap in source series: 0 recorded operations across all status categories"
                        if total_ops == 0
                        else "Aggregated gateway arrival operations across Syria (Damascus, Aleppo, Latakia)"
                    ),
                })

    records.sort(key=lambda x: (x["flight_date"], x["movement_type"]))
    return records

def record_raw_source_records(conn: sqlite3.Connection):
    """
    Ingests metadata and hashes for all raw files in data/raw into raw_source_records table.
    """
    cursor = conn.cursor()
    cursor.execute("DELETE FROM raw_source_records;")
    raw_files = list(RAW_DATA_DIR.glob("*.json"))

    for rf in raw_files:
        try:
            with open(rf, "r", encoding="utf-8") as f:
                content = f.read()
            p_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            fname = rf.name

            # Determine airport and source
            if "damairport" in fname or "_dam_" in fname:
                apt = "DAM"
            elif "alpairport" in fname or "_alp_" in fname:
                apt = "ALP"
            elif "qamishli" in fname or "_kac_" in fname:
                apt = "KAC"
            elif "deir" in fname or "_dez_" in fname:
                apt = "DEZ"
            elif "_ltk_" in fname:
                apt = "LTK"
            else:
                apt = None

            source_id = fname.replace(".json", "")
            raw_rec_id = f"raw_{fname}_{p_hash[:12]}"
            retrieved_at = datetime.fromtimestamp(rf.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
            INSERT OR REPLACE INTO raw_source_records (
                raw_record_id, source_id, airport_id, retrieved_at_utc,
                query_parameters, source_record_id, raw_payload, payload_hash,
                source_url, http_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                raw_rec_id,
                source_id,
                apt,
                retrieved_at,
                f"file={fname}",
                fname,
                content, # Full raw payload preserved for exact audit hash
                p_hash,
                f"local://data/raw/{fname}",
                200
            ))
        except Exception:
            pass
    conn.commit()

def reconcile_monotonic_events(
    incoming_events: List[Dict[str, Any]],
    existing_events: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Reconciles newly normalized incoming flight events against existing database records
    according to the Monotonic Evidence Policy:
    1. Monotonic Evidence Retention: A confirmed physical movement retains its physical telemetry
       (actual touchdown/takeoff time, tail registration, icao24 hex) and 'physical_movement' classification
       even if it drops off a rolling 24-hour feed (e.g. Flightradar24 sliding window).
    2. Explicit Retraction Handling: If an incoming record explicitly indicates cancellation,
       diversion, or source retraction, the status is updated with quality_flags='source_retraction_applied'.
    3. Invariance / Anti-Fabrication: An unsupported scheduled flight is NEVER promoted to physical_movement.
    4. Non-Destructive Retention: Historical events in the database that are outside the incoming feed's
       window are preserved rather than dropped.
    """
    if not existing_events:
        res = [dict(c) for c in incoming_events]
        res.sort(key=lambda x: (
            str(x.get("airport_id") or ""),
            str(x.get("flight_date") or ""),
            str(x.get("movement_type") or ""),
            str(x.get("flight_number") or "")
        ))
        return res

    existing_by_id: Dict[str, Dict[str, Any]] = {}
    existing_by_key: Dict[tuple, List[Dict[str, Any]]] = {}
    for r in existing_events:
        eid = r.get("event_id")
        if eid:
            existing_by_id[eid] = r
        key = (
            str(r.get("airport_id") or "").upper().strip(),
            str(r.get("movement_type") or "").lower().strip(),
            str(r.get("flight_number") or "").upper().strip().replace(" ", ""),
            str(r.get("flight_date") or "").strip()
        )
        existing_by_key.setdefault(key, []).append(r)

    reconciled: List[Dict[str, Any]] = []
    matched_existing_ids = set()

    for cand in incoming_events:
        c = dict(cand)
        eid = c.get("event_id")
        key = (
            str(c.get("airport_id") or "").upper().strip(),
            str(c.get("movement_type") or "").lower().strip(),
            str(c.get("flight_number") or "").upper().strip().replace(" ", ""),
            str(c.get("flight_date") or "").strip()
        )

        prev = None
        if eid in existing_by_id:
            prev = existing_by_id[eid]
        else:
            candidates = existing_by_key.get(key, [])
            for existing_cand in candidates:
                match_res = evaluate_cross_source_match(existing_cand, c)
                if match_res["can_merge"]:
                    prev = existing_cand
                    break

        if prev:
            prev_id = prev.get("event_id")
            if prev_id:
                matched_existing_ids.add(prev_id)
                # CRITICAL: Preserve stable canonical event ID from existing database
                c["event_id"] = prev_id

            cand_status = str(c.get("flight_status") or "").lower()
            prev_status = str(prev.get("flight_status") or "").lower()

            # 1. Operational Status Update: Cancellations and Diversions
            if cand_status in ("cancelled", "diverted") and prev_status not in ("cancelled", "diverted"):
                c["flight_status"] = cand_status
                c["quality_flags"] = "source_retraction_applied"

            # 2. Monotonic Evidence Retention: If previous record had confirmed physical movement, retain evidence
            if prev.get("record_nature") == "physical_movement":
                c["record_nature"] = "physical_movement"
                if cand_status not in ("cancelled", "diverted"):
                    c["quality_flags"] = "retained_verified_evidence_monotonic"

                prev_src = prev.get("source") or ""
                cand_src = c.get("source") or ""

                prev_arr_prio = get_timestamp_priority(prev_src, bool(prev.get("actual_arr_time")))
                cand_arr_prio = get_timestamp_priority(cand_src, bool(c.get("actual_arr_time")))
                if prev.get("actual_arr_time") and (not c.get("actual_arr_time") or prev_arr_prio > cand_arr_prio):
                    c["actual_arr_time"] = prev["actual_arr_time"]
                    c["raw_actual_arr_time"] = prev.get("raw_actual_arr_time")

                prev_dep_prio = get_timestamp_priority(prev_src, bool(prev.get("actual_dep_time")))
                cand_dep_prio = get_timestamp_priority(cand_src, bool(c.get("actual_dep_time")))
                if prev.get("actual_dep_time") and (not c.get("actual_dep_time") or prev_dep_prio > cand_dep_prio):
                    c["actual_dep_time"] = prev["actual_dep_time"]
                    c["raw_actual_dep_time"] = prev.get("raw_actual_dep_time")

                if prev.get("estimated_arr_time") and not c.get("estimated_arr_time"):
                    c["estimated_arr_time"] = prev["estimated_arr_time"]
                    c["raw_estimated_arr_time"] = prev.get("raw_estimated_arr_time")

                if prev.get("estimated_dep_time") and not c.get("estimated_dep_time"):
                    c["estimated_dep_time"] = prev["estimated_dep_time"]
                    c["raw_estimated_dep_time"] = prev.get("raw_estimated_dep_time")

                if prev.get("aircraft_registration") and not c.get("aircraft_registration"):
                    c["aircraft_registration"] = prev["aircraft_registration"]
                if prev.get("aircraft_icao24") and not c.get("aircraft_icao24"):
                    c["aircraft_icao24"] = prev["aircraft_icao24"]
                if prev.get("aircraft_model") and not c.get("aircraft_model"):
                    c["aircraft_model"] = prev["aircraft_model"]

                if prev_src and cand_src:
                    merged_srcs = list(dict.fromkeys(s for s in (cand_src.split("+") + prev_src.split("+")) if s))
                    c["source"] = "+".join(merged_srcs)
                elif prev_src:
                    c["source"] = prev_src

                if prev_status in ("landed", "departed") and cand_status in ("scheduled", "active", "unknown"):
                    c["flight_status"] = prev_status
            elif cand_status not in ("cancelled", "diverted"):
                # 3. Anti-Fabrication Invariance
                if c.get("record_nature") == "physical_movement" and not (
                    c.get("actual_arr_time") or c.get("actual_dep_time") or c.get("aircraft_registration")
                ):
                    c["record_nature"] = prev.get("record_nature", "scheduled_service")

            # 4. Preserve rich raw_json payload from previous snapshot if candidate has empty JSON
            if prev.get("raw_json") and (not c.get("raw_json") or str(c.get("raw_json")).strip() in ("", "{}")):
                c["raw_json"] = prev["raw_json"]

        reconciled.append(c)

    # 4. Non-Destructive Retention: Preserve historical records not in current feed
    for prev_id, prev_rec in existing_by_id.items():
        if prev_id not in matched_existing_ids:
            reconciled.append(dict(prev_rec))

    reconciled.sort(key=lambda x: (
        str(x.get("airport_id") or ""),
        str(x.get("flight_date") or ""),
        str(x.get("movement_type") or ""),
        str(x.get("flight_number") or "")
    ))
    return reconciled

def persist_all_to_database_and_exports(
    events: List[Dict[str, Any]],
    dam_daily_movements: List[Dict[str, Any]],
    all_daily_movements: List[Dict[str, Any]],
    hist_records: List[Dict[str, Any]],
    audit_log: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Persists flight events, airport movements, multi-airport time series, and deduplication audit
    to SQLite and exports CSV/JSON files.
    """
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        cursor = conn.cursor()

        # Load existing flight events for monotonic reconciliation
        cursor.execute("SELECT * FROM flight_events;")
        col_names = [d[0] for d in cursor.description]
        existing_rows = [dict(zip(col_names, row)) for row in cursor.fetchall()]

        # Reconcile incoming events with existing database records
        events = reconcile_monotonic_events(events, existing_rows)

        # Recompute daily movement aggregates to ensure perfect synchronization
        all_daily_movements = aggregate_daily_airport_movements(events)
        dam_daily_movements = aggregate_damascus_daily_movements(events)

        # 1. Flight Events Non-Destructive UPSERT
        upsert_flight_events_sql = """
        INSERT INTO flight_events (
            event_id, airport_id, source, source_record_id, movement_type,
            airport_iata, airport_icao, connected_airport_iata,
            connected_airport_icao, connected_airport_name, connected_country,
            connected_city, route_type, airline_name, airline_iata,
            airline_icao, flight_number, flight_date, local_operational_date,
            flight_status, scheduled_dep_time, estimated_dep_time, actual_dep_time,
            scheduled_arr_time, estimated_arr_time, actual_arr_time, raw_scheduled_dep_time,
            raw_estimated_dep_time, raw_actual_dep_time, raw_scheduled_arr_time, raw_estimated_arr_time, raw_actual_arr_time,
            aircraft_model, aircraft_registration, aircraft_icao24,
            record_nature, operating_flight_number, operating_carrier,
            observed_or_derived, quality_flags, normalization_version, raw_json
        ) VALUES (
            :event_id, :airport_id, :source, :source_record_id, :movement_type,
            :airport_iata, :airport_icao, :connected_airport_iata,
            :connected_airport_icao, :connected_airport_name, :connected_country,
            :connected_city, :route_type, :airline_name, :airline_iata,
            :airline_icao, :flight_number, :flight_date, :local_operational_date,
            :flight_status, :scheduled_dep_time, :estimated_dep_time, :actual_dep_time,
            :scheduled_arr_time, :estimated_arr_time, :actual_arr_time, :raw_scheduled_dep_time,
            :raw_estimated_dep_time, :raw_actual_dep_time, :raw_scheduled_arr_time, :raw_estimated_arr_time, :raw_actual_arr_time,
            :aircraft_model, :aircraft_registration, :aircraft_icao24,
            :record_nature, :operating_flight_number, :operating_carrier,
            :observed_or_derived, :quality_flags, :normalization_version, :raw_json
        )
        ON CONFLICT(event_id) DO UPDATE SET
            airport_id = excluded.airport_id,
            source = CASE
                WHEN flight_events.source LIKE '%flightradar24%' AND excluded.source NOT LIKE '%flightradar24%'
                THEN excluded.source || '+flightradar24'
                ELSE excluded.source
            END,
            source_record_id = COALESCE(excluded.source_record_id, flight_events.source_record_id),
            movement_type = excluded.movement_type,
            airport_iata = COALESCE(excluded.airport_iata, flight_events.airport_iata),
            airport_icao = COALESCE(excluded.airport_icao, flight_events.airport_icao),
            connected_airport_iata = COALESCE(excluded.connected_airport_iata, flight_events.connected_airport_iata),
            connected_airport_icao = COALESCE(excluded.connected_airport_icao, flight_events.connected_airport_icao),
            connected_airport_name = COALESCE(excluded.connected_airport_name, flight_events.connected_airport_name),
            connected_country = COALESCE(excluded.connected_country, flight_events.connected_country),
            connected_city = COALESCE(excluded.connected_city, flight_events.connected_city),
            route_type = COALESCE(excluded.route_type, flight_events.route_type),
            airline_name = COALESCE(excluded.airline_name, flight_events.airline_name),
            airline_iata = COALESCE(excluded.airline_iata, flight_events.airline_iata),
            airline_icao = COALESCE(excluded.airline_icao, flight_events.airline_icao),
            flight_number = excluded.flight_number,
            flight_date = excluded.flight_date,
            local_operational_date = COALESCE(excluded.local_operational_date, flight_events.local_operational_date),
            flight_status = CASE
                WHEN excluded.flight_status IN ('cancelled', 'diverted') THEN excluded.flight_status
                WHEN flight_events.flight_status IN ('landed', 'departed') AND excluded.flight_status IN ('scheduled', 'active', 'unknown') THEN flight_events.flight_status
                ELSE excluded.flight_status
            END,
            scheduled_dep_time = COALESCE(excluded.scheduled_dep_time, flight_events.scheduled_dep_time),
            estimated_dep_time = COALESCE(excluded.estimated_dep_time, flight_events.estimated_dep_time),
            actual_dep_time = CASE
                WHEN flight_events.source LIKE '%flightradar24%' AND excluded.source NOT LIKE '%flightradar24%' AND flight_events.actual_dep_time IS NOT NULL
                THEN flight_events.actual_dep_time
                ELSE COALESCE(excluded.actual_dep_time, flight_events.actual_dep_time)
            END,
            scheduled_arr_time = COALESCE(excluded.scheduled_arr_time, flight_events.scheduled_arr_time),
            estimated_arr_time = COALESCE(excluded.estimated_arr_time, flight_events.estimated_arr_time),
            actual_arr_time = CASE
                WHEN flight_events.source LIKE '%flightradar24%' AND excluded.source NOT LIKE '%flightradar24%' AND flight_events.actual_arr_time IS NOT NULL
                THEN flight_events.actual_arr_time
                ELSE COALESCE(excluded.actual_arr_time, flight_events.actual_arr_time)
            END,
            raw_scheduled_dep_time = COALESCE(excluded.raw_scheduled_dep_time, flight_events.raw_scheduled_dep_time),
            raw_estimated_dep_time = COALESCE(excluded.raw_estimated_dep_time, flight_events.raw_estimated_dep_time),
            raw_actual_dep_time = CASE
                WHEN flight_events.source LIKE '%flightradar24%' AND excluded.source NOT LIKE '%flightradar24%' AND flight_events.raw_actual_dep_time IS NOT NULL
                THEN flight_events.raw_actual_dep_time
                ELSE COALESCE(excluded.raw_actual_dep_time, flight_events.raw_actual_dep_time)
            END,
            raw_scheduled_arr_time = COALESCE(excluded.raw_scheduled_arr_time, flight_events.raw_scheduled_arr_time),
            raw_estimated_arr_time = COALESCE(excluded.raw_estimated_arr_time, flight_events.raw_estimated_arr_time),
            raw_actual_arr_time = CASE
                WHEN flight_events.source LIKE '%flightradar24%' AND excluded.source NOT LIKE '%flightradar24%' AND flight_events.raw_actual_arr_time IS NOT NULL
                THEN flight_events.raw_actual_arr_time
                ELSE COALESCE(excluded.raw_actual_arr_time, flight_events.raw_actual_arr_time)
            END,
            aircraft_model = COALESCE(excluded.aircraft_model, flight_events.aircraft_model),
            aircraft_registration = COALESCE(excluded.aircraft_registration, flight_events.aircraft_registration),
            aircraft_icao24 = COALESCE(excluded.aircraft_icao24, flight_events.aircraft_icao24),
            record_nature = CASE
                WHEN flight_events.record_nature = 'physical_movement' AND (flight_events.actual_dep_time IS NOT NULL OR flight_events.actual_arr_time IS NOT NULL)
                THEN 'physical_movement'
                WHEN excluded.flight_status IN ('cancelled', 'diverted') THEN excluded.record_nature
                WHEN flight_events.record_nature = 'physical_movement' AND excluded.record_nature != 'physical_movement'
                THEN 'physical_movement'
                ELSE excluded.record_nature
            END,
            operating_flight_number = COALESCE(excluded.operating_flight_number, flight_events.operating_flight_number),
            operating_carrier = COALESCE(excluded.operating_carrier, flight_events.operating_carrier),
            observed_or_derived = excluded.observed_or_derived,
            quality_flags = CASE
                WHEN excluded.flight_status IN ('cancelled', 'diverted') THEN excluded.quality_flags
                WHEN flight_events.record_nature = 'physical_movement' AND excluded.record_nature != 'physical_movement'
                THEN 'retained_verified_evidence_monotonic'
                ELSE excluded.quality_flags
            END,
            raw_json = CASE
                WHEN excluded.raw_json IS NOT NULL AND excluded.raw_json != '' AND excluded.raw_json != '{}'
                THEN excluded.raw_json
                ELSE flight_events.raw_json
            END;
        """
        for e in events:
            rec = {
                "estimated_dep_time": None,
                "estimated_arr_time": None,
                "raw_estimated_dep_time": None,
                "raw_estimated_arr_time": None,
                **e
            }
            cursor.execute(upsert_flight_events_sql, rec)

        # 1b. Immutable Event Evidence Ledger (Append-Only)
        evidence_insert_sql = """
        INSERT OR IGNORE INTO event_evidence (
            evidence_id, event_id, source_name, source_record_id, evidence_type,
            observed_value, raw_timestamp, snapshot_path, snapshot_sha256
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        for e in events:
            eid = e["event_id"]
            src = e.get("source") or "unknown"
            srec = e.get("source_record_id")

            if e.get("actual_arr_time"):
                raw_ts = e.get("raw_actual_arr_time")
                disc_src = determine_evidence_source(src, raw_ts)
                etype = "adsb_touchdown" if disc_src == "flightradar24" else "commercial_touchdown"
                val = str(e["actual_arr_time"])
                ev_id = "ev_" + hashlib.sha256(f"{eid}|{disc_src}|{etype}|{val}".encode("utf-8")).hexdigest()[:16]
                cursor.execute(evidence_insert_sql, (ev_id, eid, disc_src, srec, etype, val, raw_ts, None, None))

            if e.get("actual_dep_time"):
                raw_ts = e.get("raw_actual_dep_time")
                disc_src = determine_evidence_source(src, raw_ts)
                etype = "adsb_takeoff" if disc_src == "flightradar24" else "commercial_takeoff"
                val = str(e["actual_dep_time"])
                ev_id = "ev_" + hashlib.sha256(f"{eid}|{disc_src}|{etype}|{val}".encode("utf-8")).hexdigest()[:16]
                cursor.execute(evidence_insert_sql, (ev_id, eid, disc_src, srec, etype, val, raw_ts, None, None))

            if e.get("estimated_arr_time"):
                raw_ts = e.get("raw_estimated_arr_time")
                disc_src = determine_evidence_source(src, raw_ts)
                etype = "estimated_arrival"
                val = str(e["estimated_arr_time"])
                ev_id = "ev_" + hashlib.sha256(f"{eid}|{disc_src}|{etype}|{val}".encode("utf-8")).hexdigest()[:16]
                cursor.execute(evidence_insert_sql, (ev_id, eid, disc_src, srec, etype, val, raw_ts, None, None))

            if e.get("estimated_dep_time"):
                raw_ts = e.get("raw_estimated_dep_time")
                disc_src = determine_evidence_source(src, raw_ts)
                etype = "estimated_departure"
                val = str(e["estimated_dep_time"])
                ev_id = "ev_" + hashlib.sha256(f"{eid}|{disc_src}|{etype}|{val}".encode("utf-8")).hexdigest()[:16]
                cursor.execute(evidence_insert_sql, (ev_id, eid, disc_src, srec, etype, val, raw_ts, None, None))

            if e.get("aircraft_registration"):
                disc_src = "flightradar24" if "flightradar24" in src else ("aviationstack" if "aviationstack" in src else src.split("+")[0])
                val = str(e["aircraft_registration"]).strip().upper()
                ev_id = "ev_" + hashlib.sha256(f"{eid}|{disc_src}|aircraft_registration|{val}".encode("utf-8")).hexdigest()[:16]
                cursor.execute(evidence_insert_sql, (ev_id, eid, disc_src, srec, "aircraft_registration", val, None, None, None))

            if e.get("aircraft_icao24"):
                disc_src = "flightradar24" if "flightradar24" in src else ("aviationstack" if "aviationstack" in src else src.split("+")[0])
                val = str(e["aircraft_icao24"]).strip().upper()
                ev_id = "ev_" + hashlib.sha256(f"{eid}|{disc_src}|aircraft_icao24|{val}".encode("utf-8")).hexdigest()[:16]
                cursor.execute(evidence_insert_sql, (ev_id, eid, disc_src, srec, "aircraft_icao24", val, None, None, None))

        # 2. Daily Airport Movements (All Syrian Airports)
        cursor.execute("DELETE FROM daily_airport_movements;")
        for r in all_daily_movements:
            cursor.execute("""
            INSERT INTO daily_airport_movements (
                airport_id, flight_date, arrival_count, departure_count,
                completed_movements, scheduled_movements, total_movements,
                landed_count, departed_count, cancelled_count, diverted_count, scheduled_count,
                active_count, domestic_count, international_count,
                unique_aircraft_count, unique_airlines_count, passengers, cargo,
                source_id, observed_or_derived, coverage_status, quality_flags,
                methodology_version
            ) VALUES (
                :airport_id, :flight_date, :arrival_count, :departure_count,
                :completed_movements, :scheduled_movements, :total_movements,
                :landed_count, :departed_count, :cancelled_count, :diverted_count, :scheduled_count,
                :active_count, :domestic_count, :international_count,
                :unique_aircraft_count, :unique_airlines_count, :passengers, :cargo,
                :source_id, :observed_or_derived, :coverage_status, :quality_flags,
                :methodology_version
            )
            """, r)

        # 3. Damascus Daily Movements (Backward-compatible Table)
        cursor.execute("DELETE FROM damascus_daily_movements;")
        for r in dam_daily_movements:
            cursor.execute("""
            INSERT INTO damascus_daily_movements (
                flight_date, arrival_count, departure_count, completed_movements,
                scheduled_movements, total_movements, landed_count, departed_count, cancelled_count,
                diverted_count, scheduled_count, active_count, domestic_count,
                international_count, unique_aircraft_count, unique_airlines_count,
                completeness_status
            ) VALUES (
                :flight_date, :arrival_count, :departure_count, :completed_movements,
                :scheduled_movements, :total_movements, :landed_count, :departed_count, :cancelled_count,
                :diverted_count, :scheduled_count, :active_count, :domestic_count,
                :international_count, :unique_aircraft_count, :unique_airlines_count,
                :completeness_status
            )
            """, r)

        # 4. Multi-Airport 2024 Series (Syrian Gateways DAM_ALP_LTK)
        cursor.execute("DELETE FROM historical_daily_movements_2024;")
        for h in hist_records:
            cursor.execute("""
            INSERT INTO historical_daily_movements_2024 (
                flight_date, movement_type, scope, active, cancelled, diverted,
                landed, scheduled, unknown, total_recorded_operations,
                data_source, coverage_status, status_note
            ) VALUES (
                :flight_date, :movement_type, :scope, :active, :cancelled, :diverted,
                :landed, :scheduled, :unknown, :total_recorded_operations,
                :data_source, :coverage_status, :status_note
            )
            """, h)

        # 5. Deduplication Audit Trail
        cursor.execute("DELETE FROM deduplication_audit;")
        for a in audit_log:
            cursor.execute("""
            INSERT INTO deduplication_audit (
                canonical_event_id, airport_id, flight_number, movement_type,
                flight_date, source_a, source_a_record_id, source_a_raw_time,
                source_b, source_b_record_id, source_b_raw_time,
                time_difference_minutes, matching_rule, resolution_status
            ) VALUES (
                :canonical_event_id, :airport_id, :flight_number, :movement_type,
                :flight_date, :source_a, :source_a_record_id, :source_a_raw_time,
                :source_b, :source_b_record_id, :source_b_raw_time,
                :time_difference_minutes, :matching_rule, :resolution_status
            )
            """, a)

        # 6. Record raw sources
        record_raw_source_records(conn)

        conn.commit()

    # Generate CSV & JSON Exports
    # A. All Syrian Flight Events
    df_events = pd.DataFrame(events)
    df_events_clean = df_events.drop(columns=["raw_json"], errors="ignore")
    df_events_clean.to_csv(PROCESSED_DATA_DIR / "all_syrian_flight_events.csv", index=False)
    with open(PROCESSED_DATA_DIR / "all_syrian_flight_events.json", "w", encoding="utf-8") as f:
        json.dump(df_events_clean.to_dict(orient="records"), f, indent=2, ensure_ascii=False)

    # Damascus specific events
    df_dam_events = df_events_clean[df_events_clean["airport_id"] == "DAM"]
    df_dam_events.to_csv(PROCESSED_DATA_DIR / "damascus_flight_events.csv", index=False)
    with open(PROCESSED_DATA_DIR / "damascus_flight_events.json", "w", encoding="utf-8") as f:
        json.dump(df_dam_events.to_dict(orient="records"), f, indent=2, ensure_ascii=False)

    # B. All Syrian Daily Movements
    df_all_daily = pd.DataFrame(all_daily_movements)
    df_all_daily.to_csv(PROCESSED_DATA_DIR / "daily_airport_movements.csv", index=False)
    with open(PROCESSED_DATA_DIR / "daily_airport_movements.json", "w", encoding="utf-8") as f:
        json.dump(all_daily_movements, f, indent=2, ensure_ascii=False)

    # Damascus Daily Movements
    df_dam_daily = pd.DataFrame(dam_daily_movements)
    df_dam_daily.to_csv(PROCESSED_DATA_DIR / "damascus_daily_movements.csv", index=False)
    with open(PROCESSED_DATA_DIR / "damascus_daily_movements.json", "w", encoding="utf-8") as f:
        json.dump(dam_daily_movements, f, indent=2, ensure_ascii=False)

    # C. Historical 2024 Multi-Airport Series
    df_hist = pd.DataFrame(hist_records)
    df_hist.to_csv(PROCESSED_DATA_DIR / "historical_daily_movements_2024.csv", index=False)
    with open(PROCESSED_DATA_DIR / "historical_daily_movements_2024.json", "w", encoding="utf-8") as f:
        json.dump(hist_records, f, indent=2, ensure_ascii=False)

    # D. Syrian Airports Registry Export
    airports_list = list(SYRIAN_AIRPORTS_REGISTRY.values())
    df_airports = pd.DataFrame(airports_list)
    df_airports.to_csv(PROCESSED_DATA_DIR / "syrian_airports_registry.csv", index=False)
    with open(PROCESSED_DATA_DIR / "syrian_airports_registry.json", "w", encoding="utf-8") as f:
        json.dump(airports_list, f, indent=2, ensure_ascii=False)

    # E. Deduplication Audit Export
    df_audit = pd.DataFrame(audit_log)
    df_audit.to_csv(REPORTS_DIR / "deduplication_audit.csv", index=False)
    with open(REPORTS_DIR / "deduplication_audit.json", "w", encoding="utf-8") as f:
        json.dump(audit_log, f, indent=2, ensure_ascii=False)

    # Summary
    summary = {
        "engine_version": "2.0-all-syrian-airports",
        "supported_airports": list(SYRIAN_AIRPORTS_REGISTRY.keys()),
        "total_canonical_events": len(events),
        "events_per_airport": {aid: len([e for e in events if e.get("airport_id") == aid]) for aid in SYRIAN_AIRPORTS_REGISTRY},
        "daily_movement_dates_per_airport": {aid: len(set(r["flight_date"] for r in all_daily_movements if r["airport_id"] == aid)) for aid in SYRIAN_AIRPORTS_REGISTRY},
        "historical_2024_scope": "DAM_ALP_LTK (Syrian Gateways Combined)",
        "historical_2024_rows": len(hist_records),
        "historical_2024_earliest_date": hist_records[0]["flight_date"] if hist_records else None,
        "historical_2024_latest_date": hist_records[-1]["flight_date"] if hist_records else None,
        "deduplication_audited_count": len(audit_log),
    }

    with open(PROCESSED_DATA_DIR / "syrian_aviation_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return summary
