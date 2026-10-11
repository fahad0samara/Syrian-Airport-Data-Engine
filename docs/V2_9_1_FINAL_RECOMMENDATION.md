# Syrian Airport Data Engine — Version 2.9.1
# Strategic Recommendations & Final Decision Synthesis

**Document Identifier**: `docs/V2_9_1_FINAL_RECOMMENDATION.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Audit Standard**: Empirical Fact Verification, Provenance Enforcement & Non-Fabrication  
**Status**: APPROVED FINAL RECOMMENDATIONS  

---

## 1. Executive Summary

Version 2.9.1 conducted a comprehensive evidence verification and claims audit of the historical aviation research developed in Version 2.9. 

The audit succeeded in:
1. **Validating Sovereign Ground Truth**: Authenticating the 2025 annual benchmarks (12,476 flights, 1,434,998 passengers) and 2026 monthly benchmarks (Sep, Jul, May, Apr) from primary dispatches of the Syrian Civil Aviation Authority and SANA.
2. **Correcting Imprecise Estimates**: Correcting April 2026 figures from an estimated `~350–400 flights` and `>34,000 passengers` to the exact primary figures of **492 flights** and **34,347 passengers**.
3. **Rectifying API Semantics**: Correcting the claim that all 1,393 records from `damairport.gov.sy/api/flights.php` were "active operational flights", proving that 55.6% are future scheduled flights and 99.35% carry the status `scheduled`.
4. **Rejecting Synthetic Disaggregation**: Formally rejecting the proposal to apply an assumed static 75% multiplier to the 2024 World Bank SEM dataset (`DAM_ALP_LTK`), preserving raw composite integrity.
5. **Documenting Historical Transitions**: Verifying the operational cessation on December 8, 2024, domestic restart on December 18, 2024, and international resumption on January 7, 2025 across primary NOTAMs and dispatches.

---

## 2. Definitive Answers to the Five Core Strategic Questions

### Question 1: Which 2025 and 2026 statistics are genuinely verified?
**Answer:**
1. **Calendar Year 2025 (Full Year)**:
   - Total Commercial Flights: **12,476 flights** (`verified_primary`).
   - Total Passengers: **1,434,998 passengers** (`verified_primary`).
   - Arriving Passengers: **715,392 passengers** (`verified_primary`).
   - Departing Passengers: **719,606 passengers** (`verified_primary`).
   - H1 2025 (Jan 7 – Jul 7): **1,870 flights** (1,619 passenger, 159 delegation, 66 Hajj, 26 relief) and **353,282 passengers** (178,728 arr, 174,554 dep) (`verified_primary`).
   - *(Note: H2 figures of 10,606 flights and 1.08M pax are mathematically verified remainders, not an independent SCAA bulletin).*
2. **Calendar Year 2026 (Monthly Benchmarks)**:
   - **September 2026**: **2,022 flights**, **229,693 passengers** (98,693 arr, 131,000 dep), **17 operating airlines**, **19,951 airspace transit overflights** (`verified_primary`).
   - **July 2026**: **2,088 flights**, **243,260 passengers** (147,318 arr, 95,942 dep), **16 operating airlines** (`verified_primary`).
   - **May 2026**: **1,532 flights**, **148,305 passengers** (83,357 arr, 64,948 dep), **13 operating airlines** (`verified_primary`).
   - **April 2026**: **492 flights**, **34,347 passengers** (18,385 arr, 15,962 dep), **9 operating airlines**, **2,523 airspace transit overflights** (`verified_primary`).

---

### Question 2: Which statistics refer specifically to Damascus Airport?
**Answer:**
- **100% DAM-Specific**:
  - The 2025 full-year totals (12,476 flights, 1,434,998 passengers) refer **specifically and exclusively to Damascus International Airport (`DAM` / `OSDI`)**.
  - The H1 2025 bulletin (1,870 flights, 353,282 passengers) refers specifically to Damascus Airport.
  - The 2026 monthly dispatches (April, May, July, September) refer specifically to Damascus Airport.
  - The official airport API (`damairport.gov.sy/api/flights.php`) refers specifically to Damascus Airport.
- **NOT DAM-Specific (Composite or National)**:
  - The 2024 World Bank SEM dataset in our database (`historical_daily_movements_2024`) refers to **`DAM_ALP_LTK` (a 3-airport composite)**.
  - SCAA overflight counts (19,951 in Sep 2026; 2,523 in Apr 2026) refer to national Syrian airspace (`OSTT` FIR), not airport runway movements.
  - Central Bureau of Statistics (CBS) post-2011 annual abstract transport tables aggregate civil aviation nationally.

---

### Question 3: Which claims in V2.9 must be corrected or removed?
**Answer:**
1. **CORRECT**: The claim that all 1,393 records returned by `damairport.gov.sy/api/flights.php` were "active operational flights staged". **Correction**: 774 records (55.6%) are forward scheduled flights for Oct 12–31, 2026; 1,384 records (99.35%) have status `scheduled`. Only 6 are cancelled. They represent an operational FIDS board, not 1,393 executed landings/takeoffs.
2. **REMOVE / RETRACT**: The proposal to disaggregate daily 2024 SEM records using an assumed 75% Damascus multiplier. **Correction**: Static ratio disaggregation is rejected. SEM must remain in its pure multi-airport scope (`DAM_ALP_LTK`).
3. **CLARIFY**: The claim that H2 2025 had an independent SCAA report of 10,606 flights. **Correction**: SCAA published H1 (1,870) and Full Year (12,476). H2 (10,606) is a calculated remainder.
4. **CORRECT**: April 2026 flight volume reported as `~350–400 flights` and `>34,000 passengers`. **Correction**: Primary SCAA dispatches report exact figures: **492 flights** and **34,347 passengers**.

---

### Question 4: What historical information can we safely add to the engine?
**Answer:**
The following datasets meet all evidentiary and provenance standards and can safely be staged:
1. **Macro Operational Benchmarks**: Ingest authenticated SCAA annual (2025) and monthly (Apr, May, Jul, Sep 2026) flight and passenger figures into a dedicated `macro_airport_benchmarks` table.
2. **Historical Milestone Chronicle**: Formalize authenticated operational dates (Dec 8, 2024 closure; Dec 18, 2024 domestic restart; Jan 7, 2025 international restart; Apr 8, 2026 corridor reopening) into an `aerodrome_operational_status` ledger.
3. **Rolling Airport Flight Board Archiving**: Ingest the 1,393 flight records from `damairport.gov.sy/api/flights.php` into `raw_source_records` with raw JSON and SHA-256 hashes, categorizing past flights as `commercial_schedule_only` and forward flights as `future_schedule`.
4. **Commercial Carrier Timetable Baselines**: Assemble published seasonal schedules from SyrianAir and Cham Wings into a segregated `commercial_schedules` baseline.

---

### Question 5: What remains unavailable without paid or restricted sources?
**Answer:**
- **Flight-by-Flight Historical Telemetry**: Individual historical flight numbers, airframe tail registrations (e.g. `YK-AKB`), Mode-S hexes, and exact wheels-off/wheels-down timestamps for the 1,003 gap days (Jan 1, 2024 to Sep 29, 2026) remain **unavailable in free public datasets**.
- **Terrestrial Ground Radar at Damascus**: Due to Anti-Lebanon mountain shadowing and the absence of volunteer feeders, crowdsourced networks (OpenSky, ADS-B.lol, ADSB.fi) have zero low-altitude terminal data for Damascus.
- **Obtaining Physical Historical Telemetry**: Requires either:
  1. Accessing commercial space-based ADS-B archives (FlightAware AeroAPI / Aireon).
  2. Obtaining commercial historical radar logs (Flightradar24 Developer API).
  3. Ingesting internal airline dispatch logs from SyrianAir or Cham Wings.

---

## 3. Recommended Safe Implementation Roadmap

```mermaid
flowchart TD
    subgraph Phase 1: Macro Benchmarking (Zero Cost)
        M1[Create macro_airport_benchmarks table in staging]
        M2[Ingest 2025 Annual: 12,476 flights | 1,434,998 pax]
        M3[Ingest 2026 Monthly: Apr, May, Jul, Sep authenticated numbers]
    end

    subgraph Phase 2: Airport Board Ingestion (Zero Cost)
        A1[Archive damairport.gov.sy/api raw JSON with SHA-256]
        A2[Ingest 1,393 records into commercial_schedules / flight_events]
        A3[Classify 774 future flights as future_schedule]
        A4[Classify 558 past flights as commercial_schedule_only]
    end

    subgraph Phase 3: Airline Timetable Baseline (Zero Cost)
        T1[Compile SyrianAir & Cham Wings seasonal timetables]
        T2[Populate scheduled intention baseline across 1,003 gap days]
    end

    subgraph Phase 4: Precision Sample Audit (Controlled Pilot)
        P1[Acquire 8-date evaluation sample from FlightAware AeroAPI]
        P2[Calibrate timetable baselines against space-based Aireon radar]
    end

    M1 --> M2 --> M3
    A1 --> A2 --> A3 --> A4
    T1 --> T2
    P1 --> P2
```

### Immediate Action Plan:
1. **Maintain Production Isolation**: Keep `data/damascus_airport.db` completely read-only (`mode=ro`).
2. **Execute Staging Implementation**: Build staging scripts to populate `macro_airport_benchmarks` and `commercial_schedules` within an isolated staging database.
3. **No Unverified Data**: Never inject assumed percentages or unverified estimates into movement counts.

This concludes the Version 2.9.1 Evidence Verification and Claims Audit.
