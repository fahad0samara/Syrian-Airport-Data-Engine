# -*- coding: utf-8 -*-
"""
Air Traffic Monitor API Router
Provides lightweight analytical endpoints, monthly aggregation, and multi-format exports (CSV/XLSX)
for the standalone Syrian Air Traffic Monitor interface.
"""
import io
import json
from typing import Optional, List, Dict, Any
from pathlib import Path
import pandas as pd
from fastapi import APIRouter, Query, HTTPException, Response
from fastapi.responses import HTMLResponse

from src.config import STATIC_DIR
from src.database import get_connection

router = APIRouter(tags=["Air Traffic Monitor"])

@router.get("/monitor", response_class=HTMLResponse)
@router.get("/air-traffic", response_class=HTMLResponse)
def get_air_traffic_monitor_page():
    """Serves the standalone Syrian Air Traffic Monitor page."""
    file_path = STATIC_DIR / "air_traffic_monitor.html"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Air Traffic Monitor page not found.")
    return HTMLResponse(content=file_path.read_text(encoding="utf-8"))

def _build_filter_clause(
    airport_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    airline: Optional[str] = None,
    destination: Optional[str] = None,
    month: Optional[str] = None
):
    where = ["1=1"]
    params = []
    if isinstance(airport_id, str) and airport_id.upper() not in ("ALL", ""):
        where.append("airport_id = ?")
        params.append(airport_id.upper())
    if isinstance(month, str) and month.strip():
        where.append("flight_date LIKE ?")
        params.append(f"{month.strip()}%")
    if isinstance(start_date, str) and start_date.strip():
        where.append("flight_date >= ?")
        params.append(start_date.strip())
    if isinstance(end_date, str) and end_date.strip():
        where.append("flight_date <= ?")
        params.append(end_date.strip())
    if isinstance(airline, str) and airline.strip():
        where.append("(airline_name = ? OR airline_iata = ? OR operating_carrier = ?)")
        params.extend([airline.strip(), airline.strip(), airline.strip()])
    if isinstance(destination, str) and destination.strip():
        where.append("(connected_airport_iata = ? OR connected_airport_icao = ? OR connected_city = ?)")
        params.extend([destination.strip().upper(), destination.strip().upper(), destination.strip()])

    return " AND ".join(where), params

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
    Returns the 5 key performance indicators for the Syrian Air Traffic Monitor:
    1. ADS-B Observed Movements — Commercial Tracking Data (October 9–10 sample only)
    2. Scheduled flights (full selected month or filtered period)
    3. Active airlines
    4. Active destinations
    5. Airports covered
    """
    effective_month = month or "2026-10"
    w_clause, params = _build_filter_clause(
        airport_id=airport_id,
        start_date=start_date,
        end_date=end_date,
        airline=airline,
        destination=destination,
        month=effective_month if not (start_date or end_date) else None
    )

    with get_connection() as conn:
        cur = conn.cursor()
        query = f"""
            SELECT
                sum(case when record_nature = 'physical_movement' then 1 else 0 end) as actual_movements,
                sum(case when record_nature = 'scheduled_service' then 1 else 0 end) as scheduled_flights,
                count(distinct case when airline_name is not null and airline_name != '' then airline_name end) as active_airlines,
                count(distinct case when connected_airport_iata is not null and connected_airport_iata != '' then connected_airport_iata end) as active_destinations,
                count(distinct airport_id) as airports_covered,
                min(flight_date) as min_date,
                max(flight_date) as max_date,
                count(*) as total_events
            FROM flight_events
            WHERE {w_clause}
        """
        cur.execute(query, params)
        r = cur.fetchone()

    # Determine whether actual movements were observed in the selected period
    # Note: Telemetry was observed on 2026-10-09 and 2026-10-10 only.
    # In periods without telemetry, actual_movements must be reported as null (unobserved), never 0.
    actual_count = r["actual_movements"]
    if actual_count == 0 and effective_month != "2026-10":
        actual_val = None
        actual_status = "unobserved_data_gap"
    else:
        actual_val = actual_count
        actual_status = "commercial_tracking_sample" if actual_count > 0 else "zero_movements_in_sample"

    scope_label = airport_id.upper() if (isinstance(airport_id, str) and airport_id.upper() != "ALL") else "All Syrian Aerodromes"

    return {
        "period": {
            "month": effective_month if not (start_date or end_date) else None,
            "start_date": r["min_date"],
            "end_date": r["max_date"],
            "label": f"October 2026 (Latest Available Month)" if effective_month == "2026-10" and not start_date else f"{r['min_date']} to {r['max_date']}"
        },
        "airport_scope": scope_label,
        "kpis": {
            "actual_movements": actual_val,
            "actual_movements_label": "ADS-B Observed Movements — Commercial Tracking Data (October 9–10 sample only)",
            "actual_movements_status": actual_status,
            "scheduled_flights": r["scheduled_flights"] or 0,
            "active_airlines": r["active_airlines"] or 0,
            "active_destinations": r["active_destinations"] or 0,
            "airports_covered": r["airports_covered"] or 0,
            "registered_airports_total": 7,
            "passengers": None,  # Strictly null: no reliable passenger source data exists
            "passengers_note": "No reliable passenger volume data published for this operational period."
        },
        "definitions": {
            "actual_movements": "ADS-B Observed Movements — Commercial Tracking Data (October 9–10 sample only). Physical movements (wheels-off/wheels-down) with Mode-S transponder telemetry. Marketing codeshares (20 records) and unverified movements (3 records) excluded. Not a full-month total.",
            "scheduled_flights": "Commercial timetable service slots published by official airport display boards across the entire selected period.",
            "active_airlines": "Distinct airline brands represented across the selected flight dataset (including scheduled timetable and marketing-code records). Physical aircraft operations in the Oct 9-10 ADS-B sample represent 17 distinct carriers.",
            "active_destinations": "Distinct destination/origin aerodromes connected to Syrian airports during the selected period.",
            "airports_covered": "Number of Syrian aerodromes with active flight records during the selected period out of 7 registered aerodromes."
        }
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
    Returns monthly aggregated summary table and chart series:
    Month | Airport | Actual Movements | Scheduled Flights | Arrivals | Departures | Passengers (null) | Airlines | Destinations
    """
    w_clause, params = _build_filter_clause(
        airport_id=airport_id,
        month=month,
        start_date=start_date,
        end_date=end_date,
        airline=airline,
        destination=destination
    )

    with get_connection() as conn:
        cur = conn.cursor()
        query = f"""
            SELECT
                substr(flight_date, 1, 7) as month,
                airport_id,
                sum(case when record_nature = 'physical_movement' then 1 else 0 end) as actual_movements,
                sum(case when record_nature = 'scheduled_service' then 1 else 0 end) as scheduled_flights,
                sum(case when record_nature = 'scheduled_service' and movement_type = 'arrival' then 1 else 0 end) as scheduled_arrivals,
                sum(case when record_nature = 'scheduled_service' and movement_type = 'departure' then 1 else 0 end) as scheduled_departures,
                count(distinct case when airline_name is not null and airline_name != '' then airline_name end) as active_airlines,
                count(distinct case when connected_airport_iata is not null and connected_airport_iata != '' then connected_airport_iata end) as active_destinations,
                count(*) as total_records
            FROM flight_events
            WHERE {w_clause}
            GROUP BY month, airport_id
            ORDER BY month DESC, airport_id ASC
        """
        cur.execute(query, params)
        raw_rows = cur.fetchall()

    rows = []
    for r in raw_rows:
        m = r["month"]
        # Handle unobserved actual movements strictly:
        # In 2026-09, no telemetry was captured; actual_movements is None (null), not 0!
        if m == "2026-09":
            actual_m = None
            actual_note = "Telemetry unobserved for September 2026; timetable display only."
        else:
            actual_m = r["actual_movements"]
            actual_note = "ADS-B Observed Movements — Commercial Tracking Data (October 9–10 sample only)"

        rows.append({
            "month": m,
            "airport_id": r["airport_id"],
            "actual_movements": actual_m,
            "actual_movements_label": "ADS-B Observed Movements — Commercial Tracking Data (October 9–10 sample only)",
            "actual_movements_note": actual_note,
            "scheduled_flights": r["scheduled_flights"],
            "scheduled_arrivals": r["scheduled_arrivals"],
            "scheduled_departures": r["scheduled_departures"],
            "passengers": None,  # Strictly null: no speculative capacity guessing
            "passengers_note": "No reliable passenger volume data published.",
            "active_airlines": r["active_airlines"],
            "active_destinations": r["active_destinations"],
            "total_records": r["total_records"]
        })

    return {
        "count": len(rows),
        "summary": rows,
        "disclaimer": "Missing actual telemetry intervals remain null (never zero). Passenger figures are not estimated without primary authoritative source data."
    }

