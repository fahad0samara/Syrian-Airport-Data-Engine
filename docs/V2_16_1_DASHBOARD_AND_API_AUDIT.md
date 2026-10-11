# V2.16.1 — Dashboard and API Reconciliation Audit
## Metrics Verification, Endpoint Audit & Frontend Presentation Integrity

**Syrian Airport Data Engine — Version 2.16.1**  
**Audit Date:** 2026-10-11  
**User Interface Audited:** `static/index.html`  
**API Module Audited:** `src/archived_fids_history_api.py`

---

## 1. Executive Summary

This audit validates that all metrics, indicators, and tables exposed via the REST API and the frontend dashboard accurately mirror the empirical underlying data in `data/archived_fids_history_staging.db` and `data/archived_fids_staging.db`.

Key findings:
- All stat cards report exact counts: **5 Discovered, 1 Retrieved, 1 Validated, 1 Comparison-Ready**.
- A prominent rate-limit alert banner communicates that 4 captures are pending acquisition due to HTTP 429.
- Monthly scheduled flight arithmetic reconciles perfectly: **July (956) + August (886) + September (140) = 1,982 records**.
- Cross-snapshot comparison endpoint accurately reports `no_additional_snapshot_available_for_comparison` rather than empty error states or synthetic data.

---

## 2. API Endpoint Reconciliation

The historical archive API endpoints were audited against their database query results:

### 2.1. `/api/historical-archive/captures`
- **Output Metrics:**
  - `total_discovered`: `5`
  - `acquisition_status_summary`:
    - `already_acquired`: `1`
    - `rate_limited_429`: `4`
  - `rate_limited_429_count`: `4`
- **Verification:** Matches the 5 rows in `archived_snapshot_registry` exactly.

### 2.2. `/api/historical-archive/snapshots`
- **Output Metrics:**
  - `total_snapshots`: `1`
  - `validated_snapshots`: `1`
  - Record payload contains:
    - `snapshot_id`: `snap_wayback_20260709234230`
    - `comparison_eligibility`: `full_snapshot_comparison`
    - `comparison_scope`: `all_movements`
    - `total_records`: `1982`
- **Verification:** Reconciles 1:1 with validated staging database.

### 2.3. `/api/historical-archive/coverage`
- **Output Metrics:**
  - `coverage_status`: `baseline_only`
  - `unique_dates_covered`: `67`
  - `date_range`: `2026-07-05` to `2026-09-09`
  - `monthly_breakdown`:
    - `2026-07`: `956` records
    - `2026-08`: `886` records
    - `2026-09`: `140` records
  - `total_archived_records`: `1982`
- **Verification:** Sum: $956 + 886 + 140 = 1982$. Arithmetic is complete and mathematically exact.

### 2.4. `/api/historical-archive/comparisons`
- **Output Metrics:**
  - `status`: `no_additional_snapshot_available_for_comparison`
  - `total_comparisons`: `0`
  - `comparisons`: `[]`
- **Verification:** With only 1 snapshot present, no comparative pairs exist. Correctly prevents synthetic comparison rows.

---

## 3. Frontend Dashboard Presentation Audit (`static/index.html`)

The frontend user interface was audited to confirm alignment with API responses:

### 3.1. Primary KPI Header Cards
1. **Wayback Captures Discovered:** Displays `5` with subtitle `1 retrieved · 4 rate-limited (HTTP 429)`.
2. **Archived Records:** Displays `1,982` with subtitle `July 9, 2026 verified snapshot`.
3. **Calendar Coverage:** Displays `67 Days` with subtitle `2026-07-05 to 2026-09-09`.
4. **Comparison Pairs:** Displays `0` with subtitle `Requires $\ge 2$ validated snapshots`.

### 3.2. Rate Limit Notification Banner
A yellow warning callout is dynamically rendered when unacquired captures exist:
> **Wayback Machine Acquisition Notice:** 4 discovered captures are currently pending retrieval due to Archive.org HTTP 429 rate limiting. The dashboard displays metrics exclusively from the 1 cryptographically verified snapshot (`20260709234230`).

### 3.3. Table Header Semantics
- Table headers for comparison diffing display **"Displayed Airline / Brand"** and **"Displayed Airline Changed"**, avoiding confusion with operating carriers.

---

## 4. Monthly Scheduled Service Arithmetic Reconciliation

Audited directly against [`reports/v2_16_1_coverage_reconciliation.csv`](../reports/v2_16_1_coverage_reconciliation.csv):

| Month | Calendar Dates | Arrivals | Departures | Total Records | Daily Avg |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **July 2026** | 2026-07-05 to 2026-07-31 (27 days) | 480 | 476 | **956** | 35.41 |
| **August 2026** | 2026-08-01 to 2026-08-31 (31 days) | 443 | 443 | **886** | 28.58 |
| **September 2026** | 2026-09-01 to 2026-09-09 (9 days) | 70 | 70 | **140** | 15.56 |
| **Total Baseline** | **67 days** | **993** | **989** | **1,982** | **29.58** |

---

## 5. Audit Conclusion

The API and dashboard layers faithfully communicate the exact verified state of the historical archive. Rate limits are transparently displayed, coverage numbers reconcile exactly, and comparisons accurately report the single-snapshot baseline state.
