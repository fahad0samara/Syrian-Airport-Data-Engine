# V2.16.2 — Scheduled Date and Time Semantics
## Timestamp Dimensions, Timezone Grounding & Aggregation Field Specifications

**Syrian Airport Data Engine — Version 2.16.2**  
**Audit Date:** 2026-10-11  
**Target Resource:** Damascus International Airport (DAM / OSDI) FIDS API Snapshot  
**Local Timezone:** `Asia/Damascus` (UTC+3)

---

## 1. Executive Summary

This document establishes the precise field semantics and temporal boundaries governing the Damascus Airport Flight Information Display System (FIDS) historical archive. 

A critical finding of Version 2.16.2 is that timestamp confusion has been a recurring vulnerability in aviation data pipelines: conflating crawler crawl timestamps, server database row creation timestamps (`createdAt`), or derived UTC conversions with the passenger-facing scheduled flight date (`date`) causes catastrophic distortions in monthly flight distributions.

This standard establishes that **`scheduled_service_date_local` (`date`) is the sole authoritative field for monthly and daily historical flight grouping**.

---

## 2. Field Definitions & Temporal Dimensions

Every historical record contains multiple temporal coordinates. In Version 2.16.2, these dimensions are strictly segregated:

| Field Name | Source / Derived | Format | Example | Semantic Role |
| :--- | :--- | :--- | :--- | :--- |
| **`scheduled_service_date_local`** | Source (`date`) | `YYYY-MM-DD` | `2026-07-05` | **Primary grouping dimension.** The local calendar date of scheduled operation. |
| **`scheduled_service_time_local`** | Source (`time`) | `HH:MM` | `13:55` | The scheduled departure/arrival slot in local airport wall-clock time. |
| **`source_created_at`** | Source (`createdAt`) | ISO 8601 UTC | `2026-07-04T16:34:12Z` | Upstream CMS/database row creation timestamp. |
| **`snapshot_capture_datetime_utc`** | Wayback Crawl | ISO 8601 UTC | `2026-07-09T23:42:30Z` | Timestamp when the Internet Archive crawler saved the HTTP response. |
| **`retrieval_datetime_utc`** | Engine Ingestion | ISO 8601 UTC | `2026-10-11T12:00:00Z` | Timestamp when our local pipeline verified and ingested the raw file. |

---

## 3. Disallowed Date Fields for Monthly Aggregation

The engine strictly prohibits the use of the following fields for monthly, daily, or seasonal flight grouping:

1. **`source_created_at` (`createdAt`):**
   - In the July 9 snapshot, all 1,982 records have `createdAt` timestamps occurring between `2026-07-04` and `2026-07-09`.
   - **Failure Mode:** If `createdAt` were used to aggregate monthly volume, **100% of the 1,982 records would be assigned to July 2026**, resulting in July = 1,982, August = 0, September = 0.
2. **`snapshot_capture_datetime_utc`:**
   - Represents the instant the web archive crawler saved the payload (`2026-07-09T23:42:30Z`).
   - Conflating crawl dates with flight dates would collapse 67 days of future timetable schedules into a single day.
3. **Derived UTC Date Shifting:**
   - Damascus operates on `Asia/Damascus` (UTC+3 year-round, Syrian Standard Time).
   - In commercial aviation timetable displays, flight dates are scheduled according to local airport wall-clock time. Converting a 01:00 departure on August 1 to 22:00 UTC on July 31 and re-grouping by the UTC date shifts flights across calendar month boundaries artificially.
   - **Enforced Rule:** Monthly and daily grouping relies exclusively on the unaltered source string `date` (`YYYY-MM-DD`).

---

## 4. Empirical Date Verification in July 9 Baseline

An audit of all 1,982 objects in `data/raw/snapshots/wayback_damairport_fids_20260709234230.json` confirms:

- **Missing `date` fields:** 0
- **Invalid `date` regex formats (`^\d{4}-\d{2}-\d{2}$`):** 0
- **Missing `time` fields:** 0
- **Invalid `time` regex formats (`^\d{2}:\d{2}$`):** 0
- **Earliest scheduled date:** `2026-07-05`
- **Latest scheduled date:** `2026-09-09`
- **Distinct scheduled dates:** Exactly **67 consecutive calendar days** without a single calendar gap.

---

## 5. Audit Conclusion

The scheduled service date (`date`) is mathematically and semantically verified as the sole source of truth for monthly coverage. All downstream aggregation engines and regression tests strictly reference this field, guaranteeing absolute stability across analytical reports.
