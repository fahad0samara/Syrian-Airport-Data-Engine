# V2.19 — Data Product Integrity & Research Readiness Specification
## Syrian Airport Data Engine & Damascus International Airport Deep-Dive

**Document Version:** 2.19.0  
**Status:** Verified Research-Ready Baseline  
**Date:** October 2026  

---

## 1. Executive Mission & Integrity Invariants

The **Syrian Airport Data Engine** is an empirical, evidence-backed aviation data platform providing structured flight operations, scheduled timetables, and macro gateway statistics for Syrian aerodromes, with a forensic deep-dive layer for **Damascus International Airport (DAM / OSDI)**.

To serve as a reliable platform for academic research, civil aviation analysis, and economic monitoring, the platform operates under **six non-negotiable integrity invariants**:

1. **Strict Category Segregation:** Physical runway movements, scheduled timetable displays, regional multi-airport aggregates, and live regional ADS-B transponder fixes are maintained in disjoint data categories and **never combined into a single movement count**.
2. **Geographic Honesty:** Regional multi-airport aggregates (specifically the 2024 `DAM_ALP_LTK` gateway series) are never classified, presented, or disaggregated as Damascus-only statistics.
3. **No Synthetic Data:** Missing observations are strictly preserved as `no_verified_dam_data` or `unverified_data_gap`. No date or airport is ever zero-filled or synthesized.
4. **Physical Movement Evidence Gate:** Scheduled timetable records (FIDS) are never promoted to verified physical movements merely because an airport display reports "scheduled" or "arrived".
5. **Operating vs. Marketing Carrier Distinction:** Airline names on public flight boards represent commercial marketing brands, not certified Air Operator's Certificate (AOC) holders.
6. **Immutable Provenance:** Every record in the platform traces directly to an authentic source hash, URL, and timestamped raw artifact.

---

## 2. Core Data Categories

Every observation, API response, dashboard metric, and export record belongs strictly to one of the following six mutually exclusive categories:

| Data Category | Definition | Geographic Scope | Physical Evidence | Example in Engine |
|---|---|---|:---:|---|
| **`dam_verified_physical_movement`** | Aircraft runway takeoff or landing verified with direct on-ground radar sensor telemetry. Note: 98 canonical events in `flight_events` reflect commercial flight status updates from aggregator feeds; no ground-sensor radar telemetry currently exists in public archives. | DAM / OSDI | **Pending certified ground sensor** | 98 commercial events in `flight_events` (`record_nature = 'physical_movement'`) |
| **`dam_scheduled_fids`** | Official airport flight-information display board timetable listings. Represents published commercial slots, not physical movements. | DAM / OSDI | **NO** (0) | 1,982 records in `archived_fids_staging.db` (July–Sept 2026); 1,428 slots in canonical DB |
| **`regional_aggregate`** | Macro commercial aviation statistics aggregated across multiple airports or national gateways. Cannot be disaggregated to single aerodromes. | `DAM_ALP_LTK` (Damascus, Aleppo, Latakia combined) | **NO** (Macro only) | 578 daily rows in `historical_daily_movements_2024` (Syria Economic Monitor series) |
| **`live_regional_adsb`** | High-altitude overflight or regional transit transponder fixes captured by crowdsourced receivers in Levantine airspace. | Regional Airspace (96–142 km from DAM) | **NO** (0 DAM movements) | 16 live observations in `v2_18_staging.db` (15 overflights, 1 Beirut regional transit) |
| **`no_verified_dam_data`** | Historical calendar interval where no public, downloadable, flight-level, or verifiable telemetry has been recovered by this platform. **Always indicates an unrecovered data gap in platform archives; NEVER implies zero flights operated or airport closure.** | DAM / OSDI | **NO** (Unrecovered Data Gap) | 20 historical months: `2024-11` to `2024-12`, and `2025-01` to `2026-06` |
| **`unknown`** | Unaudited or unclassified records where provenance, direction, or operational completeness cannot be established. | Unspecified | **NO** | Replay-blocked Wayback captures (`HTTP 429`) where payload body was not retrieved |

---

## 3. Dataset Inventory & Provenance Catalog

The engine manages seven distinct empirical datasets:

