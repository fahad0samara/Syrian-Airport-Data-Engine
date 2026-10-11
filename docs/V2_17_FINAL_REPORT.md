# V2.17 — Damascus Historical Aviation Data Expansion
## Historical FIDS Archive + ADS-B Observation Research: Final Decision Report

### Mission Overview
Version 2.17 executed a comprehensive historical aviation data acquisition and research initiative for Damascus International Airport (**DAM** / **OSDI**):
- **Track A:** Historical official FIDS archive discovery, validation, and snapshot comparison.
- **Track B:** Historical ADS-B aircraft observation discovery, access classification, and airport association research.

All operations complied strictly with project safety rules: zero modification to protected databases, zero synthetic movement fabrication, strict isolation of staging datasets, zero account creation, and strict non-circumvention of rate limits.

---

## 1. Explicit Answers to Section 10 Questions

### 1. How many new FIDS captures were discovered?
**Four (4) new FIDS capture variants were discovered** in the Wayback Machine CDX index in addition to the single known baseline snapshot:
- `snap_wayback_20260720034051` (`?paged=1&page=1&dir=all&wfloor=2026-07-17&dexact=2026-07-20`)
- `snap_wayback_20260802011114` (`?paged=1&page=auto&dir=arrival&wfloor=2026-07-30&dexact=2026-08-02`)
- `snap_wayback_20260901001238` (`?paged=1&page=auto&dir=arrival&wfloor=2026-08-29&dexact=2026-09-01`)
- `snap_wayback_20260909200343` (`?paged=1&page=auto&dir=arrival&wfloor=2026-09-06&dexact=2026-09-09`)
Total historical captures discovered across the DAM endpoint family is **five (5)**. Zero captures were discoverable for regional Syrian airport endpoints (Aleppo, Qamishli, Deir ez-Zor).

### 2. How many were successfully retrieved?
**Zero (0) new captures were retrieved in this milestone.**
When replay retrieval was requested for the four discovered capture variants, the Wayback Machine returned `HTTP 429: Too Many Requests`. Under the mandatory safety rules (*"If a source returns 403, 429, authentication requirements, or access restrictions, record the result and stop that acquisition attempt. Do not attempt circumvention"*), acquisition was immediately halted without circumvention.
The single verified baseline snapshot (`20260709234230`) remains the sole locally acquired and validated historical FIDS snapshot.

### 3. How many were complete snapshots?
**One (1) complete snapshot.**
Only the baseline capture `snap_wayback_20260709234230` (`https://damairport.gov.sy/api/flights.php`) is an unfiltered, complete timetable snapshot containing all airlines, directions, and routes (1,982 records).

### 4. How many were filtered snapshots?
**Four (4) filtered snapshots.**
All four newly discovered captures contained URL query parameters restricting the returned flights:
- `20260720034051`: Date-filtered (`wfloor=2026-07-17; dexact=2026-07-20`) and paginated.
- `20260802011114`: Direction-filtered (`dir=arrival`), date-filtered (`wfloor=2026-07-30; dexact=2026-08-02`), and paginated.
- `20260901001238`: Direction-filtered (`dir=arrival`), date-filtered (`wfloor=2026-08-29; dexact=2026-09-01`), and paginated.
- `20260909200343`: Direction-filtered (`dir=arrival`), date-filtered (`wfloor=2026-09-06; dexact=2026-09-09`), and paginated.

### 5. How many new scheduled records were recovered?
**Zero (0) new scheduled records were recovered.**
Because the four filtered captures were blocked by Wayback HTTP 429 rate limiting, no new records could be extracted without violating non-circumvention rules. The verified historical baseline remains **1,982 records**.

### 6. What new scheduled service date coverage was added?
**Zero (0) new scheduled dates were added.**
Historical date coverage remains strictly the **67 distinct calendar dates** established by the baseline snapshot (2026-07-05 through 2026-09-09).

### 7. Which free ADS-B sources provide accessible historical data?
**None.**
None among the tested unauthenticated public endpoints provided accessible historical flight-level or state-vector queries for Damascus airport on 2024-01-01:
- **OpenSky Network:** Historical flight and state queries returned `HTTP 403 Forbidden` (`"Authenticate to get historical data"` / `"You cannot access historical flights"`). Historical queries require approved research accounts (credentials required), which cannot be created under user safety constraints.
- **ADS-B.lol:** The tested per-point historical query route returned `HTTP 503 Service Unavailable`. ADS-B.lol provides daily global bulk archive tarballs on cloud storage, but not a verified per-point historical query API.
- **ADSB.fi:** The tested historical route returned `HTTP 400 Bad Request` (unsupported route).
- **Airplanes.live:** Provides documented public endpoints for live streaming telemetry only.
*Audit Principle:* HTTP 400 and 503 endpoint responses reflect routing or interface limitations and must not be treated as proof that a provider maintains zero historical telemetry in other repositories.

### 8. What is the earliest accessible historical ADS-B observation?
**None accessible via unauthenticated query APIs.**
Because unauthenticated historical queries return HTTP 403/503/400, the earliest accessible empirical observations are from the **live telemetry window** on `2026-10-11T13:30:00Z`.

### 9. What is the latest accessible observation?
The latest accessible empirical observation is from the active live collection on `2026-10-11T13:35:00Z`.

