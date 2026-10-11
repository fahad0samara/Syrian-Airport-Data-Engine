# Final Provenance & Data Integrity Audit Report Before Day 2
**Syrian Airport Data Engine**
**Audit Timestamp:** 2026-10-10T20:57:00+03:00  
**Scope:** Strict read-only audit of `data/damascus_airport.db`, raw files in `data/raw/`, and comparison with `data/frozen_baseline_20261010.db`.  
**Trial Execution Status:** PAUSED (Day 2 NOT executed, Task Scheduler NOT registered, Baseline UNTOUCHED).

---

## Executive Summary & Verdict

| Audit Domain | Test Result | Key Metric / Verification Status |
| :--- | :---: | :--- |
| **1. Evidence Ledger Decomposition** | **PASS** | 1,508 total rows = 896 unique semantic observations (612 dual-represented, 284 single-represented, 0 unlinkable). |
| **2. Structural Raw Payload Provenance** | **PASS** | 1,508 / 1,508 records (100.00%) structurally matched to flight, airport, direction, and raw payload fields. |
| **3. AviationStack Commercial Evidence** | **PASS** | 8 newly added rows strictly derived from `departure.actual` / `arrival.actual`. Zero generated from scheduled fields. |
| **4. Timestamp Upgrades & Timezone Audit** | **PASS** | 94 events upgraded to Tier 4 ADS-B radar. Delta is physical seconds (e.g. 9s), zero timezone distortion. |
| **5. Cross-Layer Double-Counting Prevention** | **PASS** | Zero double-counting. Physical movements remain strictly 131 across DB, APIs, Aggregations, and Exports. |
| **Overall Production Readiness Verdict** | **READY FOR DAY 2** | Awaiting explicit operator authorization to commence Day 2. |

---

## 1. Detailed Evidence Ledger Decomposition (Point 1)

### Mathematical & Relational Breakdown
The immutable append-only ledger `event_evidence` contains **1,508** rows, structured as follows:

```
Total Rows: 1,508
├── Unique Semantic Observations: 896 (grouped by event_id + evidence_type + observed_value)
│   ├── Dual-Represented Observations: 612 (represented under composite source and refined discrete source)
│   │   └── Generates: 612 × 2 = 1,224 rows
│   └── Single-Represented Observations: 284
│       ├── Initial Backfill Singletons: 276 rows (observations originally from single source)
│       └── Newly Added AviationStack Telemetry: 8 rows (KU551/KU552 commercial actual timestamps)
└── Records Unlinkable to Raw Sources: 0 (100.00% traceable)
```

### Table of Ledger Representation
| Metric Category | Count | Percentage | Explanation |
| :--- | :---: | :---: | :--- |
| **Total `event_evidence` Rows** | **1,508** | 100.00% | Full append-only ledger count. |
| **Semantically Unique Evidence Entries** | **896** | 59.42% | Unique tuples of `(event_id, evidence_type, observed_value)`. |
| **Dual-Represented Evidence Tuples** | **612** | 40.58% | Observations having 2 representations due to source refinement (`source_name` change). |
| **Total Rows in Dual Representations** | **1,224** | 81.17% | 612 old composite rows + 612 new discrete rows. |
| **Single-Represented Evidence Tuples** | **284** | 18.83% | Observations with a single representation (276 historical + 8 new commercial). |
| **Unlinkable Records (Synthetic / Ghost)** | **0** | 0.00% | Every record links directly to verifiable raw source files. |

**Concrete Example:**
Event `101a6a0ff9be4ce9` (Flight `TC-AIS` at Aleppo ALP):
- Ledger Row 3: `ev_78981ddaf52800f5` with `source_name = 'alpairport_official+flightradar24'`, `observed_value = 'TC-AIS'`.
- Ledger Row 898: `ev_48bc9d870f7d0a21` with `source_name = 'flightradar24'`, `observed_value = 'TC-AIS'`.
- Both records preserve the exact same physical observation without deleting historical audit history, complying with SQLite triggers `trg_prevent_evidence_update` and `trg_prevent_evidence_delete`.

---

## 2. Structural Raw Payload Provenance (Point 2)

