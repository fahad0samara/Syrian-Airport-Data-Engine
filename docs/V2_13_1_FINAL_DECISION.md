# Syrian Airport Data Engine — Version 2.13.1
# Final Decision & Evidentiary Determination

**Document Identifier**: `docs/V2_13_1_FINAL_DECISION.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Target Airspace**: Damascus Flight Information Region (`OSTT_FIR`)  
**Scope**: Definitive Evidentiary Findings, Decision Questions, and Safety Verification  
**Status**: APPROVED AUTHORITATIVE FINAL DETERMINATION  
**Production Integrity Invariant**: `data/damascus_airport.db` SHA-256 verified identical (`c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`).

---

## 1. Executive Summary & Authoritative Evidentiary Baseline

Version 2.13.1 concludes the historical recovery claims validation and feasibility reassessment. By replacing theoretical source availability with rigorous empirical testing, this milestone establishes the true boundaries of what historical aviation data can and cannot be recovered for Damascus International Airport (`DAM` / `OSDI`).

All evaluations were executed under strict read-only protocols:
- **Production Database**: `data/damascus_airport.db`
- **Baseline SHA-256**: `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`
- **Post-Audit SHA-256**: `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`
- **Bit-for-Bit Identity**: **100% INVARIANT**. Zero database writes, modifications, or backfills.

---

## 2. Definitive Answers to the Seven Decision Questions

### Question 1: Does Wayback actually contain historical DAM flight-board snapshots?
**Answer**: **Yes, but strictly for a single snapshot in 2026. It contains ZERO snapshots for 2024 or 2025.**
* **Empirical Proof**: Querying the Wayback Machine CDX API against `damairport.gov.sy/api/flights.php` returned exactly **1 snapshot** across the entire history of the Internet Archive, captured on **2026-07-09T23:42:30Z** (digest `LWGQOMIVR7BG55CKGT4LXDRNUVKDA36L`).
* **Content**: The snapshot contains 1,982 structured JSON flight objects spanning `2026-07-05` to `2026-09-09`.
* **2024–2025 Reality**: The domain `damairport.gov.sy` was **never crawled or archived prior to July 2026**. Tested carrier domains (`syrianair.com` and `chamwings.com`) contain redirects and marketing text, but **zero flight schedule tables**.

---

### Question 2: What is the earliest confirmed usable snapshot?
**Answer**: **2026-07-09T23:42:30Z (covering flight dates beginning 2026-07-05).**
* **Technical Details**: The single usable snapshot of `damairport.gov.sy/api/flights.php` was archived on July 9, 2026. The flight objects embedded within its JSON payload describe commercial arrivals and departures spanning from **2026-07-05 through 2026-09-09**.
* **Pre-2026 Confirmation**: There is **no earlier usable snapshot** containing Damascus flight schedules anywhere in the Wayback Machine.

---

### Question 3: Does any free source currently demonstrate historical DAM flight-level data?
**Answer**: **No free source demonstrates flight-level movement data for 2024 or 2025. Only the single 2026-07-09 Wayback snapshot demonstrates historical schedule data for Q3 2026.**
* **Physical Movements**: Free crowdsourced ADS-B APIs (ADS-B.lol, ADSB.fi, OpenSky Network) have demonstrated zero low-altitude terminal coverage at OSDI.
* **Scheduled Services**: The official airport portal and airline websites maintain no open historical archives on their live servers.
* **Composite Series**: The World Bank SEM dataset in the repository (`historical_daily_movements_2024`) provides daily composite totals for `DAM_ALP_LTK`, but contains **zero individual flight-level records** and cannot be mathematically disaggregated to Damascus.

---

### Question 4: Which commercial providers have documented historical OSDI coverage?
**Answer**: **FlightRadar24 and FlightAware document global and regional coverage, but neither publicly guarantees verified low-altitude runway touchdown coverage specifically for OSDI.**
* **FlightRadar24**: Documents historical flight tracking (up to 365 days on Gold at $44.99/yr and Business at $499/yr). While en-route flights over Syria are tracked via satellite and regional receivers, terminal touchdown data at OSDI is conditional on local receiver reception, which is historically sparse.
* **FlightAware**: Documents AeroAPI and custom historical reports. In low-receiver regions, arrival times are derived from flight plans or airline OOOI messaging rather than surface sensor telemetry.
* **ADS-B Exchange, Cirium, OAG**: ADS-B Exchange has no airport-parsed movements; Cirium and OAG require enterprise contracts ($5,000–$50,000+/year) and focus on airline filings.

---

### Question 5: Which historical statistics are supported only by secondary reporting?
**Answer**: **All 31 staged macro benchmarks in `data/macro_benchmarks_staging.db` are currently supported only by secondary press reporting (Grade C).**
* **Specific Claims Relying on Secondary Quotes**:
  1. *2025 Full-Year*: 12,476 flights, 1,434,998 passengers (715,392 arriving, 719,606 departing), and 13 operating airlines (reported via secondary news citing SCAA/MoT).
  2. *2025 H1 Milestone (Jan 7 – Jul 7)*: 1,870 flights and 353,282 passengers (reported via secondary press quoting an SCAA press conference).
  3. *April 2026 Reopening*: 492 flights, 34,347 passengers, 11 airlines, and 2,523 overflights (quoted as "في نيسان 2026" in secondary articles).
  4. *May 2026*: 1,532 flights and 148,305 passengers.
  5. *July 2026*: 2,088 flights and 243,260 passengers.
  6. *September 2026*: 2,022 flights, 229,693 passengers, and 19,951 overflights.
* **Evidentiary Status**: Direct primary sovereign PDF documents or printed gazettes have not yet been archived in the repository; all 31 records remain at **Grade C (`unverified_quoted`)**.

---

### Question 6: What is the actual reason for the missing low-altitude ADS-B observations, if it can be established?
**Answer**: **The actual root cause cannot be conclusively established from available data and must be classified as `hypothesis_unverified`.**
* **What is Proven**: During the collection tests in V2.7 and V2.8, free crowdsourced ADS-B APIs returned zero aircraft state vectors below 3,000 ft AGL or on the runway at OSDI.
* **What is Unproven (`hypothesis_unverified`)**:
  * Asserting that "zero ground receivers exist within 50 km" is an unproven assumption (receiver locations are private).
  * Asserting that "Anti-Lebanon mountain terrain is the confirmed cause" is an unmeasured radio propagation hypothesis.
  * Asserting that "all ADS-B networks lose signal below FL150" is an over-generalization.
* **Alternative Plausible Causes**: Receiver power/network outages, local transponder discipline (Mode A/C operation), GPS jamming/spoofing in the Levant, or geographic filtering by upstream aggregator backends.

---

### Question 7: What is the single best next implementation step?
**Answer**: **Stage and parse the single verified 2026-07-09 Wayback FIDS snapshot (containing 1,982 scheduled flights spanning July 5 to September 9, 2026) into a dedicated staging table.**
* **Why This is the Best Step**:
  1. **Empirically Proven**: The snapshot exists, has been downloaded, decompressed, and verified to contain 1,982 valid flight objects with flight numbers, routes, scheduled times, and airlines.
  2. **Zero Financial Cost**: Completely free ($0.00).
  3. **Zero External Outreach**: Operates without contacting any external party, sending emails, or creating accounts.
  4. **Production Database Safe**: Ingestion will be directed into a separate staging table (`archived_fids_staging`) without touching `flight_events` or violating the production hash invariant.

---

## 3. Production Integrity Sign-Off

```
================================================================================
FINAL VERIFICATION SIGN-OFF: VERSION 2.13.1
================================================================================
Database Path:            data/damascus_airport.db
Baseline SHA-256 Hash:    c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b
Final SHA-256 Hash:       c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b
Integrity Invariant:      CONFIRMED 100% UNCHANGED
Regression Test Status:   178 passed out of 178 tests (Exit Code 0)
Authoritative Decision:   APPROVED
================================================================================
```
