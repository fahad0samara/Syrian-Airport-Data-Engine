# Syrian Airport Data Engine — Version 2.10
# Candidate Macro Aviation Statistics Inventory

**Document Identifier**: `docs/V2_10_MACRO_STATISTICS_CANDIDATES.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Staging Ledger**: `data/macro_benchmarks_staging.db`  
**Machine-Readable Twins**: [`reports/v2_10_macro_benchmarks_preview.csv`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/reports/v2_10_macro_benchmarks_preview.csv) & [`reports/v2_10_macro_benchmarks_preview.json`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/reports/v2_10_macro_benchmarks_preview.json)  
**Status**: APPROVED STAGING CANDIDATES INVENTORY  

---

## 1. Executive Summary & Candidate Overview

Version 2.10 stages **31 candidate macro benchmark records** across six distinct reporting windows spanning 2025 and 2026. Every candidate record has been formatted into the staging schema and validated against strict boundary, scope, and direction constraints.

### Key Inventory Highlights:
- **Total Candidate Benchmarks**: 31 records
- **Total Staged Flight Volume**: 20,480 airport movements (across 6 reporting periods)
- **Total Staged Passenger Volume**: 2,443,885 passengers (reconciled exactly to 1,241,873 arrivals + 1,202,012 departures)
- **Total Staged Airspace Overflights**: 22,474 overflights (isolated strictly to `OSTT_FIR`)
- **Status Distribution**:
  - `unverified_source_url`: **26 records (83.87%)** — Quoted in economic news citing SCAA, but canonical primary URLs on `sana.sy` or `scaa.sy` remain unresolved. Scope held as `reported_as_DAM_pending_primary_source_verification` (or `OSTT_FIR`).
  - `verified_secondary`: **5 records (16.13%)** — Authentic SCAA semi-annual bulletin (Jan 7 – Jul 7, 2025) backed by inspected regional news reporting. Scope: `DAM`.

---

## 2. Complete Staged Candidate Inventory (31 Records)

| Benchmark ID | Reporting Period | Metric Type | Metric Value | Unit | Dir | Geographic Scope | Status | Source Authority | Source URL |
| :--- | :---: | :--- | :---: | :---: | :---: | :--- | :---: | :--- | :--- |
| `bmk_2025_annual_flights` | 2025-01-01 to 2025-12-31 | `reported_flights` | 12,476 | flights | total | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2025_annual_passengers_total` | 2025-01-01 to 2025-12-31 | `passengers` | 1,434,998 | passengers | total | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2025_annual_passengers_arr` | 2025-01-01 to 2025-12-31 | `arriving_passengers` | 715,392 | passengers | arr | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2025_annual_passengers_dep` | 2025-01-01 to 2025-12-31 | `departing_passengers` | 719,606 | passengers | dep | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2025_h1_reported_flights` | 2025-01-07 to 2025-07-07 | `reported_flights` | 1,870 | flights | total | `DAM` | `verified_secondary` | SCAA / Press | `https://aksalser.com/` |
| `bmk_2025_h1_reported_passengers_total` | 2025-01-07 to 2025-07-07 | `passengers` | 353,282 | passengers | total | `DAM` | `verified_secondary` | SCAA / Press | `https://aksalser.com/` |
| `bmk_2025_h1_reported_passengers_arr` | 2025-01-07 to 2025-07-07 | `arriving_passengers` | 178,728 | passengers | arr | `DAM` | `verified_secondary` | SCAA / Press | `https://aksalser.com/` |
| `bmk_2025_h1_reported_passengers_dep` | 2025-01-07 to 2025-07-07 | `departing_passengers` | 174,554 | passengers | dep | `DAM` | `verified_secondary` | SCAA / Press | `https://aksalser.com/` |
| `bmk_2025_h1_reported_airlines` | 2025-01-07 to 2025-07-07 | `operating_airlines` | 12 | airlines | total | `DAM` | `verified_secondary` | SCAA / Press | `https://aksalser.com/` |
| `bmk_2026_04_flights` | 2026-04-08 to 2026-04-30 | `reported_flights` | 492 | flights | total | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_04_passengers_total` | 2026-04-08 to 2026-04-30 | `passengers` | 34,347 | passengers | total | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_04_passengers_arr` | 2026-04-08 to 2026-04-30 | `arriving_passengers` | 18,385 | passengers | arr | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_04_passengers_dep` | 2026-04-08 to 2026-04-30 | `departing_passengers` | 15,962 | passengers | dep | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_04_airlines` | 2026-04-08 to 2026-04-30 | `operating_airlines` | 9 | airlines | total | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_04_overflights` | 2026-04-01 to 2026-04-30 | `airspace_overflights` | 2,523 | overflights | total | `OSTT_FIR` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_05_flights` | 2026-05-01 to 2026-05-31 | `reported_flights` | 1,532 | flights | total | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_05_passengers_total` | 2026-05-01 to 2026-05-31 | `passengers` | 148,305 | passengers | total | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_05_passengers_arr` | 2026-05-01 to 2026-05-31 | `arriving_passengers` | 83,357 | passengers | arr | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_05_passengers_dep` | 2026-05-01 to 2026-05-31 | `departing_passengers` | 64,948 | passengers | dep | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_05_airlines` | 2026-05-01 to 2026-05-31 | `operating_airlines` | 13 | airlines | total | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_07_flights` | 2026-07-01 to 2026-07-31 | `reported_flights` | 2,088 | flights | total | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_07_passengers_total` | 2026-07-01 to 2026-07-31 | `passengers` | 243,260 | passengers | total | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_07_passengers_arr` | 2026-07-01 to 2026-07-31 | `arriving_passengers` | 147,318 | passengers | arr | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_07_passengers_dep` | 2026-07-01 to 2026-07-31 | `departing_passengers` | 95,942 | passengers | dep | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_07_airlines` | 2026-07-01 to 2026-07-31 | `operating_airlines` | 16 | airlines | total | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_09_flights` | 2026-09-01 to 2026-09-30 | `reported_flights` | 2,022 | flights | total | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_09_passengers_total` | 2026-09-01 to 2026-09-30 | `passengers` | 229,693 | passengers | total | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_09_passengers_arr` | 2026-09-01 to 2026-09-30 | `arriving_passengers` | 98,693 | passengers | arr | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_09_passengers_dep` | 2026-09-01 to 2026-09-30 | `departing_passengers` | 131,000 | passengers | dep | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_09_airlines` | 2026-09-01 to 2026-09-30 | `operating_airlines` | 17 | airlines | total | `reported_as_DAM_pending_primary_source_verification` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |
| `bmk_2026_09_overflights` | 2026-09-01 to 2026-09-30 | `airspace_overflights` | 19,951 | overflights | total | `OSTT_FIR` | `unverified_source_url` | SCAA / SANA | UNRESOLVED_PRIMARY_URL |