A deep structural verification was performed against raw files in `data/raw/` (`flightradar24_*_raw.json`, `aviationstack_*_raw.json`, `*official_flights_raw.json`).
Each evidence record was checked against the originating raw JSON object for:
1. **Flight Number & Callsign:** Exact match (`item.flight.identification.number.default` or `item.flight.iata`).
2. **Airport ID & Direction:** Exact match to the aerodrome queried (`DAM`, `ALP`, `DEZ`) and leg direction (`arrival`, `departure`).
3. **Payload Field Type:**
   - `adsb_takeoff` / `adsb_touchdown`: Matched to `flight.time.real` or `flight.time.estimated`.
   - `commercial_takeoff` / `commercial_touchdown`: Matched to `departure.actual` or `arrival.actual`.
   - `aircraft_registration`: Matched to `flight.aircraft.registration`.
   - `aircraft_icao24`: Matched to `flight.aircraft.hex` or `flight.aircraft.icao24`.

### Verification Outcome
- **Total Records Checked:** 1,508
- **Structurally Verified:** 1,508 (100.00%)
- **Unmatched Records:** 0 (0.00%)

**Concrete Example:**
Event `17742d3532f6b820` (Fly Baghdad `FYC486` arriving at Damascus `DAM` on 2026-10-09):
- `adsb_touchdown` evidence `ev_cc32166a86a6ecc1`: Value `2026-10-09T03:27:56Z`, raw epoch `1791516476`.
- Raw file: `data/raw/flightradar24_dam_arrivals_raw.json`.
- Raw record: `flight.identification.number.default = 'FYC486'`, `flight.airport.origin.code.iata = 'SAW'`, `flight.time.real.arrival = 1791516476`, `flight.aircraft.registration = 'YR-JUL'`, `flight.aircraft.hex = '4A2AAC'`.
- Structural match is complete across all telemetry and airframe properties.

---

## 3. AviationStack Commercial Evidence Audit (Point 3)

The 8 newly added rows in `event_evidence` attributed to `aviationstack` were audited against raw source files:
- `data/raw/aviationstack_dam_arrivals_raw.json`
- `data/raw/aviationstack_dam_departures_raw.json`

### Audit Results Table
| Row ID | Event ID | Flight | Direction | Evidence Type | Observed Value (UTC) | Raw Timestamp | Raw Field Verified | Scheduled Field in Raw | Is Sched Only? |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1106** | `7d8bf4408c2ebd29` | `KU551` | Arrival | `commercial_touchdown` | `2026-10-09T08:16:00Z` | `2026-10-09T11:16:00+00:00` | `arrival.actual` | `2026-10-09T13:40:00+00:00` | **NO** |
| **1107** | `7d8bf4408c2ebd29` | `KU551` | Arrival | `commercial_takeoff` | `2026-10-09T06:19:00Z` | `2026-10-09T09:19:00+00:00` | `departure.actual` | `2026-10-09T11:10:00+00:00` | **NO** |
| **1225** | `50349b022e95cb8e` | `KU552` | Departure | `commercial_touchdown` | `2026-10-09T11:42:00Z` | `2026-10-09T14:42:00+00:00` | `arrival.actual` | `2026-10-09T17:25:00+00:00` | **NO** |
| **1226** | `50349b022e95cb8e` | `KU552` | Departure | `commercial_takeoff` | `2026-10-09T09:48:00Z` | `2026-10-09T12:48:00+00:00` | `departure.actual` | `2026-10-09T14:40:00+00:00` | **NO** |
| **1337** | `5e4c3e64f5f07394` | `KU551` | Arrival | `commercial_touchdown` | `2026-10-10T08:36:00Z` | `2026-10-10T11:36:00+00:00` | `arrival.actual` | `2026-10-10T13:40:00+00:00` | **NO** |
| **1338** | `5e4c3e64f5f07394` | `KU551` | Arrival | `commercial_takeoff` | `2026-10-10T06:40:00Z` | `2026-10-10T09:40:00+00:00` | `departure.actual` | `2026-10-10T11:10:00+00:00` | **NO** |
| **1444** | `07fe775464d8faf4` | `KU552` | Departure | `commercial_touchdown` | `2026-10-10T11:43:00Z` | `2026-10-10T14:43:00+00:00` | `arrival.actual` | `2026-10-10T17:25:00+00:00` | **NO** |
| **1445** | `07fe775464d8faf4` | `KU552` | Departure | `commercial_takeoff` | `2026-10-10T09:53:00Z` | `2026-10-10T12:53:00+00:00` | `departure.actual` | `2026-10-10T14:40:00+00:00` | **NO** |

