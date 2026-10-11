# Syrian Airport Data Engine — Version 2.13
# Historical Source Comparison Matrix & Decision Analysis

**Document Identifier**: `docs/V2_13_SOURCE_COMPARISON_MATRIX.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Target Airspace**: Damascus Flight Information Region (`OSTT_FIR`)  
**Scope**: 13-Column Comparative Evaluation of All 18 Investigated Historical Sources  
**Machine-Readable Twin**: `reports/v2_13_historical_source_inventory.csv`  
**Status**: APPROVED DECISION MATRIX  
**Production Integrity Invariant**: `data/damascus_airport.db` SHA-256 verified identical (`c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`).

---

## 1. Standardized 13-Column Source Comparison Matrix

The table below synthesizes the complete technical feasibility investigation across all 18 candidate sources:

| # | Provider Name | Provider Category | Historical Avail. | Earliest Date | Airport-Specific (DAM) | Flight-Level Granularity | Actual Movement Timestamps | Arr/Dep Segregated | Raw Data Export | Auth & Access Req. | Cost Category | DAM Coverage Evidence | Recommendation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **SCAA Publications** | Official Authority | Yes | 2024-01-01 | Yes | No (Macro) | No | Yes | Printed / PDF | Not required | Free | `unverified_quoted` | **GO** |
| 2 | **Syrian Ministry of Transport** | Official Authority | Yes | 2024-01-01 | Yes | No (Macro) | No | Yes | Printed / PDF | Not required | Free | `unverified_quoted` | **GO** |
| 3 | **Internet Archive / Wayback** | Open Digital Archive | Yes | 2024-01-01 | Yes | Yes (FIDS) | Partial | Yes | JSON / HTML via CDX | Not required | Free | `unverified_quoted` | **GO** |
| 4 | **Syria Economic Monitor** | Academic Research | Yes | 2024-01-01 | No (Composite) | No (Daily totals) | No | Yes | CSV in repo | Not required | Free | `verified_in_repo` | **GO** (Composite only) |
| 5 | **OpenSky Network** | Academic Research | Conditional | 2013-01-01 | Yes | Yes | Yes | Yes | SQL / CSV / Parquet | Institutional Auth | Free (Academic) | `empirically_tested_sparse` | **CONDITIONAL GO** |
| 6 | **damairport.gov.sy Portal** | Official Authority | Conditional | Rolling Snapshot | Yes | Yes | No | Yes | Internal JSON API | Not required | Free | `verified_in_repo` | **CONDITIONAL GO** |
| 7 | **FlightRadar24 (Public)** | Free Public | Conditional | Rolling 7 Days | Yes | Yes | Partial | Yes | Web HTML only | Not required | Free | `verified_in_repo` | **CONDITIONAL GO** |
| 8 | **SANA News Agency** | Official Authority | Yes | 2024-01-01 | Yes | Partial | Partial | Partial | Web HTML | Not required | Free | `unverified_quoted` | **CONDITIONAL GO** |
| 9 | **FlightRadar24 (Commercial)** | Commercial Aggregator | Yes | 2020-01-01 | Yes | Yes | Yes | Yes | CSV / JSON API | Paid Subscription | ~$499/yr (Business) | `verified_in_repo` | **CONDITIONAL GO** |
| 10| **FlightAware (AeroAPI)** | Commercial Aggregator | Yes | 2015-01-01 | Yes | Yes | Yes | Yes | REST JSON / CSV | Paid API Key | $100–$1,000+/mo | `blocked_paywall` | **CONDITIONAL GO** |
| 11| **ADS-B.lol** | Free Public | No | Live Only | No | Partial | No | No | Live JSON | Not required | Free | `empirically_tested_sparse` | **NO-GO** |
| 12| **ADSB.fi** | Free Public | No | Live Only | No | Partial | No | No | Live JSON | Not required | Free | `empirically_tested_sparse` | **NO-GO** |
| 13| **ADS-B Exchange (Public)** | Free Public | No | Live Only | No | Partial | No | No | Web Map | Not required | Free | `blocked_paywall` | **NO-GO** |
| 14| **ADS-B Exchange (Commercial)**| Commercial Aggregator | Yes | 2016-01-01 | No | Yes (State vectors) | Yes | No | RapidAPI JSON | Enterprise Key | $100–$1,000/mo | `blocked_paywall` | **NO-GO** |
| 15| **FlightAware (Public)** | Free Public | No | Past 48-72h | Yes | Yes | Partial | Yes | Web HTML | Not required | Free | `blocked_paywall` | **NO-GO** |
| 16| **OurAirports** | Open Aeronautical | N/A | Static Master | Yes | No | No | No | CSV in repo | Not required | Free | `verified_in_repo` | **NO-GO** (Infra only) |
| 17| **Cirium (Ascend / Diio)** | Commercial Aggregator | Yes | 2000-01-01 | Yes | Yes | Partial | Yes | Flat files / API | Enterprise Contract | $10,000–$50,000+/yr | `blocked_paywall` | **NO-GO** |
| 18| **OAG Schedules** | Commercial Aggregator | Yes | 1995-01-01 | Yes | Yes (Schedules) | No | Yes | Flat files / Direct | Enterprise Contract | $5,000–$25,000+/yr | `blocked_paywall` | **NO-GO** |

---

## 2. Recommendation Tier Breakdown & Rationale

### 2.1 The "GO" Tier (Immediate, Non-Invasive, Legally Unrestricted)
The four sources assigned **GO** share essential operational traits: they are accessible without financial cost, require no external account purchases or API key procurement, carry no contractual redistribution lock-in, and provide direct evidentiary value:

1. **SCAA Statistical Bulletins & MoT Reports**: 
   - *Why GO*: The official sovereign authorities are the sole ground-truth providers for Syrian airport-level throughput. Their published figures anchor the macro staging layer (`macro_airport_benchmarks`).
   - *Action Required*: Acquire direct hardcopy scans or digital PDF publications to elevate staged records from Grade C to Grade A.
2. **Internet Archive / Wayback Machine**: 
   - *Why GO*: Completely free, open, public CDX query API (`web.archive.org/cdx/search/cdx`). Allows non-invasive recovery of historical FIDS web pages (`damairport.gov.sy/api/flights.php`) and airline schedule tables without touching third-party servers directly.
   - *Action Required*: Deploy CDX query scripts to harvest snapshots from 2024 to 2026.
3. **Syria Economic Monitor (World Bank)**:
   - *Why GO*: Already verified and integrated into the repository (`historical_daily_movements_2024`). Provides continuous daily composite tracking for early 2024.
   - *Constraint*: Must remain isolated as `DAM_ALP_LTK` composite; disaggregation is strictly forbidden.

### 2.2 The "CONDITIONAL GO" Tier (Valuable but Blocked by Prerequisites)
Six sources are classified as **CONDITIONAL GO**. Each possesses valuable data but cannot be deployed immediately without fulfilling specific prerequisites:

1. **OpenSky Network (Historical Academic Archive)**:
   - *Condition*: Requires approved institutional research credentials from an accredited university.
   - *Constraint*: V2.7 empirical tests proved zero terrestrial ground receivers within 50 km of Damascus. OpenSky data is valuable for quantifying en-route transit flights over Syria (>FL300), but cannot recover runway touchdown timestamps without local ground receivers.
2. **FlightRadar24 (Commercial / Business Subscription)**:
   - *Condition*: Requires commercial subscription purchase ($499/yr for Business tier).
   - *Value*: Unlocks up to 365 days of rolling historical airport arrivals and departures with aircraft registrations and actual timestamps.
3. **FlightAware (AeroAPI)**:
   - *Condition*: Requires enterprise budget approval and custom commercial quotation ($500–$1,500+).
   - *Constraint*: Strict licensing prevents committing raw API payloads directly into public git repositories.
4. **damairport.gov.sy Live Portal & FR24 Public**:
   - *Condition*: Strictly limited to real-time rolling windows (7–15 days). Valuable for continuous ongoing ingestion, but cannot retrospectively recover early 2024 or 2025 without historical web archives.
5. **SANA News Agency**:
   - *Condition*: Secondary narrative source. Requires manual retrieval of canonical permalinks to corroborate operational reopening dates and special flight operations.

### 2.3 The "NO-GO" Tier (Unviable, Redundant, or Cost-Prohibitive)
Eight sources are categorically rejected:

1. **ADS-B.lol & ADSB.fi**: Strictly live-only; no historical airport query endpoints. Proven in V2.7 to lack Damascus terminal receiver coverage.
2. **ADS-B Exchange (Public & Commercial)**: Public site is live-only with paywalled historical queries. Commercial tier requires high monthly fees ($100–$1,000/mo) and delivers raw 1-second coordinate trajectories rather than airport-parsed movements, requiring massive computational reconstruction with low return due to lack of Damascus low-altitude receivers.
3. **FlightAware Public**: Web interface aggressively gates data older than 72 hours behind paid tiers.
4. **OurAirports**: Static airport master metadata only; contains zero flight movements or timetables.
5. **Cirium & OAG**: Enterprise-only pricing models ($5,000–$50,000+/year) designed for global airlines and institutional finance, creating an impossible cost barrier for independent project research.

---

## 3. Data Scope & Licensing Analysis

| Provider | Legal Redistribution Rights | Technical Acquisition Mechanism | Integration Complexity | Primary Risk |
|---|---|---|---|---|
| **SCAA / MoT** | Public sovereign statistics (Permitted under fair-use citation) | Manual PDF / Document ingestion | Low (Staging layer) | PDF availability |
| **Wayback Machine** | Public domain web archive (Permitted for research) | Automated CDX REST API | Medium (HTML parsing) | Crawler cadence gaps |
| **OpenSky Network** | Academic research license (Attribution required; non-commercial) | Trino SQL / Python API | High (State vector analysis) | Lack of local receivers |
| **FlightRadar24 (Comm.)** | Commercial single-user license (Redistribution restricted) | API / Web CSV export | Low (Structured CSV) | Terms of service |
| **FlightAware AeroAPI** | Commercial license (Redistribution strictly restricted) | RESTful JSON API | Low (Structured JSON) | Cost & redistribution lock |
| **Cirium / OAG** | Highly restrictive enterprise NDA | Direct enterprise feed | High (Custom schema) | Extreme financial cost |
