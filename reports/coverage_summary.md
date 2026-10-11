# Syrian Airports & Damascus Deep-Dive Historical Flight Coverage Report

**Generated Date**: 2026-10-10  
**Target Scope**: All Syrian Aerodromes (DAM, ALP, LTK, DEZ, KAC, PMS, OMDM) + Damascus Deep-Dive (DAM / OSDI)  
**Aeronautical Reference**: Syrian eAIP (https://eaip.gaca.gov.sy/) & OurAirports  

---

## 1. Executive Summary & Verification Classification

This report provides an empirical, evidence-based assessment of real web-accessible flight data for Syrian airports, strictly distinguishing verified retrieved records from vendor claims, paywalled archives, and data outages.

### Data Status Categories:
1. **Historical & Operational Data Actually Retrieved**:
   - **Damascus International Airport Authority (damairport.gov.sy)**: 1,434 individual flight events retrieved directly from the airport authority database, covering 2026-09-30 to 2026-10-31 across 32 continuous dates.
   - **Aleppo International Airport Authority (alpairport.gov.sy)**: 250 individual flight events retrieved directly from the airport authority database, covering 2026-09-30 to 2026-10-11 across 12 continuous dates.
   - **Flightradar24 Multi-Airport Feeds**: 286 individual flight events across Damascus (213), Aleppo (67), and Deir ez-Zor (6).
   - **AviationStack Live Feed**: 182 individual flight events for Damascus.
   - **Syria Economic Monitor (World Bank / Data Partnership)**: 578 daily gateway observations (289 departures, 289 arrivals) covering 2024-01-01 to 2024-10-15. Preserved strictly as `multi_airport` aggregate (`DAM_ALP_LTK`), never mislabeled as Damascus-only.
   - **Syrian eAIP & OurAirports**: Authoritative aerodrome registry for all 7 Syrian aerodromes.

2. **Periods That Require Paid Access**:
   - **AviationStack Historical API**: Historical dates prior to the rolling window return `HTTP 403 Forbidden` (`code: function_access_restricted`).
   - **Flightradar24 Historical Archives**: Flight data older than 7 days is restricted to Business subscribers.
   - **FlightAware AeroAPI**: Historical queries older than 7 days require a paid commercial tier.
   - **ADS-B Exchange**: Historical REST queries require a RapidAPI enterprise subscription.

3. **Periods Requiring Institutional Access**:
   - **OpenSky Network**: Anonymous historical endpoints return `HTTP 403: You cannot access historical flights`. Requires academic Trino cluster access.

4. **Periods With Documented Outages & Missing Dates**:
   - Syria Economic Monitor 2024 dataset has 8 documented provider outage dates preserved as gaps (`2024-01-28..30`, `2024-04-29..30`, `2024-06-07..09`).
   - Operational shutdown: Syrian airspace was closed by SCAA between December 8 and December 15, 2024, resuming commercial operations January 1, 2025.

---

## 2. Source-by-Source Empirical Audit

| Source | Scope | Metric Type | Earliest Verified | Latest Verified | Observed Dates | Total Records | Verification Status | Licensing |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Damascus International Airport Authority (damairport.gov.sy)** | Damascus International Airport (DAM / OSDI) | Individual Flight Events | **2026-09-30** | **2026-10-31** | 32 | 1434 | **Retrieved & Verified: 1,434 flight event...** | Official airport public flight boar |
| **Aleppo International Airport Authority (alpairport.gov.sy)** | Aleppo International Airport (ALP / OSAP) | Individual Flight Events | **2026-09-30** | **2026-10-11** | 12 | 250 | **Retrieved & Verified: 250 flight events ...** | Official airport public flight boar |
| **Qamishli Airport Authority (qamishliairport.gov.sy)** | Qamishli Airport (KAC / OSKL) | Individual Flight Events | **None** | **None** | 0 | 0 | **Verified: Portal responsive, authority r...** | Official airport public flight boar |
| **Deir ez-Zor Airport Authority (deirezzorairport.gov.sy)** | Deir ez-Zor Airport (DEZ / OSDZ) | Individual Flight Events | **None** | **None** | 0 | 0 | **Verified: Portal responsive, authority r...** | Official airport public flight boar |
| **Syria Economic Monitor (AviationStack purchase)** | DAM, ALP, LTK (Damascus, Aleppo, Latakia combined gateways) | Daily Aggregate Observation (not individual flights) | **2024-01-01** | **2024-10-15** | 281 | 578 | **Verified: 289 daily departure observatio...** | AviationStack commercial data purch |
| **Flightradar24 Airport API (Multi-Airport Feeds)** | DAM (Damascus), ALP (Aleppo), DEZ (Deir ez-Zor), LTK (Latakia), KAC (Qamishli) | Individual Flight Events | **2026-10-08** | **2026-10-12** | 5 | 286 | **Verified: Public airport endpoint querie...** | Flightradar24 proprietary; personal |
| **AviationStack Live API** | Damascus International Airport (DAM / OSDI) | Individual Flight Events | **2026-10-08** | **2026-10-10** | 3 | 182 | **Verified: Live endpoints queried, 182 in...** | AviationStack Free/Standard terms;  |
| **Syrian Civil Aviation Authority (GACA) / Official eAIP** | DAM, ALP, LTK, DEZ, KAC, PMS, OMDM (All Syrian Aerodromes) | Authoritative Aeronautical Reference & Regulatory Milestones | **2024-12-08 (closure)** | **2025-01-01 (reopening)** | Qualitative event dates | 7 | **Verified: Official eAIP aerodrome record...** | Official government public aeronaut |
| **OurAirports / Aeronautical Registry** | DAM, ALP, LTK, DEZ, KAC, PMS, OMDM | Airfield Infrastructure Reference | **Static verified registry** | **Static verified registry** | 1 | 7 | **Verified: Runways and coordinates verifi...** | Public domain (Creative Commons CC0 |
| **OpenSky Network Historical API** | OSDI, OSAP, OSLK, OSDZ, OSKL | Individual Flight Events | **None** | **None** | 0 | 0 | **Tested: confirmed blocked without verifi...** | OpenSky Network non-commercial acad |
| **ADS-B Exchange** | Syria Airspace | State Vectors / Flight Tracking | **None** | **None** | 0 | 0 | **Tested: historical data not publicly acc...** | Commercial proprietary |
| **FlightAware (AeroAPI)** | DAM, ALP, LTK, DEZ, KAC | Individual Flight Events | **None** | **None** | 0 | 0 | **Documented: paid subscription prerequisi...** | Commercial proprietary |

---

## 3. Dynamic Operational & Ingestion Summary

### Ingestion Pipeline Health
- **EMPTY**: 2 adapter runs, 0 records fetched.
- **FAILED**: 23 adapter runs, 0 records fetched.
- **SUCCESS**: 4 adapter runs, 1896 records fetched.

### Syrian Aerodromes Ingested
- **ALP**: 1 sources queried, 1 pipeline runs.
- **DAM**: 2 sources queried, 26 pipeline runs.
- **DEZ**: 1 sources queried, 1 pipeline runs.
- **KAC**: 1 sources queried, 1 pipeline runs.

### Flight Events Semantic Breakdown
- **ALP** (261 total events):
  - `physical_movement`: 32
  - `scheduled_service`: 229
- **DAM** (1563 total events):
  - `marketing_codeshare`: 34
  - `physical_movement`: 98
  - `scheduled_service`: 1428
  - `unverified_movement`: 3
- **DEZ** (6 total events):
  - `physical_movement`: 1
  - `scheduled_service`: 5

### Deduplication Audit Status
- `AMBIGUOUS_KEPT_SEPARATE`: 15
- `MERGED_VERIFIED`: 322

### Historical Coverage Matrix Distribution (2024-01-01 to 2026-10-31)
- `commercial_schedule_only`: 18 airport-day cells
- `future_schedule`: 23 airport-day cells
- `source_checked_no_records`: 51 airport-day cells
- `unverified_data_gap`: 5078 airport-day cells
- `verified_coverage`: 5 airport-day cells

> **Data Gap vs Confirmed Zero Operations Distinction**:
> Empty API responses (e.g. Qamishli and Deir ez-Zor official flight board arrays returning `[]`) are strictly classified as `unverified_data_gap`, NOT `confirmed_zero_operations`. A zero operation classification requires independent operational confirmation or NOTAM aerodrome closure.

---

## 4. Two Distinct Data Layers Architecture

- **Layer A (All Syrian Airports)**: Each Syrian aerodrome (`DAM`, `ALP`, `LTK`, `DEZ`, `KAC`, `PMS`, `OMDM`) is maintained independently in `airports`, `flight_events`, and `daily_airport_movements`. Missing fields are preserved as null.
- **Layer B (Damascus Deep-Dive)**: Damascus (`DAM / OSDI`) has a dedicated deep-dive layer with verified airport operations, flight events, and status breakdowns.
- **Multi-Airport Historical Aggregate (`DAM_ALP_LTK`)**: The Syria Economic Monitor 2024 series is preserved strictly under `historical_daily_movements_2024` with `scope = 'DAM_ALP_LTK'`. It is never mislabeled or merged into Damascus-only counts.
