# Syrian Airport Data Engine — Version 2.14
# Final Decision & Snapshot Extraction Sign-Off

**Document Identifier**: `docs/V2_14_FINAL_DECISION.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Staging Database**: `data/archived_fids_staging.db`  
**Scope**: Definitive Technical Determination and Mandatory Answers to the Nine Decision Questions  
**Status**: APPROVED FINAL DETERMINATION  
**Production Integrity Invariant**: `data/damascus_airport.db` SHA-256 verified identical (`c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`).

---

## 1. Executive Summary & Extraction Sign-Off

Version 2.14 successfully extracts, cryptographically verifies, normalizes, and stages the single verified historical FIDS snapshot of Damascus International Airport from the Internet Archive (`2026-07-09T23:42:30Z`).

The extraction generated a fully reproducible, clean staging dataset comprising **1,982 unique scheduled flight records** spanning **67 consecutive calendar days** (`2026-07-05` through `2026-09-09`).

All processing was isolated in `data/archived_fids_staging.db`. **The production database `data/damascus_airport.db` remained strictly untouched.**

---

## 2. Definitive Answers to the Nine Mandatory Decision Questions

### Question 1: Is the snapshot genuinely parseable and reproducible?
**Answer**: **Yes, 100% parseable and bit-for-bit reproducible.**
* The raw response was downloaded via `curl` from `https://web.archive.org/web/20260709234230id_/https://damairport.gov.sy/api/flights.php`.
* It is permanently preserved at `data/raw/snapshots/wayback_damairport_fids_20260709234230.raw` with cryptographic SHA-256:
  `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf`.
* Decompression via `gzip` yields 644,922 bytes with SHA-256:
  `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491`.
* Standard Python `json.loads()` parses the entire payload without errors.

---

### Question 2: How many unique scheduled records exist?
**Answer**: **Exactly 1,982 unique flight records.**
* Every record contains a unique UUID in `id`.
* The composite key `FlightNumber_Direction_Date_ScheduledTime` yields **1,982 distinct values (0 duplicates)**.
* 1,981 records possess `status: "scheduled"`, and 1 record possesses `status: "arrived"`.

---

### Question 3: How many calendar days have at least one record?
**Answer**: **Exactly 67 consecutive calendar days.**
* The date range begins on **2026-07-05** and ends on **2026-09-09**.
* There are **zero missing dates** within this 67-day span. Every single day has between 24 and 36 scheduled movements.

---

### Question 4: Are arrivals and departures both represented?
**Answer**: **Yes, in near-perfect bilateral equilibrium.**
* **Arrivals**: **993 records** (50.10%).
* **Departures**: **989 records** (49.90%).
* All arrivals have destination `DAM`; all departures have origin `DAM`.

---

### Question 5: Are there explicit actual movement timestamps?
**Answer**: **No. Zero explicit actual movement timestamps exist in the payload.**
* The payload contains only `time` (scheduled time) and `createdAt` (CMS database insertion timestamp).
* There are no fields for `actual_arr_time`, `actual_dep_time`, transponder hex codes (`icao24`), or radar sensor confirmations.

---

### Question 6: What percentage of records have unknown or missing status?
**Answer**: **0.00% (Zero percent).**
* Every single record (1,982 / 1,982) has a populated, valid status string:
  * `scheduled`: **1,981 records (99.95%)**
  * `arrived`: **1 record (0.05%)**
* There are zero records with null, empty, or unrecognized status values.

---

### Question 7: Is the dataset suitable for historical scheduled-service analysis?
**Answer**: **Yes, highly suitable and authoritative for scheduled commercial operations.**
* The dataset provides an official, comprehensive record of commercial airline scheduling, route networks, operating carriers, and daily movement frequencies for Damascus International Airport during Q3 2026 (high summer peak).
* It accurately captures 14 international and regional airlines operating across 20 distinct airport pairs.

---

### Question 8: Is any part suitable for physical-movement verification?
**Answer**: **No. No part of this dataset is suitable for physical-movement verification.**
* In accordance with the project's strict evidentiary rules, scheduled timetables and passenger status labels do not constitute sensor proof of an aircraft touching down or taking off.
* Even the single record with `status: "arrived"` lacks a transponder timestamp. Promoting any of these records to verified `physical_movement` in `flight_events` is strictly prohibited.

---

### Question 9: What limitations prevent using it as a complete historical flight archive?
**Answer**: **Three primary structural limitations:**
1. **Narrow Temporal Horizon**: It covers only 67 days in Q3 2026 (`2026-07-05` to `2026-09-09`). It contains **zero data for 2024, 2025, or early 2026**.
2. **Schedule vs. Reality Gap**: It records published airline schedules and intent; it does not capture day-of-operation cancellations, ad-hoc diversions, charter rotations, or actual runway operational times.
3. **Missing Aircraft Equipment**: Gate assignments are 100% unpopulated, and aircraft model/registration fields are 99.8% empty, preventing airframe-level fleet utilization tracking.

---

## 3. Production Integrity Sign-Off

```
================================================================================
FINAL VERIFICATION SIGN-OFF: VERSION 2.14
================================================================================
Production Database:      data/damascus_airport.db
Staging Database:         data/archived_fids_staging.db (NEW, ISOLATED)
Baseline SHA-256 Hash:    c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b
Final SHA-256 Hash:       c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b
Integrity Invariant:      CONFIRMED 100% UNCHANGED
Staged Records Count:     1,982 records (Normalized & Raw)
Authoritative Decision:   APPROVED FOR HISTORICAL SCHEDULE STAGING
================================================================================
```
