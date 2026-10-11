# V2.17.1 — Final Evidence and Classification Audit Report

**Executive Decision: ACCEPTED WITH LIMITATIONS**

---

## 1. Objective and Scope of Audit

Version 2.17.1 conducted a forensic evidence and classification audit of the Version 2.17 Damascus Historical Aviation Data Expansion.
In accordance with strict safety mandates:
- No new data acquisition was attempted.
- No HTTP 429-blocked captures were re-queried.
- Zero modifications were made to the production database `data/damascus_airport.db` (`c512fd29...`).
- Zero modifications were made to baseline staging or analytics databases.
- All conclusions were subjected to evidence-backed audit and strict semantic discipline.

---

## 2. Audit Item 1: Wayback Capture Classification

### 2.1 Forensic CDX and Payload Review
The Internet Archive CDX metadata and local file assets for all five (5) Damascus Airport endpoint captures were re-examined:

| Capture ID | Timestamp | Original URL | Replay Status | Local Body Available? | V2.17 Initial Classification | V2.17.1 Corrected Classification | Audit Rationale |
|---|---|---|---|---|---|---|---|
| `snap_wayback_20260709234230` | 2026-07-09T23:42:30Z | `https://damairport.gov.sy/api/flights.php` | Retrieved (200 OK) | **YES** (68,891 B raw / 644,922 B JSON) | Complete | **Complete** | Local response body is available and verified. Contains 1,982 records (993 arr, 989 dep) spanning 67 dates without pagination cuts. |
| `snap_wayback_20260720034051` | 2026-07-20T03:40:51Z | `?paged=1&page=1&dir=all&wfloor=...&dexact=...` | Rate Limited (429) | **NO** | Filtered | **Unknown** | Response body is absent locally. A URL containing `page=1` must not be assumed complete or filtered without inspecting the actual server response. |
| `snap_wayback_20260802011114` | 2026-08-02T01:11:14Z | `?paged=1&page=auto&dir=arrival&wfloor=...&dexact=...` | Rate Limited (429) | **NO** | Filtered | **Unknown** | Response body is absent locally due to HTTP 429. Completeness cannot be established. |
| `snap_wayback_20260901001238` | 2026-09-01T00:12:38Z | `?paged=1&page=auto&dir=arrival&wfloor=...&dexact=...` | Rate Limited (429) | **NO** | Filtered | **Unknown** | Response body is absent locally due to HTTP 429. Completeness cannot be established. |
| `snap_wayback_20260909200343` | 2026-09-09T20:03:43Z | `?paged=1&page=auto&dir=arrival&wfloor=...&dexact=...` | Rate Limited (429) | **NO** | Filtered | **Unknown** | Response body is absent locally due to HTTP 429. Completeness cannot be established. |

### 2.2 Key Corrective Principle
- **Rule Enforced:** *"If response content is unavailable, classify completeness as `unknown`, not `complete` or `filtered`."*
- **Correction Applied:** In V2.17, the four unretrieved captures were labeled as `filtered_...` based solely on their URL query string. The audit corrected this assumption: without inspecting the response payload, it cannot be determined whether the server returned filtered results, full results, an error message, or ignored parameters. Their completeness status is now strictly recorded as **`unknown`**.
- Detailed register: `reports/v2_17_1_wayback_classification_audit.csv`.

---

## 3. Audit Item 2: ADS-B Historical Availability Claims

### 3.1 Retraction of Overbroad Generalizations
In V2.17, the statement *"no free ADS-B historical source exists"* was overly broad.
The audit replaced this generalization with a scope-limited statement describing exactly which providers, endpoints, access methods, and dates were tested.

### 3.2 Specific Provider Access Classifications
Under V2.17.1, evidence of provider accessibility is partitioned into six distinct categories:

