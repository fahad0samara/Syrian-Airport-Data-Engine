# Syrian Airport Data Engine — Version 2.14.1
# Semantic Duplicate Audit & Candidate Group Evaluation

## 1. Executive Summary

This audit performs a rigorous evaluation of duplicate candidates across the 1,982 archived FIDS records extracted from the Damascus International Airport API snapshot.

Using multi-field grouping across flight numbers, directions, scheduled dates, scheduled times, route pairs (origin/destination), airline brands, and source UUIDs, this investigation classifies all potential collision scenarios into four distinct categories:
1. **Exact Duplicate Source Records**: 0 records.
2. **Prefix-Variant Duplicate Candidates**: Exactly 1 pair (2 records) sharing identical route, time, date, and brand, where one entry omitted the IATA carrier prefix (`G9 376` vs `376`).
3. **Same-Day Multi-Rotation / Shuttle Legs**: 6 pairs (12 records) sharing normalized flight numbers on the same calendar day but representing distinct operational legs (outbound/inbound or distinct flight times).
4. **Recurring Rotations Across Dates**: 1,980 records representing regular daily/weekly commercial scheduled rotations over 67 days.

In strict compliance with audit rules, **zero records were automatically deleted**. All candidate records are preserved unaltered in the staging database.

---

## 2. Multi-Field Duplicate Evaluation Matrix

| Category Tested | Grouping Fields | Candidates Found | Audit Classification | Action Taken |
| :--- | :--- | :--- | :--- | :--- |
| **Exact Payload Duplicates** | Complete raw JSON serialization | 0 | Identical records | None (all 1,982 are distinct) |
| **Composite Key Collisions** | `CleanedFN + Dir + Date + Time` | 0 | Schedule slot collisions | None (composite keys are 100% unique) |
| **Same Slot, Route, & Brand** | `Date + Time + Dir + Origin + Dest + Brand` | **1 pair (2 records)** | `prefix_variant_duplicate_candidate` | Preserved unaltered; flagged in audit ledger |
| **Same Day, Same Normalized FN** | `CleanedFN + Date` | 6 pairs (12 records) | `same_day_multi_rotation_or_shuttle_leg` | Preserved unaltered; verified as distinct flights |
| **Cross-Date Schedule Series** | `CleanedFN + Dir + Time` across dates | 1,980 records | `recurring_daily_schedule_series` | Preserved unaltered; regular commercial timetable |

---

## 3. In-Depth Analysis of the Prefix-Variant Candidate Pair

On `2026-07-08`, an operational anomaly occurred in the airport source system where 48 records were inserted without carrier prefixes. Exactly one of these records created a semantic duplicate candidate with an existing entry:

```json
{
  "Candidate Record A": {
    "source_uuid": "e5ada70d-5245-46d4-b043-bf469c1d104f",
    "flightNumber": "G9 376",
    "airline": "طيران العربية",
    "direction": "departure",
    "origin": "DAM",
    "destination": "SHJ",
    "destinationText": "الشارقة",
    "date": "2026-07-08",
    "time": "13:55",
    "status": "scheduled",
    "createdAt": "2026-07-04T15:45:44Z"
  },
  "Candidate Record B": {
    "source_uuid": "2d2a0935-da5e-42c4-ad15-e10b4e2291ee",
    "flightNumber": "376",
    "airline": "طيران العربية",
    "direction": "departure",
    "origin": "DAM",
    "destination": "SHJ",
    "destinationText": "الشارقة",
    "date": "2026-07-08",
    "time": "13:55",
    "status": "scheduled",
    "createdAt": "2026-07-07T19:00:22Z"
  }
}
```

### Forensic Finding
- **Record A** was published on `2026-07-04` as part of the forward baseline timetable with full IATA flight number `G9 376`.
- **Record B** was uploaded on `2026-07-07` during an evening data batch where the data operator or feed ingest omitted the `G9` prefix, creating record `376`.
- Both records advertise the exact same flight from Damascus to Sharjah at `13:55` local time on `2026-07-08`.
- **Audit Decision**: This represents a high-confidence semantic duplicate in the source system. However, following data preservation principles, Record B is **NOT deleted** from staging. Both records remain in `archived_fids_normalized` and are fully traceable through [`reports/v2_14_1_duplicate_candidates.csv`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/reports/v2_14_1_duplicate_candidates.csv).

---

## 4. Evaluation of Same-Day Normalized Flight Number Pairs

Six distinct instances occur where the same normalized flight number appears twice on the same calendar day:

| Group ID | Flight Number | Airline | Date | Times | Directions | Route Details | Audit Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `DUP_GRP_002` | `728` | Fly Cham | 2026-07-08 | 01:20 & 22:20 | Arr / Arr | DXB $\rightarrow$ DAM | **Distinct rotations** (morning & night arrivals) |
| `DUP_GRP_003` | `RB444` | Syrian Airlines | 2026-07-07 | 04:30 & 22:00 | Arr / Arr | IST $\rightarrow$ DAM | **Distinct rotations** (morning & night arrivals) |
| `DUP_GRP_004` | `RJ436` | Royal Jordanian | 2026-07-05 | 08:40 & 16:15 | Dep / Arr | DAM $\rightarrow$ AMM & AMM $\rightarrow$ DAM | **Outbound & inbound shuttle legs** |
| `DUP_GRP_005` | `UNO501` | United Nations | 2026-07-06 | 11:30 & 13:40 | Dep / Arr | DAM $\rightarrow$ ALP & ALP $\rightarrow$ DAM | **UN Aleppo humanitarian shuttle rotation** |
| `DUP_GRP_006` | `UNO501` | United Nations | 2026-07-09 | 11:30 & 13:30 | Dep / Arr | DAM $\rightarrow$ ALP & ALP $\rightarrow$ DAM | **UN Aleppo humanitarian shuttle rotation** |
| `DUP_GRP_007` | `XH728` | Fly Cham | 2026-07-06 | 00:20 & 21:50 | Arr / Arr | DXB $\rightarrow$ DAM | **Distinct rotations** (00:20 marked arrived; 21:50 scheduled) |

None of these represent data entry duplicates; they are distinct operational flights that happen to share flight numbers due to circular rotation patterns or airline schedule conventions.

---

## 5. Distinction Between Unique Flight Numbers and Record Counts

A frequent point of confusion in timetable audits is why **159 unique raw flight numbers** (or 143 whitespace-cleaned flight numbers) account for **1,982 total records**.

The explanation is commercial recurring flight frequencies:
- Airlines operate commercial services on fixed repeating daily or weekly rotations.
- For example, flight `G9 433` (Air Arabia, Sharjah to Damascus) appears on all 67 calendar days in the snapshot (67 records).
- Flight `TK 848` (Turkish Airlines, Istanbul to Damascus) operates on 63 days (63 records).
- Flight `FZ 1115` (flydubai, Dubai to Damascus) operates on 63 days (63 records).
- Over the 67-day summer schedule window, an average of ~29 flights per day across 159 rotational flight numbers yields exactly 1,982 flight records.

---

## 6. Audit Conclusion

All suspected candidate groups have been categorized, explained, and indexed. Zero records were deleted. The staging database reflects 100% of the raw archive without loss or artificial suppression.
