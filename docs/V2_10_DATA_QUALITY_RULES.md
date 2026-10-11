# Syrian Airport Data Engine — Version 2.10
# Data Quality & Integrity Rules for Macro Aviation Statistics

**Document Identifier**: `docs/V2_10_DATA_QUALITY_RULES.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Scope**: Ingestion, Staging, Validation, and Reconciliation of Macro Aviation Benchmarks  
**Status**: APPROVED DATA QUALITY SPECIFICATION  

---

## 1. Overview & Purpose

Macro aviation benchmarks represent aggregate statistical summaries (annual, semi-annual, monthly) published by civil aviation authorities, transport ministries, or international bodies. 

Because macro statistics are often reported at different temporal grains, with varying degrees of documentary substantiation, and mixed with airspace overflights, strict data quality rules are required to ensure they are handled safely and never corrupt micro-level flight event logs.

---

## 2. Core Quality Rules (QR-01 through QR-10)

### Rule QR-01: Temporal Period Boundary Integrity
- **Specification**: `reporting_period_start` and `reporting_period_end` must be valid ISO 8601 calendar dates (`YYYY-MM-DD`).
- **Constraint**: `reporting_period_start <= reporting_period_end`.
- **Enforcement**: Enforced by SQLite `CHECK` constraint and Python staging validator. Records with start date after end date are rejected immediately.

### Rule QR-02: Metric Value Non-Negativity & Integer Precision
- **Specification**: `metric_value` must be a non-negative number (`metric_value >= 0`).
- **Type Rule**: For `reported_flights`, `passengers`, `arriving_passengers`, `departing_passengers`, `airspace_overflights`, and `operating_airlines`, values must represent whole positive integers. Fractional values are permitted only for derived daily averages or rate metrics.

### Rule QR-03: Metric Type & Measurement Unit Consistency
- **Specification**: Only the six standardized metric types are permitted. Each metric type is bound to an exact unit:
  - `reported_flights` $\rightarrow$ `flights`
  - `passengers` $\rightarrow$ `passengers`
  - `arriving_passengers` $\rightarrow$ `passengers`
  - `departing_passengers` $\rightarrow$ `passengers`
  - `airspace_overflights` $\rightarrow$ `overflights`
  - `operating_airlines` $\rightarrow$ `airlines`
- **Enforcement**: Invalid combinations (e.g. `reported_flights` with unit `passengers`) are rejected.

### Rule QR-04: Directional Integrity & Passenger Volume Reconciliation
- **Specification**: 
  - `arriving_passengers` must have `direction = 'arrival'`.
  - `departing_passengers` must have `direction = 'departure'`.
  - `passengers` (total) must have `direction = 'total'`.
- **Reconciliation Invariant**: For any reporting period where both arriving and departing passenger volumes are provided by the same issuing source, their sum must exactly equal total passengers:
  $$\text{arriving\_passengers} + \text{departing\_passengers} = \text{passengers (total)}$$
  Any non-zero discrepancy flags the period for forensic audit.

### Rule QR-05: Airspace Overflight Scope Isolation
- **Specification**: Airspace overflights represent aircraft traversing sovereign upper airspace without landing or taking off.
- **Enforcement Invariant**:
  ```sql
  CONSTRAINT chk_overflight_scope CHECK (
      (metric_type = 'airspace_overflights' AND geographic_scope = 'OSTT_FIR') OR
      (metric_type != 'airspace_overflights' AND geographic_scope != 'OSTT_FIR')
  )
  ```
- **Rule**: Overflights must **never** be attributed to `DAM`, nor can airport movements be scoped to `OSTT_FIR`.

### Rule QR-06: Geographic Scope Precision & Qualification
- **Specification**: 
  - `DAM`: Used only when primary sovereign documentation or inspected secondary articles explicitly state Damascus International Airport (`OSDI`).
  - `reported_as_DAM_pending_primary_source_verification`: Assigned to all statistics quoted in news wire dispatches where the direct canonical URL on `sana.sy` or `scaa.sy` remains unverified.
  - `OSTT_FIR`: Upper Damascus Flight Information Region.
  - `DAM_ALP_LTK`: World Bank SEM composite multi-gateway aggregate.
  - `SYRIA_NATIONAL`: National civil aviation aggregates without airport breakdown.

### Rule QR-07: Anti-Promotion & Unresolved URL Quarantine
- **Specification**: When a statistic's source URL cannot be resolved to a persistent canonical permalink, it must be recorded as `UNRESOLVED_PRIMARY_URL`.
- **Anti-Promotion Rule**: A record with `source_url = 'UNRESOLVED_PRIMARY_URL'` can **never** be assigned `verification_status = 'verified_primary'`. It must remain quarantined as `unverified_source_url`.

### Rule QR-08: Deduplication & Natural Key Uniqueness
- **Specification**: Staging prevents duplicate benchmark entries via a compound unique constraint:
  ```sql
  CONSTRAINT uq_benchmark UNIQUE (
      airport_icao,
      reporting_period_start,
      reporting_period_end,
      metric_type,
      direction,
      geographic_scope,
      source_name
  )
  ```
- **Behavior**: Re-staging the same benchmark updates metadata without duplicating volume metrics.

### Rule QR-09: Strict Prohibition of Synthetic Daily Disaggregation
- **Specification**: Macro totals (annual, monthly) must remain at their reported aggregate temporal grain.
- **Strict Prohibition**: Under no circumstances may a monthly total (e.g. 2,022 flights in September) be divided by calendar days (e.g. $2,022 / 30 = 67.4$) to generate synthetic rows in `flight_events` or `damascus_daily_movements`. Micro movement tables require physical telemetry, sensor evidence, or verified daily logs.

### Rule QR-10: Derived Value Disclosure & Remainder Naming
- **Specification**: Any calculated figure must have `is_derived = 1` and specify the derivation formula in `calculation_method`.
- **Semi-Annual Remainder Invariant**: Subtraction remainders ($12,476 - 1,870 = 10,606$ flights; $1,434,998 - 353,282 = 1,081,716$ pax) must **not** be staged or labeled as "H2 2025" because the SCAA reported window is Jan 7 to Jul 7, leaving Jan 1–6 and Jul 8–Dec 31 unaccounted for.

---

## 3. Data Quality Validation Matrix

| Rule ID | Validation Target | Enforcement Layer | Test Case in Test Suite |
| :--- | :--- | :--- | :--- |
| **QR-01** | Period Boundaries (`start <= end`) | DB CHECK & Python Validator | `test_reporting_period_boundaries` |
| **QR-02** | Metric Value Non-Negativity | DB CHECK & Python Validator | `test_reporting_period_boundaries` |
| **QR-03** | Metric Types & Units | DB CHECK & Python Validator | `test_airport_scope_constraints` |
| **QR-04** | Arrival + Departure = Total Pax | Python Reconciler | `test_arrival_departure_reconciliation` |
| **QR-05** | Airspace Overflight Scope Isolation | DB CHECK & Python Validator | `test_separation_of_airspace_overflights` |
| **QR-06** | Scope Precision & Qualification | DB CHECK & Python Validator | `test_airport_scope_constraints` |
| **QR-07** | Anti-Promotion (Unresolved URLs) | Python Validator | `test_unresolved_source_url_handling` |
| **QR-08** | Duplicate Benchmark Prevention | DB UNIQUE Constraint | `test_duplicate_benchmark_prevention` |
| **QR-09** | No Micro Flight Synthesis | Architectural Isolation | `test_production_database_untouched` |
| **QR-10** | Derived Value Flagging & Remainder Naming | Staging Filter & Schema Flag | `test_derived_vs_directly_reported_values` |

---

## 4. Summary & Compliance Certification

All 31 candidate benchmarks staged in Version 2.10 pass every quality rule without exception. The production database remains 100% compliant with zero modifications.