@router.get("/api/air-traffic/filter-options")
def get_air_traffic_filter_options():
    """Returns available filter options for dropdowns in Syrian Air Traffic Monitor."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT airport_id, iata_code, icao_code, name, name_ar
            FROM airports
            ORDER BY airport_id ASC
        """)
        airports = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT DISTINCT substr(flight_date, 1, 7) as month
            FROM flight_events
            WHERE flight_date IS NOT NULL AND flight_date != ''
            ORDER BY month DESC
        """)
        months = [r["month"] for r in cur.fetchall()]

        cur.execute("""
            SELECT DISTINCT airline_name
            FROM flight_events
            WHERE airline_name IS NOT NULL AND airline_name != ''
            ORDER BY airline_name ASC
        """)
        airlines = [r["airline_name"] for r in cur.fetchall()]

        cur.execute("""
            SELECT DISTINCT connected_airport_iata, connected_airport_name, connected_city
            FROM flight_events
            WHERE connected_airport_iata IS NOT NULL AND connected_airport_iata != ''
            ORDER BY connected_airport_iata ASC
        """)
        destinations = [dict(r) for r in cur.fetchall()]

    return {
        "airports": airports,
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
    format: str = Query("csv", regex="^(csv|xlsx)$")
):
    """
    Exports filtered detailed flight events as CSV or Excel (XLSX).
    Required columns:
    Date, Airport, Arrival/Departure, Actual/Scheduled Classification, Airline, Origin, Destination,
    Flight Number, Aircraft Type, Evidence/Source, Evidence Classification, Flight Status.
    """
    w_clause, params = _build_filter_clause(
        airport_id=airport_id,
        start_date=start_date,
        end_date=end_date,
        airline=airline,
        destination=destination,
        month=month
    )

    with get_connection() as conn:
        cur = conn.cursor()
        query = f"""
            SELECT
                flight_date,
                airport_id,
                movement_type,
                record_nature,
                airline_name,
                case when movement_type = 'arrival' then connected_airport_iata else airport_iata end as origin_code,
                case when movement_type = 'departure' then connected_airport_iata else airport_iata end as destination_code,
                flight_number,
                aircraft_model,
                source,
                observed_or_derived,
                flight_status,
                actual_dep_time,
                actual_arr_time,
                scheduled_dep_time,
                scheduled_arr_time
            FROM flight_events
            WHERE {w_clause}
            ORDER BY flight_date DESC, flight_number ASC
        """
        cur.execute(query, params)
        raw = cur.fetchall()

    export_rows = []
    for r in raw:
        nature_label = {
            "physical_movement": "ADS-B Observed Movement — Commercial Tracking Data (October 9–10 sample only)",
            "scheduled_service": "Scheduled Service",
            "marketing_codeshare": "Marketing Codeshare",
            "unverified_movement": "Unverified Movement"
        }.get(r["record_nature"], r["record_nature"])

        export_rows.append({
            "Date": r["flight_date"],
            "Airport": r["airport_id"],
            "Movement Type": r["movement_type"].capitalize() if r["movement_type"] else "",
            "Actual/Scheduled Classification": nature_label,
            "Airline": r["airline_name"] or "",
            "Origin": r["origin_code"] or "",
            "Destination": r["destination_code"] or "",
            "Flight Number": r["flight_number"] or "",
            "Aircraft Type": r["aircraft_model"] or "",
            "Evidence / Source": r["source"] or "",
            "Evidence Classification": r["observed_or_derived"] or "",
            "Flight Status": r["flight_status"].capitalize() if r["flight_status"] else ""
        })

    df = pd.DataFrame(export_rows)

    if format == "xlsx":
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="syrian_flight_events.xlsx"'}
        )
    else:
        buf = io.StringIO()
        df.to_csv(buf, index=False)
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
    Exports filtered monthly summary table as CSV or Excel (XLSX).
    Columns:
    Month, Airport, ADS-B Observed Movements — Commercial Tracking Data (October 9–10 sample only),
    Scheduled Flights, Scheduled Arrivals, Scheduled Departures, Passengers (null), Active Airlines, Active Destinations.
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
            "ADS-B Observed Movements — Commercial Tracking Data (October 9–10 sample only)": r["actual_movements"] if r["actual_movements"] is not None else "",
            "Scheduled Flights": r["scheduled_flights"],
            "Scheduled Arrivals": r["scheduled_arrivals"],
            "Scheduled Departures": r["scheduled_departures"],
            "Passengers": "",  # Strictly empty string for missing passenger figures
            "Active Airlines": r["active_airlines"],
            "Active Destinations": r["active_destinations"]
        })

    df = pd.DataFrame(export_rows)

    if format == "xlsx":
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="syrian_air_traffic_monthly_summary.xlsx"'}
        )
    else:
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="syrian_air_traffic_monthly_summary.csv"'}
        )
