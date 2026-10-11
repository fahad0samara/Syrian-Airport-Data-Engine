# V2.20.12 — Independent Movement Resolver & Metrics Audit

## 1. Executive Verdict: PASS WITH LIMITATIONS

An independent, read-only audit of the V2.20.11 temporal clustering resolver, canonical event database, and movement counting metrics was executed against `data/damascus_airport.db` and live API endpoints.

- **Movement Identity & Accounting:** **PASS**  
  Every one of the 131 events currently classified as `physical_movement` is accounted for exactly once. Zero distinct physical movements were accidentally merged, zero duplicate provider observations were double-counted as additional movements, and no conflicting evidence was discarded during representative cluster record selection.
- **Clustering Mechanics & Edge Cases:** **PASS**  
  The multi-factor resolver was evaluated independently against 10 critical edge cases, including equal timestamps with different event IDs, conflicting airframes, missing tail numbers, conflicting carriers, recurring callsigns on the same day, intermediate 60m–180m ambiguous gaps, midnight timezone boundaries, diameter-bounded complete linkage, and input permutations. Order invariance and determinism are mathematically guaranteed.
- **October 9 & 10 Historical Reconciliation:** **PASS**  
  The numerical differences between historical reports and current database contents are fully explained down to specific event IDs:
  - October 10: The 110 vs. 99 difference is an aerodrome-scope conflation ($99\text{ DAM total} + 11\text{ ALP scheduled} = 110$).
  - October 10: The 41 vs. 37 scheduled difference is caused by the isolation of 4 cross-source ambiguous match rows (`MATCH_SAME_AIRPORT_DIR_NUM_TIME_60_180M`) in `deduplication_audit` for dual-reported flights KU551 and KU552 ($41 - 4 = 37$).
  - October 9: All 113 records (40 scheduled, 51 physical movements, 19 marketing codeshares, 3 unverified) reconcile with 100% precision.
- **Production Safety & Baseline Immutability:** **PASS**  
  The production database was accessed strictly via read-only connections (`file:data/damascus_airport.db?mode=ro`). Zero writes, schema migrations, or backfills occurred. All six protected baseline SHA-256 hashes remain byte-for-byte untouched.
- **Limitations:** **DOCUMENTED**  
  The 60-minute single-movement and 180-minute distinct turnaround thresholds represent heuristic research assumptions rather than universal aerodynamic constants. Direct runway ground sensor evidence remains strictly null; all actual timestamps derive from commercial aggregator and airport flight board corroboration.

---

## 2. Full 131-Event Reconciliation

Every one of the 131 canonical `physical_movement` events was audited against raw source records, `v_active_evidence`, and the multi-factor movement resolver:

- **Total Physical Movement Records:** **131**
- **Resolved Commercial Movement Clusters:** **131**
- **Unique Operating Flight Callsigns:** **90**
- **Unaccounted Records:** **0**
- **Accidental Merges:** **0**
- **Missing Actual Timestamps:** **0**
- **Conflicting Registrations Within Clusters:** **0**

### Aerodrome and Direction Distribution
| Aerodrome | Code | Arrivals | Departures | Total Movements | Multi-Provider Corroborated | Single-Provider |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Damascus International** | DAM | 49 | 49 | **98** | 98 | 0 |
| **Aleppo International** | ALP | 16 | 16 | **32** | 31 | 1 |
| **Deir ez-Zor Airport** | DEZ | 1 | 0 | **1** | 0 | 1 |
| **Total** | | **66** | **65** | **131** | **129** | **2** |

### Complete Machine-Readable Audit Datasets
The complete itemized audit register for all 131 physical movement events has been generated and saved to:
- CSV: [`reports/v2_20_12_physical_movement_audit.csv`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/reports/v2_20_12_physical_movement_audit.csv)
- JSON: [`reports/v2_20_12_physical_movement_audit.json`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/reports/v2_20_12_physical_movement_audit.json)

Fields captured per event: `event_id`, `airport_id`, `movement_type`, `flight_number`, `operating_callsign`, `aircraft_registration`, `aircraft_model`, `flight_date`, `actual_movement_date`, `actual_timestamp`, `source`, `provider_count`, `providers`, `evidence_item_count`, `cluster_id`, `resolution_status`, `corroboration_type`, `runway_movement_evidence`, `evidence_discarded`.

---

## 3. Duplicate and Cluster Analysis

### 3.1 Intra-Database Canonicalization
In `data/damascus_airport.db`, every physical movement row represents a single canonical flight event. No two physical movement records on the same operational date, aerodrome, and movement direction share the same operating flight callsign:
- Duplicate canonical events: **0**
- Merged multi-provider observations in canonical database: **129** events merge up to 3 upstream provider feeds (`damairport_official`, `aviationstack`, `flightradar24`).
- Single-provider events: **2** events (`aa075ff1d48aa307` FYC761 at ALP, `9fa2db08a89a0ece` J9180 at DEZ from `flightradar24`).

