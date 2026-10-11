# V2.20.4 — Operational Classification & Movement Identity Validation Report

## Executive Summary

This audit completes Milestone **V2.20.4** of the Syrian Airport Data Engine, focusing exclusively on evidence-based operational classification, movement identity validation, and aircraft registration semantics.

Key conclusions:
1. **Event `6e9ccc725c3b169e` (G9376) Investigation:**
   - Raw source forensic analysis confirms that the timestamp `1791622800` (`2026-10-10T09:00:00Z`) represents an **estimated delayed departure** published in upstream commercial feeds, delayed overnight from its scheduled slot of `2026-10-09 13:55` Damascus local.
   - Upstream Flightradar24 status was `"Unknown"` with `real.departure: null`, and official Syrian FIDS status was `"scheduled"`. No source reported a completed physical takeoff or landed state.
   - Classification as `record_nature = 'scheduled_service'` is **defensible, correct, and strictly preserved**. It is not promoted to `physical_movement`.
2. **Movement Identity Key Validation:**
   - Evaluated the 4-tuple key `(airport_id, flight_date, movement_type, operating_flight_number)`.
   - Identified and tested failure modes where this key would erroneously merge separate physical movements (e.g. morning and evening shuttle flights sharing callsign, different carriers, or missing operating numbers).
   - Validated that the engine's multi-layered match evaluator (`evaluate_cross_source_match`) successfully defends against all 8 required edge cases and preserves ambiguous records as unmerged/ambiguous rather than forcing a false match.
3. **Aircraft Registration Semantics:**
   - Audited all 131 `physical_movement` records carrying aircraft registrations.
   - Confirmed exactly 60 distinct normalized registrations (`distinct_reported_aircraft_registrations = 60`).
   - 0 invalid or malformed registrations; 100% (131/131) supported by direct source payloads (FR24/AviationStack); 0% inherited or copied.
   - Mode-S ICAO24 transponder hex codes are available for all 131 records (60 distinct hex values).
   - Clarified that these reflect commercial telemetry aggregations, not local ground radar receiver contacts.
4. **Platform Verification & Cryptographic Safety:**
   - Verified that all 6 protected baseline files match their cryptographic SHA-256 hashes exactly.
   - All 489 project tests pass (100% pass rate, 0 failures, exit code 0).

---

## 1. Deep Forensic Investigation: Event `6e9ccc725c3b169e` (G9376)

### 1.1 Reported Values in Database
- **`event_id`**: `6e9ccc725c3b169e`
- **`airport_id`**: `DAM` (Damascus International Airport / OSDI)
- **`flight_number`**: `G9376` (Operating: `G9376`, Carrier: `Air Arabia`)
- **`movement_type`**: `departure` (Route: DAM -> SHJ / Sharjah International Airport)
- **`flight_date`**: `2026-10-09`
- **`local_operational_date`**: `2026-10-09`
- **`flight_status`**: `scheduled`
- **`record_nature`**: `scheduled_service`
- **`scheduled_dep_time`**: `2026-10-09T10:55:00Z` (`raw_scheduled_dep_time: 2026-10-09 13:55`)
- **`actual_dep_time`**: `2026-10-10T09:00:00Z` (`raw_actual_dep_time: 1791622800`)
- **`source`**: `damairport_official+aviationstack+flightradar24`
- **`source_record_id`**: `911926b1-ffef-4cc7-a094-d31effd22e15`

### 1.2 Upstream Source Payloads
Forensic inspection of the raw snapshot files revealed the exact multi-source origins:

1. **Official Damascus Airport Portal (`damairport_official_flights_raw.json`):**
   ```json
   {
     "id": "911926b1-ffef-4cc7-a094-d31effd22e15",
     "flightNumber": "G9 376",
     "airline": "Air Arabia",
     "direction": "departure",
     "origin": "DAM",
     "destination": "SHJ",
     "date": "2026-10-09",
     "time": "13:55",
     "status": "scheduled",
     "createdAt": "2026-08-01T16:12:55Z"
   }
   ```
   *Analysis:* Published commercial timetable listing for 13:55 local time (10:55 UTC) on 2026-10-09. No operational departure time or transponder telemetry.

2. **AviationStack (`aviationstack_dam_departures_raw.json`):**
   ```json
   {
     "flight_date": "2026-10-09",
     "flight_status": null,
     "departure": {
       "airport": "Damascus International Airport",
       "iata": "DAM",
       "scheduled": "2026-10-09T13:55:00+00:00",
       "estimated": "2026-10-09T13:55:00+00:00",
       "actual": null,
       "actual_runway": null
     },
     "arrival": {
       "airport": "Sharjah",
       "iata": "SHJ",
       "scheduled": "2026-10-09T18:00:00+00:00",
       "actual": null
     },
     "flight": { "iata": "G9376" },
     "aircraft": null
   }
   ```
   *Analysis:* `actual` and `actual_runway` are both strictly `null`.

