#!/usr/bin/env python3
"""
Syrian Airport Data Engine — Version 2.7
Free Aviation APIs Discovery & Damascus Airport Coverage Assessment

Tests public, free aviation APIs for Damascus International Airport (DAM / OSDI).
Measures real-time aircraft visibility across 10 km, 25 km, 50 km, 100 km, and 150 km radii.

SAFETY RULES:
- STRICTLY READ-ONLY with respect to data/damascus_airport.db (no connection or modification).
- All raw responses and manifests are written exclusively to data/free_api_research/.
- Handles timeouts, HTTP 403, 429, 500 cleanly without crashing.
"""

import os
import sys
import json
import math
import time
import ssl
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone

# Target Airport: Damascus International Airport (DAM / OSDI)
OSDI_LAT = 33.4115
OSDI_LON = 36.5156
OSDI_ELEVATION_FT = 2020.0
OSDI_ICAO = "OSDI"
OSDI_IATA = "DAM"

# Radii in kilometers and converted to nautical miles
RADII_KM = [10, 25, 50, 100, 150]
KM_TO_NM = 0.539957

# Base output directory
BASE_OUT_DIR = os.path.join("data", "free_api_research")


def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate Great Circle distance between two points in kilometers."""
    r = 6371.0  # Earth radius in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def get_bounding_box_degrees(lat, lon, max_km):
    """Calculate lat/lon bounding box for OpenSky query."""
    delta_lat = max_km / 111.0
    delta_lon = max_km / (111.0 * math.cos(math.radians(lat)))
    return {
        "lamin": round(lat - delta_lat, 4),
        "lamax": round(lat + delta_lat, 4),
        "lomin": round(lon - delta_lon, 4),
        "lomax": round(lon + delta_lon, 4),
    }


def compute_sha256(content_bytes):
    return hashlib.sha256(content_bytes).hexdigest()


def classify_trajectory(ac):
    """
    Classify movement based on V2.7 criteria:
    - overflight_observed: altitude >= 15,000 ft or cruise speed
    - approach_candidate: descending toward OSDI on approach bearing
    - departure_candidate: ascending away from OSDI DER
    - ground_observation: within airport boundary at elevation with onground=True
    - confirmed_movement: only with multiple surface rollout fixes (requires trajectory tracking)
    - insufficient_evidence: missing altitude/speed or single fix
    """
    alt = ac.get("alt_baro_ft") or ac.get("alt_geom_ft")
    gs = ac.get("speed_kts")
    vr = ac.get("vertrate_fpm")
    dist = ac.get("distance_km")
    onground = ac.get("onground", False)

    if alt is None or dist is None:
        return "insufficient_evidence"

    # Surface ground observation
    if onground or (dist <= 5.0 and alt <= 2200.0 and (gs is None or gs < 80.0)):
        return "ground_observation"

    # High-altitude overflight
    if alt >= 15000.0:
        return "overflight_observed"

    # Terminal approach candidate
    if dist <= 30.0 and alt < 10000.0 and vr is not None and vr < -300:
        return "approach_candidate"

    # Terminal departure candidate
    if dist <= 25.0 and alt < 10000.0 and vr is not None and vr > 500:
        return "departure_candidate"

    if alt < 15000.0:
        return "terminal_area_transit"

    return "insufficient_evidence"


class FreeAviationTester:
    def __init__(self):
        self.ssl_ctx = ssl.create_default_context()
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.results = {}

    def fetch_url(self, url, headers=None, timeout=12):
        req_headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(url, headers=req_headers)
        req_time = datetime.now(timezone.utc)
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=self.ssl_ctx) as resp:
                status = resp.status
                body = resp.read()
                return {
                    "status": status,
                    "body": body,
                    "error": None,
                    "timestamp": req_time.isoformat(),
                }
        except urllib.error.HTTPError as e:
            return {
                "status": e.code,
                "body": e.read(),
                "error": f"HTTP {e.code}: {e.reason}",
                "timestamp": req_time.isoformat(),
            }
        except Exception as e:
            return {
                "status": 0,
                "body": None,
                "error": str(e),
                "timestamp": req_time.isoformat(),
            }

    def save_raw_and_manifest(self, provider_dir, base_filename, raw_bytes, manifest_data):
        target_dir = os.path.join(BASE_OUT_DIR, provider_dir)
        os.makedirs(target_dir, exist_ok=True)
        raw_path = os.path.join(target_dir, base_filename)

        if raw_bytes:
            with open(raw_path, "wb") as f:
                f.write(raw_bytes)
            file_hash = compute_sha256(raw_bytes)
        else:
            file_hash = "NONE"

        manifest_data["response_file"] = raw_path
        manifest_data["file_sha256"] = file_hash

        manifest_dir = os.path.join(BASE_OUT_DIR, "manifests")
        os.makedirs(manifest_dir, exist_ok=True)
        manifest_path = os.path.join(manifest_dir, f"manifest_{base_filename}.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        return raw_path, file_hash

    def test_opensky(self):
        print("\n--- Testing OpenSky Network API ---")
        bbox = get_bounding_box_degrees(OSDI_LAT, OSDI_LON, max_km=150)
        url = (
            f"https://opensky-network.org/api/states/all"
            f"?lamin={bbox['lamin']}&lamax={bbox['lamax']}"
            f"&lomin={bbox['lomin']}&lomax={bbox['lomax']}"
        )
        print(f"URL: {url}")
        res = self.fetch_url(url)
        print(f"Status: {res['status']}, Error: {res['error']}")

        aircraft_list = []
        if res["status"] == 200 and res["body"]:
            try:
                data = json.loads(res["body"].decode("utf-8"))
                states = data.get("states") or []
                for s in states:
                    # OpenSky schema: [icao24, callsign, origin_country, time_position, last_contact,
                    #                  longitude, latitude, baro_altitude, on_ground, velocity,
                    #                  true_track, vertical_rate, sensors, geo_altitude, squawk, spi, position_source]
                    if len(s) >= 17:
                        lat = s[6]
                        lon = s[5]
                        if lat is not None and lon is not None:
                            dist = haversine_km(OSDI_LAT, OSDI_LON, lat, lon)
                        else:
                            dist = None

                        baro_alt_ft = s[7] * 3.28084 if s[7] is not None else None
                        geo_alt_ft = s[13] * 3.28084 if s[13] is not None else None
                        speed_kts = s[9] * 1.94384 if s[9] is not None else None
                        vr_fpm = s[11] * 196.85 if s[11] is not None else None

                        ac_info = {
                            "hex": s[0],
                            "callsign": (s[1] or "").strip(),
                            "country": s[2],
                            "lat": lat,
                            "lon": lon,
                            "distance_km": round(dist, 2) if dist is not None else None,
                            "alt_baro_ft": round(baro_alt_ft, 1) if baro_alt_ft is not None else None,
                            "alt_geom_ft": round(geo_alt_ft, 1) if geo_alt_ft is not None else None,
                            "speed_kts": round(speed_kts, 1) if speed_kts is not None else None,
                            "track": s[10],
                            "vertrate_fpm": round(vr_fpm, 1) if vr_fpm is not None else None,
                            "onground": bool(s[8]),
                            "squawk": s[14],
                        }
                        ac_info["classification"] = classify_trajectory(ac_info)
                        aircraft_list.append(ac_info)
            except Exception as e:
                print(f"Parsing error: {e}")

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"opensky_osdi_150km_{timestamp_str}.json"
        manifest = {
            "provider": "OpenSky Network",
            "endpoint": url,
            "request_timestamp": res["timestamp"],
            "test_radius_km": 150,
            "airport_coordinates": {"lat": OSDI_LAT, "lon": OSDI_LON, "icao": OSDI_ICAO},
            "http_status": res["status"],
            "response_record_count": len(aircraft_list),
            "errors": res["error"],
            "documentation_url": "https://openskynetwork.github.io/opensky-api/",
        }
        self.save_raw_and_manifest("opensky", filename, res["body"], manifest)
        self.results["opensky"] = {
            "http_status": res["status"],
            "error": res["error"],
            "aircraft": aircraft_list,
        }
        return self.results["opensky"]

    def test_adsb_lol(self):
        print("\n--- Testing ADS-B.lol API ---")
        # 150 km ~ 81 nm
        radius_nm = int(round(150 * KM_TO_NM))
        url = f"https://api.adsb.lol/v2/point/{OSDI_LAT}/{OSDI_LON}/{radius_nm}"
        print(f"URL: {url}")
        res = self.fetch_url(url)
        print(f"Status: {res['status']}, Error: {res['error']}")

        aircraft_list = []
        if res["status"] == 200 and res["body"]:
            try:
                data = json.loads(res["body"].decode("utf-8"))
                raw_ac = data.get("ac") or []
                for a in raw_ac:
                    lat = a.get("lat")
                    lon = a.get("lon")
                    if lat is not None and lon is not None:
                        dist = haversine_km(OSDI_LAT, OSDI_LON, lat, lon)
                    else:
                        dist = a.get("dst") * 1.852 if a.get("dst") is not None else None

                    ac_info = {
                        "hex": a.get("hex"),
                        "callsign": (a.get("flight") or "").strip(),
                        "registration": a.get("r"),
                        "aircraft_type": a.get("t"),
                        "lat": lat,
                        "lon": lon,
                        "distance_km": round(dist, 2) if dist is not None else None,
                        "alt_baro_ft": a.get("alt_baro") if isinstance(a.get("alt_baro"), (int, float)) else None,
                        "alt_geom_ft": a.get("alt_geom"),
                        "speed_kts": a.get("gs"),
                        "track": a.get("track"),
                        "vertrate_fpm": a.get("baro_rate"),
                        "onground": a.get("alt_baro") == "ground" or a.get("ground", False),
                        "squawk": a.get("squawk"),
                        "rssi": a.get("rssi"),
                    }
                    ac_info["classification"] = classify_trajectory(ac_info)
                    aircraft_list.append(ac_info)
            except Exception as e:
                print(f"Parsing error: {e}")

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"adsb_lol_osdi_150km_{timestamp_str}.json"
        manifest = {
            "provider": "ADS-B.lol",
            "endpoint": url,
            "request_timestamp": res["timestamp"],
            "test_radius_km": 150,
            "airport_coordinates": {"lat": OSDI_LAT, "lon": OSDI_LON, "icao": OSDI_ICAO},
            "http_status": res["status"],
            "response_record_count": len(aircraft_list),
            "errors": res["error"],
            "documentation_url": "https://adsb.lol/",
        }
        self.save_raw_and_manifest("adsb_lol", filename, res["body"], manifest)
        self.results["adsb_lol"] = {
            "http_status": res["status"],
            "error": res["error"],
            "aircraft": aircraft_list,
        }
        return self.results["adsb_lol"]

    def test_airplanes_live(self):
        print("\n--- Testing Airplanes.live API ---")
        radius_nm = int(round(150 * KM_TO_NM))
        url = f"https://api.airplanes.live/v2/point/{OSDI_LAT}/{OSDI_LON}/{radius_nm}"
        print(f"URL: {url}")
        res = self.fetch_url(url)
        print(f"Status: {res['status']}, Error: {res['error']}")

        aircraft_list = []
        if res["status"] == 200 and res["body"]:
            try:
                data = json.loads(res["body"].decode("utf-8"))
                raw_ac = data.get("ac") or []
                for a in raw_ac:
                    lat = a.get("lat")
                    lon = a.get("lon")
                    dist = haversine_km(OSDI_LAT, OSDI_LON, lat, lon) if lat and lon else None
                    ac_info = {
                        "hex": a.get("hex"),
                        "callsign": (a.get("flight") or "").strip(),
                        "registration": a.get("r"),
                        "distance_km": round(dist, 2) if dist else None,
                        "alt_baro_ft": a.get("alt_baro"),
                        "speed_kts": a.get("gs"),
                    }
                    aircraft_list.append(ac_info)
            except Exception as e:
                print(f"Parsing error: {e}")

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"airplanes_live_osdi_150km_{timestamp_str}.json"
        manifest = {
            "provider": "Airplanes.live",
            "endpoint": url,
            "request_timestamp": res["timestamp"],
            "test_radius_km": 150,
            "airport_coordinates": {"lat": OSDI_LAT, "lon": OSDI_LON, "icao": OSDI_ICAO},
            "http_status": res["status"],
            "response_record_count": len(aircraft_list),
            "errors": res["error"],
            "documentation_url": "https://airplanes.live/",
        }
        self.save_raw_and_manifest("airplanes_live", filename, res["body"], manifest)
        self.results["airplanes_live"] = {
            "http_status": res["status"],
            "error": res["error"],
            "aircraft": aircraft_list,
        }
        return self.results["airplanes_live"]

    def test_adsb_fi(self):
        print("\n--- Testing ADSB.fi Community API ---")
        radius_nm = int(round(150 * KM_TO_NM))
        url = f"https://opendata.adsb.fi/api/v2/lat/{OSDI_LAT}/lon/{OSDI_LON}/dist/{radius_nm}"
        print(f"URL: {url}")
        res = self.fetch_url(url)
        print(f"Status: {res['status']}, Error: {res['error']}")

        aircraft_list = []
        if res["status"] == 200 and res["body"]:
            try:
                data = json.loads(res["body"].decode("utf-8"))
                raw_ac = data.get("aircraft") or []
                for a in raw_ac:
                    lat = a.get("lat")
                    lon = a.get("lon")
                    dist = haversine_km(OSDI_LAT, OSDI_LON, lat, lon) if lat and lon else None
                    ac_info = {
                        "hex": a.get("hex"),
                        "callsign": (a.get("flight") or "").strip(),
                        "registration": a.get("r"),
                        "aircraft_type": a.get("t"),
                        "lat": lat,
                        "lon": lon,
                        "distance_km": round(dist, 2) if dist else None,
                        "alt_baro_ft": a.get("alt_baro") if isinstance(a.get("alt_baro"), (int, float)) else None,
                        "alt_geom_ft": a.get("alt_geom"),
                        "speed_kts": a.get("gs"),
                        "track": a.get("track"),
                        "vertrate_fpm": a.get("baro_rate"),
                        "onground": a.get("alt_baro") == "ground" or a.get("ground", False),
                        "squawk": a.get("squawk"),
                        "rssi": a.get("rssi"),
                    }
                    ac_info["classification"] = classify_trajectory(ac_info)
                    aircraft_list.append(ac_info)
            except Exception as e:
                print(f"Parsing error: {e}")

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"adsb_fi_osdi_150km_{timestamp_str}.json"
        manifest = {
            "provider": "ADSB.fi (Community)",
            "endpoint": url,
            "request_timestamp": res["timestamp"],
            "test_radius_km": 150,
            "airport_coordinates": {"lat": OSDI_LAT, "lon": OSDI_LON, "icao": OSDI_ICAO},
            "http_status": res["status"],
            "response_record_count": len(aircraft_list),
            "errors": res["error"],
            "documentation_url": "https://adsb.fi/",
        }
        self.save_raw_and_manifest("other_sources", filename, res["body"], manifest)
        self.results["adsb_fi"] = {
            "http_status": res["status"],
            "error": res["error"],
            "aircraft": aircraft_list,
        }
        return self.results["adsb_fi"]

    def run_all(self):
        print(f"================================================================================")
        print(f"SYRIAN AIRPORT DATA ENGINE — FREE AVIATION APIS DAMASCUS COVERAGE ASSESSMENT")
        print(f"Target: Damascus International Airport (DAM / OSDI)")
        print(f"Coordinates: Lat {OSDI_LAT}, Lon {OSDI_LON} | Elevation: {OSDI_ELEVATION_FT} ft MSL")
        print(f"Time (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"================================================================================")

        self.test_opensky()
        time.sleep(1.0)
        self.test_adsb_lol()
        time.sleep(1.0)
        self.test_airplanes_live()
        time.sleep(1.0)
        self.test_adsb_fi()

        # Compile radius breakdown
        print("\n================================================================================")
        print("GEOGRAPHIC COVERAGE ASSESSMENT BY RADIUS (10 km, 25 km, 50 km, 100 km, 150 km)")
        print("================================================================================")

        summary_report = {
            "test_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "airport": {"icao": OSDI_ICAO, "iata": OSDI_IATA, "lat": OSDI_LAT, "lon": OSDI_LON},
            "providers": {},
        }

        for p_name, p_data in self.results.items():
            status = p_data["http_status"]
            error = p_data["error"]
            ac_list = p_data["aircraft"]

            radius_counts = {10: 0, 25: 0, 50: 0, 100: 0, 150: 0}
            classifications = {}
            valid_hex_count = 0
            has_callsign_count = 0
            has_alt_count = 0
            has_speed_count = 0

            for ac in ac_list:
                hex_code = ac.get("hex")
                if hex_code and len(hex_code) == 6:
                    valid_hex_count += 1
                if ac.get("callsign"):
                    has_callsign_count += 1
                if ac.get("alt_baro_ft") is not None or ac.get("alt_geom_ft") is not None:
                    has_alt_count += 1
                if ac.get("speed_kts") is not None:
                    has_speed_count += 1

                dist = ac.get("distance_km")
                if dist is not None:
                    for r in RADII_KM:
                        if dist <= r:
                            radius_counts[r] += 1

                cls = ac.get("classification", "unclassified")
                classifications[cls] = classifications.get(cls, 0) + 1

            summary_report["providers"][p_name] = {
                "http_status": status,
                "error": error,
                "total_returned": len(ac_list),
                "valid_hex": valid_hex_count,
                "has_callsign": has_callsign_count,
                "has_altitude": has_alt_count,
                "has_speed": has_speed_count,
                "radius_breakdown": radius_counts,
                "classifications": classifications,
                "sample_aircraft": ac_list[:3] if ac_list else [],
            }

            print(f"\nProvider: {p_name.upper()}")
            print(f"  HTTP Status: {status} | Error: {error}")
            print(f"  Total Aircraft Observed: {len(ac_list)}")
            print(f"  Valid 24-bit ICAO24 Hex: {valid_hex_count}")
            print(f"  With Operating Callsign: {has_callsign_count}")
            print(f"  With Altitude Telemetry: {has_alt_count}")
            print(f"  Radius Counts:")
            for r in RADII_KM:
                print(f"    <= {r} km: {radius_counts[r]} aircraft")
            print(f"  Movement Classifications: {classifications}")

        report_path = os.path.join(BASE_OUT_DIR, "reports", "coverage_test_summary.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(summary_report, f, indent=2)
        print(f"\nSaved full structured report to: {report_path}")
        return summary_report


if __name__ == "__main__":
    tester = FreeAviationTester()
    tester.run_all()
