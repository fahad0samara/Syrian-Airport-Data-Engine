# Syrian Airport Data Engine — Version 2.9.2
# Final Strategic Recommendations & Epistemic Synthesis

**Document Identifier**: `docs/V2_9_2_FINAL_RECOMMENDATION.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Audit Standard**: Transparent Provenance, Epistemic Rigor & Zero Hallucination  
**Status**: APPROVED FINAL RECOMMENDATIONS  

---

## 1. Executive Summary & Epistemic Audit Transformation

Version 2.9.2 represents a decisive methodological upgrade for the Syrian Airport Data Engine. Rather than accepting broad claims attributed to official bodies, the engine now enforces **source URL traceability and single-fact claim decomposition**.

### Key Evidentiary Distinctions Established:
1. **Code-Test Verification $\neq$ Historical Source Verification**:
   - The test suite passing (141 / 141 tests, 100%) proves that our database schemas, foreign keys, deduplication triggers, and calculation functions operate correctly and safely without mutating production data.
   - It does **not** prove that historical flight movements occurred in the real world. Real-world physical flight movements require cryptographically traced primary evidence.
2. **Canonical Primary URLs $\neq$ Secondary News Aggregations**:
   - Only technical endpoints (`damairport.gov.sy/api/flights.php`, `datapartnership.org`, `eaip.gaca.gov.sy`) hold `verified_primary` status.
   - Claims naming SCAA or SANA that circulate in secondary news dispatches without a verifiable, direct canonical URL on `sana.sy` or `scaa.sy` are formally classified as `unverified_source_url`.
3. **Operational FIDS Display Boards $\neq$ Executed Landings/Takeoffs**:
   - The 1,393 records from `damairport.gov.sy` are passenger flight information display entries (FIDS), of which 55.6% are forward scheduled flights and 99.35% carry the status `scheduled`. They are **never** counted as completed physical movements.

---

## 2. Answers to the Core Strategic Questions

### Question 1: Which 2025 and 2026 statistics are genuinely verified?
**Answer:**
1. **Verified Primary (`verified_primary`)**:
   - Damascus Airport Live Operational API (`damairport.gov.sy/api/flights.php`):
     - `api_record_count`: **1,393 records**
     - `past_schedule_records`: **558 records** (dates < `2026-10-11`)
     - `current_schedule_records`: **61 records** (date `2026-10-11`)
     - `future_schedule_records`: **774 records** (dates > `2026-10-11`)
     - `cancelled_records`: **6 records**
     - `actual_movement_records`: **0 records**
     - **Cross-Tabulation (Date vs Display Status)**:
       | Date Classification | Total Records | `scheduled` | `cancelled` | `new-time` | `on-time` |
       | :--- | :---: | :---: | :---: | :---: | :---: |
       | **Past (< 2026-10-11)** | **558** | 553 (99.10%) | 2 (0.36%) | 2 (0.36%) | 1 (0.18%) |
       | **Today (= 2026-10-11)** | **61** | 57 (93.44%) | 4 (6.56%) | 0 (0.00%) | 0 (0.00%) |
       | **Future (> 2026-10-11)** | **774** | 774 (100.0%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) |
       | **Total** | **1,393** | **1,384 (99.35%)** | **6 (0.43%)** | **2 (0.14%)** | **1 (0.07%)** |
       *Critical Insight*: 99.10% of past-dated records retain the display status `scheduled`. A past date on this endpoint does NOT represent a completed flight; it represents a scheduled timetable slot whose calendar date has passed without status updating.
2. **Verified Secondary (`verified_secondary`)**:
   - H1 2025 Reported Period Bulletin (Jan 7 – Jul 7, 2025): **1,870 `total_reported_flights`** across 4 disaggregated categories:
     - Passenger flights: **1,619** (86.58%)
     - Official delegation flights: **159** (8.50%)
     - Seasonal Hajj pilgrimage flights: **66** (3.53%)
     - Humanitarian & relief flights: **26** (1.39%)
     - Total passengers: **353,282** (178,728 arr, 174,554 dep) across **12 airlines**, documented in reputable regional news coverage quoting SCAA.
   - Historical milestone dates: December 8, 2024 closure; December 18, 2024 domestic restart; January 7, 2025 international commercial resumption.
3. **Partially Verified / Derived Remainder (`partially_verified`)**:
   - `annual_minus_reported_period_remainder`:
     - Flights: **10,606 flights** ($12,476 - 1,870$)
     - Passengers: **1,081,716 passengers** ($1,434,998 - 353,282$)
     - Coverage Window: Explicitly covers **2025-01-01 through 2025-01-06** AND **2025-07-08 through 2025-12-31**.
     - Must NOT be called "H2 2025" unless an independent source establishes that the 6 missing January dates had zero activity or provides a dedicated H2 total.
4. **Unverified Source URLs (`unverified_source_url`)**:
   - 2025 Full-Year figures (12,476 flights, 1,434,998 passengers) and 2026 monthly figures (Sep, Jul, May, Apr) are widely quoted in economic news citing SCAA, but lack verifiable canonical article permalinks on `sana.sy` or raw PDFs on `scaa.sy`. Their scope is classified as `reported_as_DAM_pending_primary_source_verification`.

---

### Question 2: Which statistics refer specifically to Damascus Airport?
**Answer:**
- **Specifically DAM (`OSDI`)**:
  - The H1 2025 reported period bulletin (1,870 flights, 353,282 passengers).
  - The official airport API (`damairport.gov.sy/api/flights.php`).
- **Scope Qualified as `reported_as_DAM_pending_primary_source_verification`**:
  - The 2025 annual figures (12,476 flights, 1.43M pax) and 2026 monthly figures (Sep, Jul, May, Apr) in press dispatches quote SCAA for Damascus Airport, but because canonical primary URLs remain unverified, the scope is strictly held as `reported_as_DAM_pending_primary_source_verification`.
- **NOT Specifically DAM (National / Composite)**:
  - World Bank SEM dataset in our database (`historical_daily_movements_2024`) refers to **`DAM_ALP_LTK` (a 3-airport gateway composite)**.
  - SCAA overflight counts (19,951 in Sep 2026; 2,523 in Apr 2026) refer to national Syrian airspace (`OSTT` FIR), not Damascus runway operations.
  - Central Bureau of Statistics annual transport abstracts aggregate civil aviation nationally.

---

### Question 3: Which claims in V2.9 must be corrected or removed?
**Answer:**
1. **CORRECT**: The claim that all 1,393 records from `damairport.gov.sy/api/flights.php` were "active operational flights staged". **Correction**: Reclassified into `future_schedule_records` (774), `past_schedule_records` (558), and `cancelled_records` (6). Zero records represent confirmed radar touchdown telemetry.
2. **REMOVE / RETRACT**: The proposal to disaggregate 2024 SEM records using an assumed 75% Damascus multiplier. **Correction**: Formally rejected to prevent synthetic data fabrication.
3. **RECLASSIFY**: Reclassify all 2025 annual and 2026 monthly SCAA/SANA claims from `verified_primary` to `unverified_source_url` until direct, persistent primary URLs or hashed PDF bulletins are secured.
4. **SEMANTIC PERIOD CORRECTION**: Reclassify 10,606 flights and 1.08M pax from "H2 2025" to `annual_minus_reported_period_remainder`, explicitly documenting that it includes both 2025-01-01 to 2025-01-06 and 2025-07-08 to 2025-12-31.
5. **TERMINOLOGY CORRECTION**: Reclassify H1 2025 flights (1,870) from "commercial flights" to `total_reported_flights`, reflecting the inclusion of passenger, diplomatic delegation, Hajj, and relief flights.

---

### Question 4: What historical information can we safely add to the engine?
**Answer:**
The following data points meet all safety and evidentiary standards:
1. **Official Airport FIDS Schedule Feed**: Ingest the 1,393 records from `damairport.gov.sy/api/flights.php` into `raw_source_records` with raw JSON and SHA-256 hashes, categorizing past flights as `commercial_schedule_only` and forward flights as `future_schedule`.
2. **Historical Milestones Ledger**: Record the verified transition dates (Dec 8, 2024 closure; Dec 18, 2024 domestic restart; Jan 7, 2025 international restart) in an `aerodrome_operational_status` chronicle.
3. **H1 2025 Operational Benchmark**: Record H1 2025 totals (1,870 flights, 353,282 pax) in `macro_airport_benchmarks` tagged as `verified_secondary`.
4. **Multi-Airport 2024 Control Baseline**: Maintain the 578 World Bank SEM records strictly under scope `DAM_ALP_LTK` as a multi-airport gateway envelope.

---

### Question 5: What remains unavailable without paid or restricted sources?
**Answer:**
- **Flight-by-Flight Historical Telemetry**: Individual flight numbers, airframe tail registrations (e.g. `YK-AKB`), Mode-S hexes, and exact wheels-off/wheels-down timestamps across the 1,003 gap days (Jan 1, 2024 to Sep 29, 2026). No suitable historical flight-level dataset has been successfully acquired from the free sources tested so far.
- **Terrestrial Ground Observations at Damascus**: No low-altitude or near-airport observations were captured during the tested collection windows. The cause remains undetermined (could be lack of feeders, terrain obstruction, transmitter silencing, or API filtering).
- **Primary Sovereign Statistical PDFs**: Raw, cryptographically verified PDFs for SCAA Annual Statistical Bulletins (2024–2025) and Ministry of Transport Annual Follow-up Reports remain unarchived in the repository.

---

## 3. Automated Evidence Register Summary

The finalized, machine-readable register (`reports/v2_9_2_evidence_register.json`) establishes the following audited status distribution:

```text
================================================================================
FINAL EVIDENCE STATUS RECALCULATION (48 CLAIMS)
================================================================================
- unverified_source_url : 27 claims (56.25%)
- verified_primary      :  9 claims (18.75%)
- verified_secondary    :  8 claims (16.67%)
- partially_verified    :  2 claims  (4.17%)
- contradicted          :  2 claims  (4.17%)
- unverified            :  0 claims  (0.00%)
================================================================================
```

---

## 4. Production Database & Code Verification

- **Production Database**: `data/damascus_airport.db`
- **Cryptographic Hash**: `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b` (Bit-for-bit exact).
- **Production Row Counts**: Completely unchanged across all 9 core tables.
- **Regression Test Suite**: **141 / 141 tests passing (100%)**.

This concludes the Version 2.9.2 Source URL and Claim-Level Verification Audit.
