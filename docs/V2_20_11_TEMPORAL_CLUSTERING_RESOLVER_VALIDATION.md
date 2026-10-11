# V2.20.11 — Temporal Clustering Resolver Validation Report

## Executive Summary

Milestone **V2.20.11** audits and validates the multi-factor **Temporal Clustering Movement Resolver** ([`resolve_defensible_movement_identity`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/src/timestamp_provenance.py#L261)). It subjects the clustering algorithm to rigorous edge-case boundary testing, verifies mathematical transitivity and diameter bounding, validates order invariance and determinism across input permutations, reconciles all 131 physical movement events in the production database, and ensures end-to-end consistency across API endpoints, dashboard interfaces, and data exports.

All operations were conducted using strictly read-only SQLite connections (`file:data/damascus_airport.db?mode=ro`). Zero writes, schema migrations, or backfills were executed, and all six protected cryptographic baseline hashes remain byte-for-byte invariant.

---

## 1. Temporal Clustering Algorithm & Transitivity Audit

### 1.1 Mathematical Formulation: Complete Linkage vs. Single Linkage
In flight movement resolution, candidate observations sharing the same `(airport_id, local_operational_date, movement_type, operating_callsign)` must be partitioned into real-world commercial flight movements:

- **Single-Linkage (Naive Transitive Clustering):** Merges candidate $A$ and $C$ if there exists an intermediate candidate $B$ such that $|t_A - t_B| \le 60\text{m}$ and $|t_B - t_C| \le 60\text{m}$.
  - *Chaining Hazard:* If $t_A = 10:00$, $t_B = 10:45$, and $t_C = 11:15$, single-linkage would merge $A$ and $C$ even though $|t_A - t_C| = 75\text{m} > 60\text{m}$. An arbitrary series of status updates could chain over hours, improperly collapsing distinct operational movements into a single cluster.
- **Diameter-Bounded / Complete Linkage (Adopted in V2.20.11):** Requires that for every pair of observations in a cluster $C$, the pairwise temporal difference must not exceed the operational threshold:
  $$\text{diameter}(C) = \max_{x, y \in C} |t_x - t_y| \le 60.0\text{ minutes}$$
  If the diameter exceeds 60 minutes, the candidate set cannot form a single movement. Furthermore, if adjacent gaps are $\le 180$ minutes, the candidates cannot be separated into distinct turnaround legs. Such cases are strictly classified as **AMBIGUOUS** (`ambiguous_movement_identity_count += 1`), preventing false merges or false splits.

### 1.2 Transitivity & Chaining Audit Results
| Scenario | Timestamps | Gap / Spread | Resolution Outcome | Justification |
| :--- | :--- | :--- | :--- | :--- |
| **Direct Corroboration** | 10:00, 10:15 | Gap = 15m $\le$ 60m, Spread = 15m $\le$ 60m | **Resolved Single Movement** (1) | Within 60m tolerance, consistent registrations/carrier. |
| **Boundary Single Movement** | 10:00, 11:00 | Gap = 60m $\le$ 60m, Spread = 60m $\le$ 60m | **Resolved Single Movement** (1) | Upper limit of single-movement reporting variance. |
| **Transitive Chaining Hazard** | 10:00, 10:45, 11:15 | Gaps: 45m, 30m; Total Spread: 75m | **Ambiguous Candidate** (0 resolved, 1 ambiguous) | Diameter exceeds 60m; intermediate gap (30m) $< 180$m prevents separation. |
| **Ambiguous Window** | 10:00, 11:01 | Gap = 61m ($60\text{m} < \Delta \le 180\text{m}$) | **Ambiguous Candidate** (0 resolved, 1 ambiguous) | Too large for feed latency; too small for turnaround leg. |
| **Distinct Recurring Legs** | 06:00, 18:00 | Gap = 720m $> 180\text{m}$ | **Two Distinct Resolved Legs** (2 resolved, 1 callsign) | Exceeds 180m turnaround threshold; morning & evening rotations. |

### 1.3 Order Invariance & Determinism
To guarantee that resolution outcomes never depend on record arrival order, candidate records within each operational group are sorted deterministically using a composite tie-breaker:
$$\text{Sort Key} = (t_{\text{parsed\_utc}}, \text{event\_id}, \text{aircraft\_registration})$$
Tested across all permutations of multi-candidate inputs ($3! = 6$ permutations): resolution yields identical cluster boundaries, counts, and primary anchors in 100% of cases.

### 1.4 Aircraft Registration & Carrier Conflict Safety
- **Missing Registration Handling:** A record omitting aircraft registration (e.g. an aggregator feed omitting tail numbers) safely merges with a record having an explicit registration if callsign, direction, and timestamps match within 60 minutes.
- **Conflicting Registrations:** If two candidates within 60 minutes report conflicting explicit airframes (e.g. `YK-AKG` vs `YK-AKH`), the resolver refuses to merge them and flags the event as ambiguous (`ambiguous_movement_identity_count += 1`, `resolved_commercial_movement_count += 0`).
- **Conflict Masking Protection:** A record with missing registration between two conflicting registrations does not mask the conflict: the group remains strictly ambiguous.

---

## 2. Validation of Operational Time Thresholds

| Delta ($\Delta$) | Classification | Semantics & Operational Rationale |
| :---: | :---: | :--- |
| **15 minutes** | `RESOLVED_SAME_MOVEMENT` | High-confidence multi-provider commercial corroboration. Normal variance between wheels-up telemetry and gate pushback updates. |
| **59 minutes** | `RESOLVED_SAME_MOVEMENT` | Standard operational status update delay, extended taxiing, or feed synchronization latency. |
| **60 minutes** | `RESOLVED_SAME_MOVEMENT` | Exact upper boundary for single-movement commercial observation variance. |
| **61 minutes** | `AMBIGUOUS_DELTA` | Enters ambiguous window. An aircraft cannot fly a turnaround leg at DAM within 61 minutes, yet 61 minutes is too wide to confidently merge as one feed update. |
| **120 minutes** | `AMBIGUOUS_DELTA` | Core ambiguous window. Turnaround times for regional commercial narrowbodies are uncertain; unresolved without airframe telemetry. |
| **180 minutes** | `AMBIGUOUS_DELTA` | Upper boundary of ambiguous window. Preserves conservative research posture. |
| **181 minutes** | `SPLIT_DISTINCT_LEGS` | Exceeds turnaround window. Confidently establishes distinct recurring flights operating under the same commercial callsign (e.g. morning vs evening rotation). |

*Note: Scheduled and estimated timestamps are strictly prohibited from acting as actual movement anchors.*

---

## 3. Full Real-Database Resolver Reconciliation (All 131 Physical Events)

Execution of `resolve_defensible_movement_identity` over all 131 `physical_movement` events in `data/damascus_airport.db` (read-only):

```
Total Input Physical Event Records:       131
Resolved Commercial Movement Clusters:    131
Unique Operating Flight Callsigns:         90
Ambiguous Records:                          0
Records Missing Actual Timestamps:          0
Conflicting Registration Clusters:          0
Multi-Event Clusters in Database:           0
Multi-Provider Corroborated Events:       129
Single-Provider Events:                     2
```

### Reconciliation Table

| Category | Count | % of Total | Representative Event IDs | Operational Interpretation |
| :--- | :---: | :---: | :--- | :--- |
| **Resolved Movement Clusters** | 131 | 100.0% | `ca726fcf8dc8a9df`, `c4fb5f403565e2e8`, `d2cfc4a69ad66316` | Every physical movement event resolves to a unique, verified commercial movement leg. |
| **Multi-Provider Corroborated** | 129 | 98.47% | `ca726fcf8dc8a9df` (`dam+avstack+fr24`), `879105cae0cb0ba3` (`alp+fr24`) | Events corroborated across multiple commercial and airport board sources. |
| **Single-Provider Events** | 2 | 1.53% | `aa075ff1d48aa307` (`FYC761` ALP), `9fa2db08a89a0ece` (`J9180` DEZ) | Single-feed commercial reports (Flightradar24 only). |
| **Missing Actual Timestamps** | 0 | 0.0% | None | All 131 physical movements possess verified actual departure/arrival timestamps. |
| **Conflicting Registrations** | 0 | 0.0% | None | Zero conflicting airframe registrations within identical operational slots. |
| **Ambiguous Physical Records** | 0 | 0.0% | None | Zero unresolved candidates among the 131 physical movements. |

### Airport Breakdown
- **DAM (Damascus International):** 98 movements (51 on 2026-10-09, 47 on 2026-10-10)
- **ALP (Aleppo International):** 32 movements (14 on 2026-10-09, 18 on 2026-10-10)
- **DEZ (Deir ez-Zor Airport):** 1 movement (1 on 2026-10-10)
- **Total:** 131 physical movements across all Syrian aerodromes.

---

## 4. Daily Metric Reconciliation for DAM (October 9 & 10, 2026)

### 4.1 Metric Breakdown

| Metric | Oct 09 (DAM) | Oct 10 (DAM) | Counting Unit & Semantic Meaning |
| :--- | :---: | :---: | :--- |
| `source_record_count` | 113 | 99 | Total canonical database records for aerodrome and date. |
| `scheduled_service_count` | 40 | 37 | Published commercial timetable slots (`record_nature = 'scheduled_service'`). |
| `commercial_operational_event_count` | 51 | 47 | Operational events with verified actual status (`record_nature = 'physical_movement'`). |
| `unique_operating_flight_count` | 51 | 47 | Distinct operating flight callsigns (commercial service numbers, NOT aircraft). |
| `resolved_commercial_movement_count` | 51 | 47 | Distinct commercial movement legs resolved via multi-factor identity anchors. |
| `ambiguous_movement_identity_count` | 2 | 1 | Unmatched marketing codeshare listings with no matching operational flight. |
| `matched_codeshare_record_count` | 17 | 14 | Codeshares successfully matched to an operating flight leg (do not inflate count). |
| `unmatched_codeshare_record_count` | 2 | 1 | Unmatched marketing codeshare database rows. |
| `unverified_record_count` | 3 | 0 | Unverified board records lacking independent confirmation. |

*Reconciliation Invariant:*
$$\text{source\_record\_count} = \text{scheduled} + \text{operational} + \text{codeshares} + \text{unverified}$$
- **Oct 09:** $40 + 51 + (17 + 2) + 3 = 113$
- **Oct 10:** $37 + 47 + (14 + 1) + 0 = 99$

### 4.2 Metric Evolution Across Audit Milestones

| Milestone | Key Movement Identity Mechanism | DAM Oct 9 Resolved | DAM Oct 10 Resolved | Ambiguous (Oct 9 / 10) |
| :--- | :--- | :---: | :---: | :---: |
| **V2.20.8** | Callsign-level SQL separation (`COUNT(DISTINCT operating_flight_number)`). | 51 | 47 | 0 / 0 |
| **V2.20.9** | Codeshare matching & ambiguity isolation; multi-provider event merging. | 51 | 47 | 2 / 1 |
| **V2.20.10** | Multi-factor movement resolver with 60m/180m temporal leg separation. | 51 | 47 | 2 / 1 |
| **V2.20.11** | Diameter-bounded (complete-linkage) clustering; intermediate window (60m–180m) ambiguity; deterministic tie-breaking. | 51 | 47 | 2 / 1 |

### 4.3 Date Grouping Semantics
- **API Grouping:** Uses `flight_date`, which represents the published scheduled operational calendar day on airport flight information display systems (FIDS).
- **Resolver Verification:** Dynamically computes `actual_movement_date` from normalized UTC timestamps projected into Damascus local time (`Asia/Damascus`). All 131 physical movements have `actual_movement_date == flight_date`.

---

## 5. Provider Provenance Semantics

To prevent misleading claims in research exports and user interfaces:
- **Corroboration Classification:** Multi-source records are explicitly labeled:
  `multi_provider_commercial_corroboration`
- **Sensor Evidence Boundary:** Upstream commercial aggregators (Flightradar24, AviationStack) and airport website display boards share upstream operational status updates. Under no circumstances are commercial provider updates presented as certified primary radar or runway ground sensor telemetry.
- **Runway Telemetry Field:** `runway_movement_evidence` is strictly enforced as `null` across all 1,830 database records.

---

## 6. API, Dashboard & Export Consistency

1. **API Endpoints:**
   - `/api/movements/comparison` uses the exact multi-factor counting definitions validated by the resolver.
   - Deprecated metric aliases (`confirmed_unique_movement_count`, `unique_flight_movement_count`) return identical values to `resolved_commercial_movement_count` with explicit deprecation documentation.
2. **Dashboard Controls:**
   - `static/index.html` displays `resolved_commercial_movement_count`, `unique_operating_flight_count`, and `ambiguous_movement_identity_count` in dedicated research comparison panels.
   - Displays prominent warnings that commercial operational events do not represent ground radar sensor contacts.
3. **CSV & JSON Exports:**
   - Export headers include `x-evidence-level`, `x-source-provenance`, and `x-dataset-scope`.

---

## 7. Cryptographic Baseline Verification

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

**Hash Verification Status: 100% INVARIANT (Zero database mutations).**
