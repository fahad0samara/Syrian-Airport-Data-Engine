# Syrian Airport Data Engine — Version 2.13
# Historical Data Recovery Opportunities & Technical Specifications

**Document Identifier**: `docs/V2_13_DATA_RECOVERY_OPPORTUNITIES.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Target Airspace**: Damascus Flight Information Region (`OSTT_FIR`)  
**Scope**: Detailed Engineering Specifications for Six Concrete Historical Recovery Opportunities  
**Machine-Readable Twin**: `reports/v2_13_recovery_opportunities.csv`  
**Status**: APPROVED RECOVERY ACTION SPECIFICATION  
**Production Integrity Invariant**: `data/damascus_airport.db` SHA-256 verified identical (`c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`).

---

## 1. Executive Summary & Opportunity Prioritization Framework

To resolve the 34-month historical coverage gap without violating project constraints (no unverified synthetic data, zero unauthorized external communication, read-only production database), Version 2.13 specifies six discrete recovery opportunities.

Each opportunity is ranked using a four-tier prioritization model:
- **P0 (Immediate / Non-Invasive)**: Zero financial cost, zero external communication, high automation potential using public web archives.
- **P1 (Authoritative Macro Ground Truth)**: Official government report acquisition to elevate staged macro benchmarks from Grade C to Grade A.
- **P2 (Archival Secondary Telemetry)**: Web-archived snapshots of commercial tracking interfaces.
- **P3 (Commercial Acquisition)**: Paid commercial subscriptions or API extracts (requires explicit project budget allocation).
- **P4 (Academic Research Pipeline)**: Formal academic partnership for ADS-B state vector queries (useful for overflights, limited for runway contact).

---

## 2. Itemized Opportunity Specifications

### 2.1 REC-OPP-01: Wayback Machine FIDS & Airline Schedules
- **Opportunity ID**: `REC-OPP-01`
- **Source Provider**: Internet Archive (`web.archive.org`)
- **Priority Level**: **P0 (Highest Non-Invasive Priority)**
- **Target Historical Period**: `2024-01-01` through `2026-09-29`
- **Geographic Scope**: Damascus International Airport (`DAM` / `OSDI`)
- **Data Granularity**: Flight-level (Scheduled services)
- **Expected Data Fields**:
  * `flight_number` (e.g. `RB101`, `6Q202`)
  * `airline_name` (e.g. `SyrianAir`, `Cham Wings Airlines`)
  * `origin_iata` / `destination_iata` (e.g. `DXB`, `SHJ`, `KWI`, `BEY`, `ALP`)
  * `scheduled_time` (Scheduled arrival / departure timestamp)
  * `operational_status` (e.g. `Scheduled`, `Landed`, `Departed`, `Cancelled`)
- **Evidence Quality Category**: `commercial_schedules` / `scheduled_timetable`
- **Acquisition Methodology**:
  1. Query the Wayback Machine CDX API endpoint:
     `https://web.archive.org/cdx/search/cdx?url=damairport.gov.sy/*&output=json&collapse=digest`
  2. Query historical airline schedule portals:
     * `syrianair.com/*`
     * `chamwings.com/*`
  3. Parse archived JSON/HTML payloads to extract structured flight timetable events.
  4. Stage recovered flights into an archival timetable table without corrupting `flight_events` actual movement timestamps.
- **Known Limitations**: Web crawler frequency is episodic; captures scheduled timetables and passenger display statuses rather than raw radar transponder ground hits.
- **Cost Category**: **Free** ($0.00).
- **Confidence Level**: **Medium** (High for schedule recovery; Medium for exact daily flight counts).
- **Actionable Next Step**: Execute an automated CDX inventory scan against `damairport.gov.sy` and airline timetable URLs.

---

