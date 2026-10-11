# V2.20.7 — Operational Evidence & Movement Metrics Validation

## Executive Summary

Version 2.20.7 delivers an independent forensic validation of the Syrian Airport Data Engine, focusing on operational evidence provenance for all physical movement records, semantic precision in movement-count metrics, and alignment between backend calculations, API responses, dashboard displays, and export metadata.

Key achievements of this milestone:
1. **Per-Event Validation of 9 Physical-Movement Departures:** Validated the raw payloads and timestamp provenance for all 9 physical movements (7 at DAM, 2 at ALP). Confirmed that their actual departure timestamps originate from explicit commercial `real` / `actual` fields (`time.real.departure` on Flightradar24 and `departure.actual` on AviationStack). Foreign destination arrival times (`time.estimated.arrival`) are strictly recognized as destination estimates (`estimated_arr_time`), while missing actual arrival timestamps remain strictly `null`.
2. **Telemetry Boundary Clarification:** Direct ground runway sensor evidence (ASDE-X, optical/transponder surface radar) remains pending (`runway_movement_evidence = null`). Commercial aggregator status updates are explicitly labeled as `commercial_status_corroborated`, never direct runway confirmations.
3. **Movement Metric Renaming & Semantics:** Renamed `confirmed_unique_movement_count` to `resolved_commercial_movement_count` to remove the misleading connotation of runway radar confirmation, while preserving `confirmed_unique_movement_count` as a deprecated backward-compatible alias.
4. **Audit of Counting Metrics:** Formalized identity keys, inclusion/exclusion rules, codeshare deduplication, and registration handling across all movement metrics.
5. **Cross-Check of APIs, Dashboard & Exports:** Updated `/api/movements/comparison`, `/api/events/{event_id}`, and dashboard copy in `static/index.html` to eliminate unverified radar references.
6. **Comprehensive Test Suite & Protected Assets:** Added 25 regression tests in `tests/test_v2_20_7_operational_evidence_and_metrics.py`. All protected baseline SHA-256 hashes remain 100% invariant with zero writes to production databases.

---

## 1. Per-Event Validation of the 9 Physical-Movement Departures

An exhaustive inspection of raw provider payloads (`data/raw/flightradar24_dam_departures_raw.json`, `data/raw/flightradar24_alp_departures_raw.json`, and `data/raw/aviationstack_dam_departures_raw.json`) verified the exact provenance of each physical movement event:

| Event ID | Flight | Airport | Dir | Date | Provider & Source Record ID | Raw Field | Raw Timestamp | Normalized UTC | Explicit Real/Actual? | Nature & Semantics |
| :--- | :--- | :---: | :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| `6f3f3b3c16844646` | **PC771** | ALP | Dep | 2026-10-10 | FR24 (`420ff0b0`) | `time.real.departure` | 1791640807 | `2026-10-10T14:00:07Z` | **Yes (`real`)** | Commercial takeoff; destination ETA in `estimated_arr_time` (`2026-10-10T15:20:55Z`); `actual_arr_time` is `null`. |
| `339297a946c498c3` | **XY230** | ALP | Dep | 2026-10-10 | FR24 (`420fc605`) | `time.real.departure` | 1791638403 | `2026-10-10T13:20:03Z` | **Yes (`real`)** | Commercial takeoff; destination ETA in `estimated_arr_time` (`2026-10-10T15:52:33Z`); `actual_arr_time` is `null`. |
| `ed1a39d3aa27b295` | **EY562** | DAM | Dep | 2026-10-09 | FR24 (`420c4f92`) / AvStack | `time.real.departure` | 1791558501 | `2026-10-09T15:08:21Z` | **Yes (`real`)** | Commercial takeoff; destination ETA in `estimated_arr_time` (`2026-10-09T17:56:00Z`); `actual_arr_time` is `null`. |
| `c5dbcfdfa11cb7b3` | **FYC521** | DAM | Dep | 2026-10-10 | FR24 (`420eb7ef`) | `time.real.departure` | 1791610068 | `2026-10-10T05:27:48Z` | **Yes (`real`)** | Commercial takeoff; destination ETA in `estimated_arr_time` (`2026-10-10T06:44:30Z`); `actual_arr_time` is `null`. |
| `14175fe4b51cfa91` | **FYC727** | DAM | Dep | 2026-10-10 | FR24 (`420f78d3`) | `time.real.departure` | 1791631856 | `2026-10-10T11:30:56Z` | **Yes (`real`)** | Commercial takeoff; destination ETA in `estimated_arr_time` (`2026-10-10T14:04:21Z`); `actual_arr_time` is `null`. |
| `ca726fcf8dc8a9df` | **FZ1114** | DAM | Dep | 2026-10-10 | FR24 (`420fe813`) / AvStack | `time.real.departure` | 1791640456 | `2026-10-10T13:54:16Z` | **Yes (`real`)** | Commercial takeoff; destination ETA in `estimated_arr_time` (`2026-10-10T16:39:35Z`); `actual_arr_time` is `null`. |
| `81d8452b0a0b029f` | **G9376** | DAM | Dep | 2026-10-10 | FR24 (`420f5b9b`) / AvStack | `time.real.departure` | 1791630700 | `2026-10-10T11:11:40Z` | **Yes (`real`)** | Commercial takeoff; destination ETA in `estimated_arr_time` (`2026-10-10T13:56:57Z`); `actual_arr_time` is `null`. |
| `f6afc1b400abecc6` | **RB441** | DAM | Dep | 2026-10-10 | FR24 (`420ff806`) | `time.real.departure` | 1791642278 | `2026-10-10T14:24:38Z` | **Yes (`real`)** | Commercial takeoff; destination ETA in `estimated_arr_time` (`2026-10-10T18:17:12Z`); `actual_arr_time` is `null`. |
| `85e816d0ed6253c6` | **XY592** | DAM | Dep | 2026-10-10 | FR24 (`420fd1a5`) / AvStack | `time.real.departure` | 1791638817 | `2026-10-10T13:26:57Z` | **Yes (`real`)** | Commercial takeoff; destination ETA in `estimated_arr_time` (`2026-10-10T15:39:48Z`); `actual_arr_time` is `null`. |

### Validation Findings
1. **Explicit `real`/`actual` Confirmation:** In all 9 events, the actual departure timestamp was sourced from fields named `time.real.departure` (or `departure.actual` in AviationStack). Zero scheduled or estimated timestamps populate these departure fields.
2. **Destination ETA Quarantine:** Foreign destination arrivals (touchdowns at SAW, DXB, SHJ, SVO, JED) had `time.real.arrival = null` in raw payloads and provided only estimated arrival times (`time.estimated.arrival`). These are strictly placed into `estimated_arr_time`. The Syrian aerodrome actual arrival field `actual_arr_time` remains strictly `null`.
3. **No Direct Runway Sensors:** None of these commercial aggregator status timestamps represent physical on-field runway sensor confirmations (e.g. ASDE-X surface radar or runway threshold sensors). Consequently, `runway_movement_evidence` is strictly `null` across all 9 records.

---

## 2. Validation & Formalization of Movement-Count Metrics

The four central counting metrics were reviewed and formal semantics documented:

### 1. `resolved_commercial_movement_count` (formerly `confirmed_unique_movement_count`)
* **Renaming Rationale:** The term `confirmed` in `confirmed_unique_movement_count` was semantically misleading because it could imply runway sensor confirmation or certified ground radar tracking. It is renamed to `resolved_commercial_movement_count`, while preserving `confirmed_unique_movement_count` as a documented backward-compatible alias.
* **Exact SQL / Calculation:**
  ```sql
  COUNT(DISTINCT CASE 
      WHEN record_nature = 'physical_movement' 
      THEN COALESCE(NULLIF(operating_flight_number, ''), flight_number) 
  END)
  ```
* **Identity Key:** `(flight_date, airport_id, operating_flight_number)`
* **Inclusion Rules:** Records with `record_nature = 'physical_movement'` (operational flights carrying actual/real status timestamps).
* **Exclusion Rules:** Timetable scheduled slots (`record_nature = 'scheduled_service'`), marketing partner codeshares (`record_nature = 'marketing_codeshare'`), and unverified historical claims (`record_nature = 'unverified_movement'`).
* **Codeshare Treatment:** Codeshares represent secondary marketing listings; they do not inflate resolved movement counts.
* **Missing Timestamp Treatment:** Records without actual operational timestamps reside in scheduled or unverified categories and are excluded.
* **Conflicting Registrations / Operators:** Collapses duplicate records sharing the same operating flight number on the same date and aerodrome into a single operating movement leg.

