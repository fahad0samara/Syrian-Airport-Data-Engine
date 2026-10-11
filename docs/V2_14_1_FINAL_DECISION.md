# Syrian Airport Data Engine — Version 2.14.1
# Final Decision & Audit Approval

## 1. Executive Summary

Version 2.14.1 executed a comprehensive semantic and data integrity audit of the 1,982 archived Damascus International Airport (`DAM` / `OSDI`) FIDS records extracted in Version 2.14 from the verified Wayback Machine snapshot (`2026-07-09T23:42:30Z`).

The audit verified record identity, source UUID uniqueness, 1:1 raw-to-normalized reconciliation, duplicate candidate groupings, displayed airline brand semantics, status semantics, and Damascus local time conversion.

---

## 2. Definitive Answers to Key Audit Questions

### 1. Can all 1,982 source records be traced to their raw JSON objects?
**YES.** Every normalized record in `archived_fids_normalized` joins on a strict 1:1 basis with `archived_fids_raw_records` via `raw_record_id` and `source_uuid`. Zero records were dropped, synthesized, or orphaned. Every record contains an immutable SHA-256 hash (`raw_record_hash`) derived from its raw JSON serialization.

### 2. Are all records unique by source identity?
**YES.** All 1,982 records possess unique, valid 36-character canonical UUIDs (`source_uuid`) assigned by the source airport API. There are zero UUID collisions across the dataset. The source UUID is formally established as the primary record identity.

### 3. Are there any semantic duplicate candidates?
**YES, EXACTLY ONE CANDIDATE PAIR.** 
- There are **zero exact duplicates** across the entire dataset.
- There are **zero composite key collisions** (`CleanedFN + Dir + Date + Time`).
- Exactly **one semantic duplicate candidate pair** was identified on `2026-07-08` at `13:55` for departure to Sharjah (`SHJ`) by `طيران العربية`:
  - `e5ada70d-5245-46d4-b043-bf469c1d104f`: flight number `G9 376`, created on July 4, 2026.
  - `2d2a0935-da5e-42c4-ad15-e10b4e2291ee`: flight number `376`, created on July 7, 2026 during a batch upload where the `G9` prefix was omitted.
- In strict adherence to data preservation principles, both records are preserved unaltered in the staging database and indexed in [`reports/v2_14_1_duplicate_candidates.csv`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/reports/v2_14_1_duplicate_candidates.csv).

### 4. Does the source identify operating carriers or only displayed airlines?
**DISPLAYED AIRLINES ONLY.** 
The source payload contains the passenger-facing commercial brand shown on airport FIDS screens (e.g. `طيران العربية`, `فلاي شام`, `الاتحاد للطيران`). It provides zero aircraft registrations, zero ICAO 3-letter operator codes, and zero crew filings. All reporting has been formally renamed to **`Displayed Airline Distribution`**, and all operating carrier claims are marked unverified (`FALSE`).

### 5. What does the "arrived" status actually establish?
**ARCHIVED DISPLAY OBSERVATION ONLY.**
The single record bearing the status `"arrived"` (`XH 728`, DXB $\rightarrow$ DAM, scheduled `2026-07-06 00:20`) establishes only that approximately 7 minutes after scheduled arrival time (`2026-07-06T00:27:33Z`), the airport website display indicator displayed the text label `"arrived"`. It contains zero transponder sensor data, zero runway touchdown timestamps, and zero radar telemetry. It is strictly prohibited from being classified as a verified landing or physical movement.

### 6. Are the normalized local and UTC times defensible?
**YES.**
Under the Decree of the Syrian Council of Ministers (October 2022), Syria operates under permanent year-round **`UTC+3`** (`Asia/Damascus`). Airport FIDS times represent local Damascus wall-clock time. UTC timestamps were calculated strictly by subtracting 3 hours, with verified day-rollover handling for flights scheduled between `00:00` and `02:59` local time.

### 7. Is the staging dataset approved for historical scheduled-service analysis?
**YES.**
The staging dataset (`data/archived_fids_staging.db`) is fully approved for historical scheduled-service, timetable frequency, displayed route network, and commercial airline brand analysis for the period `2026-07-05` through `2026-09-09`.

### 8. Is it still prohibited from physical-movement verification?
**YES, ABSOLUTELY.**
FIDS schedule listings and website display flags do not constitute physical aircraft movement evidence under the Syrian Airport Data Engine governance charter. The dataset remains strictly segregated in the staging layer and is prohibited from insertion into production flight events.

---

## 3. Production Database Invariant & Safety Confirmation

The production database `data/damascus_airport.db` was verified in read-only mode:
- **Baseline SHA-256**: `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`
- **Current SHA-256**: `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`
- **Integrity Status**: 100% Bit-for-bit identical. Zero production writes.

No background collectors, Windows Task Scheduler tasks, external outreach, or account creations were performed.
Production integration remains unauthorized and prohibited in this version.
