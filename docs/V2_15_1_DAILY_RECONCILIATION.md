# Syrian Airport Data Engine — Version 2.15.1
# Daily Coverage Reconciliation & Temporal Audit Report

## 1. Executive Summary & Purpose

This audit report delivers an independent, empirical reconciliation of the daily flight coverage across the 67 consecutive calendar days captured in the archived Damascus International Airport (DAM / OSDI) Flight Information Display System (FIDS) snapshot (`2026-07-05` through `2026-09-09`).

A critical objective of this audit is investigating and resolving the apparent discrepancy between the prose claim in V2.14 documentation (`docs/V2_14_FINAL_DECISION.md`, line 47: *"Every single day has between 24 and 36 scheduled movements"*) and the actual metrics implemented in the V2.15 analytics layer (minimum daily count = 2, maximum daily count = 69, average = 29.58).

Direct querying of the staging database (`data/archived_fids_staging.db`) in strictly read-only mode confirms that the raw data and normalized staging records have **always** contained exactly 1,982 records with a minimum daily volume of 2 and a maximum of 69. The V2.14 prose statement was a narrative drafting oversight that observed only the mid-period steady-state operations and failed to account for the opening 5-day schedule surge and the 4-day tail off.

---

## 2. Cryptographic Integrity & Source Provenance

All calculations are derived from the immutable, bit-verified sources:
- **Raw JSON Snapshot**: `data/raw/snapshots/wayback_damairport_fids_20260709234230.json`  
  SHA-256: `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491`
- **Staging Database**: `data/archived_fids_staging.db`  
  SHA-256: `a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4`
- **Production Database**: `data/damascus_airport.db`  
  SHA-256: `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b` (Untouched; 1,830 verified movement events).

---

## 3. Root Cause Investigation of the V2.14 Narrative Discrepancy

### 3.1 The Contradictory Claim
In `docs/V2_14_FINAL_DECISION.md`, Section 4, line 47, the narrative text stated:
> *"Every single day has between 24 and 36 scheduled movements, with balanced arrivals and departures (typically 12 to 18 of each per day)."*

### 3.2 Empirical Audit Findings
Querying `archived_fids_raw_records` and `archived_fids_normalized` reveals the true distribution:
1. **July 5–9, 2026 (Opening Surge)**:
   - July 5: 64 flights (33 arrivals, 31 departures)
   - July 6: 69 flights (35 arrivals, 34 departures) — **Peak Day**
   - July 7: 60 flights (30 arrivals, 30 departures)
   - July 8: 63 flights (32 arrivals, 31 departures)
   - July 9: 68 flights (34 arrivals, 34 departures)
2. **July 10 – August 31, 2026 (Steady-State Mid-Period)**:
   - Daily flights fluctuate between 26 and 32 flights/day.
   - Example: July 10 (32), July 11 (26), July 12 (32), July 13 (28), July 14 (28).
   - Arrival/departure counts per day in this period are exactly 13–16 of each.
3. **September 1–5, 2026 (Late Period Moderation)**:
   - Sept 1: 28 flights; Sept 2: 26 flights; Sept 3: 26 flights; Sept 4: 28 flights; Sept 5: 24 flights.
4. **September 6–9, 2026 (Tail Off)**:
   - Sept 6: 2 flights (1 arrival, 1 departure)
   - Sept 7: 2 flights (1 arrival, 1 departure)
   - Sept 8: 2 flights (1 arrival, 1 departure)
   - Sept 9: 2 flights (1 arrival, 1 departure)

### 3.3 Root Cause Assessment
The author of `docs/V2_14_FINAL_DECISION.md` inspected records from the mid-period (e.g., July 10 through August 31) where daily counts indeed strictly lie between 24 and 32 movements, and drafted the sentence without checking the boundary extremes of the dataset.

No data was altered, added, or synthesized during V2.14 or V2.15. The underlying table in `data/archived_fids_staging.db` has always had exactly 1,982 records. The V2.15 analytics layer implemented the mathematically accurate reality, which this V2.15.1 audit formalizes.

---

## 4. Complete 67-Day Daily Schedule Census

The table below documents the full temporal census from `reports/v2_15_1_daily_reconciliation.csv`:

