"""
Tests for Version 2.12.2 — Source Retrieval & Verification Audit
Validates:
1. Production database invariant.
2. Presence and enum validity of the four explicit source-verification fields:
   - source_access_status
   - excerpt_match_status
   - period_support_status
   - scope_support_status
3. Independence of evidence_grade and verification_status (zero status promotions).
4. AksAlSer records homepage_only classification and Grade C retention.
5. April 2026 reporting period uncertainty (unresolved).
6. Airline count numerical evidence vs carrier identity availability.
7. Separation of national airspace overflights from DAM airport throughput.
8. Summary metrics reconciliation.
"""

import os
import csv
import json
import sqlite3
import hashlib
import pytest
from typing import Dict, Any

PROD_DB_PATH = "data/damascus_airport.db"
STAGING_DB_PATH = "data/macro_benchmarks_staging.db"
CSV_REPORT_PATH = "reports/v2_12_2_source_verification.csv"
JSON_REPORT_PATH = "reports/v2_12_2_source_verification.json"

EXPECTED_PROD_HASH = "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"

def get_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def test_production_database_untouched():
    """Verify production database has not been altered."""
    assert os.path.exists(PROD_DB_PATH), "Production database does not exist."
    current_hash = get_hash(PROD_DB_PATH)
    assert current_hash == EXPECTED_PROD_HASH, f"Production database hash changed! Got {current_hash}"

