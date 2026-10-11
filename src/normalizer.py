import json
import hashlib
import re
from datetime import datetime, timezone
import zoneinfo
from typing import List, Dict, Any, Tuple

from src.config import (
    RAW_DATA_DIR,
    SYRIAN_AIRPORTS_REGISTRY,
    SYRIAN_AIRPORT_IATAS,
    SYRIAN_AIRPORT_ICAOS,
)

DAMASCUS_TZ = zoneinfo.ZoneInfo("Asia/Damascus")

def parse_timestamp_to_utc(val: Any) -> Tuple[str | None, str | None]:
    """
    Parses input timestamp into (raw_string, normalized_iso_utc).
    Rules:
    - If val is None or empty -> (None, None)
    - If val is integer/float -> Unix epoch timestamp in UTC
    - If val is string with explicit offset (+00:00, Z, +03:00, etc.) -> parse and convert to UTC
      (NEVER subtract hours merely because a timestamp is labeled +00:00)
    - If val is timezone-naive local string -> localize using Asia/Damascus and convert to UTC
    """
    if val is None or val == "":
        return None, None

    if isinstance(val, (int, float)):
        try:
            dt = datetime.fromtimestamp(val, tz=timezone.utc)
            return str(val), dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return str(val), None

    if isinstance(val, str):
        raw_str = val.strip()
        if not raw_str:
            return None, None

        # Check for numeric epoch in string
        try:
            epoch = float(raw_str)
            dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
            return raw_str, dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass

        # Parse string formats
        dt = None
        has_tz = False

        # Try ISO format with timezone (handles +00:00, +03:00, Z)
        try:
            dt = datetime.fromisoformat(raw_str.replace("Z", "+00:00"))
            has_tz = dt.tzinfo is not None
        except ValueError:
            pass

        if dt is None:
            for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S%z"):
                try:
                    dt = datetime.strptime(raw_str, fmt)
                    has_tz = dt.tzinfo is not None
                    break
                except ValueError:
                    continue

        if dt is None:
            # Timezone-naive formats
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                try:
                    dt = datetime.strptime(raw_str, fmt)
                    has_tz = False
                    break
                except ValueError:
                    continue

        if dt is not None:
            if has_tz:
                # Explicit offset: convert directly to UTC without arbitrary shifts
                dt_utc = dt.astimezone(timezone.utc)
            else:
                # Timezone-naive: localize to Asia/Damascus and convert to UTC
                dt_local = dt.replace(tzinfo=DAMASCUS_TZ)
                dt_utc = dt_local.astimezone(timezone.utc)
            return raw_str, dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

        return raw_str, None

    return str(val), None

def parse_aviationstack_timestamp(val: Any, tz_name: str | None = "Asia/Damascus") -> Tuple[str, str | None]:
    """
    Parse an AviationStack timestamp with provider-specific timezone awareness.
    AviationStack formats airport timestamps in local wall-clock time but appends an erroneous '+00:00' / 'Z' suffix.
    We preserve the raw string, strip the erroneous UTC suffix, localize the wall-clock datetime to
    the airport's IANA timezone, and convert to true UTC.
    """
    if not val:
        return str(val) if val is not None else "", None
    raw_str = str(val).strip()
    clean_str = raw_str
    for suffix in ("+00:00", "Z", "+00"):
        if clean_str.endswith(suffix):
            clean_str = clean_str[:-len(suffix)]
            break
    try:
        dt_naive = datetime.fromisoformat(clean_str)
    except Exception:
        return raw_str, None
    tz = DAMASCUS_TZ
    if tz_name:
        try:
            tz = zoneinfo.ZoneInfo(tz_name)
        except Exception:
            tz = DAMASCUS_TZ
    dt_local = dt_naive.replace(tzinfo=tz)
    dt_utc = dt_local.astimezone(timezone.utc)
    return raw_str, dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

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
    if any(k in s for k in ("departed", "took off")):
        return "departed"
    if any(k in s for k in ("active", "en-route", "airborne")):
        return "active"
    if any(k in s for k in ("sched", "scheduled", "expected", "estimated", "on-time", "delayed", "new-time")):
        return "scheduled"
    return "unknown"

def determine_route_type(iata: str | None, icao: str | None, country: str | None) -> str:
    if iata and iata.upper() in SYRIAN_AIRPORT_IATAS:
        return "domestic"
    if icao and icao.upper() in SYRIAN_AIRPORT_ICAOS:
        return "domestic"
    if country and country.strip().lower() in ("syria", "syrian arab republic", "sy", "سوريا"):
        return "domestic"
    if iata or icao or country:
        return "international"
    return "unknown"

def generate_event_id(airport_id: str, movement_type: str, flight_number: str, flight_date: str, sched_time: str | None) -> str:
    seed = f"{airport_id.upper()}|{movement_type.lower()}|{flight_number.upper().strip().replace(' ', '')}|{flight_date}|{(sched_time or '')[:16]}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]

