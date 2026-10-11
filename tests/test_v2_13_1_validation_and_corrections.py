"""
Tests for Version 2.13.1 — Historical Recovery Claims Validation & Feasibility Corrections
Validates:
1. Production database invariant (SHA-256 remains identical).
2. Existence and non-emptiness of all 6 required documentation files in docs/.
3. Existence and schema validity of all 4 machine-readable reports in reports/.
4. Dimension separation in reports/v2_13_1_coverage_gaps.csv:
   - Daily coverage (Dimension A)
   - Flight-level records (Dimension B)
   - Aggregate statistics (Dimension C)
5. Coverage semantics corrections:
   - 2025 annual total (12,476) retained as full calendar year (not assigned to H2).
   - April 2026 reporting boundary classified as unresolved.
   - September 2026 monthly statistics scoped to full month (2026-09-01 to 2026-09-30).
   - SEM rows recognized as 289 dates x 2 movement directions.
6. Reconciliation of production database counts:
   - flight_events total: 1,830 rows (DAM: 1,563, ALP: 261, DEZ: 6).
   - DAM physical movements: 98 rows (concentrated on 2026-10-09 and 2026-10-10).
   - Rows with actual timestamps: 163 for DAM, 41 for ALP, 3 for DEZ, 207 total.
   - Rows scheduled-only: 1,400 for DAM, 220 for ALP, 3 for DEZ, 1,623 total.
7. Wayback Machine empirical audit validation:
   - Single snapshot for damairport.gov.sy/api/flights.php on 2026-07-09.
   - Zero schedule snapshots for 2024–2025.
8. Commercial provider claims validation:
   - Accurate pricing (FR24 Gold $44.99/yr, Business $499/yr).
   - Zero external outreach mandate for OpenSky.
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
    "docs/V2_13_1_COVERAGE_CORRECTIONS.md",
    "docs/V2_13_1_WAYBACK_AVAILABILITY_AUDIT.md",
    "docs/V2_13_1_COMMERCIAL_PROVIDER_CLAIMS_AUDIT.md",
    "docs/V2_13_1_ADSB_COVERAGE_LIMITATIONS.md",
    "docs/V2_13_1_RECOVERY_OPPORTUNITY_REASSESSMENT.md",
    "docs/V2_13_1_FINAL_DECISION.md"
]

REQUIRED_REPORTS = [
    "reports/v2_13_1_coverage_gaps.csv",
    "reports/v2_13_1_wayback_results.csv",
    "reports/v2_13_1_provider_comparison.csv",
    "reports/v2_13_1_recovery_opportunities.csv"
]

def get_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def test_production_database_untouched_v2_13_1():
    """Verify production database remains strictly untouched."""
    assert os.path.exists(PROD_DB_PATH), "Production DB missing"
    current_hash = get_hash(PROD_DB_PATH)
    assert current_hash == EXPECTED_PROD_HASH, f"Production DB hash changed: {current_hash}"

def test_v2_13_1_documentation_files_exist():
    """Verify all 6 required documentation deliverables exist and are non-empty."""
    for doc in REQUIRED_DOCS:
        assert os.path.exists(doc), f"Missing doc: {doc}"
        assert os.path.getsize(doc) > 1000, f"Doc too small: {doc} ({os.path.getsize(doc)} bytes)"

def test_v2_13_1_reports_exist_and_non_empty():
    """Verify all 4 required machine-readable reports exist and have content."""
    for rep in REQUIRED_REPORTS:
        assert os.path.exists(rep), f"Missing report: {rep}"
        assert os.path.getsize(rep) > 200, f"Report too small: {rep}"

def test_dimension_separation_in_coverage_gaps():
    """Verify coverage gaps report cleanly separates Daily Coverage, Flight Records, and Macro Stats."""
    with open("reports/v2_13_1_coverage_gaps.csv", "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 14, f"Expected 14 periods, got {len(rows)}"

    for r in rows:
        # Dimension A columns
        assert "calendar_days_total" in r
        assert "dam_days_verified_physical" in r
        assert "dam_days_schedule_only" in r
        assert "dam_days_unverified_obs" in r
        assert "dam_days_no_known_evidence" in r
        assert "days_composite_only" in r

        # Dimension B columns
        assert "dam_flight_records_physical" in r
        assert "dam_flight_records_scheduled" in r
        assert "dam_flight_records_codeshare" in r
        assert "dam_flight_records_unverified" in r
        assert "other_airports_flight_records" in r

        # Dimension C columns
        assert "macro_reported_flights" in r
        assert "macro_total_passengers" in r
        assert "macro_geographic_scope" in r
        assert "macro_reporting_period" in r

def test_coverage_semantics_corrections():
    """Verify critical semantic corrections: 2025 annual period, April unresolved, September full month."""
    with open("reports/v2_13_1_coverage_gaps.csv", "r", encoding="utf-8") as f:
        rows = {r["period_id"]: r for r in csv.DictReader(f)}

    # 1. 2025 Annual Total
    annual_2025 = rows.get("GAP-2025-ANNUAL")
    assert annual_2025 is not None
    assert annual_2025["period_start"] == "2025-01-01"
    assert annual_2025["period_end"] == "2025-12-31"
    assert annual_2025["macro_reported_flights"] == "12476"
    assert annual_2025["macro_total_passengers"] == "1434998"

    # 2. April 2026 Unresolved Boundary
    m04 = rows.get("GAP-2026-M04")
    assert m04 is not None
    assert m04["period_boundary_status"] == "unresolved_source_wording"
    assert "OSTT_FIR" in m04["macro_geographic_scope"]

    # 3. September 2026 Full Month
    m09 = rows.get("GAP-2026-M09")
    assert m09 is not None
    assert m09["period_end"] == "2026-09-30"
    assert m09["macro_reported_flights"] == "2022"

    # 4. SEM 2024 composite
    p1 = rows.get("GAP-2024-P1")
    assert p1 is not None
    assert p1["days_composite_only"] == "289"
    assert p1["dam_days_verified_physical"] == "0"
    assert p1["dam_flight_records_physical"] == "0"

def test_production_database_counts_reconciliation():
    """Verify exact flight_events row counts, airport breakdown, and actual timestamp reconciliation."""
    conn = sqlite3.connect(f"file:{PROD_DB_PATH}?mode=ro", uri=True)
    c = conn.cursor()

    # Total rows in flight_events
    c.execute("SELECT COUNT(*) FROM flight_events")
    assert c.fetchone()[0] == 1830

    # Airport breakdown
    c.execute("SELECT airport_id, COUNT(*) FROM flight_events GROUP BY airport_id ORDER BY airport_id")
    airport_counts = dict(c.fetchall())
    assert airport_counts == {"ALP": 261, "DAM": 1563, "DEZ": 6}

    # DAM record nature
    c.execute("SELECT record_nature, COUNT(*) FROM flight_events WHERE airport_id = 'DAM' GROUP BY record_nature")
    dam_nature = dict(c.fetchall())
    assert dam_nature == {
        "physical_movement": 98,
        "scheduled_service": 1428,
        "marketing_codeshare": 34,
        "unverified_movement": 3
    }

    # Rows with actual timestamps vs scheduled only
    c.execute("""
        SELECT 
            airport_id,
            SUM(CASE WHEN actual_dep_time IS NOT NULL OR actual_arr_time IS NOT NULL THEN 1 ELSE 0 END),
            SUM(CASE WHEN actual_dep_time IS NULL AND actual_arr_time IS NULL THEN 1 ELSE 0 END)
        FROM flight_events
        GROUP BY airport_id
        ORDER BY airport_id
    """)
    ts_breakdown = {r[0]: (r[1], r[2]) for r in c.fetchall()}
    assert ts_breakdown["DAM"] == (163, 1400)
    assert ts_breakdown["ALP"] == (41, 220)
    assert ts_breakdown["DEZ"] == (3, 3)

    # Physical movements date distribution (must be Oct 9 and Oct 10 only)
    c.execute("SELECT DISTINCT flight_date FROM flight_events WHERE airport_id = 'DAM' AND record_nature = 'physical_movement'")
    phys_dates = sorted([r[0] for r in c.fetchall()])
    assert phys_dates == ["2026-10-09", "2026-10-10"]

    conn.close()

def test_wayback_results_validation():
    """Verify Wayback Machine results audit shows exactly 1 snapshot for API and 0 for 2024-2025 schedules."""
    with open("reports/v2_13_1_wayback_results.csv", "r", encoding="utf-8") as f:
        results = list(csv.DictReader(f))

    assert len(results) == 4

    api_res = [r for r in results if r["target_tested"] == "damairport.gov.sy/api/flights.php"][0]
    assert api_res["contains_actual_flight_info"] == "Yes"
    assert int(api_res["flight_records_count"]) == 1982
    assert api_res["snapshot_timestamp"] == "20260709234230"
    assert int(api_res["snapshots_found_2024_2025"]) == 0

    other_targets = [r for r in results if r["target_tested"] != "damairport.gov.sy/api/flights.php"]
    for r in other_targets:
        assert r["contains_actual_flight_info"] == "No" or "No" in r["contains_actual_flight_info"]

def test_provider_claims_and_opensky_mandate():
    """Verify commercial provider claims accuracy and OpenSky external outreach removal."""
    with open("reports/v2_13_1_provider_comparison.csv", "r", encoding="utf-8") as f:
        providers = {p["provider_name"]: p for p in csv.DictReader(f)}

    assert len(providers) == 6

    fr24 = providers["FlightRadar24"]
    assert "Gold" in fr24["pricing_and_terms"]
    assert "44.99" in fr24["pricing_and_terms"]
    assert fr24["factual_verdict"] == "CONDITIONAL GO"

    opensky = providers["OpenSky Network"]
    assert "MANDATE COMPLIANCE" in opensky["audit_notes"]
    assert "NO-GO" in opensky["factual_verdict"]

def test_recovery_opportunities_reassessment():
    """Verify reclassified opportunities conform to evidence-based decision tiers."""
    with open("reports/v2_13_1_recovery_opportunities.csv", "r", encoding="utf-8") as f:
        opps = list(csv.DictReader(f))

    assert len(opps) == 6

    allowed_decisions = {"GO", "CONDITIONAL GO", "NO-GO", "NO-GO (Operational Task Removed)", "UNKNOWN"}
    for opp in opps:
        assert opp["decision"] in allowed_decisions, f"Invalid decision: {opp['decision']}"
        assert opp["exact_target"]
        assert opp["evidence_supporting_availability"]
        assert opp["next_practical_step"]

    # REC-OPP-01-V2131 (Wayback single 2026 snapshot) is GO
    assert opps[0]["opportunity_id"] == "REC-OPP-01-V2131"
    assert opps[0]["decision"] == "GO"

    # REC-OPP-02-V2131 (Wayback 2024-2025) is NO-GO
    assert opps[1]["opportunity_id"] == "REC-OPP-02-V2131"
    assert opps[1]["decision"] == "NO-GO"

    # REC-OPP-06-V2131 (OpenSky outreach) is removed
    assert opps[5]["opportunity_id"] == "REC-OPP-06-V2131"
    assert "NO-GO" in opps[5]["decision"]
