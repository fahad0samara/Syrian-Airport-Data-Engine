"""
Syrian Airport Data Engine — Version 2.11
Macro Aviation Statistics Staging Layer

Provides isolated schema definitions, validation constraints, and staging logic
for aggregate annual and monthly airport benchmarks, cleanly separated from
individual flight-level telemetry and events.
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional

DDL_MACRO_AIRPORT_BENCHMARKS = """
CREATE TABLE IF NOT EXISTS macro_airport_benchmarks (
    benchmark_id TEXT PRIMARY KEY,
    airport_icao TEXT NOT NULL,
    airport_iata TEXT,
    reporting_period_start TEXT NOT NULL,
    reporting_period_end TEXT NOT NULL,
    period_completeness TEXT NOT NULL DEFAULT 'complete',
    is_partial_period INTEGER NOT NULL DEFAULT 0,
    metric_type TEXT NOT NULL,
    metric_value INTEGER NOT NULL,
    unit TEXT NOT NULL,
    direction TEXT,
    geographic_scope TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_publication_date TEXT NOT NULL,
    source_reference TEXT,
    source_excerpt TEXT,
    verification_status TEXT NOT NULL,
    calculation_method TEXT NOT NULL,
    is_derived INTEGER NOT NULL DEFAULT 0,
    collected_at TEXT NOT NULL,
    CONSTRAINT chk_period CHECK (reporting_period_start <= reporting_period_end),
    CONSTRAINT chk_period_comp CHECK (period_completeness IN ('complete', 'partial')),
    CONSTRAINT chk_is_partial CHECK (is_partial_period IN (0, 1)),
    CONSTRAINT chk_metric_val CHECK (metric_value >= 0),
    CONSTRAINT chk_metric_integer CHECK (metric_value = CAST(metric_value AS INTEGER)),
    CONSTRAINT chk_metric_type CHECK (metric_type IN (
        'reported_flights',
        'passengers',
        'arriving_passengers',
        'departing_passengers',
        'airspace_overflights',
        'operating_airlines'
    )),
    CONSTRAINT chk_unit CHECK (unit IN ('flights', 'passengers', 'airlines', 'overflights')),
    CONSTRAINT chk_direction CHECK (direction IS NULL OR direction IN ('arrival', 'departure', 'total')),
    CONSTRAINT chk_geo_scope CHECK (geographic_scope IN (
        'DAM',
        'reported_as_DAM_pending_primary_source_verification',
        'OSTT_FIR',
        'SYRIA_NATIONAL',
        'DAM_ALP_LTK'
    )),
    CONSTRAINT chk_verif_status CHECK (verification_status IN (
        'verified_primary',
        'verified_secondary',
        'partially_verified',
        'unverified_source_url',
        'contradicted'
    )),
    CONSTRAINT chk_is_derived CHECK (is_derived IN (0, 1)),
    CONSTRAINT chk_overflight_scope CHECK (
        (metric_type = 'airspace_overflights' AND geographic_scope = 'OSTT_FIR') OR
        (metric_type != 'airspace_overflights' AND geographic_scope != 'OSTT_FIR')
    ),
    CONSTRAINT uq_benchmark UNIQUE (
        airport_icao,
        reporting_period_start,
        reporting_period_end,
        metric_type,
        direction,
        geographic_scope,
        source_name
    )
);