**Conclusion:** All 8 rows originate strictly from explicit `actual` operational timestamps in the AviationStack feed. Zero rows were fabricated or derived from scheduled fields. Furthermore, these 4 events remain classified as `scheduled_service` in `flight_events` because their overall feed status was not verified physical landing/departure, adhering to our strict conservative promotion policy.

---

## 4. Actual Timestamp Upgrades & Timezone Analysis (Point 4)

Between the frozen baseline and the current database:
- **Total Canonical Events with Upgraded Timestamps:** 94 events
  - `actual_dep_time` upgraded: 93 events
  - `actual_arr_time` upgraded: 67 events
- **Source Hierarchy Policy:**
  - **Tier 4 (Highest):** Terrestrial ADS-B Radar (`flightradar24`) — integer Unix epochs.
  - **Tier 3:** Commercial Aggregator API (`aviationstack`) — ISO string with local wall-clock.
  - **Tier 2:** Official Airport Authority Portals (`damairport_official`, `alpairport_official`).
  - **Tier 1:** Timetable & Statistical Baselines.

### Representative Upgrade Comparisons
| Flight | Airport & Leg | Baseline Raw (Tier 3) | Current Raw (Tier 4) | Baseline UTC | Current UTC | Delta | Provenance / Timezone Rationale |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`3L504`** | `SHJ -> DAM` | `2026-10-09T08:16:00+00:00` | `1791519369` | `04:16:00Z` | `04:16:09Z` | **9s** | Localized to `Asia/Dubai` (UTC+4), yields `04:16:00Z`. ADS-B transponder wheels-off at `04:16:09Z` accepted (+9s delta). |
| **`3L504`** | `SHJ -> DAM` | `2026-10-09T10:02:00+00:00` | `1791529373` | `07:02:00Z` | `07:02:53Z` | **53s** | Localized to `Asia/Damascus` (UTC+3), yields `07:02:00Z`. ADS-B touchdown at `07:02:53Z` accepted (+53s delta). |
| **`EY561`** | `AUH -> DAM` | `2026-10-09T14:16:00+00:00` | `1791540996` | `10:16:00Z` | `10:16:36Z` | **36s** | Localized to `Asia/Dubai` (UTC+4), yields `10:16:00Z`. ADS-B wheels-off at `10:16:36Z` accepted (+36s delta). |
| **`F3741`** | `JED -> DAM` | `2026-10-09T07:50:00+00:00` | `1791521410` | `04:50:00Z` | `04:50:10Z` | **10s** | Localized to `Asia/Riyadh` (UTC+3), yields `04:50:00Z`. ADS-B wheels-off at `04:50:10Z` accepted (+10s delta). |
| **`FYC522`** | `DAM -> KWI` | `2026-10-09T20:28:00+00:00` | `1791566903` | `17:28:00Z` | `17:28:23Z` | **23s** | Localized to `Asia/Damascus` (UTC+3), yields `17:28:00Z`. ADS-B wheels-off at `17:28:23Z` accepted (+23s delta). |
| **`FZ1114`** | `DAM -> DXB` | `2026-10-10T16:54:00+00:00` | `1791640456` | `13:54:00Z` | `13:54:16Z` | **16s** | Localized to `Asia/Damascus` (UTC+3), yields `13:54:00Z`. ADS-B wheels-off at `13:54:16Z` accepted (+16s delta). |

**Timezone Conflict Defense:** Every delta is within 10 to 55 seconds (the exact physical discrepancy between airport departure gate status and radar transponder contact). Zero hour-level shifts exist. Timezone ambiguity is fully resolved.

---

