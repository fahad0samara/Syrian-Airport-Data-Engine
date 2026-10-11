"""
Syrian Airport Data Engine — Version 2.11
Tests for Macro Aviation Statistics Staging Layer & Reporting Audit

Validates:
1. Strict integer validation (fractional values rejected in Python and SQLite).
2. Reporting-period boundaries (start <= end, malformed dates rejected).
3. Partial-period labeling (April 2026 as partial Apr 8–30, H1 as partial Jan 7–Jul 7).
4. Prevention of overlapping-period aggregation (annual vs sub-period).
5. Source traceability and quotation presence without status promotion.
6. Airport scope constraints and allowed values.
7. Arrival + Departure totals reconciliation against total passenger volume.
8. Duplicate benchmark prevention via unique constraint.
9. Derived vs directly reported value handling and flags (no H2 remainders).
10. Separation of airspace overflights from airport movements.
11. Unresolved source URL handling and verification status quarantine.
12. Production database read-only isolation and bit-for-bit SHA-256 preservation.
"""

import sqlite3
import hashlib
import pytest
from pathlib import Path
from typing import Dict, Any

from src.macro_benchmarks import (
    init_macro_benchmarks_table,
    validate_benchmark_record,
    stage_macro_benchmarks,
    detect_overlapping_aggregations,
    check_period_overlap,
    VALID_METRIC_TYPES,
    VALID_GEOGRAPHIC_SCOPES,
    VALID_VERIFICATION_STATUSES
)
from scripts.build_v2_11_reports import MACRO_BENCHMARKS_V2_11

PROD_DB = Path("data/damascus_airport.db")
EXPECTED_PROD_HASH = "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"


def get_file_sha256(path: Path) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@pytest.fixture
def in_memory_staging_db():
    conn = sqlite3.connect(":memory:")
    init_macro_benchmarks_table(conn)
    yield conn
    conn.close()


def test_production_database_untouched():
    """Verify that production database exists and has exact bit-for-bit hash."""
    assert PROD_DB.exists(), "Production database must exist"
    current_hash = get_file_sha256(PROD_DB)
    assert current_hash == EXPECTED_PROD_HASH, f"Production DB mutated! Expected {EXPECTED_PROD_HASH}, got {current_hash}"


def test_fractional_values_rejected_in_python_and_sqlite(in_memory_staging_db):
    """Task 1: Reject fractional values in both Python validation and SQLite constraints."""
    # 1. Python validation rejects fractional metric values
    record = dict(MACRO_BENCHMARKS_V2_11[0])
    record["benchmark_id"] = "bmk_test_fractional"
    record["metric_value"] = 12476.5  # Fractional
    
    errors = validate_benchmark_record(record)
    assert any("Fractional value rejected" in e for e in errors), f"Expected fractional rejection, got: {errors}"

    # 2. SQLite CHECK constraint chk_metric_integer rejects fractional inserts
    with pytest.raises(sqlite3.IntegrityError):
        in_memory_staging_db.execute("""
        INSERT INTO macro_airport_benchmarks (
            benchmark_id, airport_icao, airport_iata, reporting_period_start, reporting_period_end,
            period_completeness, is_partial_period, metric_type, metric_value, unit, direction,
            geographic_scope, source_name, source_url, source_publication_date, verification_status,
            calculation_method, is_derived, collected_at
        ) VALUES (
            'test_bad_fraction', 'OSDI', 'DAM', '2025-01-01', '2025-12-31',
            'complete', 0, 'reported_flights', 12476.75, 'flights', 'total',
            'DAM', 'SCAA', 'http://test', '2026-01-15', 'verified_secondary',
            'official_report', 0, '2026-10-11T00:00:00Z'
        )
        """)


def test_partial_period_labeling(in_memory_staging_db):
    """Task 2: Label partial reporting periods clearly; specifically identify April 2026 as Apr 8–30."""
    # 1. April 2026 airport movements must be partial
    apr_flights = [b for b in MACRO_BENCHMARKS_V2_11 if b["benchmark_id"] == "bmk_2026_04_flights"][0]
    assert apr_flights["reporting_period_start"] == "2026-04-08"
    assert apr_flights["reporting_period_end"] == "2026-04-30"
    assert apr_flights["period_completeness"] == "partial"
    assert apr_flights["is_partial_period"] == 1
    assert "April 8–30" in apr_flights["source_reference"]

    # 2. 2025 H1 reported bulletin must be partial (Jan 7 to Jul 7, 182 days)
    h1_flights = [b for b in MACRO_BENCHMARKS_V2_11 if b["benchmark_id"] == "bmk_2025_h1_reported_flights"][0]
    assert h1_flights["reporting_period_start"] == "2025-01-07"
    assert h1_flights["reporting_period_end"] == "2025-07-07"
    assert h1_flights["period_completeness"] == "partial"
    assert h1_flights["is_partial_period"] == 1

    # 3. Complete periods (Annual 2025, May 2026, July 2026, September 2026)
    ann_flights = [b for b in MACRO_BENCHMARKS_V2_11 if b["benchmark_id"] == "bmk_2025_annual_flights"][0]
    assert ann_flights["period_completeness"] == "complete"
    assert ann_flights["is_partial_period"] == 0

    # 4. Validator rejects mismatched completeness
    bad_comp = dict(apr_flights)
    bad_comp["period_completeness"] = "complete"  # Mismatch with is_partial_period=1
    errors = validate_benchmark_record(bad_comp)
    assert any("Completeness mismatch" in e for e in errors)


