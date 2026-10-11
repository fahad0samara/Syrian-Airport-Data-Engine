# Syrian Airport Data Engine — Version 2.13
# Historical Coverage Gap Analysis (2024-01-01 to Present)

**Document Identifier**: `docs/V2_13_HISTORICAL_COVERAGE_GAP_ANALYSIS.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Target Airspace**: Damascus Flight Information Region (`OSTT_FIR`)  
**Scope**: Chronological Coverage Audit, 6-Category Data Classification, and Physical Telemetry Root-Cause Analysis  
**Machine-Readable Twin**: `reports/v2_13_coverage_gaps.csv`  
**Status**: APPROVED BASELINE GAP SPECIFICATION  
**Production Integrity Invariant**: `data/damascus_airport.db` SHA-256 verified identical (`c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`).

---

## 1. Executive Summary & Audit Mandate

Damascus International Airport (`DAM` / `OSDI`) serves as Syria's primary aviation gateway. However, a rigorous audit of the Syrian Airport Data Engine's database reveals that **the repository currently possesses zero verified flight-level physical movements for the entire period from 2024-01-01 through 2026-09-29**.

The current production flight table (`flight_events`) contains exactly 1,830 rows, all concentrated in a 32-day snapshot window from `2026-09-30` to `2026-10-31`. Furthermore:
- Only **207** rows represent actual movement observations with confirmed touchdown/takeoff timestamps.
- **1,623** rows represent scheduled flights (predominantly future operations).
- In the historical daily coverage matrix (`historical_coverage_matrix`), out of 5,175 tracked airport-calendar cells, **5,078 are classified as `unverified_data_gap` (98.1%)**.
- Only 5 calendar days have verified movement coverage for DAM.

The objective of Version 2.13 is to perform an exhaustive, evidence-based technical assessment of why this gap exists, how the historical timeline from 2024-01-01 to the present breaks down across six distinct data categories, and the physical engineering factors governing data availability in Syrian airspace.

---

## 2. Six Standard Data Categories

To prevent conflation of distinct aviation phenomena (a critical integrity rule established in V2.10–V2.12.2), all aviation information across the target period is categorized into six mutually exclusive types:

1. **Verified Physical Movements**: Transponder- or radar-confirmed runway operations (touchdown / wheels-off) with verifiable timestamps (`actual_arr_time` / `actual_dep_time`), verified ICAO 24-bit transponder hex addresses, and ground-track continuity.
2. **Commercial Schedules**: Published timetables and Flight Information Display Systems (FIDS) indicating airline intent, published flight numbers, origin/destination pairs, and scheduled departure/arrival times (`scheduled_time`). These do not prove physical operation.
3. **Unverified Movement Observations**: Crowdsourced receiver detections in Syrian airspace lacking terminal approach fixes, multilateration (MLAT) lock below 3,000 ft AGL, or physical confirmation of aerodrome landing.
4. **Aggregate Airport Statistics**: Official macro statistics published by aerodrome authorities (SCAA, MoT) reporting aggregate monthly or annual flight totals, passenger throughput, and cargo tonnage. These provide macro totals without individual flight records.
5. **National Airspace Statistics**: Overflight transit movements transiting the Damascus Flight Information Region (`OSTT_FIR`) without landing or departing at Syrian aerodromes.
6. **Unknown / Unavailable Data**: Complete operational and statistical vacuums where neither individual flights nor aggregate statistical bulletins are recorded.

---

## 3. Chronological Period Breakdown (14 Discrete Intervals)

The 34-month historical span (`2024-01-01` to `2026-10-31`) is divided into 14 distinct chronological intervals based on operational milestones, geopolitical events, and source boundaries:

| Period ID | Start Date | End Date | Days | Verified Physical | Commercial Schedules | Unverified Obs. | Aggregate Airport Stats | National Airspace Stats | Unknown / Vacuum | Coverage State | Feasibility |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **GAP-2024-P1** | 2024-01-01 | 2024-10-15 | 289 | 0 | 0 | 0 | 578 | 0 | 0 | `aggregate_composite_only` | Medium |
| **GAP-2024-P2** | 2024-10-16 | 2024-12-07 | 53 | 0 | 0 | 0 | 0 | 0 | 53 | `complete_gap` | Low |
| **GAP-2024-P3** | 2024-12-08 | 2024-12-17 | 10 | 0 | 0 | 0 | 0 | 0 | 10 | `complete_gap` | Low |
| **GAP-2024-P4** | 2024-12-18 | 2025-01-06 | 20 | 0 | 0 | 0 | 0 | 0 | 20 | `complete_gap` | Medium |
| **GAP-2025-H1** | 2025-01-07 | 2025-07-07 | 182 | 0 | 0 | 0 | 1,870 | 0 | 182 | `aggregate_macro_only` | High |
| **GAP-2025-H2** | 2025-07-08 | 2025-12-31 | 177 | 0 | 0 | 0 | 12,476 | 0 | 177 | `aggregate_macro_only` | Medium |
| **GAP-2026-Q1** | 2026-01-01 | 2026-04-07 | 97 | 0 | 0 | 0 | 0 | 0 | 97 | `complete_gap` | Low |
| **GAP-2026-M04**| 2026-04-08 | 2026-04-30 | 23 | 0 | 0 | 0 | 492 | 2,523 | 23 | `aggregate_macro_only` | High |
| **GAP-2026-M05**| 2026-05-01 | 2026-05-31 | 31 | 0 | 0 | 0 | 1,532 | 0 | 31 | `aggregate_macro_only` | High |
| **GAP-2026-M06**| 2026-06-01 | 2026-06-30 | 30 | 0 | 0 | 0 | 0 | 0 | 30 | `complete_gap` | Medium |
| **GAP-2026-M07**| 2026-07-01 | 2026-07-31 | 31 | 0 | 0 | 0 | 2,088 | 0 | 31 | `aggregate_macro_only` | High |
| **GAP-2026-M08**| 2026-08-01 | 2026-08-31 | 31 | 0 | 0 | 0 | 0 | 0 | 31 | `complete_gap` | Medium |
| **GAP-2026-M09**| 2026-09-01 | 2026-09-29 | 29 | 0 | 0 | 0 | 2,022 | 19,951 | 29 | `aggregate_macro_only` | High |
| **GAP-2026-SNAPSHOT**| 2026-09-30 | 2026-10-31 | 32 | 207 | 1,623 | 3 | 1,563 | 0 | 0 | `active_snapshot_window` | High |

---

## 4. In-Depth Period Analysis

### 4.1 GAP-2024-P1: Pre-Transition Gateway Monitoring (2024-01-01 to 2024-10-15)
- **Duration**: 289 calendar days.
- **Current Repository State**: Contains 578 daily rows in `historical_daily_movements_2024` (289 arrival records, 289 departure records).
- **Core Constraint**: These records originate from the World Bank / Syria Economic Monitor dataset and are explicitly scoped to `DAM_ALP_LTK` (a composite metric combining Damascus, Aleppo, and Latakia airports).
- **Integrity Rule**: As established in V2.3 and V2.9, disaggregating this composite using an assumed multiplier (e.g. 75% for Damascus) is strictly prohibited as synthetic fabrication. Damascus-specific flight-level events are completely absent.
- **Recovery Potential**: Medium. Archival timetable reconstruction via Wayback Machine can recover Damascus scheduled operations.

### 4.2 GAP-2024-P2: Late Autumn Pre-Transition Vacuum (2024-10-16 to 2024-12-07)
- **Duration**: 53 calendar days.
- **Current Repository State**: Complete vacuum. Zero flight events, zero aggregate statistics.
- **Root Cause**: The World Bank SEM monitoring project terminated its daily publication on 2024-10-15. No institutional ingest pipeline was active during this period.
- **Recovery Potential**: Low. Requires commercial historical aggregators (FlightRadar24, FlightAware) or historical timetable web archives.

### 4.3 GAP-2024-P3: Emergency Airspace Suspension (2024-12-08 to 2024-12-17)
- **Duration**: 10 calendar days.
- **Current Repository State**: Complete vacuum in database.
- **Operational Reality**: Damascus International Airport operations were officially halted following major political transition and emergency NOTAM issuances. Commercial schedules dropped to zero.
- **Recovery Potential**: Low. Evacuation, humanitarian, and diplomatic flights operated ad-hoc; transponder records require military/state or raw unscrubbed ADS-B logs.

### 4.4 GAP-2024-P4: Domestic Resumption & Pre-International Resumption (2024-12-18 to 2025-01-06)
- **Duration**: 20 calendar days.
- **Current Repository State**: Complete vacuum in database.
- **Operational Reality**: On 2024-12-18, Syrian domestic flights resumed between Damascus and Aleppo (SyrianAir). International commercial services remained suspended until 2025-01-07.
- **Recovery Potential**: Medium. Airline domestic schedules and state announcements can verify specific flight operations.

### 4.5 GAP-2025-H1: SCAA 6-Month Post-Resumption Milestone (2025-01-07 to 2025-07-07)
- **Duration**: 182 calendar days.
- **Current Repository State**: 1,870 flights and 353,282 passengers staged as macro benchmarks in `data/macro_benchmarks_staging.db` (Grade C). Zero daily flight events in `flight_events`.
- **Evidence Character**: Originates from an official SCAA press conference on 2025-07-08 breaking down flights into: 1,619 passenger, 159 delegation/state, 66 Hajj pilgrim, and 26 humanitarian relief flights.
- **Recovery Potential**: High for macro validation (locating primary SCAA PDF); Medium for flight-level recovery via Wayback Machine FIDS.

### 4.6 GAP-2025-H2: Second Half Operational Expansion (2025-07-08 to 2025-12-31)
- **Duration**: 177 calendar days.
- **Current Repository State**: Represented only through the annual macro benchmark of 12,476 flights and 1,434,998 passengers. Zero daily flight events.
- **Critical Integrity Rule (V2.9.3)**: Subtracting H1 from the annual figure yields 10,606 flights (`annual_minus_reported_period_remainder`). This remainder cannot be labeled "H2 2025" because it contains missing dates from early January and does not represent an independently reported statistical period.
- **Recovery Potential**: Medium. Commercial data extracts or airline schedule archives.

### 4.7 GAP-2026-Q1: Infrastructure Rehabilitation Closure (2026-01-01 to 2026-04-07)
- **Duration**: 97 calendar days.
- **Current Repository State**: Complete vacuum.
- **Operational Reality**: Damascus airport was closed to scheduled international traffic for comprehensive runway, taxiway, and passenger terminal rehabilitation.
- **Recovery Potential**: Low. Commercial operations were zero; only special maintenance or state calibration flights occurred.

### 4.8 GAP-2026-M04: Commercial Reopening (2026-04-08 to 2026-04-30)
- **Duration**: 23 calendar days.
- **Current Repository State**: Staged macro benchmarks: 492 flights, 34,347 passengers, 2,523 overflights (Grade C). Zero flight events.
- **Period Semantics Rule (V2.12.1)**: Source quotes "في نيسان 2026" without explicit day numbers. The reporting period status is formally marked `unresolved_reopening_window`. Overflights (2,523) strictly represent `OSTT_FIR`, not Damascus airport runway movements.
- **Recovery Potential**: High. SCAA monthly bulletin retrieval.

### 4.9 GAP-2026-M05 to M09: Post-Reopening Monthly Operations (2026-05-01 to 2026-09-29)
- **May 2026**: 1,532 flights, 148,305 passengers staged (Grade C).
- **June 2026**: 30-day reporting vacuum. Zero staged records.
- **July 2026**: 2,088 flights, 243,260 passengers staged (Grade C).
- **August 2026**: 31-day reporting vacuum. Zero staged records.
- **September 2026 (1–29)**: 2,022 flights, 229,693 passengers, 19,951 overflights staged (Grade C).
- **Recovery Potential**: High for macro bulletin recovery; Medium for flight-level reconstruction.

### 4.10 GAP-2026-SNAPSHOT: Active Ingestion & Snapshot Window (2026-09-30 to 2026-10-31)
- **Duration**: 32 calendar days.
- **Current Repository State**: 1,830 rows in `flight_events` (207 actual movements, 1,623 scheduled flights).
- **Coverage State**: This is the only period in the entire project lifecycle with granular flight records.

---

## 5. Technical Root-Cause Analysis: The Damascus Ground Receiver Vacuum

A central finding of Version 2.7 live receiver tests and Version 2.8 collection experiments is the **complete absence of crowdsourced terrestrial ADS-B receivers within 50 km of Damascus International Airport**.

```
[ Aircraft at Cruise: FL300–FL400 ] ---------> Detected by receivers in Cyprus, Beirut, Amman
                 \
                  \ (Descent below FL150)
                   \
                    X  <-- Line-of-sight obstructed by Anti-Lebanon Mountain Range
                       \
                        \ (Terminal Approach: < 3,000 ft AGL)
                         \
                          v
               [ OSDI / DAM Runways ]  <-- ZERO ground receiver coverage (Signal Vacuum)
