"""
Tests for Version 2.12 & Version 2.12.1 — Source Evidence Verification Audit
Validates:
1. Production database invariant (absolute safety).
2. Grade B requirement of accessible direct article permalink (AksAlSer downgraded to C).
3. April 2026 reporting period uncertainty (unresolved boundary).
4. Operating airline count evidence vs carrier-level identity availability.
5. Separation of airport and FIR airspace overflight statistics.
6. Preservation of verification_status and independent evidence_grade.
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
CSV_REPORT_PATH = "reports/v2_12_source_evidence_audit.csv"
JSON_REPORT_PATH = "reports/v2_12_source_evidence_audit.json"
CSV_REPORT_V2_12_1_PATH = "reports/v2_12_1_source_evidence_audit.csv"
JSON_REPORT_V2_12_1_PATH = "reports/v2_12_1_source_evidence_audit.json"

EXPECTED_PROD_HASH = "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"

def get_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def test_production_database_untouched():
    """Verify production database has not been altered."""
    assert os.path.exists(PROD_DB_PATH), "Production database does not exist."
    current_hash = get_hash(PROD_DB_PATH)
    assert current_hash == EXPECTED_PROD_HASH, f"Production database hash changed! Got {current_hash}"

def test_audit_reports_exist_and_cover_all_31_records():
    """Verify both CSV and JSON audit reports exist for both v2_12 and v2_12_1."""
    for cpath, jpath in [
        (CSV_REPORT_PATH, JSON_REPORT_PATH),
        (CSV_REPORT_V2_12_1_PATH, JSON_REPORT_V2_12_1_PATH)
    ]:
        assert os.path.exists(cpath), f"CSV audit report missing: {cpath}"
        assert os.path.exists(jpath), f"JSON audit report missing: {jpath}"

        with open(cpath, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            assert len(reader) == 31, f"Expected 31 rows in {cpath}, got {len(reader)}"

        with open(jpath, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert len(data) == 31, f"Expected 31 items in {jpath}, got {len(data)}"

def test_verification_status_and_evidence_grade_separation():
    """Ensure verification_status and evidence_grade are separate fields and not conflated."""
    with open(JSON_REPORT_V2_12_1_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    for r in records:
        assert "verification_status" in r, f"Missing verification_status in {r['benchmark_id']}"
        assert "evidence_grade" in r, f"Missing evidence_grade in {r['benchmark_id']}"
        assert r["verification_status"] in ("verified_primary", "verified_secondary", "unverified_source_url", "rejected")
        assert r["evidence_grade"] in ("A", "B", "C", "D")

    # Confirm preservation of verification statuses
    status_counts = {}
    for r in records:
        s = r["verification_status"]
        status_counts[s] = status_counts.get(s, 0) + 1

    assert status_counts.get("verified_secondary") == 5, "5 AksAlSer records must retain verified_secondary status"
    assert status_counts.get("unverified_source_url") == 26, "26 SANA records must retain unverified_source_url status"

def test_grade_b_requires_accessible_direct_source():
    """
    Task 5 Requirement 1:
    Grade B requires an accessible direct article permalink and a matching excerpt.
    A homepage URL alone (e.g. 'https://aksalser.com/') is insufficient.
    Downgrade AksAlSer records to Grade C until the direct article permalink is located.
    """
    with open(JSON_REPORT_V2_12_1_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    aksalser_records = [r for r in records if "AksAlSer" in r["source_name"]]
    assert len(aksalser_records) == 5, f"Expected 5 AksAlSer records, got {len(aksalser_records)}"

    for r in aksalser_records:
        # Verify URL is root domain only
        assert r["source_url"].rstrip("/") == "https://aksalser.com"
        assert r["has_direct_source_url"] is False, "Homepage URL must not be classified as direct source URL"
        # Verify downgraded to Grade C
        assert r["evidence_grade"] == "C", f"Record {r['benchmark_id']} must be Grade C due to root-domain URL"
        # Verify verification_status is preserved
        assert r["verification_status"] == "verified_secondary", "verification_status must remain verified_secondary"

def test_april_period_uncertainty():
    """
    Task 5 Requirement 2:
    April 2026 period semantics: Do not assume April 8–30 from the airport reopening date.
    Compare the source excerpt ('في نيسان 2026'), reporting period, and operational reopening timeline.
    Mark reporting period boundary as unresolved without inventing a replacement period.
    """
    with open(JSON_REPORT_V2_12_1_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    april_records = [r for r in records if "bmk_2026_04" in r["benchmark_id"]]
    assert len(april_records) == 6, f"Expected 6 April 2026 records, got {len(april_records)}"

    for r in april_records:
        assert r["reporting_period_status"] == "unresolved_period_boundary", (
            f"Record {r['benchmark_id']} must have reporting_period_status = 'unresolved_period_boundary'"
        )
        assert "في نيسان 2026" in r["period_uncertainty_note"], (
            f"Record {r['benchmark_id']} must document discrepancy with quoted 'في نيسان 2026'"
        )
        # Verify we did not invent a replacement period
        if r["metric_type"] != "airspace_overflights":
            assert r["reporting_period_start"] == "2026-04-08"
            assert r["reporting_period_end"] == "2026-04-30"

def test_airline_count_evidence_versus_carrier_identity_availability():
    """
    Task 5 Requirement 3:
    Reassess operating airline counts:
    Missing carrier identities alone do not invalidate a directly reported count.
    Distinguish source support for the numerical count from missing carrier-level detail.
    Keep unsupported claims unverified.
    """
    with open(JSON_REPORT_V2_12_1_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    airline_records = [r for r in records if r["metric_type"] == "operating_airlines"]
    assert len(airline_records) == 5, f"Expected 5 airline count records, got {len(airline_records)}"

    for r in airline_records:
        # Numerical count is supported directly in text
        assert r["supports_numerical_count"] is True, (
            f"Numerical count must be marked supported for {r['benchmark_id']}"
        )
        # Carrier identities are missing
        assert r["has_carrier_level_detail"] is False, (
            f"Carrier level detail must be marked False for {r['benchmark_id']}"
        )
        # Graded C (citation metadata exists, but unverified primary)
        assert r["evidence_grade"] == "C"

        # Verification status preserved: H1 is verified_secondary, 2026 monthly are unverified_source_url
        if "bmk_2025_h1" in r["benchmark_id"]:
            assert r["verification_status"] == "verified_secondary"
        else:
            assert r["verification_status"] == "unverified_source_url"

def test_separation_of_airport_and_fir_statistics():
    """
    Task 5 Requirement 4:
    Keep OSTT_FIR overflight figures out of DAM airport throughput reporting.
    Do not delete their historical evidence.
    Document a future separate Syrian FIR statistics ledger.
    """
    with open(JSON_REPORT_V2_12_1_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    overflight_records = [r for r in records if r["metric_type"] == "airspace_overflights"]
    assert len(overflight_records) == 2, f"Expected 2 overflight records, got {len(overflight_records)}"

    for r in overflight_records:
        # Must be excluded from DAM airport throughput reporting
        assert r["is_airport_throughput"] == 0, (
            f"Overflights record {r['benchmark_id']} must have is_airport_throughput == 0"
        )
        assert r["geographic_scope"] == "OSTT_FIR"
        assert "DAM" not in r["geographic_scope"]

        # Historical evidence preserved (not deleted)
        assert r["metric_value"] in (2523, 19951)
        assert r["source_excerpt"] != ""
        assert "separate Syrian FIR statistics ledger" in r["audit_finding"]

def test_evidence_grade_distribution_v2_12_1():
    """Verify that all 31 records are graded C under V2.12.1 criteria."""
    with open(JSON_REPORT_V2_12_1_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for r in records:
        counts[r["evidence_grade"]] += 1

    assert counts["A"] == 0, "Grade A must be 0 (no primary official docs in repo)"
    assert counts["B"] == 0, "Grade B must be 0 (AksAlSer downgraded to C due to homepage URL)"
    assert counts["C"] == 31, "All 31 records must be Grade C"
    assert counts["D"] == 0, "Grade D must be 0 (airline counts and overflights reassessed to C)"
