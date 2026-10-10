# Damascus International Airport (DAM / OSDI) — Data Engine

An empirical flight operations data engine and historical analysis platform for **Damascus International Airport, Syria (IATA: `DAM`, ICAO: `OSDI`)**.

This project discovers, acquires, normalizes, deduplicates, and audits real flight operations from multiple web-accessible sources. It does not fabricate sample records or invent synthetic dates.

---

## 🚀 Key Features

1. **Normalized Flight-Events Database (`SQLite`)**:
   - `flight_events`: 266 deduplicated, cross-validated physical flight operations with aircraft registration, ICAO24 hex code, airline metadata, route classification, and timestamps.
   - `damascus_daily_movements`: Daily aggregated movement counts (arrivals, departures, total, landed, cancelled, unique aircraft, airlines) with no synthetic zeros.
   - `historical_daily_movements_2024`: 578 operational records covering 2024-01-01 to 2024-10-15 extracted from the World Bank / Data Partnership research notebook.
   - `data_quality_audit`: Automated audit trail enforcing 7 integrity rules.

2. **Deduplication & Provenance Engine (`src/normalizer.py`)**:
   - **Timezone Reconciliation**: Identifies and adjusts AviationStack's local Damascus wall-clock times (`Asia/Damascus`, UTC+3) labeled with `+00:00` into true UTC, matching Flightradar24's unix timestamps to the exact minute.
   - **Multi-Source Fusion**: Matches flights on `(movement_type, normalized_flight_number, flight_date, hourly_slot)` to merge complementary attributes: Flightradar24 provides aircraft model, hex, registration, and actual timestamps; AviationStack provides airport terminal, timezone, and airline metadata. 130 duplicate flight entries were pruned and merged.

3. **REST API (`src/api.py`)**:
   - Built on FastAPI with full filtering, pagination, statistics, and streaming exports.
   - `/api/flights`: Search and filter flight events.
   - `/api/movements/daily`: Damascus-specific daily operational counts.
   - `/api/movements/historical-2024`: 2024 historical operational series.
   - `/api/movements/stats`: Airport KPIs, top destinations, top airlines, unique aircraft.
   - `/api/coverage`: Evidence-based provider coverage audit in JSON.
   - `/api/quality`: Live automated data quality check results.
   - `/api/export/{dataset}`: Download CSV or JSON exports.
   - `/api/airport`: Airfield specifications and runway designations.

4. **Minimal Data Tab UI (`static/index.html`)**:
   - Web application accessible at `http://127.0.0.1:8000/` or `/data`.
   - Interactive tables for flight events, daily movements, and 2024 historical trends.
   - Visual coverage matrix and quality checklist audit.
   - Direct download buttons for CSV and JSON datasets.

5. **Evidence-Based Coverage & Missing-Date Reporting**:
   - `reports/coverage_report.csv`
   - `reports/coverage_report.json`
   - `reports/coverage_summary.md`

---

## 📂 Project Structure

```
syria damascus airport/
├── data/
│   ├── damascus_airport.db                     # SQLite normalized operational database
│   ├── raw/
│   │   ├── aviationstack_dam_departures_raw.json # Raw AviationStack departures
│   │   ├── aviationstack_dam_arrivals_raw.json   # Raw AviationStack arrivals
│   │   ├── flightradar24_dam_departures_raw.json # Raw Flightradar24 departures
│   │   ├── flightradar24_dam_arrivals_raw.json   # Raw Flightradar24 arrivals
│   │   ├── daily_departures_from_dam__alp_and_ltk.json # Syria Economic Monitor 2024 time series
│   │   ├── daily_arrivals_to_dam__alp_and_ltk.json     # Syria Economic Monitor 2024 time series
│   │   └── damascus_airport_metadata.json        # Airfield and runway specifications
│   └── processed/
│       ├── damascus_flight_events.csv & .json    # 266 normalized physical flight records
│       ├── damascus_daily_movements.csv & .json  # Aggregated daily movements (no synthetic zeros)
│       └── historical_daily_movements_2024.csv & .json # 2024 research operational time series
├── src/
│   ├── config.py                               # Settings and airfield constants
│   ├── database.py                             # SQLite schema and connection manager
│   ├── normalizer.py                           # Timezone reconciliation and deduplication
│   ├── aggregator.py                           # Movement aggregation and export pipeline
│   ├── quality_checker.py                      # 7-rule integrity auditor
│   ├── coverage.py                             # Coverage report generator
│   └── api.py                                  # FastAPI REST application
├── static/
│   └── index.html                              # Interactive Data Tab UI
├── scripts/
│   ├── fetch_raw_data.py                       # Live and historical data fetcher
│   ├── backfill.py                             # Historical backfill execution
│   └── daily_refresh.py                        # Automated daily refresh job
├── reports/
│   ├── coverage_report.csv                     # Machine-readable coverage metrics
│   ├── coverage_report.json                    # Structured coverage data
│   ├── coverage_summary.md                     # Markdown coverage report
│   └── quality_audit.json                      # Automated data quality audit results
├── tests/
│   ├── test_engine.py                          # Normalization & aggregation tests
│   ├── test_quality.py                         # Quality assurance & guardrail tests
│   └── test_api.py                             # REST API integration tests
└── pytest.ini                                  # Test runner configuration
```

---

## 🛠️ Usage Instructions

### 1. Run the REST API & Data Tab
```bash
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```
Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in any web browser to view the Data Tab UI.

### 2. Run the Historical Backfill
```bash
python scripts/backfill.py
```

### 3. Run the Daily Refresh Job
```bash
python scripts/daily_refresh.py
```

### 4. Run Automated Tests
```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"; python -m pytest -v
```

---

## 📊 Summary of Verified Evidence

| Metric / Dataset | Earliest Verified Date | Latest Verified Date | Verified Records | Source Provenance |
| :--- | :--- | :--- | :--- | :--- |
| **Historical Daily Operations (DAM, ALP, LTK)** | **2024-01-01** | **2024-10-15** | 578 daily rows (289 dep, 289 arr) | Syria Economic Monitor (World Bank / Data Partnership) |
| **Individual Damascus Flight Events** | **2026-10-08** | **2026-10-12** | 266 deduplicated flights | AviationStack & Flightradar24 |
| **Damascus Daily Movements** | **2026-10-08** | **2026-10-12** | 5 daily summary records | Damascus Data Engine |
| **Unique Aircraft Tracked** | 2026-10-08 | 2026-10-12 | 98 distinct airframes | Flightradar24 & AviationStack hex/registration |
| **Aeronautical Metadata** | Static Verified Registry | Static Verified Registry | Runways 05R/23L & 05L/23R | OurAirports / Syrian eAIP |