### 2.2 REC-OPP-02: SCAA & MoT Official Statistical Publications
- **Opportunity ID**: `REC-OPP-02`
- **Source Provider**: Syrian Civil Aviation Authority (SCAA) & Ministry of Transport (MoT)
- **Priority Level**: **P1 (Authoritative Macro Ground Truth)**
- **Target Historical Period**: `2024-01-01` through `2026-09-30`
- **Geographic Scope**: Damascus International Airport (`DAM` / `OSDI`) & Damascus FIR (`OSTT_FIR`)
- **Data Granularity**: Monthly and Annual Macro Aggregates
- **Expected Data Fields**:
  * `total_reported_flights` (Segregated into passenger, cargo, diplomatic, Hajj, relief)
  * `total_passengers` (Segregated into arriving and departing)
  * `airspace_overflights` (Damascus FIR transit movements)
  * `operating_airlines` (Direct count of active carriers)
  * `cargo_tonnage` (Freight movements in metric tons)
- **Evidence Quality Category**: `aggregate_airport_statistics` / `primary_official`
- **Acquisition Methodology**:
  1. Locate and download official sovereign publications:
     * SCAA Annual Aviation Reports for 2024 and 2025.
     * SCAA Monthly Statistical Gazettes for 2026 (April, May, July, September).
     * Syrian Ministry of Transport Annual Transport Sector Performance Reviews.
  2. Save downloaded PDF documents or official gazette scans into `data/sources/scaa/` with verifiable cryptographic SHA-256 hashes.
  3. Ingest confirmed figures into `macro_airport_benchmarks` to elevate evidence grades from `Grade C` to `Grade A`.
- **Known Limitations**: Provides macro aggregate totals only; cannot reconstruct individual tail numbers, daily flight numbers, or hourly movements.
- **Cost Category**: **Free** ($0.00).
- **Confidence Level**: **High** (Official sovereign administrative statistics).
- **Actionable Next Step**: Retrieve raw SCAA 2025 Annual Report and 2026 monthly press bulletins from verified public government repositories.

---

### 2.3 REC-OPP-03: Wayback Machine FlightRadar24 Airport History
- **Opportunity ID**: `REC-OPP-03`
- **Source Provider**: Internet Archive mirror of FlightRadar24 (`web.archive.org/web/*/flightradar24.com/data/airports/dam/*`)
- **Priority Level**: **P2 (Secondary Telemetry Archival Recovery)**
- **Target Historical Period**: `2024-01-01` through `2025-12-31`
- **Geographic Scope**: Damascus International Airport (`DAM` / `OSDI`)
- **Data Granularity**: Flight-level (Secondary flight logs)
- **Expected Data Fields**:
  * `flight_number`
  * `callsign`
  * `aircraft_registration` (Tail number, e.g. `YK-AKA`)
  * `aircraft_model` (e.g. `A320`, `A343`)
  * `scheduled_time`
  * `actual_time` (Estimated/recorded touchdown and takeoff)
- **Evidence Quality Category**: `unverified_movement_observations` / `secondary_curated`
- **Acquisition Methodology**:
  1. Query the CDX API for snapshots of:
     * `flightradar24.com/data/airports/dam/arrivals`
     * `flightradar24.com/data/airports/dam/departures`
  2. Parse the table structures from cached HTML pages.
  3. Corroborate airframe tail numbers against known SyrianAir and Cham Wings fleets.
- **Known Limitations**: Web crawler visits to FR24 airport pages are intermittent; many calendar days may be un-crawled or blocked by Cloudflare challenge pages during archiving.
- **Cost Category**: **Free** ($0.00).
- **Confidence Level**: **Medium**.
- **Actionable Next Step**: Audit CDX index for `flightradar24.com/data/airports/dam/*` snapshots to measure capture frequency.

---

### 2.4 REC-OPP-04: FlightRadar24 Business Subscription / Historical API
- **Opportunity ID**: `REC-OPP-04`
- **Source Provider**: FlightRadar24 AB (Stockholm, Sweden)
- **Priority Level**: **P3 (Commercial Acquisition)**
- **Target Historical Period**: Rolling past 365 days (and up to 3 years via custom enterprise tier)
- **Geographic Scope**: Damascus International Airport (`DAM` / `OSDI`)
- **Data Granularity**: Flight-level (Satellite ADS-B and MLAT telemetry)
- **Expected Data Fields**:
  * `flight_id`
  * `callsign`
  * `aircraft_registration`
  * `icao24`
  * `scheduled_dep_time` / `actual_dep_time`
  * `scheduled_arr_time` / `actual_arr_time`
  * `origin_airport` / `destination_airport`