```

### 5.1 Physical and Line-of-Sight Limitations
1. **Radio Line of Sight (RLOS)**: 1090 MHz ADS-B signals travel strictly line-of-sight. The Anti-Lebanon Mountain Range (peaks exceeding 2,600 m / 8,500 ft) blocks low-altitude reception from terrestrial receivers located in Lebanon (OLBA) or the Mediterranean.
2. **Horizon Distance**: To receive an aircraft at runway level (elevation 616 m / 2,020 ft) in Damascus from Amman (Jordan, ~175 km distance), the radar horizon equation \(d \approx 3.57 (\sqrt{h_1} + \sqrt{h_2})\) requires receiver antenna heights unachievable in standard civilian setups.
3. **Absence of Local Feeder Nodes**: Due to ten years of conflict, international sanctions, and telecommunications import restrictions, volunteer ADS-B feeder communities (such as those supporting FlightRadar24, OpenSky Network, or ADS-B Exchange) have essentially zero active ground stations inside Damascus city or airport perimeter.

### 5.2 Consequence for Free ADS-B APIs
- OpenSky Network, ADS-B.lol, and ADSB.fi capture high-altitude overflights transiting the Damascus FIR (`OSTT_FIR`) above FL300.
- When an aircraft descends below approximately 12,000–15,000 ft on approach to OSDI, the transponder signal is lost.
- Consequently, **free open-source ADS-B networks cannot detect runway touchdowns, wheels-off events, or taxi operations at Damascus International Airport**.
- This physical constraint explains why empirical tests in V2.7 yielded 0 airport movements despite active airspace overflights.

---

## 6. Synthesis: The Three Paths Forward

Recovering historical data for DAM requires acknowledging that no single source provides 100% of flight-level physical telemetry:

1. **Macro Historical Coverage**: SCAA and Ministry of Transport statistical bulletins can provide verified monthly and annual airport totals (flights, passengers, airlines) across 2024–2026.
2. **Timetable / Schedule Recovery**: The Internet Archive / Wayback Machine contains historical snapshots of the official Damascus Airport FIDS portal (`damairport.gov.sy/api/flights.php`) and airline timetables (SyrianAir, Cham Wings). This can reconstruct flight numbers, airlines, routes, and scheduled times.
3. **Physical Telemetry Recovery**: Commercial aviation aggregators (FlightRadar24 Business/Enterprise or FlightAware AeroAPI) maintain space-based (satellite ADS-B) and multilateral tracking data capable of filling the terrestrial receiver vacuum, but require commercial procurement.
