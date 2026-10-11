import urllib.request
import json
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
import sys
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.config import RAW_DATA_DIR, AVIATIONSTACK_KEY
from src.adapters.flightradar24 import Flightradar24Adapter

def save_payload(filename: str, data: any) -> Path:
    raw_dir = RAW_DATA_DIR
    snapshot_dir = raw_dir / "snapshots"
    raw_dir.mkdir(parents=True, exist_ok=True)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    p = raw_dir / filename
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    sp = snapshot_dir / f"{ts_str}_{filename}"
    with open(sp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    count = len(data) if isinstance(data, list) else len(data.get("flights", []))
    print(f" -> Saved {filename} ({count} items)")
    return p

def fetch_all():
    print("=" * 60)
    print("FETCHING REAL AVIATION DATA FOR ALL SYRIAN AIRPORTS")
    print("=" * 60)

    # 1. Official Damascus Portal
    print("\n[1] Fetching official Damascus International Airport flights (damairport.gov.sy)...")
    try:
        req = urllib.request.Request("https://damairport.gov.sy/api/flights.php", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as res:
            d = json.loads(res.read().decode("utf-8"))
            save_payload("damairport_official_flights_raw.json", d)
    except Exception as e:
        print(f"Error fetching damairport: {e}")

    # 2. Official Aleppo Portal
    print("\n[2] Fetching official Aleppo International Airport flights (alpairport.gov.sy)...")
    try:
        req = urllib.request.Request("https://alpairport.gov.sy/api/flights.php", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as res:
            d = json.loads(res.read().decode("utf-8"))
            save_payload("alpairport_official_flights_raw.json", d)
    except Exception as e:
        print(f"Error fetching alpairport: {e}")

    # 3. Official Qamishli Portal
    print("\n[3] Querying official Qamishli Airport portal (qamishliairport.gov.sy)...")
    try:
        req = urllib.request.Request("https://qamishliairport.gov.sy/api/flights.php", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as res:
            d = json.loads(res.read().decode("utf-8"))
            save_payload("qamishliairport_official_flights_raw.json", d)
    except Exception as e:
        print(f"Error querying qamishliairport: {e}")

    # 4. Official Deir ez-Zor Portal
    print("\n[4] Querying official Deir ez-Zor Airport portal (deirezzorairport.gov.sy)...")
    try:
        req = urllib.request.Request("https://deirezzorairport.gov.sy/api/flights.php", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as res:
            d = json.loads(res.read().decode("utf-8"))
            save_payload("deirezzorairport_official_flights_raw.json", d)
    except Exception as e:
        print(f"Error querying deirezzorairport: {e}")

    # 5. Flightradar24 airport schedules for Syrian airports
    print("\n[5] Querying Flightradar24 feeds for Syrian airports...")
    for code in ["dam", "alp", "ltk", "kac", "dez"]:
        arr_all = []
        dep_all = []
        for p in [-1, 1]:
            try:
                url = f"https://api.flightradar24.com/common/v1/airport.json?code={code}&plugin[]=&plugin-setting[extended][medata]=1&page={p}"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                with urllib.request.urlopen(req, timeout=15) as res:
                    data = json.loads(res.read().decode("utf-8"))
                    sched = data.get("result", {}).get("response", {}).get("airport", {}).get("pluginData", {}).get("schedule", {})
                    arr_all.extend(sched.get("arrivals", {}).get("data", []))
                    dep_all.extend(sched.get("departures", {}).get("data", []))
            except Exception as e:
                pass
        if arr_all or dep_all:
            fr_adapter = Flightradar24Adapter()
            arr_merged = fr_adapter.merge_rolling_records(f"flightradar24_{code}_arrivals_raw.json", arr_all)
            dep_merged = fr_adapter.merge_rolling_records(f"flightradar24_{code}_departures_raw.json", dep_all)
            save_payload(f"flightradar24_{code}_arrivals_raw.json", arr_merged)
            save_payload(f"flightradar24_{code}_departures_raw.json", dep_merged)
        else:
            print(f" -> FR24 {code.upper()}: 0 flights reported")

    # 6. AviationStack (if key is set)
    if AVIATIONSTACK_KEY:
        print("\n[6] Querying AviationStack API for Syrian airports...")
        for code in ["DAM", "ALP", "LTK", "KAC", "DEZ"]:
            for direction, iata_param in [("departures", "dep_iata"), ("arrivals", "arr_iata")]:
                try:
                    url = f"https://api.aviationstack.com/v1/flights?access_key={AVIATIONSTACK_KEY}&{iata_param}={code}&limit=100"
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=15) as res:
                        as_data = json.loads(res.read().decode("utf-8"))
                        save_payload(f"aviationstack_{code.lower()}_{direction}_raw.json", as_data)
                except Exception as e:
                    print(f"AviationStack {code} {direction} error: {e}")
    else:
        print("\n[6] AVIATIONSTACK_KEY not configured in env. Existing verified snapshots preserved.")

    print("\n" + "=" * 60)
    print("ALL RAW DATA FETCHING COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    fetch_all()