```
                                    ┌────────────────────────────────────────────────────────┐
                                    │               Syrian Airport Data Engine               │
                                    └───────────────────────────┬────────────────────────────┘
                                                                │
                 ┌──────────────────────────────────────────────┴─────────────────────────────────────────────┐
                 │                                                                                            │
                 ▼                                                                                            ▼
┌─────────────────────────────────────────────────┐                                  ┌─────────────────────────────────────────────────┐
│     Layer A: Operational & Canonical Database   │                                  │      Layer B: Staging & Historical Archives     │
│             data/damascus_airport.db            │                                  │        data/archived_fids_staging.db, etc.      │
├─────────────────────────────────────────────────┤                                  ├─────────────────────────────────────────────────┤
│ • flight_events (1,830 canonical events)        │                                  │ • archived_fids_raw_records (1,982 records)     │
│ • daily_airport_movements (46 dates)            │                                  │ • archived_fids_normalized (1,982 records)      │
│ • damascus_daily_movements (32 dates)           │                                  │ • fids_analytics_records (1,982 records)        │
│ • historical_daily_movements_2024 (578 rows)    │                                  │ • recovered_observations (16 live fixes)        │
│ • airports (7 aerodromes)                       │                                  │ • monthly_dam_coverage (34 audit months)        │
│ • deduplication_audit (337 pairwise comparisons)│                                  │ • raw_snapshots (Wayback memento, S3 samples)   │
└─────────────────────────────────────────────────┘                                  └─────────────────────────────────────────────────┘
```

### Detailed Dataset Profiles:

#### 1. Damascus Deep-Dive Canonical Flight Events
- **Primary Table:** `flight_events` (where `airport_id = 'DAM'`)
- **Geographic Scope:** Damascus International Airport (DAM / OSDI)
- **Temporal Horizon:** `2026-09-30` to `2026-10-31`
- **Total Records:** 1,563 canonical events
- **Breakdown by Nature:**
  - `dam_verified_physical_movement`: 98 (commercial aggregator actual status timestamps from Flightradar24/AviationStack; pending certified ground-sensor radar telemetry)
  - `dam_scheduled_fids` (`scheduled_service`): 1,428 (published commercial timetable slots)
  - `marketing_codeshare`: 34 (commercial partner listings sharing a single aircraft)
  - `unverified_movement`: 3 (completed on flight board but lacking independent timestamp verification)
- **Source & Provenance:** Official Damascus Airport Flight Information Board (`https://damairport.gov.sy/api/flights.php`) and commercial aggregator feeds (Flightradar24, AviationStack).
- **Known Limitations:** Covers rolling operational schedule only; actual timestamps reflect aggregator commercial status updates rather than raw terminal ground-radar telemetry. Historical dates prior to 2026-09-30 not hosted on public live portal.

#### 2. All Syrian Aerodromes Canonical Flight Events
- **Primary Table:** `flight_events` (all airports)
- **Geographic Scope:** Damascus (DAM: 1,563), Aleppo (ALP: 261), Deir ez-Zor (DEZ: 6)
- **Temporal Horizon:** `2026-09-30` to `2026-10-31`
- **Total Records:** 1,830 canonical events
- **Breakdown by Nature:** Physical movements (131: 98 DAM, 32 ALP, 1 DEZ), scheduled services (1,662), codeshares (34), unverified (3).
- **Source & Provenance:** Official Syrian airport authority portals (`damairport.gov.sy`, `alpairport.gov.sy`, `qamishliairport.gov.sy`, `deirezzorairport.gov.sy`) and Flightradar24.
- **Known Limitations:** Qamishli (KAC) and Deir ez-Zor (DEZ) portals are responsive (HTTP 200) but currently publish zero active flight rows. Latakia (LTK) passenger movements are unpublished due to military/cargo restrictions.

#### 3. 2024 Syria Economic Monitor Commercial Air Traffic Gateway Series
- **Primary Table:** `historical_daily_movements_2024`
- **Geographic Scope:** `DAM_ALP_LTK` (Three-airport gateway aggregate across Damascus, Aleppo, and Latakia combined)
- **Temporal Horizon:** `2024-01-01` to `2024-10-15` (289 distinct calendar dates)
- **Total Records:** 578 daily rows (289 arrival rows + 289 departure rows)
- **Data Category:** `regional_aggregate`
- **Source & Provenance:** Syria Economic Monitor (World Bank / Data Partnership research notebooks, compiled via commercial AviationStack purchase).
- **CRITICAL RESEARCH LIMITATION:** This series represents combined Syrian commercial gateway operations. **Zero Damascus-specific disaggregated records exist in this series.** It CANNOT be used to calculate DAM-only daily or monthly totals, and zero portion can be allocated to Damascus.