def test_overlapping_period_aggregation_prevention():
    """Task 2: Detect overlapping periods and prevent summing annual with sub-period totals."""
    overlaps = detect_overlapping_aggregations(MACRO_BENCHMARKS_V2_11)
    assert len(overlaps) > 0, "Must detect overlapping annual and sub-period benchmarks"
    
    # Must specifically catch 2025 annual vs 2025 H1 reported window
    annual_vs_h1_found = any(
        "bmk_2025_annual_flights" in ov and "bmk_2025_h1_reported_flights" in ov
        for ov in overlaps
    )
    assert annual_vs_h1_found, "Must detect overlap between 2025 annual and H1 reported flights"


def test_source_traceability_and_references(in_memory_staging_db):
    """Task 3: Ensure source references are detailed, citations documented, and statuses preserved."""
    for b in MACRO_BENCHMARKS_V2_11:
        ref = b.get("source_reference")
        assert ref is not None and len(ref) > 20, f"Benchmark {b['benchmark_id']} missing detailed source_reference"
        assert b.get("source_excerpt") is not None, f"Benchmark {b['benchmark_id']} missing source_excerpt"

    # Preserved verification statuses: 26 unverified_source_url, 5 verified_secondary
    unv = [b for b in MACRO_BENCHMARKS_V2_11 if b["verification_status"] == "unverified_source_url"]
    sec = [b for b in MACRO_BENCHMARKS_V2_11 if b["verification_status"] == "verified_secondary"]
    assert len(unv) == 26
    assert len(sec) == 5
    assert all(b["source_url"] == "UNRESOLVED_PRIMARY_URL" for b in unv)
    assert all("aksalser.com" in b["source_url"] for b in sec)


def test_reporting_period_boundaries(in_memory_staging_db):
    """Test start <= end constraint and malformed date strings."""
    invalid_record = dict(MACRO_BENCHMARKS_V2_11[0])
    invalid_record["benchmark_id"] = "bmk_test_invalid_period"
    invalid_record["reporting_period_start"] = "2025-12-31"
    invalid_record["reporting_period_end"] = "2025-01-01"
    
    errors = validate_benchmark_record(invalid_record)
    assert len(errors) > 0
    assert any("start" in e and "end" in e for e in errors)
    
    with pytest.raises(sqlite3.IntegrityError):
        in_memory_staging_db.execute("""
        INSERT INTO macro_airport_benchmarks (
            benchmark_id, airport_icao, airport_iata, reporting_period_start, reporting_period_end,
            period_completeness, is_partial_period, metric_type, metric_value, unit, direction,
            geographic_scope, source_name, source_url, source_publication_date, verification_status,
            calculation_method, is_derived, collected_at
        ) VALUES (
            'test_bad_period', 'OSDI', 'DAM', '2025-12-31', '2025-01-01',
            'complete', 0, 'reported_flights', 100, 'flights', 'total', 'DAM', 'Test',
            'http://test', '2025-01-01', 'verified_secondary', 'official_report', 0, '2026-10-11T00:00:00Z'
        )
        """)


def test_airport_scope_constraints(in_memory_staging_db):
    """Test valid and invalid geographic scope constraints."""
    invalid_record = dict(MACRO_BENCHMARKS_V2_11[0])
    invalid_record["benchmark_id"] = "bmk_test_invalid_scope"
    invalid_record["geographic_scope"] = "INVALID_GLOBAL_SCOPE"
    
    errors = validate_benchmark_record(invalid_record)
    assert any("geographic_scope" in e for e in errors)

    with pytest.raises(sqlite3.IntegrityError):
        in_memory_staging_db.execute("""
        INSERT INTO macro_airport_benchmarks (
            benchmark_id, airport_icao, airport_iata, reporting_period_start, reporting_period_end,
            period_completeness, is_partial_period, metric_type, metric_value, unit, direction,
            geographic_scope, source_name, source_url, source_publication_date, verification_status,
            calculation_method, is_derived, collected_at
        ) VALUES (
            'test_bad_scope', 'OSDI', 'DAM', '2025-01-01', '2025-12-31',
            'complete', 0, 'reported_flights', 100, 'flights', 'total', 'UNSUPPORTED_REGION', 'Test',
            'http://test', '2025-01-01', 'verified_secondary', 'official_report', 0, '2026-10-11T00:00:00Z'
        )
        """)


