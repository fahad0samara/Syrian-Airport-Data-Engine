import time
import json
from typing import Dict, Any, List
from pathlib import Path

from src.adapters.base import BaseSourceAdapter

OFFICIAL_PORTAL_CONFIGS = {
    "DAM": {
        "source_id": "damairport_official",
        "name": "Damascus International Airport Authority",
        "url": "https://damairport.gov.sy/api/flights.php",
        "filename": "damairport_official_flights_raw.json",
    },
    "ALP": {
        "source_id": "alpairport_official",
        "name": "Aleppo International Airport Authority",
        "url": "https://alpairport.gov.sy/api/flights.php",
        "filename": "alpairport_official_flights_raw.json",
    },
    "KAC": {
        "source_id": "qamishliairport_official",
        "name": "Qamishli Airport Authority",
        "url": "https://qamishliairport.gov.sy/api/flights.php",
        "filename": "qamishliairport_official_flights_raw.json",
    },
    "DEZ": {
        "source_id": "deirezzorairport_official",
        "name": "Deir ez-Zor Airport Authority",
        "url": "https://deirezzorairport.gov.sy/api/flights.php",
        "filename": "deirezzorairport_official_flights_raw.json",
    }
}

class OfficialAirportAdapter(BaseSourceAdapter):
    """
    Adapter for official Syrian Civil Aviation aerodrome public operational boards.
    Collects live operational schedules, gate statuses, and aircraft assignments.
    """
    def __init__(self, airport_id: str):
        cfg = OFFICIAL_PORTAL_CONFIGS.get(airport_id.upper(), {})
        super().__init__(
            source_id=cfg.get("source_id", f"{airport_id.lower()}airport_official"),
            provider_name=cfg.get("name", f"{airport_id} Airport Authority"),
            source_type="official_portal",
            licensing="Official airport public flight board",
            supported_airports=[airport_id.upper()],
            data_nature="scheduled_and_operational",
            default_url=cfg.get("url")
        )
        self.airport_id = airport_id.upper()
        self.filename = cfg.get("filename", f"{airport_id.lower()}airport_official_flights_raw.json")

    def fetch_and_save(self) -> Dict[str, Any]:
        """
        Polls the official airport portal, handles retries, preserves snapshots,
        and logs the ingestion run. Never fabricates missing records.
        """
        start_t = time.time()
        url = self.default_url
        status_code, content, error = self.fetch_with_retry(url, timeout=15, max_retries=3)
        duration = round(time.time() - start_t, 2)

        if status_code == 200 and content:
            try:
                data = json.loads(content.decode("utf-8"))
                saved_path = self.save_raw_payload(
                    filename=self.filename,
                    data=data,
                    airport_id=self.airport_id,
                    source_url=url,
                    http_status=status_code,
                    duration_seconds=duration
                )
                flight_count = len(data.get("flights", [])) if isinstance(data, dict) else len(data)
                return {
                    "status": "SUCCESS" if flight_count > 0 else "EMPTY",
                    "airport_id": self.airport_id,
                    "records_fetched": flight_count,
                    "file_saved": str(saved_path),
                    "http_status": status_code,
                    "duration_seconds": duration,
                    "error": None
                }
            except Exception as ex:
                self.record_failure(self.airport_id, f"JSON parse error: {ex}", status_code, duration)
                return {
                    "status": "FAILED",
                    "airport_id": self.airport_id,
                    "records_fetched": 0,
                    "http_status": status_code,
                    "duration_seconds": duration,
                    "error": f"JSON parse error: {ex}"
                }
        else:
            self.record_failure(self.airport_id, error or f"HTTP {status_code}", status_code, duration)
            return {
                "status": "FAILED",
                "airport_id": self.airport_id,
                "records_fetched": 0,
                "http_status": status_code,
                "duration_seconds": duration,
                "error": error or f"HTTP {status_code}"
            }