#### 4. Archived Damascus FIDS Historical Timetable Snapshot
- **Primary Database:** `data/archived_fids_staging.db` & `data/archived_fids_analytics.db`
- **Geographic Scope:** Damascus International Airport (DAM / OSDI)
- **Temporal Horizon:** `2026-07-05` to `2026-09-09` (67 consecutive calendar dates)
- **Total Records:** 1,982 scheduled flight records (993 arrivals, 989 departures)
- **Monthly Distribution:** July 2026: 956 | August 2026: 886 | September 2026: 140
- **Data Category:** `dam_scheduled_fids`
- **Physical Movement Evidence Count:** **0** (Zero physical movements confirmed)
- **Source & Provenance:** Internet Archive Wayback Machine snapshot (`2026-07-09T23:42:30Z`) of `https://damairport.gov.sy/api/flights.php`. Raw payload preserved in `data/raw/snapshots/`.
- **Known Limitations:** Represents archived timetable displays as published on the airport web board on July 9, 2026. Displayed statuses (1,981 `scheduled`, 1 `arrived`) reflect web board displays, not physical radar tracking. Displayed airlines represent commercial marketing brands (e.g., Air Arabia, Flynas, Cham Wings), not operating carrier AOCs.

#### 5. Live Regional ADS-B Transponder Research Sample
- **Primary Table:** `recovered_observations` in `data/staging/v2_18/v2_18_staging.db`
- **Geographic Scope:** Regional Airspace (Levant; 96.2 km to 141.9 km from Damascus Airport)
- **Temporal Horizon:** `2026-10-11T13:30:00Z` to `2026-10-11T13:35:00Z`
- **Total Records:** 16 raw transponder observations (9 unique aircraft by ICAO24)
- **Data Category:** `live_regional_adsb`
- **Classification:** 15 high-altitude overflights (FL224–FL410 traversing regional airways); 1 regional transit operating in Lebanese airspace (Beirut OLBA).
- **DAM Airport Movements:** **0** (Zero approach candidates, zero departure candidates, zero airport surface movements).
- **Source & Provenance:** Public live queries from ADS-B.lol and ADSB.fi feeder networks.
- **Known Limitations:** Demonstrates sensor availability in neighboring airspace, but contains zero Damascus airport movements. Illustrates cross-provider sensor dependence (7 duplicate aircraft across lol and fi).

---

## 4. Geographic & Temporal Coverage Matrix (34 Months)

The 34-month historical audit window (`2024-01` to `2026-10`) is categorized as follows:

```
2024                                                    2025                       2026
Jan-Oct: regional_aggregate (DAM_ALP_LTK, 578 rows)    Jan-Dec: no_verified_dam   Jan-Jun: no_verified_dam
Nov-Dec: no_verified_dam_data (Series ended Oct 15)                                Jul-Sep: dam_scheduled_fids (1,982 rows)
                                                                                   Oct:     live_regional_adsb (16 fixes)
```

| Calendar Period | Months Count | Verified Category | Airport Scope | Verified DAM Movements | Can Claim DAM Historical Coverage? |
|---|:---:|---|---|:---:|:---:|
| **2024-01 to 2024-10** | 10 | `regional_aggregate` | `DAM_ALP_LTK` | **0** | **NO** (Gateway aggregate only) |
| **2024-11 to 2024-12** | 2 | `no_verified_dam_data` | `NONE` | **0** | **NO** (Source series ended 2024-10-15) |
| **2025-01 to 2026-06** | 18 | `no_verified_dam_data` | `NONE` | **0** | **NO** (Confirmed public data gap) |
| **2026-07 to 2026-09** | 3 | `dam_scheduled_fids` | `DAM / OSDI` | **0** | **NO** (Scheduled timetable displays only) |
| **2026-10** | 1 | `live_regional_adsb` | `REGIONAL_AIRSPACE` | **0** | **NO** (Live regional transponder sample) |

**Total Verified DAM Historical Physical Movements Recovered (2024–Present):** **0** (Zero).

---

## 5. API & Export Behavioral Semantics

All API endpoints and export handlers enforce strict semantic guarantees:

1. **Airport Filtering Is Strict:**
   - Querying `/api/flights?airport_id=DAM` guarantees that every returned event has `airport_id == 'DAM'`.
   - Querying `/api/movements/daily?airport_id=DAM` queries only Damascus records. It **never** injects rows from `historical_daily_movements_2024`.