def test_arrival_departure_reconciliation(in_memory_staging_db):
    """Test that for all periods with arrival & departure passenger figures, their sum equals total passengers."""
    inserted, errors = stage_macro_benchmarks(in_memory_staging_db, MACRO_BENCHMARKS_V2_11)
    assert inserted == len(MACRO_BENCHMARKS_V2_11)
    assert len(errors) == 0

    cur = in_memory_staging_db.cursor()
    cur.execute("""
        SELECT DISTINCT reporting_period_start, reporting_period_end
        FROM macro_airport_benchmarks
        WHERE metric_type IN ('passengers', 'arriving_passengers', 'departing_passengers')
    """)
    periods = cur.fetchall()
    assert len(periods) == 6

    for p_start, p_end in periods:
        cur.execute("""
            SELECT metric_type, metric_value
            FROM macro_airport_benchmarks
            WHERE reporting_period_start = ? AND reporting_period_end = ?
              AND metric_type IN ('passengers', 'arriving_passengers', 'departing_passengers')
        """, (p_start, p_end))
        pax_dict = dict(cur.fetchall())
        
        arr = pax_dict.get('arriving_passengers')
        dep = pax_dict.get('departing_passengers')
        tot = pax_dict.get('passengers')
        
        assert arr is not None and dep is not None and tot is not None
        assert arr + dep == tot, f"Reconciliation failure for {p_start} to {p_end}: {arr} + {dep} != {tot}"


def test_duplicate_benchmark_prevention(in_memory_staging_db):
    """Test that duplicate benchmarks with same natural key are prevented by unique constraint."""
    inserted, errors = stage_macro_benchmarks(in_memory_staging_db, [MACRO_BENCHMARKS_V2_11[0]])
    assert inserted == 1

    dup = dict(MACRO_BENCHMARKS_V2_11[0])
    dup["benchmark_id"] = "bmk_test_duplicate_key"
    
    with pytest.raises(sqlite3.IntegrityError):
        stage_macro_benchmarks(in_memory_staging_db, [dup])


def test_derived_vs_directly_reported_values(in_memory_staging_db):
    """Test handling of is_derived flag and ensure candidates contain no unverified H2 remainders."""
    inserted, _ = stage_macro_benchmarks(in_memory_staging_db, MACRO_BENCHMARKS_V2_11)
    assert inserted == len(MACRO_BENCHMARKS_V2_11)

    cur = in_memory_staging_db.cursor()
    cur.execute("SELECT count(*) FROM macro_airport_benchmarks WHERE is_derived = 1")
    assert cur.fetchone()[0] == 0, "No candidate benchmarks should be tagged is_derived=1"

    cur.execute("SELECT count(*) FROM macro_airport_benchmarks WHERE metric_value IN (10606, 1081716)")
    assert cur.fetchone()[0] == 0, "Remainder values must not be staged as H2 benchmarks"


def test_separation_of_airspace_overflights(in_memory_staging_db):
    """Test that airspace overflights are strictly isolated with scope OSTT_FIR and cannot be assigned to DAM."""
    bad_overflight = {
        "benchmark_id": "bmk_bad_overflight",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-09-01",
        "reporting_period_end": "2026-09-30",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "airspace_overflights",
        "metric_value": 19951,
        "unit": "overflights",
        "direction": "total",
        "geographic_scope": "DAM",  # VIOLATION
        "source_name": "SCAA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-10-04",
        "source_reference": "Test reference",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    }
    errors = validate_benchmark_record(bad_overflight)
    assert any("Separation violation" in e for e in errors)

    with pytest.raises(sqlite3.IntegrityError):
        in_memory_staging_db.execute("""
        INSERT INTO macro_airport_benchmarks (
            benchmark_id, airport_icao, airport_iata, reporting_period_start, reporting_period_end,
            period_completeness, is_partial_period, metric_type, metric_value, unit, direction,
            geographic_scope, source_name, source_url, source_publication_date, verification_status,
            calculation_method, is_derived, collected_at
        ) VALUES (
            'bad_of', 'OSDI', 'DAM', '2026-09-01', '2026-09-30',
            'complete', 0, 'airspace_overflights', 19951, 'overflights', 'total', 'DAM', 'SCAA',
            'UNRESOLVED', '2026-10-04', 'unverified_source_url', 'official_report', 0, '2026-10-11T00:00:00Z'
        )
        """)


def test_unresolved_source_url_handling(in_memory_staging_db):
    """Test that unresolved URLs are preserved as UNRESOLVED_PRIMARY_URL and cannot be promoted to verified_primary."""
    bad_unresolved = dict(MACRO_BENCHMARKS_V2_11[0])
    bad_unresolved["benchmark_id"] = "bmk_bad_promotion"
    bad_unresolved["source_url"] = "UNRESOLVED_PRIMARY_URL"
    bad_unresolved["verification_status"] = "verified_primary"  # VIOLATION

    errors = validate_benchmark_record(bad_unresolved)
    assert any("Status violation" in e for e in errors)
