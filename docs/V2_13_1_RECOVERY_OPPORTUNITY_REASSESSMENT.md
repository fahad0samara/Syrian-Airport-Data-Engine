# Syrian Airport Data Engine — Version 2.13.1
# Reassessment of Historical Data Recovery Opportunities

**Document Identifier**: `docs/V2_13_1_RECOVERY_OPPORTUNITY_REASSESSMENT.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Scope**: Evidence-Based Reclassification of Historical Recovery Opportunities  
**Machine-Readable Twin**: `reports/v2_13_1_recovery_opportunities.csv`  
**Status**: APPROVED REASSESSMENT REGISTER  
**Production Integrity Invariant**: `data/damascus_airport.db` SHA-256 verified identical (`c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`).

---

## 1. Executive Summary & Four-Tier Decision Standard

Version 2.13.1 re-evaluates all historical recovery opportunities specified in Version 2.13 against demonstrable evidentiary standards.

Each candidate opportunity is categorized into one of four mutually exclusive decision tiers:
- **`GO`**: A specific source, verified URL/access path, and usable historical data have been **empirically demonstrated**.
- **`CONDITIONAL GO`**: A plausible source exists, but required terminal coverage, specific date boundaries, or commercial procurement remain unverified.
- **`NO-GO`**: The source cannot satisfy the stated operational or temporal requirement based on verified evidence.
- **`UNKNOWN`**: Insufficient empirical evidence exists to render a defensible determination.

### Mandate on Confidence Scores and External Contact:
1. **No Speculative Confidence Percentages**: Arbitrary percentage ratings (e.g. "85% confidence") are eliminated. Reliability is expressed strictly through verified evidentiary status.
2. **Zero External Contact**: All proposals to send emails to OpenSky, submit research applications, request university sponsorships, or create third-party accounts are strictly removed from actionable tasks in compliance with the user's explicit directive.

---

## 2. Itemized Opportunity Reassessments

### 2.1 Opportunity REC-OPP-01-V2131: Wayback Machine 2026-07-09 FIDS Snapshot
- **Opportunity Title**: Ingestion of Single Demonstrated Damascus Airport FIDS Snapshot
- **Decision Tier**: **`GO`**
- **Exact Target**: `https://web.archive.org/web/20260709234230/https://damairport.gov.sy/api/flights.php`
- **Evidence Supporting Availability**: 
  * The Wayback Machine CDX API confirms exactly one historical capture with HTTP 200, MIME `application/json`, digest `LWGQOMIVR7BG55CKGT4LXDRNUVKDA36L`, and uncompressed payload size of 68,891 bytes.
  * Retrieval and parsing of the decompressed payload demonstrated **1,982 structured JSON flight objects** with explicit directional segregation (`arrival` and `departure`).
- **Actual Demonstrated Date Range**: **2026-07-05 through 2026-09-09** (67 calendar dates).
- **Geographic Scope**: Damascus International Airport (`DAM` / `OSDI`).
- **Data Granularity**: Flight-level commercial schedule and operational timetable status (flight number, airline, origin/destination, scheduled date, scheduled time, gate, aircraft type, operational status).
- **Known Limitations**: Represents passenger display timetable status, not physical radar touchdown/takeoff timestamps. Does not cover 2024 or 2025.
- **Cost Evidence**: **$0.00** (Free public web archive).
- **Next Practical Step**: Ingest the 1,982 flight objects into a dedicated staging table (`archived_fids_staging`) to benchmark Q3 2026 commercial scheduled operations.

---

### 2.2 Opportunity REC-OPP-02-V2131: Wayback Machine 2024–2025 Historical Timetables
- **Opportunity Title**: Recovery of 2024–2025 Flight Schedules via Internet Archive
- **Decision Tier**: **`NO-GO`**
- **Exact Target**: `damairport.gov.sy`, `syrianair.com`, `chamwings.com`
- **Evidence Supporting Availability**:
  * An exhaustive CDX index audit proved that **zero snapshots** of `damairport.gov.sy` exist in the Wayback Machine prior to July 2026.
  * Snapshots of `syrianair.com` in 2024–2025 are minimal HTTP 301 redirects (~1 KB) or asset links with zero flight tables.
  * Snapshots of `chamwings.com` in 2024–2025 contain promotional marketing banners and dynamic booking search forms with zero tabular timetables.
- **Actual Demonstrated Date Range**: **None (0 days demonstrated)**.
- **Geographic Scope**: Damascus International Airport (`DAM`).
- **Data Granularity**: None.
- **Known Limitations**: The source materials simply were not crawled or preserved by the Internet Archive during the target period.
- **Cost Evidence**: $0.00.
- **Next Practical Step**: Conclude this recovery pathway as permanently unviable. Close the task.

---

### 2.3 Opportunity REC-OPP-03-V2131: Sovereign Statistical Publications (SCAA / MoT)
- **Opportunity Title**: Sovereign Civil Aviation Authority Macro Benchmark Ground Truth
- **Decision Tier**: **`CONDITIONAL GO`**
- **Exact Target**: Official SCAA Annual Statistical Reports and Monthly Gazettes
- **Evidence Supporting Availability**:
  * 31 aggregate macro benchmark records are staged in `data/macro_benchmarks_staging.db`.
  * Secondary press reports quote official SCAA press conferences and Ministry of Transport bulletins for 2025 annual throughput (12,476 flights; 1,434,998 pax) and 2026 monthly metrics.
