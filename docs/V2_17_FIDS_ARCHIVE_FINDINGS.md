# V2.17 — Track A: Historical FIDS Archive Discovery & Validation

## 1. Executive Summary

Track A of Version 2.17 investigated the historical availability of official Flight Information Display System (FIDS) API captures for Damascus International Airport (**DAM** / **OSDI**) and regional Syrian airports (**ALP**, **KAC**, **DEZ**).

The investigation utilized the Internet Archive Wayback Machine CDX API, examined known URL variants, performed replay accessibility checks within strict non-circumvention safety boundaries, and established an isolated staging database and audit reports.

---

## 2. Endpoint Discovery & Inventory

### 2.1 Damascus International Airport (DAM / OSDI)
The official FIDS API endpoint is:
`https://damairport.gov.sy/api/flights.php`

A forensic analysis of the Internet Archive CDX index and historical query patterns identified five (5) distinct capture events for Damascus airport endpoint variants:

| Capture ID | Timestamp | Original URL / Variant | Classification | HTTP Status | Archive Digest | Local Status |
|---|---|---|---|---|---|---|
| `snap_wayback_20260709234230` | 2026-07-09T23:42:30Z | `https://damairport.gov.sy/api/flights.php` | Complete Unfiltered | 200 OK | `LWGQOMIVR7BG55CKGT4LXDRNUVKDA36L` | **Retrieved & Validated (1,982 records)** |
| `snap_wayback_20260720034051` | 2026-07-20T03:40:51Z | `?paged=1&page=1&dir=all&wfloor=2026-07-17&dexact=2026-07-20` | Filtered (Date & Pagination) | 200 OK | `5XPJUI5F52UOB5LJFQS6V2H7QK53WMZV` | Halted (Replay HTTP 429) |
| `snap_wayback_20260802011114` | 2026-08-02T01:11:14Z | `?paged=1&page=auto&dir=arrival&wfloor=2026-07-30&dexact=2026-08-02` | Filtered (Arrivals & Date) | 200 OK | `5UXRH7MNTOJW3WZ4KTMODHCZASJTC45Y` | Halted (Replay HTTP 429) |
| `snap_wayback_20260901001238` | 2026-09-01T00:12:38Z | `?paged=1&page=auto&dir=arrival&wfloor=2026-08-29&dexact=2026-09-01` | Filtered (Arrivals & Date) | 200 OK | `MZOHYTG7ISAYZ24ZNYW5EO27E4CEGI4W` | Halted (Replay HTTP 429) |
| `snap_wayback_20260909200343` | 2026-09-09T20:0343Z | `?paged=1&page=auto&dir=arrival&wfloor=2026-09-06&dexact=2026-09-09` | Filtered (Arrivals & Date) | 200 OK | `25PYEJCFKSNC5ZSM2MMZFOFEQRNIAFSJ` | Halted (Replay HTTP 429) |

### 2.2 Regional Syrian Airport Endpoints
The following regional civil aviation endpoints were evaluated:
- Aleppo International Airport: `https://alpairport.gov.sy/api/flights.php`
- Qamishli Airport: `https://qamishliairport.gov.sy/api/flights.php`
- Deir ez-Zor Airport: `https://deirezzorairport.gov.sy/api/flights.php`

**Finding:** Live CDX indexing queries returned `HTTP 503: Service Unavailable` and network timeouts. No archived historical FIDS API snapshots were retrievable for regional Syrian airport endpoints during this session.

---

## 3. Retrieval Policy & Rate-Limit Enforcement

Under Section 2 of the V2.17 specifications:
> *"If a source returns 403, 429, authentication requirements, or access restrictions, record the result and stop that acquisition attempt. Do not attempt circumvention."*

During live replay retrieval requests against `https://web.archive.org/web/{timestamp}id_/{original_url}`, the Wayback Machine returned `HTTP 429: Too Many Requests` across all four (4) parameterized capture attempts.

In strict adherence to the project rules:
1. Replay requests were immediately terminated without retries or proxy rotation.
2. The HTTP 429 status was logged in `reports/v2_17_fids_capture_inventory.csv` and `reports/v2_17_fids_capture_validation.csv`.
3. No corrupted or incomplete mock responses were generated.
4. The verified baseline snapshot (`20260709234230`) remains the sole validated source of truth.

---

## 4. Complete vs. Filtered Snapshot Classification

A primary data-integrity principle established in V2.16 and maintained in V2.17 is the strict differentiation between **Complete** and **Filtered** snapshots:

1. **Complete Snapshot (`snap_wayback_20260709234230`)**:
   - URL contains zero query parameters (`https://damairport.gov.sy/api/flights.php`).
   - Represents the complete server timetable snapshot across all airlines and directions.
   - Contains 1,982 records (993 arrivals, 989 departures) covering 67 consecutive calendar dates (2026-07-05 to 2026-09-09).
2. **Filtered Snapshots (`20260720`, `20260802`, `20260901`, `20260909`)**:
   - URL contains explicit filter parameters:
     * `dir=arrival` (restricts results to inbound flights only).
     * `wfloor=...&dexact=...` (restricts results to a narrow 3-day scheduling window).
     * `paged=1&page=...` (paginated display slice).
   - In accordance with V2.17 rules, any record absent from a filtered snapshot MUST NOT be interpreted as a deleted flight or cancellation.

---

## 5. Verified Historical Scheduled Coverage

The confirmed historical scheduled coverage for Damascus International Airport is summarized below:

| Month | Total Scheduled Records | Arrivals | Departures | Distinct Scheduled Dates | Earliest Date | Latest Date |
|---|---:|---:|---:|---:|---|---|
| **July 2026** | 956 | 480 | 476 | 27 | 2026-07-05 | 2026-07-31 |
| **August 2026** | 886 | 443 | 443 | 31 | 2026-08-01 | 2026-08-31 |
| **September 2026** | 140 | 70 | 70 | 9 | 2026-09-01 | 2026-09-09 |
| **Total Baseline** | **1,982** | **993** | **989** | **67** | **2026-07-05** | **2026-09-09** |

*Crucial Aviation Semantic Distinction:* All 1,982 records represent scheduled and displayed timetable entries on the airport FIDS API. They do NOT represent physical aircraft radar movements, transponder state vectors, or confirmed runway touchdowns.

---

## 6. Staging & Hash Verification

All Track A data structures are staged in isolated storage:
- Database: `data/staging/v2_17_fids/v2_17_fids_staging.db`
- Baseline Raw Hash: `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf`
- Baseline JSON Hash: `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491`
- Production Database Modification: **NONE (Verified unchanged)**.