### 3.2 Dual-Representation Flights (Physical Movement vs. Scheduled Service)
Two flights on October 10 at DAM have dual representation across different `record_nature` classifications:
1. **KU551 (Arrival):**
   - Physical movement: `a7f037c44172a714` (`damairport_official+flightradar24`, actual arr 08:36:58Z).
   - Scheduled service: `5e4c3e64f5f07394` (`aviationstack+flightradar24`, scheduled arr 10:40:00Z).
2. **KU552 (Departure):**
   - Physical movement: `f6d68e398c4ae6e7` (`damairport_official+flightradar24`, actual dep 09:53:48Z).
   - Scheduled service: `07fe775464d8faf4` (`aviationstack+flightradar24`, scheduled dep 11:40:00Z).

*Resolution:* The resolver anchors the operational flight movement strictly using the `physical_movement` event with verified operational telemetry. The corresponding `scheduled_service` row is segregated into published timetable display totals and is never double-counted as an operational movement.

### 3.3 Marketing Codeshare Clustering
Across the entire database, 34 `marketing_codeshare` records exist:
- **31 Matched Codeshares:** Successfully linked to a commercially reported operating flight on the same aerodrome, date, and direction. They are excluded from operating flight and movement counts.
- **3 Unmatched Codeshares:** Unlinked partner ticket listings preserved in `ambiguous_movement_identity_count`:
  - `266051748a8bfc53` (DAM, 2026-10-09, GF5950 $\to$ XY387)
  - `9d63e7b0ca0d99b9` (DAM, 2026-10-09, GF5952 $\to$ XY377)
  - `513b621947d0300a` (DAM, 2026-10-10, GF5952 $\to$ XY377)

---

## 4. October 9 and October 10 SQL Reconciliation

Direct SQL queries executed against `data/damascus_airport.db`:

```sql
SELECT flight_date, airport_id, record_nature, COUNT(*)
FROM flight_events
WHERE flight_date IN ('2026-10-09', '2026-10-10')
GROUP BY flight_date, airport_id, record_nature;
```

### 4.1 Damascus (DAM) Exact Breakdown

| Metric | October 09, 2026 | October 10, 2026 | Counting Unit & Meaning |
| :--- | :---: | :---: | :--- |
| `source_record_count` | **113** | **99** | Total canonical database rows for aerodrome and date. |
| `scheduled_service_count` | **40** | **37** | Published timetable display slots (`record_nature = 'scheduled_service'`). |
| `commercial_operational_event_count` | **51** | **47** | Commercially reported operational flights (`record_nature = 'physical_movement'`). |
| `codeshare_record_count` | **19** | **15** | Secondary partner ticket listings (`record_nature = 'marketing_codeshare'`). |
| `matched_codeshare_record_count` | **17** | **14** | Codeshares matched to an operational movement leg. |
| `unmatched_codeshare_record_count` | **2** | **1** | Codeshares without operational match (ambiguous). |
| `unverified_record_count` | **3** | **0** | Historical completion claims lacking independent corroboration. |
| `unique_operating_flight_count` | **51** | **47** | Distinct operating callsigns (airline service numbers, NOT aircraft). |
| `resolved_commercial_movement_count` | **51** | **47** | Resolved commercial movement legs (multi-factor identity). |
| `ambiguous_movement_identity_count` | **2** | **1** | Candidate movements with unresolved identity. |

*Reconciliation Invariant:*
- Oct 09: $40\text{ sched} + 51\text{ phys} + 19\text{ code} + 3\text{ unver} = 113\text{ total}$
- Oct 10: $37\text{ sched} + 47\text{ phys} + 15\text{ code} + 0\text{ unver} = 99\text{ total}$

### 4.2 Investigation of Numerical Discrepancies

1. **October 10: 110 versus 99 records**
   - **Root Cause:** Conflation of regional aerodrome scope.
   - On October 10, Damascus International Airport (DAM) contains exactly **99** canonical records.
   - Concurrently, Aleppo International Airport (ALP) contains **11** scheduled service records on October 10.
   - Early aggregate reporting queried October 10 scheduled records without aerodrome isolation: $99\text{ (DAM total)} + 11\text{ (ALP scheduled)} = 110\text{ records}$.
   - The correct aerodrome-specific total for DAM is **99**.

2. **October 10: 41 versus 37 scheduled records**
   - **Root Cause:** Deduplication audit ambiguity isolation.
   - In `deduplication_audit`, 4 records for October 10 were flagged under `MATCH_SAME_AIRPORT_DIR_NUM_TIME_60_180M` (`AMBIGUOUS_KEPT_SEPARATE`): audit IDs `1497`, `1498` (KU551) and `1503`, `1504` (KU552).
   - Early un-deduplicated staging counts reflected 41 raw candidate timetable slots.
   - When canonical deduplication resolved the dual representations into separate physical movements and distinct scheduled services, exactly **37** scheduled services remained for DAM.
   - The difference of **4** corresponds exactly to the 4 ambiguous staging records.

