# Syrian Airport Data Engine — Version 2.13.1
# Historical Coverage Claims Validation & Database Reconciliation

**Document Identifier**: `docs/V2_13_1_COVERAGE_CORRECTIONS.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Target Airspace**: Damascus Flight Information Region (`OSTT_FIR`)  
**Scope**: Factual Corrections to V2.13 Coverage Claims, Separation of Dimensions, and Production Database Cross-Tabulation  
**Machine-Readable Twin**: `reports/v2_13_1_coverage_gaps.csv`  
**Status**: APPROVED VALIDATION REGISTER & DATABASE RECONCILIATION  
**Production Integrity Invariant**: `data/damascus_airport.db` SHA-256 verified identical (`c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`).

---

## 1. Executive Summary & Audit Mandate

Version 2.13.1 executes an exhaustive audit of the historical coverage claims presented in Version 2.13. In V2.13, several critical evidentiary conflations and arithmetic misattributions occurred:
1. Aggregate macro statistics were conflated with individual flight records in coverage tables.
2. The 2025 annual total of 12,476 flights was erroneously assigned to the second-half interval `2025-07-08` through `2025-12-31`.
3. The arithmetic remainder from subtraction (`12,476 - 1,870 = 10,606`) was represented as though it were an independently reported "H2" statistic.
4. April 2026 airport statistics were mapped to April 8–30 despite the primary Arabic excerpt quoting "في نيسان 2026" without explicit day numbers.
5. September 2026 monthly statistics were assigned to `2026-09-01` to `2026-09-29` as though they described only that pre-snapshot interval, whereas the official bulletin explicitly reports the full calendar month.
6. The 578 World Bank Syria Economic Monitor (SEM) rows were described as flight movements, when in reality they represent 289 calendar dates multiplied by two movement directions (arrivals and departures) for a multi-airport composite gateway (`DAM_ALP_LTK`).
7. Total database row counts (`1,830` flight events, `207` actual movements, `1,623` scheduled flights) were reported as Damascus figures, when in fact they represent the aggregate across three separate Syrian airports (`DAM`, `ALP`, `DEZ`).

This document provides the authoritative, mathematically reconciled correction across all dimensions.

---

## 2. Dimension Separation Framework

To ensure that different units of measure and evidentiary natures are never blended into identical numerical columns, all historical analysis is partitioned into three distinct dimensions:

```
+----------------------------------------------------------------------------------------------------+
| DIMENSION A: DAILY CALENDAR COVERAGE (Tracking Days)                                               |
| - Total Calendar Days in Period                                                                    |
| - Days with Verified Physical Movement Evidence (Touchdown/takeoff confirmed by radar sensors)     |
| - Days with Commercial Schedule-Only Evidence (Timetables/FIDS without physical sensor lock)       |
| - Days with Unverified Observations (Observations lacking terminal approach fixes)                 |
| - Days with No Known DAM-Specific Evidence (Complete data vacuum for Damascus)                     |
| - Days with Only Aggregate Composite Data (Multi-airport gateway data e.g. DAM_ALP_LTK)            |
+----------------------------------------------------------------------------------------------------+
| DIMENSION B: FLIGHT-LEVEL DATABASE RECORDS (Physical Rows in flight_events)                        |
| - Physical Movements (Transponder/radar-confirmed runway operations)                                |
| - Scheduled Services (Published commercial flights without confirmed runway sensors)              |
| - Marketing Codeshares (Duplicate commercial flight listings for same physical aircraft leg)       |
| - Unverified Movements (Telemetry observations failing qualification criteria)                     |
| - Segregated by Airport ID (DAM vs. ALP vs. DEZ) and Source Provider                               |
+----------------------------------------------------------------------------------------------------+
| DIMENSION C: MACRO AGGREGATE STATISTICS (Staged Benchmark Layer)                                   |
| - Reported Flight Volume (Total flights across all operational categories)                         |
| - Reported Passenger Throughput (Total, Arriving, Departing)                                       |
| - Operating Airline Counts (Direct reported numerical carrier count)                               |
| - National Airspace Transit Overflights (Damascus FIR / OSTT_FIR transit traffic)                   |
| - Preserving Exact Reporting Period Boundaries and Geographic Scope                                |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Production Database Cross-Tabulation & Reconciliation

A read-only forensic SQL cross-tabulation was executed against `data/damascus_airport.db`. The results definitively resolve the V2.13 claim of "1,830 flight events, 207 actual movements, and 1,623 scheduled flights":

### 3.1 Breakdown by Airport Identifier (`airport_id`)
```sql
SELECT airport_id, COUNT(*) FROM flight_events GROUP BY airport_id;
```
| Airport Code | Airport Name | Total Flight Events | Percentage of Total |
|---|---|---|---|
| **DAM** | Damascus International Airport | **1,563** | 85.41% |
| **ALP** | Aleppo International Airport | **261** | 14.26% |
| **DEZ** | Deir ez-Zor Airport | **6** | 0.33% |
| **TOTAL** | All Syrian Aerodromes | **1,830** | **100.00%** |

