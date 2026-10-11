# V2.20.10 — Movement Leg Identity & SQL Counting Consistency

## Executive Summary

Version 2.20.10 resolves the fundamental semantic contradiction between single-callsign repeated flight legs (e.g. morning and evening departures) and multi-provider deduplication in the Syrian Airport Data Engine.

In V2.20.9, the SQL identity key was:
```sql
(airport_id, flight_date, movement_type, operating_flight_number)
```
While this prevented duplicate `event_id` records from inflating counts, it inadvertently collapsed two distinct legs operated by the same airline under the same flight number on the same date and direction.

Under V2.20.10:
1. **Multi-Factor Movement Leg Identity Logic:** Adopted `resolve_defensible_movement_identity` in `src/timestamp_provenance.py` and `src/api.py`. Movement legs are anchored by aerodrome, local movement date, direction, operating callsign, actual movement timestamp, and airframe registration compatibility.
2. **Repeated Callsign Separation:** Verified that two flights operating under the same callsign >180 minutes apart (e.g., 06:00 and 18:00) resolve into **2 distinct movement legs**, while `unique_operating_flight_count` remains **1**.
3. **Multi-Provider Merge Invariance:** Verified that multiple provider observations of the same physical movement within 60 minutes (e.g. FR24 at 13:54:16Z and AviationStack at 13:54:00Z) merge into **1 movement leg**.
4. **Timestamp Provenance of KU551/KU552:** Audited raw payloads in `data/raw/` for the 6 KU551/KU552 dual-representation records. Both FR24 (`time.real`) and AviationStack (`actual`) confirmed actual touchdown and takeoff timestamps for Oct 9 and Oct 10 operations, while Oct 11 records were strictly scheduled timetable slots with null actual timestamps.
5. **Zero Production DB Writes:** All 6 protected baseline SHA-256 hashes remain 100% invariant across execution.

---

## 1. Audit of Pure SQL Limitations

### A. The Collapse Contradiction in Pure SQL
A simple SQL `COUNT(DISTINCT airport_id || '_' || flight_date || '_' || movement_type || '_' || callsign)` fails on repeated flight numbers:
* If Syrian Air operates `RB100` at 06:00 and `RB100` at 18:00, both records share identical `(DAM, 2026-10-10, departure, RB100)` keys.
* A pure callsign-grouping key collapses these 2 real-world flight operations into 1.

### B. The Timestamp Inflation Contradiction in Pure SQL
Conversely, appending raw actual timestamps to the SQL string:
`airport_id || '_' || flight_date || '_' || movement_type || '_' || callsign || '_' || actual_dep_time`
fails on multi-provider feeds:
* FR24 reports actual departure `13:54:16Z`.
* AviationStack reports actual departure `13:54:00Z`.
* Because `13:54:16Z != 13:54:00Z`, a string distinct count produces 2 instead of 1.

### C. The Defensible Solution Adopted
To resolve both contradictions without guessing, the platform implements a **Temporal Clustering Resolver** (`resolve_defensible_movement_identity`):
1. **Window $\le$ 60 minutes:** Observations within 60m are evaluated for registration and carrier compatibility. If compatible, they merge into **1 movement leg** (multi-provider observation of the same flight).
2. **Window $>$ 180 minutes:** Operations separated by $>180$m (e.g. 12h apart) are split into **distinct movement legs** (e.g. morning and evening legs).
3. **Intermediate Window (60m < diff $\le$ 180m) or Conflicting Registrations:** Flagged as **ambiguous** and excluded from resolved movement totals.

---

## 2. The 10 Synthetic Regression Scenarios

All 10 required synthetic regression scenarios are verified in `tests/test_v2_20_10_movement_leg_identity.py`:

| # | Scenario Description | Evaluation Logic | Resolution & Status |
| :---: | :--- | :--- | :--- |
| **1** | Same callsign, airport, date, direction, two timestamps 12h apart | `RB100` at 06:00 and 18:00 (`diff = 720m > 180m`) | **Count: 2**. Distinct operational legs resolved. Callsign count = 1. |
| **2** | Same movement observed by FR24 and AviationStack within seconds | `FZ1114` at 13:54:16Z vs 13:54:00Z (`diff = 16s <= 60m`), same reg `A6-FEC` | **Count: 1**. Merged into single physical movement leg. |
| **3** | Same callsign with different airframes and different timestamps | `RB100` at 06:00 (`YK-AKG`) and 18:00 (`YK-AKH`), `diff = 720m` | **Count: 2**. Distinct legs evaluated with different airframes. |
| **4** | Same callsign with conflicting registrations in overlapping slot | `RB441` at 14:24:38Z with `YK-AKG` vs `YK-AKH` (`diff = 0m`) | **Ambiguous (Count: 0 resolved, 1 ambiguous)**. Airframe conflict prevents merge. |
| **5** | Same callsign with missing actual timestamps | `RB999` with `actual_dep_time = None` | **Unresolved (Count: 0 resolved, 1 ambiguous)**. Lacks operational anchor. |
| **6** | Same scheduled flight listed by two providers | Two `scheduled_service` records for `KU551` without actual times | **Count: 0 operational, 2 scheduled services**. Timetable only. |
| **7** | Multiple codeshares pointing to one operating movement | `QR6119` and `WY5233` both point to `RJ437` arrival at 11:45:38Z | **Count: 1**. Codeshares deduplicated against operating flight. |
| **8** | Two different operating callsigns | `RB441` and `FZ1114` on same date and direction | **Count: 2**. Distinct operating airline services. |
| **9** | Same callsign on different local dates | `RJ437` on Oct 9 vs `RJ437` on Oct 10 | **Count: 2**. Distinct legs anchored by separate dates. |
| **10** | Scheduled date differs from actual local movement date | Scheduled 23:50 Oct 9, actual departure 00:15 Oct 10 Damascus local | **Count: 1**. Anchored to Oct 10 actual movement date. |

---

## 3. Audit of KU551 / KU552 Cross-Nature Overlaps

Raw JSON payloads in `data/raw/` (`flightradar24_dam_arrivals_raw.json`, `flightradar24_dam_departures_raw.json`, `aviationstack_dam_arrivals_raw.json`, `aviationstack_dam_departures_raw.json`) were forensically inspected:

| Date | Flight | Movement | FR24 Raw Field & Value | AviationStack Raw Field & Value | Verified Semantic Provenance |
| :---: | :---: | :---: | :--- | :--- | :--- |
| **2026-10-09** | **KU551** | Arrival | `flight.time.real.arrival = 1791533798` (`08:16:38Z`), `status.text = "Landed 11:16"`, reg `9K-AKO` | `arrival.actual = "2026-10-09T11:16:00+00:00"` (local `11:16`, UTC `08:16:00Z`) | **Genuine Actual Timestamp** (observed touchdown by both providers, diff = 38s). |
| **2026-10-09** | **KU552** | Departure | `flight.time.real.departure = 1791539286` (`09:48:06Z`), `status.text = "Departed 12:48"`, reg `9K-AKO` | `departure.actual = "2026-10-09T12:48:00+00:00"` (local `12:48`, UTC `09:48:00Z`) | **Genuine Actual Timestamp** (observed takeoff by both providers, diff = 6s). |
| **2026-10-10** | **KU551** | Arrival | `flight.time.real.arrival = 1791621418` (`08:36:58Z`), `status.text = "Landed 11:36"`, reg `9K-AKP` | `arrival.actual = "2026-10-10T11:36:00+00:00"` (local `11:36`, UTC `08:36:00Z`) | **Genuine Actual Timestamp** (observed touchdown by both providers, diff = 58s). |
| **2026-10-10** | **KU552** | Departure | `flight.time.real.departure = 1791626028` (`09:53:48Z`), `status.text = "Departed 12:53"`, reg `9K-AKP` | `departure.actual = "2026-10-10T12:53:00+00:00"` (local `12:53`, UTC `09:53:00Z`) | **Genuine Actual Timestamp** (observed takeoff by both providers, diff = 48s). |
| **2026-10-11** | **KU551** | Arrival | `flight.time.real.arrival = None`, `status.text = "Scheduled"`, reg = `""` | `None` | **Scheduled Only** (no actual or estimated movement telemetry). |
| **2026-10-11** | **KU552** | Departure | `flight.time.real.departure = None`, `status.text = "Scheduled"`, reg = `""` | `None` | **Scheduled Only** (no actual or estimated movement telemetry). |

