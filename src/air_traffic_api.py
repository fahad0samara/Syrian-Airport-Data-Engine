# -*- coding: utf-8 -*-
"""
Air Traffic Monitor API Router — CSV-First Implementation
Provides analytical endpoints, independent coverage dimensions, monthly aggregation,
and multi-format exports (CSV/XLSX) based strictly on data/processed/all_syrian_flight_events.csv.

Primary Data Source:
    data/processed/all_syrian_flight_events.csv (1,830 verified event records).
    Does NOT query SQLite for monitor metrics.
    Does NOT implement SQL fallback.
"""
import io
import json
from typing import Optional, List, Dict, Any
from pathlib import Path
import pandas as pd
from fastapi import APIRouter, Query, HTTPException, Response
from fastapi.responses import HTMLResponse

from src.config import STATIC_DIR, PROCESSED_DATA_DIR, SYRIAN_AIRPORTS_REGISTRY

router = APIRouter(tags=["Air Traffic Monitor"])

PRIMARY_CSV_PATH = PROCESSED_DATA_DIR / "all_syrian_flight_events.csv"

REQUIRED_COLUMNS = [
    "event_id",
    "airport_id",
    "source",
    "movement_type",
    "record_nature",
    "flight_status",
    "flight_date",
    "airline_name",
    "connected_airport_iata",
    "flight_number",
    "aircraft_model",
    "observed_or_derived"
]

@router.get("/monitor", response_class=HTMLResponse)
@router.get("/air-traffic", response_class=HTMLResponse)
def get_air_traffic_monitor_page():
    """Serves the standalone Syrian Air Traffic Monitor page."""
    file_path = STATIC_DIR / "air_traffic_monitor.html"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Air Traffic Monitor page not found.")
    return HTMLResponse(content=file_path.read_text(encoding="utf-8"))

def load_primary_flight_events(csv_path: Optional[Path] = None) -> pd.DataFrame:
    """
    Loads and validates the primary CSV dataset.
    Raises HTTPException 500 if file is missing, unreadable, or missing required columns.
    Strictly avoids querying SQLite.
    """
    target_path = csv_path or PRIMARY_CSV_PATH
    if not target_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Primary dataset file '{target_path.as_posix()}' is missing. Monitor requires CSV-first data source."
        )

    try:
        df = pd.read_csv(target_path, dtype={"flight_number": str, "event_id": str})
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Primary dataset file '{target_path.as_posix()}' could not be parsed: {str(e)}"
        )

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Primary dataset file is missing required columns: {missing}"
        )

    # Safe null and string normalization
    df["flight_date"] = df["flight_date"].fillna("").astype(str).str.strip()
    df["airport_id"] = df["airport_id"].fillna("").astype(str).str.strip().str.upper()
    df["record_nature"] = df["record_nature"].fillna("").astype(str).str.strip()
    df["movement_type"] = df["movement_type"].fillna("").astype(str).str.strip().str.lower()
    df["flight_status"] = df["flight_status"].fillna("").astype(str).str.strip().str.lower()
    df["airline_name"] = df["airline_name"].fillna("").astype(str).str.strip()
    df["connected_airport_iata"] = df["connected_airport_iata"].fillna("").astype(str).str.strip().str.upper()

    return df

def apply_filters(
    df: pd.DataFrame,
    airport_id: Optional[str] = None,
    month: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    airline: Optional[str] = None,
    destination: Optional[str] = None
) -> pd.DataFrame:
    """Applies standard query filters to flight events DataFrame."""
    filtered = df.copy()

    if isinstance(airport_id, str) and airport_id.strip() and airport_id.upper() not in ("ALL", ""):
        filtered = filtered[filtered["airport_id"] == airport_id.strip().upper()]

    if isinstance(month, str) and month.strip():
        filtered = filtered[filtered["flight_date"].str.startswith(month.strip())]

    if isinstance(start_date, str) and start_date.strip():
        filtered = filtered[filtered["flight_date"] >= start_date.strip()]

    if isinstance(end_date, str) and end_date.strip():
        filtered = filtered[filtered["flight_date"] <= end_date.strip()]

    if isinstance(airline, str) and airline.strip():
        val = airline.strip().lower()
        airline_match = (
            filtered["airline_name"].str.lower() == val
        )
        if "airline_iata" in filtered.columns:
            airline_match = airline_match | (filtered["airline_iata"].fillna("").astype(str).str.lower() == val)
        if "operating_carrier" in filtered.columns:
            airline_match = airline_match | (filtered["operating_carrier"].fillna("").astype(str).str.lower() == val)
        filtered = filtered[airline_match]

    if isinstance(destination, str) and destination.strip():
        val = destination.strip().upper()
        dest_match = (
            filtered["connected_airport_iata"] == val
        )
        if "connected_airport_icao" in filtered.columns:
            dest_match = dest_match | (filtered["connected_airport_icao"].fillna("").astype(str).str.upper() == val)
        if "connected_city" in filtered.columns:
            dest_match = dest_match | (filtered["connected_city"].fillna("").astype(str).str.upper() == val)
        filtered = filtered[dest_match]

    return filtered

