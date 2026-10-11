# Syrian Airport Data Engine

An empirical flight operations processing engine, schedule reconciler, and historical aviation analysis platform focused on **Damascus International Airport (IATA: `DAM`, ICAO: `OSDI`)** and regional Syrian aerodromes (**Aleppo `ALP`, Latakia `LTK`, Deir ez-Zor `DEZ`, Qamishli `KAC`, Palmyra `PMS`**).

The engine collects, normalizes, deduplicates, and audits historical aviation data from airport flight information display systems (FIDS), commercial flight-tracking aggregators, and multilateral economic monitoring datasets. The platform prioritizes source transparency, cryptographic data integrity, and strict separation between published schedules, commercial tracking updates, and regional macro statistics.

---

## 1. Project Overview

- **Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)
- **Regional Scope**: Civil and joint civil-military aerodromes across the Syrian Arab Republic
- **Canonical Timezone**: `Asia/Damascus` (all local timestamps are reconciled to UTC offsets with explicit daylight-saving tracking)
- **Primary Objective**: Provide an auditable, verifiable record of Syrian flight activity while documenting data provenance, observation limits, and temporal coverage boundaries.

---

## 2. Main Capabilities

All capabilities described below are implemented, tested, and operational within the codebase:

### Flight Movement and Schedule Records
- **Canonical Event Store**: 1,830 canonical records stored in a normalized relational database (`data/damascus_airport.db`).
- **Strict Nature Segregation**: Every record is classified into one of four distinct operational natures:
  - `physical_movement` (131 records): Commercially reported operational flights with actual arrival or departure timestamps corroborated across commercial feeds and airport boards.
  - `scheduled_service` (1,662 records): Published commercial timetable display slots without verified operational telemetry.
  - `marketing_codeshare` (34 records): Secondary ticketing partner listings linked to an operating aircraft leg (excluded from movement totals).
  - `unverified_movement` (3 records): Historical board listings lacking independent multi-source corroboration.

### Source Traceability and Evidence Provenance
- **Immutable Evidence Ledger**: An audit table (`event_evidence`) containing 1,508 raw provider observations linked directly to canonical events via foreign keys.
- **Provider Transparency**: Tracks original provider identity, capture method, raw payload snapshots, and timestamp precision for every data point.

### Movement Classification and Identity Resolution
- **Deterministic Leg Matching**: Implements diameter-bounded complete-linkage clustering ($\le 60\text{ min}$) to group corroborated records while preventing transitive chaining across rotations.
- **Turnaround Isolation**: Enforces a $> 180\text{ min}$ threshold to cleanly separate distinct turnarounds and return flights of the same airframe.

### Data Quality and Temporal Validation
- **Automated Validation Rules**: Verifies UTC timestamp consistency, detects invalid null combinations, flags route mismatches, and audits duplicate candidates.
- **Timezone Normalization**: Automatically converts varied source representations into canonical ISO-8601 UTC strings (`YYYY-MM-DDTHH:MM:SSZ`) alongside local Damascus representations.

### Historical Coverage Assessment
- **Timeline Coverage Matrix**: Maps data density across different acquisition epochs, distinguishing between continuous collection periods, point-in-time web archive captures, and macro time series.

### Multi-Airport Comparisons
- **Aerodromes Registry**: Complete geographic, runway, and operational metadata for 7 Syrian airports.
- **Regional Isolation**: Explicitly separates single-airport Damascus records from 3-airport regional time series (`DAM`, `ALP`, `LTK`).

### Research-Grade CSV and JSON Exports
- **Export Streaming**: Dedicated export endpoints for flights, daily movements, and historical records.
- **Cryptographic Sidecars**: Every export can be generated alongside a metadata sidecar containing query parameters, record counts, timestamp boundaries, and analytical caveats.

### REST API and Interactive Interface
- **FastAPI Service**: Comprehensive REST API supporting structured queries, pagination, filtering, and JSON schema compliance.
- **Interactive Data Interface**: Lightweight, accessible web dashboard (`static/index.html`) served at `/` and `/data`, displaying schedule vs. movement comparisons, evidence metrics, and methodology disclosures.

---

## 3. Data Sources and Methodology