# 1. Official Syrian Airport Portals (damairport.gov.sy & alpairport.gov.sy)
def normalize_official_portal_flights(raw_data: List[Dict[str, Any]], airport_id: str) -> List[Dict[str, Any]]:
    records = []
    reg_info = SYRIAN_AIRPORTS_REGISTRY.get(airport_id, {})
    airport_iata = reg_info.get("iata_code", airport_id)
    airport_icao = reg_info.get("icao_code", f"OS{airport_id}")

    for item in raw_data:
        flight_num_raw = str(item.get("flightNumber") or "UNKNOWN").strip()
        flight_number = flight_num_raw.replace(" ", "")
        direction = str(item.get("direction") or "arrival").strip().lower()
        movement_type = "departure" if direction == "departure" else "arrival"

        airline_name = item.get("airline") or ""
        airline_info = item.get("airlineInfo") or {}
        airline_iata = airline_info.get("iata") or None

        origin_apt = item.get("originAirport") or {}
        dest_apt = item.get("destinationAirport") or {}
        conn_apt = origin_apt if movement_type == "arrival" else dest_apt

        connected_iata = conn_apt.get("code") or (item.get("origin") if movement_type == "arrival" else item.get("destination"))
        connected_icao = conn_apt.get("icao")
        connected_name = conn_apt.get("name_en") or conn_apt.get("name_ar")
        connected_country = conn_apt.get("country_en") or conn_apt.get("country_ar")
        connected_city = conn_apt.get("city_en") or conn_apt.get("city_ar")

        date_val = str(item.get("date") or "").strip()
        time_val = str(item.get("time") or "").strip()
        raw_time_str = f"{date_val} {time_val}".strip() if (date_val and time_val) else (date_val or None)

        raw_time, utc_iso = parse_timestamp_to_utc(raw_time_str)
        local_operational_date = date_val or (utc_iso[:10] if utc_iso else "")

        sched_dep = utc_iso if movement_type == "departure" else None
        raw_sched_dep = raw_time if movement_type == "departure" else None
        sched_arr = utc_iso if movement_type == "arrival" else None
        raw_sched_arr = raw_time if movement_type == "arrival" else None

        raw_status = str(item.get("status") or "scheduled")
        flight_status = normalize_status(raw_status)
        route_type = determine_route_type(connected_iata, connected_icao, connected_country)

        if flight_status in ("landed", "departed"):
            record_nature = "unverified_movement"
        else:
            record_nature = "scheduled_service"

        event_id = generate_event_id(airport_id, movement_type, flight_number, local_operational_date, utc_iso)

        records.append({
            "event_id": event_id,
            "airport_id": airport_id,
            "source": f"{airport_id.lower()}airport_official",
            "source_record_id": str(item.get("id") or f"off_{airport_id}_{local_operational_date}_{flight_number}"),
            "movement_type": movement_type,
            "airport_iata": airport_iata,
            "airport_icao": airport_icao,
            "connected_airport_iata": connected_iata,
            "connected_airport_icao": connected_icao,
            "connected_airport_name": connected_name,
            "connected_country": connected_country,
            "connected_city": connected_city,
            "route_type": route_type,
            "airline_name": airline_name,
            "airline_iata": airline_iata,
            "airline_icao": None,
            "flight_number": flight_number,
            "flight_date": local_operational_date,
            "local_operational_date": local_operational_date,
            "flight_status": flight_status,
            "scheduled_dep_time": sched_dep,
            "estimated_dep_time": None,
            "actual_dep_time": None,
            "scheduled_arr_time": sched_arr,
            "estimated_arr_time": None,
            "actual_arr_time": None,
            "raw_scheduled_dep_time": raw_sched_dep,
            "raw_estimated_dep_time": None,
            "raw_actual_dep_time": None,
            "raw_scheduled_arr_time": raw_sched_arr,
            "raw_estimated_arr_time": None,
            "raw_actual_arr_time": None,
            "aircraft_model": item.get("aircraft") or None,
            "aircraft_registration": None,
            "aircraft_icao24": None,
            "record_nature": record_nature,
            "operating_flight_number": flight_number,
            "operating_carrier": airline_name,
            "observed_or_derived": "observed",
            "quality_flags": "official_authority_source",
            "normalization_version": "2.0",
            "raw_json": json.dumps(item, ensure_ascii=False),
        })

    return records

