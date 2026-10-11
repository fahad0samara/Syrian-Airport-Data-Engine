import json
import sqlite3
from pathlib import Path

def trace():
    # 1. Search in DB
    conn = sqlite3.connect('data/damascus_airport.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM flight_events WHERE flight_number = 'RJ435' OR event_id = 'daeb7ccbd61341a2'")
    rows = [dict(r) for r in cur.fetchall()]
    print(f"DB occurrences of RJ435 / daeb7ccbd61341a2: {len(rows)}")
    for r in rows:
        print("DB row:", {k: r[k] for k in ['event_id', 'flight_number', 'airport_id', 'movement_type', 'flight_date', 'flight_status', 'record_nature', 'source', 'source_record_id', 'actual_arr_time', 'aircraft_registration', 'aircraft_icao24']})

    cur.execute("SELECT * FROM deduplication_audit WHERE canonical_event_id = 'daeb7ccbd61341a2' OR flight_number = 'RJ435'")
    audits = [dict(r) for r in cur.fetchall()]
    print(f"\nDeduplication audit entries: {len(audits)}")
    for a in audits:
        print("Audit entry:", a)
    conn.close()

    # 2. Search in snapshots
    snap_dir = Path('data/raw/snapshots')
    print("\nSearching in snapshots for RJ435...")
    for s in sorted(snap_dir.glob('*.json')):
        text = s.read_text(encoding='utf-8')
        if 'RJ435' in text or 'RJ 435' in text or 'RJA435' in text:
            print(f"  Found in snapshot: {s.name} ({s.stat().st_size} bytes)")

    # 3. Inspect RJ435 payloads across snapshots
    base_snap = snap_dir / '20261010_144557_flightradar24_dam_arrivals_raw.json'
    if base_snap.exists():
        with open(base_snap, encoding='utf-8') as f:
            base_data = json.load(f)
        print("\n=== BASELINE FR24 DAM ARRIVALS (20261010_144557) ===")
        rj_base = [x for x in base_data if 'RJ435' in json.dumps(x)]
        print(f"Matches for RJ435: {len(rj_base)}")
        for x in rj_base:
            fl = x.get('flight', {})
            sched = fl.get('time', {}).get('scheduled', {})
            real = fl.get('time', {}).get('real', {})
            aircraft = fl.get('aircraft', {})
            st = fl.get('status', {})
            print(f"  Flight: {fl.get('identification', {}).get('number', {}).get('default')} | ID: {fl.get('identification', {}).get('id')} | aircraft: {aircraft.get('model', {}).get('code')} (reg: {aircraft.get('registration')}, hex: {aircraft.get('hex')}) | status: {st.get('text')} | sched_arr: {sched.get('arrival')} | real_arr: {real.get('arrival')}")

    live_snap = snap_dir / '20261010_164054_flightradar24_dam_arrivals_raw.json'
    if live_snap.exists():
        with open(live_snap, encoding='utf-8') as f:
            live_data = json.load(f)
        print("\n=== LIVE FR24 DAM ARRIVALS (20261010_164054) ===")
        rj_live = [x for x in live_data if 'RJ435' in json.dumps(x)]
        print(f"Matches for RJ435: {len(rj_live)}")
        for x in rj_live:
            fl = x.get('flight', {})
            sched = fl.get('time', {}).get('scheduled', {})
            real = fl.get('time', {}).get('real', {})
            aircraft = fl.get('aircraft', {})
            st = fl.get('status', {})
            print(f"  Flight: {fl.get('identification', {}).get('number', {}).get('default')} | ID: {fl.get('identification', {}).get('id')} | aircraft: {aircraft.get('model', {}).get('code')} (reg: {aircraft.get('registration')}, hex: {aircraft.get('hex')}) | status: {st.get('text')} | sched_arr: {sched.get('arrival')} | real_arr: {real.get('arrival')}")

if __name__ == '__main__':
    trace()
