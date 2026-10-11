import urllib.request
import json
import os
import re
import base64
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from src.config import AVIATIONSTACK_KEY, RAW_DATA_DIR, PROCESSED_DATA_DIR, REPORTS_DIR

def save_with_snapshot(filename: str, data: Any):
    # 1. Main raw folder
    filepath = RAW_DATA_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # 2. Timestamped snapshot directory
    snapshot_dir = RAW_DATA_DIR / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    snapshot_path = snapshot_dir / f"{ts}_{filename}"
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def main():
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. AviationStack DAM departures & arrivals
    if AVIATIONSTACK_KEY:
        print("1. Fetching AviationStack DAM departures...")
        try:
            url_dep = f"https://api.aviationstack.com/v1/flights?access_key={AVIATIONSTACK_KEY}&dep_iata=DAM&limit=100"
            res = urllib.request.urlopen(url_dep, timeout=20)
            as_dep = json.loads(res.read())
            save_with_snapshot("aviationstack_dam_departures_raw.json", as_dep)
            count_dep = len(as_dep.get("data", []))
            print(f"Saved AviationStack departures: {count_dep} flights")
        except Exception as e:
            print(f"AviationStack dep error: {e}")

        print("Fetching AviationStack DAM arrivals...")
        try:
            url_arr = f"https://api.aviationstack.com/v1/flights?access_key={AVIATIONSTACK_KEY}&arr_iata=DAM&limit=100"
            res = urllib.request.urlopen(url_arr, timeout=20)
            as_arr = json.loads(res.read())
            save_with_snapshot("aviationstack_dam_arrivals_raw.json", as_arr)
            count_arr = len(as_arr.get("data", []))
            print(f"Saved AviationStack arrivals: {count_arr} flights")
        except Exception as e:
            print(f"AviationStack arr error: {e}")
    else:
        print("1. AVIATIONSTACK_KEY environment variable not set. Using existing verified raw snapshot.")

    # 2. Flightradar24 DAM arrivals and departures
    print("2. Fetching Flightradar24 DAM data...")
    fr24_arr_all = []
    fr24_dep_all = []
    for p in [-1, 1]:
        try:
            url_fr = f"https://api.flightradar24.com/common/v1/airport.json?code=dam&plugin[]=&plugin-setting[extended][medata]=1&page={p}"
            req = urllib.request.Request(url_fr, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            res = urllib.request.urlopen(req, timeout=20)
            data = json.loads(res.read())
            sched = data.get("result", {}).get("response", {}).get("airport", {}).get("pluginData", {}).get("schedule", {})
            arr_data = sched.get("arrivals", {}).get("data", [])
            dep_data = sched.get("departures", {}).get("data", [])
            fr24_arr_all.extend(arr_data)
            fr24_dep_all.extend(dep_data)
        except Exception as e:
            print(f"FR24 page {p} error: {e}")

    if fr24_arr_all:
        save_with_snapshot("flightradar24_dam_arrivals_raw.json", fr24_arr_all)
    if fr24_dep_all:
        save_with_snapshot("flightradar24_dam_departures_raw.json", fr24_dep_all)
    print(f"Saved Flightradar24: {len(fr24_arr_all)} arrivals, {len(fr24_dep_all)} departures")

    # 3. Syria Economic Monitor Bokeh time-series extraction
    print("3. Extracting Syria Economic Monitor historical aviation time-series...")
    sem_url = "https://datapartnership.org/syria-economic-monitor/notebooks/aviation/aviation_update.html"
    try:
        req = urllib.request.Request(sem_url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
        matches = re.findall(r"const docs_json = ({.*?});\s*const render_items", html, re.DOTALL)

        def decode_val(val):
            if isinstance(val, dict) and val.get("type") == "ndarray":
                arr_info = val["array"]
                if isinstance(arr_info, dict) and "data" in arr_info:
                    b = base64.b64decode(arr_info["data"])
                    dt = np.dtype(val["dtype"])
                    if val.get("order") == "little":
                        dt = dt.newbyteorder("<")
                    return np.frombuffer(b, dtype=dt).tolist()
                elif isinstance(arr_info, list):
                    return arr_info
            return val

        extracted_data = {}
        for i, m in enumerate(matches):
            d = json.loads(m)
            for doc_id, doc in d.items():
                for r in doc.get("roots", []):
                    title = r.get("attributes", {}).get("title", {}).get("attributes", {}).get("text") if isinstance(r.get("attributes", {}).get("title"), dict) else f"figure_{i}"
                    
                    def find_sources(obj):
                        sources = []
                        if isinstance(obj, dict):
                            if obj.get("name") == "ColumnDataSource":
                                sources.append(obj)
                            for k, v in obj.items():
                                sources.extend(find_sources(v))
                        elif isinstance(obj, list):
                            for item in obj:
                                sources.extend(find_sources(item))
                        return sources
                    
                    sources = find_sources(r)
                    for s in sources:
                        entries = s.get("attributes", {}).get("data", {}).get("entries", [])
                        if entries:
                            cols = {}
                            for col_name, col_data in entries:
                                cols[col_name] = decode_val(col_data)
                            try:
                                df = pd.DataFrame(cols)
                                if "flight_date" in df.columns:
                                    df["flight_date_iso"] = pd.to_datetime(df["flight_date"], unit="ms").dt.strftime("%Y-%m-%d")
                                    extracted_data[title] = df.to_dict(orient="records")
                                elif "airportcity" in df.columns:
                                    extracted_data[f"routes_{title}_{s.get('id')}"] = df.to_dict(orient="records")
                            except Exception:
                                pass

        for title, records in extracted_data.items():
            filename = re.sub(r"[^a-zA-Z0-9_]", "_", title.lower()).strip("_") + ".json"
            save_with_snapshot(filename, records)
            print(f"Saved {filename}: {len(records)} records")
    except Exception as e:
        print(f"SEM extraction note: {e}")

    # 4. OurAirports metadata for OSDI
    print("4. Saving Damascus Airport (OSDI/DAM) reference metadata...")
    dam_airport_metadata = {
        "id": "5833",
        "ident": "OSDI",
        "type": "large_airport",
        "name": "Damascus International Airport",
        "latitude_deg": 33.415001,
        "longitude_deg": 36.515202,
        "elevation_ft": 2021,
        "continent": "AS",
        "iso_country": "SY",
        "iso_region": "SY-DI",
        "municipality": "Damascus",
        "scheduled_service": "yes",
        "gps_code": "OSDI",
        "iata_code": "DAM",
        "local_code": "",
        "runways": [
            {
                "ident": "05R/23L",
                "length_ft": 11811,
                "width_ft": 148,
                "surface": "ASP",
                "lighted": 1,
                "closed": 0
            },
            {
                "ident": "05L/23R",
                "length_ft": 9843,
                "width_ft": 148,
                "surface": "ASP",
                "lighted": 1,
                "closed": 0
            }
        ]
    }
    save_with_snapshot("damascus_airport_metadata.json", dam_airport_metadata)
    print("Saved damascus_airport_metadata.json")

if __name__ == "__main__":
    main()
