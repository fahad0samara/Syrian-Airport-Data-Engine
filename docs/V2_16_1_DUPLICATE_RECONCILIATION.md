# V2.16.1 — Duplicate Candidate Reconciliation
## Empirical Investigation of Flight Designators, Slot Collisions & Prefix Variations

**Syrian Airport Data Engine — Version 2.16.1**  
**Audit Date:** 2026-10-11  
**Report Reference:** [`reports/v2_16_1_duplicate_candidates.csv`](../reports/v2_16_1_duplicate_candidates.csv)  
**Target Snapshot:** `wayback_damairport_fids_20260709234230.json` (1,982 records)

---

## 1. Executive Summary

This audit performs a forensic examination of flight number duplicate claims in the Damascus International Airport July 9, 2026 FIDS snapshot.

Two prominent claims were evaluated:
1. **The alleged `RB272` vs. `RB2722` duplicate:** Comprehensive inspection confirms that **`RB2722` does not exist anywhere in the official July 9 snapshot**. Furthermore, flight numbers with differing numeric digits represent distinct scheduled services, not prefix variants.
2. **The `G9 376` vs. `376` collision:** A genuine slot collision and probable prefix-omission duplicate exists on **2026-07-08 at 13:55** (Air Arabia, DAM $\rightarrow$ SHJ), where two records coexist with identical slots, routes, and core numeric digits. Both records are preserved unaltered in staging.

---

## 2. Investigation Case 1: The `RB 272` vs. `RB 2722` Claim

### 2.1. Empirical Search in July 9 Snapshot
An automated string and regex search across all 1,982 records in `data/raw/snapshots/wayback_damairport_fids_20260709234230.json` and `data/archived_fids_staging.db` yielded:

- Occurrences of `RB2722` or `RB 2722`: **0**
- Occurrences of `RB272` or `RB 272`: **2**
  - Record 1: `2026-07-06 17:00` | DAM $\rightarrow$ AMS | Syrian Air | UUID `406c1fe8-251f-4d92-bb8f-0158ad46c3ef`
  - Record 2: `2026-07-09 17:00` | DAM $\rightarrow$ AMS | Syrian Air | UUID `32f7a957-c466-411a-a53e-5bc314aeb1f6`

### 2.2. Domain Analysis: 3-Digit vs. 4-Digit Flight Numbers
In standard commercial aviation practice:
- Flight `RB 272` and Flight `RB 2722` are fundamentally different flight numbers.
- A 4-digit flight number (`2722`) typically designates an extra section, operational ferry, charter segment, or code-share feeder, whereas `272` is a mainline scheduled flight.
- **Audit Finding:** The assertion in earlier narrative documents that `RB 2722` was a duplicate of `RB 272` was a narrative error. Even if both were present, they could not be merged as a prefix-variant duplicate because their numeric suffixes differ.

---

## 3. Investigation Case 2: The `G9 376` vs. `376` Slot Collision

### 3.1. Verified Empirical Discovery
On `2026-07-08` at `13:55`, two records appear in the snapshot:

| Field | Record A | Record B |
| :--- | :--- | :--- |
| **Source UUID** | `e5ada70d-5245-46d4-b043-bf469c1d104f` | `2d2a0935-da5e-42c4-ad15-e10b4e2291ee` |
| **Flight Number** | `G9 376` (stored normalized as `G9376`) | `376` |
| **Date / Time** | `2026-07-08 13:55` | `2026-07-08 13:55` |
| **Direction** | `departure` | `departure` |
| **Origin $\rightarrow$ Destination** | DAM $\rightarrow$ SHJ | DAM $\rightarrow$ SHJ |
| **Displayed Airline** | `Air Arabia` | `Air Arabia` |
| **Aircraft** | `A320` | `A320` |
| **Displayed Status** | `scheduled` | `scheduled` |

### 3.2. Causal Evaluation
- Both records share identical scheduling parameters: slot (13:55), route (DAM-SHJ), airline (Air Arabia, IATA code `G9`), and aircraft (A320).
- Record A includes the 2-character IATA carrier prefix `G9`.
- Record B omits the prefix, displaying only the numeric sequence `376`.
- **Classification:** `possible_prefix_variant_duplicate`
- **Handling Policy:** In accordance with audit rules, **both records are retained in staging and historical databases**. They are flagged for transparency but NOT collapsed, ensuring zero data loss and 100% cryptographic trace back to source bytes.

---

## 4. Protection of Legitimate Operational Distinctions

To prevent false-positive duplicate flagging, the comparison engine enforces three strict isolation checks:

1. **Different-Date Protection:**
   Same flight number on different dates (e.g. `RB 272` on July 6 vs July 9) represents standard recurring weekly/daily services. They are never flagged as duplicate candidates.
2. **Different-Route Protection:**
   Flights operating with the same number but serving different destinations (e.g. multi-sector or circular routings) are preserved as distinct movements.
3. **Alphanumeric Carrier Prefix Normalization:**
   The comparison engine uses regex `re.sub(r'^[A-Za-z][A-Za-z0-9]?\s*|^[0-9][A-Za-z]\s*', '', flight_num.strip())` to isolate the numeric flight core when detecting prefix omissions, preventing false matches between distinct numbers like `272` and `2722`.

---

## 5. Audit Conclusion

The only confirmed prefix-variant duplicate candidate in the July 9 baseline snapshot is `G9 376` vs `376` on 2026-07-08. `RB 2722` is non-existent. Both records of the `376` collision remain preserved, and the comparison rules prevent erroneous merges.
