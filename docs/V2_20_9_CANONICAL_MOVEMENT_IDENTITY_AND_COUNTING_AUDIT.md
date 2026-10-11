# V2.20.9 — Canonical Movement Identity & Counting Audit

## Executive Summary

Version 2.20.9 completes a rigorous audit of movement identity and counting correctness across all 1,830 canonical events in the Syrian Airport Data Engine. 

Key achievements:
1. **Audit of Canonical Event Identity:** Inspected all 1,830 events and all 131 `physical_movement` events. Identified 6 real-world commercial flights with dual representations across ingestion feeds (where one feed was classified as `physical_movement` and another as `scheduled_service`), plus 2 duplicate scheduled timetable pairs. Within `physical_movement` alone, confirmed 0 duplicate records.
2. **Decoupling Movement Count from `event_id`:** Replaced raw `COUNT(DISTINCT event_id)` in `/api/movements/comparison` with multi-factor leg keys `(airport_id, flight_date, movement_type, operating_flight_number)`. This ensures that multiple database events representing the same real-world flight leg cannot inflate movement counts.
3. **Codeshare Ambiguity Counting:** Refined `ambiguous_movement_identity_count` to measure distinct unresolved operating candidates (`COUNT(DISTINCT candidate_target)`), while `unmatched_codeshare_record_count` tracks database row frequency.
4. **Classification & Evidence Consistency:** Audited all 1,830 records to ensure `physical_movement` surfaces as `commercially_reported_operational_event`, and `runway_movement_evidence` is strictly `null`.
5. **Zero Production DB Writes:** All 6 protected baseline SHA-256 hashes remain 100% invariant.

---

## 1. Audit of Canonical Event Identity

### A. Database-Wide Event Inventory (1,830 Total Records)

| Aerodrome | Physical Movement (DB) / Operational Event (API) | Scheduled Service | Marketing Codeshare | Unverified Claim | Total Records |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **DAM** (Damascus) | 98 | 1,428 | 34 | 3 | **1,563** |
| **ALP** (Aleppo) | 32 | 229 | 0 | 0 | **261** |
| **DEZ** (Deir ez-Zor) | 1 | 5 | 0 | 0 | **6** |
| **Total** | **131** | **1,662** | **34** | **3** | **1,830** |

### B. Identified Duplicate Canonical Events

Cross-source grouping by `(airport_id, flight_date, movement_type, flight_number)` identified **8 pairs of overlapping records**:

#### 1. Dual-Representation Operational Overlaps (6 Flights)
For these 6 commercial flights, two distinct providers ingested records: one was stored as `physical_movement` (with verified operational telemetry), while the second was stored as `scheduled_service`:
1. **KU551 (DAM, 2026-10-09 Arrival):**
   - `338013f63c29b89e`: `physical_movement` (`damairport_official+flightradar24`, actual arr `08:16:38Z`, reg `9K-AKO`)
   - `7d8bf4408c2ebd29`: `scheduled_service` (`aviationstack+flightradar24`, actual arr `08:16:00Z`, reg `9K-AKO`)
2. **KU552 (DAM, 2026-10-09 Departure):**
   - `5860be4ec1930a7d`: `physical_movement` (`damairport_official+flightradar24`, actual dep `09:48:06Z`, reg `9K-AKO`)
   - `50349b022e95cb8e`: `scheduled_service` (`aviationstack+flightradar24`, actual dep `09:48:00Z`, reg `9K-AKO`)
3. **KU551 (DAM, 2026-10-10 Arrival):**
   - `a7f037c44172a714`: `physical_movement` (`damairport_official+flightradar24`, actual arr `08:36:58Z`, reg `9K-AKP`)
   - `5e4c3e64f5f07394`: `scheduled_service` (`aviationstack+flightradar24`, actual arr `08:36:00Z`, reg `9K-AKP`)
4. **KU552 (DAM, 2026-10-10 Departure):**
   - `f6d68e398c4ae6e7`: `physical_movement` (`damairport_official+flightradar24`, actual dep `09:53:48Z`, reg `9K-AKP`)
   - `07fe775464d8faf4`: `scheduled_service` (`aviationstack+flightradar24`, actual dep `09:53:00Z`, reg `9K-AKP`)
5. **3L504 (DAM, 2026-10-09 Arrival):**
   - `9f6b8756b5dc286f`: `physical_movement` (`aviationstack+flightradar24`, actual arr `07:02:53Z`, reg `A6-AUE`)
   - `3032d52b24c076c6`: `scheduled_service` (`damairport_official+flightradar24`, sched arr `09:15:00Z`)
6. **3L505 (DAM, 2026-10-09 Departure):**
   - `186aafcfa362ce5a`: `physical_movement` (`aviationstack+flightradar24`, actual dep `08:40:20Z`, reg `A6-AUE`)
   - `8e175a742c8a7bfc`: `scheduled_service` (`damairport_official+flightradar24`, sched dep `10:15:00Z`)

#### 2. Duplicate Scheduled Timetable Slots (2 Flights)
7. **KU551 (DAM, 2026-10-11 Arrival):** `bc2bad216c908835` (Damascus FIDS) and `7bd42f080650185a` (FR24). Both `scheduled_service`, no operational telemetry.
8. **KU552 (DAM, 2026-10-11 Departure):** `9b2022032251803a` (Damascus FIDS) and `c5b55bb5a8f87343` (FR24). Both `scheduled_service`, no operational telemetry.

*(Note: RB381 on 2026-10-11 has two scheduled departure slots at 13:35 and 16:35, representing two distinct scheduled flights on that date).*

#### 3. Duplicate Records Within `physical_movement`
* **Count:** **0**. No duplicate records exist within `physical_movement` for the same aerodrome, date, direction, and callsign.