2. **Regional Gateway Endpoints Declare Multi-Airport Scope:**
   - `/api/movements/historical-2024` and `/api/movements/multi-airport` return:
     - `"dataset_name": "Syria Economic Monitor 2024 Gateway Operations Time Series"`
     - `"scope": "DAM_ALP_LTK"`
     - `"included_airports": ["DAM", "ALP", "LTK"]`
     - `"data_category": "regional_aggregate"`
     - `"is_dam_specific": false`
     - `"warning": "The 2024 DAM_ALP_LTK series is a three-airport aggregate... Cannot be used as DAM-specific movement counts."`
3. **Movement Types Are Disjoint:**
   - `/api/movements/verified`: Contains only `record_nature = 'physical_movement'`.
   - `/api/movements/scheduled`: Contains only `record_nature = 'scheduled_service'`.
   - `/api/movements/unverified`: Contains only `record_nature = 'unverified_movement'`.
   - There is **zero overlap** among the three categories (disjoint sets of `event_id`).
4. **Archived FIDS Analytics Declares Timetable Semantics:**
   - All `/api/archived-fids/*` and `/api/historical-archive/*` responses include a mandatory semantic disclaimer:
     `"These records represent archived scheduled/displayed flight information, not verified physical aircraft movements."`
     and report `"physical_movement_evidence_count": 0`.
5. **Missing Values Remain NULL or Explicit Gaps:**
   - Missing actual times in `flight_events` remain `NULL`.
   - Provider outages in 2024 remain marked as `unverified_data_gap`.
   - Missing months remain classified as `no_verified_dam_data`.

---

## 6. What the Platform Can and Cannot Currently Claim

### What the Platform CAN Legally & Empirically Claim:

✔ **Current Operational Window (Oct 2026):** High-fidelity, multi-source canonical flight events for Damascus (1,563 events) and Aleppo (261 events) with commercial operation actual status timestamps (131 flights) cross-referenced from Flightradar24 and AviationStack aggregators.  
✔ **Archived Timetable Frequency (Jul–Sep 2026):** Exact scheduled service frequencies (1,982 flights), destination network, hourly distribution, and commercial airline brand distributions as published on Damascus Airport's official FIDS board across 67 consecutive calendar dates.  
✔ **Macro Gateway Trends (Jan–Oct 2024):** Daily operational status volumes (active, cancelled, diverted, landed, scheduled) for Syria's primary commercial aviation gateways (`DAM_ALP_LTK` combined).  
✔ **Aeronautical Infrastructure Baseline:** Verified runway dimensions, surface types, headings, and aerodrome coordinates for 7 Syrian airports based on the Syrian Civil Aviation Authority eAIP.  
✔ **Forensic Deduplication & Evidence Register:** 100% traceable pairwise deduplication audit trail (337 records) preserving ambiguous delta cases separately without synthetic merging.

### What the Platform CANNOT Claim:

✖ **NO Direct Ground-Radar Sensor Telemetry:** Commercial aggregator timestamps reflect airline operational status updates, not raw ADS-B transponder state vectors with onground=true captured by an independent Damascus runway sensor.  
✖ **NO Complete Historical Flight Log for Damascus:** The platform does NOT possess continuous, daily, flight-level historical records for Damascus International Airport prior to September 30, 2026.  
✖ **NO 2024 Damascus-Only Movement Statistics:** The 578 records in the 2024 series are a three-airport aggregate (`DAM_ALP_LTK`). They CANNOT be cited as Damascus-only flight movements.  
✖ **NO Physical Radar Verification for FIDS Records:** The 1,982 records in the archived FIDS snapshot are timetable displays; they CANNOT be cited as confirmed runway takeoffs or landings.  
✖ **NO Operating Carrier Certainty from Flight Boards:** Airline brands displayed on airport boards represent commercial marketing names; they do NOT prove which entity operated the aircraft under its AOC.  
✖ **NO Full Historical ADS-B Coverage:** Open-access ADS-B receiver archives do not maintain indexed historical flight-level coverage for Damascus airspace. The October 2026 crowdsourced ADS-B sample contains 16 regional/overflight fixes (15 high-altitude overflights, 1 Beirut transit) and zero Damascus surface or runway events.  
✖ **`no_verified_dam_data` NEVER Means Zero Flights or Airport Closure:** Denotes strictly an unrecovered historical data gap in platform archives, not airport closure.