3. **Flightradar24 Snapshot (`20261010_164054_flightradar24_dam_departures_raw.json`):**
   ```json
   {
     "flight": {
       "identification": {
         "id": null,
         "row": 5873468507,
         "number": { "default": "G9376" }
       },
       "status": {
         "text": "Unknown",
         "generic": { "status": { "text": "unknown", "type": "departure" } }
       },
       "aircraft": { "model": { "code": "320" }, "hex": "", "registration": "" },
       "time": {
         "scheduled": { "departure": 1791543300 },
         "real": { "departure": null, "arrival": null },
         "estimated": { "departure": 1791622800, "arrival": null }
       }
     }
   }
   ```
   *Analysis:*
   - `time.scheduled.departure = 1791543300` corresponds to `2026-10-09 10:55:00 UTC` (13:55 Damascus local).
   - `time.real.departure = null` (no physical departure confirmed).
   - `time.estimated.departure = 1791622800` corresponds to `2026-10-10 09:00:00 UTC` (12:00 Damascus local).
   - `aircraft.hex = ""` and `aircraft.registration = ""` (no Mode-S aircraft transponder contact).
   - Upstream status was `"Unknown"`.

### 1.3 Active Evidence and Retractions
- In `v_active_evidence`, two rows exist for this event:
  - `ev_809974eb71be3a65` (source: `damairport_official+aviationstack+flightradar24`, observed_value: `2026-10-10T09:00:00Z`, raw: `1791622800`)
  - `ev_aef32f35d286b2e7` (source: `flightradar24`, observed_value: `2026-10-10T09:00:00Z`, raw: `1791622800`)
- Both rows were generated from the upstream FR24 estimated payload.
- In `evidence_retractions`, there are 0 retractions.
- In `scratch/migrated_45_events.csv`, this event was identified with reason: `estimated_timestamp_misclassified_as_adsb_telemetry` and `actual_to_est: True`.

### 1.4 Determination & Classification Decision
- **Determination:** The timestamp `1791622800` represents **Case 2/4: An estimated delayed departure timestamp from a commercial feed that was upstream-placed in an estimated field and ingested into the timestamp field, but which never represented an actual physical runway movement.**
- **Decision:** Because `flight_status` was `scheduled` (and `unknown` in FR24) and no source reported a completed physical movement (`departed` or `landed`), the normalization pipeline correctly preserved `record_nature = 'scheduled_service'`.
- **Verdict:** Do NOT promote G9376 to `physical_movement`. Keep `record_nature = 'scheduled_service'`. The scheduled date remains `2026-10-09`, while the estimated/actual movement timestamp points to `2026-10-10T09:00:00Z`.

---

## 2. Movement Identity Key Validation & Edge Cases

### 2.1 Audit of the Key `(airport_id, flight_date, movement_type, operating_flight_number)`
The composite key `(airport_id, flight_date, movement_type, operating_flight_number)` correctly separates arrivals from departures and distinguishes airports. However, **it is insufficient as a standalone primary movement identity key** because:
1. **Operating flight numbers are commercial service designations, not unique physical aircraft legs.**
2. Airlines regularly operate multiple flights in the same direction on the same date with the same flight number (e.g. daily double shuttles, feeder loops).
3. Missing or null operating flight numbers would collapse unrelated flights.
4. Flights with conflicting carriers or divergent timestamps would be merged erroneously.

### 2.2 Evaluation of the 8 Required Test Cases
The engine's `evaluate_cross_source_match` logic was validated against all 8 required edge cases:

| Case # | Scenario Description | Evaluation Rule | Engine Outcome | Can Merge? | Rationale |
|---|---|---|---|---|---|
| **1** | Same flight number, date, airport, direction; different actual timestamps (e.g. 08:00 vs 20:00 UTC) | Temporal Delta (> 180 min) | `SPLIT_DISTINCT_LEG` | **No** | Prevents collapsing distinct morning and evening services into one movement. |
| **2** | Same flight number, different operating carriers (e.g. Syrian Air vs Qatar Airways) | Carrier Compatibility | `CONFLICT_CARRIER` | **No** | Prevents merging flights operated by different commercial carriers. |
| **3** | Same flight number, multiple movements on one date | Temporal Clustering | `SPLIT_DISTINCT_LEG` | **No** | Identifies independent flight rotations operating under the same commercial flight number. |
| **4** | Same aircraft registration, different flight numbers (e.g. RB515 vs RB521 on YK-BAA) | Service Callsign Match | `MISMATCH_FLIGHT_NUMBER` | **No** | Confirms airframe identity is NOT flight identity; distinct flight numbers represent distinct movements. |
| **5** | Different flight numbers, same aircraft registration | Service Callsign Match | `MISMATCH_FLIGHT_NUMBER` | **No** | Prevents airframe tracking from overriding operational movement boundaries. |
| **6** | Missing operating flight number | Identity Anchor Check | `MISMATCH_FLIGHT_NUMBER` | **No** | Records lacking flight number are not merged together; treated as unmergeable / ambiguous. |
| **7** | Missing actual timestamp | Temporal Anchor Check | `POTENTIAL_MATCH_LACKS_TIME` | **No** | Cannot verify operational occurrence without temporal evidence; remains unmerged. |
| **8** | Codeshare & operating flight with different marketing numbers (EK2212 / FZ1113) | Codeshare Cross-Reference | `CONFIRMED_MATCH` | **Yes** | Successfully associates codeshare with operating flight without inflating operating flight totals. |

