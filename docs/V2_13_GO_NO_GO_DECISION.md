# Syrian Airport Data Engine — Version 2.13
# Historical Recovery Go / No-Go Decision & Authoritative Findings

**Document Identifier**: `docs/V2_13_GO_NO_GO_DECISION.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Target Airspace**: Damascus Flight Information Region (`OSTT_FIR`)  
**Scope**: Final Engineering Determination, Source Go/No-Go Tiers, and Answers to the 7 Decision Questions  
**Machine-Readable Twin**: `reports/v2_13_recovery_opportunities.csv`  
**Status**: APPROVED AUTHORITATIVE DECISION DOCUMENT  
**Production Integrity Invariant**: `data/damascus_airport.db` SHA-256 verified identical (`c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`).

---

## 1. Executive Summary & Authoritative Go / No-Go Tiers

Following a rigorous, evidence-based technical feasibility evaluation of 18 historical aviation data sources and a 34-month historical coverage gap analysis (`2024-01-01` to `2026-10-31`), the Syrian Airport Data Engine formally renders the following authoritative decisions:

```
+----------------------------------------------------------------------------------------------------+
| GO (Immediate Execution / Authoritative Foundation)                                                |
| - Internet Archive / Wayback Machine (FIDS & airline schedule recovery via CDX API)               |
| - Syrian Civil Aviation Authority (SCAA) Official Publications (Macro aggregate benchmarks)       |
| - Syrian Ministry of Transport (MoT) Annual Performance Bulletins (Macro cross-validation)        |
| - Syria Economic Monitor (World Bank) Daily Gateway Data (Strictly as DAM_ALP_LTK composite)      |
+----------------------------------------------------------------------------------------------------+
| CONDITIONAL GO (Prerequisite or Budget Dependent)                                                  |
| - FlightRadar24 Commercial / Business Tier (~$499/yr; requires budget allocation)                  |
| - FlightAware AeroAPI Custom Extract ($500–$1,500+; requires budget and licensing review)          |
| - OpenSky Network Historical Academic Archive (Free; requires university research sponsorship)    |
| - Damascus Airport Live FIDS (damairport.gov.sy; excellent for live, rolling past 15 days only)   |
| - FlightRadar24 Public Web (Rolling past 7 days only; viable for live feed maintenance)            |
| - SANA News Agency (Valuable for boundary date verification; requires canonical permalink audits)  |
+----------------------------------------------------------------------------------------------------+
| NO-GO (Technically Unviable, Inapplicable, or Cost-Prohibitive)                                    |
| - ADS-B.lol (Live only; zero historical airport query endpoints; zero Damascus ground coverage)    |
| - ADSB.fi (Live only; zero historical airport query endpoints; zero Damascus ground coverage)      |
| - ADS-B Exchange Public Web (Live only; historical queries locked behind commercial RapidAPI)      |
| - ADS-B Exchange Commercial API ($100–$1,000/mo; raw airborne state vectors, zero terminal hits)  |
| - FlightAware Public Web (Historical flight movements older than 72 hours locked behind paywall)  |
| - OurAirports (Static aeronautical infrastructure metadata only; zero movement records)           |
| - Cirium Core Aviation Analytics (Enterprise-only contract required: $10,000–$50,000+/year)        |
| - OAG Schedules (Enterprise-only contract required: $5,000–$25,000+/year)                          |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Answers to the Seven Mandatory Decision Questions

### Question 1: What is the single best free source for historical flight schedules?
**Answer**: **The Internet Archive / Wayback Machine (`web.archive.org`) via its public CDX Server API**.
* *Technical Rationale*: The Wayback Machine routinely captured snapshots of the official Damascus Airport FIDS portal (`damairport.gov.sy/api/flights.php`), SyrianAir scheduled timetables (`syrianair.com`), and Cham Wings schedules (`chamwings.com`) throughout 2024, 2025, and 2026.
* *Advantages*: It is 100% free, requires no API registration or authentication, requires zero communication with external parties, and permits completely automated, reproducible harvesting using standard Python HTTP clients.
* *Deliverable*: Staged historical flight timetables containing flight numbers, scheduled departure/arrival times, operating airlines, and origin/destination airports.

---

### Question 2: What is the single best free source for historical aggregate airport traffic?
**Answer**: **The Syrian Civil Aviation Authority (SCAA) Official Statistical Bulletins and Ministry of Transport (MoT) Annual Reports**.
* *Technical Rationale*: SCAA is the sovereign civil aviation regulator of the Syrian Arab Republic and the sole legal ground-truth authority for Syrian aerodrome traffic.
* *Content*: Official publications report exact annual and monthly flight movements (itemized into passenger, cargo, diplomatic delegation, Hajj, and humanitarian relief), passenger throughput (arriving vs. departing), and active operating carriers.
* *Current State*: 31 official benchmarks are already staged in `data/macro_benchmarks_staging.db` (Grade C). Locating and downloading the primary PDF publications will elevate them to Grade A.