| Date | Total Records | Arrivals | Departures | Scheduled | Arrived | Unique UUIDs | Unique Raw Flt | Unique Norm Flt | Duplicate Candidates |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 2026-07-05 | 64 | 33 | 31 | 64 | 0 | 64 | 63 | 63 | 0 |
| 2026-07-06 | 69 | 35 | 34 | 68 | 1 | 69 | 68 | 67 | 0 |
| 2026-07-07 | 60 | 30 | 30 | 60 | 0 | 60 | 60 | 59 | 0 |
| 2026-07-08 | 63 | 32 | 31 | 63 | 0 | 63 | 62 | 62 | 2 |
| 2026-07-09 | 68 | 34 | 34 | 68 | 0 | 68 | 67 | 67 | 0 |
| 2026-07-10 | 32 | 16 | 16 | 32 | 0 | 32 | 32 | 32 | 0 |
| 2026-07-11 | 26 | 13 | 13 | 26 | 0 | 26 | 26 | 26 | 0 |
| 2026-07-12 | 32 | 16 | 16 | 32 | 0 | 32 | 32 | 32 | 0 |
| 2026-07-13 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-07-14 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-07-15 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-07-16 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-07-17 | 30 | 15 | 15 | 30 | 0 | 30 | 30 | 30 | 0 |
| 2026-07-18 | 26 | 13 | 13 | 26 | 0 | 26 | 26 | 26 | 0 |
| 2026-07-19 | 32 | 16 | 16 | 32 | 0 | 32 | 32 | 32 | 0 |
| 2026-07-20 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-07-21 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-07-22 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-07-23 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-07-24 | 30 | 15 | 15 | 30 | 0 | 30 | 30 | 30 | 0 |
| 2026-07-25 | 26 | 13 | 13 | 26 | 0 | 26 | 26 | 26 | 0 |
| 2026-07-26 | 32 | 16 | 16 | 32 | 0 | 32 | 32 | 32 | 0 |
| 2026-07-27 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-07-28 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-07-29 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-07-30 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-07-31 | 30 | 15 | 15 | 30 | 0 | 30 | 30 | 30 | 0 |
| 2026-08-01 | 26 | 13 | 13 | 26 | 0 | 26 | 26 | 26 | 0 |
| 2026-08-02 | 32 | 16 | 16 | 32 | 0 | 32 | 32 | 32 | 0 |
| 2026-08-03 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-08-04 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-08-05 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-08-06 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-08-07 | 30 | 15 | 15 | 30 | 0 | 30 | 30 | 30 | 0 |
| 2026-08-08 | 26 | 13 | 13 | 26 | 0 | 26 | 26 | 26 | 0 |
| 2026-08-09 | 32 | 16 | 16 | 32 | 0 | 32 | 32 | 32 | 0 |
| 2026-08-10 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-08-11 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-08-12 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-08-13 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-08-14 | 30 | 15 | 15 | 30 | 0 | 30 | 30 | 30 | 0 |
| 2026-08-15 | 26 | 13 | 13 | 26 | 0 | 26 | 26 | 26 | 0 |
| 2026-08-16 | 32 | 16 | 16 | 32 | 0 | 32 | 32 | 32 | 0 |
| 2026-08-17 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-08-18 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-08-19 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-08-20 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-08-21 | 30 | 15 | 15 | 30 | 0 | 30 | 30 | 30 | 0 |
| 2026-08-22 | 26 | 13 | 13 | 26 | 0 | 26 | 26 | 26 | 0 |
| 2026-08-23 | 32 | 16 | 16 | 32 | 0 | 32 | 32 | 32 | 0 |
| 2026-08-24 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-08-25 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-08-26 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-08-27 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-08-28 | 30 | 15 | 15 | 30 | 0 | 30 | 30 | 30 | 0 |
| 2026-08-29 | 26 | 13 | 13 | 26 | 0 | 26 | 26 | 26 | 0 |
| 2026-08-30 | 32 | 16 | 16 | 32 | 0 | 32 | 32 | 32 | 0 |
| 2026-08-31 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-09-01 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-09-02 | 26 | 13 | 13 | 26 | 0 | 26 | 26 | 26 | 0 |
| 2026-09-03 | 26 | 13 | 13 | 26 | 0 | 26 | 26 | 26 | 0 |
| 2026-09-04 | 28 | 14 | 14 | 28 | 0 | 28 | 28 | 28 | 0 |
| 2026-09-05 | 24 | 12 | 12 | 24 | 0 | 24 | 24 | 24 | 0 |
| 2026-09-06 | 2 | 1 | 1 | 2 | 0 | 2 | 2 | 2 | 0 |
| 2026-09-07 | 2 | 1 | 1 | 2 | 0 | 2 | 2 | 2 | 0 |
| 2026-09-08 | 2 | 1 | 1 | 2 | 0 | 2 | 2 | 2 | 0 |
| 2026-09-09 | 2 | 1 | 1 | 2 | 0 | 2 | 2 | 2 | 0 |
| **TOTAL** | **1,982** | **993** | **989** | **1,981** | **1** | **1,982** | — | — | **2** |

---

## 5. Statistical Summary & Key Metrics

1. **Total Consecutive Calendar Days**: 67 days (Zero missing dates from `2026-07-05` to `2026-09-09`).
2. **Total Scheduled Records**: 1,982 records.
3. **Daily Minimum**: 2 flights/day (occurring on September 6, 7, 8, 9).
4. **Daily Maximum**: 69 flights/day (occurring on July 6).
5. **Arithmetic Mean**:
   $$\text{Daily Average} = \frac{1,982}{67} = 29.5821 \text{ records/day}$$
6. **Arrivals Total**: 993 records (50.10%).
7. **Departures Total**: 989 records (49.90%).
8. **Status Distribution**: 1,981 `scheduled` (99.95%) and 1 `arrived` (0.05% on 2026-07-06).
9. **Duplicate Candidates**: Exactly 1 pair (2 records) on 2026-07-08 (G9 376 / 376).
