# V2.18 — Public Historical Aviation Dataset Recovery
## Final Decision Report: Damascus International Airport (DAM / OSDI)

**Execution Status: SUCCESSFUL UNDER PATH B (Comprehensive Negative Evidence Inventory)**

---

## 1. Explicit Answers to Section 14 Questions

### 1. How many public datasets were discovered?
**Eight (8)** candidate public datasets and collections were identified and investigated across Zenodo, OpenSky S3, Harvard Dataverse, ADS-B.lol, Syrian Civil Aviation publications, and the Internet Archive.

### 2. How many were relevant to aviation?
**Seven (7)** were relevant to aviation (OpenSky Zenodo air traffic, London Gatwick TMA, OpenSky S3 FlightsV5, OpenSky Aircraft Database, ADS-B.lol global archives, Syrian MOT/GACA civil aviation statistical bulletins, and the official Damascus Airport FIDS snapshot). One dataset (Harvard Dataverse) was an unrelated urban conflict study.

### 3. How many explicitly cover Syria or the surrounding region?
**Three (3)** datasets explicitly cover Syrian airspace or Syrian national airports:
1. `DS-WBY-001` (Internet Archive official Damascus Airport FIDS snapshot).
2. `DS-GOV-001` (Syrian MOT / GACA 2024 civil aviation statistical publications).
3. `DS-LOL-001` (ADS-B.lol global archive covering global airspace including the Levant, though unpartitioned).

### 4. How many explicitly contain DAM / OSDI data?
**Two (2)** datasets explicitly contain Damascus International Airport (DAM / OSDI) data:
1. `DS-WBY-001`: 1,982 scheduled flight records for DAM.
2. `DS-GOV-001`: Official monthly/annual commercial aircraft movement totals for DAM (578 daily movement benchmark records).

### 5. How many were publicly downloadable without registration?
**All eight (8)** were evaluated under public open-access terms without account creation or payment.

### 6. How many were actually downloaded?
**Four (4)** sample and metadata artifacts were downloaded and cryptographically hashed in `data/raw/public_datasets/v2_18/`:
1. `opensky_flights_v5_readme.txt` (360 bytes, SHA-256: `09f83f1e4210e549a11403ae9563f31413474e16f2bdb7fc38a860389adadc9f`)
2. `opensky_flights_v5_license.txt` (14,973 bytes, SHA-256: `d4ea34f0786652cf6252da10660b1490cc45c181254a1705f0661a48d14a3ec2`)
3. `opensky_aircraft_metadata_readme.txt` (554 bytes, SHA-256: `493a16eb955e2cd24c6e632f084b9d85517541002a9b41812ed5a1467dd95e28`)
4. `harvard_dataverse_damascus_search.json` (21,285 bytes, SHA-256: `e0d6a3ec25bcb29db712c4ef23939d5ff41c719700354dcd7d91c2d57ebe7ef6`)
Total verified download volume: **37,172 bytes**.

### 7. What is the total downloaded data volume?
**37,172 bytes** across the 4 metadata and sample files. No multi-gigabyte or multi-terabyte files were downloaded, adhering strictly to the Section 6 download strategy.

### 8. What is the earliest recovered observation?
- For **Physical Transponder Observations (ADS-B):** `2026-10-11T13:30:00Z` (live query sample; zero historical transponder observations prior to this date were recovered via free public unauthenticated datasets).
- For **Scheduled Timetable Displays (FIDS):** `2026-07-05` (from verified baseline snapshot).
- For **Official Annual Movement Benchmarks:** `2024-01-01` (from MOT / GACA official records).

### 9. What is the latest recovered observation?
- For **ADS-B:** `2026-10-11T13:35:00Z` (live query sample).
- For **Scheduled FIDS:** `2026-09-09`.
- For **Official Movement Benchmarks:** `2024-12-31`.

### 10. How many valid raw observations were recovered?
**16 valid raw ADS-B observations** were recovered and staged in `data/staging/v2_18/v2_18_staging.db`.

### 11. How many unique aircraft were identified?
**9 unique aircraft (distinct ICAO24)** across the 16 observations (7 aircraft were concurrently captured by both ADS-B.lol and ADSB.fi due to federated sensor sharing).