- **Actual Demonstrated Date Range**: `2025-01-07` through `2026-09-30` (Selected milestone and monthly reporting periods).
- **Geographic Scope**: Damascus International Airport (`DAM`) and Damascus FIR (`OSTT_FIR`).
- **Data Granularity**: Monthly and annual aggregate statistics (reported flights, passengers, airline counts, overflights).
- **Known Limitations**: Provides aggregate airport volumes; cannot reconstruct individual tail numbers, daily flights, or transponder telemetry. Currently staged at Grade C pending acquisition of primary documents.
- **Cost Evidence**: **$0.00** (Public sovereign statistical gazettes).
- **Next Practical Step**: Search for and archive primary digital PDF publications or official scanned gazettes from Syrian government digital portals to promote records to Grade A.

---

### 2.4 Opportunity REC-OPP-04-V2131: FlightRadar24 Airport History
- **Opportunity Title**: Commercial Flight Tracking Rolling History Evaluation
- **Decision Tier**: **`CONDITIONAL GO`**
- **Exact Target**: FlightRadar24 Airport Data Module (`DAM` / `OSDI`)
- **Evidence Supporting Availability**:
  * Publicly documented subscription tiers confirm 365 days of historical airport data is available (Gold plan: $44.99/year; Business plan: $499/year).
- **Actual Demonstrated Date Range**: Rolling 365 days from query date.
- **Geographic Scope**: Damascus International Airport (`DAM` / `OSDI`).
- **Data Granularity**: Flight-level movements (flight number, airline, callsign, aircraft type, registration, scheduled and recorded times).
- **Known Limitations**: Terrestrial receiver coverage around Damascus is sparse. Public documentation does not guarantee that 365 days of historical data for OSDI contains transponder-confirmed runway touchdown timestamps rather than estimated progress. Requires commercial purchase. Commercial terms restrict open data redistribution.
- **Cost Evidence**: $44.99/year (Gold personal) or $499.00/year (Business commercial).
- **Next Practical Step**: Retain on hold. In strict compliance with safety rules, do not purchase subscriptions or initiate vendor communication.

---

### 2.5 Opportunity REC-OPP-05-V2131: FlightAware AeroAPI Custom Extract
- **Opportunity Title**: Enterprise Commercial Aviation Intelligence Evaluation
- **Decision Tier**: **`CONDITIONAL GO`**
- **Exact Target**: FlightAware AeroAPI v4 / Custom Historical Airport Report
- **Evidence Supporting Availability**:
  * Documented enterprise API capabilities for global airport arrivals and departures.
- **Actual Demonstrated Date Range**: Historical archives spanning multiple years.
- **Geographic Scope**: Damascus International Airport (`DAM` / `OSDI`).
- **Data Granularity**: Flight-level tracks and status.
- **Known Limitations**: Substantial financial cost ($500–$3,000+). In regions with low terrestrial receiver density, FlightAware derives arrival timestamps from flight plans or airline OOOI messaging. Restrictive commercial licensing.
- **Cost Evidence**: $100/mo base for 30-day queries; $500–$3,000+ for historical custom airport reports.
- **Next Practical Step**: Retain on hold. Do not initiate commercial outreach or procurement.

---

### 2.6 Opportunity REC-OPP-06-V2131: OpenSky Network External Outreach
- **Opportunity Title**: OpenSky Academic Research Application & Submission
- **Decision Tier**: **`NO-GO (Operational Task Removed)`**
- **Exact Target**: OpenSky Network Historical Academic Database
- **Evidence Supporting Availability**:
  * OpenSky historical database contains global state vectors, but anonymous queries return HTTP 403 Forbidden.
  * Empirical testing in V2.7 demonstrated zero low-altitude receiver reception within 50 km of Damascus.
- **Actual Demonstrated Date Range**: High-altitude transit overflights only (>FL300).
- **Geographic Scope**: `OSTT_FIR` (Airspace transit only; zero runway coverage at OSDI).
- **Data Granularity**: Raw 1-second state vectors.
- **Known Limitations**: Cannot observe runway touchdown or takeoff movements at Damascus.
- **Mandate Compliance**: In accordance with the user's explicit instructions, **all external outreach, emails to OpenSky, institutional applications, and account creations are prohibited and permanently removed from actionable roadmaps**.
- **Next Practical Step**: Maintain OpenSky in the source catalog as a documented reference source for high-altitude airspace transit physics; initiate zero external outreach.

---

## 3. Authoritative Decision Summary

| Opportunity ID | Target Source | Scope | Demonstrated Range | Granularity | Cost | Decision Tier |
|---|---|---|---|---|---|---|
| **REC-OPP-01-V2131** | Wayback FIDS Snapshot (2026-07-09) | DAM | 2026-07-05 to 2026-09-09 | Scheduled Timetable (1,982 flts) | $0.00 | **GO** |
| **REC-OPP-02-V2131** | Wayback 2024–2025 Schedules | DAM | None (0 snapshots found) | None | $0.00 | **NO-GO** |
| **REC-OPP-03-V2131** | SCAA / MoT Official Publications | DAM / FIR | 2025–2026 (Selected macro periods) | Monthly/Annual Aggregates | $0.00 | **CONDITIONAL GO** |
| **REC-OPP-04-V2131** | FlightRadar24 Airport History | DAM | Rolling 365 Days | Flight-level Tracks | $44.99–$499/yr | **CONDITIONAL GO** |
| **REC-OPP-05-V2131** | FlightAware AeroAPI Report | DAM | Multi-year | Flight-level Tracks | $500–$3,000+ | **CONDITIONAL GO** |
| **REC-OPP-06-V2131** | OpenSky External Outreach | OSTT_FIR | En-route overflights only | State Vectors | Free | **NO-GO (Task Removed)**|
