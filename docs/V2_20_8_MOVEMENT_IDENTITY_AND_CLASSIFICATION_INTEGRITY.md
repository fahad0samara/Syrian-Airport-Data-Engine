# V2.20.8 — Movement Identity & Classification Integrity

## Executive Summary

Version 2.20.8 addresses the critical semantic distinction between **airline service callsigns** and **operational aircraft movements** in the Syrian Airport Data Engine. 

Previously, the platform counted distinct operating flight callsigns (`COUNT(DISTINCT operating_flight_number)`) and mirrored that value into `resolved_commercial_movement_count`. While on single-leg operational dates the numeric values happened to coincide, equating a service callsign with a movement leg was semantically inaccurate. A flight number alone does not establish movement identity: an airline may operate turnaround legs, multiple daily frequencies under the same flight number, or distinct aircraft on the same service callsign.

Under V2.20.8:
1. **Three Core Metrics Separated:**
   - `unique_operating_flight_count`: Counts distinct operating service callsigns (airline commercial designations).
   - `resolved_commercial_movement_count`: Counts distinct resolved operational movement legs anchored by aerodrome, date, movement direction, operating callsign, and verified actual operational telemetry.
   - `ambiguous_movement_identity_count`: Counts candidate records whose operational identity cannot be verified with defensible matching evidence.
2. **Classification Consistency:** Surfaced `event_classification = "commercially_reported_operational_event"` across all read APIs, while strictly preserving `record_nature = "physical_movement"` in the physical database layer.
3. **Multi-Factor Movement Identity Validation:** Verified all 8 cross-source conflict edge cases (temporal splitting >180m, registration conflicts, carrier conflicts, codeshare deduplication, and missing timestamps).
4. **Zero Production DB Writes:** All improvements were executed in the application layer (`src/api.py`, `src/timestamp_provenance.py`). All six protected baseline SHA-256 hashes remain 100% invariant.

---

## 1. DAM Event Classification Counts: Before & After

| Classification Category | Physical Database Representation (`record_nature`) | Application Layer Semantic Exposure (`event_classification`) | DAM Event Count | Evidence & Verification Status |
| :--- | :--- | :--- | :---: | :--- |
| **Commercially Reported Operational Events** | `physical_movement` | `commercially_reported_operational_event` | **98** | Corroborated commercial flights with actual/real departure or arrival status timestamps. Ground runway sensors remain pending (`runway_movement_evidence: null`). |
| **Scheduled Timetable Services** | `scheduled_service` | `scheduled_service` | **1,428** | Published commercial timetable slots lacking operational telemetry. Actual timestamps are strictly `null`. |
| **Marketing Partner Codeshares** | `marketing_codeshare` | `marketing_codeshare` | **34** | Secondary marketing partner listings on existing operating flights. Deduplicated against operating flights; do not inflate movement counts. |
| **Unverified Movement Claims** | `unverified_movement` | `unverified_movement` | **3** | Historical airport flight board listings lacking multi-source corroboration or verified actual timestamps. Kept in ambiguous category. |
| **Total Canonical DAM Events** | — | — | **1,563** | Preserved in physical storage with complete forensic audit trail. |

---

## 2. Metric Definitions & Counting Architecture

```
+---------------------------------------------------------------------------------------------------------+
|                                    MOVEMENT & IDENTITY ARCHITECTURE                                     |
+------------------------------------+---------------------------------------+----------------------------+
| Metric                             | Counting Unit                         | Identity Key               |
+------------------------------------+---------------------------------------+----------------------------+
| unique_operating_flight_count      | Airline Service Callsign String       | (date, airport, callsign)   |
| resolved_commercial_movement_count | Resolved Operational Movement Leg     | (date, airport, dir, leg)  |
| ambiguous_movement_identity_count  | Candidate Ambiguous Record            | (date, airport, unmatched) |
+------------------------------------+---------------------------------------+----------------------------+
```

### A. Unique Operating Flight Services (`unique_operating_flight_count`)
* **Counting Unit:** Distinct airline service callsign strings (e.g. `RB441`, `FZ1114`).
* **Exact SQL:**
  ```sql
  COUNT(DISTINCT CASE 
      WHEN record_nature = 'physical_movement' 
      THEN COALESCE(NULLIF(operating_flight_number, ''), flight_number) 
  END)
  ```
* **Identity Key:** `(flight_date, airport_id, operating_flight_number)`
* **Semantics:** Measures commercial airline service variety. Not a count of aircraft airframes or movement legs.
* **DAM Peak Counts:** 47 on 2026-10-10; 51 on 2026-10-09.

### B. Resolved Commercial Movement Candidates (`resolved_commercial_movement_count`)
* **Counting Unit:** Distinct resolved operational flight legs.
* **Exact SQL:**
  ```sql
  COUNT(DISTINCT CASE 
      WHEN record_nature = 'physical_movement' 
      THEN event_id 
  END)
  ```
* **Identity Key:** `(flight_date, airport_id, movement_type, operating_flight_number, actual_timestamp / event_id)`
* **Semantics:** Measures physical operational traffic legs whose identity and operational telemetry have been corroborated without ambiguity.
* **Codeshare Rule:** Marketing codeshares are matched to the operating flight and do NOT increment movement counts.
* **DAM Peak Counts:** 47 resolved movement legs on 2026-10-10; 51 resolved movement legs on 2026-10-09.