---

## 2. Validation of Resolved Movement Counts

### Semantic Distinction of Metrics

```
+------------------------------------+------------------------------------+---------------------------------------------------+
| Metric                             | Counting Unit                      | Identity Key                                      |
+------------------------------------+------------------------------------+---------------------------------------------------+
| unique_operating_flight_count      | Airline Service Callsign           | (airport_id, flight_date, operating_flight_num)    |
| resolved_commercial_movement_count | Resolved Operational Movement Leg  | (airport_id, flight_date, movement_type, callsign)|
| ambiguous_movement_identity_count  | Distinct Unresolved Candidate      | (airport_id, flight_date, movement_type, target)  |
| unmatched_codeshare_record_count   | Database Row Count                 | Raw marketing row count                           |
+------------------------------------+------------------------------------+---------------------------------------------------+
```

### Decoupling from `event_id`
Previously, `resolved_commercial_movement_count` executed:
```sql
COUNT(DISTINCT CASE WHEN record_nature = 'physical_movement' THEN event_id END)
```
This counted database rows rather than real-world movement legs. Under V2.20.9, this was updated to:
```sql
COUNT(DISTINCT CASE WHEN record_nature = 'physical_movement' THEN 
    airport_id || '_' || flight_date || '_' || movement_type || '_' || COALESCE(NULLIF(operating_flight_number, ''), flight_number)
END)
```
* **Protection:** Even if multiple provider payloads produce multiple `event_id` records in `physical_movement`, they merge into **1** resolved movement count.
* **Peak Counts:**
  - DAM 2026-10-10: **47** resolved movement legs (47 distinct operating callsigns).
  - DAM 2026-10-09: **51** resolved movement legs (51 distinct operating callsigns).
  - ALP 2026-10-10: **18** resolved movement legs.
  - ALP 2026-10-09: **14** resolved movement legs.
  - DEZ 2026-10-10: **1** resolved movement leg.
  - Schedule-Only Dates (e.g., 2026-10-01): **0** resolved movement legs.

---

## 3. Codeshare Ambiguity Audit

### A. Codeshares Referencing the Same Operating Flight
Multiple marketing codeshares frequently reference the same underlying operating flight:
- **DAM 2026-10-10 Arrival (RJ437):** Both `QR6119` (Qatar Airways) and `WY5233` (Oman Air) codeshare on `RJ437`. Both match to `RJ437` and do not increment movement counts.
- **DAM 2026-10-10 Departure (RJ438):** Both `QR6118` and `WY5234` codeshare on `RJ438`. Both match to `RJ438`.
- **DAM 2026-10-09 Arrival (RJ437):** Both `QR6119` and `WY5233` match to `RJ437`.
- **DAM 2026-10-09 Departure (RJ438):** Both `QR6118` and `WY5234` match to `RJ438`.

### B. Distinct Unresolved Candidate Counts
`ambiguous_movement_identity_count` now counts distinct unresolved target flight candidates (`COUNT(DISTINCT candidate_target)`):
- **DAM 2026-10-10:** **1** distinct unresolved candidate (`GF5952` pointing to missing flight `XY377`).
- **DAM 2026-10-09:** **2** distinct unresolved candidates (`GF5950` -> `XY375`, `GF5952` -> `XY377`).
- If multiple marketing codeshares or duplicate marketing rows reference the same missing operating flight, they resolve to **1** ambiguous candidate.

---

## 4. Classification Consistency

Audited all 1,830 canonical events:
1. `record_nature = 'physical_movement'` maps to:
   - `event_classification = "commercially_reported_operational_event"`
   - `evidence_level = "commercial_operational_status"`
2. `record_nature = 'scheduled_service'` maps to:
   - `event_classification = "scheduled_service"`
   - `evidence_level = "scheduled_timetable_display"`
3. `record_nature = 'marketing_codeshare'` maps to:
   - `event_classification = "marketing_codeshare"`
   - `evidence_level = "commercial_partner_listing"`
4. `record_nature = 'unverified_movement'` maps to:
   - `event_classification = "unverified_movement"`
   - `evidence_level = "unverified_claim"`
5. `runway_movement_evidence`: strictly `null` across all 1,830 events. No aggregator observation is relabeled as direct runway or radar sensor verification.

---

## 5. Protected Assets & Cryptographic Invariance

| Protected Asset Path | Expected Baseline SHA-256 Hash | Current SHA-256 Hash | Status |
| :--- | :--- | :--- | :---: |
| `data/damascus_airport.db` | `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b` | `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b` | **MATCH** |
| `data/archived_fids_staging.db` | `a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4` | `a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4` | **MATCH** |
| `data/archived_fids_analytics.db` | `e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe` | `e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe` | **MATCH** |
| `data/archived_fids_history_staging.db` | `39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f` | `39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f` | **MATCH** |
| `data/raw/snapshots/wayback_damairport_fids_20260709234230.raw` | `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf` | `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf` | **MATCH** |
| `data/raw/snapshots/wayback_damairport_fids_20260709234230.json` | `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491` | `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491` | **MATCH** |

* **Zero Production DB Writes:** No SQL writes to `data/damascus_airport.db` or staging databases.
* **No Database Migrations:** Production schema unchanged.
* **No Pipeline Activation:** Collectors, schedulers, and scrapers remained dormant.

---

## 6. Regression Test Suite Results

Test execution via `python scratch/run_test_suite.py`:
```text
============================ 587 passed in 24.74s =============================
Exit code: 0
Production DB Hash AFTER:  c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b
Hashes match: True
```
All 10 required regression tests in `tests/test_v2_20_9_canonical_movement_identity.py` passed with 100% compliance.
