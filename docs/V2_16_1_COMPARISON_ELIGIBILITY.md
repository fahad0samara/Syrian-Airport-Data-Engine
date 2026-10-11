# V2.16.1 — Comparison Eligibility Matrix & Rules
## Snapshot Compatibility, Scoping Constraints & Cross-Snapshot Comparison Invariants

**Syrian Airport Data Engine — Version 2.16.1**  
**Audit Date:** 2026-10-11  
**Module Audited:** `src/archived_fids_snapshot_comparison.py`  
**Database Audited:** `data/archived_fids_history_staging.db`

---

## 1. Executive Summary

This document formalizes the comparative eligibility framework governing cross-snapshot diffing in the Syrian Airport Data Engine. 

Direct comparisons between snapshots captured under differing query parameters, directional filters, or pagination boundaries will generate misleading analytical artifacts (e.g. reporting thousands of cancelled flights when the second snapshot was merely filtered to arrivals). Version 2.16.1 introduces a formal eligibility state machine and automated pre-comparison validation to prevent illegitimate comparisons.

---

## 2. Comparison Eligibility Classifications

Every snapshot in `archived_snapshot_registry` is assigned an eligibility state based on its acquisition status, validation status, and URL parameters:

| Classification | Definition | Pre-requisites | Permitted Comparisons |
| :--- | :--- | :--- | :--- |
| `full_snapshot_comparison` | Snapshot is unfiltered, fully acquired, and cryptographically validated. | HTTP 200, Valid JSON, No query filters (`direction=none`, `date=none`, `page=none`). | Can be compared against any other `full_snapshot_comparison` snapshot. |
| `scoped_comparison_only` | Snapshot contains valid records but is restricted by server query parameters (e.g. `direction=arrival`). | HTTP 200, Valid JSON, Query filters present. | Can only be compared against snapshots within the exact same scope (e.g. arrivals vs arrivals). |
| `not_comparable` | Snapshot payload is structurally malformed, incomplete, or corrupted. | JSON parsing failure, missing essential fields. | Excluded from all comparative analytics. |
| `not_acquired` | Capture metadata exists in index, but replay payload has not been downloaded. | HTTP 429, 503, or offline deferral. | Excluded from comparison until acquired. |
| `not_validated` | Payload is downloaded but has not completed formal schema and cryptographic checks. | Pending validation check. | Excluded until validation status is `PASSED`. |

---

## 3. Directional Filtering Restrictions

When a snapshot is retrieved from `damairport.gov.sy/api/flights.php?direction=arrival`:

- **Structural Limitation:** The server payload contains exclusively arrivals ($N_{dep} = 0$).
- **Disallowed Comparison:** 
  Comparing `snap_wayback_20260715120410` (arrivals only) against `snap_wayback_20260709234230` (full manifest of 993 arrivals and 989 departures) as a full snapshot would register 989 removed departures.
- **Enforced Rule:** The comparison engine enforces `scope_compatible: False` and blocks global net difference calculations. If scoped comparison is enabled, baseline departures are masked prior to diffing.

---

## 4. Date Filtering Restrictions

When a snapshot is retrieved from `damairport.gov.sy/api/flights.php?date=2026-07-20`:

- **Structural Limitation:** The payload contains only records for a single calendar date.
- **Disallowed Comparison:** 
  A single-date snapshot cannot be used to compute 67-day continuity or schedule drift outside of `2026-07-20`.
- **Enforced Rule:** Diffing must be restricted to records where `original_date == '2026-07-20'`. Records outside that date in the baseline are marked `outside_comparison_temporal_scope`, not `removed_display_record`.

---

## 5. Current System Comparison State

Because exactly one snapshot (`snap_wayback_20260709234230`) is physically acquired and validated in the system today:

1. **Total Validated Snapshots:** 1
2. **Total Eligible Comparison Pairs:** 0
3. **Total Cross-Snapshot Comparisons Performed:** 0
4. **Endpoint Status:** `/api/historical-archive/comparisons` reports:
   ```json
   {
     "status": "no_additional_snapshot_available_for_comparison",
     "total_comparisons": 0,
     "comparisons": []
   }
   ```
5. **No Synthetic Comparisons:** The engine strictly refuses to generate mock or speculative comparison rows.

---

## 6. Audit Conclusion

The comparison eligibility matrix establishes unambiguous boundaries for historical change analysis. By categorizing snapshots by acquisition state and query scope, Version 2.16.1 ensures that future snapshot acquisitions cannot produce false schedule attrition or erroneous cancellation metrics.