def compute_schedule_coverage(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes Schedule Coverage exclusively from record_nature == 'scheduled_service'.
    Does not interpret schedule records as actual physical flights.
    """
    sched_df = df[df["record_nature"] == "scheduled_service"]
    dates = sorted([d for d in sched_df["flight_date"].unique() if d])
    dates_count = len(dates)
    total_records = len(sched_df)

    if total_records == 0:
        status = "No Schedule Records"
        status_ar = "لا توجد سجلات جداول"
    else:
        status = "Available"
        status_ar = "متاحة"

    arr_count = int((sched_df["movement_type"] == "arrival").sum())
    dep_count = int((sched_df["movement_type"] == "departure").sum())

    distinct_airlines = [a for a in sched_df["airline_name"].unique() if a]
    distinct_destinations = [d for d in sched_df["connected_airport_iata"].unique() if d]

    return {
        "status": status,
        "status_ar": status_ar,
        "scheduled_service_records": total_records,
        "scheduled_arrivals": arr_count,
        "scheduled_departures": dep_count,
        "scheduled_dates_count": dates_count,
        "first_scheduled_date": dates[0] if dates else None,
        "last_scheduled_date": dates[-1] if dates else None,
        "active_scheduled_airlines": len(distinct_airlines),
        "active_scheduled_destinations": len(distinct_destinations)
    }

def compute_observation_coverage(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes Actual Observation Coverage exclusively from record_nature == 'physical_movement'.
    Does NOT count marketing codeshares or unverified records.
    Explicitly marks monitoring outside observed dates as Unknown.
    """
    obs_df = df[df["record_nature"] == "physical_movement"]
    dates = sorted([d for d in obs_df["flight_date"].unique() if d])
    dates_count = len(dates)
    total_records = len(obs_df)

    if total_records == 0:
        status = "No Observed Movement Records"
        status_ar = "لا توجد سجلات حركات مرصودة"
        obs_val = None
    else:
        status = "Observed Movements Available"
        status_ar = "تتوفر حركات مرصودة"
        obs_val = total_records

    arr_count = int((obs_df["movement_type"] == "arrival").sum())
    dep_count = int((obs_df["movement_type"] == "departure").sum())

    distinct_airlines = [a for a in obs_df["airline_name"].unique() if a]
    distinct_destinations = [d for d in obs_df["connected_airport_iata"].unique() if d]

    return {
        "status": status,
        "status_ar": status_ar,
        "observed_movements": obs_val,
        "observed_movements_label": "ADS-B Observed Movements — Commercial Tracking Data (October 9–10 sample only)",
        "observed_arrivals": arr_count if obs_val is not None else None,
        "observed_departures": dep_count if obs_val is not None else None,
        "observed_dates_count": dates_count,
        "observed_dates": dates,
        "first_observed_date": dates[0] if dates else None,
        "last_observed_date": dates[-1] if dates else None,
        "active_observed_airlines": len(distinct_airlines),
        "active_observed_destinations": len(distinct_destinations),
        "monitoring_outside_status": "Monitoring Coverage Unknown",
        "monitoring_outside_status_ar": "تغطية المراقبة خارج هذه التواريخ غير معروفة",
        "methodology_note": "Observed movements represent available commercial ADS-B tracking observations classified under the project's evidence methodology. They should not be interpreted as complete airport traffic or independent official radar confirmation. 'No Observed Movement Records' does not mean zero flights occurred. Monitoring Coverage Unknown indicates monitoring status outside observed dates cannot be established from available records."
    }

@router.get("/api/air-traffic/kpis")
def get_air_traffic_kpis(
    airport_id: Optional[str] = Query(None, description="Airport filter (DAM, ALP, DEZ, etc.)"),
    month: Optional[str] = Query(None, description="Month filter YYYY-MM (defaults to latest month: 2026-10)"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    airline: Optional[str] = Query(None, description="Airline filter"),
    destination: Optional[str] = Query(None, description="Destination IATA/city filter")
):
    """
    Returns KPIs and independent coverage metrics derived strictly from the primary CSV dataset.
    """
    df = load_primary_flight_events()

    effective_month = month or "2026-10"
    filtered = apply_filters(
        df=df,
        airport_id=airport_id,
        month=effective_month if not (start_date or end_date) else None,
        start_date=start_date,
        end_date=end_date,
        airline=airline,
        destination=destination
    )

    sched_cov = compute_schedule_coverage(filtered)
    obs_cov = compute_observation_coverage(filtered)

    codeshare_count = int((filtered["record_nature"] == "marketing_codeshare").sum())
    unverified_count = int((filtered["record_nature"] == "unverified_movement").sum())

    airports_covered = int(filtered["airport_id"].nunique())
    scope_label = airport_id.upper() if (isinstance(airport_id, str) and airport_id.upper() != "ALL") else "All Syrian Aerodromes"

    return {
        "period": {
            "month": effective_month if not (start_date or end_date) else None,
            "start_date": filtered["flight_date"].min() if len(filtered) > 0 else None,
            "end_date": filtered["flight_date"].max() if len(filtered) > 0 else None,
            "label": "October 2026 (Latest Available Month)" if effective_month == "2026-10" and not start_date else f"{filtered['flight_date'].min()} to {filtered['flight_date'].max()}"
        },
        "airport_scope": scope_label,
        "kpis": {
            "scheduled_flights": sched_cov["scheduled_service_records"],
            "scheduled_arrivals": sched_cov["scheduled_arrivals"],
            "scheduled_departures": sched_cov["scheduled_departures"],
            "actual_movements": obs_cov["observed_movements"],
            "actual_movements_label": obs_cov["observed_movements_label"],
            "actual_movements_status": obs_cov["status"],
            "active_airlines": int(filtered["airline_name"].replace("", pd.NA).dropna().nunique()),
            "active_destinations": int(filtered["connected_airport_iata"].replace("", pd.NA).dropna().nunique()),
            "airports_covered": airports_covered,
            "registered_airports_total": 7,
            "marketing_codeshares": codeshare_count,
            "unverified_movements": unverified_count,
            "passengers": None,  # Strictly null: no speculative capacity guessing
            "passengers_note": "No reliable passenger volume data published for this operational period."
        },
        "schedule_coverage": sched_cov,
        "observation_coverage": obs_cov,
        "definitions": {
            "scheduled_flights": "Commercial timetable service slots published by official airport display boards across the entire selected period (record_nature = 'scheduled_service'). Includes scheduled, active, cancelled, diverted, and unknown status slots.",
            "actual_movements": "ADS-B Observed Movements — Commercial Tracking Data (October 9–10 sample only). Physical movements (wheels-off/wheels-down) with Mode-S transponder telemetry (record_nature = 'physical_movement'). Marketing codeshares (20 in landed/departed sample) and unverified movements (3 records) excluded.",
            "active_airlines": "Distinct airline brands represented across the selected flight dataset. Physical aircraft operations in the Oct 9-10 ADS-B sample represent 17 distinct carriers.",
            "active_destinations": "Distinct destination/origin aerodromes connected to Syrian airports during the selected period.",
            "airports_covered": "Number of Syrian aerodromes with active flight records during the selected period out of 7 registered aerodromes.",
            "marketing_codeshares": "Marketing codeshare listings matching physical aircraft transponders 1:1; preserved for transparency but excluded from physical movement counts to avoid double-counting.",
            "unverified_movements": "Movements appearing on airport monitors lacking corroborating ADS-B Mode-S trajectory records.",
            "coverage_separation": "Schedule Coverage measures published timetable availability; Actual Observation Coverage measures telemetry reception availability. A lack of observed records outside observed dates indicates Monitoring Coverage Unknown, not zero flights."
        }
    }

@router.get("/api/air-traffic/coverage")
def get_air_traffic_coverage(
    airport_id: Optional[str] = Query(None, description="Airport filter"),
    month: Optional[str] = Query(None, description="Month filter YYYY-MM"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD")
):
    """
    Returns independent Schedule Coverage and Actual Observation Coverage dimensions side-by-side.
    """
    df = load_primary_flight_events()
    filtered = apply_filters(
        df=df,
        airport_id=airport_id,
        month=month,
        start_date=start_date,
        end_date=end_date
    )

    return {
        "period": {
            "month": month,
            "start_date": filtered["flight_date"].min() if len(filtered) > 0 else None,
            "end_date": filtered["flight_date"].max() if len(filtered) > 0 else None
        },
        "airport_scope": airport_id.upper() if airport_id and airport_id.upper() != "ALL" else "All Syrian Aerodromes",
        "schedule_coverage": compute_schedule_coverage(filtered),
        "observation_coverage": compute_observation_coverage(filtered)
    }

@router.get("/api/air-traffic/monthly-summary")
def get_air_traffic_monthly_summary(
    airport_id: Optional[str] = Query(None, description="Airport filter"),
    month: Optional[str] = Query(None, description="Month filter YYYY-MM"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    airline: Optional[str] = Query(None, description="Airline filter"),
    destination: Optional[str] = Query(None, description="Destination filter")
):
    """
    Returns monthly aggregated summary derived strictly from primary CSV.
    Keeps scheduled and observed metrics strictly separated.
    """
    df = load_primary_flight_events()
    filtered = apply_filters(
        df=df,
        airport_id=airport_id,
        month=month,
        start_date=start_date,
        end_date=end_date,
        airline=airline,
        destination=destination
    )

    filtered["month"] = filtered["flight_date"].str.slice(0, 7)
    grouped = filtered.groupby(["month", "airport_id"])

    rows = []
    for (m, ap), grp in grouped:
        sched_cov = compute_schedule_coverage(grp)
        obs_cov = compute_observation_coverage(grp)

        rows.append({
            "month": m,
            "airport_id": ap,
            "scheduled_flights": sched_cov["scheduled_service_records"],
            "scheduled_arrivals": sched_cov["scheduled_arrivals"],
            "scheduled_departures": sched_cov["scheduled_departures"],
            "scheduled_airlines": sched_cov["active_scheduled_airlines"],
            "scheduled_destinations": sched_cov["active_scheduled_destinations"],
            "schedule_coverage_status": sched_cov["status"],
            "actual_movements": obs_cov["observed_movements"],
            "actual_movements_label": "ADS-B Observed Movements — Commercial Tracking Data (October 9–10 sample only)",
            "actual_movements_note": "ADS-B Observed Movements — Commercial Tracking Data (October 9–10 sample only)" if obs_cov["observed_movements"] is not None else "Telemetry unobserved; timetable display only.",
            "observed_arrivals": obs_cov["observed_arrivals"],
            "observed_departures": obs_cov["observed_departures"],
            "observed_airlines": obs_cov["active_observed_airlines"],
            "observed_destinations": obs_cov["active_observed_destinations"],
            "observation_coverage_status": obs_cov["status"],
            "monitoring_outside_status": obs_cov["monitoring_outside_status"],
            "passengers": None,  # Strictly null
            "passengers_note": "No reliable passenger volume data published.",
            "marketing_codeshares": int((grp["record_nature"] == "marketing_codeshare").sum()),
            "unverified_movements": int((grp["record_nature"] == "unverified_movement").sum()),
            "total_records": len(grp)
        })

    # Sort descending by month, ascending by airport
    rows.sort(key=lambda r: (r["month"], r["airport_id"]), reverse=True)

    return {
        "count": len(rows),
        "summary": rows,
        "disclaimer": "Missing actual telemetry intervals remain null (never zero). Scheduled services and observed movements represent different coverage windows and must never be combined into a single total."
    }

@router.get("/api/air-traffic/filter-options")
def get_air_traffic_filter_options():
    """
    Returns available filter options derived strictly from primary CSV and airport registry.
    Does not query SQLite.
    """
    df = load_primary_flight_events()

    # Extract active airport codes from CSV
    active_airports = sorted(df["airport_id"].unique().tolist())
    airports_list = []
    for ap_id in active_airports:
        reg = SYRIAN_AIRPORTS_REGISTRY.get(ap_id, {})
        airports_list.append({
            "airport_id": ap_id,
            "iata_code": reg.get("iata_code", ap_id),
            "icao_code": reg.get("icao_code", ""),
            "name": reg.get("name", f"Airport {ap_id}"),
            "name_ar": reg.get("name_ar", f"مطار {ap_id}")
        })

    # Months
    months = sorted([m for m in df["flight_date"].str.slice(0, 7).unique() if m], reverse=True)

    # Airlines
    airlines = sorted([a for a in df["airline_name"].unique() if a])

    # Destinations
    dest_df = df[["connected_airport_iata", "connected_airport_name", "connected_city"]].drop_duplicates()
    destinations = []
    for _, row in dest_df.iterrows():
        iata = row.get("connected_airport_iata")
        if iata and str(iata).strip():
            destinations.append({
                "connected_airport_iata": str(iata).strip().upper(),
                "connected_airport_name": str(row.get("connected_airport_name") or ""),
                "connected_city": str(row.get("connected_city") or "")
            })
    destinations.sort(key=lambda x: x["connected_airport_iata"])

    return {
        "airports": airports_list,
        "months": months,
        "airlines": airlines,
        "destinations": destinations
    }

@router.get("/api/air-traffic/export/events")
def export_air_traffic_events(
    airport_id: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    airline: Optional[str] = Query(None),
    destination: Optional[str] = Query(None),
    record_nature: Optional[str] = Query(None, description="Optional filter: scheduled_service, physical_movement, marketing_codeshare, unverified_movement"),
    format: str = Query("csv", regex="^(csv|xlsx)$")
):
    """
    Exports filtered flight events as CSV or Excel (XLSX) directly from primary CSV.
    Preserves original record_nature, evidence sources, and classification.
    """
    df = load_primary_flight_events()
    filtered = apply_filters(
        df=df,
        airport_id=airport_id,
        month=month,
        start_date=start_date,
        end_date=end_date,
        airline=airline,
        destination=destination
    )

    if isinstance(record_nature, str) and record_nature.strip():
        filtered = filtered[filtered["record_nature"] == record_nature.strip()]

    export_rows = []
    for _, r in filtered.iterrows():
        rn = r["record_nature"]
        nature_label = {
            "physical_movement": "ADS-B Observed Movement — Commercial Tracking Data (October 9–10 sample only)",
            "scheduled_service": "Scheduled Service",
            "marketing_codeshare": "Marketing Codeshare",
            "unverified_movement": "Unverified Movement"
        }.get(rn, rn)

        mov_type = str(r.get("movement_type") or "").strip().lower()
        connected = str(r.get("connected_airport_iata") or "")
        ap_code = str(r.get("airport_iata") or r.get("airport_id") or "")
        origin_code = connected if mov_type == "arrival" else ap_code
        dest_code = ap_code if mov_type == "arrival" else connected

        export_rows.append({
            "Date": r.get("flight_date", ""),
            "Airport": r.get("airport_id", ""),
            "Movement Type": mov_type.capitalize() if mov_type else "",
            "Actual/Scheduled Classification": nature_label,
            "Record Nature Key": rn,
            "Airline": r.get("airline_name", "") or "",
            "Origin": origin_code or "",
            "Destination": dest_code or "",
            "Flight Number": r.get("flight_number", "") or "",
            "Aircraft Type": r.get("aircraft_model", "") or "",
            "Aircraft Registration": r.get("aircraft_registration", "") or "",
            "Aircraft ICAO24": r.get("aircraft_icao24", "") or "",
            "Evidence / Source": r.get("source", "") or "",
            "Evidence Classification": r.get("observed_or_derived", "") or "",
            "Flight Status": str(r.get("flight_status", "")).capitalize()
        })

    out_df = pd.DataFrame(export_rows)

    if format == "xlsx":
        buf = io.BytesIO()
        out_df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="syrian_flight_events.xlsx"'}
        )
    else:
        buf = io.StringIO()
        out_df.to_csv(buf, index=False)
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="syrian_flight_events.csv"'}
        )

@router.get("/api/air-traffic/export/monthly")
def export_air_traffic_monthly(
    airport_id: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    airline: Optional[str] = Query(None),
    destination: Optional[str] = Query(None),
    format: str = Query("csv", regex="^(csv|xlsx)$")
):
    """
    Exports filtered monthly summary table derived from primary CSV.
    Preserves separation between scheduled and observed columns.
    """
    data_res = get_air_traffic_monthly_summary(
        airport_id=airport_id,
        month=month,
        start_date=start_date,
        end_date=end_date,
        airline=airline,
        destination=destination
    )
    rows = data_res["summary"]

    export_rows = []
    for r in rows:
        export_rows.append({
            "Month": r["month"],
            "Airport": r["airport_id"],
            "Scheduled Flights": r["scheduled_flights"],
            "Scheduled Arrivals": r["scheduled_arrivals"],
            "Scheduled Departures": r["scheduled_departures"],
            "Scheduled Airlines": r["scheduled_airlines"],
            "Scheduled Destinations": r["scheduled_destinations"],
            "Schedule Coverage Status": r["schedule_coverage_status"],
            "ADS-B Observed Movements — Commercial Tracking Data (October 9–10 sample only)": r["actual_movements"] if r["actual_movements"] is not None else "",
            "Observed Arrivals": r["observed_arrivals"] if r["observed_arrivals"] is not None else "",
            "Observed Departures": r["observed_departures"] if r["observed_departures"] is not None else "",
            "Observed Airlines": r["observed_airlines"] if r["observed_airlines"] is not None else "",
            "Observed Destinations": r["observed_destinations"] if r["observed_destinations"] is not None else "",
            "Observation Coverage Status": r["observation_coverage_status"],
            "Monitoring Outside Observed Dates": r["monitoring_outside_status"],
            "Passengers": "",  # Strictly empty string for missing figures
            "Marketing Codeshares": r["marketing_codeshares"],
            "Unverified Movements": r["unverified_movements"]
        })

    out_df = pd.DataFrame(export_rows)

    if format == "xlsx":
        buf = io.BytesIO()
        out_df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="syrian_air_traffic_monthly_summary.xlsx"'}
        )
    else:
        buf = io.StringIO()
        out_df.to_csv(buf, index=False)
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="syrian_air_traffic_monthly_summary.csv"'}
        )

