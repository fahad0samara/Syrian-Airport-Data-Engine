"""
Tests for Version 2.13 — Historical Data Recovery Feasibility & Recovery Roadmap
Validates:
1. Production database invariant (SHA-256 remains identical).
2. Existence and completeness of all 6 required documentation files in docs/.
3. Existence and schema validity of all 4 machine-readable reports in reports/.
4. Coverage of all 18 investigated historical sources with valid recommendations.
5. Chronological gap analysis covering 14 discrete periods spanning 2024-01-01 to present across 6 categories.
6. Specifications of all 6 concrete recovery opportunities (REC-OPP-01 to REC-OPP-06) with valid priorities.
7. Production database state verification (1,830 flight events concentrated in 2026 snapshot; zero 2024-2025 events).
8. Segregation between macro benchmarks staging and production flight events.
"""

import os
import csv
import json
import sqlite3
import hashlib
import pytest
from typing import List, Dict, Any

PROD_DB_PATH = "data/damascus_airport.db"
STAGING_DB_PATH = "data/macro_benchmarks_staging.db"

EXPECTED_PROD_HASH = "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"

REQUIRED_DOCS = [
    "docs/V2_13_HISTORICAL_COVERAGE_GAP_ANALYSIS.md",
    "docs/V2_13_HISTORICAL_SOURCE_INVENTORY.md",
    "docs/V2_13_SOURCE_COMPARISON_MATRIX.md",
    "docs/V2_13_DATA_RECOVERY_OPPORTUNITIES.md",
    "docs/V2_13_HISTORICAL_RECOVERY_ROADMAP.md",
    "docs/V2_13_GO_NO_GO_DECISION.md"
]

REQUIRED_REPORTS = [
    "reports/v2_13_historical_source_inventory.csv",
    "reports/v2_13_historical_source_inventory.json",
    "reports/v2_13_coverage_gaps.csv",
    "reports/v2_13_recovery_opportunities.csv"
]

def get_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def test_production_database_untouched():
    """Verify production database has not been altered (bit-for-bit invariant)."""
    assert os.path.exists(PROD_DB_PATH), "Production database does not exist."
    current_hash = get_hash(PROD_DB_PATH)
    assert current_hash == EXPECTED_PROD_HASH, f"Production database hash changed! Got {current_hash}"

def test_v2_13_documentation_files_exist_and_non_empty():
    """Verify all 6 required documentation deliverables exist and contain substantial content."""
    for doc_path in REQUIRED_DOCS:
        assert os.path.exists(doc_path), f"Required documentation file missing: {doc_path}"
        assert os.path.getsize(doc_path) > 1000, f"Documentation file too small: {doc_path} ({os.path.getsize(doc_path)} bytes)"

def test_v2_13_machine_readable_reports_exist_and_valid():
    """Verify all 4 required reports exist and are non-empty."""
    for report_path in REQUIRED_REPORTS:
        assert os.path.exists(report_path), f"Required report missing: {report_path}"
        assert os.path.getsize(report_path) > 200, f"Report file too small: {report_path}"

def test_source_inventory_coverage_and_recommendations():
    """Verify source inventory contains exactly 18 sources and valid recommendations."""
    inv_csv = "reports/v2_13_historical_source_inventory.csv"
    inv_json = "reports/v2_13_historical_source_inventory.json"

    with open(inv_csv, "r", encoding="utf-8") as f:
        csv_records = list(csv.DictReader(f))
    with open(inv_json, "r", encoding="utf-8") as f:
        json_records = json.load(f)

    assert len(csv_records) == 18, f"Expected 18 sources in CSV, got {len(csv_records)}"
    assert len(json_records) == 18, f"Expected 18 sources in JSON, got {len(json_records)}"

    valid_recommendations = {"GO", "CONDITIONAL GO", "NO-GO"}
    source_ids = set()

    for r in json_records:
        source_ids.add(r["source_id"])
        assert r["recommendation"] in valid_recommendations, f"Invalid recommendation: {r['recommendation']}"
        assert "provider_name" in r and r["provider_name"]
        assert "provider_category" in r
        assert "cost_category" in r
        assert "dam_coverage_evidence" in r

    assert "opensky_network" in source_ids
    assert "damairport_official" in source_ids
    assert "scaa_publications" in source_ids
    assert "syrian_mot" in source_ids
    assert "wayback_machine" in source_ids
    assert "flightradar24_commercial" in source_ids
    assert "flightaware_aeroapi" in source_ids

