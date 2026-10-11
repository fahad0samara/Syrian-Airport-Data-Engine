# Syrian Airport Data Engine — Version 2.11
# Macro Statistics Quality & Reporting Audit Report

**Document Identifier**: `docs/V2_11_MACRO_STATISTICS_AUDIT.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Target Airspace**: Damascus Flight Information Region (`OSTT_FIR`)  
**Scope**: Macro Aviation Statistics Data Quality, Integer Precision, Period Overlap Defense, Source Traceability, and Staging Audit  
**Status**: APPROVED AUDIT SPECIFICATION & STAGING INVENTORY  
**Verification Hash Invariant**: Production database `data/damascus_airport.db` SHA-256 remains bit-for-bit identical (`c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`).

---

## 1. Executive Summary & Audit Mandate

The Version 2.11 milestone builds directly on the Version 2.10 macro statistics staging layer. While Version 2.10 established the physical schema and baseline candidate staging in `data/macro_benchmarks_staging.db`, Version 2.11 executes a rigorous quality and reporting audit to ensure that:

1. **Integer Integrity is Inviolable**: All count metrics (`reported_flights`, `passengers`, `arriving_passengers`, `departing_passengers`, `operating_airlines`, and `airspace_overflights`) are strictly validated as non-fractional whole integers at both the Python application layer and SQLite database constraint layer.
2. **Period-Aware Reporting Prevents Aggregation Fallacies**: Overlapping reporting periods are formally tracked and prevented from being summed together. Annual figures can never be added to semi-annual or monthly figures. Non-standard calendar periods are explicitly labeled with their exact calendar span and completeness status.
3. **Partial Reporting Periods are Clearly Disclosed**: Specifically, April 2026 airport movements (`2026-04-08` through `2026-04-30`, covering 23 operational days post-reopening) are categorized as `partial`, distinct from complete monthly overflight observations (`2026-04-01` through `2026-04-30`). Similarly, the 2025 H1 SCAA bulletin (`2025-01-07` through `2025-07-07`, covering 182 days commemorating six months of operations) is marked as `partial` relative to the full calendar half-year.
4. **Source Traceability is Documented with Precision**: Existing verification statuses are preserved without false promotions. Primary versus secondary source distinctions are maintained. Quoted source excerpts, publication titles, dates, and paragraph-level citations are attached to every staged record.
5. **Analytical Remainders are Excluded from Benchmark Staging**: Subtraction remainders ($12,476 - 1,870 = 10,606$ flights and $1,434,998 - 353,282 = 1,081,716$ passengers) are recognized as derived residual calculations spanning fragmented date intervals (`2025-01-01`–`2025-01-06` and `2025-07-08`–`2025-12-31`) rather than published authoritative benchmarks. Consequently, they are quarantined from the official benchmark register.

---

## 2. Architectural & Database Schema Upgrades

To support period completeness and audit traceability, the schema in `data/macro_benchmarks_staging.db` was upgraded with four key structural additions:

```sql
CREATE TABLE IF NOT EXISTS macro_airport_benchmarks (
    benchmark_id TEXT PRIMARY KEY,
    airport_icao TEXT NOT NULL,
    airport_iata TEXT,
    reporting_period_start TEXT NOT NULL,
    reporting_period_end TEXT NOT NULL,
    period_completeness TEXT NOT NULL DEFAULT 'complete' 
        CHECK (period_completeness IN ('complete', 'partial')),
    is_partial_period INTEGER NOT NULL DEFAULT 0 
        CHECK (is_partial_period IN (0, 1)),
    metric_type TEXT NOT NULL 
        CHECK (metric_type IN (
            'reported_flights', 
            'passengers', 
            'arriving_passengers', 
            'departing_passengers', 
            'airspace_overflights', 
            'operating_airlines'
        )),
    metric_value REAL NOT NULL,
    unit TEXT NOT NULL 
        CHECK (unit IN ('flights', 'passengers', 'overflights', 'airlines')),
    direction TEXT 
        CHECK (direction IN ('arrival', 'departure', 'total', NULL)),
    geographic_scope TEXT NOT NULL 
        CHECK (geographic_scope IN (
            'DAM', 
            'OSTT_FIR', 
            'reported_as_DAM_pending_primary_source_verification'
        )),
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_publication_date TEXT NOT NULL,
    source_reference TEXT,
    source_excerpt TEXT NOT NULL,
    verification_status TEXT NOT NULL 
        CHECK (verification_status IN (
            'verified_primary', 
            'verified_secondary', 
            'unverified_source_url', 
            'rejected'
        )),
    calculation_method TEXT NOT NULL 
        CHECK (calculation_method IN (
            'official_report', 
            'derived_subtraction', 
            'derived_sum', 
            'analytical_estimate'
        )),
    is_derived INTEGER NOT NULL DEFAULT 0 
        CHECK (is_derived IN (0, 1)),
    collected_at TEXT NOT NULL,

    -- Boundary and Precision Constraints
    CONSTRAINT chk_period_order CHECK (reporting_period_start <= reporting_period_end),
    CONSTRAINT chk_positive_value CHECK (metric_value >= 0),
    CONSTRAINT chk_metric_integer CHECK (metric_value = CAST(metric_value AS INTEGER)),
    CONSTRAINT chk_overflight_scope CHECK (
        (metric_type = 'airspace_overflights' AND geographic_scope = 'OSTT_FIR') OR
        (metric_type != 'airspace_overflights' AND geographic_scope != 'OSTT_FIR')
    )
);
```

### Key Schema Improvements:
1. `period_completeness`: Explicit enumeration (`'complete'`, `'partial'`).
2. `is_partial_period`: Boolean indicator (`0` or `1`) for high-speed indexing and query filters.
3. `source_reference`: Detailed citation string storing document title, publication details, and paragraph/section numbers.
4. `CONSTRAINT chk_metric_integer CHECK (metric_value = CAST(metric_value AS INTEGER))`: SQLite-level enforcement guaranteeing zero fractional values in stored count metrics.

---

## 3. Dual-Layer Integer Validation

All count metrics in the macro aviation staging layer represent discrete entities (flights, human passengers, aircraft overflights, or operating air carriers). Under no circumstances can these metrics accept fractional values.

### 3.1 Python Application Layer Validation
In `src/macro_benchmarks.py`, the validator `validate_benchmark_record()` executes strict type and value checks:
- Rejects boolean values (which in Python subclass `int`).
- Rejects any numerical value where `isinstance(val, float)` has a non-zero fractional component (e.g. `12.5`).
- Rejects non-numeric types (strings, nulls).
- Validates non-negativity (`metric_value >= 0`).

```python
val = record.get("metric_value")
if val is None or isinstance(val, bool) or not isinstance(val, (int, float)):
    errors.append(f"metric_value must be a valid integer number, got {type(val).__name__}: {val}")
