import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple
from src.config import (
    RAW_DATA_DIR,
    AIRPORT_IATA,
    AIRPORT_ICAO,
    SYRIAN_AIRPORT_IATAS,
    SYRIAN_AIRPORT_ICAOS,
)

def parse_iso_or_epoch(val: Any, is_damascus_local_source: bool = False) -> str | None:
    """
    Parses timestamp string or epoch number into ISO 8601 UTC string (YYYY-MM-DDTHH:MM:SSZ).
    AviationStack represents Damascus flight wall-clock times with a +00:00 suffix.
    When is_damascus_local_source is True, adjusts the 3-hour Damascus offset to true UTC.
    """
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        try:
            dt = datetime.fromtimestamp(val, tz=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return None
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        dt = None
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(val, fmt)
                break
            except ValueError:
                continue
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            if is_damascus_local_source:
                # AviationStack outputs Damascus wall-clock time with +00:00; Damascus is UTC+3
                dt = dt - timedelta(hours=3)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            epoch = float(val)
            dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return val
    return None

def normalize_status(status_str: Any) -> str:
    if not status_str or not isinstance(status_str, str):
        return "unknown"
    s = status_str.strip().lower()
    if any(k in s for k in ("landed", "arrived")):
        return "landed"
    if any(k in s for k in ("cancel", "cancelled", "canceled")):
        return "cancelled"
    if any(k in s for k in ("divert", "diverted")):
        return "diverted"
    if any(k in s for k in ("active", "en-route", "departed", "airborne")):
        return "active"
    if any(k in s for k in ("sched", "scheduled", "expected", "estimated")):
        return "scheduled"
    return "unknown"

def determine_route_type(iata: str | None, icao: str | None, country: str | None) -> str:
    if iata and iata.upper() in SYRIAN_AIRPORT_IATAS:
        return "domestic"
    if icao and icao.upper() in SYRIAN_AIRPORT_ICAOS:
        return "domestic"
    if country and country.strip().lower() in ("syria", "syrian arab republic", "sy"):
        return "domestic"
    if iata or icao or country:
        return "international"
    return "unknown"

def generate_event_id(movement_type: str, flight_number: str, flight_date: str, sched_time: str | None) -> str:
    seed = f"{movement_type.lower()}|{flight_number.upper().strip()}|{flight_date}|{(sched_time or '')[:16]}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]

def normalize_aviationstack(raw_data: List[Dict[str, Any]], movement_type: str) -> List[Dict[str, Any]]:
    records = []
    for item in raw_data:
        dep = item.get("departure") or {}
        arr = item.get("arrival") or {}
        airline = item.get("airline") or {}
        flight = item.get("flight") or {}
        aircraft = item.get("aircraft") or {}

        flight_number = flight.get("iata") or flight.get("icao") or flight.get("number") or "UNKNOWN"
        raw_status = item.get("flight_status") or "unknown"
        flight_status = normalize_status(raw_status)

        # In AviationStack, Damascus timestamps (timezone Asia/Damascus) are wall-clock with +00:00
        sched_dep = parse_iso_or_epoch(dep.get("scheduled"), is_damascus_local_source=True)
        act_dep = parse_iso_or_epoch(dep.get("actual"), is_damascus_local_source=True)
        sched_arr = parse_iso_or_epoch(arr.get("scheduled"), is_damascus_local_source=True)
        act_arr = parse_iso_or_epoch(arr.get("actual"), is_damascus_local_source=True)

        if movement_type == "departure":
            connected_iata = arr.get("iata")
            connected_icao = arr.get("icao")
            connected_name = arr.get("airport")
            connected_city = arr.get("timezone", "").split("/")[-1].replace("_", " ") if arr.get("timezone") else None
            connected_country = None
            ref_time = sched_dep or act_dep
        else:
            connected_iata = dep.get("iata")
            connected_icao = dep.get("icao")
            connected_name = dep.get("airport")
            connected_city = dep.get("timezone", "").split("/")[-1].replace("_", " ") if dep.get("timezone") else None
            connected_country = None
            ref_time = sched_arr or act_arr

        flight_date = ref_time[:10] if ref_time else (item.get("flight_date") or "")
        route_type = determine_route_type(connected_iata, connected_icao, connected_country)
        event_id = generate_event_id(movement_type, flight_number, flight_date, ref_time)

        records.append({
            "event_id": event_id,
            "source": "aviationstack",
            "source_record_id": f"as_{item.get('flight_date')}_{flight_number}",
            "movement_type": movement_type,
            "airport_iata": AIRPORT_IATA,
            "airport_icao": AIRPORT_ICAO,
            "connected_airport_iata": connected_iata,
            "connected_airport_icao": connected_icao,
            "connected_airport_name": connected_name,
            "connected_country": connected_country,
            "connected_city": connected_city,
            "route_type": route_type,
            "airline_name": airline.get("name"),
            "airline_iata": airline.get("iata"),
            "airline_icao": airline.get("icao"),
            "flight_number": flight_number,
            "flight_date": flight_date,
            "flight_status": flight_status,
            "scheduled_dep_time": sched_dep,
            "actual_dep_time": act_dep,
            "scheduled_arr_time": sched_arr,
            "actual_arr_time": act_arr,
            "aircraft_model": aircraft.get("iata") or aircraft.get("icao"),
            "aircraft_registration": aircraft.get("registration"),
            "aircraft_icao24": aircraft.get("icao24"),
            "raw_json": json.dumps(item),
        })
    return records

def normalize_flightradar24(raw_data: List[Dict[str, Any]], movement_type: str) -> List[Dict[str, Any]]:
    records = []
    for entry in raw_data:
        flight = entry.get("flight") or {}
        ident = flight.get("identification") or {}
        flight_number = (ident.get("number") or {}).get("default") or ident.get("callsign") or "UNKNOWN"

        status_obj = flight.get("status") or {}
        raw_status = (status_obj.get("generic", {}).get("status", {}) or {}).get("text") or status_obj.get("text")
        flight_status = normalize_status(raw_status)

        aircraft = flight.get("aircraft") or {}
        airline = flight.get("airline") or {}
        airport = flight.get("airport") or {}
        origin = airport.get("origin") or {}
        dest = airport.get("destination") or {}

        time_obj = flight.get("time") or {}
        sched_time_obj = time_obj.get("scheduled") or {}
        real_time_obj = time_obj.get("real") or {}

        sched_dep = parse_iso_or_epoch(sched_time_obj.get("departure"))
        act_dep = parse_iso_or_epoch(real_time_obj.get("departure"))
        sched_arr = parse_iso_or_epoch(sched_time_obj.get("arrival"))
        act_arr = parse_iso_or_epoch(real_time_obj.get("arrival"))

        if movement_type == "departure":
            ref_time = sched_dep or act_dep
            connected_iata = (dest.get("code") or {}).get("iata")
            connected_icao = (dest.get("code") or {}).get("icao")
            connected_name = dest.get("name")
            connected_country = (dest.get("position", {}).get("country") or {}).get("name")
            connected_city = (dest.get("region") or {}).get("city")
        else:
            ref_time = sched_arr or act_arr
            connected_iata = (origin.get("code") or {}).get("iata")
            connected_icao = (origin.get("code") or {}).get("icao")
            connected_name = origin.get("name")
            connected_country = (origin.get("position", {}).get("country") or {}).get("name")
            connected_city = (origin.get("region") or {}).get("city")

        flight_date = ref_time[:10] if ref_time else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        route_type = determine_route_type(connected_iata, connected_icao, connected_country)
        event_id = generate_event_id(movement_type, flight_number, flight_date, ref_time)

        records.append({
            "event_id": event_id,
            "source": "flightradar24",
            "source_record_id": f"fr24_{ident.get('row') or event_id}",
            "movement_type": movement_type,
            "airport_iata": AIRPORT_IATA,
            "airport_icao": AIRPORT_ICAO,
            "connected_airport_iata": connected_iata,
            "connected_airport_icao": connected_icao,
            "connected_airport_name": connected_name,
            "connected_country": connected_country,
            "connected_city": connected_city,
            "route_type": route_type,
            "airline_name": airline.get("name"),
            "airline_iata": (airline.get("code") or {}).get("iata"),
            "airline_icao": (airline.get("code") or {}).get("icao"),
            "flight_number": flight_number,
            "flight_date": flight_date,
            "flight_status": flight_status,
            "scheduled_dep_time": sched_dep,
            "actual_dep_time": act_dep,
            "scheduled_arr_time": sched_arr,
            "actual_arr_time": act_arr,
            "aircraft_model": (aircraft.get("model") or {}).get("text") or (aircraft.get("model") or {}).get("code"),
            "aircraft_registration": aircraft.get("registration") or None,
            "aircraft_icao24": aircraft.get("hex") or None,
            "raw_json": json.dumps(entry),
        })
    return records

def deduplicate_flight_events(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """
    Deduplicates records across AviationStack and Flightradar24.
    Matches flights by:
    - movement_type
    - normalized flight_number
    - flight_date
    - scheduled or operational time slot (hourly)
    Merges complementary metadata:
    - If FR24 has aircraft model/registration/hex, enrich AS record
    - If AS has terminal/city or FR24 has actual timestamps, merge them
    - Prioritize verified actual landed/diverted status over 'scheduled'
    """
    seen = {}
    duplicates_count = 0

    for rec in records:
        f_num = rec["flight_number"].strip().upper().replace(" ", "").replace("-", "")
        m_type = rec["movement_type"]
        f_date = rec["flight_date"]
        t_ref = rec["scheduled_dep_time"] if m_type == "departure" else rec["scheduled_arr_time"]
        time_slot = t_ref[:13] if t_ref and len(t_ref) >= 13 else f_date

        key = (m_type, f_num, f_date, time_slot)

        if key in seen:
            duplicates_count += 1
            existing = seen[key]
            # Merge fields
            for field in (
                "actual_dep_time", "actual_arr_time",
                "aircraft_registration", "aircraft_icao24", "aircraft_model",
                "airline_name", "connected_country", "connected_city", "connected_airport_name"
            ):
                if not existing.get(field) and rec.get(field):
                    existing[field] = rec[field]
            # Promote status if existing is scheduled and new has definitive status
            if existing.get("flight_status") == "scheduled" and rec.get("flight_status") in ("landed", "active", "cancelled", "diverted"):
                existing["flight_status"] = rec["flight_status"]
            # Append source provenance
            if rec["source"] not in existing["source"]:
                existing["source"] = f"{existing['source']}+{rec['source']}"
        else:
            seen[key] = dict(rec)

    deduped_records = list(seen.values())
    return deduped_records, duplicates_count

def load_and_normalize_all_events() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    all_raw_events = []
    audit = {}

    as_dep_path = RAW_DATA_DIR / "aviationstack_dam_departures_raw.json"
    if as_dep_path.exists():
        with open(as_dep_path, "r", encoding="utf-8") as f:
            as_dep_json = json.load(f)
            data = as_dep_json.get("data", [])
            as_dep_recs = normalize_aviationstack(data, "departure")
            all_raw_events.extend(as_dep_recs)
            audit["aviationstack_departures_raw"] = len(as_dep_recs)

    as_arr_path = RAW_DATA_DIR / "aviationstack_dam_arrivals_raw.json"
    if as_arr_path.exists():
        with open(as_arr_path, "r", encoding="utf-8") as f:
            as_arr_json = json.load(f)
            data = as_arr_json.get("data", [])
            as_arr_recs = normalize_aviationstack(data, "arrival")
            all_raw_events.extend(as_arr_recs)
            audit["aviationstack_arrivals_raw"] = len(as_arr_recs)

    fr_dep_path = RAW_DATA_DIR / "flightradar24_dam_departures_raw.json"
    if fr_dep_path.exists():
        with open(fr_dep_path, "r", encoding="utf-8") as f:
            fr_dep_data = json.load(f)
            fr_dep_recs = normalize_flightradar24(fr_dep_data, "departure")
            all_raw_events.extend(fr_dep_recs)
            audit["flightradar24_departures_raw"] = len(fr_dep_recs)

    fr_arr_path = RAW_DATA_DIR / "flightradar24_dam_arrivals_raw.json"
    if fr_arr_path.exists():
        with open(fr_arr_path, "r", encoding="utf-8") as f:
            fr_arr_data = json.load(f)
            fr_arr_recs = normalize_flightradar24(fr_arr_data, "arrival")
            all_raw_events.extend(fr_arr_recs)
            audit["flightradar24_arrivals_raw"] = len(fr_arr_recs)

    audit["total_raw_events"] = len(all_raw_events)

    deduped_events, duplicates_count = deduplicate_flight_events(all_raw_events)
    audit["duplicates_pruned"] = duplicates_count
    audit["total_deduped_events"] = len(deduped_events)

    return deduped_events, audit
