import time
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.config import AVIATIONSTACK_KEY, RAW_DATA_DIR
from src.adapters.base import BaseSourceAdapter

class AviationStackAdapter(BaseSourceAdapter):
    """
    Adapter for AviationStack Commercial Flight Tracking API.
    Collects rolling flights with airline codes and codeshared relationships.
    Strictly observes licensing and free-tier access terms.
    """
    def __init__(self):
        super().__init__(
            source_id="aviationstack_live",
            provider_name="AviationStack Flight Tracking API",
            source_type="commercial_api_feed",
            licensing="AviationStack API terms (Free/Standard)",
            supported_airports=["DAM", "ALP", "LTK", "KAC", "DEZ"],
            data_nature="rolling_operational_feed",
            default_url="https://api.aviationstack.com/v1/flights"
        )
        self.api_key = AVIATIONSTACK_KEY

    def fetch_airport_flights(self, airport_code: str) -> Dict[str, Any]:
        """
        Queries AviationStack if API key is provided in environment.
        Preserves existing verified snapshots when key is not configured.
        """
        code_upper = airport_code.upper()
        code_lower = airport_code.lower()
        if not self.api_key:
            return {
                "status": "SKIPPED",
                "airport_id": code_upper,
                "records_fetched": 0,
                "message": "AVIATIONSTACK_KEY not configured. Preserving existing verified raw snapshots.",
                "error": None
            }

        start_t = time.time()
        total_fetched = 0
        last_status = 200
        last_error = None

        for direction, iata_param in [("departures", "dep_iata"), ("arrivals", "arr_iata")]:
            url = f"{self.default_url}?access_key={self.api_key}&{iata_param}={code_upper}&limit=100"
            status_code, content, error = self.fetch_with_retry(url, timeout=15, max_retries=2)
            last_status = status_code
            if status_code == 200 and content:
                try:
                    data = json.loads(content.decode("utf-8"))
                    self.save_raw_payload(
                        filename=f"aviationstack_{code_lower}_{direction}_raw.json",
                        data=data,
                        airport_id=code_upper,
                        source_url=f"{self.default_url}?{iata_param}={code_upper}",
                        http_status=status_code,
                        duration_seconds=round(time.time() - start_t, 2)
                    )
                    items = data.get("data", [])
                    total_fetched += len(items)
                except Exception as ex:
                    last_error = f"JSON parse error for {direction}: {ex}"
            else:
                last_error = error or f"HTTP {status_code}"

        duration = round(time.time() - start_t, 2)
        if total_fetched > 0:
            return {
                "status": "SUCCESS",
                "airport_id": code_upper,
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
                    "records_fetched": 0,
                    "http_status": 200,
                    "duration_seconds": duration,
                    "error": None
                }
            else:
                self.record_failure(code_upper, last_error or "AviationStack query failed", last_status, duration)
                return {
                    "status": "FAILED",
                    "airport_id": code_upper,
                    "records_fetched": 0,
                    "http_status": last_status,
                    "duration_seconds": duration,
                    "error": last_error
                }
