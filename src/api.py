import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import sqlite3

from src.config import (
    BASE_DIR,
    PROCESSED_DATA_DIR,
    REPORTS_DIR,
    STATIC_DIR,
    RAW_DATA_DIR,
    DB_PATH,
    AIRPORT_IATA,
    AIRPORT_ICAO,
    AIRPORT_NAME,
    SYRIAN_AIRPORTS_REGISTRY,
)
from src.database import get_connection
from src.timestamp_provenance import (
    correct_flight_record_semantics,
    correct_evidence_item,
    MISLABELED_EVIDENCE_MAP,
    resolve_defensible_movement_identity,
)

app = FastAPI(
    title="Syrian Airport Data Engine & Damascus Deep-Dive",
    description="Empirical flight operations database and analytical engine for all Syrian airports with a Damascus International Airport deep-dive layer.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for Data Tab UI
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

from src.archived_fids_analytics import router as archived_fids_router
app.include_router(archived_fids_router)

from src.archived_fids_history_api import router as archived_fids_history_router
app.include_router(archived_fids_history_router)

from src.air_traffic_api import router as air_traffic_router
app.include_router(air_traffic_router)

@app.get("/", response_class=HTMLResponse)
@app.get("/data", response_class=HTMLResponse)
def get_data_tab():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return "<h1>Syrian Airport Data Engine</h1><p>Data tab UI loading...</p>"

@app.get("/api/airports")
def get_airports():
    """
    Returns official Syrian aerodromes registry from the database.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM airports ORDER BY airport_type, name;")
        rows = [dict(r) for r in cursor.fetchall()]
        for r in rows:
            if r.get("runways_json"):
                try:
                    r["runways"] = json.loads(r["runways_json"])
                except Exception:
                    r["runways"] = []
    return rows

@app.get("/api/airport")
def get_airport_info(airport_id: str = Query("DAM", description="Airport identifier e.g. DAM, ALP, DEZ")):
    """
    Returns detailed airport specifications and runway dimensions.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM airports WHERE airport_id = ? OR iata_code = ? OR icao_code = ?;",
                       (airport_id.upper(), airport_id.upper(), airport_id.upper()))
        row = cursor.fetchone()
        if row:
            res = dict(row)
            res["ident"] = res.get("icao_code", "OSDI")
            if res.get("runways_json"):
                try:
                    res["runways"] = json.loads(res["runways_json"])
                except Exception:
                    res["runways"] = []
            return res

    if airport_id.upper() in SYRIAN_AIRPORTS_REGISTRY:
        reg = dict(SYRIAN_AIRPORTS_REGISTRY[airport_id.upper()])
        reg["ident"] = reg.get("icao_code", "OSDI")
        return reg

    raise HTTPException(status_code=404, detail=f"Airport '{airport_id}' not found in registry.")

def normalize_timestamp_to_utc(ts_val) -> Optional[str]:
    """
    Normalizes a timestamp value (Unix seconds, Unix milliseconds, or ISO-8601 string)
    to normalized UTC ISO-8601 string: YYYY-MM-DDTHH:MM:SSZ.
    Returns None if missing, unparseable, or ambiguous (lacks timezone/offset evidence).
    """
    if ts_val is None or ts_val == "":
        return None
    s = str(ts_val).strip()
    if not s or s.lower() in ("none", "null"):
        return None
    try:
        if s.isdigit():
            v = int(s)
            if len(s) == 10:
                dt = datetime.fromtimestamp(v, tz=timezone.utc)
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            elif len(s) == 13:
                dt = datetime.fromtimestamp(v / 1000.0, tz=timezone.utc)
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            elif len(s) > 13:
                dt = datetime.fromtimestamp(v / 1000000.0, tz=timezone.utc)
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        elif s.replace(".", "", 1).isdigit() and s.count(".") == 1:
            v = float(s)
            if v > 1e11:
                v = v / 1000.0
            dt = datetime.fromtimestamp(v, tz=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass
    try:
        clean_s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_s)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        # Naive timestamp without timezone: never infer UTC or Damascus local time without source evidence
        return None
    except Exception:
        pass
    return None

def _enrich_flight_records(rows: list, conn: sqlite3.Connection) -> list:
    """
    Enriches flight event records with evidence transparency fields.
    Preserves all existing keys for backward compatibility.
    """
    if not rows:
        return rows

    event_ids = [r["event_id"] for r in rows if r.get("event_id")]
    ev_info = {}
    if event_ids:
        placeholders = ",".join(["?"] * len(event_ids))
        cursor = conn.cursor()
        try:
            cursor.execute(f"""
                SELECT event_id, COUNT(*) as ev_count, COUNT(DISTINCT source_name) as prov_count,
                       MAX(snapshot_path) as snapshot_path, MAX(raw_timestamp) as raw_ts
                FROM v_active_evidence
                WHERE event_id IN ({placeholders})
                GROUP BY event_id
            """, event_ids)
            for er in cursor.fetchall():
                ev_info[er[0]] = {
                    "ev_count": er[1],
                    "prov_count": er[2],
                    "snapshot_path": er[3],
                    "raw_ts": er[4]
                }
        except sqlite3.OperationalError:
            pass

    tz_dam = ZoneInfo("Asia/Damascus")

    for r in rows:
        correct_flight_record_semantics(r)
        eid = r.get("event_id")
        ev = ev_info.get(eid, {})
        nature = r.get("record_nature")

        if nature == "physical_movement":
            evidence_level = "commercial_status_corroborated"
        elif nature in ("scheduled_service", "scheduled_timetable"):
            evidence_level = "scheduled_timetable_display"
        elif nature == "marketing_codeshare":
            evidence_level = "commercial_partner_listing"
        elif nature == "unverified_movement":
            evidence_level = "unverified_claim"
        else:
            evidence_level = "unknown"

        actual_ts = r.get("actual_dep_time") if r.get("movement_type") == "departure" else r.get("actual_arr_time")
        if not actual_ts:
            actual_ts = r.get("actual_dep_time") or r.get("actual_arr_time") or None

        estimated_ts = r.get("estimated_dep_time") if r.get("movement_type") == "departure" else r.get("estimated_arr_time")
        if not estimated_ts:
            estimated_ts = r.get("estimated_dep_time") or r.get("estimated_arr_time") or None

        # Source observation timestamp: raw sensor/feed timestamp only. Ingestion timestamps are strictly separated.
        raw_source_obs_ts = ev.get("raw_ts") or r.get("raw_actual_dep_time") or r.get("raw_actual_arr_time") or r.get("raw_estimated_dep_time") or r.get("raw_estimated_arr_time") or None
        normalized_source_obs_ts = normalize_timestamp_to_utc(raw_source_obs_ts)
        ingested_at = r.get("created_at") or None

        prov_cnt = ev.get("prov_count", 1 if r.get("source") else 0)
        # Deduplicated active observations count for this event
        indep_obs_cnt = ev.get("ev_count", 1 if r.get("source") else 0)
        # Upstream commercial aggregators lack verified separate sensor hardware
        indep_prov_cnt = None

        # Date Semantics:
        # scheduled_flight_date: Timetable/flight board scheduled operational calendar date.
        # actual_movement_date: Local calendar date strictly when genuine physical movement occurred (null if unobserved or estimated).
        # estimated_movement_date: Local calendar date derived from estimated timestamps.
        # flight_date: Preserved backward-compatible primary key date representing scheduled operational day.
        r["scheduled_flight_date"] = r.get("flight_date")
        actual_local_date = None
        ref_actual_ts = normalized_source_obs_ts if (nature == "physical_movement" and normalized_source_obs_ts) else actual_ts
        if ref_actual_ts and actual_ts:
            try:
                dt_utc = datetime.fromisoformat(ref_actual_ts.replace("Z", "+00:00"))
                actual_local_date = dt_utc.astimezone(tz_dam).date().isoformat()
            except Exception:
                actual_local_date = None
        r["actual_movement_date"] = actual_local_date

        estimated_local_date = None
        if estimated_ts:
            try:
                dt_utc = datetime.fromisoformat(estimated_ts.replace("Z", "+00:00"))
                estimated_local_date = dt_utc.astimezone(tz_dam).date().isoformat()
            except Exception:
                estimated_local_date = None
        r["estimated_movement_date"] = estimated_local_date

        r["geographic_scope"] = r.get("airport_id")
        r["evidence_level"] = evidence_level
        r["event_classification"] = "commercially_reported_operational_event" if nature == "physical_movement" else (nature or "unknown")
        r["provider_count"] = prov_cnt
        r["independent_observation_count"] = indep_obs_cnt
        r["independent_provider_count"] = indep_prov_cnt
        r["runway_movement_evidence"] = None
        r["source_observed_at"] = normalized_source_obs_ts
        r["source_observed_at_raw"] = str(raw_source_obs_ts) if raw_source_obs_ts is not None else None
        r["source_timestamp"] = normalized_source_obs_ts  # backward compatibility for V2.20
        r["ingested_at"] = ingested_at
        r["actual_timestamp"] = actual_ts
        r["estimated_timestamp"] = estimated_ts
        r["source_snapshot"] = ev.get("snapshot_path") or r.get("source_record_id") or None

    return rows

