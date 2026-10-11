# V2.20.6 — Immutable Evidence Correction & End-to-End Semantic Audit

## Executive Summary

Version 2.20.6 delivers a comprehensive, independent semantic audit and forensic correction of the evidence taxonomy and timestamp provenance across the Syrian Airport Data Engine. 

Following the V2.20.5 discovery of 76 mislabeled evidence records in `event_evidence` (`adsb_takeoff` and `adsb_touchdown`) derived from estimated timestamps rather than actual Mode-S telemetry or runway movement observations, V2.20.6 validates the full resolution without compromising the cryptographic immutability of the production SQLite database (`data/damascus_airport.db`).

The production database is protected by SQLite immutability triggers (`trg_prevent_evidence_update`, `trg_prevent_evidence_delete`) and monitored against strict SHA-256 baseline hashes. To adhere strictly to immutable ledger principles, all 76 records remain intact in the physical storage layer while the application layer, forensic endpoints, and research exports expose both the immutable original classification (`original_evidence_type`) and the corrected semantic interpretation (`evidence_type`), alongside an auditable correction ledger (`correction_history`).

Across 528 test cases, zero regressions or semantic inconsistencies were detected. All six protected baseline SHA-256 hashes remain 100% invariant.

---

## 1. Audit of the 76 Mislabeled Evidence Records

An exhaustive forensic inspection of the 76 mislabeled evidence rows in `event_evidence` confirmed:
- **35 `adsb_takeoff` records:** Derived from `time.estimated.departure` (predicted schedule/delay times on Flightradar24) or `departure.estimated` (AviationStack).
- **41 `adsb_touchdown` records:** Derived from `time.estimated.arrival` or `arrival.estimated` (including 18 foreign destination arrival estimates associated with legitimate Damascus and Aleppo physical departures).

### Forensic Inventory Summary

| Metric | Value |
| :--- | :--- |
| **Total Evidence Records in Ledger** | 3,118 |
| **Total Mislabeled Records Identified** | 76 |
| **Affected Takeoff Records (`adsb_takeoff`)** | 35 |
| **Affected Touchdown Records (`adsb_touchdown`)** | 41 |
| **Corrected Semantic Takeoff Interpretation** | `estimated_departure_timetable_prediction` |
| **Corrected Semantic Touchdown Interpretation** | `destination_estimated_arrival_prediction` |
| **Correction Mechanism** | `derived_at_read_time_immutable_ledger_preserved` |
| **Underlying Physical Rows Modified / Deleted** | **0** (strictly immutable) |

### Complete Forensic Reports
- **CSV Ledger:** [`reports/v2_20_6_mislabeled_evidence_audit.csv`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/reports/v2_20_6_mislabeled_evidence_audit.csv)
- **JSON Ledger:** [`reports/v2_20_6_mislabeled_evidence_audit.json`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/reports/v2_20_6_mislabeled_evidence_audit.json)

---

## 2. End-to-End Timestamp Consistency & Provenance

All six timestamp dimensions have been traced and enforced across database queries, normalizer pipelines, timestamp provenance transformations, aggregation modules, API endpoints, the dashboard UI, CSV/JSON exports, and sidecars:

```
+--------------------------------------------------------------------------+
|                        SIX TIMESTAMP DIMENSIONS                          |
+--------------------------------------------------------------------------+
| 1. scheduled_dep_time : Timetable scheduled departure (UTC ISO-8601)     |
| 2. estimated_dep_time : Upstream estimated departure (UTC ISO-8601)      |
| 3. actual_dep_time    : Authoritative actual departure; null if unobserved|
| 4. scheduled_arr_time : Timetable scheduled arrival (UTC ISO-8601)       |
| 5. estimated_arr_time : Upstream estimated arrival (UTC ISO-8601)        |
| 6. actual_arr_time    : Authoritative actual arrival; null if unobserved  |
+--------------------------------------------------------------------------+
```

### Invariant Rules
1. **Source `actual`/`real` Only:** Only raw source fields explicitly designated as `time.real.departure`, `time.real.arrival`, `departure.actual`, or `arrival.actual` can populate `actual_dep_time` or `actual_arr_time`.
2. **Strict Null Preservation:** Missing actual timestamps remain `null`. They are never filled with schedule fallbacks or zero strings (`"0"`).
3. **Ingestion Separation:** Ingestion timestamps (`ingested_at` / `created_at`) are never conflated with source observation times (`source_observed_at`).
4. **Operational Date Separation:**
   - `scheduled_flight_date`: Preserved timetable scheduled date.
   - `actual_movement_date`: Derived in airport-local timezone strictly when an actual movement timestamp exists; null otherwise.
   - `estimated_movement_date`: Derived in airport-local timezone from estimated timestamps.

---

## 3. Reconciliation of the 40 Affected Events

All 40 events identified in the V2.20.5 inventory were audited against live application output:

