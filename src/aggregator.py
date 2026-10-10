import json
import sqlite3
from typing import List, Dict, Any
import pandas as pd
from src.config import (
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    DB_PATH,
)
from src.database import get_connection

def aggregate_damascus_daily_movements(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Computes daily arrival and departure movement metrics strictly from verified Damascus flight records.
    Never fills missing dates with zeros.
    """
    if not events:
        return []

    df = pd.DataFrame(events)
    # Ensure flight_date exists
    df = df[df["flight_date"].notnull() & (df["flight_date"] != "")]

    daily_records = []
    grouped = df.groupby("flight_date")

    for date_str, group in grouped:
        arr_df = group[group["movement_type"] == "arrival"]
        dep_df = group[group["movement_type"] == "departure"]

        arr_count = len(arr_df)
        dep_count = len(dep_df)

        # Total movements: only valid when both directions have observations
        if arr_count > 0 and dep_count > 0:
            total_movements = arr_count + dep_count
            completeness = "complete_verified"
        elif arr_count > 0:
            total_movements = arr_count
            completeness = "partial_arrivals_only"
        elif dep_count > 0:
            total_movements = dep_count
            completeness = "partial_departures_only"
        else:
            continue

        # Status breakdowns
        landed_count = int((group["flight_status"] == "landed").sum())
        cancelled_count = int((group["flight_status"] == "cancelled").sum())
        diverted_count = int((group["flight_status"] == "diverted").sum())
        scheduled_count = int((group["flight_status"] == "scheduled").sum())
        active_count = int((group["flight_status"] == "active").sum())

        # Route breakdowns
        domestic_count = int((group["route_type"] == "domestic").sum())
        international_count = int((group["route_type"] == "international").sum())

        # Unique aircraft identifiers (registration or hex)
        aircraft_ids = set()
        for _, row in group.iterrows():
            reg = row.get("aircraft_registration")
            hex_id = row.get("aircraft_icao24")
            if reg and str(reg).strip():
                aircraft_ids.add(str(reg).strip().upper())
            elif hex_id and str(hex_id).strip():
                aircraft_ids.add(str(hex_id).strip().upper())

        # Unique airlines
        airlines = set()
        for _, row in group.iterrows():
            al = row.get("airline_name") or row.get("airline_iata") or row.get("airline_icao")
            if al and str(al).strip():
                airlines.add(str(al).strip())

        daily_records.append({
            "flight_date": date_str,
            "arrival_count": arr_count,
            "departure_count": dep_count,
            "total_movements": total_movements,
            "landed_count": landed_count,
            "cancelled_count": cancelled_count,
            "diverted_count": diverted_count,
            "scheduled_count": scheduled_count,
            "active_count": active_count,
            "domestic_count": domestic_count,
            "international_count": international_count,
            "unique_aircraft_count": len(aircraft_ids),
            "unique_airlines_count": len(airlines),
            "completeness_status": completeness,
        })

    daily_records.sort(key=lambda x: x["flight_date"])
    return daily_records

def load_historical_sem_series() -> List[Dict[str, Any]]:
    """
    Loads Syria Economic Monitor 2024 daily time-series records for DAM, ALP, and LTK.
    Distinguishes operational status counts and preserves provider missing dates.
    """
    historical_records = []

    dep_file = RAW_DATA_DIR / "daily_departures_from_dam__alp_and_ltk.json"
    arr_file = RAW_DATA_DIR / "daily_arrivals_to_dam__alp_and_ltk.json"

    known_missing_dates = {
        "2024-01-28", "2024-01-29", "2024-01-30",
        "2024-04-29", "2024-04-30",
        "2024-06-07", "2024-06-08", "2024-06-09"
    }

    if dep_file.exists():
        with open(dep_file, "r", encoding="utf-8") as f:
            dep_data = json.load(f)
            for row in dep_data:
                f_date = row.get("flight_date_iso")
                act = int(row.get("active", 0))
                can = int(row.get("cancelled", 0))
                div = int(row.get("diverted", 0))
                lan = int(row.get("landed", 0))
                sch = int(row.get("scheduled", 0))
                unk = int(row.get("unknown", 0))
                total = act + can + div + lan + sch + unk
                note = "documented_provider_gap" if f_date in known_missing_dates else "verified_research_record"

                historical_records.append({
                    "flight_date": f_date,
                    "movement_type": "departure",
                    "scope": "DAM_ALP_LTK",
                    "active": act,
                    "cancelled": can,
                    "diverted": div,
                    "landed": lan,
                    "scheduled": sch,
                    "unknown": unk,
                    "total_recorded_operations": total,
                    "data_source": "Syria Economic Monitor (AviationStack)",
                    "status_note": note,
                })

    if arr_file.exists():
        with open(arr_file, "r", encoding="utf-8") as f:
            arr_data = json.load(f)
            for row in arr_data:
                f_date = row.get("flight_date_iso")
                act = int(row.get("active", 0))
                can = int(row.get("cancelled", 0))
                div = int(row.get("diverted", 0))
                lan = int(row.get("landed", 0))
                sch = int(row.get("scheduled", 0))
                unk = int(row.get("unknown", 0))
                total = act + can + div + lan + sch + unk
                note = "documented_provider_gap" if f_date in known_missing_dates else "verified_research_record"

                historical_records.append({
                    "flight_date": f_date,
                    "movement_type": "arrival",
                    "scope": "DAM_ALP_LTK",
                    "active": act,
                    "cancelled": can,
                    "diverted": div,
                    "landed": lan,
                    "scheduled": sch,
                    "unknown": unk,
                    "total_recorded_operations": total,
                    "data_source": "Syria Economic Monitor (AviationStack)",
                    "status_note": note,
                })

    return historical_records

def persist_all_to_database_and_exports(events: List[Dict[str, Any]], daily_movements: List[Dict[str, Any]], hist_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. Flight Events
        cursor.execute("DELETE FROM flight_events;")
        for e in events:
            cursor.execute("""
            INSERT OR REPLACE INTO flight_events (
                event_id, source, source_record_id, movement_type, airport_iata, airport_icao,
                connected_airport_iata, connected_airport_icao, connected_airport_name,
                connected_country, connected_city, route_type, airline_name, airline_iata,
                airline_icao, flight_number, flight_date, flight_status,
                scheduled_dep_time, actual_dep_time, scheduled_arr_time, actual_arr_time,
                aircraft_model, aircraft_registration, aircraft_icao24, raw_json
            ) VALUES (
                :event_id, :source, :source_record_id, :movement_type, :airport_iata, :airport_icao,
                :connected_airport_iata, :connected_airport_icao, :connected_airport_name,
                :connected_country, :connected_city, :route_type, :airline_name, :airline_iata,
                :airline_icao, :flight_number, :flight_date, :flight_status,
                :scheduled_dep_time, :actual_dep_time, :scheduled_arr_time, :actual_arr_time,
                :aircraft_model, :aircraft_registration, :aircraft_icao24, :raw_json
            )
            """, e)

        # 2. Damascus Daily Movements
        cursor.execute("DELETE FROM damascus_daily_movements;")
        for d in daily_movements:
            cursor.execute("""
            INSERT OR REPLACE INTO damascus_daily_movements (
                flight_date, arrival_count, departure_count, total_movements,
                landed_count, cancelled_count, diverted_count, scheduled_count, active_count,
                domestic_count, international_count, unique_aircraft_count,
                unique_airlines_count, completeness_status
            ) VALUES (
                :flight_date, :arrival_count, :departure_count, :total_movements,
                :landed_count, :cancelled_count, :diverted_count, :scheduled_count, :active_count,
                :domestic_count, :international_count, :unique_aircraft_count,
                :unique_airlines_count, :completeness_status
            )
            """, d)

        # 3. Historical Daily Movements 2024
        cursor.execute("DELETE FROM historical_daily_movements_2024;")
        for h in hist_records:
            cursor.execute("""
            INSERT OR REPLACE INTO historical_daily_movements_2024 (
                flight_date, movement_type, scope, active, cancelled, diverted,
                landed, scheduled, unknown, total_recorded_operations, data_source, status_note
            ) VALUES (
                :flight_date, :movement_type, :scope, :active, :cancelled, :diverted,
                :landed, :scheduled, :unknown, :total_recorded_operations, :data_source, :status_note
            )
            """, h)

        conn.commit()

    # 4. Generate CSV and JSON Exports
    # Damascus Flight Events (exclude heavy raw_json in clean CSV)
    events_clean = [{k: v for k, v in e.items() if k != "raw_json"} for e in events]
    pd.DataFrame(events_clean).to_csv(PROCESSED_DATA_DIR / "damascus_flight_events.csv", index=False)
    with open(PROCESSED_DATA_DIR / "damascus_flight_events.json", "w", encoding="utf-8") as f:
        json.dump(events_clean, f, indent=2)

    # Damascus Daily Movements
    pd.DataFrame(daily_movements).to_csv(PROCESSED_DATA_DIR / "damascus_daily_movements.csv", index=False)
    with open(PROCESSED_DATA_DIR / "damascus_daily_movements.json", "w", encoding="utf-8") as f:
        json.dump(daily_movements, f, indent=2)

    # Historical 2024 Daily Movements
    pd.DataFrame(hist_records).to_csv(PROCESSED_DATA_DIR / "historical_daily_movements_2024.csv", index=False)
    with open(PROCESSED_DATA_DIR / "historical_daily_movements_2024.json", "w", encoding="utf-8") as f:
        json.dump(hist_records, f, indent=2)

    # Summary
    summary = {
        "airport_iata": "DAM",
        "airport_icao": "OSDI",
        "airport_name": "Damascus International Airport",
        "total_verified_damascus_flights": len(events),
        "earliest_damascus_flight_date": min((e["flight_date"] for e in events), default=None),
        "latest_damascus_flight_date": max((e["flight_date"] for e in events), default=None),
        "historical_2024_records_count": len(hist_records),
        "historical_2024_earliest_date": min((h["flight_date"] for h in hist_records), default=None),
        "historical_2024_latest_date": max((h["flight_date"] for h in hist_records), default=None),
        "total_unique_aircraft": len(set(e["aircraft_registration"] for e in events if e.get("aircraft_registration")) | set(e["aircraft_icao24"] for e in events if e.get("aircraft_icao24"))),
        "total_unique_airlines": len(set(e["airline_name"] for e in events if e.get("airline_name"))),
    }
    with open(PROCESSED_DATA_DIR / "damascus_airport_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary
