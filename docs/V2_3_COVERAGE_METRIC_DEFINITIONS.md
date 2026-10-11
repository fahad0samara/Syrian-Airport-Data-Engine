# Syrian Airport Data Engine — Version 2.3
# Coverage Metric Definitions & Mathematical Semantics

**Document Identifier**: `docs/V2_3_COVERAGE_METRIC_DEFINITIONS.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Audit Date**: 2026-10-11  
**Target Standard**: Rigorous Epistemic Grounding for Aviation Time-Series Coverage  
**Status**: APPROVED SPECIFICATION  

---

## 1. Executive Summary & Epistemic Principles

Historical aviation tracking in conflict-affected, low-sensor-density aerodromes like Damascus International Airport (`DAM` / `OSDI`) presents severe semantic pitfalls if telemetry voids are naively conflated with airport inactivity. 

To eliminate data corruption, historical hallucinations, and invalid statistical claims, Version 2.3 establishes the following **immutable epistemic principles**:

1. **Absence of Evidence is NOT Evidence of Absence**: An API returning `[]` (empty response) or a receiver network capturing zero transponder packets on a given date indicates solely that the querying engine observed no records. It does **not** prove that zero flights occurred.
2. **Missing Historical Data Must Remain Unknown**: Any calendar date lacking positive physical sensor observations or verified ground truth must be classified as an `unverified_data_gap`. It must never be recorded as zero operations.
3. **Partial Observation ≠ Completeness**: A calendar date containing a single verified aircraft landing confirms that the airport was physically active on that day; it does **not** prove that only one flight landed, nor does it establish that the day was fully observed.
4. **NOTAM Scope Boundary**: An official Notice to Airmen (NOTAM) or aeronautical authority closure notice proves zero civil operations **only** when its temporal window spans the full operational day (00:00 to 24:00 local time) and its legal/operational scope applies universally to all civil traffic. Partial-day closures, runway maintenance windows, or VIP curfew exceptions do not establish zero operations for the entire date.
5. **No Completeness Without Denominators**: "Coverage completeness" (%) cannot be calculated for individual flight movements unless an authoritative, independent census total (such as an audited state air traffic control log) exists for the exact same aerodrome, date, and movement definition.

---

## 2. Standardized Coverage Metrics & Mathematical Formulations

Let $\mathcal{D} = \{d_1, d_2, \dots, d_N\}$ denote the set of all calendar dates within an evaluation window $[T_{\text{start}}, T_{\text{end}}]$, where $N = |\mathcal{D}|$ is the total number of evaluated calendar days.

All calendar dates are indexed in Damascus local operational time (`Asia/Damascus`, UTC+3).

---

### Metric 1: Verified Days Rate (`verified_days_rate`)

* **Semantic Definition**: The proportion of calendar days in the evaluation period that possess **at least one** verified physical aircraft movement (arrival or departure) confirmed by active, independent provider telemetry.
* **Mathematical Formula**:
  $$\text{verified\_days\_rate} = \frac{|\{d \in \mathcal{D} \mid M_{\text{verified}}(d) \ge 1\}|}{N}$$
* **Numerator**: Total count of unique calendar dates having $\ge 1$ active, non-retracted `physical_movement` event in `flight_events`.
* **Denominator**: $N = |\mathcal{D}|$ (Total number of evaluated calendar days in the query window).
* **Domain & Range**: Real number in $[0.0, 1.0]$ (or $0.0\%$ to $100.0\%$).
* **Critical Rule**: A day contributing to the numerator indicates positive operational proof; it does **not** assert that all operations on that day were captured.

---

### Metric 2: Verified Movements Count (`verified_movements_count`)

* **Semantic Definition**: The exact integer sum of all individual physical aircraft movements (arrivals and departures) confirmed by active, non-retracted physical sensor evidence at `DAM` / `OSDI`.
* **Mathematical Formula**:
  $$\text{verified\_movements\_count} = \sum_{d \in \mathcal{D}} M_{\text{verified}}(d)$$
  where $M_{\text{verified}}(d)$ is the count of events where:
  - `event_type IN ('arrival', 'departure')`
  - `classification = 'physical_movement'`
  - `status = 'active'`
  - `retracted = 0` (or `retraction_status = 'active'`)
* **Numerator / Value**: Non-negative integer.
* **Denominator**: **None**. This is an absolute event tally, not a ratio or percentage.
* **Critical Rule**: Under no circumstances should `verified_movements_count` be divided by scheduled flights to calculate "completeness", because non-scheduled flights (governmental, humanitarian, military, cargo charters) are unrepresented in commercial schedules.

---

### Metric 3: Source Checked No Records Days (`source_checked_no_records_days`)

* **Semantic Definition**: The number of calendar dates on which an automated ingestion adapter queried a provider endpoint, received a valid and successful `HTTP 200 OK` response containing zero flight records, but where **no independent physical sensor or official closure evidence exists** to confirm airport closure.
* **Mathematical Formula**:
  $$\text{source\_checked\_no\_records\_days} = |\{d \in \mathcal{D} \mid \text{QuerySuccess}(d) \land \text{RecordCount}(d) = 0 \land \neg \text{ConfirmedClosed}(d)\}|$$
* **Numerator**: Count of unique calendar dates returning empty provider payloads under normal API operation.
* **Denominator**: $N = |\mathcal{D}|$.
* **Classification State**: Calendar dates in this category remain classified as `unverified_data_gap`.
* **Critical Rule**: This metric measures **adapter query execution**, not aerodrome reality. It must never be reported as "zero flight days".

---

### Metric 4: Confirmed Closure Days (`confirmed_closure_days`)

* **Semantic Definition**: The number of calendar days on which Damascus International Airport was officially and completely closed to civil aviation pursuant to an authoritative statutory notice (NOTAM, AIP supplement, or Ministry of Transport executive decree).
* **Mathematical Formula**:
  $$\text{confirmed\_closure\_days} = |\{d \in \mathcal{D} \mid \text{NOTAM\_Closure}(d) = \text{True} \land \text{ClosureDuration}(d) = 24.0\text{h}\}|$$
* **Numerator**: Count of calendar dates where verified aeronautical documentation confirms full 24-hour aerodrome closure (e.g., runway reconstruction, wartime airspace denial, security shutdowns).
* **Denominator**: $N = |\mathcal{D}|$.
* **Evidence Requirement**: Must reference a specific, verified NOTAM series number (e.g., `A0124/24 NOTAMN OSDI AIRPORT CLOSED TO ALL CIVIL TRAFFIC`) with explicit effective from/to UTC timestamps.
* **Critical Rule**: Partial-day closures (e.g. runway closed 02:00–06:00 UTC for maintenance) do **not** qualify as confirmed closure days; operations during open hours remain subject to standard verification.

---

### Metric 5: Confirmed Zero Operations Days (`confirmed_zero_operations_days`)

* **Semantic Definition**: The subset of confirmed closure days on which both statutory closure evidence AND multi-provider sensor checks independently confirm that zero physical aircraft movements occurred.
* **Mathematical Formula**:
  $$\text{confirmed\_zero\_operations\_days} = |\{d \in \mathcal{D} \mid d \in \text{ConfirmedClosureDays} \land M_{\text{verified}}(d) = 0 \land \text{EnRouteSensorsChecked}(d) = \text{True}\}|$$
* **Numerator**: Count of calendar dates where both legal closure and empirical radar/ADS-B monitoring corroborate complete cessation of flight activity.
* **Denominator**: $N = |\mathcal{D}|$.
* **Status in Engine**: `confirmed_zero_operations`.
* **Critical Rule**: This is the **only** classification state permitted to record zero movements as ground truth.

---

### Metric 6: Unverified Data Gap Days (`unverified_data_gap_days`)

* **Semantic Definition**: The number of calendar dates within the evaluation period for which the engine lacks both positive verified physical telemetry and verified closure documentation.
* **Mathematical Formula**:
  $$\text{unverified\_data\_gap\_days} = N - \left( |\{d \in \mathcal{D} \mid M_{\text{verified}}(d) \ge 1\}| + \text{confirmed\_zero\_operations\_days} \right)$$
* **Numerator**: Count of calendar dates with unknown ground truth.
* **Denominator**: $N = |\mathcal{D}|$.
* **Rate**:
  $$\text{gap\_rate} = \frac{\text{unverified\_data\_gap\_days}}{N}$$
* **Critical Rule**: In all analytical exports, dashboards, and reporting tables, these days must be explicitly represented as `NULL` or `"unverified_data_gap"`, NEVER as `0`.

---

### Metric 7: Commercial Schedule Days (`commercial_schedule_days`)

* **Semantic Definition**: The number of calendar dates on which published commercial airline timetable schedules (e.g., Syrian Air, Cham Wings scheduled flights) exist in the database for `DAM` / `OSDI`.
* **Mathematical Formula**:
  $$\text{commercial\_schedule_days} = |\{d \in \mathcal{D} \mid S_{\text{commercial}}(d) \ge 1\}|$$
  where $S_{\text{commercial}}(d)$ is the count of events where `classification = 'scheduled_commercial'`.
* **Numerator**: Count of calendar dates with scheduled timetable data.
* **Denominator**: $N = |\mathcal{D}|$.
* **Critical Rule**: Scheduled commercial flights represent forward intentions, not historical movements. A scheduled flight that is neither confirmed by physical telemetry nor confirmed cancelled must remain `scheduled_commercial` and cannot be counted as an operation.

---

### Metric 8: Future Schedule Days (`future_schedule_days`)

* **Semantic Definition**: The subset of commercial schedule days that fall strictly after the current operational timestamp ($d > d_{\text{current}}$).
* **Mathematical Formula**:
  $$\text{future\_schedule\_days} = |\{d \in \mathcal{D} \mid d > d_{\text{current}} \land S_{\text{commercial}}(d) \ge 1\}|$$
* **Numerator**: Count of calendar dates containing forward timetable records.
* **Denominator**: Total future dates evaluated.
* **Critical Rule**: Future schedule days must be segregated from historical coverage audits. They cannot be included in historical gap or verification ratios.

---

## 3. Summary Semantic Reference Matrix

| Metric Name | Mathematical Type | Denominator | Allows Zero Inferences? | Permitted Database Status |
| :--- | :--- | :--- | :--- | :--- |
| `verified_days_rate` | Ratio $[0.0, 1.0]$ | Total calendar days in window ($N$) | No | `observed` / `verified_coverage` |
| `verified_movements_count` | Absolute Integer | None (Count) | No (Positive sum) | `physical_movement` |
| `source_checked_no_records_days`| Integer Count | Total calendar days in window ($N$) | **NO** | `unverified_data_gap` |
| `confirmed_closure_days` | Integer Count | Total calendar days in window ($N$) | Only if 24h NOTAM | `confirmed_closure` |
| `confirmed_zero_operations_days`| Integer Count | Total calendar days in window ($N$) | **YES** (Dual-proven) | `confirmed_zero_operations` |
| `unverified_data_gap_days` | Integer Count | Total calendar days in window ($N$) | **NO** (Must be unknown) | `unverified_data_gap` |
| `commercial_schedule_days` | Integer Count | Total calendar days in window ($N$) | No | `scheduled_commercial` |
| `future_schedule_days` | Integer Count | Total future days evaluated | No | `future_schedule` |

---

## 4. Implementation Invariants for Syrian Airport Data Engine

1. **Database Schema Enforcement**:
   - `coverage_status` in any daily summary table must strictly adhere to the enum:
     `('observed', 'unverified_data_gap', 'confirmed_closure', 'confirmed_zero_operations')`.
   - `total_recorded_operations` must be set to `0` **only** when `coverage_status = 'confirmed_zero_operations'`.
   - When `coverage_status = 'unverified_data_gap'`, `total_recorded_operations` must be `0` with explicit status note *"Unverified data gap in source series: 0 recorded operations across all status categories"*, or stored as `NULL` in analytical views to prevent aggregate summing errors.

2. **Aggregation Safety**:
   - SQL queries calculating historical operational totals must explicitly filter:
     ```sql
     WHERE classification = 'physical_movement' 
       AND status = 'active'
     ```
   - Under no circumstances should `SUM(total_recorded_operations)` from aggregate tables (such as `historical_daily_movements_2024`) be combined with `flight_events` without de-duplicating by date, airport scope, and movement classification.