*Correction*: The 1,830 flight events are **not** all Damascus flights. **Damascus International Airport accounts for exactly 1,563 flight events.**

---

### 3.2 Breakdown by Record Nature (`record_nature`)
```sql
SELECT airport_id, record_nature, COUNT(*) 
FROM flight_events 
GROUP BY airport_id, record_nature;
```
| Airport | `record_nature` | Row Count | Operational Definition |
|---|---|---|---|
| **DAM** | `physical_movement` | **98** | Transponder-confirmed touchdown or takeoff at OSDI |
| **DAM** | `scheduled_service` | **1,428** | Published airline schedule or FIDS timetable entry |
| **DAM** | `marketing_codeshare` | **34** | Commercial codeshare flight number mapped to operating flight |
| **DAM** | `unverified_movement` | **3** | Incomplete telemetry failing qualification thresholds |
| *DAM Subtotal* | | *1,563* | |
| **ALP** | `physical_movement` | **32** | Transponder-confirmed runway operation at OSAP |
| **ALP** | `scheduled_service` | **229** | Scheduled flight at Aleppo |
| *ALP Subtotal* | | *261* | |
| **DEZ** | `physical_movement` | **1** | Transponder-confirmed runway operation at OSDZ |
| **DEZ** | `scheduled_service` | **5** | Scheduled flight at Deir ez-Zor |
| *DEZ Subtotal* | | *6* | |
| **GRAND TOTAL**| | **1,830** | |

---

### 3.3 Movement Timestamp Reconciliation: "Actual Movement" Audit
The phrase "actual movement" was used imprecisely in V2.13 to denote any row where an actual timestamp field was not null. A forensic audit reveals:

```sql
SELECT 
    airport_id,
    COUNT(*) as total_rows,
    SUM(CASE WHEN actual_dep_time IS NOT NULL OR actual_arr_time IS NOT NULL THEN 1 ELSE 0 END) as rows_with_actual_ts,
    SUM(CASE WHEN actual_dep_time IS NULL AND actual_arr_time IS NULL THEN 1 ELSE 0 END) as rows_scheduled_only
FROM flight_events
GROUP BY airport_id;
```
| Airport | Total Rows | Rows with Actual Timestamp | Rows Scheduled Only | `physical_movement` (Strict) |
|---|---|---|---|---|
| **DAM** | 1,563 | **163** | **1,400** | **98** |
| **ALP** | 261 | **41** | **220** | **32** |
| **DEZ** | 6 | **3** | **3** | **1** |
| **TOTAL** | **1,830** | **207** | **1,623** | **131** |

#### Evidentiary Analysis of the "207" Figure:
1. **Multi-Airport Total**: The number 207 is the sum of rows with actual timestamps across **all three airports combined** (`163 DAM + 41 ALP + 3 DEZ = 207`).
2. **Damascus-Only Count**: For Damascus specifically, exactly **163 rows** possess an actual departure or arrival timestamp.
3. **Timestamp Presence vs. Physical Movement**: Of the 163 Damascus rows with an actual timestamp:
   - **98** rows represent validated `physical_movement` events confirmed by ground radar/transponder sensors.
   - **31** rows represent `marketing_codeshare` records that inherit the actual timestamp of their operating flight.
   - **31** rows represent `scheduled_service` records where a single leg or off-block time was recorded but did not meet full physical movement qualification.
   - **3** rows represent `unverified_movement` records where signal noise or unconfirmed radar hits exist.
4. **Scheduled-Only Count**: The number 1,623 is the sum of scheduled-only rows across all airports (`1,400 DAM + 220 ALP + 3 DEZ = 1,623`). For Damascus alone, exactly **1,400 rows** are scheduled only.

---

### 3.4 Temporal Concentration of Physical Movements
Physical movements in the entire production database are restricted to **two calendar days**:
- **2026-10-09**: 51 physical movements for DAM, 14 for ALP.
- **2026-10-10**: 47 physical movements for DAM, 18 for ALP, 1 for DEZ.
- **All other calendar days in `flight_events` (2026-09-30 to 2026-10-08 and 2026-10-11 to 2026-10-31)** contain **zero verified physical movements**.

In the coverage matrix (`historical_coverage_matrix`):
- `verified_coverage`: Exactly **2 calendar days** for DAM (`2026-10-09` and `2026-10-10`).
- `commercial_schedule_only`: **9 calendar days** (`2026-09-30` to `2026-10-08`).
- `future_schedule`: **21 calendar days** (`2026-10-11` to `2026-10-31`).
- `unverified_data_gap`: **1,003 calendar days** (`2024-01-01` to `2026-09-29`).

