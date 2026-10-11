"""
Syrian Airport Data Engine — Version 2.16
Snapshot Comparison Engine & Historical Archive Staging Database

Manages the isolated historical staging database:
data/archived_fids_history_staging.db

Supports 10 comparative categories:
1. exact_same_digest: Exact same snapshot digest
2. same_uuid_identical: Same source UUID and identical content
3. same_uuid_modified: Same source UUID but modified fields
4. new_source_uuid: New source UUID present in comparison but not baseline
5. missing_source_uuid: Source UUID present in baseline but missing from comparison
6. same_flight_and_slot: Same flight number and schedule slot across snapshots
7. prefix_variant_duplicate: Possible prefix-variant duplicate
8. rescheduled_service: Rescheduled service (flight in new time slot)
9. removed_display_record: Record no longer displayed in later snapshot (does NOT imply flight cancellation)
10. ambiguous_change: Multi-field change requiring manual review

Invariants:
- data/damascus_airport.db is NEVER accessed or modified.
- data/archived_fids_staging.db is NEVER modified.
- Missing records are NEVER interpreted as physical cancellations without explicit proof.
- Foreign keys enabled, parameterized SQL used exclusively, idempotent execution.
"""

import os
import re
import csv
import json
import sqlite3
import hashlib
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple

HISTORY_DB_PATH = "data/archived_fids_history_staging.db"