### 10. Are observations actually associated with DAM?
**No.**
None of the observed aircraft fixes within the 150 km radial query around Damascus are associated with DAM surface movements, arrivals, or departures. Every detected aircraft is either:
1. A high-altitude transcontinental overflight traversing Syrian airspace at flight levels FL220 to FL400; or
2. A regional operation within neighboring Lebanese airspace (such as flights departing or approaching Beirut Rafic Hariri International Airport, OLBA).

### 11. How many unique observations and aircraft were recovered?
- **Total Staged Live Observations:** 16 observations.
- **Unique Aircraft (ICAO24):** 9 unique aircraft (all 7 aircraft reported by ADSB.fi were concurrently reported by ADS-B.lol due to federated community sensor sharing).
All raw payloads and manifest files have been cryptographically preserved in `data/raw/adsb/v2_17/` with verified SHA-256 hashes.

### 12. How many records are only overflights or regional observations?
**All 16 observations (100%) are overflights or regional observations.**
- Overflight Observations: 15 (high-altitude cruise FL224–FL410)
- Regional Observations: 1 (MEA428 at 10,175 ft climbing out of Beirut OLBA in Lebanese airspace)
- Airport Surface Observations: 0
- Approach Candidates: 0
- Departure Candidates: 0
In accordance with conservative association rules, overflights and regional fixes are strictly excluded from Damascus airport movement counts.

### 13. Which sources have no usable historical access?
1. **ADSB.fi:** No historical API capability (HTTP 400).
2. **Airplanes.live:** Live feed only; no historical endpoint.
3. **ADS-B.lol:** No queryable per-point historical API (HTTP 503); only unfiltered global daily bulk archive dumps.
4. **OpenSky Network (Unauthenticated):** Historical queries older than 1 hour are blocked with HTTP 403 Forbidden.

### 14. What data gaps remain?
1. **Historical ADS-B Airspace Gap:** Unobserved historical ADS-B data for Damascus airspace from 2024-01-01 to 2026-10-10 under unauthenticated access tiers.
2. **Damascus Low-Altitude Receiver Coverage (Unverified Hypothesis):** It has been hypothesized that western terrain (Anti-Lebanon range) could impede VHF line-of-sight from regional receivers to low-altitude traffic at OSDI (2,020 ft). However, absent a direct RF propagation study or receiver site audit, this is recorded strictly as an unverified hypothesis and NOT a factual conclusion.
3. **FIDS Calendar Coverage Boundary:** Official FIDS scheduled coverage is currently bounded to 2026-07-05 through 2026-09-09. Dates outside this window remain unrepresented in official timetable archives.
4. **Regional Syrian Airport Archives:** Complete absence of historical FIDS API captures for Aleppo, Qamishli, and Deir ez-Zor airports.

### 15. Were any records promoted to confirmed physical movements?
**Zero (0) records were promoted.**
Under the project's evidence standards:
- Scheduled FIDS records are strictly classified as timetable display records, NEVER physical movements.
- High-altitude overflights and regional Lebanese flights are strictly excluded from Damascus airport movement metrics.
- No synthetic or estimated physical flight movements were created.

### 16. Did any protected database or original snapshot change?
**No.**
Every protected database and baseline snapshot was hash-verified before and after execution:
- `data/damascus_airport.db`: `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b` (MATCH - UNCHANGED)
- `data/archived_fids_staging.db`: `a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4` (MATCH - UNCHANGED)
- `data/archived_fids_analytics.db`: `e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe` (MATCH - UNCHANGED)
- `data/archived_fids_history_staging.db`: `39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f` (MATCH - UNCHANGED)
- `wayback_damairport_fids_20260709234230.raw`: `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf` (MATCH - UNCHANGED)
- `wayback_damairport_fids_20260709234230.json`: `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491` (MATCH - UNCHANGED)

### 17. How many tests passed and failed?
**All 350+ tests passed; 0 failed.** (See Section 3 for test execution verification).

---

## 2. Inventory of V2.17 Generated Deliverables

### Track A (Historical FIDS):
- Isolated Database: `data/staging/v2_17_fids/v2_17_fids_staging.db`
- Reports:
  * `reports/v2_17_fids_capture_inventory.csv`
  * `reports/v2_17_fids_capture_validation.csv`
  * `reports/v2_17_fids_coverage.csv`
  * `reports/v2_17_fids_snapshot_comparison.csv`
  * `docs/V2_17_FIDS_ARCHIVE_FINDINGS.md`

### Track B (ADS-B Research):
- Raw Archive & Manifest: `data/raw/adsb/v2_17/`
- Isolated Database: `data/staging/v2_17_adsb/v2_17_adsb_staging.db`
- Reports:
  * `reports/v2_17_adsb_source_inventory.csv`
  * `reports/v2_17_adsb_historical_coverage.csv`
  * `reports/v2_17_adsb_observation_validation.csv`
  * `reports/v2_17_adsb_airport_association.csv`
  * `docs/V2_17_ADSB_SOURCE_FINDINGS.md`

### Unified Architecture & Governance:
- Protected Baseline Hash Audit: `reports/v2_17_baseline_integrity.json`
- Unified Source Registry: `reports/v2_17_unified_source_registry.csv` and `.json`
- Final Comprehensive Report: `docs/V2_17_FINAL_REPORT.md`

---

## 3. Testing & Verification Summary

A dedicated regression test suite was implemented in `tests/test_v2_17_historical_expansion.py` enforcing all 20 specific validation areas defined in Section 9 of the V2.17 specification. Full test suite execution across all modules confirms complete stability with zero regressions.