# 2. AviationStack Live Normalizer
def normalize_aviationstack(raw_data: List[Dict[str, Any]], movement_type: str, airport_id: str = "DAM") -> List[Dict[str, Any]]:
    records = []
    reg_info = SYRIAN_AIRPORTS_REGISTRY.get(airport_id, {})
    airport_iata = reg_info.get("iata_code", airport_id)
    airport_icao = reg_info.get("icao_code", f"OS{airport_id}")

    for item in raw_data:
        dep = item.get("departure") or {}
        arr = item.get("arrival") or {}
        airline = item.get("airline") or {}
        flight = item.get("flight") or {}
        aircraft = item.get("aircraft") or {}

        flight_number = str(flight.get("iata") or flight.get("icao") or flight.get("number") or "UNKNOWN").replace(" ", "")
        raw_status = item.get("flight_status") or "unknown"
        flight_status = normalize_status(raw_status)

        dep_tz = dep.get("timezone") or ("Asia/Damascus" if movement_type == "departure" else None)
        arr_tz = arr.get("timezone") or ("Asia/Damascus" if movement_type == "arrival" else None)

        raw_sched_dep, sched_dep = parse_aviationstack_timestamp(dep.get("scheduled"), dep_tz)
        raw_est_dep, est_dep = parse_aviationstack_timestamp(dep.get("estimated"), dep_tz)
        raw_act_dep, act_dep = parse_aviationstack_timestamp(dep.get("actual"), dep_tz)
        raw_sched_arr, sched_arr = parse_aviationstack_timestamp(arr.get("scheduled"), arr_tz)
        raw_est_arr, est_arr = parse_aviationstack_timestamp(arr.get("estimated"), arr_tz)
        raw_act_arr, act_arr = parse_aviationstack_timestamp(arr.get("actual"), arr_tz)

        if movement_type == "departure":
            connected_iata = arr.get("iata")
            connected_icao = arr.get("icao")
            connected_name = arr.get("airport")
            connected_city = arr.get("timezone", "").split("/")[-1].replace("_", " ") if arr.get("timezone") else None
            connected_country = None
            ref_time = sched_dep or act_dep or est_dep
        else:
            connected_iata = dep.get("iata")
            connected_icao = dep.get("icao")
            connected_name = dep.get("airport")
            connected_city = dep.get("timezone", "").split("/")[-1].replace("_", " ") if dep.get("timezone") else None
            connected_country = None
            ref_time = sched_arr or act_arr or est_arr

        # Local operational date in Asia/Damascus
        if ref_time:
            try:
                dt_utc = datetime.fromisoformat(ref_time.replace("Z", "+00:00"))
                dt_local = dt_utc.astimezone(DAMASCUS_TZ)
                flight_date = dt_local.strftime("%Y-%m-%d")
            except Exception:
                flight_date = ref_time[:10]
        else:
            flight_date = item.get("flight_date") or ""

        codeshared = flight.get("codeshared")
        if codeshared:
            record_nature = "marketing_codeshare"
            op_fnum = codeshared.get("flight_iata") or codeshared.get("flight_number")
            operating_flight_number = str(op_fnum).replace(" ", "").upper() if op_fnum else None
            operating_carrier = codeshared.get("airline_name")
        elif flight_status in ("landed", "departed"):
            record_nature = "unverified_movement"
            operating_flight_number = flight_number
            operating_carrier = airline.get("name")
        else:
            record_nature = "scheduled_service"
            operating_flight_number = flight_number
            operating_carrier = airline.get("name")
        route_type = determine_route_type(connected_iata, connected_icao, connected_country)
        event_id = generate_event_id(airport_id, movement_type, flight_number, flight_date, ref_time)

        records.append({
            "event_id": event_id,
            "airport_id": airport_id,
            "source": "aviationstack",
            "source_record_id": f"as_{item.get('flight_date')}_{flight_number}_{ref_time or ''}",
            "movement_type": movement_type,
            "airport_iata": airport_iata,
            "airport_icao": airport_icao,
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
            "local_operational_date": flight_date,
            "flight_status": flight_status,
            "scheduled_dep_time": sched_dep,
            "estimated_dep_time": est_dep,
            "actual_dep_time": act_dep,
            "scheduled_arr_time": sched_arr,
            "estimated_arr_time": est_arr,
            "actual_arr_time": act_arr,
            "raw_scheduled_dep_time": raw_sched_dep,
            "raw_estimated_dep_time": raw_est_dep,
            "raw_actual_dep_time": raw_act_dep,
            "raw_scheduled_arr_time": raw_sched_arr,
            "raw_estimated_arr_time": raw_est_arr,
            "raw_actual_arr_time": raw_act_arr,
            "aircraft_model": aircraft.get("iata") or aircraft.get("icao"),
            "aircraft_registration": aircraft.get("registration"),
            "aircraft_icao24": aircraft.get("icao24"),
            "record_nature": record_nature,
            "operating_flight_number": operating_flight_number,
            "operating_carrier": operating_carrier,
            "observed_or_derived": "observed",
            "quality_flags": "aviationstack_feed_damascus_tz_corrected",
            "normalization_version": "2.1",
            "raw_json": json.dumps(item, ensure_ascii=False),
        })

    return records

