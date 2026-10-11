# Syrian Airport Data Engine — Version 2.13
# Historical Source Inventory & Technical Feasibility Report

**Document Identifier**: `docs/V2_13_HISTORICAL_SOURCE_INVENTORY.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Target Airspace**: Damascus Flight Information Region (`OSTT_FIR`)  
**Scope**: In-Depth Technical Assessment of 18 Historical Aviation Data Sources  
**Machine-Readable Twins**: `reports/v2_13_historical_source_inventory.csv` & `reports/v2_13_historical_source_inventory.json`  
**Status**: APPROVED CANDIDATE INVENTORY  
**Production Integrity Invariant**: `data/damascus_airport.db` SHA-256 verified identical (`c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`).

---

## 1. Executive Summary & Assessment Methodology

Version 2.13 conducts an exhaustive technical investigation into 18 candidate historical aviation data sources to determine their viability for recovering Damascus International Airport (`DAM` / `OSDI`) flight movements, airline schedules, and macro operational statistics for the period spanning **2024-01-01 through 2026-10-31**.

Each provider was evaluated against thirteen standardized technical and operational criteria:
1. **Provider Category**: Academic research, open archive, official authority, free public, or commercial aggregator.
2. **Historical Query Availability**: Does the platform support historical queries, or is it strictly live-only?
3. **Earliest Available Date**: The historical temporal limit of the provider's database.
4. **Airport Specificity**: Can queries isolate `DAM` / `OSDI` specifically, or only regional airspace / composites?
5. **Flight-Level Granularity**: Does the provider expose individual flight records or only macro aggregates?
6. **Actual Movement Timestamps**: Are physical touchdown (`actual_arr_time`) and takeoff (`actual_dep_time`) timestamps recorded?
7. **Directional Segregation**: Are arrivals and departures explicitly segregated?
8. **Raw Data Export**: Can raw CSV, JSON, or parquet datasets be acquired programmatically?
9. **Authentication & Authorization**: Anonymous, free API key, academic institutional approval, or enterprise contract.
10. **Financial Cost**: Free, monthly subscription, enterprise contract, or custom sales quotation.
11. **Damascus Empirical Coverage**: Real-world evidence of Damascus reception (verified in repo, empirically tested sparse, unverified quoted, or blocked paywall).
12. **Known Technical Limitations**: Horizon shielding, transponder filtering, data gaps, or legal redistribution restrictions.
13. **Engineering Recommendation**: Definitive categorization into `GO`, `CONDITIONAL GO`, or `NO-GO`.

---

## 2. Category 1: Free & Public Aviation Sources (13 Sources)

### 2.1 OpenSky Network
- **Provider Category**: Academic Research Institution (Switzerland / Germany).
- **Historical Availability**: Conditional (REST API blocked; academic archive available).
- **Earliest Date**: 2013-01-01.
- **Airport Specificity**: Yes (Supports query by ICAO code `OSDI`).
- **Flight-Level Data**: Yes (Individual flight tracks and state vectors).
- **Actual Movement Timestamps**: Yes (Calculated arrival/departure timestamps if ground contact exists).
- **Arrivals/Departures Segregated**: Yes (`/flights/arrival` and `/flights/departure` endpoints).
- **Raw Export Available**: Yes (Trino/Impala SQL interface, CSV, Parquet).
- **Authentication**: Academic Institutional Credentials required. Anonymous access returns `HTTP 403 Forbidden` (`You cannot access historical flights`).
- **Cost**: Free (for non-commercial academic research).
- **Damascus Empirical Evidence**: `empirically_tested_sparse`. Empirically verified in V2.7: zero terrestrial ADS-B receivers within 50 km of Damascus. OpenSky records high-altitude transit flights (>FL300) over Syria, but has zero runway contact at OSDI.
- **Limitations**: Requires institutional sponsorship. V2.6 application package prepared in `docs/` remains unsubmitted per project safety policy.
- **Recommendation**: `CONDITIONAL GO` (Academic pipeline only; cannot recover runway movements without ground stations).

### 2.2 ADS-B.lol
- **Provider Category**: Free Public Community Network.
- **Historical Availability**: No (Live point/radius API only).
- **Earliest Date**: Live telemetry only (no historical archive).
- **Airport Specificity**: No (Spatial radius queries centered on coordinates `33.411, 36.514`).
- **Flight-Level Data**: Partial (Aircraft state vectors).
- **Actual Movement Timestamps**: No.
- **Arrivals/Departures Segregated**: No.
- **Raw Export Available**: No.
- **Authentication**: Not required.
- **Cost**: Free.
- **Damascus Empirical Evidence**: `empirically_tested_sparse`. Live testing in V2.7 confirmed zero receiver coverage below FL250 in southern Syria.
- **Limitations**: Strictly live; no historical REST query endpoints. Cannot recover past operations.
- **Recommendation**: `NO-GO`.

### 2.3 ADSB.fi
- **Provider Category**: Free Public Community Network.
- **Historical Availability**: No (Live open-data API only).
- **Earliest Date**: Live telemetry only.
- **Airport Specificity**: No (Geographic bounding box or radius only).
- **Flight-Level Data**: Partial.
- **Actual Movement Timestamps**: No.
- **Arrivals/Departures Segregated**: No.
- **Raw Export Available**: No.
- **Authentication**: Not required.
- **Cost**: Free.
- **Damascus Empirical Evidence**: `empirically_tested_sparse`.
- **Limitations**: Operates identically to ADS-B.lol; lacks historical search and terrestrial receivers in Damascus basin.
- **Recommendation**: `NO-GO`.

### 2.4 ADS-B Exchange (Public Web)
- **Provider Category**: Free Public Web Interface.
- **Historical Availability**: No (Public tracking interface is live-only).
- **Earliest Date**: Live only.
- **Airport Specificity**: No.
- **Flight-Level Data**: Partial (Visual map rendering only).
- **Actual Movement Timestamps**: No.
- **Arrivals/Departures Segregated**: No.
- **Raw Export Available**: No.
- **Authentication**: Not required.
- **Cost**: Free.
- **Damascus Empirical Evidence**: `blocked_paywall` (Historical capabilities gated behind commercial RapidAPI tier).
- **Limitations**: Public web frontend does not permit historical raw data extraction.
- **Recommendation**: `NO-GO`.

### 2.5 OurAirports
- **Provider Category**: Open Aeronautical Database.
- **Historical Availability**: Not applicable (Static infrastructure dataset).
- **Earliest Date**: Static baseline.
- **Airport Specificity**: Yes (`OSDI` / `DAM`).
- **Flight-Level Data**: No (Airport master metadata only: runways, navigation aids, coordinates).
- **Actual Movement Timestamps**: No.
- **Arrivals/Departures Segregated**: No.
- **Raw Export Available**: Yes (Full CSV export verified in repository `data/ourairports_syria.csv`).
- **Authentication**: Not required.
- **Cost**: Free.
- **Damascus Empirical Evidence**: `verified_in_repo`.
- **Limitations**: Contains zero movement telemetry, timetables, or flight logs.
- **Recommendation**: `NO-GO` (Infrastructure reference only; zero movement recovery utility).

### 2.6 FlightRadar24 (Public / Web)
- **Provider Category**: Free Public Aggregator (Web / App).
- **Historical Availability**: Conditional (Rolling past 7 days only).
- **Earliest Date**: Current date minus 7 days.
- **Airport Specificity**: Yes (`flightradar24.com/data/airports/dam`).
- **Flight-Level Data**: Yes (Flight number, airline, aircraft type, scheduled/actual times).
- **Actual Movement Timestamps**: Partial (Recorded when MLAT/ADS-B lock exists; otherwise estimated).
- **Arrivals/Departures Segregated**: Yes.
- **Raw Export Available**: No (HTML interface only; scraping restricted by Terms of Service).
- **Authentication**: Not required for web viewing.
- **Cost**: Free.
- **Damascus Empirical Evidence**: `verified_in_repo` (Sampled in V2.1–V2.2).
- **Limitations**: Window strictly limited to 7 days. Cannot access 2024 or 2025 data.
- **Recommendation**: `CONDITIONAL GO` (Rolling maintenance only; non-viable for deep historical recovery).

### 2.7 FlightAware (Public / Web)
- **Provider Category**: Free Public Aggregator (Web).
- **Historical Availability**: No (Limited to past 48–72 hours).
- **Earliest Date**: Past 2–3 days.
- **Airport Specificity**: Yes (`flightaware.com/live/airport/OSDI`).
- **Flight-Level Data**: Yes.
- **Actual Movement Timestamps**: Partial.
- **Arrivals/Departures Segregated**: Yes.
- **Raw Export Available**: No.
- **Authentication**: Not required for web viewing.
- **Cost**: Free.
- **Damascus Empirical Evidence**: `blocked_paywall`.
- **Limitations**: Web interface truncates historical airport operations older than 72 hours.
- **Recommendation**: `NO-GO`.

### 2.8 Official Damascus Airport Website (`damairport.gov.sy`)
- **Provider Category**: Official Aerodrome Operator Portal.
- **Historical Availability**: Conditional (Active FIDS endpoint retains ~10–15 recent days).
- **Earliest Date**: Current rolling timetable snapshot.
- **Airport Specificity**: Yes (Direct ground FIDS for `DAM`).
- **Flight-Level Data**: Yes (Flight number, airline, scheduled arrival/departure, origin/destination, status).
- **Actual Movement Timestamps**: No (Displays flight status like `Landed` or `Departed`, but lacks raw radar timestamp).
- **Arrivals/Departures Segregated**: Yes (`flights.php?type=arrivals` / `departures`).
- **Raw Export Available**: Yes (JSON payload via internal REST endpoint).
- **Authentication**: Not required (Public civic portal).
- **Cost**: Free.
- **Damascus Empirical Evidence**: `verified_in_repo` (Directly harvested in production database).
- **Limitations**: Does not maintain an official long-term historical archive on the live server.
- **Recommendation**: `CONDITIONAL GO` (Excellent for current monitoring; historical recovery requires archival mirrors).

### 2.9 Syrian Civil Aviation Authority (SCAA) Publications
- **Provider Category**: Official Civil Aviation Regulatory Authority.
- **Historical Availability**: Yes (Periodic statistical bulletins and official statements).
- **Earliest Date**: 2024-01-01.
- **Airport Specificity**: Yes (Airport-level aggregate metrics for Damascus, Aleppo, Latakia).
- **Flight-Level Data**: No (Macro statistical aggregates: monthly/annual flights, passengers, cargo).
- **Actual Movement Timestamps**: No.
- **Arrivals/Departures Segregated**: Yes (Segregated passenger arrivals/departures).
- **Raw Export Available**: No (Published in text bulletins, official press releases, and printed reports).
- **Authentication**: Not required.
- **Cost**: Free.
- **Damascus Empirical Evidence**: `unverified_quoted` (31 staged records currently at Grade C in staging layer).
- **Limitations**: Lacks flight-level event logs. Hardcopy or direct digital PDF reports required to elevate evidence to Grade A.
- **Recommendation**: `GO` (Essential foundation for macro airport benchmark ground truth).

### 2.10 Syrian Ministry of Transport (MoT)
- **Provider Category**: Sovereign Transportation Ministry.
- **Historical Availability**: Yes (Annual infrastructure performance reviews).
- **Earliest Date**: 2024-01-01.
- **Airport Specificity**: Yes.
- **Flight-Level Data**: No (Macro passenger and cargo aggregates across transport sectors).
- **Actual Movement Timestamps**: No.
- **Arrivals/Departures Segregated**: Yes.
- **Raw Export Available**: No.
- **Authentication**: Not required.
- **Cost**: Free.
- **Damascus Empirical Evidence**: `unverified_quoted`.
- **Limitations**: Broad macroeconomic focus; does not itemize daily flights.
- **Recommendation**: `GO` (Secondary validation for SCAA macro benchmarks).

### 2.11 Syrian Arab News Agency (SANA)
- **Provider Category**: Official State News Agency.
- **Historical Availability**: Yes (Searchable archival news dispatches).
- **Earliest Date**: 2024-01-01.
- **Airport Specificity**: Yes.
- **Flight-Level Data**: Partial (Specific state delegations, first commercial resumptions, Hajj flights).
- **Actual Movement Timestamps**: Partial (News reporting of specific flight arrival dates and hours).
- **Arrivals/Departures Segregated**: Partial.
- **Raw Export Available**: No (HTML articles).
- **Authentication**: Not required.
- **Cost**: Free.
- **Damascus Empirical Evidence**: `unverified_quoted` (Canonical permalinks pending verification).
- **Limitations**: Narrative reporting; lacks continuous tabular records.
- **Recommendation**: `CONDITIONAL GO` (Valid for verifying operational boundary dates and special flight operations).

### 2.12 Syria Economic Monitor (World Bank Data Partnership)
- **Provider Category**: Multilateral Economic Research Project.
- **Historical Availability**: Yes (Historical daily composite time series).
- **Earliest Date**: 2024-01-01 to 2024-10-15.
- **Airport Specificity**: No (Composite metric: `DAM_ALP_LTK`).
- **Flight-Level Data**: No (Daily aggregated movement totals).
- **Actual Movement Timestamps**: No.
- **Arrivals/Departures Segregated**: Yes (289 arrival days, 289 departure days).
- **Raw Export Available**: Yes (578 daily records integrated into `historical_daily_movements_2024`).
- **Authentication**: Not required.
- **Cost**: Free.
- **Damascus Empirical Evidence**: `verified_in_repo`.
- **Limitations**: Multi-airport composite cannot be mathematically disaggregated to Damascus alone. Coverage ceases after 2024-10-15.
- **Recommendation**: `GO` (Retained as reference composite; prohibited from disaggregation).

### 2.13 Internet Archive / Wayback Machine
- **Provider Category**: Open Digital Web Archive.
- **Historical Availability**: Yes (Persistent web crawl snapshots since 1996).
- **Earliest Date**: 2024-01-01 (and earlier).
- **Airport Specificity**: Yes (Targets specific Damascus airport URLs).
- **Flight-Level Data**: Yes (Archived FIDS pages, airline timetables, and FR24 airport pages).
- **Actual Movement Timestamps**: Partial (Preserves status and timetables as captured at crawl time).
- **Arrivals/Departures Segregated**: Yes.
- **Raw Export Available**: Yes (CDX API allows automated index querying and raw JSON extraction).
- **Authentication**: Not required.
- **Cost**: Free.
- **Damascus Empirical Evidence**: `unverified_quoted`.
- **Limitations**: Temporal resolution is discrete (depends on whether crawler visited during a given date).
- **Recommendation**: `GO` (Highest-priority free pathway for recovering granular flight schedules).

---

## 3. Category 2: Commercial & Enterprise Aviation Aggregators (5 Sources)

### 3.1 FlightRadar24 (Commercial / Business / Custom Data)
- **Provider Category**: Commercial Global Flight Tracking Aggregator.
- **Historical Availability**: Yes.
- **Earliest Date**: 2020-01-01 (Custom archival datasets span back to 2016).
- **Airport Specificity**: Yes (`DAM` / `OSDI` airport history).
- **Flight-Level Data**: Yes (Complete flight records: flight number, callsign, aircraft type, registration, ICAO 24-bit address).
- **Actual Movement Timestamps**: Yes (Actual runway takeoff and landing times derived from satellite ADS-B and MLAT).
- **Arrivals/Departures Segregated**: Yes.
- **Raw Export Available**: Yes (CSV / JSON data exports).
- **Authentication**: Required (Paid user account or API key).
- **Cost**: 
  * Business Plan: ~$499/year (Provides rolling 365 days of historical airport movements).
  * Custom Historical Extract: $1,500–$5,000+ for multi-year bespoke raw database export.
- **Damascus Empirical Evidence**: `verified_in_repo` (Historically confirmed to capture Syrian commercial traffic via satellite receivers).
- **Limitations**: Commercial subscription cost; terrestrial receiver density over Syria remains low, relying partially on space-based satellite ADS-B.
- **Recommendation**: `CONDITIONAL GO` (Viable if project budget is allocated for commercial procurement).

### 3.2 FlightAware (AeroAPI / Custom Reports)
- **Provider Category**: Commercial Aviation Intelligence Provider (Collins Aerospace).
- **Historical Availability**: Yes.
- **Earliest Date**: 2015-01-01.
- **Airport Specificity**: Yes (`OSDI`).
- **Flight-Level Data**: Yes (Individual flight tracks, gate times, runway times).
- **Actual Movement Timestamps**: Yes (`actual_on`, `actual_off`).
- **Arrivals/Departures Segregated**: Yes.
- **Raw Export Available**: Yes (RESTful JSON API and custom CSV delivery).
- **Authentication**: Required (AeroAPI key).
- **Cost**:
  * AeroAPI Historical: $100/mo base + query query fees ($0.05–$0.20 per query); typical cost $500–$1,500.
  * Bespoke Historical Airport Report: $1,000–$3,500.
- **Damascus Empirical Evidence**: `blocked_paywall`.
- **Limitations**: Expensive pricing tiers; strict commercial licensing prohibits redistributing raw data in public open-source repositories without express permission.
- **Recommendation**: `CONDITIONAL GO` (Viable alternative to FR24 if enterprise budget authorized).

### 3.3 ADS-B Exchange (Commercial Historical API)
- **Provider Category**: Unfiltered Commercial Flight Tracking Aggregator.
- **Historical Availability**: Yes.
- **Earliest Date**: 2016-01-01.
- **Airport Specificity**: No (Spatial bounding box or aircraft state vector search; does not parse airport movements).
- **Flight-Level Data**: Yes (Raw 1-second state vectors: latitude, longitude, altitude, ground speed).
- **Actual Movement Timestamps**: Yes (Requires custom trajectory interpolation to detect landing).
- **Arrivals/Departures Segregated**: No (Raw airborne vectors only).
- **Raw Export Available**: Yes (JSON via RapidAPI).
- **Authentication**: Required (RapidAPI enterprise key).
- **Cost**: $100–$1,000+/month based on request volume.
- **Damascus Empirical Evidence**: `blocked_paywall`.
- **Limitations**: High computational overhead (requires downloading massive spatial vector streams and calculating runway intersections); low-altitude receiver gap around Damascus persists.
- **Recommendation**: `NO-GO` (High cost and extreme engineering complexity for low terminal return).

### 3.4 Cirium (Ascend / Diio / Core Aviation Analytics)
- **Provider Category**: Enterprise Global Aviation Intelligence Leader.
- **Historical Availability**: Yes.
- **Earliest Date**: 2000-01-01.
- **Airport Specificity**: Yes.
- **Flight-Level Data**: Yes (Published airline schedules, aircraft fleet utilization, and verified historical flights).
- **Actual Movement Timestamps**: Partial (Combines ACARS, ASDI radar, and airline schedule progress).
- **Arrivals/Departures Segregated**: Yes.
- **Raw Export Available**: Yes (Snowflake direct share, API, flat files).
- **Authentication**: Enterprise contract required.
- **Cost**: Enterprise pricing ($10,000–$50,000+/year). No individual or ad-hoc researcher pricing.
- **Damascus Empirical Evidence**: `blocked_paywall`.
- **Limitations**: Massive financial barrier; restrictive enterprise-only legal agreements.
- **Recommendation**: `NO-GO` (Cost-prohibitive for independent research).

### 3.5 OAG (Official Aviation Guide)
- **Provider Category**: Enterprise Airline Schedule & Capacity Provider.
- **Historical Availability**: Yes.
- **Earliest Date**: 1995-01-01.
- **Airport Specificity**: Yes.
- **Flight-Level Data**: Yes (Scheduled commercial passenger and cargo flights).
- **Actual Movement Timestamps**: No (OAG is fundamentally a schedule and capacity aggregator, not an ADS-B sensor network).
- **Arrivals/Departures Segregated**: Yes.
- **Raw Export Available**: Yes (Schedules Analyzer, flat files).
- **Authentication**: Enterprise contract required.
- **Cost**: Enterprise pricing ($5,000–$25,000+/year).
- **Damascus Empirical Evidence**: `blocked_paywall`.
- **Limitations**: High financial cost; reflects filed schedules rather than physical transponder-confirmed operations.
- **Recommendation**: `NO-GO` (Cost-prohibitive and schedule-only).