elif isinstance(val, float) and not val.is_integer():
    errors.append(f"metric_value must be a whole integer for count metrics, got fractional float: {val}")
elif val < 0:
    errors.append(f"metric_value must be non-negative (>= 0), got: {val}")
```

### 3.2 Database Engine Layer Validation
Even if bad data bypasses application code, SQLite enforces:
$$\text{metric\_value} = \text{CAST}(\text{metric\_value AS INTEGER})$$
Any attempt to insert `492.5` or `12476.1` triggers an immediate `sqlite3.IntegrityError: CHECK constraint failed: chk_metric_integer`.

---

## 4. Period-Aware Reporting & Overlap Prevention

### 4.1 The Overlap Hazard
A critical vulnerability in aggregate aviation reporting is the accidental summation of nested or overlapping periods. For example, summing the 2025 Annual reported flights ($12,476$) with the 2025 H1 reported flights ($1,870$) would result in double-counting:
$$12,476 + 1,870 = 14,346 \quad \text{(FATAL DOUBLE-COUNT)}$$

### 4.2 Automated Overlap Detection Engine
To eliminate this risk, `src/macro_benchmarks.py` introduces `detect_overlapping_aggregations()` and `check_period_overlap()`:
$$\text{Overlap} \iff \max(\text{start}_1, \text{start}_2) \le \min(\text{end}_1, \text{end}_2)$$
When two records share the same aerodrome (`airport_icao`), metric type (`metric_type`), and directional scope (`direction`), any temporal overlap triggers an audit warning, and aggregation functions refuse to sum them.

### 4.3 Identified Overlapping Pairs in the Benchmark Register
The V2.11 audit detected four legitimate overlapping pairs in the staging dataset:

| Pair ID | Metric | Period A | Period B | Status |
|:---|:---|:---|:---|:---|
| **OVL-01** | `reported_flights` | 2025 Annual (`2025-01-01` to `2025-12-31`) | 2025 H1 Reported (`2025-01-07` to `2025-07-07`) | Flagged & Separated |
| **OVL-02** | `passengers` (total) | 2025 Annual (`2025-01-01` to `2025-12-31`) | 2025 H1 Reported (`2025-01-07` to `2025-07-07`) | Flagged & Separated |
| **OVL-03** | `arriving_passengers` | 2025 Annual (`2025-01-01` to `2025-12-31`) | 2025 H1 Reported (`2025-01-07` to `2025-07-07`) | Flagged & Separated |
| **OVL-04** | `departing_passengers` | 2025 Annual (`2025-01-01` to `2025-12-31`) | 2025 H1 Reported (`2025-01-07` to `2025-07-07`) | Flagged & Separated |

These records cannot be combined. They represent alternative granularity views from distinct official reporting announcements.

---

## 5. Precise Period Boundaries & Partial-Period Disclosure

### 5.1 April 2026: Partial Month vs Complete Month
Damascus International Airport was formally reopened for commercial flights on **April 8, 2026**. Consequently:
- **Airport Runway Operations (DAM)**:
  - Reporting Period: `2026-04-08` to `2026-04-30` (23 calendar days).
  - Completeness: `partial` (`is_partial_period = 1`).
  - Metrics: 492 flights, 34,347 total passengers (18,385 arr / 15,962 dep), 9 operating airlines.
  - Reason: The airport was closed between April 1 and April 7, 2026. Treating this figure as a full calendar month would distort daily frequency calculations.
- **Airspace Overflights (OSTT_FIR)**:
  - Reporting Period: `2026-04-01` to `2026-04-30` (30 calendar days).
  - Completeness: `complete` (`is_partial_period = 0`).
  - Metrics: 2,523 overflights.
  - Reason: Syrian airspace navigation services monitored overflights across the entire calendar month.

### 5.2 2025 SCAA H1 Bulletin: 6-Month Operational Milestone
The SCAA press conference on July 15, 2025, reported on the six-month operational period following the resumption of services on January 7, 2025:
- Reporting Period: `2025-01-07` to `2025-07-07` (182 calendar days).
- Completeness: `partial` (`is_partial_period = 1`).
- Metrics: 1,870 flights, 353,282 total passengers (178,728 arr / 174,554 dep), 12 operating airlines.
- Distinction: This period omits January 1–6, 2025, and July 8–December 31, 2025. It cannot be designated as calendar H1 (January 1 to June 30).

---

## 6. Source Traceability & Verification Status Preservation

In accordance with strict historical audit standards:
- **No Promotion of Unverified Claims**: Records lacking authenticated direct primary document URLs remain strictly classified as `unverified_source_url` under `reported_as_DAM_pending_primary_source_verification`.
- **Secondary Source Evidence**: Records substantiated by media transcripts quoting official SCAA statements are classified as `verified_secondary`.

### Complete Inventory of Staged Records (31 Benchmarks)

| Benchmark ID | Period Start | Period End | Compl. | Metric Type | Value | Unit | Dir. | Scope | Status | Source Citation & Reference |
|:---|:---|:---|:---|:---|---:|:---|:---|:---|:---|:---|
| `bmk_2025_annual_flights` | 2025-01-01 | 2025-12-31 | complete | reported_flights | 12,476 | flights | total | pending_primary | unverified_source_url | SANA / Rebuilding Syria, 'Civil Aviation Annual Report 2025', pub 2026-01-15, para 1. |
| `bmk_2025_annual_passengers_total` | 2025-01-01 | 2025-12-31 | complete | passengers | 1,434,998 | passengers | total | pending_primary | unverified_source_url | SANA / Rebuilding Syria, 'Civil Aviation Annual Report 2025', pub 2026-01-15, para 2. |
| `bmk_2025_annual_passengers_arr` | 2025-01-01 | 2025-12-31 | complete | arriving_passengers | 715,392 | passengers | arr | pending_primary | unverified_source_url | SANA / Rebuilding Syria, 'Civil Aviation Annual Report 2025', pub 2026-01-15, para 3. |
| `bmk_2025_annual_passengers_dep` | 2025-01-01 | 2025-12-31 | complete | departing_passengers | 719,606 | passengers | dep | pending_primary | unverified_source_url | SANA / Rebuilding Syria, 'Civil Aviation Annual Report 2025', pub 2026-01-15, para 3. |
| `bmk_2025_h1_reported_flights` | 2025-01-07 | 2025-07-07 | partial | reported_flights | 1,870 | flights | total | DAM | verified_secondary | AksAlSer / Yalla Syria, 'Civil Aviation: 1,870 Flights in First Half', pub 2025-07-15, para 2. |
| `bmk_2025_h1_reported_passengers_total` | 2025-01-07 | 2025-07-07 | partial | passengers | 353,282 | passengers | total | DAM | verified_secondary | AksAlSer / Yalla Syria, 'Civil Aviation: 353,282 Passengers', pub 2025-07-15, para 1. |
| `bmk_2025_h1_reported_passengers_arr` | 2025-01-07 | 2025-07-07 | partial | arriving_passengers | 178,728 | passengers | arr | DAM | verified_secondary | AksAlSer / Yalla Syria, 'Civil Aviation: H1 2025 Traffic Disaggregation', pub 2025-07-15, para 3. |
| `bmk_2025_h1_reported_passengers_dep` | 2025-01-07 | 2025-07-07 | partial | departing_passengers | 174,554 | passengers | dep | DAM | verified_secondary | AksAlSer / Yalla Syria, 'Civil Aviation: H1 2025 Traffic Disaggregation', pub 2025-07-15, para 3. |
| `bmk_2025_h1_reported_airlines` | 2025-01-07 | 2025-07-07 | partial | operating_airlines | 12 | airlines | total | DAM | verified_secondary | AksAlSer / Yalla Syria, 'Civil Aviation: Operating Carriers in H1', pub 2025-07-15, para 4. |
| `bmk_2026_04_flights` | 2026-04-08 | 2026-04-30 | partial | reported_flights | 492 | flights | total | pending_primary | unverified_source_url | SANA, 'Traffic Resumption at Damascus Airport (April 8–30)', pub 2026-05-05, para 1. |
| `bmk_2026_04_passengers_total` | 2026-04-08 | 2026-04-30 | partial | passengers | 34,347 | passengers | total | pending_primary | unverified_source_url | SANA, 'Traffic Resumption at Damascus Airport (April 8–30)', pub 2026-05-05, para 2. |
| `bmk_2026_04_passengers_arr` | 2026-04-08 | 2026-04-30 | partial | arriving_passengers | 18,385 | passengers | arr | pending_primary | unverified_source_url | SANA, 'Traffic Resumption at Damascus Airport (April 8–30)', pub 2026-05-05, para 3. |
| `bmk_2026_04_passengers_dep` | 2026-04-08 | 2026-04-30 | partial | departing_passengers | 15,962 | passengers | dep | pending_primary | unverified_source_url | SANA, 'Traffic Resumption at Damascus Airport (April 8–30)', pub 2026-05-05, para 3. |
| `bmk_2026_04_airlines` | 2026-04-08 | 2026-04-30 | partial | operating_airlines | 9 | airlines | total | pending_primary | unverified_source_url | SANA, 'Operating Carriers Bulletin (April 8–30)', pub 2026-05-05, para 4. |
| `bmk_2026_04_overflights` | 2026-04-01 | 2026-04-30 | complete | airspace_overflights | 2,523 | overflights | total | OSTT_FIR | unverified_source_url | SANA, 'April 2026 Airspace Overflights Report', pub 2026-05-05, para 5. |
| `bmk_2026_05_flights` | 2026-05-01 | 2026-05-31 | complete | reported_flights | 1,532 | flights | total | pending_primary | unverified_source_url | SANA, 'May 2026 Air Traffic Bulletin', pub 2026-06-04, para 1. |
| `bmk_2026_05_passengers_total` | 2026-05-01 | 2026-05-31 | complete | passengers | 148,305 | passengers | total | pending_primary | unverified_source_url | SANA, 'May 2026 Air Traffic Bulletin', pub 2026-06-04, para 2. |
| `bmk_2026_05_passengers_arr` | 2026-05-01 | 2026-05-31 | complete | arriving_passengers | 83,357 | passengers | arr | pending_primary | unverified_source_url | SANA, 'May 2026 Air Traffic Bulletin', pub 2026-06-04, para 3. |
| `bmk_2026_05_passengers_dep` | 2026-05-01 | 2026-05-31 | complete | departing_passengers | 64,948 | passengers | dep | pending_primary | unverified_source_url | SANA, 'May 2026 Air Traffic Bulletin', pub 2026-06-04, para 3. |
| `bmk_2026_05_airlines` | 2026-05-01 | 2026-05-31 | complete | operating_airlines | 13 | airlines | total | pending_primary | unverified_source_url | SANA, 'May 2026 Operating Airlines Bulletin', pub 2026-06-04, para 4. |
| `bmk_2026_07_flights` | 2026-07-01 | 2026-07-31 | complete | reported_flights | 2,088 | flights | total | pending_primary | unverified_source_url | SANA, 'July 2026 Summer Passenger Traffic Bulletin', pub 2026-08-04, para 1. |
| `bmk_2026_07_passengers_total` | 2026-07-01 | 2026-07-31 | complete | passengers | 243,260 | passengers | total | pending_primary | unverified_source_url | SANA, 'July 2026 Summer Passenger Traffic Bulletin', pub 2026-08-04, para 2. |
| `bmk_2026_07_passengers_arr` | 2026-07-01 | 2026-07-31 | complete | arriving_passengers | 147,318 | passengers | arr | pending_primary | unverified_source_url | SANA, 'July 2026 Summer Passenger Traffic Bulletin', pub 2026-08-04, para 3. |
| `bmk_2026_07_passengers_dep` | 2026-07-01 | 2026-07-31 | complete | departing_passengers | 95,942 | passengers | dep | pending_primary | unverified_source_url | SANA, 'July 2026 Summer Passenger Traffic Bulletin', pub 2026-08-04, para 3. |
| `bmk_2026_07_airlines` | 2026-07-01 | 2026-07-31 | complete | operating_airlines | 16 | airlines | total | pending_primary | unverified_source_url | SANA, 'July 2026 Summer Passenger Traffic Bulletin', pub 2026-08-04, para 4. |
| `bmk_2026_09_flights` | 2026-09-01 | 2026-09-30 | complete | reported_flights | 2,022 | flights | total | pending_primary | unverified_source_url | SANA, 'September 2026 Traffic Performance', pub 2026-10-04, para 1. |
| `bmk_2026_09_passengers_total` | 2026-09-01 | 2026-09-30 | complete | passengers | 229,693 | passengers | total | pending_primary | unverified_source_url | SANA, 'September 2026 Traffic Performance', pub 2026-10-04, para 2. |
| `bmk_2026_09_passengers_arr` | 2026-09-01 | 2026-09-30 | complete | arriving_passengers | 98,693 | passengers | arr | pending_primary | unverified_source_url | SANA, 'September 2026 Traffic Performance', pub 2026-10-04, para 3. |
| `bmk_2026_09_passengers_dep` | 2026-09-01 | 2026-09-30 | complete | departing_passengers | 131,000 | passengers | dep | pending_primary | unverified_source_url | SANA, 'September 2026 Traffic Performance', pub 2026-10-04, para 3. |
| `bmk_2026_09_airlines` | 2026-09-01 | 2026-09-30 | complete | operating_airlines | 17 | airlines | total | pending_primary | unverified_source_url | SANA, 'September 2026 Traffic Performance', pub 2026-10-04, para 4. |
| `bmk_2026_09_overflights` | 2026-09-01 | 2026-09-30 | complete | airspace_overflights | 19,951 | overflights | total | OSTT_FIR | unverified_source_url | SANA, 'September 2026 Syrian Airspace Overflights Report', pub 2026-10-04, para 5. |

---

## 7. Derived Subtraction Remainders: Policy & Status

In previous exploratory drafts, mathematical remainders were calculated:
- **Flight Remainder**: $12,476 - 1,870 = 10,606$ flights
- **Passenger Remainder**: $1,434,998 - 353,282 = 1,081,716$ passengers

### Why These are Excluded from Staged Benchmarks:
1. **Discontinuous Period**: The remainder represents the discontinuous union of two separated intervals:
   $$\text{Interval}_1 = [2025\text{-}01\text{-}01, 2025\text{-}01\text{-}06], \quad \text{Interval}_2 = [2025\text{-}07\text{-}08, 2025\text{-}12\text{-}31]$$
   It does not correspond to standard calendar H2 (`2025-07-01` through `2025-12-31`).
2. **Not Directly Reported**: No civil aviation authority published the numbers $10,606$ or $1,081,716$. They are synthetic analytical derivations.
3. **Database Integrity**: The staging database is reserved for actual reported benchmarks. Derived analytical artifacts belong in analytical documentation rather than official benchmark registers.

---

## 8. Verification & Production Safety Assurance

### 8.1 Automated Test Execution
The complete test suite of 153 tests was executed:
- **Macro Benchmark Specific Tests** (12 tests in `tests/test_macro_benchmarks.py`):
  - `test_production_database_untouched`: Verified production database remains unmodified.
  - `test_fractional_values_rejected_in_python_and_sqlite`: Verified that fractional floats are rejected by both Python validators and SQLite `CHECK` constraints.
  - `test_partial_period_labeling`: Verified that partial periods (such as April 8–30, 2026, and Jan 7–Jul 7, 2025) are correctly classified.
  - `test_overlapping_period_aggregation_prevention`: Verified overlap detection algorithm and aggregation rejection.
  - `test_source_traceability_and_references`: Verified citation string existence, publication dates, and source excerpts.
  - `test_reporting_period_boundaries`: Verified start date <= end date constraints.
  - `test_airport_scope_constraints`: Verified DAM vs OSTT_FIR scope enforcement.
  - `test_arrival_departure_reconciliation`: Verified arrival + departure sum reconciliation.
  - `test_duplicate_benchmark_prevention`: Verified unique constraints on benchmarks.
  - `test_derived_vs_directly_reported_values`: Verified exclusion of derived remainders.
  - `test_separation_of_airspace_overflights`: Verified FIR boundary separation.
  - `test_unresolved_source_url_handling`: Verified quarantine of unverified primary URLs.
- **Overall Suite**: 153 passed out of 153 in 17.42 seconds.

### 8.2 Production Database Cryptographic Invariant
- **Target File**: `data/damascus_airport.db`
- **Hash Before Execution**: `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`
- **Hash After Execution**: `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`
- **Result**: Match confirmed. Zero bytes altered.

---

## 9. Conclusion & Next Steps

Version 2.11 successfully establishes a hardened, traceable, and period-aware macro aviation statistics layer. All 31 candidate benchmarks are staged in `data/macro_benchmarks_staging.db` with complete provenance and structural validation. 

Key deliverables generated:
- Staging Database: `data/macro_benchmarks_staging.db`
- CSV Export: `reports/v2_11_macro_statistics_report.csv`
- JSON Export: `reports/v2_11_macro_statistics_report.json`
- Comprehensive Audit Document: `docs/V2_11_MACRO_STATISTICS_AUDIT.md`