# 3. Flightradar24 Normalizer (Multi-Airport)
def normalize_flightradar24(raw_data: List[Dict[str, Any]], movement_type: str, airport_id: str = "DAM") -> List[Dict[str, Any]]:
    records = []
    reg_info = SYRIAN_AIRPORTS_REGISTRY.get(airport_id, {})
    airport_iata = reg_info.get("iata_code", airport_id)
    airport_icao = reg_info.get("icao_code", f"OS{airport_id}")

    for item in raw_data:
        flight = item.get("flight") or {}
        ident = flight.get("identification") or {}
        status_info = flight.get("status") or {}
        airline = flight.get("airline") or {}
        aircraft = flight.get("aircraft") or {}
        airport_info = flight.get("airport") or {}
        time_info = flight.get("time") or {}

        flight_number = str(ident.get("number", {}).get("default") or ident.get("callsign") or "UNKNOWN").replace(" ", "")
        raw_status_text = status_info.get("text") or status_info.get("generic", {}).get("status", {}).get("text") or "unknown"
        flight_status = normalize_status(raw_status_text)

        sched = time_info.get("scheduled") or {}
        real = time_info.get("real") or {}
        estimated = time_info.get("estimated") or {}

        raw_sched_dep, sched_dep = parse_timestamp_to_utc(sched.get("departure"))
        raw_est_dep, est_dep = parse_timestamp_to_utc(estimated.get("departure"))
        raw_act_dep, act_dep = parse_timestamp_to_utc(real.get("departure"))
        raw_sched_arr, sched_arr = parse_timestamp_to_utc(sched.get("arrival"))
        raw_est_arr, est_arr = parse_timestamp_to_utc(estimated.get("arrival"))
        raw_act_arr, act_arr = parse_timestamp_to_utc(real.get("arrival"))

        if movement_type == "departure":
            dest = airport_info.get("destination") or {}
            connected_iata = dest.get("code", {}).get("iata")
            connected_icao = dest.get("code", {}).get("icao")
            connected_name = dest.get("name")
            connected_country = dest.get("position", {}).get("country", {}).get("name")
            connected_city = dest.get("position", {}).get("region", {}).get("city")
            ref_time = sched_dep or act_dep or est_dep
        else:
            orig = airport_info.get("origin") or {}
            connected_iata = orig.get("code", {}).get("iata")
            connected_icao = orig.get("code", {}).get("icao")
            connected_name = orig.get("name")
            connected_country = orig.get("position", {}).get("country", {}).get("name")
            connected_city = orig.get("position", {}).get("region", {}).get("city")
            ref_time = sched_arr or act_arr or est_arr

        # Local operational date in Asia/Damascus
        if ref_time:
            try:
                dt_utc = datetime.fromisoformat(ref_time.replace("Z", "+00:00"))
                dt_local = dt_utc.astimezone(DAMASCUS_TZ)
                flight_date = dt_local.strftime("%Y-%m-%d")
            except Exception:
                flight_date = ref_time[:10]
        else:
            flight_date = ""

        route_type = determine_route_type(connected_iata, connected_icao, connected_country)
        event_id = generate_event_id(airport_id, movement_type, flight_number, flight_date, ref_time)
        fr_row_id = ident.get("row") or ident.get("id")

        if (movement_type == "departure" and act_dep and flight_status == "departed") or \
           (movement_type == "arrival" and act_arr and flight_status == "landed"):
            record_nature = "physical_movement"
        else:
            record_nature = "scheduled_service"

        records.append({
            "event_id": event_id,
            "airport_id": airport_id,
            "source": "flightradar24",
            "source_record_id": f"fr24_{fr_row_id or flight_number}_{ref_time or ''}",
            "movement_type": movement_type,
            "airport_iata": airport_iata,
            "airport_icao": airport_icao,
            "connected_airport_iata": connected_iata,
            "connected_airport_icao": connected_icao,
            "connected_airport_name": connected_name,
            "connected_country": connected_country,
            "connected_city": connected_city,
            "route_type": route_type,
            "airline_name": airline.get("name"),
            "airline_iata": None,
            "airline_icao": airline.get("code", {}).get("icao"),
            "flight_number": flight_number,
            "flight_date": flight_date,
            "local_operational_date": flight_date,
            "flight_status": flight_status,
            "scheduled_dep_time": sched_dep,
            "estimated_dep_time": est_dep,
            "actual_dep_time": act_dep,
            "scheduled_arr_time": sched_arr,
            "estimated_arr_time": est_arr,
            "actual_arr_time": act_arr,
            "raw_scheduled_dep_time": raw_sched_dep,
            "raw_estimated_dep_time": raw_est_dep,
            "raw_actual_dep_time": raw_act_dep,
            "raw_scheduled_arr_time": raw_sched_arr,
            "raw_estimated_arr_time": raw_est_arr,
            "raw_actual_arr_time": raw_act_arr,
            "aircraft_model": aircraft.get("model", {}).get("text") or aircraft.get("model", {}).get("code"),
            "aircraft_registration": aircraft.get("registration"),
            "aircraft_icao24": aircraft.get("hex"),
            "record_nature": record_nature,
            "operating_flight_number": flight_number,
            "operating_carrier": airline.get("name"),
            "observed_or_derived": "observed",
            "quality_flags": "fr24_radar_feed",
            "normalization_version": "2.0",
            "raw_json": json.dumps(item, ensure_ascii=False),
        })

    return records

def get_timestamp_priority(source_name: str | None, has_actual: bool) -> int:
    """
    Returns the evidence priority tier for operational flight movement timestamps:
    - Tier 4: Terrestrial ADS-B radar physical telemetry (Flightradar24 actual touchdown/wheels-off epoch)
    - Tier 3: Commercial flight tracker actual timestamps (AviationStack actual)
    - Tier 2: Official airport portal actual operational timestamps (damairport, alpairport, etc.)
    - Tier 1: Scheduled service timetable timestamps (NEVER treated as physical movements)
    - Tier 0: Missing or unknown timestamps
    """
    if not has_actual or not source_name:
        return 0
    src = str(source_name).lower()
    if "flightradar24" in src or "adsb" in src:
        return 4
    elif "aviationstack" in src:
        return 3
    elif "official" in src or "damairport" in src or "alpairport" in src:
        return 2
    return 1

def determine_evidence_source(source_name: str | None, raw_ts: str | None = None) -> str:
    """
    Resolves the discrete originating source provider for an evidence record,
    decoupling discrete evidence observations from the composite event-level lineage.
    """
    if not source_name:
        return "unknown"
    src = str(source_name).strip()
    if "+" not in src:
        return src
    if raw_ts and str(raw_ts).strip().isdigit() and "flightradar24" in src:
        return "flightradar24"
    if raw_ts and ("+00:00" in str(raw_ts) or "+03:00" in str(raw_ts)) and "aviationstack" in src:
        return "aviationstack"
    if "flightradar24" in src and (raw_ts is None or str(raw_ts).strip().isdigit()):
        return "flightradar24"
    if "aviationstack" in src:
        return "aviationstack"
    for part in src.split("+"):
        if any(p in part for p in ["damairport", "alpairport", "deir", "qamishli"]):
            return part
    return src.split("+")[0]