### 2.3 Ambiguity Handling
- When candidate records have ambiguous timestamp deltas (between 60m and 180m), the engine flags them as `POTENTIAL_MATCH_AMBIGUOUS_DELTA` (`can_merge = False`).
- In `/api/movements/comparison`, codeshares that lack a matching operational flight on that date remain explicitly reported under `unmatched_codeshare_record_count` with `ambiguous: true`, rather than being forced into a match.

---

## 3. Aircraft Registration Semantics

### 3.1 Audit Findings (131 `physical_movement` Records)
A comprehensive audit of the 131 records classified as `physical_movement` carrying aircraft registrations established:

1. **Non-null Registrations:** Exactly **131** records.
2. **Distinct Normalized Registrations:** Exactly **60** distinct airframe registrations (`distinct_reported_aircraft_registrations = 60`).
3. **Invalid or Malformed Registrations:** **0** (all conform to standard national/ICAO registration prefix formats).
4. **Direct Source Evidence:** **131** records (100%) are directly supported by upstream commercial feed payloads (FR24 or AviationStack).
5. **Inherited or Copied Registrations:** **0** records (0%). No registrations were artificially copied from codeshare partners or other flights.
6. **Mode-S ICAO24 Availability:** All 131 records have non-empty Mode-S 24-bit hex transponder addresses, resolving to **60 distinct hex addresses** that map 1:1 to the 60 distinct registrations.

### 3.2 Breakdown by Airport
- **DAM (Damascus International):** 98 records
- **ALP (Aleppo International):** 32 records
- **DEZ (Deir ez-Zor):** 1 record
- **Total:** 131 records

### 3.3 Metric Standardization
- The metric is formally standardized as:
  ```
  distinct_reported_aircraft_registrations
  ```
- **Semantic Boundary:** This count represents distinct aircraft registrations reported in commercial aviation aggregator feeds. It is **NOT** a certified ground radar count or physical receiver observation, as Damascus Airport has no verified ADS-B receiver feeding the public ledger.

---

## 4. API & Dashboard Consistency

| Endpoint | Semantic Invariant Enforced | Status |
|---|---|---|
| `/api/movements/verified` | Strictly filters `record_nature = 'physical_movement'`. Excludes timetable records (`scheduled_service`) and unverified claims. | Verified |
| `/api/movements/scheduled` | Strictly returns timetable schedule records (`record_nature = 'scheduled_service'`). Excluded from operational movement counts. | Verified |
| `/api/movements/comparison` | Separates `commercial_operational_event_count`, `scheduled_record_count`, `codeshare_record_count`, `matched_codeshare_record_count`, and `unmatched_codeshare_record_count`. Codeshares do NOT inflate operating flight counts. | Verified |
| `/api/movements/stats` | Exposes `distinct_reported_aircraft_registrations` alongside backward-compatible aliases `total_unique_aircraft` and `unique_aircraft_tracked`. | Verified |
| `/api/export/{dataset}` | Every export carries verified dataset provenance, geographic scope, and evidence levels. | Verified |

---

## 5. Verification & Safety Summary

### 5.1 Protected Baseline Hashes (SHA-256 Invariance)
All 6 baseline assets were cryptographically verified before and after this milestone:

| Asset Path | Expected SHA-256 Hash | Post-Audit Hash | Status |
|---|---|---|---|
| `data/damascus_airport.db` | `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b` | `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b` | **MATCH (Unchanged)** |
| `data/archived_fids_staging.db` | `a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4` | `a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4` | **MATCH (Unchanged)** |
| `data/archived_fids_analytics.db` | `e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe` | `e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe` | **MATCH (Unchanged)** |
| `data/archived_fids_history_staging.db` | `39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f` | `39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f` | **MATCH (Unchanged)** |
| `data/raw/snapshots/wayback_damairport_fids_20260709234230.raw` | `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf` | `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf` | **MATCH (Unchanged)** |
| `data/raw/snapshots/wayback_damairport_fids_20260709234230.json` | `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491` | `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491` | **MATCH (Unchanged)** |

### 5.2 Test Execution Results
- **Targeted V2.20.4 Tests (`tests/test_v2_20_4_operational_classification.py`):** 15 passed in 1.68s.
- **Full Test Suite (`tests/`):** **489 passed in 31.12s** (0 failures, 0 errors, exit code 0).
- **Zero Production Database Writes:** No insert, update, or delete commands were run against `data/damascus_airport.db`.