def test_v2_12_2_reports_exist_and_cover_all_31_records():
    """Verify both CSV and JSON audit reports exist and contain all 31 benchmarks."""
    assert os.path.exists(CSV_REPORT_PATH), f"CSV report missing: {CSV_REPORT_PATH}"
    assert os.path.exists(JSON_REPORT_PATH), f"JSON report missing: {JSON_REPORT_PATH}"

    with open(CSV_REPORT_PATH, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 31, f"Expected 31 rows in CSV, got {len(reader)}"

    with open(JSON_REPORT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == 31, f"Expected 31 items in JSON, got {len(data)}"

def test_source_verification_fields_presence_and_enums():
    """Verify the four explicit source-verification fields exist and conform to allowed enums."""
    with open(JSON_REPORT_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    allowed_access = {"accessible", "inaccessible", "homepage_only", "archive_only", "not_found", "not_checked"}
    allowed_excerpt = {"exact_match", "partial_match", "no_match", "not_checked"}
    allowed_period = {"explicit", "partial", "unresolved", "not_applicable"}
    allowed_scope = {"explicit", "partial", "unresolved"}

    for r in records:
        bid = r["benchmark_id"]
        assert "source_access_status" in r, f"Missing source_access_status in {bid}"
        assert "excerpt_match_status" in r, f"Missing excerpt_match_status in {bid}"
        assert "period_support_status" in r, f"Missing period_support_status in {bid}"
        assert "scope_support_status" in r, f"Missing scope_support_status in {bid}"

        assert r["source_access_status"] in allowed_access, f"Invalid source_access_status in {bid}: {r['source_access_status']}"
        assert r["excerpt_match_status"] in allowed_excerpt, f"Invalid excerpt_match_status in {bid}: {r['excerpt_match_status']}"
        assert r["period_support_status"] in allowed_period, f"Invalid period_support_status in {bid}: {r['period_support_status']}"
        assert r["scope_support_status"] in allowed_scope, f"Invalid scope_support_status in {bid}: {r['scope_support_status']}"

def test_evidence_grade_and_verification_status_independence():
    """Ensure evidence_grade and verification_status remain independent and no status was upgraded."""
    with open(JSON_REPORT_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    v_counts = {}
    g_counts = {}
    for r in records:
        v = r["verification_status"]
        g = r["evidence_grade"]
        v_counts[v] = v_counts.get(v, 0) + 1
        g_counts[g] = g_counts.get(g, 0) + 1

    # Statuses must remain strictly preserved
    assert v_counts.get("verified_secondary") == 5, f"Expected 5 verified_secondary, got {v_counts.get('verified_secondary')}"
    assert v_counts.get("unverified_source_url") == 26, f"Expected 26 unverified_source_url, got {v_counts.get('unverified_source_url')}"

    # All 31 records must be Grade C in V2.12.1/V2.12.2
    assert g_counts.get("C") == 31, f"Expected 31 Grade C records, got {g_counts.get('C')}"

def test_aksalser_source_access_is_homepage_only():
    """Verify that the 5 AksAlSer records are classified as homepage_only and Grade C."""
    with open(JSON_REPORT_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    aksalser = [r for r in records if "AksAlSer" in r["source_name"]]
    assert len(aksalser) == 5, f"Expected 5 AksAlSer records, got {len(aksalser)}"

    for r in aksalser:
        assert r["source_access_status"] == "homepage_only", (
            f"Record {r['benchmark_id']} must have source_access_status == 'homepage_only'"
        )
        assert r["direct_url_available"] is False
        assert r["evidence_grade"] == "C"
        assert r["verification_status"] == "verified_secondary"
        assert r["excerpt_match_status"] == "exact_match"
        assert r["period_support_status"] == "explicit"
        assert r["scope_support_status"] == "explicit"

def test_april_2026_period_support_status_unresolved():
    """Verify that April 2026 airport movements have period_support_status == 'unresolved'."""
    with open(JSON_REPORT_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    april_airport = [
        r for r in records 
        if "bmk_2026_04" in r["benchmark_id"] and r["metric_type"] != "airspace_overflights"
    ]
    assert len(april_airport) == 5, f"Expected 5 April airport records, got {len(april_airport)}"

    for r in april_airport:
        assert r["period_support_status"] == "unresolved", (
            f"Record {r['benchmark_id']} must have period_support_status == 'unresolved'"
        )
        assert r["excerpt_match_status"] == "partial_match", (
            f"Record {r['benchmark_id']} must have excerpt_match_status == 'partial_match'"
        )
        assert r["reporting_period_status"] == "unresolved_period_boundary"

    # April overflight covers full calendar month
    april_overflight = [r for r in records if r["benchmark_id"] == "bmk_2026_04_overflights"][0]
    assert april_overflight["period_support_status"] == "explicit"
    assert april_overflight["excerpt_match_status"] == "exact_match"

def test_operating_airlines_count_support_vs_carrier_identity():
    """Verify that operating airlines claims support the numerical count but lack carrier detail."""
    with open(JSON_REPORT_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    airlines = [r for r in records if r["metric_type"] == "operating_airlines"]
    assert len(airlines) == 5, f"Expected 5 operating airlines records, got {len(airlines)}"

    for r in airlines:
        assert r["excerpt_supports_value"] is True
        assert r["metric_identification"] == "airport_airlines"

def test_airspace_overflights_scope_and_segregation():
    """Verify overflights are segregated from DAM airport throughput and scoped to OSTT_FIR."""
    with open(JSON_REPORT_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    overflights = [r for r in records if r["metric_type"] == "airspace_overflights"]
    assert len(overflights) == 2, f"Expected 2 overflight records, got {len(overflights)}"

    for r in overflights:
        assert r["is_airport_throughput"] == 0
        assert r["geographic_scope"] == "OSTT_FIR"
        assert r["scope_support_status"] == "explicit"
        assert r["metric_identification"] == "national_airspace_overflights"

def test_summary_metrics_reconciliation():
    """Verify exact counts of access, match, period, and scope categories."""
    with open(JSON_REPORT_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    accessible_direct = sum(1 for r in records if r["source_access_status"] == "accessible")
    homepage_only = sum(1 for r in records if r["source_access_status"] == "homepage_only")
    archive_only = sum(1 for r in records if r["source_access_status"] == "archive_only")
    missing_sources = sum(1 for r in records if r["source_access_status"] == "not_found")

    assert accessible_direct == 0, f"Expected 0 accessible direct sources, got {accessible_direct}"
    assert homepage_only == 5, f"Expected 5 homepage-only sources, got {homepage_only}"
    assert archive_only == 0, f"Expected 0 archive-only sources, got {archive_only}"
    assert missing_sources == 26, f"Expected 26 missing sources, got {missing_sources}"

    exact_matches = sum(1 for r in records if r["excerpt_match_status"] == "exact_match")
    partial_matches = sum(1 for r in records if r["excerpt_match_status"] == "partial_match")
    assert exact_matches == 26, f"Expected 26 exact matches, got {exact_matches}"
    assert partial_matches == 5, f"Expected 5 partial matches, got {partial_matches}"

    unsupported_periods = sum(1 for r in records if r["period_support_status"] == "unresolved")
    assert unsupported_periods == 5, f"Expected 5 unsupported (unresolved) periods, got {unsupported_periods}"