def evaluate_cross_source_match(
    event_a: Dict[str, Any],
    event_b: Dict[str, Any],
    max_window_minutes: float = 60.0,
    ambiguous_window_minutes: float = 180.0
) -> Dict[str, Any]:
    """
    Evaluates cross-source event matching between two flight records using multi-factor criteria:
    - Primary Factors (Hard Prerequisites): Airport, movement type, flight date, flight identity.
    - Airframe Compatibility: Explicit conflict if non-empty registrations or hexes differ.
    - Operating Carrier / Codeshare Compatibility: Explicit conflict if carriers differ without codeshare.
    - Temporal Window Comparison:
      * diff <= max_window_minutes: CONFIRMED_MATCH (can merge)
      * max_window < diff <= ambiguous_window: POTENTIAL_MATCH_AMBIGUOUS_DELTA (kept separate)
      * diff > ambiguous_window: SPLIT_DISTINCT_LEG (distinct operational flights on same day)
      * missing time: POTENTIAL_MATCH_LACKS_TIME (kept separate)
    """
    apt_a = str(event_a.get("airport_id") or "").strip().upper()
    apt_b = str(event_b.get("airport_id") or "").strip().upper()
    if apt_a and apt_b and apt_a != apt_b:
        return {
            "can_merge": False,
            "match_status": "MISMATCH_AIRPORT",
            "confidence_score": 0.0,
            "conflict_reason": f"Different airports: {apt_a} vs {apt_b}",
            "time_diff_minutes": None
        }

    mtype_a = str(event_a.get("movement_type") or "").strip().lower()
    mtype_b = str(event_b.get("movement_type") or "").strip().lower()
    if mtype_a and mtype_b and mtype_a != mtype_b:
        return {
            "can_merge": False,
            "match_status": "MISMATCH_DIRECTION",
            "confidence_score": 0.0,
            "conflict_reason": f"Different movement directions: {mtype_a} vs {mtype_b}",
            "time_diff_minutes": None
        }

    date_a = str(event_a.get("flight_date") or "").strip()
    date_b = str(event_b.get("flight_date") or "").strip()
    if date_a and date_b and date_a != date_b:
        return {
            "can_merge": False,
            "match_status": "MISMATCH_DATE",
            "confidence_score": 0.0,
            "conflict_reason": f"Different operational dates: {date_a} vs {date_b}",
            "time_diff_minutes": None
        }

    fn_a = str(event_a.get("flight_number") or "").replace(" ", "").upper()
    fn_b = str(event_b.get("flight_number") or "").replace(" ", "").upper()
    op_a = str(event_a.get("operating_flight_number") or "").replace(" ", "").upper()
    op_b = str(event_b.get("operating_flight_number") or "").replace(" ", "").upper()

    fn_match = False
    is_codeshare = False
    if fn_a and fn_b and fn_a == fn_b:
        fn_match = True
    elif (fn_a and op_b and fn_a == op_b) or (fn_b and op_a and fn_b == op_a) or (op_a and op_b and op_a == op_b):
        fn_match = True
        is_codeshare = True

    if not fn_match:
        return {
            "can_merge": False,
            "match_status": "MISMATCH_FLIGHT_NUMBER",
            "confidence_score": 0.0,
            "conflict_reason": f"Different flight numbers: {fn_a} vs {fn_b}",
            "time_diff_minutes": None
        }

    # Airframe conflict check
    reg_a = str(event_a.get("aircraft_registration") or "").strip().upper()
    reg_b = str(event_b.get("aircraft_registration") or "").strip().upper()
    if reg_a and reg_b and reg_a != reg_b:
        return {
            "can_merge": False,
            "match_status": "CONFLICT_REGISTRATION",
            "confidence_score": 0.0,
            "conflict_reason": f"Conflicting aircraft registrations: {reg_a} vs {reg_b}",
            "time_diff_minutes": None
        }

    hex_a = str(event_a.get("aircraft_icao24") or "").strip().upper()
    hex_b = str(event_b.get("aircraft_icao24") or "").strip().upper()
    if hex_a and hex_b and hex_a != hex_b:
        return {
            "can_merge": False,
            "match_status": "CONFLICT_ICAO24",
            "confidence_score": 0.0,
            "conflict_reason": f"Conflicting aircraft ICAO24 hex: {hex_a} vs {hex_b}",
            "time_diff_minutes": None
        }

    # Carrier compatibility check
    carr_a = str(event_a.get("operating_carrier") or event_a.get("airline_name") or "").strip().lower()
    carr_b = str(event_b.get("operating_carrier") or event_b.get("airline_name") or "").strip().lower()
    if carr_a and carr_b and not is_codeshare:
        def norm_carr(c):
            c = re.sub(r'\(.*?\)', '', c).lower()
            for w in ("airlines", "airline", "airways", "airway", "aviation", "lines", "line", "air"):
                c = c.replace(w, "")
            return c.replace(" ", "").strip()
        nc_a = norm_carr(carr_a)
        nc_b = norm_carr(carr_b)

        # Check known ACMI wet-lease relationships (e.g. Dan Air operating for Cham Wings / Fly Cham)
        is_acmi = False
        if (fn_a.startswith("FYC") or fn_b.startswith("FYC")) and any("dan" in c for c in (nc_a, nc_b)) and any("cham" in c for c in (nc_a, nc_b)):
            is_acmi = True

        if nc_a and nc_b and not is_acmi:
            if nc_a not in nc_b and nc_b not in nc_a:
                return {
                    "can_merge": False,
                    "match_status": "CONFLICT_CARRIER",
                    "confidence_score": 0.0,
                    "conflict_reason": f"Conflicting operating carriers: '{carr_a}' vs '{carr_b}'",
                    "time_diff_minutes": None
                }

    # Temporal reference time comparison
    if mtype_a == "arrival":
        ref_a = event_a.get("scheduled_arr_time") or event_a.get("actual_arr_time") or event_a.get("estimated_arr_time") or event_a.get("scheduled_dep_time") or event_a.get("actual_dep_time") or event_a.get("estimated_dep_time")
        ref_b = event_b.get("scheduled_arr_time") or event_b.get("actual_arr_time") or event_b.get("estimated_arr_time") or event_b.get("scheduled_dep_time") or event_b.get("actual_dep_time") or event_b.get("estimated_dep_time")
    else:
        ref_a = event_a.get("scheduled_dep_time") or event_a.get("actual_dep_time") or event_a.get("estimated_dep_time") or event_a.get("scheduled_arr_time") or event_a.get("actual_arr_time") or event_a.get("estimated_arr_time")
        ref_b = event_b.get("scheduled_dep_time") or event_b.get("actual_dep_time") or event_b.get("estimated_dep_time") or event_b.get("scheduled_arr_time") or event_b.get("actual_arr_time") or event_b.get("estimated_arr_time")

    if not ref_a or not ref_b:
        return {
            "can_merge": False,
            "match_status": "POTENTIAL_MATCH_LACKS_TIME",
            "confidence_score": 0.40,
            "conflict_reason": "Missing scheduled or actual timestamp anchor",
            "time_diff_minutes": None
        }

    try:
        t1 = datetime.fromisoformat(ref_a.replace("Z", "+00:00"))
        t2 = datetime.fromisoformat(ref_b.replace("Z", "+00:00"))
        diff_minutes = abs((t1 - t2).total_seconds()) / 60.0
    except Exception:
        return {
            "can_merge": False,
            "match_status": "POTENTIAL_MATCH_INVALID_TIME",
            "confidence_score": 0.30,
            "conflict_reason": f"Invalid ISO timestamp format: '{ref_a}' or '{ref_b}'",
            "time_diff_minutes": None
        }

    if diff_minutes <= max_window_minutes:
        conf = 1.0 if (reg_a and reg_b and reg_a == reg_b) or diff_minutes <= 15.0 else 0.95
        return {
            "can_merge": True,
            "match_status": "CONFIRMED_MATCH",
            "confidence_score": conf,
            "conflict_reason": None,
            "time_diff_minutes": round(diff_minutes, 1)
        }
    elif max_window_minutes < diff_minutes <= ambiguous_window_minutes:
        return {
            "can_merge": False,
            "match_status": "POTENTIAL_MATCH_AMBIGUOUS_DELTA",
            "confidence_score": 0.50,
            "conflict_reason": f"Time difference {round(diff_minutes, 1)}m is in ambiguous range ({max_window_minutes}m-{ambiguous_window_minutes}m)",
            "time_diff_minutes": round(diff_minutes, 1)
        }
    else:
        return {
            "can_merge": False,
            "match_status": "SPLIT_DISTINCT_LEG",
            "confidence_score": 0.10,
            "conflict_reason": f"Time difference {round(diff_minutes, 1)}m exceeds {ambiguous_window_minutes}m (distinct leg)",
            "time_diff_minutes": round(diff_minutes, 1)
        }