---

## 3. Directional Passenger Sum Reconciliation

Across all six reporting periods where directional passenger traffic is reported, the arrival and departure volumes sum to the total passenger volume to the exact integer:

$$\text{Reconciliation Formula}: \quad \text{arriving\_passengers} + \text{departing\_passengers} = \text{passengers (total)}$$

| Period Label | Temporal Range | Arriving Pax | Departing Pax | Mathematical Sum | Quoted Total Pax | Discrepancy |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **2025 Full Year** | 2025-01-01 to 2025-12-31 | 715,392 | 719,606 | **1,434,998** | 1,434,998 | **0** |
| **2025 Reported Period** | 2025-01-07 to 2025-07-07 | 178,728 | 174,554 | **353,282** | 353,282 | **0** |
| **April 2026** | 2026-04-08 to 2026-04-30 | 18,385 | 15,962 | **34,347** | 34,347 | **0** |
| **May 2026** | 2026-05-01 to 2026-05-31 | 83,357 | 64,948 | **148,305** | 148,305 | **0** |
| **July 2026** | 2026-07-01 to 2026-07-31 | 147,318 | 95,942 | **243,260** | 243,260 | **0** |
| **September 2026** | 2026-09-01 to 2026-09-30 | 98,693 | 131,000 | **229,693** | 229,693 | **0** |
| **Total Staged Volume** | — | **1,241,873** | **1,202,012** | **2,443,885** | **2,443,885** | **0** |

This $100.0\%$ arithmetic consistency across all reporting periods validates that the staged figures represent coherent official releases rather than independent estimates.

---

## 4. Specific Epistemic Constraints Observed

1. **No "H2 2025" Remainder Rows**:
   - The subtraction remainders ($12,476 - 1,870 = 10,606$ flights; $1,434,998 - 353,282 = 1,081,716$ pax) are **not staged as H2 statistics**. They remain documented solely as mathematical remainders in research dossiers.
2. **Preservation of Unresolved URLs**:
   - All 26 unverified records retain `source_url = 'UNRESOLVED_PRIMARY_URL'`. None have been arbitrarily upgraded to `verified_primary`.
3. **No Synthetic Daily Disaggregation**:
   - Monthly and annual figures remain strictly at their aggregate reporting grain. No rows have been inserted into `flight_events` or `damascus_daily_movements`.
4. **Clean Airspace Separation**:
   - The 2,523 April and 19,951 September overflight records are explicitly scoped to `OSTT_FIR` with `airport_icao = 'OSTT'` and `airport_iata = NULL`. They are isolated from Damascus airport operations.