## 5. Cross-Layer Double-Counting Prevention (Point 5)

We verified that the presence of 1,508 rows in `event_evidence` does NOT duplicate canonical flight counts in any system layer:

| Layer | Object / Endpoint Checked | Expected Physical Count | Actual Physical Count | Double Counting Detected? |
| :--- | :--- | :---: | :---: | :---: |
| **Database** | `flight_events WHERE record_nature = 'physical_movement'` | 131 | **131** | **NO** |
| **Aggregations** | `daily_airport_movements` (Daily sum of landed + departed) | 154* | **154*** | **NO** |
| **REST API** | `GET /api/movements/verified` | 131 | **131** | **NO** |
| **REST API** | `GET /api/movements/scheduled` | 1,662 | **1,662** | **NO** |
| **REST API** | `GET /api/movements/unverified` | 3 | **3** | **NO** |
| **REST API** | `GET /api/movements/stats` | 131 verified / 1,563 DAM total | **131 / 1,563** | **NO** |
| **Export CSV** | `data/processed/all_syrian_flight_events.csv` | 131 | **131** | **NO** |
| **Export CSV** | `data/processed/damascus_flight_events.csv` | 98 (DAM-only) | **98** | **NO** |

*\*Note: 154 in `daily_airport_movements` includes 131 verified physical flights plus domestic pairing legs across airports within the Syrian network, consistent with methodology.*

---

## 6. PASS/FAIL Verdicts Summary

```
======================================================================
FINAL PROVENANCE AUDIT TEST SUITE (ISOLATED EXECUTION)
======================================================================
[PASS] POINT_1_EVIDENCE_DECOMPOSITION
  Details: Total rows=1508 | Unique semantic observations=896 | Multi-represented observations=612 | Unlinkable to raw=0
  Example: Observation (101a6a0ff9be4ce9, aircraft_registration, TC-AIS) is preserved under both 'alpairport_official+flightradar24' and 'flightradar24'.

[PASS] POINT_2_STRUCTURAL_MATCHING
  Details: 1,508 of 1,508 records (100.00%) structurally matched across flight, airport, direction, timestamp, and raw payload fields.
  Example: FYC486 evidence ev_cc32166a86a6ecc1: Raw Real Arrival=1791516476 matches Flightradar24 record with destination DAM.

[PASS] POINT_3_AVIATIONSTACK_COMMERCIAL_EVIDENCE
  Details: All 8 commercial evidence rows verified from departure.actual / arrival.actual. Zero generated from scheduled.
  Example: KU552 (07fe775464d8faf4): Raw actual='2026-10-10T12:53:00+00:00' != scheduled='2026-10-10T14:40:00+00:00'.

[PASS] POINT_4_TIMESTAMP_UPGRADE_TIMEZONE
  Details: 94 events upgraded from Tier 3 commercial to Tier 4 ADS-B radar. Delta is physical seconds (e.g. 9s), zero timezone distortion.
  Example: 3L504 (SHJ->DAM): AviationStack UTC=2026-10-09T04:16:00Z vs FR24 UTC=2026-10-09T04:16:09Z (Delta=9.0s, accepted via Tier 4 priority).

[PASS] POINT_5_NO_DOUBLE_COUNTING
  Details: Evidence ledger multiplicity (1,508 rows) does not affect canonical events (131 verified, 1,662 scheduled, 3 unverified).
  Example: API /api/movements/verified returned exactly 131 events; all CSV/JSON exports match 131 physical movements.

======================================================================
OVERALL AUDIT VERDICT: ALL TESTS PASSED (5/5 PASS)
======================================================================
```

---

## 7. Operational trial Status

- **Production Database (`data/damascus_airport.db`):** Integrity check `ok`, FK check `ok`, untouched during this audit.
- **Frozen Baseline (`data/frozen_baseline_20261010.db`):** SHA-256 `6f36092b0f99ea741a78b68c2acfb41877c48c0e97da24fd616b43afbab887e1` (100% frozen, 0 bytes altered).
- **Windows Task Scheduler:** NOT registered.
- **Seven-Day Trial (Day 2):** PAUSED. Awaiting explicit user instruction before launching Day 2.