1. **Authentication Required — OpenSky Network (Historical REST API)**
   - *Endpoints Tested:* `api/flights/arrival?airport=OSDI`, `api/flights/departure`, `api/states/all?time=1704067200`.
   - *Tested Date:* `2024-01-01`.
   - *Response:* `HTTP 403 Forbidden` (`"Authenticate to get historical data"` / `"You cannot access historical flights"`).
   - *Audit Finding:* Historical data exists within OpenSky's research cluster (Impala/Trino), but unauthenticated REST access is blocked. The access limitation is **authentication/credentials required**, not absence of historical data. Safety rules prohibit account registration.
2. **HTTP Error / Temporary Service Failure — ADS-B.lol**
   - *Endpoint Tested:* `api/v2/history/point/33.4115/36.5156/81/2024-01-01`.
   - *Response:* `HTTP 503 Service Temporarily Unavailable`.
   - *Audit Finding:* The 503 error indicates that the tested per-point historical query route failed or is not hosted. However, **HTTP 503 alone must not be treated as proof that ADS-B.lol possesses no historical data**; ADS-B.lol maintains bulk global daily tarball archives on cloud storage.
3. **HTTP Error / Route Not Implemented — ADSB.fi**
   - *Endpoint Tested:* `api/v2/history/lat/33.4115/lon/36.5156/dist/81/date/2024-01-01`.
   - *Response:* `HTTP 400 Bad Request`.
   - *Audit Finding:* HTTP 400 indicates the server rejected the route/parameters. It does not prove the absence of historical telemetry in other formats or systems.
4. **Live-Only Access — Airplanes.live**
   - *Endpoint Tested:* `api/v2/point/33.4115/36.5156/81`.
   - *Response:* `HTTP 200 OK`.
   - *Audit Finding:* Provider documentation supports live streaming point queries only. No historical API endpoints are exposed.
5. **Paid Access — Commercial Providers (FlightAware, Flightradar24, Cirium)**
   - *Audit Finding:* Commercial services hold historical tracking data, but require paid commercial subscriptions and API keys. Not investigated per safety rules.
6. **Not Investigated — Global Research Archives (Zenodo Bulk Dumps)**
   - *Audit Finding:* Multi-terabyte global dumps exist on academic repositories (e.g. Zenodo OpenSky community), but were not downloaded or filtered for DAM due to compute and storage boundaries.

- Detailed register: `reports/v2_17_1_adsb_claim_audit.csv`.

---

## 4. Audit Item 3: Terrain and Receiver Blindspot Claim Evaluation

### 4.1 Evidentiary Review
In V2.17 documentation, the following statement appeared:
> *"Damascus Low-Altitude ADS-B Blindspot: Lack of local crowdsourced receiver stations in Damascus terminal airspace (receivers in Lebanon/Jordan cannot observe aircraft on the surface or below 4,000 ft AMSL at OSDI due to the Anti-Lebanon Mountain range)."*

### 4.2 Audit Finding and Correction
- **Evidence Gap:** The repository contains no direct RF propagation study, line-of-sight topographical Fresnel-zone analysis, feeder station coordinates, or empirical receiver site surveys.
- **Action Taken:**
  1. The statement has been **completely removed as a factual conclusion**.
  2. The concept is preserved strictly as an **unverified hypothesis**:
     > *"Hypothesis (Unverified): Topographical terrain to the west of Damascus (Anti-Lebanon range) could theoretically impede VHF Line-of-Sight signals from receivers stationed in neighboring jurisdictions to low-altitude traffic at OSDI (elevation 2,020 ft). However, because no direct RF propagation analysis or feeder site audit has been performed, this remains an unverified hypothesis."*
  3. **Strict Causality Rule:** The absence of nearby aircraft observations in a single live test snapshot must **NOT** be attributed to terrain causality; it may reflect traffic absence, receiver offline status, or filtering policies.

---

## 5. Audit Item 4: ADS-B Observation Classification & Revalidation

### 5.1 Revalidation of All 16 Staged Observations
All 16 observations staged in `data/staging/v2_17_adsb/v2_17_adsb_staging.db` were re-audited across seven mandatory dimensions:

| Check Item | Audit Finding | Compliance Status |
|---|---|---|
| **Raw Payload Hashes** | SHA-256 hashes (`8d3db2...` for lol, `6bb9c9...` for fi) match raw source files exactly | **PASSED** |
| **Provider Attribution** | 9 records from ADS-B.lol, 7 records from ADSB.fi | **PASSED** |
| **Observation Timestamps** | Valid ISO 8601 UTC timestamps with timezone indicators | **PASSED** |
| **Aircraft Identifiers** | All 16 records have valid 6-character hexadecimal ICAO24 addresses | **PASSED** |
| **Distance to OSDI** | Distances range from 96.24 km to 141.95 km (0 fixes within 95 km) | **PASSED** |
| **Altitude Distribution** | 15 fixes between FL224 and FL410; 1 fix at 10,175 ft climbing in Lebanese FIR | **PASSED** |
| **Movement Promotion** | **0 DAM movements; 0 confirmed physical movements** | **PASSED** |

### 5.2 Classification Breakdown
- **Overflight Observations (15 records):** High-altitude transcontinental flights traversing regional airspace at cruise levels (FL224 to FL410; e.g. `GFA004` at FL390, `UAE7V` at FL400, `UAE7TR` at FL360, `AIC151` at FL400).
- **Regional Observations (1 record):** Operations in Lebanese airspace / Beirut OLBA terminal area (`MEA428` at 10,175 ft climbing at 2,688 fpm at 136.9 km NW of Damascus).
- **Airport Surface Observations:** **0**
- **Approach Candidates:** **0**
- **Departure Candidates:** **0**
- **Confirmed Physical Movements Promoted:** **0 (Zero)**

Every observation remains strictly excluded from Damascus airport movement metrics.

---

## 6. Audit Item 5: Test and Integrity Verification

### 6.1 Cryptographic Database & Snapshot Invariant
All protected databases and source snapshot files match their baseline hashes:

| Database / File | Verified Hash | Status |
|---|---|---|
| `data/damascus_airport.db` | `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b` | **PRISTINE (Unchanged)** |
| `data/archived_fids_staging.db` | `a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4` | **PRISTINE (Unchanged)** |
| `data/archived_fids_analytics.db` | `e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe` | **PRISTINE (Unchanged)** |
| `data/archived_fids_history_staging.db` | `39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f` | **PRISTINE (Unchanged)** |
| `wayback_damairport_fids_20260709234230.raw` | `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf` | **PRISTINE (Unchanged)** |
| `wayback_damairport_fids_20260709234230.json` | `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491` | **PRISTINE (Unchanged)** |

### 6.2 Test Suite Execution
- V2.17-Specific Tests: 20 passed, 0 failed.
- Full Repository Regression Suite: **350 passed, 0 failed in 20.91s**.
- Audit verification artifact: `reports/v2_17_1_integrity_verification.json`.

---

## 7. Final Audit Decision

### **Decision: ACCEPTED WITH LIMITATIONS**

### Rationale and Limitations Stated:
1. **No Historical Coverage Expansion:** No new historical FIDS records or historical ADS-B flight observations were retrieved in V2.17 or V2.17.1. The verified historical scheduled baseline remains strictly **1,982 records across 67 dates** (`2026-07-05` to `2026-09-09`).
2. **Access Barriers Identified:**
   - Internet Archive Wayback Machine replay returned HTTP 429 rate limits for discovered parameterized captures; acquisition was halted without circumvention.
   - OpenSky Network historical queries require registered research credentials (HTTP 403), prohibited under user safety rules.
   - Community feeds (ADS-B.lol, ADSB.fi) do not expose verified per-point historical query APIs via tested unauthenticated endpoints.
3. **Observation Boundaries:** All 16 captured live ADS-B observations are high-altitude overflights or regional Lebanese traffic; zero observations represent Damascus airport movements, and zero were promoted to physical movements.
4. **Immutability Maintained:** Zero mutations were applied to production or baseline staging datasets.
