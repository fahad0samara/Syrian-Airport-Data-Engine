import json
from pathlib import Path
from typing import Optional, List
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
)
from src.database import get_connection

app = FastAPI(
    title="Damascus International Airport Data Engine",
    description="Empirical flight operations database and analytical engine for Damascus International Airport (DAM/OSDI), Syria.",
    version="1.0.0"
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

@app.get("/", response_class=HTMLResponse)
@app.get("/data", response_class=HTMLResponse)
def get_data_tab():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return "<h1>Damascus Airport Data Engine</h1><p>Data tab UI loading...</p>"

@app.get("/api/airport")
def get_airport_info():
    meta_path = RAW_DATA_DIR / "damascus_airport_metadata.json"
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "ident": AIRPORT_ICAO,
        "iata_code": AIRPORT_IATA,
        "name": AIRPORT_NAME,
        "country": "Syria",
    }

@app.get("/api/flights")
def get_flights(
    date: Optional[str] = Query(None, description="Filter by YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    movement_type: Optional[str] = Query(None, description="arrival or departure"),
    status: Optional[str] = Query(None, description="landed, active, scheduled, cancelled, diverted"),
    airline: Optional[str] = Query(None, description="Filter by airline name or code"),
    route_type: Optional[str] = Query(None, description="domestic or international"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    query = "SELECT * FROM flight_events WHERE 1=1"
    params = []

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
    if airline:
        query += " AND (airline_name LIKE ? OR airline_iata = ? OR airline_icao = ?)"
        pattern = f"%{airline}%"
        params.extend([pattern, airline.upper(), airline.upper()])
    if route_type:
        query += " AND route_type = ?"
        params.append(route_type.lower())

    count_query = f"SELECT COUNT(*) FROM ({query})"

    query += " ORDER BY flight_date DESC, coalesce(scheduled_dep_time, scheduled_arr_time) DESC LIMIT ? OFFSET ?"
    params_paged = list(params) + [limit, offset]

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]

        cursor.execute(query, params_paged)
        rows = cursor.fetchall()
        flights = []
        for r in rows:
            d = dict(r)
            if "raw_json" in d:
                del d["raw_json"]
            flights.append(d)

    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "data": flights
    }

@app.get("/api/flights/{event_id}")
def get_flight_detail(event_id: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM flight_events WHERE event_id = ?", (event_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Flight event not found")
        d = dict(row)
        if d.get("raw_json"):
            try:
                d["raw_json"] = json.loads(d["raw_json"])
            except Exception:
                pass
        return d

@app.get("/api/movements/daily")
def get_daily_movements():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM damascus_daily_movements ORDER BY flight_date ASC")
        rows = [dict(r) for r in cursor.fetchall()]
    return {"total_days": len(rows), "data": rows}

@app.get("/api/movements/historical-2024")
def get_historical_2024(
    movement_type: Optional[str] = Query(None, description="arrival or departure"),
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    query = "SELECT * FROM historical_daily_movements_2024 WHERE 1=1"
    params = []
    if movement_type:
        query += " AND movement_type = ?"
        params.append(movement_type.lower())
    
    count_query = f"SELECT COUNT(*) FROM ({query})"
    query += " ORDER BY flight_date ASC, movement_type ASC LIMIT ? OFFSET ?"
    params_paged = list(params) + [limit, offset]

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]

        cursor.execute(query, params_paged)
        rows = [dict(r) for r in cursor.fetchall()]

    return {"total": total_count, "limit": limit, "offset": offset, "data": rows}

@app.get("/api/movements/stats")
def get_movement_stats():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM flight_events")
        total_flights = cursor.fetchone()[0]

        cursor.execute("SELECT movement_type, COUNT(*) FROM flight_events GROUP BY movement_type")
        by_movement = {r[0]: r[1] for r in cursor.fetchall()}

        cursor.execute("SELECT flight_status, COUNT(*) FROM flight_events GROUP BY flight_status")
        by_status = {r[0]: r[1] for r in cursor.fetchall()}

        cursor.execute("SELECT route_type, COUNT(*) FROM flight_events GROUP BY route_type")
        by_route = {r[0]: r[1] for r in cursor.fetchall()}

        cursor.execute("""
            SELECT connected_airport_iata, connected_airport_name, connected_city, COUNT(*) as cnt
            FROM flight_events
            WHERE connected_airport_iata IS NOT NULL
            GROUP BY connected_airport_iata
            ORDER BY cnt DESC LIMIT 10
        """)
        top_destinations = [
            {"iata": r[0], "name": r[1], "city": r[2], "flights": r[3]}
            for r in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT coalesce(airline_name, airline_iata, 'Unknown'), COUNT(*) as cnt
            FROM flight_events
            GROUP BY 1
            ORDER BY cnt DESC LIMIT 10
        """)
        top_airlines = [
            {"airline": r[0], "flights": r[1]}
            for r in cursor.fetchall()
        ]

        cursor.execute("SELECT COUNT(DISTINCT coalesce(aircraft_registration, aircraft_icao24)) FROM flight_events WHERE aircraft_registration IS NOT NULL OR aircraft_icao24 IS NOT NULL")
        unique_aircraft = cursor.fetchone()[0]

    return {
        "airport": AIRPORT_NAME,
        "iata": AIRPORT_IATA,
        "icao": AIRPORT_ICAO,
        "total_verified_flights": total_flights,
        "by_movement_type": by_movement,
        "by_status": by_status,
        "by_route_type": by_route,
        "unique_aircraft_tracked": unique_aircraft,
        "top_connected_airports": top_destinations,
        "top_airlines": top_airlines,
    }

@app.get("/api/coverage")
def get_coverage():
    rep_path = REPORTS_DIR / "coverage_report.json"
    if rep_path.exists():
        with open(rep_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@app.get("/api/quality")
def get_quality():
    qa_path = REPORTS_DIR / "quality_audit.json"
    if qa_path.exists():
        with open(qa_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"status": "No audit available"}

@app.get("/api/export/{dataset}")
def export_dataset(dataset: str, format: str = Query("csv", pattern="^(csv|json)$")):
    mapping = {
        "damascus_flights": ("damascus_flight_events.csv", "damascus_flight_events.json"),
        "damascus_daily": ("damascus_daily_movements.csv", "damascus_daily_movements.json"),
        "historical_2024": ("historical_daily_movements_2024.csv", "historical_daily_movements_2024.json"),
        "coverage_report": ("coverage_report.csv", "coverage_report.json"),
    }

    if dataset not in mapping:
        raise HTTPException(status_code=404, detail="Dataset not found. Choose: damascus_flights, damascus_daily, historical_2024, coverage_report")

    csv_name, json_name = mapping[dataset]
    target_name = csv_name if format == "csv" else json_name
    
    file_path = PROCESSED_DATA_DIR / target_name
    if not file_path.exists():
        file_path = REPORTS_DIR / target_name
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Export file {target_name} not found")

    media_type = "text/csv" if format == "csv" else "application/json"
    return FileResponse(file_path, media_type=media_type, filename=target_name)