def get_history_db_connection(db_path: str = HISTORY_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_history_database(db_path: str = HISTORY_DB_PATH) -> str:
    """Initializes the schema for data/archived_fids_history_staging.db."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = get_history_db_connection(db_path)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS archived_snapshot_registry (
        snapshot_id TEXT PRIMARY KEY,
        original_url TEXT NOT NULL,
        wayback_timestamp TEXT NOT NULL,
        capture_datetime TEXT NOT NULL,
        retrieval_datetime TEXT NOT NULL,
        http_status INTEGER NOT NULL,
        mime_type TEXT NOT NULL,
        content_digest TEXT NOT NULL,
        raw_sha256 TEXT,
        json_sha256 TEXT NOT NULL,
        total_records INTEGER NOT NULL,
        validation_status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        normalized_endpoint TEXT DEFAULT 'https://damairport.gov.sy/api/flights.php',
        query_parameters TEXT DEFAULT '{}',
        capture_type TEXT DEFAULT 'unfiltered_endpoint',
        direction_filter TEXT DEFAULT 'none',
        comparison_eligibility TEXT DEFAULT 'full_snapshot_comparison',
        comparison_scope TEXT DEFAULT 'all_movements',
        scope_compatible INTEGER DEFAULT 1,
        comparison_exclusion_reason TEXT DEFAULT NULL
    );
    """)

    # Migrate any missing columns if table already existed
    cur.execute("PRAGMA table_info(archived_snapshot_registry)")
    cols = {r[1] for r in cur.fetchall()}
    new_cols = [
        ("normalized_endpoint", "TEXT DEFAULT 'https://damairport.gov.sy/api/flights.php'"),
        ("query_parameters", "TEXT DEFAULT '{}'"),
        ("capture_type", "TEXT DEFAULT 'unfiltered_endpoint'"),
        ("direction_filter", "TEXT DEFAULT 'none'"),
        ("comparison_eligibility", "TEXT DEFAULT 'full_snapshot_comparison'"),
        ("comparison_scope", "TEXT DEFAULT 'all_movements'"),
        ("scope_compatible", "INTEGER DEFAULT 1"),
        ("comparison_exclusion_reason", "TEXT DEFAULT NULL")
    ]
    for col_name, col_def in new_cols:
        if col_name not in cols:
            cur.execute(f"ALTER TABLE archived_snapshot_registry ADD COLUMN {col_name} {col_def}")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS archived_snapshot_records (
        record_pk INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_id TEXT NOT NULL,
        source_uuid TEXT NOT NULL,
        flight_number TEXT NOT NULL,
        original_date TEXT NOT NULL,
        original_time TEXT NOT NULL,
        direction TEXT NOT NULL,
        origin TEXT NOT NULL,
        destination TEXT NOT NULL,
        displayed_airline TEXT NOT NULL,
        displayed_status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        raw_record_hash TEXT NOT NULL,
        normalized_record_hash TEXT NOT NULL,
        FOREIGN KEY (snapshot_id) REFERENCES archived_snapshot_registry(snapshot_id) ON DELETE CASCADE
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_hist_snap ON archived_snapshot_records(snapshot_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hist_uuid ON archived_snapshot_records(source_uuid);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hist_slot ON archived_snapshot_records(original_date, original_time, flight_number);")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS snapshot_comparison_results (
        comparison_id TEXT PRIMARY KEY,
        baseline_snapshot_id TEXT NOT NULL,
        comparison_snapshot_id TEXT NOT NULL,
        source_uuid TEXT,
        comparison_category TEXT NOT NULL,
        changed_fields TEXT,
        review_status TEXT NOT NULL,
        details TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (baseline_snapshot_id) REFERENCES archived_snapshot_registry(snapshot_id),
        FOREIGN KEY (comparison_snapshot_id) REFERENCES archived_snapshot_registry(snapshot_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS snapshot_validation_issues (
        issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_id TEXT NOT NULL,
        source_uuid TEXT,
        issue_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        details TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (snapshot_id) REFERENCES archived_snapshot_registry(snapshot_id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()
    return db_path

def ingest_snapshot(
    validation_data: Dict[str, Any],
    original_url: str = "https://damairport.gov.sy/api/flights.php",
    wayback_timestamp: Optional[str] = None,
    content_digest: str = "",
    db_path: str = HISTORY_DB_PATH
) -> str:
    """
    Ingests a validated snapshot into data/archived_fids_history_staging.db idempotently.
    """
    init_history_database(db_path)
    conn = get_history_db_connection(db_path)
    cur = conn.cursor()

    snap_id = validation_data["snapshot_id"]
    if wayback_timestamp is None:
        wayback_timestamp = snap_id.replace("snap_wayback_", "")

    ts = wayback_timestamp
    cap_dt = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}:{ts[12:14]}" if len(ts) >= 14 else ts

    # Check if already registered
    cur.execute("SELECT snapshot_id FROM archived_snapshot_registry WHERE snapshot_id = ?", (snap_id,))
    if cur.fetchone():
        # Already ingested; return
        conn.close()
        return snap_id

    im = validation_data.get("identity_metrics", {})
    total_records = im.get("total_records", 0)

    from scripts.discover_wayback_fids import parse_url_variant
    url_info = parse_url_variant(original_url)
    norm_endpoint = url_info["normalized_endpoint"]
    qparams = url_info["query_parameters"]
    ctype = url_info["capture_type"]
    dir_filter = url_info["direction_filter"]
    eligibility = "full_snapshot_comparison" if dir_filter in ("none", "all") else "scoped_comparison_only"
    scope = "all_movements" if dir_filter in ("none", "all") else f"{dir_filter}_movements_only"
    scope_comp = 1 if eligibility == "full_snapshot_comparison" else 0
    excl_reason = None if eligibility == "full_snapshot_comparison" else f"filtered_{dir_filter}_scope"

    cur.execute("""
    INSERT INTO archived_snapshot_registry (
        snapshot_id, original_url, wayback_timestamp, capture_datetime, retrieval_datetime,
        http_status, mime_type, content_digest, raw_sha256, json_sha256,
        total_records, validation_status, created_at,
        normalized_endpoint, query_parameters, capture_type, direction_filter,
        comparison_eligibility, comparison_scope, scope_compatible, comparison_exclusion_reason
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        snap_id,
        original_url,
        wayback_timestamp,
        cap_dt,
        validation_data.get("validated_at", datetime.now().isoformat()),
        200,
        "application/json",
        content_digest or "UNKNOWN",
        validation_data.get("raw_sha256"),
        validation_data.get("json_sha256", ""),
        total_records,
        validation_data.get("validation_status", "VALID"),
        datetime.now().isoformat(),
        norm_endpoint,
        qparams,
        ctype,
        dir_filter,
        eligibility,
        scope,
        scope_comp,
        excl_reason
    ))

    # Read records from JSON
    json_path = validation_data.get("json_path")
    if json_path and os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            js = json.load(f)
            flts = js.get("flights", [])
            for fobj in flts:
                uid = str(fobj.get("id") or "").strip()
                fnum = str(fobj.get("flightNumber") or "").strip()
                fdate = str(fobj.get("date") or "").strip()
                ftime = str(fobj.get("time") or "").strip()
                fdir = str(fobj.get("direction") or "").lower().strip()
                forig = str(fobj.get("origin") or "").strip()
                fdest = str(fobj.get("destination") or "").strip()
                fair = str(fobj.get("airline") or "").strip()
                fstat = str(fobj.get("status") or "").lower().strip()
                fcreated = str(fobj.get("createdAt") or "").strip()

                raw_hash = hashlib.sha256(json.dumps(fobj, sort_keys=True).encode("utf-8")).hexdigest()
                norm_str = f"{fnum}|{fdate}|{ftime}|{fdir}|{forig}|{fdest}|{fair}|{fstat}"
                norm_hash = hashlib.sha256(norm_str.encode("utf-8")).hexdigest()

                cur.execute("""
                INSERT INTO archived_snapshot_records (
                    snapshot_id, source_uuid, flight_number, original_date, original_time,
                    direction, origin, destination, displayed_airline, displayed_status,
                    created_at, raw_record_hash, normalized_record_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    snap_id, uid, fnum, fdate, ftime,
                    fdir, forig, fdest, fair, fstat,
                    fcreated, raw_hash, norm_hash
                ))

    # Insert validation issues
    for iss in validation_data.get("issues", []):
        cur.execute("""
        INSERT INTO snapshot_validation_issues (
            snapshot_id, source_uuid, issue_type, severity, details, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            snap_id,
            iss.get("source_uuid"),
            iss.get("issue_type", "general"),
            iss.get("severity", "INFO"),
            iss.get("details", ""),
            datetime.now().isoformat()
        ))

    conn.commit()
    conn.close()
    return snap_id

def check_comparison_eligibility(
    baseline_id: str,
    comparison_id: str,
    db_path: str = HISTORY_DB_PATH
) -> Dict[str, Any]:
    """
    Evaluates whether two snapshots can be legitimately compared.
    Distinguishes full comparison from scoped comparison.
    """
    conn = get_history_db_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM archived_snapshot_registry WHERE snapshot_id = ?", (baseline_id,))
    base = cur.fetchone()
    cur.execute("SELECT * FROM archived_snapshot_registry WHERE snapshot_id = ?", (comparison_id,))
    comp = cur.fetchone()
    conn.close()

    if not base:
        return {
            "comparison_eligibility": "not_comparable",
            "comparison_scope": "none",
            "scope_compatible": False,
            "comparison_exclusion_reason": f"baseline_snapshot_{baseline_id}_not_found"
        }

    if not comp:
        return {
            "comparison_eligibility": "not_acquired",
            "comparison_scope": "none",
            "scope_compatible": False,
            "comparison_exclusion_reason": f"comparison_snapshot_{comparison_id}_not_acquired"
        }

    base_d = dict(base)
    comp_d = dict(comp)

    # Check validation status
    if comp_d.get("validation_status") not in ("VALID", "PASSED"):
        return {
            "comparison_eligibility": "not_validated",
            "comparison_scope": "none",
            "scope_compatible": False,
            "comparison_exclusion_reason": "comparison_snapshot_failed_validation"
        }

    # Scope detection
    base_dir = base_d.get("direction_filter") or "none"
    comp_dir = comp_d.get("direction_filter") or "none"

    if base_dir == "none" and comp_dir == "none":
        return {
            "comparison_eligibility": "full_snapshot_comparison",
            "comparison_scope": "all_movements",
            "scope_compatible": True,
            "comparison_exclusion_reason": None
        }
    elif base_dir == comp_dir:
        return {
            "comparison_eligibility": "full_snapshot_comparison",
            "comparison_scope": f"{base_dir}_movements",
            "scope_compatible": True,
            "comparison_exclusion_reason": None
        }
    else:
        shared_scope = comp_dir if comp_dir in ("arrival", "departure") else base_dir
        return {
            "comparison_eligibility": "scoped_comparison_only",
            "comparison_scope": f"{shared_scope}_movements_only",
            "scope_compatible": False,
            "comparison_exclusion_reason": f"scope_mismatch_{base_dir}_vs_{comp_dir}"
        }

def compare_snapshots(
    baseline_id: str,
    comparison_id: str,
    allow_scoped: bool = True,
    db_path: str = HISTORY_DB_PATH
) -> List[Dict[str, Any]]:
    """
    Compares two snapshots recorded in data/archived_fids_history_staging.db.
    Classifies changes into deterministic comparative categories.
    """
    if baseline_id == comparison_id:
        return []

    eligibility = check_comparison_eligibility(baseline_id, comparison_id, db_path)
    if eligibility["comparison_eligibility"] in ("not_acquired", "not_validated", "not_comparable"):
        raise ValueError(f"Snapshot comparison ineligible: {eligibility['comparison_exclusion_reason']}")

    if eligibility["comparison_eligibility"] == "scoped_comparison_only" and not allow_scoped:
        raise ValueError(f"Snapshots have incompatible scopes for full comparison: {eligibility['comparison_exclusion_reason']}")

    conn = get_history_db_connection(db_path)
    cur = conn.cursor()

    # 1. Fetch registry info
    cur.execute("SELECT * FROM archived_snapshot_registry WHERE snapshot_id IN (?, ?)", (baseline_id, comparison_id))
    regs = {r["snapshot_id"]: dict(r) for r in cur.fetchall()}

    if baseline_id not in regs or comparison_id not in regs:
        conn.close()
        raise ValueError(f"Both snapshots must be registered: {baseline_id}, {comparison_id}")

    # Check category 1: exact same digest
    b_digest = regs[baseline_id]["content_digest"]
    c_digest = regs[comparison_id]["content_digest"]
    if b_digest and c_digest and b_digest not in ("", "UNKNOWN") and b_digest == c_digest:
        res = [{
            "comparison_id": f"CMP_{baseline_id}_{comparison_id}_EXACT_DIGEST",
            "baseline_snapshot_id": baseline_id,
            "comparison_snapshot_id": comparison_id,
            "source_uuid": None,
            "comparison_category": "exact_same_digest",
            "changed_fields": None,
            "review_status": "identical_snapshot",
            "details": f"Both snapshots share identical Wayback content digest '{b_digest}'."
        }]
        conn.close()
        return res

    # 2. Fetch records
    cur.execute("SELECT * FROM archived_snapshot_records WHERE snapshot_id = ?", (baseline_id,))
    base_records = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT * FROM archived_snapshot_records WHERE snapshot_id = ?", (comparison_id,))
    comp_records = [dict(r) for r in cur.fetchall()]

    # If scoped comparison, restrict both to the shared scope
    if eligibility["comparison_eligibility"] == "scoped_comparison_only":
        shared_dir = "arrival" if "arrival" in eligibility["comparison_scope"] else "departure"
        base_records = [r for r in base_records if r["direction"] == shared_dir]
        comp_records = [r for r in comp_records if r["direction"] == shared_dir]

    base_by_uuid = {r["source_uuid"]: r for r in base_records if r["source_uuid"]}
    comp_by_uuid = {r["source_uuid"]: r for r in comp_records if r["source_uuid"]}

    base_by_slot = defaultdict(list)
    for r in base_records:
        base_by_slot[(r["original_date"], r["original_time"], r["direction"])].append(r)

    comp_by_slot = defaultdict(list)
    for r in comp_records:
        comp_by_slot[(r["original_date"], r["original_time"], r["direction"])].append(r)

    comparisons: List[Dict[str, Any]] = []

    # Check common UUIDs
    common_uuids = set(base_by_uuid.keys()) & set(comp_by_uuid.keys())
    for uid in common_uuids:
        b_rec = base_by_uuid[uid]
        c_rec = comp_by_uuid[uid]

        if b_rec["normalized_record_hash"] == c_rec["normalized_record_hash"]:
            # Category 2: same_uuid_identical
            comparisons.append({
                "comparison_id": f"CMP_{baseline_id}_{comparison_id}_{uid}_IDENTICAL",
                "baseline_snapshot_id": baseline_id,
                "comparison_snapshot_id": comparison_id,
                "source_uuid": uid,
                "comparison_category": "same_uuid_identical",
                "changed_fields": None,
                "review_status": "verified_concordant",
                "details": f"Record {b_rec['flight_number']} ({b_rec['original_date']}) identical across snapshots."
            })
        else:
            # Category 3: same_uuid_modified
            diffs = []
            for field in ["flight_number", "original_date", "original_time", "direction", "origin", "destination", "displayed_airline", "displayed_status"]:
                if b_rec[field] != c_rec[field]:
                    diffs.append(f"{field}: '{b_rec[field]}' -> '{c_rec[field]}'")

            cat = "same_uuid_modified"
            # Specific sub-classifications
            if len(diffs) >= 3:
                cat = "ambiguous_change"
            elif len(diffs) == 1 and "displayed_status" in diffs[0]:
                cat = "display_status_changed"
            elif len(diffs) == 1 and "displayed_airline" in diffs[0]:
                cat = "displayed_airline_changed"
            elif any("original_time" in d or "original_date" in d for d in diffs):
                cat = "rescheduled_service"

            comparisons.append({
                "comparison_id": f"CMP_{baseline_id}_{comparison_id}_{uid}_MOD",
                "baseline_snapshot_id": baseline_id,
                "comparison_snapshot_id": comparison_id,
                "source_uuid": uid,
                "comparison_category": cat,
                "changed_fields": "; ".join(diffs),
                "review_status": "requires_manual_review",
                "details": f"UUID {uid} modified across snapshots: {', '.join(diffs)}."
            })

    # Category 4: new_source_uuid (in comparison but not in baseline)
    new_uuids = set(comp_by_uuid.keys()) - set(base_by_uuid.keys())
    for uid in new_uuids:
        c_rec = comp_by_uuid[uid]
        slot_key = (c_rec["original_date"], c_rec["original_time"], c_rec["direction"])
        matching_slot_base = base_by_slot.get(slot_key, [])
        matching_fnum = [r for r in matching_slot_base if r["flight_number"] == c_rec["flight_number"]]

        if matching_fnum:
            cat = "same_flight_and_slot"
            rev = "uuid_rotation_or_reissued"
            details = f"Flight {c_rec['flight_number']} at {slot_key[0]} {slot_key[1]} re-indexed under new UUID {uid}."
        else:
            # Check prefix variant: must be carrier code omission (num1 == num2, not extra digits like RB272 vs RB2722)
            is_prefix = False
            for b_cand in matching_slot_base:
                f1 = c_rec["flight_number"]
                f2 = b_cand["flight_number"]
                num1 = re.sub(r'^[A-Za-z][A-Za-z0-9]?\s*|^[0-9][A-Za-z]\s*', '', f1.strip())
                num2 = re.sub(r'^[A-Za-z][A-Za-z0-9]?\s*|^[0-9][A-Za-z]\s*', '', f2.strip())
                if num1 == num2 and num1 and (f1.strip() != f2.strip()) and c_rec["displayed_airline"] == b_cand["displayed_airline"]:
                    is_prefix = True
                    break
            if is_prefix:
                cat = "prefix_variant_duplicate"
                rev = "requires_manual_review"
                details = f"New UUID {uid} matches existing slot as prefix-variant flight."
            else:
                cat = "new_source_uuid"
                rev = "new_schedule_entry"
                details = f"New schedule entry {c_rec['flight_number']} ({c_rec['displayed_airline']}) on {c_rec['original_date']}."

        comparisons.append({
            "comparison_id": f"CMP_{baseline_id}_{comparison_id}_{uid}_NEW",
            "baseline_snapshot_id": baseline_id,
            "comparison_snapshot_id": comparison_id,
            "source_uuid": uid,
            "comparison_category": cat,
            "changed_fields": None,
            "review_status": rev,
            "details": details
        })

    # Category 5: missing_source_uuid (in baseline but not in comparison)
    missing_uuids = set(base_by_uuid.keys()) - set(comp_by_uuid.keys())
    for uid in missing_uuids:
        b_rec = base_by_uuid[uid]
        # Does the comparison snapshot cover this scheduled date?
        comp_dates = {r["original_date"] for r in comp_records}
        if b_rec["original_date"] in comp_dates:
            cat = "removed_display_record"
            rev = "no_longer_listed_on_board"
            details = f"Flight {b_rec['flight_number']} ({b_rec['original_date']} {b_rec['original_time']}) omitted from comparison display. Note: Omission from display board does not prove physical flight cancellation."
        else:
            cat = "missing_source_uuid"
            rev = "outside_comparison_coverage"
            details = f"UUID {uid} scheduled for {b_rec['original_date']}, which is outside comparison snapshot's displayed calendar window."

        comparisons.append({
            "comparison_id": f"CMP_{baseline_id}_{comparison_id}_{uid}_MISSING",
            "baseline_snapshot_id": baseline_id,
            "comparison_snapshot_id": comparison_id,
            "source_uuid": uid,
            "comparison_category": cat,
            "changed_fields": None,
            "review_status": rev,
            "details": details
        })

    # Save to snapshot_comparison_results
    cur.execute("DELETE FROM snapshot_comparison_results WHERE baseline_snapshot_id = ? AND comparison_snapshot_id = ?", (baseline_id, comparison_id))
    for c in comparisons:
        cur.execute("""
        INSERT INTO snapshot_comparison_results (
            comparison_id, baseline_snapshot_id, comparison_snapshot_id,
            source_uuid, comparison_category, changed_fields, review_status, details, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            c["comparison_id"], c["baseline_snapshot_id"], c["comparison_snapshot_id"],
            c["source_uuid"], c["comparison_category"], c["changed_fields"],
            c["review_status"], c["details"], datetime.now().isoformat()
        ))

    conn.commit()
    conn.close()
    return comparisons

def generate_comparison_reports(comparisons: List[Dict[str, Any]], output_csv: str = "reports/v2_16_snapshot_comparison.csv"):
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "comparison_id",
            "baseline_snapshot_id",
            "comparison_snapshot_id",
            "source_uuid",
            "comparison_category",
            "changed_fields",
            "review_status",
            "details"
        ])
        for c in comparisons:
            writer.writerow([
                c["comparison_id"],
                c["baseline_snapshot_id"],
                c["comparison_snapshot_id"],
                c.get("source_uuid") or "",
                c["comparison_category"],
                c.get("changed_fields") or "",
                c["review_status"],
                c["details"]
            ])
    print(f"Generated {output_csv} ({len(comparisons)} comparison records)", flush=True)

if __name__ == "__main__":
    init_history_database()
    print("Historical archive database initialized at data/archived_fids_history_staging.db")
