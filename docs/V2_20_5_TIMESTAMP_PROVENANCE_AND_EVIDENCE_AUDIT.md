# V2.20.5 — Estimated vs Actual Timestamp Provenance & Evidence Taxonomy Audit

## Executive Summary

Version 2.20.5 completes an end-to-end data-semantics audit and correction of timestamp provenance and evidence taxonomy across the Syrian Airport Data Engine. 

Following the forensic analysis of flight **G9376** (`event_id = 6e9ccc725c3b169e`), an exhaustive audit was conducted across the production SQLite database (`data/damascus_airport.db`) and all raw snapshots (Flightradar24 and AviationStack). The audit revealed that estimated departure and arrival timestamps (`time.estimated.departure`, `time.estimated.arrival`, `departure.estimated`, `arrival.estimated`) were historically mapped into database columns named `actual_dep_time` and `actual_arr_time`, generating mislabeled evidence rows (`adsb_takeoff` and `adsb_touchdown`) for flights that lacked actual Mode-S telemetry or runway movement observations.

Because the production database is cryptographically protected by baseline SHA-256 hashes and SQLite immutability triggers on the evidence ledger, all corrections were deterministically implemented in the application layer (`src/timestamp_provenance.py`, `src/api.py`), accompanied by synchronized processed exports (`data/processed/`), dashboard transparency updates (`static/index.html`), and a dedicated 17-point test suite (`tests/test_v2_20_5_timestamp_provenance.py`). All 506 project tests pass, and all 6 protected baseline cryptographic hashes remain invariant.

---

## 1. Audit of the Estimated-to-Actual Timestamp Mapping

An automated inspection of all 1,830 records in `flight_events` against raw source payloads identified exactly **40 affected events**:

1. **31 Scheduled Service Events:** Flights listed on commercial timetables where estimated departure or arrival timestamps (e.g., predicted delays or estimated schedules) were mapped into `actual_dep_time` or `actual_arr_time`. For these records, no actual departure or arrival occurred; their actual timestamp fields must be strictly `null`.
2. **9 Physical Movement Departure Events:** Real commercial flights departing Damascus (DAM) or Aleppo (ALP) (`PC771`, `XY230`, `EY562`, `FYC521`, `FYC727`, `FZ1114`, `G9376 [Oct 10]`, `RB441`, `XY592`) that had legitimate actual takeoff times from Syrian airports, but where the destination airport estimated arrival time (`time.estimated.arrival`) was mapped into `actual_arr_time`.

### Complete Inventory Report

The complete audit inventory has been exported to:
[`reports/v2_20_5_estimated_mapping_inventory.csv`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/reports/v2_20_5_estimated_mapping_inventory.csv)

| Column | Description |
| :--- | :--- |
| `event_id` | Unique hex identifier of the canonical event |
| `flight_number` | Operating or commercial flight callsign |
| `airport_id` | Syrian aerodrome identifier (`DAM` or `ALP`) |
| `source` | Upstream data provider feed (`flightradar24`, `aviationstack`) |
| `raw_source_field` | Raw payload field (`time.estimated.departure`, `time.estimated.arrival`) |
| `stored_database_field` | Misallocated table column (`actual_dep_time`, `actual_arr_time`) |
| `record_nature` | Classification category (`scheduled_service`, `physical_movement`) |
| `evidence_type` | Ledger evidence type (`adsb_takeoff`, `adsb_touchdown`) |
| `correction_required` | Action applied (`shift_to_estimated_dep_time_and_null_actual`, `shift_to_estimated_arr_time_and_null_actual`) |
| `reason` | Technical forensic justification |

---

## 2. Corrected Timestamp Semantics in the Application Layer

To ensure strict data provenance, the application layer now exposes six distinct, explicit timestamp fields across all APIs and exports:

1. `scheduled_dep_time`: Timetable scheduled departure time (UTC ISO-8601).
2. `estimated_dep_time`: Upstream estimated departure time (UTC ISO-8601).
3. `actual_dep_time`: Authoritative verified actual departure time (UTC ISO-8601); strictly `null` if unobserved.
4. `scheduled_arr_time`: Timetable scheduled arrival time (UTC ISO-8601).
5. `estimated_arr_time`: Upstream estimated arrival time (UTC ISO-8601).
6. `actual_arr_time`: Authoritative verified actual arrival time (UTC ISO-8601); strictly `null` if unobserved.

