import urllib.request
import urllib.error
import json
import time
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from src.config import RAW_DATA_DIR, DB_PATH
from src.database import get_connection

class BaseSourceAdapter:
    """
    Abstract base adapter for Syrian aviation data feeds.
    Provides idempotent retrieval, transient error retries with exponential backoff,
    SHA-256 payload hashing, timestamped snapshot preservation, and automated audit logging.
    """
    def __init__(
        self,
        source_id: str,
        provider_name: str,
        source_type: str,
        licensing: str,
        supported_airports: List[str],
        data_nature: str = "scheduled_and_operational",
        default_url: Optional[str] = None
    ):
        self.source_id = source_id
        self.provider_name = provider_name
        self.source_type = source_type
        self.licensing = licensing
        self.supported_airports = supported_airports
        self.data_nature = data_nature
        self.default_url = default_url

    def fetch_with_retry(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 15,
        max_retries: int = 3,
        backoff_factor: float = 1.5
    ) -> Tuple[int, Optional[bytes], Optional[str]]:
        """
        Executes HTTP GET request with retries and exponential backoff.
        Returns: (http_status, response_bytes, error_message)
        """
        req_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SyrianAirportDataEngine/2.1"}
        if headers:
            req_headers.update(headers)

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                req = urllib.request.Request(url, headers=req_headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    status = resp.getcode()
                    content = resp.read()
                    return status, content, None
            except urllib.error.HTTPError as e:
                last_error = f"HTTP {e.code}: {e.reason}"
                # Do not retry on 401, 403, 404 (client/auth errors)
                if e.code in (401, 403, 404):
                    return e.code, None, last_error
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last_error = str(e)

            if attempt < max_retries:
                sleep_sec = backoff_factor ** attempt
                time.sleep(sleep_sec)

        return 0, None, last_error

    def save_raw_payload(
        self,
        filename: str,
        data: Any,
        airport_id: Optional[str] = None,
        source_url: Optional[str] = None,
        http_status: int = 200,
        error_message: Optional[str] = None,
        duration_seconds: float = 0.0
    ) -> Path:
        """
        Saves raw payload with timestamped snapshot, computes SHA-256 hash,
        and logs the ingestion run to the SQLite database.
        """
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        snapshot_dir = RAW_DATA_DIR / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        now_utc = datetime.now(timezone.utc)
        ts_str = now_utc.strftime("%Y%m%d_%H%M%S")
        iso_ts = now_utc.isoformat()

        # Format payload as bytes and calculate hash
        payload_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()

        # 1. Primary raw file
        primary_path = RAW_DATA_DIR / filename
        with open(primary_path, "wb") as f:
            f.write(payload_bytes)

        # 2. Historical snapshot
        snapshot_path = snapshot_dir / f"{ts_str}_{filename}"
        with open(snapshot_path, "wb") as f:
            f.write(payload_bytes)

        # Count records
        if isinstance(data, list):
            rec_count = len(data)
        elif isinstance(data, dict):
            rec_count = len(data.get("flights") or data.get("data") or [])
        else:
            rec_count = 0

        status = "SUCCESS" if rec_count > 0 else ("EMPTY" if http_status == 200 else "FAILED")

        # 3. Record in database (raw_source_records & ingestion_runs)
        try:
            with get_connection() as conn:
                cur = conn.cursor()
                # Log ingestion run
                run_id = f"run_{self.source_id}_{airport_id or 'ALL'}_{ts_str}_{uuid.uuid4().hex[:6]}"
                cur.execute("""
                INSERT INTO ingestion_runs (
                    run_id, run_timestamp, source_id, airport_id, status,
                    records_fetched, payload_hash, http_status, error_message, duration_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id, iso_ts, self.source_id, airport_id, status,
                    rec_count, payload_hash, http_status, error_message, duration_seconds
                ))

                # Update source_registry freshness
                if status in ("SUCCESS", "EMPTY"):
                    cur.execute("""
                    UPDATE source_registry
                    SET last_successful_retrieval = ?,
                        freshness_indicator = 'fresh',
                        last_checked_at = CURRENT_TIMESTAMP
                    WHERE source_id = ?
                    """, (iso_ts, self.source_id))

                conn.commit()
        except Exception:
            pass

        return primary_path

    def record_failure(
        self,
        airport_id: Optional[str],
        error_message: str,
        http_status: int = 0,
        duration_seconds: float = 0.0
    ):
        """
        Logs a failed ingestion run without deleting or corrupting existing data.
        """
        now_utc = datetime.now(timezone.utc)
        ts_str = now_utc.strftime("%Y%m%d_%H%M%S")
        iso_ts = now_utc.isoformat()
        run_id = f"run_{self.source_id}_{airport_id or 'ALL'}_{ts_str}_{uuid.uuid4().hex[:6]}"
        try:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                INSERT INTO ingestion_runs (
                    run_id, run_timestamp, source_id, airport_id, status,
                    records_fetched, payload_hash, http_status, error_message, duration_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id, iso_ts, self.source_id, airport_id, "FAILED",
                    0, None, http_status, error_message, duration_seconds
                ))
                cur.execute("""
                UPDATE source_registry
                SET freshness_indicator = 'stale_error',
                    last_checked_at = CURRENT_TIMESTAMP
                WHERE source_id = ?
                """, (self.source_id,))
                conn.commit()
        except Exception:
            pass
