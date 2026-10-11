import json
import glob
import os
import pandas as pd
import sqlite3

def run_audit():
    print("=== 1. RAW FILES INVENTORY ===")
    for f in sorted(glob.glob("data/raw/*.json")):
        size = os.path.getsize(f)
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        if isinstance(data, list):
            print(f"{f}: {len(data)} items, {size} bytes")
        elif isinstance(data, dict):
            if "flights" in data:
                print(f"{f}: {len(data.get('flights', []))} flights (official airport portal), {size} bytes")
            elif "data" in data:
                total_claim = data.get("pagination", {}).get("total")
                print(f"{f}: {len(data['data'])} records (pagination.total={total_claim}), {size} bytes")
            else:
                print(f"{f}: dict with keys {list(data.keys())[:5]}, {size} bytes")

    print("\n=== 2. PROCESSED FILES INVENTORY ===")
    for f in sorted(glob.glob("data/processed/*")):
        size = os.path.getsize(f)
        if f.endswith(".csv"):
            df = pd.read_csv(f)
            print(f"{f}: {len(df)} rows, {len(df.columns)} columns, {size} bytes")
        elif f.endswith(".json"):
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            if isinstance(data, list):
                print(f"{f}: {len(data)} items, {size} bytes")
            else:
                print(f"{f}: summary dict, {size} bytes")

    print("\n=== 3. SQLITE DATABASE INVENTORY ===")
    conn = sqlite3.connect("data/damascus_airport.db")
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    for t in sorted(tables):
        count = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        cols = [c[1] for c in cur.execute(f"PRAGMA table_info({t})").fetchall()]
        print(f"Table '{t}': {count} rows, columns: {cols}")

    print("\n=== 4. FLIGHT EVENTS BY AIRPORT ===")
    cur.execute("SELECT airport_id, COUNT(*), MIN(flight_date), MAX(flight_date), COUNT(DISTINCT flight_date) FROM flight_events GROUP BY airport_id")
    for r in cur.fetchall():
        print(f"Airport: {r[0]} | Events: {r[1]} | Earliest: {r[2]} | Latest: {r[3]} | Distinct Dates: {r[4]}")

    print("\n=== 5. FLIGHT EVENTS DETAILED BREAKDOWN ===")
    cur.execute("SELECT source, COUNT(*), MIN(flight_date), MAX(flight_date) FROM flight_events GROUP BY source")
    for r in cur.fetchall():
        print(f"Source: {r[0]} | Count: {r[1]} | Earliest: {r[2]} | Latest: {r[3]}")

    cur.execute("SELECT movement_type, COUNT(*) FROM flight_events GROUP BY movement_type")
    for r in cur.fetchall():
        print(f"Movement Type: {r[0]} | Count: {r[1]}")

    cur.execute("SELECT flight_status, COUNT(*) FROM flight_events GROUP BY flight_status")
    for r in cur.fetchall():
        print(f"Status: {r[0]} | Count: {r[1]}")

    cur.execute("SELECT route_type, COUNT(*) FROM flight_events GROUP BY route_type")
    for r in cur.fetchall():
        print(f"Route Type: {r[0]} | Count: {r[1]}")

    # Null values analysis
    print("\n=== 6. NULL FIELD AUDIT IN FLIGHT EVENTS ===")
    total = cur.execute("SELECT COUNT(*) FROM flight_events").fetchone()[0]
    cur.execute("PRAGMA table_info(flight_events)")
    col_names = [c[1] for c in cur.fetchall()]
    for col in col_names:
        null_count = cur.execute(f"SELECT COUNT(*) FROM flight_events WHERE {col} IS NULL OR {col} = ''").fetchone()[0]
        pct = (null_count / total * 100) if total > 0 else 0
        if null_count > 0:
            print(f"Column '{col}': {null_count}/{total} null or empty ({pct:.1f}%)")

if __name__ == '__main__':
    run_audit()
