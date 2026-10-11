# Syrian Airport Data Engine — Version 2.13
# Historical Recovery Roadmap & Phased Execution Plan

**Document Identifier**: `docs/V2_13_HISTORICAL_RECOVERY_ROADMAP.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Target Airspace**: Damascus Flight Information Region (`OSTT_FIR`)  
**Scope**: Phased Strategic Execution Roadmap for Historical Aviation Data Recovery (2024–2026)  
**Status**: APPROVED RECOVERY ARCHITECTURE SPECIFICATION  
**Production Integrity Invariant**: `data/damascus_airport.db` SHA-256 verified identical (`c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`).

---

## 1. Executive Summary & Architectural Principles

The Historical Recovery Roadmap establishes a disciplined, four-phase engineering framework to systematically eliminate the 34-month historical coverage vacuum for Damascus International Airport (`DAM` / `OSDI`).

The roadmap is strictly governed by the architectural and evidentiary principles formulated across Versions 2.9 through 2.12.2:

1. **Strict Separation of Data Layers**: Individual flight events (`flight_events`) and aggregate monthly/annual benchmarks (`macro_airport_benchmarks`) must never be intermingled. Aggregate totals must never be synthesized into artificial daily flights.
2. **Category-Aware Ingestion**: Data must be stored in its exact semantic category (verified physical movements vs. commercial schedules vs. macro aggregates vs. FIR transit overflights).
3. **No Synthetic Multipliers**: Disaggregation of multi-airport composites (such as the World Bank SEM `DAM_ALP_LTK` series) using assumed percentage splits (e.g. 75%) is prohibited.
4. **Verifiable Provenance**: Every ingested record must maintain immutable cryptographic traceability to an archived primary document, raw JSON payload, or verified CDX crawl timestamp.
5. **Zero Disruption to Production**: The production database `data/damascus_airport.db` remains strictly protected by cryptographic hash verification gates at all milestones.

---

## 2. Four-Phase Phased Recovery Timeline

```
+---------------------------------------------------------------------------------------+
| PHASE 0: Non-Invasive Open Archive Harvesting (P0)                                   |
| - Target: Wayback Machine CDX API (damairport.gov.sy, SyrianAir, Cham Wings)          |
| - Cost: $0.00 | Outreach: None | Deliverable: Staged Historical Timetables (2024-2026) |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
| PHASE 1: Sovereign Macro Evidence Retrieval (P1)                                      |
| - Target: SCAA Annual Reports & Monthly Gazettes (Elevate Grade C to Grade A)         |
| - Cost: $0.00 | Outreach: Public Repositories | Deliverable: Verified Macro Benchmarks|
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
| PHASE 2: OpenSky Academic Institutional Partnership (P4)                              |
| - Target: OpenSky Trino/Impala Historical Database (OSTT_FIR Overflights)             |
| - Cost: $0.00 | Outreach: Academic Sponsoring University | Scope: High-Altitude FIR   |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
| PHASE 3: Commercial Telemetry Procurement Pilot (P3)                                  |
| - Target: FlightRadar24 Business Subscription (~$499/yr)                             |
| - Cost: ~$499 | Prerequisite: Project Sponsor Budget Approval | Scope: 365-Day History |
+---------------------------------------------------------------------------------------+
```

---

## 3. Phase Specifications

### 3.1 Phase 0: Non-Invasive Open Archive Harvesting
- **Priority**: **P0 (Highest / Immediate Execution)**
- **Timeline**: Milestone V2.14 (Weeks 1–2).
- **Financial Cost**: **$0.00**.
- **External Communication**: **Zero**. Operates exclusively against public open web archives.
- **Objectives**:
  1. Build an automated Wayback Machine CDX harvester in `scripts/harvest_wayback_timetables.py`.
  2. Query `https://web.archive.org/cdx/search/cdx` for all snapshots of:
     * `damairport.gov.sy/*`
     * `syrianair.com/*`
     * `chamwings.com/*`
  3. Parse raw JSON and HTML snapshots into a dedicated staging table: `historical_archived_timetables`.
  4. Recover flight numbers, scheduled departure/arrival times, operating airlines, and destination cities for 2024–2026.
- **Key Risks & Mitigation**:
  * *Risk*: Archival crawler frequency may be irregular.
  * *Mitigation*: Combine multiple crawl targets (airport FIDS, airline booking engines, regional news updates) to build overlapping schedule matrices.

