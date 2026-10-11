# Syrian Airport Data Engine — Version 2.15.1
# API Endpoints & Export Data Reconciliation Audit

## 1. Executive Summary

This document audits the 10 HTTP endpoints and data export pipelines provided by the Version 2.15 Archived FIDS Analytics Layer (`/api/archived-fids/*`).

Each endpoint's output has been independently cross-validated against direct SQL calculations on `data/archived_fids_staging.db` in strictly read-only mode.

The audit confirms:
- **100% Data Concordance**: Every endpoint, CSV export, and JSON payload returns figures that reconcile exactly with the 1,982 staged records.
- **Strict Production Isolation**: Zero queries access `data/damascus_airport.db` (production movements remain at 1,830 verified events).
- **Zero Physical Movement Promotion**: All endpoints return `physical_movement_evidence_count = 0` and include explicit semantic warnings.

---

## 2. API Endpoint Audit Matrix

| Endpoint | Method | Key Metrics Returned | Staging DB SQL Reconciled | HTTP Status | Production DB Access |
| :--- | :---: | :--- | :---: | :---: | :---: |
| `/api/archived-fids/summary` | `GET` | Total: 1,982; Arr: 993; Dep: 989; Days: 67; Brands: 14 | **Exact Match** | 200 OK | **None** |
| `/api/archived-fids/coverage` | `GET` | Range: 2026-07-05 to 2026-09-09; Days: 67; Total: 1,982 | **Exact Match** | 200 OK | **None** |
| `/api/archived-fids/daily` | `GET` | 67 daily objects; Min: 2; Max: 69; Sum: 1,982 | **Exact Match** | 200 OK | **None** |
| `/api/archived-fids/airlines` | `GET` | 14 entities; Top: G9 (509); UN (4); Sum: 1,982 | **Exact Match** | 200 OK | **None** |
| `/api/archived-fids/routes` | `GET` | Top origins/destinations; Arr: DAM; Dep: DAM | **Exact Match** | 200 OK | **None** |
| `/api/archived-fids/hourly` | `GET` | 24 buckets (00–23); Local time UTC+3; Sum: 1,982 | **Exact Match** | 200 OK | **None** |
| `/api/archived-fids/weekly` | `GET` | 7 weekday objects; Sun–Wed (10 occ), Thu–Sat (9 occ) | **Exact Match** | 200 OK | **None** |
| `/api/archived-fids/duplicate-candidates` | `GET` | 1 pair (G9 376 / 376 on 2026-07-08 13:55) | **Exact Match** | 200 OK | **None** |
| `/api/archived-fids/export/csv` | `GET` | CSV download for daily, airlines, routes, hourly, etc. | **Exact Match** | 200 OK | **None** |
| `/api/archived-fids/export/json` | `GET` | Full JSON export of analytics summary & datasets | **Exact Match** | 200 OK | **None** |

---

## 3. Directional & Route Parameter Reconciliation

### 3.1 Arrival & Departure Isolation
- **Total Scheduled Records**: 1,982
- **Scheduled Arrivals**: 993 (50.10%)
- **Scheduled Departures**: 989 (49.90%)
- **Net Balance**: $+4$ arrivals over 67 days.

### 3.2 Directional Invariance Checks
1. For all 993 arrival records, `destination_iata` is strictly `DAM`.
2. For all 989 departure records, `origin_iata` is strictly `DAM`.
3. Filter query parameter tests (`?direction=arrival`, `?direction=departure`) return exact subsets:
   - Calling `/api/archived-fids/summary?direction=arrival` returns exactly 993 records.
   - Calling `/api/archived-fids/summary?direction=departure` returns exactly 989 records.
   - Sum of filtered queries ($993 + 989 = 1,982$) matches unfiltered query with zero discrepancy.

---

## 4. Hourly Distribution Reconciliation (Local Wall-Clock Time)

A potential risk in historical timetable analysis is inadvertent conversion of local scheduled times to UTC before aggregation, causing a 3-hour shift.

The audit verified:
1. Hourly aggregation is performed directly on the first two characters of `scheduled_time` (`SUBSTR(scheduled_time, 1, 2)`).
2. The snapshot's native timestamps reflect Damascus local time (`Asia/Damascus`, `UTC+3`).
3. Total flights across the 24 hourly buckets sum to **1,982** (993 arrivals and 989 departures).
4. No automated UTC shift occurs during API serialization.

---

## 5. Candidate Duplicate Pair Audit

The staging and analytics layers contain 1 candidate duplicate flight pair:
- **Pair Identification**: `DUP_CANDIDATE_001`
- **Record 1**: UUID `e5ada70d-5245-46d4-b043-bf469c1d104f`, flight `G9 376`, Air Arabia, 2026-07-08 13:55, DAM $\rightarrow$ SHJ.
- **Record 2**: UUID `2d2a0935-da5e-42c4-ad15-e10b4e2291ee`, flight `376`, Air Arabia, 2026-07-08 13:55, DAM $\rightarrow$ SHJ.
- **Audit Rule Verification**:
  - The API does **not** delete, merge, or suppress either record.
  - Both records are served in `/daily`, `/airlines`, `/routes`, and `/export/*`.
  - The pair is transparently flagged under `is_duplicate_candidate = 1` and detailed via `/api/archived-fids/duplicate-candidates` with `review_status = "requires_manual_review"`.

---

## 6. Export Artifacts Integrity

The automated reports generated in `reports/`:
- `v2_15_1_daily_reconciliation.csv`: 68 lines (1 header + 67 daily rows).
- `v2_15_1_weekday_reconciliation.csv`: 8 lines (1 header + 7 weekday rows).
- `v2_15_1_entity_reconciliation.csv`: 15 lines (1 header + 14 entity rows).
- `v2_15_1_metric_reconciliation.json`: Comprehensive 17 KB audit payload.

Every numeric figure across these four files reconciles with zero discrepancy to the underlying database and API responses.
