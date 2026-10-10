import sqlite3
from typing import Generator
from src.config import DB_PATH

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS flight_events (
            event_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            source_record_id TEXT,
            movement_type TEXT NOT NULL,
            airport_iata TEXT DEFAULT 'DAM',
            airport_icao TEXT DEFAULT 'OSDI',
            connected_airport_iata TEXT,
            connected_airport_icao TEXT,
            connected_airport_name TEXT,
            connected_country TEXT,
            connected_city TEXT,
            route_type TEXT,
            airline_name TEXT,
            airline_iata TEXT,
            airline_icao TEXT,
            flight_number TEXT,
            flight_date TEXT NOT NULL,
            flight_status TEXT NOT NULL,
            scheduled_dep_time TEXT,
            actual_dep_time TEXT,
            scheduled_arr_time TEXT,
            actual_arr_time TEXT,
            aircraft_model TEXT,
            aircraft_registration TEXT,
            aircraft_icao24 TEXT,
            raw_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_flight_date ON flight_events(flight_date);
        CREATE INDEX IF NOT EXISTS idx_movement_type ON flight_events(movement_type);
        CREATE INDEX IF NOT EXISTS idx_flight_status ON flight_events(flight_status);
        CREATE INDEX IF NOT EXISTS idx_airline ON flight_events(airline_name);
        CREATE INDEX IF NOT EXISTS idx_source ON flight_events(source);
        CREATE INDEX IF NOT EXISTS idx_flight_number ON flight_events(flight_number);

        CREATE TABLE IF NOT EXISTS damascus_daily_movements (
            flight_date TEXT PRIMARY KEY,
            arrival_count INTEGER,
            departure_count INTEGER,
            total_movements INTEGER,
            landed_count INTEGER,
            cancelled_count INTEGER,
            diverted_count INTEGER,
            scheduled_count INTEGER,
            active_count INTEGER,
            domestic_count INTEGER,
            international_count INTEGER,
            unique_aircraft_count INTEGER,
            unique_airlines_count INTEGER,
            completeness_status TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS historical_daily_movements_2024 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_date TEXT NOT NULL,
            movement_type TEXT NOT NULL,
            scope TEXT NOT NULL,
            active INTEGER DEFAULT 0,
            cancelled INTEGER DEFAULT 0,
            diverted INTEGER DEFAULT 0,
            landed INTEGER DEFAULT 0,
            scheduled INTEGER DEFAULT 0,
            unknown INTEGER DEFAULT 0,
            total_recorded_operations INTEGER DEFAULT 0,
            data_source TEXT,
            status_note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(flight_date, movement_type, scope)
        );

        CREATE INDEX IF NOT EXISTS idx_hist_date ON historical_daily_movements_2024(flight_date);
        CREATE INDEX IF NOT EXISTS idx_hist_type ON historical_daily_movements_2024(movement_type);

        CREATE TABLE IF NOT EXISTS data_quality_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            check_name TEXT NOT NULL,
            passed INTEGER NOT NULL,
            metric_value REAL,
            details TEXT
        );
        """)

if __name__ == '__main__':
    init_db()
    print(f"Initialized database at: {DB_PATH}")
