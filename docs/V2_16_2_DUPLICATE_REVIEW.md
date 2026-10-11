# V2.16.2 — Duplicate Review & Candidate Classification
## Empirical Verification of Flight Number Collisions, Prefix Omissions & Distinct Service Protection

**Syrian Airport Data Engine — Version 2.16.2**  
**Audit Date:** 2026-10-11  
**Report Reference:** [`reports/v2_16_2_duplicate_audit.csv`](../reports/v2_16_2_duplicate_audit.csv)  
**Dataset Analyzed:** `data/raw/snapshots/wayback_damairport_fids_20260709234230.json` (1,982 records)

---

## 1. Executive Summary

This document details the forensic audit of duplicate flight claims within the July 9, 2026 Damascus Airport FIDS snapshot.

Summary of Findings:
1. **Candidate A (`G9 376` vs. `376`):** Confirmed as an empirical prefix-omission candidate on `2026-07-08` at `13:55`. Classified as **`possible_prefix_variant_duplicate`**. Both records remain preserved unaltered in staging and production databases.
2. **Candidate B (`RB 272` vs. `RB 2722`):** Exhaustive search across all 1,982 records proves that **`RB2722` does not exist**. Furthermore, 3-digit vs. 4-digit flight designators represent distinct commercial services. Classified as **`distinct_services`**.

---

## 2. Forensic Evaluation of Candidate A: `G9 376` vs. `376`

### 2.1. Candidate Record Manifest
On July 8, 2026 at 13:55, two separate objects are present in the source JSON:

| Attribute | Record 1 | Record 2 |
| :--- | :--- | :--- |
| **Source UUID** | `e5ada70d-5245-46d4-b043-bf469c1d104f` | `2d2a0935-da5e-42c4-ad15-e10b4e2291ee` |
| **Original Flight Number** | `G9 376` | `376` |
| **Scheduled Date** | `2026-07-08` | `2026-07-08` |
| **Scheduled Time** | `13:55` | `13:55` |
| **Direction** | `departure` | `departure` |
| **Route** | DAM $\rightarrow$ SHJ | DAM $\rightarrow$ SHJ |
| **Displayed Airline** | `طيران العربية` (Air Arabia) | `طيران العربية` (Air Arabia) |
| **Raw Record Hash** | `29783cf502752ba819e6717db4c72da1...` | `9e878ec67c2c921445a36b07002fac4a...` |
| **Audit Classification** | `possible_prefix_variant_duplicate` | `possible_prefix_variant_duplicate` |

### 2.2. Analytical Evaluation
- **Slot Collision:** Both records share the exact same departure slot (`13:55`), origin (`DAM`), destination (`SHJ`), and carrier (`Air Arabia`).
- **Prefix Discrepancy:** Record 1 includes the standard 2-character IATA airline code `G9`, whereas Record 2 omits it.
- **Handling Policy:** In accordance with strict audit rules, **neither record is deleted or merged**. Collapsing records without independent physical evidence (such as radar transponder ADS-B traces) would violate source-of-truth traceability.

---

## 3. Forensic Evaluation of Candidate B: `RB 272` vs. `RB 2722`

### 3.1. Verification of Existence
An exhaustive regex search (`RB\s*2722`) across all 1,982 records confirms:
- **`RB2722` Count:** **0** (Non-existent in the July 9 snapshot).
- **`RB272` Count:** **2**
  - Record 1: UUID `196ac08d-9c26-43e8-b3e0-add847eb5603` on `2026-07-06` at `17:00` (DAM $\rightarrow$ AMS, Syrian Air).
  - Record 2: UUID `44db8043-2867-4e8d-86b7-918f7675b126` on `2026-07-09` at `17:00` (DAM $\rightarrow$ AMS, Syrian Air).

### 3.2. Domain Semantics
- Flights occurring on different calendar dates (`2026-07-06` and `2026-07-09`) are distinct scheduled operations, not duplicates.
- Flight numbers with differing numeric digits (`272` vs `2722`) represent different flight identities in commercial aviation.

---

## 4. Duplicate Candidate Classification Standard

Version 2.16.2 formalizes four audit classifications:

1. **`confirmed_duplicate`**: Identical UUID, flight number, slot, and route across duplicated records within a single snapshot. (Current count: **0**).
2. **`possible_prefix_variant_duplicate`**: Identical slot, route, and airline on the same date where one record omits the airline prefix. (Current count: **1 pair / 2 records**).
3. **`distinct_services`**: Flights sharing carrier or similar numeric sequences but operating on different dates, different routes, or with different numeric suffixes. (Current count: **1,980 records**).
4. **`ambiguous_requires_manual_review`**: Multi-field anomalies where intent cannot be programmatically resolved. (Current count: **0**).

---

## 5. Audit Conclusion

The only valid duplicate candidate is the `G9 376` vs `376` pair on July 8, 2026. The `RB 2722` claim is definitively dismissed. All 1,982 records remain safely preserved in their authentic, unmerged state.
