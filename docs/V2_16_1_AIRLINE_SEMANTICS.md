# V2.16.1 — Airline Semantics & Brand Change Audit
## Displayed Airline vs. Operating Carrier Distinctions & Semantic Re-classification

**Syrian Airport Data Engine — Version 2.16.1**  
**Audit Date:** 2026-10-11  
**Entity Analyzed:** Airline / Carrier representation in FIDS snapshots  
**Schema Column:** `displayed_airline` (formerly generic `airline`)

---

## 1. Executive Summary

This audit establishes the domain semantics governing airline identification in historical Damascus Airport flight information displays. 

In version 2.16, cross-snapshot modifications in airline fields were labeled generically as `airline_changed`. In aviation data engineering, this creates significant ambiguity: it implies that the operating airline or air operator certificate (AOC) changed. In reality, FIDS boards display marketing brands, commercial charters, wet-lease operators, or ground handling representations. Version 2.16.1 formally standardizes this comparative category to `displayed_airline_changed` (retaining `airline_changed` as a deprecated backward-compatible alias) and audits displayed airline branding fidelity.

---

## 2. Theoretical Grounding: Displayed Brand vs. Operating Carrier

An airport Flight Information Display System (FIDS) is a public passenger-facing interface, not an air traffic control (ATC) flight progress strip or radar track.

### 2.1. The Operational Differences:
- **Displayed Airline (`displayed_airline`):**
  - The textual name or brand rendered on airport television screens and web portals (e.g. "Syrian Air", "Cham Wings", "Fly Cham", "Air Arabia", "Fly Baghdad").
  - Subject to codeshare agreements, wet leases (ACMI), commercial charter marketing, or administrative rebranding.
- **Operating Carrier:**
  - The actual entity operating the aircraft, possessing the AOC, and filing the IFR flight plan with Syrian Civil Aviation Authority (CAA).
- **Audit Rule:**
  Because the FIDS snapshot provides only the passenger display text, the engine must NEVER claim knowledge of the operating carrier beyond the literal display string. To do so would constitute unsupported speculation.

---

## 3. Migration to `displayed_airline_changed`

In `src/archived_fids_snapshot_comparison.py`, the comparative categorization engine was updated:

```python
# Before (V2.16):
comparison_category = "airline_changed"

# After (V2.16.1):
comparison_category = "displayed_airline_changed"
# (Backward compatibility maintained via API deprecation layer)
```

### Affected Systems:
1. **Database Schema:** `archived_snapshot_comparisons.comparison_category` records `displayed_airline_changed`.
2. **REST API:** `/api/historical-archive/comparisons` returns `displayed_airline_changed`.
3. **Frontend Dashboard:** Summary cards and table headers reflect `Displayed Airline / Organization` and `Displayed Airline Changed`.

---

## 4. Preservation of Historical Display Strings

In `archived_fids_staging.db` and the raw July 9 snapshot, the following 12 distinct display strings appear across the 1,982 records:

| Displayed Airline String | Flights | Classification Category |
| :--- | :--- | :--- |
| `Syrian Air` | 768 | Scheduled Commercial Carrier |
| `Cham Wings Airlines` | 422 | Scheduled Commercial Carrier |
| `Air Arabia` | 240 | Scheduled Commercial Carrier |
| `Fly Baghdad` | 134 | Scheduled Commercial Carrier |
| `Fly Cham` | 98 | Commercial Brand / Charter Entity |
| `Mahan Air` | 86 | Scheduled Commercial Carrier |
| `FlyNas` | 64 | Scheduled Commercial Carrier |
| `UR Airlines` | 52 | Scheduled Commercial Carrier |
| `Iraqi Airways` | 48 | Scheduled Commercial Carrier |
| `Caspian Airlines` | 32 | Scheduled Commercial Carrier |
| `Kuwait Airways` | 24 | Scheduled Commercial Carrier |
| `Kish Air` | 14 | Scheduled Commercial Carrier |

Each entity is tracked exactly as recorded in the raw JSON payload, preventing artificial consolidation (e.g., merging `Cham Wings` and `Fly Cham` without explicit source evidence).

---

## 5. Audit Conclusion

The migration to `displayed_airline_changed` clarifies the precise epistemic boundaries of the data engine. The engine records and compares what was displayed to passengers, without conflating display text with verified operating carrier identity.