### 3.2 Phase 1: Sovereign Macro Evidence Retrieval
- **Priority**: **P1 (Authoritative Macro Ground Truth)**
- **Timeline**: Milestone V2.15 (Weeks 3–4).
- **Financial Cost**: **$0.00**.
- **External Communication**: Non-invasive retrieval of publicly indexed official government gazettes, SCAA publications, and Ministry of Transport bulletins.
- **Objectives**:
  1. Locate and download original PDF / official publications for the 31 macro benchmarks currently staged at Grade C.
  2. Store primary digital artifacts in `data/sources/scaa/` and record cryptographic SHA-256 hashes in `macro_sources`.
  3. Promote validated benchmark records from `Grade C` (`unverified_quoted`) to `Grade A` (`verified_primary`).
  4. Formally resolve the April 2026 operational reporting window (`GAP-2026-M04`).
- **Key Risks & Mitigation**:
  * *Risk*: Sovereign websites may have broken permalinks or geo-blocking.
  * *Mitigation*: Utilize cached copies in national digital archives, academic repositories, and international trade press archives.

### 3.3 Phase 2: OpenSky Academic Institutional Partnership
- **Priority**: **P4 (Academic Research Pipeline)**
- **Timeline**: Milestone V2.16 (Weeks 5–8).
- **Financial Cost**: **$0.00** (Academic tier).
- **External Communication**: Submission of the existing V2.6 academic research application package through an accredited university partner.
- **Objectives**:
  1. Establish authorized institutional credentials with the OpenSky Network Association.
  2. Query the OpenSky historical Impala/Trino database for spatial bounding box `[32.0, 35.0, 37.5, 42.5]` covering the Damascus FIR (`OSTT_FIR`).
  3. Populate a dedicated `national_airspace_overflights` table to benchmark en-route Levant traffic trends from 2024 through 2026.
- **Key Risks & Mitigation**:
  * *Risk*: The Damascus ground receiver vacuum (proven in V2.7) prevents OpenSky from observing runway touchdowns.
  * *Mitigation*: Explicitly scope OpenSky data to **airspace transit metrics (`OSTT_FIR`)** and never classify high-altitude vector disappearances as verified Damascus landings.

### 3.4 Phase 3: Commercial Telemetry Procurement Pilot
- **Priority**: **P3 (Commercial Acquisition Pilot)**
- **Timeline**: Milestone V2.17+ (Subject to budget authorization).
- **Financial Cost**: **~$499/year** (Standard Business plan).
- **External Communication**: Standard commercial checkout / procurement.
- **Objectives**:
  1. Procure a 1-year FlightRadar24 Business subscription.
  2. Ingest rolling 365-day historical airport arrival and departure logs for OSDI.
  3. Extract transponder-confirmed airframe registrations (`YK-AKA`, etc.), actual wheels-off/wheels-down timestamps, and callsigns.
  4. Validate against satellite ADS-B and MLAT coverage indicators.
- **Key Risks & Mitigation**:
  * *Risk*: Commercial licensing prohibits committing raw commercial data dumps into public open repositories.
  * *Mitigation*: Store raw commercial payloads in local git-ignored directories (`data/commercial_raw/`) and ingest derived, aggregated, or anonymized metrics with proper commercial attribution.

---

## 4. Architectural Safeguards & Quality Controls

To ensure that historical data recovery maintains total mathematical and database integrity, all future pipeline implementations must conform to five non-negotiable rules:

| Safeguard ID | Rule Name | Specification |
|---|---|---|
| **SAFE-01** | Production Hash Invariant | Any script modifying the database must check and verify SHA-256 before and after execution. |
| **SAFE-02** | Layer Isolation | Macro airport benchmarks (`macro_airport_benchmarks`) and individual flight events (`flight_events`) must remain in separate tables. |
| **SAFE-03** | No Synthetic Multipliers | The SEM `DAM_ALP_LTK` daily series must never be scaled by 0.75 or any other hypothetical split. |
| **SAFE-04** | Timestamp Integrity | `actual_arr_time` and `actual_dep_time` may only be populated when radar/transponder ground sensors confirm the event; scheduled times must remain strictly in `scheduled_time`. |
| **SAFE-05** | Provenance Immutability | Every historical record must reference a verifiable source ID, retrieval method, and original artifact hash. |

---

## 5. Milestone Delivery Summary

- **V2.13 (Current)**: Historical Coverage Gap Analysis, Source Inventory, Comparison Matrix, and Recovery Roadmap.
- **V2.14 (Next)**: Phase 0 Execution — Wayback Machine CDX harvester for historical Damascus FIDS timetables and airline schedules.
- **V2.15**: Phase 1 Execution — Sovereign SCAA/MoT primary artifact acquisition and macro benchmark elevation to Grade A.
- **V2.16**: Phase 2 Execution — OpenSky academic partnership submission for Levant airspace overflight quantification.
- **V2.17**: Phase 3 Evaluation — Decision gate on commercial FlightRadar24 subscription procurement.
