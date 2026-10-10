# Damascus International Airport (DAM / OSDI) Historical Flight Coverage Report

**Generated Date**: 2026-10-10  
**Target Airport**: Damascus International Airport, Syria (IATA: `DAM`, ICAO: `OSDI`)  
**Coordinates**: Lat 33.415001° N, Lon 36.515202° E | Elevation: 2,021 ft  
**Evaluation Range**: 2024-01-01 to Latest Available Date  

---

## 1. Executive Summary & Verification Classification

This report provides an empirical, evidence-based assessment of real web-accessible flight data for Damascus International Airport, distinguishing verified retrieved records from vendor marketing claims, paywalled archives, and data outages.

### Data Status Categories:
1. **Historical Data Actually Retrieved**:
   - **Syria Economic Monitor (World Bank / Data Partnership)**: 289 daily time-series records from **2024-01-01 to 2024-10-15** detailing departures and arrivals by operational status (`active`, `cancelled`, `diverted`, `landed`, `scheduled`, `unknown`) across Syria's international gateways (DAM, ALP, LTK). Extracted directly from serialized scientific Bokeh data sources embedded in the published research notebook.
   - **AviationStack Live API**: 182 raw flight records for DAM retrieved via authenticated API queries across departures and arrivals.
   - **Flightradar24 Airport API**: 214 flight records for DAM retrieved across departures and arrivals, including aircraft registrations, ICAO24 hexes, routes, and actual timestamps.
   - **Unified Damascus Event Engine**: 266 deduplicated, cross-validated individual flight events for Damascus International Airport, correcting local UTC+3 wall-clock offsets and merging multi-source aircraft metadata.
   - **OurAirports Infrastructure Registry**: Comprehensive airfield specifications, coordinates, and runway dimensions (Runway 05R/23L: 11,811 ft, Runway 05L/23R: 9,843 ft).

2. **Periods That Require Paid Access**:
   - **AviationStack Historical API**: Historical dates prior to the rolling window (e.g., querying `flight_date=2024-01-05`) return `HTTP 403 Forbidden` (`code: function_access_restricted`). Historical queries require a paid enterprise subscription ($500+/year).
   - **Flightradar24 Historical Archives**: Flight data older than 7 days is restricted to Flightradar24 Business/Enterprise subscribers.
   - **FlightAware AeroAPI**: Historical queries older than 7 days require a paid AeroAPI tier ($100+/month).
   - **ADS-B Exchange**: Historical REST queries require a RapidAPI enterprise subscription ($100-$1,000/month).

3. **Periods Requiring Institutional Access**:
   - **OpenSky Network**: Anonymous historical endpoints (`/flights/departure?airport=OSDI` and `/flights/arrival`) return `HTTP 403: You cannot access historical flights`. Requires academic researcher credentials and Trino cluster access.

4. **Periods With Documented Outages & Missing Dates**:
   - In the Syria Economic Monitor AviationStack 2024 dataset, 8 dates had zero records due to documented provider outages:
     - `2024-01-28`, `2024-01-29`, `2024-01-30` (3 days)
     - `2024-04-29`, `2024-04-30` (2 days)
     - `2024-06-07`, `2024-06-08`, `2024-06-09` (3 days)
     *As per data engineering standards, these missing dates are recorded as missing/null and never filled with synthetic zeros.*
   - Operational shutdown: Syrian airspace and Damascus airport were closed by SCAA between **December 8 and December 15, 2024** following the fall of the Assad regime, with commercial operations restricted until **January 1, 2025**.

---

## 2. Source-by-Source Empirical Audit

| Source | Metric | Earliest Verified | Latest Verified | Retrieved Records | Verified Status | Licensing / Terms |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Syria Economic Monitor** | Daily operations by status (DAM, ALP, LTK) | **2024-01-01** | **2024-10-15** | 289 daily records (dep), 289 daily records (arr) | **Retrieved & Verified** | Open research / CC-BY |
| **AviationStack Live API** | Flight events, airlines, status, scheduled times | **2026-10-09** | **2026-10-10** | 182 raw records (90 dep, 92 arr) | **Retrieved & Verified** | AviationStack API terms |
| **Flightradar24 API** | Flight events, aircraft hex/reg, routes, actual times | **2026-10-08** | **2026-10-11** | 214 raw records (107 dep, 107 arr) | **Retrieved & Verified** | FR24 proprietary / research |
| **OpenSky Network** | ADS-B historical flights | None | None | 0 (HTTP 403 Forbidden) | **Blocked** | Academic Trino required |
| **ADS-B Exchange** | Raw ADS-B state vectors | None | None | 0 (Paywalled) | **Blocked** | Enterprise API key required |
| **FlightAware AeroAPI** | Flight schedules & tracking | None | None | 0 (Paywalled) | **Blocked** | Commercial tier required |
| **Syrian Civil Aviation** | NOTAMs & operational milestones | 2024-12-08 | 2025-01-01 | Event milestones | **Verified Qualitative** | Official SCAA notices |
| **OurAirports** | Airfield coordinates, runways, metadata | Static | Static | Complete metadata | **Retrieved & Verified** | Public Domain (CC0) |

---

## 3. Data Integrity & Deduplication Rules

1. **Timezone Reconciliation**: AviationStack provides Damascus flight wall-clock times labeled with `+00:00`. Damascus is located in `Asia/Damascus` (UTC+3). The engine normalizes AviationStack wall-clock times to true UTC by subtracting 3 hours, bringing them into exact minute-level alignment with Flightradar24's epoch timestamps.
2. **Defensible Deduplication**: Matches flights on `(movement_type, normalized_flight_number, flight_date, hourly_slot)`. Merges complementary attributes: Flightradar24 provides aircraft model, hex, registration, and actual timestamps; AviationStack provides airport terminal, timezone, and airline metadata. 130 overlapping records were pruned and merged, yielding 266 distinct Damascus flight operations.
3. **No Synthetic Zero Filling**: Missing provider dates are explicitly flagged and preserved as gaps rather than assumed to be zero operations.
4. **No Speculative Passenger/Cargo Estimates**: Flight movement metrics represent observed aircraft operations only. No fictitious passenger counts or cargo tonnages are manufactured from seat capacities.

---

## 4. Deliverables Produced

- `data/damascus_airport.db`: SQLite database storing normalized flight events, Damascus daily movements, and 2024 historical series.
- `data/processed/damascus_flight_events.csv` & `.json`: Normalized Damascus flight events with provenance.
- `data/processed/damascus_daily_movements.csv` & `.json`: Aggregated daily Damascus movements.
- `data/processed/historical_daily_movements_2024.csv` & `.json`: Syria Economic Monitor 2024 daily operations.
- `reports/coverage_report.csv` & `.json`: Machine-readable coverage audit.
- `reports/quality_audit.json`: Automated data quality rules validation report.