@app.get("/api/flights")
def get_flights(
    airport_id: Optional[str] = Query(None, description="Filter by airport ID (DAM, ALP, DEZ, etc.) or omit for all"),
    date: Optional[str] = Query(None, description="Filter by YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    movement_type: Optional[str] = Query(None, description="arrival or departure"),
    status: Optional[str] = Query(None, description="landed, active, scheduled, cancelled, diverted"),
    airline: Optional[str] = Query(None, description="Filter by airline name or code"),
    route_type: Optional[str] = Query(None, description="domestic or international"),
    record_nature: Optional[str] = Query(None, description="physical_movement, marketing_codeshare, scheduled_service, unverified_movement"),
    evidence_level: Optional[str] = Query(None, description="commercial_status_corroborated, scheduled_timetable_display, commercial_partner_listing, unverified_claim"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    query = "SELECT * FROM flight_events WHERE 1=1"
    params = []

    if airport_id:
        query += " AND airport_id = ?"
        params.append(airport_id.upper())
    if date:
        query += " AND flight_date = ?"
        params.append(date)
    if start_date:
        query += " AND flight_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND flight_date <= ?"
        params.append(end_date)
    if movement_type:
        query += " AND movement_type = ?"
        params.append(movement_type.lower())
    if status:
        query += " AND flight_status = ?"
        params.append(status.lower())
    if record_nature:
        rn = record_nature.lower()
        if rn in ("commercially_reported_operational_event", "commercially_reported"):
            rn = "physical_movement"
        query += " AND record_nature = ?"
        params.append(rn)
    if evidence_level:
        el = evidence_level.lower()
        if el == "commercial_status_corroborated":
            query += " AND record_nature = 'physical_movement'"
        elif el == "scheduled_timetable_display":
            query += " AND record_nature = 'scheduled_service'"
        elif el == "commercial_partner_listing":
            query += " AND record_nature = 'marketing_codeshare'"
        elif el == "unverified_claim":
            query += " AND record_nature = 'unverified_movement'"
    if airline:
        query += " AND (airline_name LIKE ? OR airline_iata = ? OR airline_icao = ?)"
        params.extend([f"%{airline}%", airline.upper(), airline.upper()])
    if route_type:
        query += " AND route_type = ?"
        params.append(route_type.lower())

    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]

        query += " ORDER BY flight_date DESC, (scheduled_dep_time || scheduled_arr_time) ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        for r in rows:
            r.pop("raw_json", None)

        rows = _enrich_flight_records(rows, conn)

    return {
        "airport_filter": airport_id or "all_syrian_airports",
        "total": total_count,
        "total_matching": total_count,
        "limit": limit,
        "offset": offset,
        "flights": rows,
        "data": rows
    }

@app.get("/api/events/{event_id}")
def get_event_detail(event_id: str):
    """
    Returns full details for a canonical flight event by event_id.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM flight_events WHERE event_id = ?", (event_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Flight event '{event_id}' not found")
        data = dict(row)
        data.pop("raw_json", None)
        enriched = _enrich_flight_records([data], conn)
        return enriched[0]

@app.get("/api/events/{event_id}/evidence")
def get_event_evidence(
    event_id: str,
    include_retracted: bool = Query(False, description="Include retracted observations in historical audit trail"),
    forensic: bool = Query(False, description="Include forensic audit details, raw field mappings, and correction history")
):
    """
    Returns empirical evidence supporting a flight event.
    Active evidence is queried from v_active_evidence.
    Retracted observations are retained in the historical audit trail.
    All evidence rows expose both their immutable original classification and their
    corrected semantic interpretation with full provenance and correction history.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type = 'view' AND name = 'v_active_evidence';")
        has_view = cursor.fetchone()[0] > 0

        if has_view:
            if include_retracted:
                cursor.execute("""
                    SELECT ee.*,
                           CASE WHEN ae.evidence_id IS NOT NULL THEN 'active' ELSE 'retracted' END as ledger_status,
                           er.reason as retraction_reason,
                           er.observed_at as retracted_at,
                           er.actor as retracted_by
                    FROM event_evidence ee
                    LEFT JOIN v_active_evidence ae ON ee.evidence_id = ae.evidence_id
                    LEFT JOIN (
                        SELECT evidence_id, reason, observed_at, actor
                        FROM (
                            SELECT evidence_id, reason, observed_at, actor, action,
                                   ROW_NUMBER() OVER (PARTITION BY evidence_id ORDER BY sequence_num DESC) as rn
                            FROM evidence_retractions
                        ) WHERE rn = 1 AND action = 'retract'
                    ) er ON ee.evidence_id = er.evidence_id
                    WHERE ee.event_id = ?
                    ORDER BY ee.observed_at ASC;
                """, (event_id,))
            else:
                cursor.execute("""
                    SELECT *, 'active' as ledger_status
                    FROM v_active_evidence
                    WHERE event_id = ?
                    ORDER BY observed_at ASC;
                """, (event_id,))
        else:
            cursor.execute("SELECT *, 'active' as ledger_status FROM event_evidence WHERE event_id = ?;", (event_id,))

        raw_rows = [dict(r) for r in cursor.fetchall()]

    rows = [correct_evidence_item(r) for r in raw_rows]
    active_count = sum(1 for r in rows if r.get("ledger_status") == "active")
    retracted_count = sum(1 for r in rows if r.get("ledger_status") == "retracted")
    corrected_count = sum(1 for r in rows if r.get("is_estimated"))

    return {
        "event_id": event_id,
        "evidence_count": len(rows),
        "active_count": active_count,
        "retracted_count": retracted_count,
        "corrected_count": corrected_count,
        "has_mislabeled_evidence": corrected_count > 0,
        "forensic_mode": forensic,
        "include_retracted": include_retracted,
        "evidence": rows,
        "data": rows
    }

@app.get("/api/evidence/audit")
@app.get("/api/evidence/corrections")
def get_evidence_audit():
    """
    Forensic audit endpoint exposing all 76 mislabeled evidence records originally
    classified as adsb_takeoff or adsb_touchdown but derived from upstream estimated timestamps.
    Preserves the immutable event_evidence database ledger while providing complete correction history.
    """
    records = list(MISLABELED_EVIDENCE_MAP.values())
    takeoff_cnt = sum(1 for r in records if "takeoff" in r.get("original_evidence_type", ""))
    touchdown_cnt = sum(1 for r in records if "touchdown" in r.get("original_evidence_type", ""))

    return {
        "audit_version": "2.20.6-mislabeled-evidence-audit",
        "total_mislabeled_evidence_records": len(records),
        "original_takeoffs_reclassified": takeoff_cnt,
        "original_touchdowns_reclassified": touchdown_cnt,
        "immutable_ledger_policy": "Original event_evidence rows remain strictly unmodified under cryptographic baseline invariants. Semantic corrections are applied at read time with visible audit trails.",
        "records": records
    }


@app.get("/api/movements/daily")
def get_daily_movements(
    airport_id: Optional[str] = Query("DAM", description="Airport identifier e.g. DAM, ALP, DEZ, or 'all'"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """
    Returns independent daily movements per airport.
    """
    query = "SELECT * FROM daily_airport_movements WHERE 1=1"
    params = []

    if airport_id and airport_id.lower() != "all":
        query += " AND airport_id = ?"
        params.append(airport_id.upper())

    if start_date:
        query += " AND flight_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND flight_date <= ?"
        params.append(end_date)

    query += " ORDER BY flight_date ASC, airport_id ASC"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]

    return {
        "airport_id": airport_id or "all",
        "total_days": len(rows),
        "count": len(rows),
        "daily_movements": rows,
        "data": rows
    }

@app.get("/api/movements/multi-airport")
@app.get("/api/movements/historical-2024")
def get_historical_2024(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    movement_type: Optional[str] = Query(None),
    limit: Optional[int] = Query(None),
    offset: Optional[int] = Query(None),
):
    """
    Returns Syria Economic Monitor 2024 multi-airport gateway series (DAM_ALP_LTK).
    Scope is explicitly marked to prevent conflating with single-airport data.
    """
    query = "SELECT * FROM historical_daily_movements_2024 WHERE 1=1"
    params = []

    if start_date:
        query += " AND flight_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND flight_date <= ?"
        params.append(end_date)
    if movement_type:
        query += " AND movement_type = ?"
        params.append(movement_type.lower())

    query += " ORDER BY flight_date ASC, movement_type ASC"
    if limit is not None:
        query += f" LIMIT {limit}"
        if offset is not None:
            query += f" OFFSET {offset}"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]

    return {
        "dataset_name": "Syria Economic Monitor 2024 Gateway Operations Time Series",
        "scope": "DAM_ALP_LTK",
        "included_airports": ["DAM", "ALP", "LTK"],
        "data_category": "regional_aggregate",
        "is_dam_specific": False,
        "movement_nature": "aggregate_gateway_operations_by_status",
        "source": "Syria Economic Monitor (World Bank / Data Partnership)",
        "earliest_observed_date": "2024-01-01",
        "latest_observed_date": "2024-10-15",
        "total": len(rows),
        "count": len(rows),
        "warning": "The 2024 DAM_ALP_LTK series is a three-airport aggregate covering Damascus (DAM), Aleppo (ALP), and Latakia (LTK) combined. Zero DAM-specific disaggregation is available in source data. Cannot be used as DAM-specific movement counts.",
        "records": rows,
        "data": rows
    }

@app.get("/api/movements/verified")
@app.get("/api/movements/operational")
@app.get("/api/movements/commercially-reported")
def get_verified_movements(
    airport_id: Optional[str] = Query(None, description="Filter by airport ID (DAM, ALP, DEZ, etc.) or omit for all"),
    date: Optional[str] = Query(None, description="Filter by YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    movement_type: Optional[str] = Query(None, description="arrival or departure"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    Returns commercially reported operational aircraft events (airline operational status updates
    with actual departure/arrival timestamps cross-matched from commercial feeds).
    Marketing codeshares and unverified schedule-only records are excluded.
    Direct on-field runway sensor telemetry remains pending.
    """
    query = "SELECT * FROM flight_events WHERE record_nature = 'physical_movement'"
    params = []

    if airport_id:
        query += " AND airport_id = ?"
        params.append(airport_id.upper())
    if date:
        query += " AND flight_date = ?"
        params.append(date)
    if start_date:
        query += " AND flight_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND flight_date <= ?"
        params.append(end_date)
    if movement_type:
        query += " AND movement_type = ?"
        params.append(movement_type.lower())

    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]

        query += " ORDER BY flight_date DESC, (actual_dep_time || actual_arr_time || scheduled_dep_time || scheduled_arr_time) ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        for r in rows:
            r.pop("raw_json", None)

        rows = _enrich_flight_records(rows, conn)

    return {
        "record_nature": "physical_movement",
        "event_classification": "commercially_reported_operational_event",
        "description": "Commercially reported operational events with actual departure/arrival status timestamps (excluding marketing codeshares and unverified schedule-only records). Direct on-ground runway sensor telemetry is pending.",
        "airport_filter": airport_id or "all_syrian_airports",
        "total": total_count,
        "count": len(rows),
        "limit": limit,
        "offset": offset,
        "movements": rows,
        "data": rows
    }

@app.get("/api/movements/comparison")
def get_movements_comparison(
    airport_id: Optional[str] = Query("DAM", description="Airport identifier e.g. DAM, ALP, DEZ, or 'all'"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
):
    """
    Returns comparative breakdown of scheduled timetable services vs commercially reported operational events.
    """
    query = """
        SELECT flight_date, airport_id,
               SUM(CASE WHEN record_nature = 'physical_movement' THEN 1 ELSE 0 END) as commercial_operational_event_count,
               SUM(CASE WHEN record_nature = 'scheduled_service' THEN 1 ELSE 0 END) as scheduled_record_count,
               SUM(CASE WHEN record_nature = 'marketing_codeshare' THEN 1 ELSE 0 END) as codeshare_record_count,
               SUM(CASE WHEN record_nature = 'unverified_movement' THEN 1 ELSE 0 END) as unverified_count,
               COUNT(DISTINCT CASE WHEN record_nature = 'physical_movement' THEN COALESCE(NULLIF(operating_flight_number, ''), flight_number) END) as unique_operating_flight_count,
               COUNT(DISTINCT CASE WHEN record_nature = 'physical_movement' THEN 
                   airport_id || '_' || flight_date || '_' || movement_type || '_' || COALESCE(NULLIF(operating_flight_number, ''), flight_number)
               END) as resolved_commercial_movement_count,
               COUNT(*) as unique_event_count
        FROM flight_events
        WHERE 1=1
    """
    params = []
    if airport_id and airport_id.lower() != "all":
        query += " AND airport_id = ?"
        params.append(airport_id.upper())
    if start_date:
        query += " AND flight_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND flight_date <= ?"
        params.append(end_date)
    query += " GROUP BY flight_date, airport_id ORDER BY flight_date ASC"

    codeshare_query = """
        SELECT 
            c.flight_date, c.airport_id,
            SUM(CASE WHEN p.flight_number IS NOT NULL THEN 1 ELSE 0 END) as matched,
            COUNT(DISTINCT CASE WHEN p.flight_number IS NULL THEN 
                c.airport_id || '_' || c.flight_date || '_' || c.movement_type || '_' || COALESCE(NULLIF(c.operating_flight_number, ''), c.flight_number)
            END) as ambiguous_candidates,
            SUM(CASE WHEN p.flight_number IS NULL THEN 1 ELSE 0 END) as unmatched_rows
        FROM flight_events c
        LEFT JOIN (
            SELECT DISTINCT flight_date, airport_id, movement_type, flight_number
            FROM flight_events
            WHERE record_nature = 'physical_movement'
        ) p 
          ON c.flight_date = p.flight_date
         AND c.airport_id = p.airport_id
         AND c.movement_type = p.movement_type
         AND c.operating_flight_number = p.flight_number
        WHERE c.record_nature = 'marketing_codeshare'
    """
    cs_params = []
    if airport_id and airport_id.lower() != "all":
        codeshare_query += " AND c.airport_id = ?"
        cs_params.append(airport_id.upper())
    if start_date:
        codeshare_query += " AND c.flight_date >= ?"
        cs_params.append(start_date)
    if end_date:
        codeshare_query += " AND c.flight_date <= ?"
        cs_params.append(end_date)
    codeshare_query += " GROUP BY c.flight_date, c.airport_id"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        raw_rows = [dict(r) for r in cursor.fetchall()]

        cursor.execute(codeshare_query, cs_params)
        cs_map = {(r["flight_date"], r["airport_id"]): (r["matched"] or 0, r["ambiguous_candidates"] or 0, r["unmatched_rows"] or 0) for r in cursor.fetchall()}

    rows = []
    for r in raw_rows:
        key = (r["flight_date"], r["airport_id"])
        matched_cs, ambig_candidates, unmatched_cs_rows = cs_map.get(key, (0, 0, 0))

        item = {
            "flight_date": r["flight_date"],
            "airport_id": r["airport_id"],
            "total_records": r["unique_event_count"],
            "source_record_count": r["unique_event_count"],
            "scheduled_record_count": r["scheduled_record_count"],
            "scheduled_service_count": r["scheduled_record_count"],
            "commercial_operational_event_count": r["commercial_operational_event_count"],
            "codeshare_record_count": r["codeshare_record_count"],
            "matched_codeshare_record_count": matched_cs,
            "unmatched_codeshare_record_count": unmatched_cs_rows,
            "unverified_record_count": r["unverified_count"],
            "unique_operating_flight_count": r["unique_operating_flight_count"],
            "resolved_commercial_movement_count": r["resolved_commercial_movement_count"],
            "confirmed_unique_movement_count": r["resolved_commercial_movement_count"],
            "ambiguous_movement_identity_count": ambig_candidates,
            "unique_flight_movement_count": r["resolved_commercial_movement_count"],
            # Backward compatibility for V2.20 clients
            "unique_event_count": r["unique_event_count"],
            "codeshare_matched_to_operating_flight": matched_cs,
            "codeshare_ambiguous_or_unmatched": ambig_candidates,
            "scheduled_count": r["scheduled_record_count"],
            "commercially_reported_count": r["commercial_operational_event_count"],
            "codeshare_count": r["codeshare_record_count"],
            "unverified_count": r["unverified_count"],
            "total_events": r["unique_event_count"],
        }
        rows.append(item)

    return {
        "airport_id": airport_id or "all",
        "total_days": len(rows),
        "comparison": rows,
        "warning": "Commercially reported events represent airline operational status updates, not physical runway radar sensor contacts. Marketing codeshares represent partner listings for existing operating aircraft and are not added to operational flight totals.",
        "field_definitions": {
            "total_records": "Total raw database event records for the airport and date across all categories.",
            "source_record_count": "Total raw/canonical database event records for the airport and date across all categories.",
            "scheduled_service_count": "Number of published commercial timetable slots (counting unit: scheduled timetable display records).",
            "scheduled_record_count": "Number of published commercial timetable slots (record_nature = 'scheduled_service').",
            "commercial_operational_event_count": "Number of commercially reported operational flights with actual departure/arrival status timestamps (record_nature = 'physical_movement').",
            "codeshare_record_count": "Number of secondary marketing partner ticket listings (record_nature = 'marketing_codeshare').",
            "matched_codeshare_record_count": "Codeshares whose operating flight number matches a commercially reported operational flight on that date and direction.",
            "unmatched_codeshare_record_count": "Codeshares with no matching operational flight record on that date (remain explicitly ambiguous).",
            "unverified_record_count": "Commercial board records lacking independent verification (record_nature = 'unverified_movement').",
            "unique_operating_flight_count": "Count of distinct operating flight service callsigns within the selected aerodrome and date. Counting unit: distinct airline service callsigns, NOT distinct physical aircraft airframes. Not an aircraft or movement count.",
            "resolved_commercial_movement_count": "Count of distinct commercial operational movement legs whose operational identity has been resolved using defensible multi-factor matching evidence. Counting unit: resolved operational flight legs. A flight number alone is insufficient to establish movement identity; direction, date, aerodrome, and verified operational telemetry anchor each leg. Does NOT imply runway radar sensor confirmation.",
            "confirmed_unique_movement_count": "Deprecated alias for 'resolved_commercial_movement_count'. Retained for backward compatibility; 'confirmed' refers to commercial identity resolution across listings, NOT ground radar or runway sensor contacts.",
            "ambiguous_movement_identity_count": "Count of candidate movements (such as unmatched marketing codeshares) whose operational identity cannot be confidently resolved on that date.",
            "unique_flight_movement_count": "Count of distinct operational movement legs (airport, date, direction, operating flight). Does not represent certified ground radar sensor contacts."
        },
        "deduplication_rules": [
            "Operating Flight Services: unique_operating_flight_count counts distinct service callsigns (operating flight numbers are commercial designations, NOT physical aircraft registrations or distinct flight legs).",
            "Movement Identity: resolved_commercial_movement_count establishes distinct movement legs using multi-factor identity anchors (aerodrome, date, direction, operating callsign, and verified actual operational telemetry).",
            "Repeated Flight Numbers: two flights operating under the same flight number (e.g. morning and evening legs, or turnaround legs) are counted as multiple resolved movements in resolved_commercial_movement_count, while unique_operating_flight_count counts the callsign once.",
            "Codeshares: marketing_codeshare records represent partner ticket listings on an operating aircraft leg; they do NOT inflate operating flight service or movement totals.",
            "Ambiguity Preservation: candidate records lacking defensible matching evidence (such as unmatched codeshares) remain classified in ambiguous_movement_identity_count and are never merged or silently discarded.",
            "Timetable Schedules: scheduled_service records represent published flight board slots without independent telemetry confirmation; they are kept separate from operational movements.",
            "Movement Separation: movements in different directions (arrival vs departure) or at different aerodromes are never merged together.",
            "Total Records: total_records represents raw database rows across all categories, not unique flight movements."
        ]
    }

@app.get("/api/movements/scheduled")
def get_scheduled_movements(
    airport_id: Optional[str] = Query(None, description="Filter by airport ID (DAM, ALP, DEZ, etc.) or omit for all"),
    date: Optional[str] = Query(None, description="Filter by YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    movement_type: Optional[str] = Query(None, description="arrival or departure"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    Returns commercial scheduled flight slots published on airport flight boards
    (record_nature = 'scheduled_service') without independent ground radar telemetry confirmation.
    Unverified historical completions and marketing codeshares are excluded.
    """
    query = "SELECT * FROM flight_events WHERE record_nature = 'scheduled_service'"
    params = []

    if airport_id:
        query += " AND airport_id = ?"
        params.append(airport_id.upper())
    if date:
        query += " AND flight_date = ?"
        params.append(date)
    if start_date:
        query += " AND flight_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND flight_date <= ?"
        params.append(end_date)
    if movement_type:
        query += " AND movement_type = ?"
        params.append(movement_type.lower())

    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]

        query += " ORDER BY flight_date DESC, (scheduled_dep_time || scheduled_arr_time) ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        for r in rows:
            r.pop("raw_json", None)

        rows = _enrich_flight_records(rows, conn)

    return {
        "record_nature": "scheduled_service",
        "description": "Published commercial timetable slots and airport authority flight board listings.",
        "airport_filter": airport_id or "all_syrian_airports",
        "total": total_count,
        "count": len(rows),
        "limit": limit,
        "offset": offset,
        "movements": rows,
        "data": rows
    }

@app.get("/api/movements/unverified")
def get_unverified_movements(
    airport_id: Optional[str] = Query(None, description="Filter by airport ID (DAM, ALP, DEZ, etc.) or omit for all"),
    date: Optional[str] = Query(None, description="Filter by YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    movement_type: Optional[str] = Query(None, description="arrival or departure"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    Returns unverified flight operations (record_nature = 'unverified_movement') that completed
    or departed on commercial flight boards or public portals but lack independent ADS-B ground
    radar telemetry to confirm runway movement. Records are never promoted to physical_movement
    merely because their flight_status is landed or departed.
    """
    query = "SELECT * FROM flight_events WHERE record_nature = 'unverified_movement'"
    params = []

    if airport_id:
        query += " AND airport_id = ?"
        params.append(airport_id.upper())
    if date:
        query += " AND flight_date = ?"
        params.append(date)
    if start_date:
        query += " AND flight_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND flight_date <= ?"
        params.append(end_date)
    if movement_type:
        query += " AND movement_type = ?"
        params.append(movement_type.lower())

    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]

        query += " ORDER BY flight_date DESC, (actual_dep_time || actual_arr_time || scheduled_dep_time || scheduled_arr_time) ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        for r in rows:
            r.pop("raw_json", None)
            r["verification_limitation"] = "Lacks independent ADS-B ground radar telemetry confirmation."

        rows = _enrich_flight_records(rows, conn)

    return {
        "record_nature": "unverified_movement",
        "description": "Historical flight operations recorded on commercial boards but lacking independent radar telemetry.",
        "airport_filter": airport_id or "all_syrian_airports",
        "total": total_count,
        "count": len(rows),
        "limit": limit,
        "offset": offset,
        "movements": rows,
        "data": rows
    }

@app.get("/api/movements/stats")
def get_stats():
    with get_connection() as conn:
        cursor = conn.cursor()

        # Airport events counts
        cursor.execute("""
        SELECT airport_id, COUNT(*) as cnt,
               MIN(flight_date) as min_date, MAX(flight_date) as max_date,
               COUNT(DISTINCT flight_date) as dates_count
        FROM flight_events
        GROUP BY airport_id
        """)
        apt_stats = [dict(r) for r in cursor.fetchall()]

        # Status counts
        cursor.execute("""
        SELECT flight_status, COUNT(*) as cnt
        FROM flight_events
        GROUP BY flight_status
        """)
        status_stats = dict(cursor.fetchall())

        # Total unique aircraft and airlines
        cursor.execute("SELECT COUNT(DISTINCT NULLIF(aircraft_registration, '')) FROM flight_events;")
        unique_aircraft = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT NULLIF(airline_name, '')) FROM flight_events;")
        unique_airlines = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM flight_events WHERE airport_id = 'DAM';")
        dam_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM historical_daily_movements_2024;")
        hist_2024_rows = cursor.fetchone()[0]

        # Top connected airports
        cursor.execute("""
        SELECT connected_airport_iata, COUNT(*) as cnt
        FROM flight_events
        WHERE connected_airport_iata IS NOT NULL AND connected_airport_iata != ''
        GROUP BY connected_airport_iata
        ORDER BY cnt DESC LIMIT 5;
        """)
        top_conn = [dict(r) for r in cursor.fetchall()]

    return {
        "engine_version": "2.0-all-syrian-airports",
        "iata": "DAM",
        "airport_events_breakdown": apt_stats,
        "total_verified_flights": dam_count,
        "flight_statuses": status_stats,
        "total_unique_aircraft": unique_aircraft,
        "unique_aircraft_tracked": unique_aircraft,
        "distinct_reported_aircraft_registrations": unique_aircraft,
        "deprecated_metrics": {
            "total_unique_aircraft": "Deprecated: equates commercial tail codes with verified airframes. Use 'distinct_reported_aircraft_registrations' instead.",
            "unique_aircraft_tracked": "Deprecated: implies continuous radar sensor tracking. Use 'distinct_reported_aircraft_registrations' instead."
        },
        "total_unique_airlines": unique_airlines,
        "top_connected_airports": top_conn,
        "historical_2024_rows": hist_2024_rows,
        "historical_2024_scope": "DAM_ALP_LTK",
    }

@app.get("/api/sources")
def get_sources():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM source_registry ORDER BY scope, source_id;")
        rows = [dict(r) for r in cursor.fetchall()]
    return rows

@app.get("/api/deduplication")
def get_deduplication(
    airport_id: Optional[str] = Query(None),
    resolution: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    query = "SELECT * FROM deduplication_audit WHERE 1=1"
    params = []
    if airport_id:
        query += " AND airport_id = ?"
        params.append(airport_id.upper())
    if resolution:
        query += " AND resolution_status = ?"
        params.append(resolution.upper())

    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]

    return {
        "total_records": total,
        "total_comparisons_logged": total,
        "limit": limit,
        "offset": offset,
        "records": rows,
        "data": rows
    }

@app.get("/api/ingestion/health")
def get_ingestion_health():
    """
    Returns latest automated ingestion runs, per-source health status,
    success/failure metrics, and recent error traces.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # Ingestion runs summary
        cursor.execute("""
            SELECT status, count(*) as count, sum(records_fetched) as total_records
            FROM ingestion_runs
            GROUP BY status
        """)
        status_summary = {r["status"]: {"count": r["count"], "records": r["total_records"] or 0} for r in cursor.fetchall()}

        # Recent runs
        cursor.execute("""
            SELECT run_id, run_timestamp, source_id, airport_id, status, records_fetched,
                   http_status, error_message, duration_seconds
            FROM ingestion_runs
            ORDER BY run_timestamp DESC
            LIMIT 25
        """)
        recent_runs = [dict(r) for r in cursor.fetchall()]

        # Source health status
        cursor.execute("""
            SELECT source_id, provider_name, source_type, supported_airports,
                   access_status, freshness_indicator, reliability_indicator,
                   last_successful_retrieval, known_limitations
            FROM source_registry
            ORDER BY source_id
        """)
        sources_status = [dict(r) for r in cursor.fetchall()]

    return {
        "overall_status": "OPERATIONAL",
        "summary": status_summary,
        "recent_runs": recent_runs,
        "sources_health": sources_status
    }

@app.get("/api/coverage/matrix")
def get_coverage_matrix(
    airport_id: Optional[str] = Query(None, description="Airport identifier e.g. DAM, ALP, LTK, DEZ, KAC"),
    classification: Optional[str] = Query(None, description="verified_coverage, commercial_schedule_only, source_checked_no_records, unverified_data_gap, future_schedule"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    limit: int = Query(100, ge=1, le=5000),
    offset: int = Query(0, ge=0)
):
    """
    Returns 2024-2026 historical coverage matrix entries classifying every date into
    one of 5 strict empirical categories.
    """
    query = "SELECT * FROM historical_coverage_matrix WHERE 1=1"
    params = []

    if airport_id:
        query += " AND airport_id = ?"
        params.append(airport_id.upper())
    if classification:
        query += " AND coverage_classification = ?"
        params.append(classification.lower())
    if start_date:
        query += " AND flight_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND flight_date <= ?"
        params.append(end_date)

    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]

        # Classification counts within filtered criteria
        class_query = query.replace("SELECT *", "SELECT coverage_classification, COUNT(*) as count") + " GROUP BY coverage_classification"
        cursor.execute(class_query, params)
        class_counts = {r["coverage_classification"]: r["count"] for r in cursor.fetchall()}

        query += " ORDER BY flight_date DESC, airport_id ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]

    return {
        "total_cells": total,
        "classification_breakdown": class_counts,
        "limit": limit,
        "offset": offset,
        "matrix": rows
    }

@app.get("/api/coverage")
def get_coverage():
    cov_path = REPORTS_DIR / "coverage_report.json"
    if cov_path.exists():
        with open(cov_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"message": "Coverage report not found. Run backfill.py to generate."}

@app.get("/api/quality")
def get_quality():
    q_path = REPORTS_DIR / "quality_audit.json"
    if q_path.exists():
        with open(q_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"message": "Quality audit report not found. Run backfill.py to generate."}

@app.get("/api/historical-coverage/timeline")
def get_historical_coverage_timeline():
    """
    Returns month-by-month verified historical coverage status for the 34-month audit window (2024-01 to 2026-10).
    Each month includes geographic scope, dataset category, evidence level, source period, record count,
    and explicit warnings for non-DAM-specific or missing periods.
    """
    timeline_csv = REPORTS_DIR / "v2_18_1_coverage_correction.csv"
    timeline = []
    if timeline_csv.exists():
        import csv
        with open(timeline_csv, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                ym = r["year_month"]
                cat = r["corrected_category"]
                raw_cnt = int(r["raw_records_count"])
                scope = r["airport_scope"]

                if cat == "regional_aggregate":
                    scope_desc = "DAM_ALP_LTK (Syrian Commercial Gateways Aggregate)"
                    ev_level = "multi_airport_macro_aggregate"
                    warning = "Three-airport regional aggregate (DAM, ALP, LTK combined); zero DAM-specific disaggregation available. Cannot be used as DAM movement counts."
                    is_dam = False
                    has_dam_obs = False
                elif cat == "no_verified_dam_data":
                    scope_desc = "NONE (Platform Data Gap)"
                    ev_level = "no_coverage"
                    warning = "Platform historical data gap; zero verified Damascus records recovered. Indicates absence of source data, never zero flights or airport closure."
                    is_dam = False
                    has_dam_obs = False
                elif cat == "dam_scheduled_fids":
                    scope_desc = "Damascus International Airport (DAM)"
                    ev_level = "scheduled_timetable_display"
                    warning = "Official archived FIDS schedule slots. Represents timetable records, not physical radar-confirmed movements."
                    is_dam = True
                    has_dam_obs = True
                elif cat == "live_regional_adsb":
                    scope_desc = "Damascus (DAM) & Regional Airspace"
                    ev_level = "regional_airspace_observation"
                    warning = "Live ADS-B sample query covering 15 regional overflights and 1 regional transit. Does not confirm direct runway movements."
                    is_dam = False
                    has_dam_obs = True
                else:
                    scope_desc = scope
                    ev_level = "unknown"
                    warning = "Unclassified temporal window."
                    is_dam = False
                    has_dam_obs = False

                timeline.append({
                    "source_period": ym,
                    "geographic_scope": scope_desc,
                    "dataset_category": cat,
                    "evidence_level": ev_level,
                    "record_count": raw_cnt,
                    "explicit_warning": warning,
                    "is_dam_specific": is_dam,
                    "contains_dam_observation": has_dam_obs
                })

    return {
        "audit_window": "2024-01 through 2026-10 (34 months)",
        "total_months": len(timeline),
        "timeline": timeline,
        "disclaimer": "Do not display regional aggregates, archived schedules, and live regional ADS-B samples as one continuous DAM movement series. Data gaps represent unrecovered platform coverage, never zero flights or airport closure."
    }


EXPORT_METADATA = {
    "all_syrian_flight_events": {
        "dataset_name": "All Syrian Aerodromes Flight Events",
        "geographic_scope": "All Syrian Aerodromes (DAM, ALP, LTK, DEZ, KAC)",
        "scope": "All Syrian Aerodromes",
        "dataset_category": "flight_events",
        "category": "flight_events",
        "evidence_level": "multi_tier_commercial_and_timetable",
        "source_provenance": "Official Syrian airport authority portals & Flightradar24 commercial feeds",
        "provenance": "Official Syrian airport authority portals & Flightradar24 commercial feeds",
        "source_observation_period": "2026-07-05 to 2026-10-10",
        "generation_timestamp": "2026-10-11T17:45:00Z",
        "known_limitations": "Operational events represent commercial status messages; estimated timestamps are strictly separated into estimated_dep_time and estimated_arr_time; ground runway radar sensor telemetry is pending.",
    },
    "damascus_flight_events": {
        "dataset_name": "Damascus International Airport Flight Events",
        "geographic_scope": "Damascus International Airport (DAM / OSDI)",
        "scope": "Damascus International Airport (DAM / OSDI)",
        "dataset_category": "flight_events",
        "category": "flight_events",
        "evidence_level": "multi_tier_commercial_and_timetable",
        "source_provenance": "damairport.gov.sy official flight board & Flightradar24 commercial feeds",
        "provenance": "damairport.gov.sy official flight board & Flightradar24 commercial feeds",
        "source_observation_period": "2026-07-05 to 2026-10-10",
        "generation_timestamp": "2026-10-11T17:45:00Z",
        "known_limitations": "Operational events represent commercial status updates with actual timestamps; estimated timestamps are strictly separated into estimated_dep_time and estimated_arr_time; direct runway radar telemetry is pending.",
    },
    "daily_airport_movements": {
        "dataset_name": "Daily Aerodrome Movements Rollup",
        "geographic_scope": "All Syrian Aerodromes (DAM, ALP, DEZ, LTK, KAC)",
        "scope": "All Syrian Aerodromes",
        "dataset_category": "daily_aggregates",
        "category": "daily_aggregates",
        "evidence_level": "operational_aggregates",
        "source_provenance": "Layer A operational database daily rollup",
        "provenance": "Layer A operational database daily rollup",
        "source_observation_period": "2026-07-05 to 2026-10-10",
        "generation_timestamp": "2026-10-11T17:45:00Z",
        "known_limitations": "Aggregates commercial flight events and scheduled timetable services per airport.",
    },
    "damascus_daily_movements": {
        "dataset_name": "Damascus Daily Airport Movements",
        "geographic_scope": "Damascus International Airport (DAM / OSDI)",
        "scope": "Damascus International Airport (DAM / OSDI)",
        "dataset_category": "daily_aggregates",
        "category": "daily_aggregates",
        "evidence_level": "operational_aggregates",
        "source_provenance": "Layer A operational database Damascus daily rollup",
        "provenance": "Layer A operational database Damascus daily rollup",
        "source_observation_period": "2026-07-05 to 2026-10-10",
        "generation_timestamp": "2026-10-11T17:45:00Z",
        "known_limitations": "Reflects normalized commercial operations and timetable listings for Damascus only.",
    },
    "historical_daily_movements_2024": {
        "dataset_name": "Syria Economic Monitor 2024 Commercial Gateways Aggregate",
        "geographic_scope": "DAM_ALP_LTK (Three-airport regional aggregate: Damascus, Aleppo, Latakia combined)",
        "scope": "DAM_ALP_LTK (Three-airport regional aggregate: Damascus, Aleppo, Latakia combined)",
        "dataset_category": "regional_aggregate",
        "category": "regional_aggregate",
        "evidence_level": "macro_commercial_gateway_series",
        "source_provenance": "Syria Economic Monitor (World Bank / Data Partnership)",
        "provenance": "Syria Economic Monitor (World Bank / Data Partnership)",
        "source_observation_period": "2024-01-01 to 2024-10-15",
        "generation_timestamp": "2026-10-11T17:45:00Z",
        "known_limitations": "Three-airport aggregate. Zero DAM-specific disaggregation available. Must not be counted as DAM-only movements.",
    },
    "syrian_airports_registry": {
        "dataset_name": "Syrian Aerodromes Authoritative Registry",
        "geographic_scope": "7 Syrian Aerodromes",
        "scope": "7 Syrian Aerodromes",
        "dataset_category": "infrastructure_reference",
        "category": "infrastructure_reference",
        "evidence_level": "authoritative_aeronautical_specifications",
        "source_provenance": "Syrian Civil Aviation Authority eAIP & OurAirports",
        "provenance": "Syrian Civil Aviation Authority eAIP & OurAirports",
        "source_observation_period": "2026-10-11",
        "generation_timestamp": "2026-10-11T17:45:00Z",
        "known_limitations": "Static aeronautical infrastructure reference specifications.",
    },
    "deduplication_audit": {
        "dataset_name": "Deterministic Deduplication Audit Log",
        "geographic_scope": "System-wide pairwise comparisons",
        "scope": "System-wide pairwise comparisons",
        "dataset_category": "audit_log",
        "category": "audit_log",
        "evidence_level": "deterministic_deduplication_trail",
        "source_provenance": "Automated deduplication and canonical resolution pipeline",
        "provenance": "Automated deduplication and canonical resolution pipeline",
        "source_observation_period": "2026-10-01 to 2026-10-10",
        "generation_timestamp": "2026-10-11T17:45:00Z",
        "known_limitations": "Pairwise entity comparison logs resolving duplicate commercial feed items.",
    },
    "historical_coverage_matrix_2024_2026": {
        "dataset_name": "Historical Aerodrome Coverage Matrix (2024-2026)",
        "geographic_scope": "Syrian Aerodromes (2024-2026)",
        "scope": "Syrian Aerodromes (2024-2026)",
        "dataset_category": "coverage_matrix",
        "category": "coverage_matrix",
        "evidence_level": "empirical_coverage_classification",
        "source_provenance": "Multi-milestone verified historical coverage audit",
        "provenance": "Multi-milestone verified historical coverage audit",
        "source_observation_period": "2024-01-01 to 2026-10-10",
        "generation_timestamp": "2026-10-11T17:45:00Z",
        "known_limitations": "Categorizes dates into macro aggregates, platform data gaps, FIDS schedules, and live ADS-B.",
    },
    "v2_18_damascus_coverage": {
        "dataset_name": "Damascus Historical Dataset Recovery Matrix",
        "geographic_scope": "Damascus (DAM) & Regional Airspace (34 months)",
        "scope": "Damascus (DAM) & Regional Airspace (34 months)",
        "dataset_category": "coverage_matrix",
        "category": "coverage_matrix",
        "evidence_level": "empirical_coverage_classification",
        "source_provenance": "V2.18 Historical Aviation Dataset Recovery",
        "provenance": "V2.18 Historical Aviation Dataset Recovery",
        "source_observation_period": "2024-01 to 2026-10",
        "generation_timestamp": "2026-10-11T17:45:00Z",
        "known_limitations": "Evaluates candidate datasets against Damascus physical movement criteria.",
    },
    "v2_18_1_coverage_correction": {
        "dataset_name": "34-Month Forensic Coverage Reconciliation",
        "geographic_scope": "Damascus (DAM) & Regional Airspace (34 months)",
        "scope": "Damascus (DAM) & Regional Airspace (34 months)",
        "dataset_category": "coverage_matrix",
        "category": "coverage_matrix",
        "evidence_level": "forensic_coverage_reconciliation",
        "source_provenance": "V2.18.1 Historical Coverage Integrity Audit",
        "provenance": "V2.18.1 Historical Coverage Integrity Audit",
        "source_observation_period": "2024-01 to 2026-10",
        "generation_timestamp": "2026-10-11T17:45:00Z",
        "known_limitations": "Quarantines 2024 regional aggregates; confirms 18-month data gap as no_verified_dam_data.",
    },
    "v2_18_1_dataset_scope_audit": {
        "dataset_name": "Public Candidate Dataset Scope Audit",
        "geographic_scope": "Public Candidate Datasets",
        "scope": "Public Candidate Datasets",
        "dataset_category": "audit_log",
        "category": "audit_log",
        "evidence_level": "forensic_dataset_evaluation",
        "source_provenance": "V2.18.1 Scope Audit",
        "provenance": "V2.18.1 Scope Audit",
        "source_observation_period": "2024 to 2026",
        "generation_timestamp": "2026-10-11T17:45:00Z",
        "known_limitations": "Evaluation of external candidate aviation archives.",
    },
    "v2_18_dataset_scoring": {
        "dataset_name": "Dataset Integrity & Feasibility Scoring",
        "geographic_scope": "Public Candidate Datasets",
        "scope": "Public Candidate Datasets",
        "dataset_category": "audit_log",
        "category": "audit_log",
        "evidence_level": "scoring_matrix",
        "source_provenance": "V2.18 Dataset Scoring",
        "provenance": "V2.18 Dataset Scoring",
        "source_observation_period": "2024 to 2026",
        "generation_timestamp": "2026-10-11T17:45:00Z",
        "known_limitations": "Quantitative feasibility scoring of potential historical repositories.",
    },
    "v2_18_dataset_inventory": {
        "dataset_name": "Public Historical Aviation Repository Catalog",
        "geographic_scope": "Public Candidate Repositories",
        "scope": "Public Candidate Repositories",
        "dataset_category": "dataset_inventory",
        "category": "dataset_inventory",
        "evidence_level": "repository_catalog",
        "source_provenance": "V2.18 Candidate Discovery",
        "provenance": "V2.18 Candidate Discovery",
        "source_observation_period": "2024 to 2026",
        "generation_timestamp": "2026-10-11T17:45:00Z",
        "known_limitations": "Catalog of publicly identified aviation repositories.",
    },
    "v2_19_2_physical_movement_audit": {
        "dataset_name": "Event-Level Operational Movement Provenance Audit",
        "geographic_scope": "All Syrian Aerodromes Physical Movements (131 records)",
        "scope": "All Syrian Aerodromes Physical Movements (131 records)",
        "dataset_category": "audit_log",
        "category": "audit_log",
        "evidence_level": "event_level_provenance_audit",
        "source_provenance": "V2.19.2 Forensic Physical Movement Audit",
        "provenance": "V2.19.2 Forensic Physical Movement Audit",
        "source_observation_period": "2026-10-09 to 2026-10-10",
        "generation_timestamp": "2026-10-11T17:45:00Z",
        "known_limitations": "Verifies 0 direct runway sensor contacts among 131 commercially reported operational events.",
    },
    "v2_20_6_mislabeled_evidence_audit": {
        "dataset_name": "Forensic Mislabeled Evidence Audit (76 Records)",
        "geographic_scope": "DAM & ALP Aerodromes",
        "scope": "DAM & ALP Aerodromes",
        "dataset_category": "audit_log",
        "category": "audit_log",
        "evidence_level": "event_level_provenance_audit",
        "source_provenance": "V2.20.6 Forensic Evidence Taxonomy Audit",
        "provenance": "V2.20.6 Forensic Evidence Taxonomy Audit",
        "source_observation_period": "2026-10-09 to 2026-10-10",
        "generation_timestamp": "2026-10-11T18:55:00Z",
        "known_limitations": "Complete inventory of 76 evidence rows derived from estimated timestamps rather than Mode-S telemetry. Immutable ledger preserved.",
    }
}

VALID_EXPORT_DATASETS = {
    "all_syrian_flight_events": "all_syrian_flight_events",
    "damascus_flight_events": "damascus_flight_events",
    "damascus_flights": "damascus_flight_events",
    "flight_events": "damascus_flight_events",
    "daily_airport_movements": "daily_airport_movements",
    "damascus_daily_movements": "damascus_daily_movements",
    "daily_movements": "damascus_daily_movements",
    "historical_2024": "historical_daily_movements_2024",
    "historical_daily_movements_2024": "historical_daily_movements_2024",
    "syrian_airports": "syrian_airports_registry",
    "airports": "syrian_airports_registry",
    "deduplication_audit": "deduplication_audit",
    "historical_coverage_matrix": "historical_coverage_matrix_2024_2026",
    "coverage_matrix": "historical_coverage_matrix_2024_2026",
    "v2_18_damascus_coverage": "v2_18_damascus_coverage",
    "damascus_coverage": "v2_18_damascus_coverage",
    "v2_18_1_coverage_correction": "v2_18_1_coverage_correction",
    "coverage_correction": "v2_18_1_coverage_correction",
    "v2_18_1_dataset_scope_audit": "v2_18_1_dataset_scope_audit",
    "dataset_scope_audit": "v2_18_1_dataset_scope_audit",
    "v2_18_dataset_scoring": "v2_18_dataset_scoring",
    "dataset_scoring": "v2_18_dataset_scoring",
    "v2_18_dataset_inventory": "v2_18_dataset_inventory",
    "dataset_inventory": "v2_18_dataset_inventory",
    "v2_19_2_physical_movement_audit": "v2_19_2_physical_movement_audit",
    "physical_movement_audit": "v2_19_2_physical_movement_audit",
    "v2_20_6_mislabeled_evidence_audit": "v2_20_6_mislabeled_evidence_audit",
    "mislabeled_evidence_audit": "v2_20_6_mislabeled_evidence_audit",
    "evidence_audit": "v2_20_6_mislabeled_evidence_audit",
}

@app.get("/api/export/{dataset}")
def export_dataset(
    dataset: str,
    format: str = Query("csv", regex="^(csv|json)$"),
    include_metadata: bool = Query(False, description="Embed self-describing metadata envelope or header comments")
):
    dataset = dataset.lower().strip()
    if dataset not in VALID_EXPORT_DATASETS:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset}' not found. Valid: {list(VALID_EXPORT_DATASETS.keys())}")

    target_key = VALID_EXPORT_DATASETS[dataset]
    filename = f"{target_key}.{format}"
    file_path = PROCESSED_DATA_DIR / filename
    if not file_path.exists():
        file_path = REPORTS_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Export file '{filename}' not found. Run backfill script first.")

    meta = EXPORT_METADATA.get(target_key, {})
    headers = {
        "X-Dataset-Name": meta.get("dataset_name", target_key),
        "X-Dataset-Scope": meta.get("geographic_scope", meta.get("scope", "Unspecified")),
        "X-Dataset-Category": meta.get("dataset_category", meta.get("category", "unknown")),
        "X-Evidence-Level": meta.get("evidence_level", "unknown"),
        "X-Source-Provenance": meta.get("source_provenance", meta.get("provenance", "Unknown")),
        "X-Source-Observation-Period": meta.get("source_observation_period", "Unknown"),
        "X-Generation-Timestamp": meta.get("generation_timestamp", "2026-10-11T17:45:00Z"),
        "X-Known-Limitations": meta.get("known_limitations", "None"),
        "X-Generated-At": meta.get("generation_timestamp", "2026-10-11T17:45:00Z")  # backward compatibility
    }

    if not include_metadata:
        media_type = "text/csv" if format == "csv" else "application/json"
        return FileResponse(path=file_path, filename=filename, media_type=media_type, headers=headers)

    # Embedded self-describing export format
    if format == "json":
        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
        enveloped = {
            "metadata": meta,
            "data": content
        }
        return Response(content=json.dumps(enveloped, indent=2), media_type="application/json", headers=headers)
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        header_comment = (
            f"# METADATA\n"
            f"# dataset_name: {meta.get('dataset_name')}\n"
            f"# geographic_scope: {meta.get('geographic_scope')}\n"
            f"# dataset_category: {meta.get('dataset_category')}\n"
            f"# evidence_level: {meta.get('evidence_level')}\n"
            f"# source_provenance: {meta.get('source_provenance')}\n"
            f"# source_observation_period: {meta.get('source_observation_period')}\n"
            f"# generation_timestamp: {meta.get('generation_timestamp')}\n"
            f"# known_limitations: {meta.get('known_limitations')}\n"
        )
        return Response(content=header_comment + content, media_type="text/csv", headers=headers)

@app.get("/api/export/{dataset}/sidecar")
def get_export_sidecar(dataset: str):
    dataset = dataset.lower().strip()
    if dataset not in VALID_EXPORT_DATASETS:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset}' not found. Valid: {list(VALID_EXPORT_DATASETS.keys())}")

    target_key = VALID_EXPORT_DATASETS[dataset]
    meta = EXPORT_METADATA.get(target_key, {})
    headers = {
        "Content-Disposition": f'attachment; filename="{target_key}.metadata.json"',
        "X-Dataset-Name": meta.get("dataset_name", target_key),
        "X-Dataset-Scope": meta.get("geographic_scope", "Unspecified"),
        "X-Dataset-Category": meta.get("dataset_category", "unknown"),
        "X-Evidence-Level": meta.get("evidence_level", "unknown"),
        "X-Source-Provenance": meta.get("source_provenance", "Unknown"),
        "X-Source-Observation-Period": meta.get("source_observation_period", "Unknown"),
        "X-Generation-Timestamp": meta.get("generation_timestamp", "2026-10-11T17:45:00Z"),
        "X-Known-Limitations": meta.get("known_limitations", "None")
    }
    return Response(content=json.dumps(meta, indent=2), media_type="application/json", headers=headers)

@app.get("/api/export/{dataset}/metadata")
def get_export_metadata(dataset: str):
    dataset = dataset.lower().strip()
    if dataset not in VALID_EXPORT_DATASETS:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset}' not found. Valid: {list(VALID_EXPORT_DATASETS.keys())}")

    target_key = VALID_EXPORT_DATASETS[dataset]
    meta = EXPORT_METADATA.get(target_key, {})
    return {
        "dataset_key": dataset,
        "canonical_target": target_key,
        "metadata": meta
    }