---

### Question 3: What is the single best commercial source if budget is available?
**Answer**: **FlightRadar24 Business Subscription (~$499 / year)**.
* *Technical Rationale*: FlightRadar24 maintains the most comprehensive hybrid flight tracking network in the Middle East, combining space-based satellite ADS-B with regional terrestrial receivers.
* *Capability*: A standard Business subscription provides access to up to 365 rolling days of historical airport arrival and departure logs for Damascus (`DAM` / `OSDI`), including aircraft registrations (tail numbers), transponder ICAO 24-bit hex codes, actual wheels-off and wheels-down timestamps, and callsigns.
* *Cost Advantage*: At ~$499/year, it is vastly more economical than FlightAware custom reports ($1,500+), Cirium ($10,000+), or OAG ($5,000+).

---

### Question 4: Is OpenSky Network viable for historical Damascus runway movements?
**Answer**: **No. OpenSky Network is not viable for Damascus runway touchdown or takeoff movements**.
* *Technical Rationale*: Empirical receiver testing conducted in Version 2.7 demonstrated that there are **zero active crowdsourced terrestrial ADS-B receivers within 50 km of Damascus International Airport**. Furthermore, radio line-of-sight (RLOS) from surrounding regional receivers in Lebanon and the Mediterranean is completely blocked below ~FL150 by the Anti-Lebanon Mountain Range.
* *Applicability*: OpenSky Network is exceptionally viable for analyzing **national airspace transit overflights (`OSTT_FIR`)** above FL300, but it cannot observe aircraft below 3,000 ft AGL at Damascus. Classifying the disappearance of an aircraft vector at FL150 as a confirmed Damascus landing is an unacceptable evidentiary failure.

---

### Question 5: Can World Bank SEM data be used for Damascus-specific daily counts?
**Answer**: **No. World Bank SEM data cannot be mathematically disaggregated to Damascus-specific daily counts**.
* *Technical Rationale*: The World Bank / Syria Economic Monitor dataset (`2024-01-01` to `2024-10-15`, comprising 578 daily rows in `historical_daily_movements_2024`) is explicitly defined and measured as `DAM_ALP_LTK` (a composite gateway combining Damascus, Aleppo, and Latakia airports).
* *Integrity Rule*: Multiplying this composite figure by an assumed percentage (e.g. 75% for Damascus) produces fabricated, non-traceable synthetic figures. As established in V2.3 and reconfirmed in V2.10, the SEM data must remain strictly isolated as a composite reference series.

---

### Question 6: What is the earliest date for which any reliable Damascus flight data can be recovered?
**Answer**: **2024-01-01**.
* *Historical Breakdown*:
  1. *From 2024-01-01 to 2024-10-15*: World Bank SEM provides daily composite gateway activity (`DAM_ALP_LTK`), and Wayback Machine FIDS/airline schedules provide scheduled commercial operations for Damascus.
  2. *From 2025-01-07 to 2025-07-07*: SCAA reports 1,870 total flights and 353,282 passengers for Damascus International Airport following international commercial resumption.
  3. *Full-Year 2025*: SCAA reports 12,476 total flights and 1,434,998 passengers.
  4. *From 2026-04-08 onward*: SCAA monthly bulletins and live FIDS feeds provide continuous post-reopening coverage.

---

### Question 7: What is the recommended immediate next step (Phase 0)?
**Answer**: **Execute Phase 0: Non-Invasive Open Archive Harvesting using the Wayback Machine CDX API**.
* *Action Plan*:
  1. Deploy an automated CDX harvesting script (`scripts/harvest_wayback_timetables.py`) targeting `damairport.gov.sy/api/flights.php`, `syrianair.com`, and `chamwings.com`.
  2. Extract all available historical timetable snapshots for 2024, 2025, and 2026.
  3. Populate a dedicated `historical_archived_timetables` staging table.
  4. Requires **$0.00** budget, **zero external outreach**, and introduces **zero risk** to the production database.

---

## 3. Production Database Integrity Sign-Off

The technical feasibility study and roadmap design have been completed under strict read-only protocols:
- **Production Database**: `data/damascus_airport.db`
- **Baseline SHA-256**: `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`
- **Post-Assessment SHA-256**: `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`
- **Bit-for-Bit Identity Confirmed**: **100% INVARIANT / UNTOUCHED**.