### Strict Semantic Rules
- **No Ingestion Leakage:** `ingested_at` (`created_at`) is strictly separated and never used as observation time.
- **No Estimated Promotion:** Estimated timestamps never populate `actual_dep_time` or `actual_arr_time`.
- **Missing Actuals Remain Null:** Missing actual timestamps remain `null`—never fabricated zeros (`"0"`) or scheduled fallbacks.
- **Operational Date Semantics:**
  - `scheduled_flight_date`: Preserved scheduled operational calendar date.
  - `actual_movement_date`: Airport-local calendar date derived strictly when genuine actual movement timestamps exist (null for estimated/scheduled flights).
  - `estimated_movement_date`: Airport-local calendar date derived from estimated timestamps.

---

## 3. Evidence Taxonomy Audit

An inspection of the `event_evidence` ledger identified **76 mislabeled evidence rows**:
- **35 `adsb_takeoff` rows:** Created from `time.estimated.departure` rather than actual Mode-S takeoff telemetry.
- **41 `adsb_touchdown` rows:** Created from `time.estimated.arrival` rather than actual Mode-S touchdown telemetry.

### Preservation and Correction Policy
1. **Immutable Database Ledger:** The SQLite database ledger remains cryptographically unchanged. No records or evidence rows were deleted or modified in production databases.
2. **Application Layer Reclassification:** When evidence rows derived from estimated timestamps are loaded or evaluated by the engine, `correct_evidence_item()` reclassifies their `evidence_type` to `estimated_departure` or `estimated_arrival` and sets `is_estimated = True`.
3. **No Inference of Physical Movements:** The rule is strictly enforced: an estimated timestamp alone never justifies classifying an event as a `physical_movement`.

---

## 4. Movement Counting & Deduplication Semantics

The movement counting and codeshare matching semantics were audited and standardized:

### Field Definitions
- `confirmed_unique_movement_count`: Distinct operating flights with corroborated operational status timestamps on that date and direction.
- `ambiguous_movement_identity_count`: Marketing partner codeshares that cannot be matched to an operating flight on that date.
- `unique_operating_flight_count`: Distinct operating flight callsigns (operating carrier service identity).
- `marketing_codeshare`: Secondary partner listings. Marketing codeshares are never added to operating movement totals.

### Endpoint Consistency
`/api/movements/comparison` exposes full daily breakdowns with:
- `confirmed_unique_movement_count`
- `ambiguous_movement_identity_count`
- `unique_operating_flight_count`
- `scheduled_record_count`
- `commercial_operational_event_count`
- Full `field_definitions` and `deduplication_rules` metadata dictionaries.

---

## 5. API, Dashboard & Export Consistency

1. **Dashboard UI (`static/index.html`):**
   - Added `Estimated (UTC)` column to the main flight events table.
   - Updated table row rendering to display `scheduled`, `estimated`, and `actual` timestamps independently.
   - Added platform warning banner highlighting aircraft metric deprecation and timestamp separation.
2. **Stats Endpoint (`/api/movements/stats`):**
   - Added `deprecated_metrics` dictionary formally documenting the deprecation of `total_unique_aircraft` and `unique_aircraft_tracked`.
   - Exposes `distinct_reported_aircraft_registrations` (63 distinct commercial registrations across Syrian aerodromes; 60 on physical movements).
3. **Processed Exports & Metadata:**
   - Synchronized `all_syrian_flight_events.csv`, `all_syrian_flight_events.json`, `damascus_flight_events.csv`, and `damascus_flight_events.json` to expose `estimated_dep_time`, `estimated_arr_time`, and null out estimated timestamps from actual columns.
   - Updated `EXPORT_METADATA` headers and descriptions for `/api/export/{dataset}`.

---

## 6. Cryptographic Baseline Verification

All 6 baseline files were verified before and after execution. Every SHA-256 digest remains identical:

| Protected File Path | Baseline SHA-256 Digest | Status |
| :--- | :--- | :--- |
| `data/damascus_airport.db` | `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b` | **VERIFIED INTACT** |
| `data/archived_fids_staging.db` | `a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4` | **VERIFIED INTACT** |
| `data/archived_fids_analytics.db` | `e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe` | **VERIFIED INTACT** |
| `data/archived_fids_history_staging.db` | `39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f` | **VERIFIED INTACT** |
| `data/raw/snapshots/wayback_damairport_fids_20260709234230.raw` | `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf` | **VERIFIED INTACT** |
| `data/raw/snapshots/wayback_damairport_fids_20260709234230.json` | `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491` | **VERIFIED INTACT** |

---

## 7. Verification Test Results

```
============================ 506 passed in 23.82s =============================
Production DB Hash BEFORE: c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b
Production DB Hash AFTER:  c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b
Hashes match: True
```