### Conclusion on KU Overlaps
* On **2026-10-09** and **2026-10-10**, the four Kuwait Airways records represent **genuine operational movements** corroborated by both Flightradar24 and AviationStack with actual flight status timestamps and verified airframe registrations (`9K-AKO` on Oct 9, `9K-AKP` on Oct 10).
* On **2026-10-11**, both providers list **purely scheduled services** without operational telemetry.

---

## 4. Metric Semantics & Separation

In `/api/movements/comparison`, the metrics are strictly separated and exposed:

```
+------------------------------------+-----------------------+-------------------------------------------------------------+
| Metric Field                       | Counting Unit         | Definition & Semantics                                      |
+------------------------------------+-----------------------+-------------------------------------------------------------+
| unique_operating_flight_count      | Operating Service     | Distinct operating airline callsign strings on that date.   |
| resolved_commercial_movement_count | Operational Leg       | Defensibly resolved movement legs anchored by telemetry.    |
| ambiguous_movement_identity_count  | Ambiguous Candidate   | Unresolved candidates (unmatched codeshares, conflicts).    |
| scheduled_service_count            | Timetable Record      | Published timetable slots without operational telemetry.    |
| source_record_count                | Canonical Database Row| Total raw database records for the aerodrome and date.      |
+------------------------------------+-----------------------+-------------------------------------------------------------+
```

### Damascus Airport (DAM) Before & After Counts

| Date | Metric | V2.20.9 (Legacy Key) | V2.20.10 (Multi-Factor Resolver) | Semantics & Verification |
| :---: | :--- | :---: | :---: | :--- |
| **2026-10-10** | `unique_operating_flight_count` | 47 | **47** | Distinct airline service callsign strings. |
| **2026-10-10** | `resolved_commercial_movement_count` | 47 | **47** | Distinct operational flight legs. |
| **2026-10-10** | `ambiguous_movement_identity_count` | 1 | **1** | Unmatched codeshare candidate (`GF5952` -> `XY377`). |
| **2026-10-10** | `scheduled_service_count` | 37 | **37** | Timetable slots without operational telemetry. |
| **2026-10-10** | `source_record_count` | 99 | **99** | Total canonical database records (37 sched + 47 ops + 15 codeshares). |
| **2026-10-09** | `unique_operating_flight_count` | 51 | **51** | Distinct airline service callsign strings. |
| **2026-10-09** | `resolved_commercial_movement_count` | 51 | **51** | Distinct operational flight legs. |
| **2026-10-09** | `ambiguous_movement_identity_count` | 2 | **2** | Unmatched codeshare candidates (`GF5950`, `GF5952`). |
| **2026-10-09** | `scheduled_service_count` | 41 | **41** | Timetable slots without operational telemetry. |
| **2026-10-09** | `source_record_count` | 113 | **113** | Total canonical database records. |

---

## 5. Protected Assets & Cryptographic Invariance

| Protected Asset Path | Expected Baseline SHA-256 Hash | Current SHA-256 Hash | Verification Status |
| :--- | :--- | :--- | :---: |
| `data/damascus_airport.db` | `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b` | `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b` | **MATCH** |
| `data/archived_fids_staging.db` | `a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4` | `a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4` | **MATCH** |
| `data/archived_fids_analytics.db` | `e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe` | `e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe` | **MATCH** |
| `data/archived_fids_history_staging.db` | `39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f` | `39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f` | **MATCH** |
| `data/raw/snapshots/wayback_damairport_fids_20260709234230.raw` | `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf` | `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf` | **MATCH** |
| `data/raw/snapshots/wayback_damairport_fids_20260709234230.json` | `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491` | `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491` | **MATCH** |

---

## 6. Test Suite Results

Test execution via `python scratch/run_test_suite.py`:
```text
============================ 604 passed in 26.14s =============================
Exit code: 0
Production DB Hash AFTER:  c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b
Hashes match: True
```
All 604 tests in the test suite pass with 100% compliance.