3. **October 9: 113 records and 40 scheduled records**
   - All 113 records are fully accounted for: 40 scheduled services, 51 physical movements, 19 codeshares (17 matched, 2 unmatched), and 3 unverified records (`da62b72fddd47380` DN486, `7d218d73064da96f` RJ439, `b039089ebbacd076` RJ440).

4. **Cross-Midnight Arrivals**
   - Three flights scheduled on October 9 arrived after local midnight on October 10:
     - `FYC522`: Scheduled 2026-10-09, actual arrival 2026-10-09T21:41Z $\to$ 2026-10-10 00:41 local.
     - `RB444`: Scheduled 2026-10-09, actual arrival 2026-10-09T21:46Z $\to$ 2026-10-10 00:46 local.
     - `RB502`: Scheduled 2026-10-09, actual arrival 2026-10-09T22:31Z $\to$ 2026-10-10 01:31 local.
   - `flight_date` preserves the published timetable operational day (`2026-10-09`), while `actual_movement_date` correctly reflects the calendar day of touchdown (`2026-10-10`).

---

## 5. API, Dashboard & Export Consistency

1. **Resolver Parity:**
   - Both `/api/movements/comparison` and the test suite call identical logic and return identical counts for all aerodromes and date ranges.
2. **Metric Separation:**
   - `unique_operating_flight_count` counts distinct commercial flight callsigns (e.g. 51 on Oct 9, 47 on Oct 10).
   - `resolved_commercial_movement_count` counts verified operational movement legs.
   - `ambiguous_movement_identity_count` counts distinct unresolved candidate movements (e.g. 2 on Oct 9, 1 on Oct 10), never raw duplicate rows.
3. **Deprecated Aliases:**
   - `confirmed_unique_movement_count` and `unique_flight_movement_count` return identical values to `resolved_commercial_movement_count` with explicit deprecation notices.
4. **Transparency & Sensor Claims:**
   - All API payloads, dashboard panels, and exports enforce `runway_movement_evidence: null`.
   - Corroborated records carry the explicit description `multi_provider_commercial_corroboration`.
   - Prominent warnings state that commercial operational events represent airline operational updates, not physical runway radar contacts.

---

## 6. Remaining Limitations

1. **Configurable Heuristic Thresholds:**
   The 60-minute single-movement tolerance and 180-minute distinct turnaround separation are **heuristic research thresholds**, not physical aviation constants. While suitable for standard commercial turnarounds at Damascus, regional turnarounds under 180 minutes remain classified as ambiguous without airframe transponder telemetry.
2. **Lack of Primary Ground Telemetry:**
   All 131 operational events reflect commercial provider updates (Flightradar24, AviationStack, and official FIDS boards). No primary radar or multilateration ground receiver directly confirms runway occupancy.
3. **Unresolved Codeshares:**
   Three marketing codeshare listings have no matching operating flight in the canonical database and remain preserved in ambiguity metrics.

---

## 7. Full Test Results

The platform regression test suite was executed via `scratch/run_test_suite.py`:

```
============================ 644 passed in 24.89s =============================
Exit code: 0
```

- Total passing tests: **644**
- Total failing tests: **0**
- Test suites covering movement identity:
  - `tests/test_v2_20_10_movement_leg_identity.py` (17 tests)
  - `tests/test_v2_20_11_temporal_clustering_validation.py` (24 tests)
  - `tests/test_v2_20_12_independent_movement_audit.py` (16 tests)

---

## 8. Cryptographic Baseline Verification & Safety Confirmation

All six protected baseline data assets were verified byte-for-byte before and after test execution:

```
Asset 1: data/damascus_airport.db
SHA-256: c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b

Asset 2: data/archived_fids_staging.db
SHA-256: a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4

Asset 3: data/archived_fids_analytics.db
SHA-256: e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe

Asset 4: data/archived_fids_history_staging.db
SHA-256: 39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f

Asset 5: data/raw/snapshots/wayback_damairport_fids_20260709234230.raw
SHA-256: 5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf

Asset 6: data/raw/snapshots/wayback_damairport_fids_20260709234230.json
SHA-256: ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491
```

**Production Safety Invariant:**
- Production databases were queried strictly via read-only connections (`file:data/damascus_airport.db?mode=ro`).
- Zero production database writes, schema alterations, or data backfills were executed.
- Zero external network requests, account registrations, paid subscriptions, or Task Scheduler modifications occurred.
- All raw historical payloads, snapshots, and immutable ledger evidence remain byte-for-byte identical to baseline.