def test_coverage_gaps_chronology_and_categories():
    """Verify coverage gaps report covers all 14 periods spanning 2024 to 2026 across 6 categories."""
    gaps_csv = "reports/v2_13_coverage_gaps.csv"
    with open(gaps_csv, "r", encoding="utf-8") as f:
        periods = list(csv.DictReader(f))

    assert len(periods) == 14, f"Expected 14 chronological periods, got {len(periods)}"

    period_ids = [p["period_id"] for p in periods]
    assert "GAP-2024-P1" in period_ids
    assert "GAP-2024-P4" in period_ids
    assert "GAP-2025-H1" in period_ids
    assert "GAP-2025-H2" in period_ids
    assert "GAP-2026-M04" in period_ids
    assert "GAP-2026-SNAPSHOT" in period_ids

    # Check earliest start and latest end
    assert periods[0]["period_start"] == "2024-01-01"
    assert periods[-1]["period_end"] == "2026-10-31"

    # Verify that the 6 categories are represented as columns
    expected_categories = [
        "verified_physical_movements",
        "commercial_schedules",
        "unverified_movement_observations",
        "aggregate_airport_statistics",
        "national_airspace_statistics",
        "unknown_or_unavailable"
    ]
    for cat in expected_categories:
        assert cat in periods[0], f"Category column missing: {cat}"

def test_recovery_opportunities_priorities_and_specifications():
    """Verify all 6 recovery opportunities exist with valid priority rankings and actionable steps."""
    opp_csv = "reports/v2_13_recovery_opportunities.csv"
    with open(opp_csv, "r", encoding="utf-8") as f:
        opportunities = list(csv.DictReader(f))

    assert len(opportunities) == 6, f"Expected 6 recovery opportunities, got {len(opportunities)}"

    valid_priorities = {"P0", "P1", "P2", "P3", "P4"}
    opp_ids = set()

    for opp in opportunities:
        opp_ids.add(opp["opportunity_id"])
        assert opp["priority_level"] in valid_priorities, f"Invalid priority: {opp['priority_level']}"
        assert opp["actionable_next_step"], f"Missing actionable next step for {opp['opportunity_id']}"
        assert opp["estimated_cost_category"]
        assert opp["confidence_level"] in {"High", "Medium", "Low"}

    assert opp_ids == {
        "REC-OPP-01",
        "REC-OPP-02",
        "REC-OPP-03",
        "REC-OPP-04",
        "REC-OPP-05",
        "REC-OPP-06"
    }

def test_production_db_state_and_temporal_concentration():
    """Verify production database tables and confirm that flight_events has zero rows prior to 2026-09-30."""
    conn = sqlite3.connect(f"file:{PROD_DB_PATH}?mode=ro", uri=True)
    cursor = conn.cursor()

    # Total flight events count
    cursor.execute("SELECT COUNT(*) FROM flight_events")
    total_events = cursor.fetchone()[0]
    assert total_events == 1830, f"Expected 1830 flight events, got {total_events}"

    # Events prior to 2026-09-30 must be exactly 0
    cursor.execute("SELECT COUNT(*) FROM flight_events WHERE scheduled_dep_time < '2026-09-30' AND scheduled_arr_time < '2026-09-30'")
    prior_events = cursor.fetchone()[0]
    assert prior_events == 0, f"Expected 0 flight events prior to 2026-09-30, got {prior_events}"

    # Verify actual movement timestamps count
    cursor.execute("SELECT COUNT(*) FROM flight_events WHERE actual_dep_time IS NOT NULL OR actual_arr_time IS NOT NULL")
    actual_movements = cursor.fetchone()[0]
    assert actual_movements == 207, f"Expected 207 actual movements, got {actual_movements}"

    # Verify SEM composite records
    cursor.execute("SELECT COUNT(*) FROM historical_daily_movements_2024")
    sem_count = cursor.fetchone()[0]
    assert sem_count == 578, f"Expected 578 SEM composite rows, got {sem_count}"

    conn.close()

def test_macro_staging_benchmarks_isolation():
    """Verify macro staging benchmarks remain intact with all 31 records at Grade C and preserved verification status."""
    conn = sqlite3.connect(f"file:{STAGING_DB_PATH}?mode=ro", uri=True)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM macro_airport_benchmarks")
    benchmarks_count = cursor.fetchone()[0]
    assert benchmarks_count == 31, f"Expected 31 macro benchmarks, got {benchmarks_count}"

    cursor.execute("SELECT verification_status, COUNT(*) FROM macro_airport_benchmarks GROUP BY verification_status")
    status_counts = dict(cursor.fetchall())
    assert status_counts.get("verified_secondary") == 5, f"Expected 5 verified_secondary, got {status_counts.get('verified_secondary')}"
    assert status_counts.get("unverified_source_url") == 26, f"Expected 26 unverified_source_url, got {status_counts.get('unverified_source_url')}"

    conn.close()

    # Verify all 31 records are Grade C in the V2.12.2 verification report
    audit_report_path = "reports/v2_12_2_source_verification.json"
    assert os.path.exists(audit_report_path), f"Audit report missing: {audit_report_path}"
    with open(audit_report_path, "r", encoding="utf-8") as f:
        records = json.load(f)
    assert len(records) == 31
    assert all(r["evidence_grade"] == "C" for r in records), "All 31 staged benchmarks must be Grade C"