### 2. `ambiguous_movement_identity_count`
* **Exact SQL / Calculation:**
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
* **Inclusion Rules:** Marketing codeshares whose operating flight callsign cannot be joined to an operational flight on that date, direction, and aerodrome.
* **Exclusion Rules:** Codeshares successfully matched to an operating flight (classified as `matched_codeshare_record_count`).
* **Treatment of Ambiguity:** Kept strictly isolated; **never** artificially merged or counted in `resolved_commercial_movement_count`.

### 3. `unique_operating_flight_count`
* **Exact SQL / Calculation:**
  Identical to `resolved_commercial_movement_count`.
* **Semantics:** Distinct operating service callsigns among operational flights. Clearly distinguished from distinct physical airframe bodies (an aircraft may operate multiple flight legs, or multiple commercial services may operate on distinct dates).

### 4. `distinct_reported_aircraft_registrations`
* **Exact SQL / Calculation:**
  ```sql
  SELECT COUNT(DISTINCT NULLIF(aircraft_registration, '')) FROM flight_events;
  ```
* **Identity Key:** Cleaned, non-empty airframe registration string: `NULLIF(aircraft_registration, '')`.
* **Value:** **63** reported tail codes across Syrian aerodromes (**60** among physical movements).
* **Semantics:** Distinct airframe tail numbers reported by commercial airlines and flight feeds. Not equivalent to physical runway sensor or optical camera confirmations.
* **Deprecated Aliases:** `total_unique_aircraft` and `unique_aircraft_tracked` remain available as backward-compatible aliases with deprecation notices.

---

## 3. Cross-Check of API Responses, Dashboard UI & Exports

1. **`/api/movements/comparison`:**
   - Exposes `resolved_commercial_movement_count` as the primary metric.
   - Retains `confirmed_unique_movement_count` as a deprecated backward-compatible alias.
   - Field definitions explicitly clarify that `resolved_commercial_movement_count` does NOT imply runway radar sensor confirmation.
2. **`/api/events/{event_id}`:**
   - Added direct endpoint to inspect canonical event details, returning enriched timestamp fields, evidence transparency fields, and operational classifications.
3. **`/api/movements/verified`:**
   - Description explicitly states: `"Commercially reported operational events with actual departure/arrival status timestamps... Direct on-ground runway sensor telemetry is pending."`
   - `runway_movement_evidence: null` is enforced across all records.
4. **Dashboard (`static/index.html`):**
   - Corrected download card descriptions to replace `"verified physical radar movements"` with `"commercially reported operational events"` and `"commercial flight feeds"`.
   - Updated copy to state that ground runway sensors remain pending.
5. **Research Exports & Metadata Sidecars:**
   - All dataset export headers and `.metadata.json` sidecars declare `evidence_level = "multi_tier_commercial_and_timetable"` and explicitly state that direct runway radar sensor telemetry is pending.

---

## 4. Protected Assets & Cryptographic Invariance

| Protected Asset File | Expected Baseline SHA-256 Hash | Current SHA-256 Hash | Status |
| :--- | :--- | :--- | :---: |
| `data/damascus_airport.db` | `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b` | `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b` | **MATCH** |
| `data/archived_fids_staging.db` | `a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4` | `a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4` | **MATCH** |
| `data/archived_fids_analytics.db` | `e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe` | `e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe` | **MATCH** |
| `data/archived_fids_history_staging.db` | `39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f` | `39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f` | **MATCH** |
| `data/raw/snapshots/wayback_damairport_fids_20260709234230.raw` | `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf` | `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf` | **MATCH** |
| `data/raw/snapshots/wayback_damairport_fids_20260709234230.json` | `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491` | `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491` | **MATCH** |

### Confirmation of Non-Modification
* **Zero Production Database Writes:** No SQL `INSERT`, `UPDATE`, or `DELETE` operations were performed.
* **No Database Migrations:** Schema remained unaltered.
* **No Telemetry Fabrication:** Missing timestamps remain `null`; estimated arrival times are preserved as estimates.