- **Evidence Quality Category**: `verified_physical_movements` (when satellite lock confirmed)
- **Acquisition Methodology**:
  1. Procure a standard FlightRadar24 Business subscription (~$499/year).
  2. Utilize the Airport History module to extract tabular CSV arrival and departure logs for OSDI covering the past 365 days.
  3. Validate against local receiver coverage flags to distinguish transponder-confirmed touchdowns from estimated arrivals.
- **Known Limitations**: Requires commercial subscription. Limited to 365 rolling days under standard plan (extracts dating back to early 2024 require custom commercial quote). Restrictive commercial licensing terms regarding public data redistribution.
- **Cost Category**: **Commercial Subscription** (~$499/year).
- **Confidence Level**: **High** (Industry-standard commercial tracking).
- **Actionable Next Step**: Evaluate project sponsor budget authorization before initiating procurement.

---

### 2.5 REC-OPP-05: FlightAware AeroAPI Historical Data Extract
- **Opportunity ID**: `REC-OPP-05`
- **Source Provider**: FlightAware LLC / Collins Aerospace (Houston, TX, USA)
- **Priority Level**: **P3 (Commercial Acquisition)**
- **Target Historical Period**: `2024-01-01` through `2026-09-30`
- **Geographic Scope**: Damascus International Airport (`DAM` / `OSDI`)
- **Data Granularity**: Flight-level (Global hybrid tracking)
- **Expected Data Fields**:
  * `ident` (Flight number / callsign)
  * `origin` / `destination`
  * `actual_off` / `actual_on`
  * `aircraft_type`
  * `status` (Arrived, Cancelled, En Route)
- **Evidence Quality Category**: `secondary_curated`
- **Acquisition Methodology**:
  1. Submit formal enterprise historical data query to FlightAware sales engineering for airport `OSDI` covering specified dates.
  2. Ingest custom JSON/CSV delivery into staging layer.
- **Known Limitations**: Substantial commercial cost ($500–$1,500+). In regions with low terrestrial ADS-B receiver density, FlightAware frequently relies on airline GDS schedule messaging rather than physical sensor telemetry. Strict redistribution constraints.
- **Cost Category**: **Custom Quotation** ($500–$1,500+).
- **Confidence Level**: **Medium**.
- **Actionable Next Step**: Formulate exact temporal bounds and schema requirements for formal vendor quotation if approved.

---

### 2.6 REC-OPP-06: OpenSky Network Academic Research Access
- **Opportunity ID**: `REC-OPP-06`
- **Source Provider**: OpenSky Network Association (Switzerland)
- **Priority Level**: **P4 (Academic Research Pipeline)**
- **Target Historical Period**: `2024-01-01` through `2026-09-30`
- **Geographic Scope**: Damascus Flight Information Region (`OSTT_FIR`)
- **Data Granularity**: Raw transponder state vectors (1-second resolution)
- **Expected Data Fields**:
  * `time`
  * `icao24`
  * `lat`, `lon`
  * `baro_altitude`, `geo_altitude`
  * `velocity`, `heading`, `vertical_rate`
  * `callsign`
- **Evidence Quality Category**: `unfiltered_telemetry` (Airspace overflights only)
- **Acquisition Methodology**:
  1. Submit the comprehensive academic application package prepared in V2.6 through an accredited university research sponsor.
  2. Query OpenSky Historical Impala/Trino database for spatial bounding box `[32.0, 35.0, 37.5, 42.5]`.
- **Known Limitations**: Requires accredited academic institutional credentials. Zero terrestrial receivers in Damascus basin means OpenSky cannot detect aircraft below ~FL150. Useful strictly for **overflight analysis (`national_airspace_statistics`)**, not for airport runway movements.
- **Cost Category**: **Free** ($0.00 for non-commercial academic research).
- **Confidence Level**: **Low** for airport runway touchdown recovery; **High** for OSTT_FIR airspace transit recovery.
- **Actionable Next Step**: Await formal project sponsor authorization before initiating academic university submission.