@router.get("/api/air-traffic/export/coverage")
def export_air_traffic_coverage(
    airport_id: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: str = Query("csv", regex="^(csv|xlsx)$")
):
    """
    Exports independent Schedule Coverage and Actual Observation Coverage dimensions side-by-side.
    """
    cov_res = get_air_traffic_coverage(
        airport_id=airport_id,
        month=month,
        start_date=start_date,
        end_date=end_date
    )
    sched = cov_res["schedule_coverage"]
    obs = cov_res["observation_coverage"]

    export_rows = [{
        "Airport Scope": cov_res["airport_scope"],
        "Schedule Coverage Status": sched["status"],
        "Scheduled Flights": sched["scheduled_service_records"],
        "Scheduled Arrivals": sched["scheduled_arrivals"],
        "Scheduled Departures": sched["scheduled_departures"],
        "Dates with Schedule Records": sched["scheduled_dates_count"],
        "First Scheduled Date": sched["first_scheduled_date"] or "",
        "Last Scheduled Date": sched["last_scheduled_date"] or "",
        "Observation Coverage Status": obs["status"],
        "ADS-B Observed Movements (Commercial Tracking Data)": obs["observed_movements"] if obs["observed_movements"] is not None else "",
        "Observed Arrivals": obs["observed_arrivals"] if obs["observed_arrivals"] is not None else "",
        "Observed Departures": obs["observed_departures"] if obs["observed_departures"] is not None else "",
        "Dates with Observed Movement Records": obs["observed_dates_count"],
        "First Observed Date": obs["first_observed_date"] or "",
        "Last Observed Date": obs["last_observed_date"] or "",
        "Monitoring Coverage Outside Observed Dates": obs["monitoring_outside_status"]
    }]

    out_df = pd.DataFrame(export_rows)

    if format == "xlsx":
        buf = io.BytesIO()
        out_df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="syrian_air_traffic_coverage_summary.xlsx"'}
        )
    else:
        buf = io.StringIO()
        out_df.to_csv(buf, index=False)
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="syrian_air_traffic_coverage_summary.csv"'}
        )
