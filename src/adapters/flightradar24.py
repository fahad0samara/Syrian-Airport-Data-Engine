import time
import json
from typing import Dict, Any, List
from pathlib import Path

from src.config import RAW_DATA_DIR
from src.adapters.base import BaseSourceAdapter

class Flightradar24Adapter(BaseSourceAdapter):
    """
    Adapter for Flightradar24 airport operational feeds.
    Retrieves rolling active flights, airframe registrations, hex identifiers,
    and terrestrial ADS-B wheels-off and wheels-down timestamps.
    """
    def __init__(self):
        super().__init__(
            source_id="flightradar24",
            provider_name="Flightradar24 Airport Live Radar Feed",
            source_type="terrestrial_adsb_radar",
            licensing="Flightradar24 proprietary / personal/research use",
            supported_airports=["DAM", "ALP", "LTK", "KAC", "DEZ"],
            data_nature="live_and_recent_movements",
            default_url="https://api.flightradar24.com/common/v1/airport.json"
        )

    def fetch_airport_movements(self, airport_code: str) -> Dict[str, Any]:
        """
        Polls Flightradar24 airport schedule for arrivals and departures (pages -1 and 1).
        """
        start_t = time.time()
        code_lower = airport_code.lower()
        code_upper = airport_code.upper()
        arr_all = []
        dep_all = []
        last_status = 200
        last_error = None

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        for page in [-1, 1]:
            url = f"{self.default_url}?code={code_lower}&plugin[]=&plugin-setting[extended][medata]=1&page={page}"
            status_code, content, error = self.fetch_with_retry(url, headers=headers, timeout=15, max_retries=2)
            last_status = status_code
            if status_code == 200 and content:
                try:
                    data = json.loads(content.decode("utf-8"))
                    sched = data.get("result", {}).get("response", {}).get("airport", {}).get("pluginData", {}).get("schedule", {})
                    arr_all.extend(sched.get("arrivals", {}).get("data", []))
                    dep_all.extend(sched.get("departures", {}).get("data", []))
                except Exception as ex:
                    last_error = f"JSON parse error on page {page}: {ex}"
            else:
                last_error = error or f"HTTP {status_code}"

        duration = round(time.time() - start_t, 2)
        total_fetched = len(arr_all) + len(dep_all)

        if total_fetched > 0:
            arr_merged = self.merge_rolling_records(f"flightradar24_{code_lower}_arrivals_raw.json", arr_all)
            dep_merged = self.merge_rolling_records(f"flightradar24_{code_lower}_departures_raw.json", dep_all)

            self.save_raw_payload(
                filename=f"flightradar24_{code_lower}_arrivals_raw.json",
                data=arr_merged,
                airport_id=code_upper,
                source_url=f"{self.default_url}?code={code_lower}",
                http_status=last_status,
                duration_seconds=duration / 2
            )
            self.save_raw_payload(
                filename=f"flightradar24_{code_lower}_departures_raw.json",
                data=dep_merged,
                airport_id=code_upper,
                source_url=f"{self.default_url}?code={code_lower}",
                http_status=last_status,
                duration_seconds=duration / 2
            )
            return {
                "status": "SUCCESS",
                "airport_id": code_upper,
                "arrivals_fetched": len(arr_all),
                "departures_fetched": len(dep_all),
                "records_fetched": total_fetched,
                "http_status": last_status,
                "duration_seconds": duration,
                "error": None
            }
        else:
            if last_status == 200:
                return {
                    "status": "EMPTY",
                    "airport_id": code_upper,
                    "arrivals_fetched": 0,
                    "departures_fetched": 0,
                    "records_fetched": 0,
                    "http_status": 200,
                    "duration_seconds": duration,
                    "error": None
                }
            else:
                self.record_failure(code_upper, last_error or "FR24 query failed", last_status, duration)
                return {
                    "status": "FAILED",
                    "airport_id": code_upper,
                    "arrivals_fetched": 0,
                    "departures_fetched": 0,
                    "records_fetched": 0,
                    "http_status": last_status,
                    "duration_seconds": duration,
                    "error": last_error
                }

    def merge_rolling_records(self, filename: str, new_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merges new rolling schedule records with existing accumulated raw records by flight ID.
        Prevents historical movements from being lost when they age out of FR24's 24-hour buffer.
        """
        raw_path = RAW_DATA_DIR / filename
        existing = []
        if raw_path.exists():
            try:
                with open(raw_path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if isinstance(d, list):
                        existing = d
            except Exception:
                existing = []

        by_key = {}
        for item in existing:
            fid = item.get("flight", {}).get("identification", {}).get("id") or (
                item.get("flight", {}).get("identification", {}).get("number", {}).get("default"),
                item.get("flight", {}).get("time", {}).get("scheduled", {}).get("arrival") or item.get("flight", {}).get("time", {}).get("scheduled", {}).get("departure")
            )
            if fid:
                by_key[fid] = item

        for item in new_items:
            fid = item.get("flight", {}).get("identification", {}).get("id") or (
                item.get("flight", {}).get("identification", {}).get("number", {}).get("default"),
                item.get("flight", {}).get("time", {}).get("scheduled", {}).get("arrival") or item.get("flight", {}).get("time", {}).get("scheduled", {}).get("departure")
            )
            if fid:
                by_key[fid] = item

        return list(by_key.values())