The engine ingests data across three distinct methodological tiers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCE TIERS                               │
├──────────────────────────┬───────────────────────┬─────────────────────┤
│ 1. Airport FIDS Boards   │ 2. ADS-B & Aggregators│ 3. Macro Aggregates │
│ (Damascus Airport Portal)│ (AviationStack / FR24)│ (World Bank / SEM)  │
├──────────────────────────┼───────────────────────┼─────────────────────┤
│ • Published Timetables   │ • Commercial Statuses │ • 3-Airport Totals  │
│ • Terminal Display Slots │ • Corroborated Dates  │ • Regional Trends   │
│ • NOT Radar Touchdowns   │ • Patchy Coverage     │ • NOT DAM-Only      │
└──────────────────────────┴───────────────────────┴─────────────────────┘
```

1. **Official Airport FIDS Records**:
   - Retrieved from official airport information portals (e.g., `damairport.gov.sy`) and preserved historical captures.
   - **Methodological Role**: Reflects published commercial passenger timetables and scheduled capacity.
   - **Crucial Distinction**: FIDS records represent timetable listings; they do *not* constitute proof of completed physical runway movements or ground radar contact.

2. **Commercial Flight-Tracking Sources & ADS-B Observations**:
   - Ingested from international commercial flight-tracking aggregators (e.g., AviationStack, Flightradar24).
   - **Methodological Role**: Provides multi-source operational status updates, actual reported times, aircraft registrations, and carrier callsigns.
   - **Crucial Distinction**: ADS-B transponder coverage over Syrian airspace is subject to geographical receiver gaps, terrain masking, and electronic interference. Commercial status updates do *not* constitute direct runway sensor confirmations.

3. **Regional Macro Statistics (`DAM_ALP_LTK`)**:
   - Compiled from multilateral economic monitoring datasets (World Bank / Data Partnership 2024 series).
   - **Methodological Role**: Tracks aggregate civil aviation gateway activity across Syria.
   - **Crucial Distinction**: These datasets combine traffic across Damascus (`DAM`), Aleppo (`ALP`), and Latakia (`LTK`) into a single composite metric. They must *never* be presented as Damascus-only statistics.

---

## 4. Data Limitations

To maintain scientific and analytical integrity, users of this dataset must observe the following documented constraints:

1. **Absence of Record $\ne$ Absence of Flight**:
   Historical coverage contains collection gaps. Missing data for a specific day or period indicates that no verified records were retrieved during that acquisition window, not that flight activity ceased.

2. **Historical DAM-Only Coverage is Incomplete**:
   Continuous, uninterrupted daily flight tracking for Damascus International Airport alone is not available across all historical years. Available records represent specific observation snapshots and collection campaigns.

3. **Schedules Must Not Be Conflated With Completed Movements**:
   A scheduled flight entry in a timetable does not guarantee operational execution. Flights may be canceled, diverted, or unoperated without being reflected in static timetable boards.

4. **Regional Aggregates Must Not Be Cited as Damascus Totals**:
   Data labeled `DAM_ALP_LTK` aggregates three separate airports across Syria. Presenting regional totals as Damascus International Airport traffic is methodologically invalid.

5. **ADS-B Telemetry Sample Limitations**:
   The available sample of commercially tracked flights does not represent a complete census of all operations at Damascus. Ground movements, uncorroborated military transports, and non-transponder aircraft are not captured.

6. **Preservation of Gaps**:
   The platform strictly forbids interpolating missing dates with synthetic or simulated flights. If records do not exist for a given date, the engine reports zero recorded events and flags the coverage gap.

---

## 5. Installation and Usage

### Prerequisites
- Python 3.10 or higher (tested and verified on Python 3.13)
- Windows, macOS, or Linux

### Installation

1. Clone or download the repository:
   ```bash
   git clone https://github.com/<owner>/syrian-airport-data-engine.git
   cd "syrian-airport-data-engine"
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

Start the backend API and web interface:
```bash
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

Once running:
- **Web Interface**: Open `http://127.0.0.1:8000/` or `http://127.0.0.1:8000/data` in any modern web browser.
- **Interactive API Documentation (Swagger)**: Visit `http://127.0.0.1:8000/docs`.
- **Alternative API Documentation (ReDoc)**: Visit `http://127.0.0.1:8000/redoc`.

### Running Tests

Execute the automated test suite using pytest:
```bash
pytest
```

*Note for environments with external pytest plugins installed (e.g. LangSmith):*
```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"; pytest tests/ -v -p no:langsmith
```

All 644 automated unit, integration, and regression tests pass without errors or skipped tests.

---

## 6. Key API Endpoints

The API is organized into logical functional modules:

### Airport & Reference Data
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/airports` | Full Syrian aerodromes registry (DAM, ALP, LTK, DEZ, KAC, PMS, OMDM). |
| `GET` | `/api/airport?airport_id=DAM` | Detailed technical specifications, coordinates, and runway dimensions. |

### Flight Records & Operational Classifications
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/flights` | Paginated canonical flight events with carrier, date, and status filters. |
| `GET` | `/api/movements/comparison` | Breakdown comparing scheduled timetable slots vs. operational events. |
| `GET` | `/api/movements/verified` | Commercially reported operational flights with verified timestamps. |
| `GET` | `/api/movements/scheduled` | Published commercial timetable display records without independent telemetry. |
| `GET` | `/api/movements/daily` | Aggregated daily movement counts for Damascus. |
| `GET` | `/api/movements/multi-airport` | Regional 3-airport (DAM, ALP, LTK) daily time-series records. |

### Provenance, Evidence & Quality Audits
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/events/{event_id}/evidence` | Complete multi-provider raw observation chain for an individual event. |
| `GET` | `/api/evidence/audit` | Summary audit of all underlying evidence observations. |
| `GET` | `/api/coverage/matrix` | Historical coverage matrix by source and date range. |
| `GET` | `/api/quality` | Data quality assessment, completeness rates, and anomaly detection. |

### Research Data Exports
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/export/{dataset}?format=csv` | Stream CSV dataset (`flights`, `daily_movements`, `historical_2024`, `archived_fids_records`). |
| `GET` | `/api/export/{dataset}?format=json` | Stream JSON dataset. |
| `GET` | `/api/export/{dataset}/sidecar` | Download cryptographic verification sidecar with source caveats and record counts. |

---

## 7. Project Structure

```
syria-damascus-airport/
├── data/                               # Protected operational databases and immutable raw captures
│   ├── damascus_airport.db             # Primary canonical SQLite database (read-only mode)
│   ├── archived_fids_staging.db        # Archived FIDS raw staging database
│   ├── archived_fids_analytics.db      # FIDS timetable analytics database
│   ├── archived_fids_history_staging.db# Historical snapshot comparison registry
│   └── raw/                            # Immutable raw JSON/RAW capture payloads from providers
├── src/                                # Application and data processing engine source code
│   ├── api.py                          # FastAPI application, route handlers, and export logic
│   ├── config.py                       # Airport registry, coordinate data, and environment settings
│   ├── database.py                     # Safe read-only SQLite connection manager
│   ├── normalizer.py                   # Timezone conversion, field normalization, and schema mapping
│   ├── timestamp_provenance.py         # Multi-factor movement resolver and diameter clustering
│   ├── aggregator.py                   # Daily aggregation pipelines and export formatters
│   ├── historical_coverage.py          # Coverage timeline builder and regional isolation logic
│   ├── quality_checker.py              # Data quality audit rules and anomaly checks
│   └── adapters/                       # Source-specific ingestion adapters
├── static/                             # Interactive research web dashboard
│   └── index.html                      # Single-page data browser, comparisons, and documentation
├── tests/                              # Comprehensive regression and audit test suite (644 tests)
├── reports/                            # Detailed audit reports, CSV registers, and analytical PDFs
│   ├── Syrian_Airport_Data_Analysis_AR.pdf # Comprehensive analytical report in Arabic (8 pages)
│   ├── INDEPENDENT_ANALYTICAL_REVIEW.md    # Independent statistical and analytical review
│   ├── FINAL_ANALYTICAL_CORRECTIONS.md     # Itemized analytical correction register
│   └── v2_20_12_physical_movement_audit.csv# Itemized audit of all 131 operational events
├── docs/                               # Milestone documentation, specifications, and architecture notes
├── requirements.txt                    # Python project dependencies
├── pytest.ini                          # Test configuration
└── README.md                           # Project documentation
```

---

## 8. Cryptographic Baseline & Data Protection

To guarantee that analytical results remain defensible and reproducible, all database assets are accessed strictly in read-only mode (`mode=ro`). The production database checksum is cryptographically verified:

| File Asset | SHA-256 Checksum | Access Mode |
| :--- | :--- | :--- |
| `data/damascus_airport.db` | `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b` | Read-Only |
| `data/archived_fids_staging.db` | `a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4` | Read-Only |
| `data/archived_fids_analytics.db` | `e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe` | Read-Only |
| `data/archived_fids_history_staging.db` | `39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f` | Read-Only |

No test, script, or API request writes to or modifies these production database assets.

---

## 9. Project Status

The Syrian Airport Data Engine is presented honestly as a **source-traceable, evidence-corroborated aviation research platform with explicitly documented coverage limitations**.

- It does **not** claim complete historical coverage of Syrian civil aviation.
- It does **not** present scheduled timetable listings as confirmed physical runway movements.
- It maintains full transparency regarding data gaps, commercial tracking limitations, and regional dataset scopes.