CREATE INDEX IF NOT EXISTS idx_macro_period ON macro_airport_benchmarks (reporting_period_start, reporting_period_end);
CREATE INDEX IF NOT EXISTS idx_macro_metric ON macro_airport_benchmarks (metric_type, direction);
CREATE INDEX IF NOT EXISTS idx_macro_scope ON macro_airport_benchmarks (geographic_scope);
CREATE INDEX IF NOT EXISTS idx_macro_verif ON macro_airport_benchmarks (verification_status);
"""

VALID_METRIC_TYPES = {
    'reported_flights',
    'passengers',
    'arriving_passengers',
    'departing_passengers',
    'airspace_overflights',
    'operating_airlines'
}

VALID_GEOGRAPHIC_SCOPES = {
    'DAM',
    'reported_as_DAM_pending_primary_source_verification',
    'OSTT_FIR',
    'SYRIA_NATIONAL',
    'DAM_ALP_LTK'
}

VALID_VERIFICATION_STATUSES = {
    'verified_primary',
    'verified_secondary',
    'partially_verified',
    'unverified_source_url',
    'contradicted'
}


def init_macro_benchmarks_table(conn: sqlite3.Connection) -> None:
    """Initializes the macro_airport_benchmarks table and indexes in target database."""
    conn.executescript(DDL_MACRO_AIRPORT_BENCHMARKS)
    conn.commit()


def check_period_overlap(p1_start: str, p1_end: str, p2_start: str, p2_end: str) -> bool:
    """Returns True if [p1_start, p1_end] and [p2_start, p2_end] overlap temporally."""
    return max(p1_start, p2_start) <= min(p1_end, p2_end)


def detect_overlapping_aggregations(records: List[Dict[str, Any]]) -> List[str]:
    """
    Audits a list of benchmark records to ensure overlapping periods are never summed.
    Returns list of warning/error messages if overlapping periods are found for the same aerodrome/metric/direction.
    """
    overlaps = []
    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            r1, r2 = records[i], records[j]
            if (r1.get('airport_icao') == r2.get('airport_icao') and
                r1.get('metric_type') == r2.get('metric_type') and
                r1.get('direction') == r2.get('direction')):
                s1, e1 = str(r1.get('reporting_period_start')), str(r1.get('reporting_period_end'))
                s2, e2 = str(r2.get('reporting_period_start')), str(r2.get('reporting_period_end'))
                if check_period_overlap(s1, e1, s2, e2):
                    overlaps.append(
                        f"Overlapping period conflict between '{r1.get('benchmark_id')}' "
                        f"([{s1} to {e1}]) and '{r2.get('benchmark_id')}' ([{s2} to {e2}]) "
                        f"for metric '{r1.get('metric_type')}'"
                    )
    return overlaps


def validate_benchmark_record(record: Dict[str, Any]) -> List[str]:
    """
    Validates a benchmark record against all business rules and constraints.
    Returns a list of error messages (empty if valid).
    """
    errors = []
    
    # 1. Period boundary validation
    start_str = record.get('reporting_period_start')
    end_str = record.get('reporting_period_end')
    
    try:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
        if start_date > end_date:
            errors.append(f"Invalid period: start ({start_str}) must be <= end ({end_str})")
    except (ValueError, TypeError):
        errors.append(f"Invalid date format: start='{start_str}', end='{end_str}'; expected YYYY-MM-DD")

    # 2. Period completeness validation
    p_comp = record.get('period_completeness', 'complete')
    if p_comp not in ('complete', 'partial'):
        errors.append(f"Invalid period_completeness: '{p_comp}'; must be 'complete' or 'partial'")
        
    is_partial = record.get('is_partial_period', 0)
    if is_partial not in (0, 1):
        errors.append(f"Invalid is_partial_period: '{is_partial}'; must be 0 or 1")
        
    if (p_comp == 'partial' and is_partial != 1) or (p_comp == 'complete' and is_partial != 0):
        errors.append(f"Completeness mismatch: period_completeness='{p_comp}' but is_partial_period={is_partial}")

    # 3. Metric value validation (STRICT INTEGER ENFORCEMENT)
    val = record.get('metric_value')
    m_type = record.get('metric_type')
    
    if val is None or isinstance(val, bool) or not isinstance(val, (int, float)) or val < 0:
        errors.append(f"Invalid metric_value: '{val}' must be a non-negative integer")
    elif isinstance(val, float) and not val.is_integer():
        errors.append(f"Fractional value rejected: '{val}' must be an exact integer for metric_type '{m_type}'")

    # 4. Metric type validation
    if m_type not in VALID_METRIC_TYPES:
        errors.append(f"Invalid metric_type: '{m_type}'; must be one of {sorted(VALID_METRIC_TYPES)}")

    # 5. Scope and overflight separation
    scope = record.get('geographic_scope')
    if scope not in VALID_GEOGRAPHIC_SCOPES:
        errors.append(f"Invalid geographic_scope: '{scope}'; must be one of {sorted(VALID_GEOGRAPHIC_SCOPES)}")
        
    if m_type == 'airspace_overflights' and scope != 'OSTT_FIR':
        errors.append(f"Separation violation: airspace_overflights must have geographic_scope 'OSTT_FIR', got '{scope}'")
    if m_type != 'airspace_overflights' and scope == 'OSTT_FIR':
        errors.append(f"Separation violation: non-overflight metric '{m_type}' cannot have scope 'OSTT_FIR'")

    # 6. Verification status validation
    v_status = record.get('verification_status')
    if v_status not in VALID_VERIFICATION_STATUSES:
        errors.append(f"Invalid verification_status: '{v_status}'; must be one of {sorted(VALID_VERIFICATION_STATUSES)}")

    # 7. Unresolved URL consistency
    url = record.get('source_url', '')
    if url == 'UNRESOLVED_PRIMARY_URL' and v_status == 'verified_primary':
        errors.append("Status violation: cannot mark verified_primary when source_url is UNRESOLVED_PRIMARY_URL")

    # 8. Direction validation
    direction = record.get('direction')
    if direction not in (None, 'arrival', 'departure', 'total'):
        errors.append(f"Invalid direction: '{direction}'; must be arrival, departure, total, or None")

    if m_type == 'arriving_passengers' and direction != 'arrival':
        errors.append(f"Direction mismatch: arriving_passengers must have direction 'arrival', got '{direction}'")
    if m_type == 'departing_passengers' and direction != 'departure':
        errors.append(f"Direction mismatch: departing_passengers must have direction 'departure', got '{direction}'")

    return errors


def stage_macro_benchmarks(conn: sqlite3.Connection, records: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
    """
    Stages a batch of candidate benchmark records into macro_airport_benchmarks.
    Returns (inserted_count, validation_errors).
    """
    all_errors = []
    valid_records = []
    
    for r in records:
        errs = validate_benchmark_record(r)
        if errs:
            all_errors.extend([f"Record {r.get('benchmark_id')}: {e}" for e in errs])
        else:
            valid_records.append(r)
            
    if all_errors:
        return 0, all_errors

    insert_sql = """
    INSERT INTO macro_airport_benchmarks (
        benchmark_id,
        airport_icao,
        airport_iata,
        reporting_period_start,
        reporting_period_end,
        period_completeness,
        is_partial_period,
        metric_type,
        metric_value,
        unit,
        direction,
        geographic_scope,
        source_name,
        source_url,
        source_publication_date,
        source_reference,
        source_excerpt,
        verification_status,
        calculation_method,
        is_derived,
        collected_at
    ) VALUES (
        :benchmark_id,
        :airport_icao,
        :airport_iata,
        :reporting_period_start,
        :reporting_period_end,
        :period_completeness,
        :is_partial_period,
        :metric_type,
        :metric_value,
        :unit,
        :direction,
        :geographic_scope,
        :source_name,
        :source_url,
        :source_publication_date,
        :source_reference,
        :source_excerpt,
        :verification_status,
        :calculation_method,
        :is_derived,
        :collected_at
    )
    """
    cur = conn.cursor()
    cur.executemany(insert_sql, valid_records)
    conn.commit()
    return len(valid_records), []