1. **31 Scheduled Service Events:**
   - Verified that `actual_dep_time` is `null` and `actual_arr_time` is `null`.
   - All estimated times are correctly placed in `estimated_dep_time` and `estimated_arr_time`.
   - `record_nature` remains strictly `scheduled_service`.
2. **9 Commercial Physical Movement Departures:**
   - Real departures (`PC771`, `XY230`, `EY562`, `FYC521`, `FYC727`, `FZ1114`, `G9376 [Oct 10]`, `RB441`, `XY592`).
   - Verified that legitimate actual departure timestamps (`actual_dep_time`) from Syrian runways are preserved.
   - Foreign destination estimated arrival times are isolated in `estimated_arr_time`; `actual_arr_time` remains strictly `null`.

---

## 4. Movement Identity & Counting Semantics

A rigorous audit of movement identity rules was completed:

- **Operating Flight vs Movement Identity:** Operating flight callsigns are distinct from aircraft airframe identities. An operating flight number represents an air service, not an immutable physical asset.
- **Codeshare Deduplication:** Marketing partner codeshares (e.g., flight records sharing identical route, date, and schedule where one is a commercial codeshare) are matched against primary operating flights.
- **Ambiguous Movement Handling:**
  - `confirmed_unique_movement_count`: 51 movements on the peak date (2026-10-10) for Damascus International Airport.
  - `ambiguous_movement_identity_count`: Exactly 2 records flagged where upstream codeshare links could not be verified with mathematical certainty. These are retained as explicitly ambiguous and never artificially merged.
  - `total_records`: 1,481 records representing the comprehensive totality of scheduled timetable rows, commercial operational events, and marketing entries.
- **Cross-Source Edge Cases:** The 8 known cross-source conflict edge cases (divergent commercial statuses, mismatched local timezones, differing carrier prefixes) are handled deterministically without data loss.

---

## 5. Aircraft Registration Metrics

Aircraft registration metrics across Syrian aerodromes were evaluated for clarity:

- `distinct_reported_aircraft_registrations`: Exactly **63** non-empty normalized airframe registrations reported across all Syrian airports (**60** among commercial physical movement events).
- **Distinction from Runway Sensors:** Clearly documented in all UI tooltips and export metadata that this metric reflects commercially reported airframe identifiers rather than optical/physical runway sensor confirmations.
- **Deprecated Aliases:** `total_unique_aircraft` and `unique_aircraft_tracked` are preserved as backward-compatible aliases pointing to `distinct_reported_aircraft_registrations`, accompanied by explicit deprecation notices.

---

## 6. API, UI & Export Verification

### Forensic API Mode
The `/api/events/{event_id}/evidence` endpoint supports `?forensic=true`:
- Standard Mode: Returns semantically corrected evidence items (`evidence_type = estimated_departure_timetable_prediction`, etc.).
- Forensic Mode: Surfaces top-level metadata:
  - `has_mislabeled_evidence: true`
  - `corrected_count: <int>`
  - `forensic_mode: true`
  - Item fields: `original_evidence_type`, `corrected_semantic_interpretation`, `correction_status`, `correction_history`.

### Dedicated Evidence Audit API
- Endpoints: `@app.get("/api/evidence/audit")` and `@app.get("/api/evidence/corrections")`.
- Exposes the complete 76-record forensic audit ledger with summary statistics.

### Research Export Integration
- Registered dataset: `v2_20_6_mislabeled_evidence_audit`.
- Available via `/api/export/v2_20_6_mislabeled_evidence_audit?format=csv` and `json`.
- Complete research metadata sidecars and CSV headers included.

### Dashboard UI Enhancements
- Added **Evidence Taxonomy Forensic Audit (76 Records)** card to the Research Exports tab in [`static/index.html`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/static/index.html).
- Direct download buttons for CSV and JSON audit ledgers.
- Visual distinction between estimated and actual timestamps in the flight inspector.

---

## 7. Cryptographic Integrity & Verification Results

All project assets remain completely intact, and no writes occurred to production databases.

### Protected Baseline SHA-256 Hashes

| Protected Asset Path | Expected Baseline SHA-256 Hash | Verified Match |
| :--- | :--- | :---: |
| `data/damascus_airport.db` | `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b` | **TRUE** |
| `data/archived_fids_staging.db` | `a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4` | **TRUE** |
| `data/archived_fids_analytics.db` | `e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe` | **TRUE** |
| `data/archived_fids_history_staging.db` | `39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f` | **TRUE** |
| `data/raw/snapshots/wayback_damairport_fids_20260709234230.raw` | `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf` | **TRUE** |
| `data/raw/snapshots/wayback_damairport_fids_20260709234230.json` | `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491` | **TRUE** |

### Test Suite Execution
- **Total Test Cases Executed:** 528
- **Passed:** 528
- **Failed / Regressed:** 0
- **Execution Time:** 23.05 seconds