---

### 3.5 Cross-Tabulation: Source Provider by Airport and Record Nature
```sql
SELECT source, record_nature, COUNT(*) 
FROM flight_events 
WHERE airport_id = 'DAM' 
GROUP BY source, record_nature;
```
| Source Label | `record_nature` | Count | Description |
|---|---|---|---|
| `damairport_official` | `scheduled_service` | 1,297 | Live FIDS timetable ingestion from official airport portal |
| `damairport_official+aviationstack+flightradar24` | `physical_movement` | 71 | Reconciled ground movement confirmed across all 3 providers |
| `damairport_official+flightradar24` | `scheduled_service` | 43 | Commercial flight with FR24 estimated progress |
| `aviationstack+flightradar24` | `physical_movement` | 23 | Radar-confirmed physical movement |
| `flightradar24` | `scheduled_service` | 37 | Scheduled commercial flight from FR24 feed |
| `aviationstack` | `marketing_codeshare` | 34 | Marketing codeshare flight number from AviationStack |
| `aviationstack+flightradar24` | `scheduled_service` | 19 | Dual-source scheduled flight |
| `damairport_official+aviationstack+flightradar24` | `scheduled_service` | 16 | Triple-source scheduled flight |
| `aviationstack` | `scheduled_service` | 16 | Commercial schedule from AviationStack |
| `damairport_official+flightradar24` | `physical_movement` | 4 | Ground radar confirmed arrival/departure |
| `damairport_official+aviationstack` | `unverified_movement` | 2 | Conflicting timestamp delta (>120 min) |
| `aviationstack` | `unverified_movement` | 1 | Unconfirmed commercial status |
| **TOTAL DAM** | | **1,563** | |

---

## 4. Mandatory Coverage Claims Corrections

### 4.1 Correction 1: 2025 Annual Total vs. H2 Remainder
- **V2.13 Claim**: The period `2025-07-08` through `2025-12-31` was assigned 12,476 flights (or an aggregate remainder of 10,606 flights) as an "aggregate macro" statistic for H2.
- **Correction**: 
  * The figure **12,476 flights** is an **annual statistic** for the entire calendar year `2025-01-01` through `2025-12-31`. It must never be assigned as the statistic of the interval July 8 to December 31.
  * The figure **1,870 flights** is an official milestone statistic reported by SCAA for the exact period **2025-01-07 through 2025-07-07**.
  * The subtraction remainder (`12,476 - 1,870 = 10,606 flights`) is an **analytical calculation**, not an independently published sovereign statistic. Furthermore, the remainder covers not only late 2025, but also the omitted dates from `2025-01-01` to `2025-01-06`.
  * **Rule**: The annual total remains stored strictly with period `2025-01-01` to `2025-12-31`. The remainder is explicitly labeled `annual_minus_reported_period_remainder` and must never be represented as an independent H2 benchmark.

### 4.2 Correction 2: April 2026 Reporting Boundary
- **V2.13 Claim**: April 2026 airport traffic was assigned to the period `2026-04-08` through `2026-04-30` based on the operational reopening date.
- **Correction**: 
  * The secondary reporting quoting SCAA states "في نيسان 2026" (in April 2026) without citing explicit day numbers.
  * In accordance with V2.12.1 and V2.12.2 rules, when an official source uses general month terminology, the reporting boundary must be formally classified as `unresolved_reopening_window`.
  * The 2,523 overflights reported in the same bulletin strictly represent the Damascus Flight Information Region (`OSTT_FIR`), not runway movements at Damascus International Airport.

### 4.3 Correction 3: September 2026 Full-Month Scope
- **V2.13 Claim**: September 2026 statistics (2,022 flights, 229,693 passengers) were assigned to `2026-09-01` through `2026-09-29`.
- **Correction**: 
  * The SCAA monthly statistical bulletin describes the **full calendar month** of September 2026 (`2026-09-01` to `2026-09-30`).
  * Truncating the reporting period to September 29 was an artifact of the database's live ingestion start date (September 30). The aggregate benchmark must retain its true monthly scope (`2026-09-01` to `2026-09-30`).
  * Overflights (19,951) describe `OSTT_FIR` airspace transits, not airport traffic.

### 4.4 Correction 4: World Bank SEM Daily Row Interpretation
- **V2.13 Claim**: Described the 578 rows in `historical_daily_movements_2024` as "aggregate airport statistics" or individual movements.
- **Correction**: 
  * The 578 rows represent **289 calendar dates** (`2024-01-01` to `2024-10-15`) multiplied by **two movement directions** (`arrival` and `departure`).
  * The geographic scope is strictly `DAM_ALP_LTK` (a composite gateway combining Damascus, Aleppo, and Latakia).
  * The data contains zero Damascus-specific flight counts. Applying static percentage splits (e.g. 75%) is prohibited.