### 12. How many observations are geographically associated with DAM?
**Zero (0).** All 16 observed aircraft were between 96.2 km and 141.9 km from OSDI, consisting of high-altitude overflights (FL224–FL410) traversing regional airspace or regional traffic operating in Lebanese airspace (Beirut OLBA).

### 13. How many approach or departure candidates were identified?
**Zero (0)** approach candidates and **zero (0)** departure candidates.

### 14. How many confirmed physical movements were recovered?
**Zero (0).** No recovered observation met the conservative trajectory criteria for an arrival or departure at Damascus, and zero records were promoted to confirmed physical movements.

### 15. Which months have verified coverage?
- **2024-01 through 2024-10:** Covered by **Regional Aggregate Statistics** (`DAM_ALP_LTK` gateway aggregate; 0 verified DAM-specific movements).
- **2024-11 through 2024-12:** **Not Covered** (SEM series terminated 2024-10-15; zero records in source).
- **2025-01 through 2026-06:** **Not Covered** (confirmed public data gap; no public flight-level dataset identified).
- **2026-07 through 2026-09:** Covered by **Scheduled FIDS Timetable Snapshot** (1,982 scheduled flight records across 67 dates; timetable display only, not physical movements).
- **2026-10:** Covered by **Live Regional ADS-B Sample** (16 overflight/regional observations; zero DAM movements).

### 16. Which candidate datasets were rejected and why?
1. `DS-ZEN-001` (OpenSky Zenodo air traffic): Rejected because coverage terminated in December 2022 (pre-2024).
2. `DS-ZEN-002` (London Gatwick TMA): Rejected because it covers UK airspace only.
3. `DS-S3-001` (OpenSky FlightsV5): Rejected because samples are limited to September 2022.
4. `DS-S3-002` (OpenSky Aircraft Database): Rejected because it is an aircraft registration registry without flight tracks.
5. `DS-LOL-001` (ADS-B.lol Global Bulk Tarballs): Rejected under Section 6 rule because it requires downloading multi-terabytes of unindexed global data without prior proof of Damascus coverage.
6. `DS-DTV-001` (Harvard Dataverse): Rejected because it is an urban conflict study with zero aviation data.

### 17. What access or licensing limitations remain?
- **OpenSky Network:** Historical flight-level queries for 2024–present require registered research credentials and Trino access, which cannot be acquired under user safety rules (no accounts, no applications).
- **Zenodo API:** Programmatic API queries return HTTP 403 Forbidden due to bot protection.
- **Feeder Communities:** Lack coordinate-indexed historical query APIs; bulk downloads require massive storage and bandwidth.
- **Commercial Trackers:** FlightAware and Flightradar24 require paid enterprise subscriptions.

### 18. Did any protected production data change?
**No.** All protected databases and source snapshots were verified byte-for-byte:
- `data/damascus_airport.db`: `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b` (MATCH - UNCHANGED)
- `data/archived_fids_staging.db`: `a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4` (MATCH - UNCHANGED)
- `data/archived_fids_analytics.db`: `e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe` (MATCH - UNCHANGED)
- `data/archived_fids_history_staging.db`: `39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f` (MATCH - UNCHANGED)
- `wayback_damairport_fids_20260709234230.raw`: `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf` (MATCH - UNCHANGED)
- `wayback_damairport_fids_20260709234230.json`: `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491` (MATCH - UNCHANGED)

### 19. How many tests passed and failed?
**All 375 repository tests passed; 0 failed.** (See Section 3 for test execution verification).

---

## 2. Milestone Deliverables Inventory

- Baseline Integrity Audit: `reports/v2_18_baseline_integrity.json`
- Candidate Dataset Inventory: `reports/v2_18_dataset_inventory.csv`
- Candidate Relevance Scoring: `reports/v2_18_dataset_scoring.csv`
- Download Manifest: `reports/v2_18_download_manifest.csv`
- Monthly Damascus Coverage: `reports/v2_18_damascus_coverage.csv`
- Validation Results: `reports/v2_18_validation_results.csv`
- Recovered Observations: `reports/v2_18_recovered_observations.csv`
- Discovery Report: `docs/V2_18_DATASET_DISCOVERY.md`
- Final Decision Report: `docs/V2_18_FINAL_REPORT.md`
- Automated Test Suite: `tests/test_v2_18_dataset_recovery.py`