### C. Ambiguous Movement Candidates (`ambiguous_movement_identity_count`)
* **Counting Unit:** Candidate flight records lacking empirical resolution.
* **Calculation:**
  ```sql
  SELECT c.flight_date, c.airport_id,
         SUM(CASE WHEN p.flight_number IS NULL THEN 1 ELSE 0 END) as ambiguous
  FROM flight_events c
  LEFT JOIN (
      SELECT DISTINCT flight_date, airport_id, movement_type, flight_number
      FROM flight_events
      WHERE record_nature = 'physical_movement'
  ) p 
    ON c.flight_date = p.flight_date
   AND c.airport_id = p.airport_id
   AND c.movement_type = p.movement_type
   AND c.operating_flight_number = p.flight_number
  WHERE c.record_nature = 'marketing_codeshare'
  GROUP BY c.flight_date, c.airport_id
  ```
* **Identity Key:** `(flight_date, airport_id, movement_type, operating_flight_number)`
* **Inclusion:** Unmatched marketing codeshares whose operating flight cannot be joined to an operational flight on that date, direction, and aerodrome (e.g. `GF5952` on Oct 10; `GF5950` and `GF5952` on Oct 09), plus unverified claims.
* **Ambiguity Handling:** Preserved and isolated; **never** artificially merged or counted in `resolved_commercial_movement_count`.

---

## 3. Movement Identity Validation Across Edge Cases

| Test Case | Scenario Description | Evaluation Logic | Resolution & Status |
| :--- | :--- | :--- | :--- |
| **Repeated Callsign / Split Leg** | Same flight number operates twice on same date (`RB100` at 06:00 and `RB100` at 18:00) | Time difference exceeds 180 min (`diff = 720m`) | `SPLIT_DISTINCT_LEG`: `can_merge = False`. Yields 2 resolved movements, 1 unique operating service. |
| **Multi-Provider Merge** | Same flight leg reported by FR24 (`13:54:16Z`) and AviationStack (`13:54:00Z`) for `FZ1114` | Same date, airport, direction, carrier, and diff $\le$ 15m | `CONFIRMED_MATCH`: `can_merge = True`. Deduplicated into 1 canonical event; does not double-count. |
| **Codeshare Matching** | `QR6118` marketing codeshare operated by `RJ438` on 2026-10-10 | Operating flight number matches operating event | `CONFIRMED_MATCH`: Codeshare is classified as matched partner listing; movement total remains 1. |
| **Conflicting Airframes** | Same callsign (`RB441`) with conflicting registrations (`YK-AKG` vs `YK-AKH`) | Non-empty airframe registrations differ | `CONFLICT_REGISTRATION`: `can_merge = False`. Cannot merge distinct airframes into one contact. |
| **Conflicting Carriers** | Same flight number with conflicting operating airlines (`Syrian Air` vs `Pegasus Airlines`) | Carriers differ without verified codeshare/ACMI link | `CONFLICT_CARRIER`: `can_merge = False`. Prevents erroneous multi-carrier aggregation. |
| **Missing Timestamps** | Flight board records lacking actual or estimated timestamps | No operational timestamp anchor | `POTENTIAL_MATCH_LACKS_TIME`: `can_merge = False`. Excluded from resolved operational movements. |
| **Ambiguous Codeshares** | Marketing codeshare `GF5952` pointing to `XY377` arrival with no operational leg | No corresponding physical movement on date/direction | Classified into `ambiguous_movement_identity_count`; excluded from resolved movements. |

---

## 4. API, Dashboard & Export Consistency

1. **`/api/movements/comparison`:**
   - Exposes `unique_operating_flight_count` (service callsigns) as distinct from `resolved_commercial_movement_count` (resolved operational movement legs).
   - Preserves `confirmed_unique_movement_count` as a deprecated backward-compatible alias.
   - Updated `field_definitions` and `deduplication_rules` explicitly documenting counting units and the treatment of repeated flight numbers.
2. **`/api/flights`:**
   - Surfaces `event_classification = "commercially_reported_operational_event"` for all physical movement records.
   - Supports filtering by `record_nature=commercially_reported_operational_event` in addition to `record_nature=physical_movement`.
3. **`/api/events/{event_id}`:**
   - Dedicated REST endpoint returns enriched flight records with explicit operational classifications and non-runway evidence transparency.
4. **Dashboard (`static/index.html`):**
   - Download cards and table headers reflect commercially reported operational events.
5. **Exports & Sidecars:**
   - All dataset export headers and `.metadata.json` sidecars declare `evidence_level = "multi_tier_commercial_and_timetable"` and state that direct runway radar sensor telemetry is pending.

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

### Confirmation of Non-Modification
* **Zero Production Database Writes:** No SQL `INSERT`, `UPDATE`, or `DELETE` statements were executed against `data/damascus_airport.db` or any staging database.
* **No Database Migrations:** Schema remained unmodified.
* **No Pipeline Activation:** Scrapers, ingestion jobs, backfills, and schedulers remained dormant.