# 4. Strict Deduplication Pipeline with Full Audit Logging
def deduplicate_with_audit(
    events: List[Dict[str, Any]],
    max_window_minutes: float = 60.0,
    ambiguous_window_minutes: float = 180.0
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
    """
    Conservative deduplication:
    - Partitioned by airport_id and movement_type (arrivals and departures are NEVER merged).
    - Matches identical normalized flight number on the same local date using evaluate_cross_source_match.
    - Evaluates carrier, airframe registration, and temporal reference window.
    """
    audit_log = []
    stats = {
        "total_raw_events": len(events),
        "merged_verified_count": 0,
        "flagged_ambiguous_count": 0,
        "split_distinct_leg_count": 0,
    }

    # Group events by (airport_id, movement_type, flight_number, flight_date)
    grouped = {}
    for e in events:
        grp_key = (e["airport_id"], e["movement_type"], e["flight_number"], e["flight_date"])
        grouped.setdefault(grp_key, []).append(e)

    canonical_events = []

    for grp_key, grp_list in grouped.items():
        if len(grp_list) == 1:
            canonical_events.append(grp_list[0])
            continue

        # Multiple records for same flight number, direction, date, airport
        merged_clusters = []
        for cand in grp_list:
            cand_raw_time = cand.get("raw_scheduled_arr_time") or cand.get("raw_actual_arr_time") or cand.get("raw_estimated_arr_time") or cand.get("raw_scheduled_dep_time") or cand.get("raw_actual_dep_time") or cand.get("raw_estimated_dep_time")

            placed = False
            for cluster in merged_clusters:
                lead = cluster["lead"]
                lead_raw_time = lead.get("raw_scheduled_arr_time") or lead.get("raw_actual_arr_time") or lead.get("raw_estimated_arr_time") or lead.get("raw_scheduled_dep_time") or lead.get("raw_actual_dep_time") or lead.get("raw_estimated_dep_time")

                match_res = evaluate_cross_source_match(lead, cand, max_window_minutes, ambiguous_window_minutes)

                if match_res["can_merge"]:
                    # Verified merge
                    stats["merged_verified_count"] += 1
                    diff_minutes = match_res["time_diff_minutes"]
                    audit_log.append({
                        "canonical_event_id": lead["event_id"],
                        "airport_id": lead["airport_id"],
                        "flight_number": lead["flight_number"],
                        "movement_type": lead["movement_type"],
                        "flight_date": lead["flight_date"],
                        "source_a": lead["source"],
                        "source_a_record_id": lead["source_record_id"],
                        "source_a_raw_time": lead_raw_time,
                        "source_b": cand["source"],
                        "source_b_record_id": cand["source_record_id"],
                        "source_b_raw_time": cand_raw_time,
                        "time_difference_minutes": diff_minutes,
                        "matching_rule": f"CONFIRMED_MATCH_CONF_{match_res['confidence_score']}",
                        "resolution_status": "MERGED_VERIFIED",
                    })

                    # Merge static metadata fields
                    for field in ("aircraft_registration", "aircraft_model", "aircraft_icao24",
                                  "airline_name", "airline_iata", "airline_icao",
                                  "connected_airport_iata", "connected_airport_icao",
                                  "connected_airport_name", "connected_country", "connected_city"):
                        if not lead.get(field) and cand.get(field):
                            lead[field] = cand[field]
                        elif cand.get(field) and "flightradar24" in cand.get("source", "").lower() and field in ("aircraft_registration", "aircraft_icao24", "aircraft_model"):
                            lead[field] = cand[field]

                    # Merge actual arrival timestamps using source evidence priority
                    lead_arr_prio = get_timestamp_priority(lead.get("source"), bool(lead.get("actual_arr_time")))
                    cand_arr_prio = get_timestamp_priority(cand.get("source"), bool(cand.get("actual_arr_time")))
                    if cand.get("actual_arr_time") and (cand_arr_prio > lead_arr_prio or not lead.get("actual_arr_time")):
                        lead["actual_arr_time"] = cand["actual_arr_time"]
                        lead["raw_actual_arr_time"] = cand.get("raw_actual_arr_time")

                    # Merge actual departure timestamps using source evidence priority
                    lead_dep_prio = get_timestamp_priority(lead.get("source"), bool(lead.get("actual_dep_time")))
                    cand_dep_prio = get_timestamp_priority(cand.get("source"), bool(cand.get("actual_dep_time")))
                    if cand.get("actual_dep_time") and (cand_dep_prio > lead_dep_prio or not lead.get("actual_dep_time")):
                        lead["actual_dep_time"] = cand["actual_dep_time"]
                        lead["raw_actual_dep_time"] = cand.get("raw_actual_dep_time")

                    # Merge estimated arrival timestamps
                    if not lead.get("estimated_arr_time") and cand.get("estimated_arr_time"):
                        lead["estimated_arr_time"] = cand["estimated_arr_time"]
                        lead["raw_estimated_arr_time"] = cand.get("raw_estimated_arr_time")

                    # Merge estimated departure timestamps
                    if not lead.get("estimated_dep_time") and cand.get("estimated_dep_time"):
                        lead["estimated_dep_time"] = cand["estimated_dep_time"]
                        lead["raw_estimated_dep_time"] = cand.get("raw_estimated_dep_time")

                    # Upgrade status: confirmed physical operation overrides scheduled/active
                    cand_st = cand.get("flight_status")
                    lead_st = lead.get("flight_status")
                    status_prio = {
                        "cancelled": 5,
                        "diverted": 5,
                        "departed": 4,
                        "landed": 4,
                        "active": 2,
                        "scheduled": 1,
                        "unknown": 0,
                    }
                    if status_prio.get(cand_st, 0) > status_prio.get(lead_st, 0):
                        lead["flight_status"] = cand_st
                    elif lead.get("movement_type") == "departure" and lead_st == "landed" and cand_st == "departed":
                        lead["flight_status"] = "departed"

                    if lead["source"] != cand["source"] and cand["source"] not in lead["source"]:
                        lead["source"] = f"{lead['source']}+{cand['source']}"
                    lead["quality_flags"] = "merged_cross_source_verified"

                    # Record nature and operating carrier inheritance
                    if cand.get("record_nature") == "physical_movement" or lead.get("record_nature") == "physical_movement":
                        lead["record_nature"] = "physical_movement"
                    elif cand.get("record_nature") == "marketing_codeshare" or lead.get("record_nature") == "marketing_codeshare":
                        lead["record_nature"] = "marketing_codeshare"
                    elif cand.get("record_nature") == "unverified_movement" or lead.get("record_nature") == "unverified_movement":
                        lead["record_nature"] = "unverified_movement"

                    if not lead.get("operating_flight_number") and cand.get("operating_flight_number"):
                        lead["operating_flight_number"] = cand["operating_flight_number"]
                    if not lead.get("operating_carrier") and cand.get("operating_carrier"):
                        lead["operating_carrier"] = cand["operating_carrier"]

                    placed = True
                    break
                elif match_res["match_status"] in ("POTENTIAL_MATCH_AMBIGUOUS_DELTA", "POTENTIAL_MATCH_LACKS_TIME"):
                    stats["flagged_ambiguous_count"] += 1
                    audit_log.append({
                        "canonical_event_id": lead["event_id"],
                        "airport_id": lead["airport_id"],
                        "flight_number": lead["flight_number"],
                        "movement_type": lead["movement_type"],
                        "flight_date": lead["flight_date"],
                        "source_a": lead["source"],
                        "source_a_record_id": lead["source_record_id"],
                        "source_a_raw_time": lead_raw_time,
                        "source_b": cand["source"],
                        "source_b_record_id": cand["source_record_id"],
                        "source_b_raw_time": cand_raw_time,
                        "time_difference_minutes": match_res["time_diff_minutes"],
                        "matching_rule": match_res["match_status"],
                        "resolution_status": "FLAGGED_AMBIGUOUS_KEPT_SEPARATE",
                    })
                elif match_res["match_status"] == "SPLIT_DISTINCT_LEG":
                    stats["split_distinct_leg_count"] += 1
                    audit_log.append({
                        "canonical_event_id": lead["event_id"],
                        "airport_id": lead["airport_id"],
                        "flight_number": lead["flight_number"],
                        "movement_type": lead["movement_type"],
                        "flight_date": lead["flight_date"],
                        "source_a": lead["source"],
                        "source_a_record_id": lead["source_record_id"],
                        "source_a_raw_time": lead_raw_time,
                        "source_b": cand["source"],
                        "source_b_record_id": cand["source_record_id"],
                        "source_b_raw_time": cand_raw_time,
                        "time_difference_minutes": match_res["time_diff_minutes"],
                        "matching_rule": "TIME_DIFF_GT_180M",
                        "resolution_status": "SPLIT_DISTINCT_LEG",
                    })

            if not placed:
                merged_clusters.append({"lead": cand})

        for cluster in merged_clusters:
            canonical_events.append(cluster["lead"])

    # Ensure all canonical events have strictly unique event_ids
    seen_ids = set()
    for idx, ce in enumerate(canonical_events):
        if ce["event_id"] in seen_ids:
            ce["event_id"] = f"{ce['event_id']}_{idx}"
        seen_ids.add(ce["event_id"])

    canonical_events.sort(key=lambda x: (x["airport_id"], x["flight_date"], x["movement_type"], x["flight_number"]))
    return canonical_events, audit_log, stats

# 5. Master Ingestion Loader for All Syrian Airports
def load_and_normalize_all_events() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    all_raw_events = []

    # A. Official Damascus Airport Portal (damairport.gov.sy)
    dam_off_file = RAW_DATA_DIR / "damairport_official_flights_raw.json"
    if dam_off_file.exists():
        with open(dam_off_file, "r", encoding="utf-8") as f:
            d = json.load(f)
            flist = d.get("flights", []) if isinstance(d, dict) else d
            norm = normalize_official_portal_flights(flist, "DAM")
            all_raw_events.extend(norm)

    # B. Official Aleppo Airport Portal (alpairport.gov.sy)
    alp_off_file = RAW_DATA_DIR / "alpairport_official_flights_raw.json"
    if alp_off_file.exists():
        with open(alp_off_file, "r", encoding="utf-8") as f:
            d = json.load(f)
            flist = d.get("flights", []) if isinstance(d, dict) else d
            norm = normalize_official_portal_flights(flist, "ALP")
            all_raw_events.extend(norm)

    # C. AviationStack DAM Live Data
    as_dep_file = RAW_DATA_DIR / "aviationstack_dam_departures_raw.json"
    as_arr_file = RAW_DATA_DIR / "aviationstack_dam_arrivals_raw.json"
    if as_dep_file.exists():
        with open(as_dep_file, "r", encoding="utf-8") as f:
            d = json.load(f)
            all_raw_events.extend(normalize_aviationstack(d.get("data", []), "departure", "DAM"))
    if as_arr_file.exists():
        with open(as_arr_file, "r", encoding="utf-8") as f:
            d = json.load(f)
            all_raw_events.extend(normalize_aviationstack(d.get("data", []), "arrival", "DAM"))

    # D. Flightradar24 for Syrian Airports (DAM, ALP, DEZ, etc.)
    for code, apt_id in [("dam", "DAM"), ("alp", "ALP"), ("dez", "DEZ"), ("ltk", "LTK"), ("kac", "KAC")]:
        fr_dep = RAW_DATA_DIR / f"flightradar24_{code}_departures_raw.json"
        fr_arr = RAW_DATA_DIR / f"flightradar24_{code}_arrivals_raw.json"
        if fr_dep.exists():
            with open(fr_dep, "r", encoding="utf-8") as f:
                d = json.load(f)
                all_raw_events.extend(normalize_flightradar24(d, "departure", apt_id))
        if fr_arr.exists():
            with open(fr_arr, "r", encoding="utf-8") as f:
                d = json.load(f)
                all_raw_events.extend(normalize_flightradar24(d, "arrival", apt_id))

    # Run conservative deduplication with full audit logging
    canonical_events, audit_log, stats = deduplicate_with_audit(all_raw_events)
    return canonical_events, audit_log, stats
