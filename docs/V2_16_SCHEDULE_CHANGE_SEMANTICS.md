# Syrian Airport Data Engine — Version 2.16
# Cross-Snapshot Comparison & Schedule Change Semantics

## 1. Executive Summary

When multiple historical FIDS snapshots are retrieved across time, comparing them reveals how airport display boards evolved.

However, airport FIDS boards possess distinct operational characteristics that differ fundamentally from airline booking engines or radar feeds:
- Flight boards display rolling operational windows (e.g., today $\pm 3$ days or upcoming 60 days).
- A flight record disappearing from a later snapshot does **not** prove the flight was cancelled.
- A scheduled time change on a display board reflects timetable adjustments or administrative rescheduling, not physical aircraft takeoff delays.

This document defines the 10 standard comparison categories implemented in [`src/archived_fids_snapshot_comparison.py`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/src/archived_fids_snapshot_comparison.py).

---

## 2. The 10 Comparative Categories

| Category Code | Human-Readable Title | Definition & Operational Interpretation | Review Status |
| :--- | :--- | :--- | :--- |
| `exact_same_digest` | **Exact Same Digest** | The two snapshots possess identical SHA-1 content digests; represents an identical archival capture. | `identical_snapshot` |
| `same_uuid_identical` | **Identical Record** | Same source UUID and identical normalized fields (`flight_number`, `date`, `time`, `direction`, `route`, `airline`, `status`). | `verified_concordant` |
| `same_uuid_modified` | **Modified Record** | Same source UUID persists, but one or more attributes (e.g., status, gate) were altered. | `requires_manual_review` |
| `new_source_uuid` | **New Record** | A UUID appears in the comparison snapshot that was not present in the baseline. Represents added timetable capacity. | `new_schedule_entry` |
| `missing_source_uuid` | **Missing Record** | A baseline UUID does not appear in the comparison snapshot because the date falls outside the comparison window. | `outside_comparison_coverage` |
| `same_flight_and_slot` | **Re-indexed Slot** | Identical flight number, date, time, and route re-indexed under a newly generated UUID. | `uuid_rotation_or_reissued` |
| `prefix_variant_duplicate` | **Prefix-Variant Pair** | Same schedule slot matching an existing entry where carrier IATA code is omitted or duplicated (e.g., `G9 376` vs `376`). | `requires_manual_review` |
| `rescheduled_service` | **Rescheduled Service** | A recurring flight number appears at a revised time slot on the same date. | `schedule_adjustment` |
| `removed_display_record` | **Omitted Display Record** | A flight scheduled within the comparison's active calendar range is omitted from the board. **Does not prove physical flight cancellation.** | `no_longer_listed_on_board` |
| `ambiguous_change` | **Ambiguous Change** | Multiple fields (e.g., flight number, time, and route) altered concurrently under one UUID; requires analyst adjudication. | `requires_manual_review` |

---

## 3. Strict Semantic Guardrails

1. **No Inferred Cancellations**:
   Unless the source API explicitly provides `status: "cancelled"`, an omitted flight must NEVER be labeled as cancelled. The standard label is `no_longer_listed_on_board`.
2. **No Overwriting**:
   Snapshot comparisons are strictly additive. Record observations in snapshot A are never overwritten or deleted by snapshot B. Both observations are preserved in `archived_snapshot_records` and linked through `snapshot_comparison_results`.
3. **Traceability**:
   Every comparison record includes:
   - `baseline_snapshot_id`
   - `comparison_snapshot_id`
   - `source_uuid`
   - `comparison_category`
   - `changed_fields`
   - `review_status`
   - `details`
