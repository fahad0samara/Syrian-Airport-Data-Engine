# Syrian Airport Data Engine — Version 2.9.3
# Period Semantics & Evidence Consistency Audit Report

**Document Identifier**: `docs/V2_9_3_PERIOD_AND_SEMANTICS_CORRECTIONS.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Timezone**: `Asia/Damascus` (UTC+3)  
**Standard**: Strict Epistemic Honesty, Temporal Precision & Methodological Traceability  
**Status**: APPROVED AUDIT DELIVERABLE  

---

## 1. Executive Summary & Purpose

This document records the forensic review and epistemic corrections applied to the Version 2.9.2 evidence register for Damascus International Airport (`DAM` / `OSDI`). 

The Version 2.9.3 audit resolves five specific methodological ambiguities identified in previous iterations:
1. **Critical Period Correction for 2025**: Reclassifying derived figures from "H2 2025" to `annual_minus_reported_period_remainder` due to non-standard semi-annual reporting dates.
2. **Flight Category Terminology Correction**: Reclassifying the H1 2025 figure from "commercial flights" to `total_reported_flights` based on explicit source disaggregation.
3. **Airport FIDS API Classification & Date Overlap**: Providing an empirical cross-tabulation of date classifications versus display statuses across all 1,393 records from `damairport.gov.sy/api/flights.php`.
4. **ADS-B Coverage & Terrain Shadowing Wording**: Retracting unverified assumptions regarding mountain terrain obstruction and replacing them with empirical observation bounds.
5. **Geographic Scope Precision**: Establishing strict qualified scope labels (`reported_as_DAM_pending_primary_source_verification`) for claims whose sovereign primary URLs remain unverified.

This is a **documentation and evidence audit only**. No modifications have been made to the production database (`data/damascus_airport.db`), which remains cryptographically intact.

---

## 2. Correction 1: Critical H1/H2 Period Semantics & Remainder Decomposition

### 2.1 The Problem
In Version 2.9 and Version 2.9.1, the semi-annual figures were colloquially referred to as "H1 2025" and the subtraction remainder ($12,476 - 1,870 = 10,606$ flights; $1,434,998 - 353,282 = 1,081,716$ passengers) was labeled as "H2 2025".

However, documentary inspection of the official SCAA semi-annual press bulletin reveals that its reporting period is **January 7, 2025 through July 7, 2025** (182 calendar days), commemorating the six-month anniversary of the commercial reopening on January 7, 2025. It does **not** cover calendar H1 (January 1 through June 30, 2025; 181 days).

### 2.2 Mathematical & Calendar Decomposition
The annual reported envelope covers the complete calendar year:
$$\text{Annual Window} = [\text{2025-01-01}, \text{2025-12-31}] \quad (365 \text{ calendar days})$$

The SCAA reported period bulletin covers:
$$\text{Reported Period Window} = [\text{2025-01-07}, \text{2025-07-07}] \quad (182 \text{ calendar days})$$

Subtracting the reported period from the annual total leaves a two-part disjoint temporal remainder:
$$\text{Remainder Window} = [\text{2025-01-01}, \text{2025-01-06}] \cup [\text{2025-07-08}, \text{2025-12-31}]$$
$$\text{Remainder Days} = 6 \text{ days} + 177 \text{ days} = 183 \text{ calendar days}$$

| Window Segment | Date Range | Calendar Days | Reported / Derived Flights | Reported / Derived Passengers | Semantic Classification |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Pre-Resumption Window** | 2025-01-01 to 2025-01-06 | 6 days | Part of Remainder | Part of Remainder | Commercial closure; military/diplomatic ops unverified |
| **SCAA Reported Period** | 2025-01-07 to 2025-07-07 | 182 days | 1,870 flights | 353,282 pax | `total_reported_flights` (Documented semi-annual bulletin) |
| **Post-Bulletin Window** | 2025-07-08 to 2025-12-31 | 177 days | Part of Remainder | Part of Remainder | High-intensity operational expansion |
| **Complete Remainder** | **Jan 1–6 & Jul 8–Dec 31** | **183 days** | **10,606 flights** | **1,081,716 pax** | `annual_minus_reported_period_remainder` |
| **Full Calendar Year** | **2025-01-01 to 2025-12-31** | **365 days** | **12,476 flights** | **1,434,998 pax** | `2025_annual` (SCAA quoted annual envelope) |

### 2.3 Epistemic Enforcement Rules
1. **Mandatory Naming**: The remainder figures ($10,606$ flights and $1,081,716$ passengers) must be labeled `annual_minus_reported_period_remainder` in all tables, JSON objects, and documentation.
2. **Explicit Date Disclosures**: Every mention of this remainder must state that it encompasses **both 2025-01-01 to 2025-01-06 and 2025-07-08 to 2025-12-31**.
3. **Prohibition of "H2 2025"**: Neither remainder may be referred to as "H2 2025" or "verified H2" unless an independent primary source verifies that the missing 6 January days had zero movements or provides a dedicated July 1 to December 31 official total.

---

## 3. Correction 2: H1 Flight Category Terminology

### 2.1 The Problem
In Version 2.9, the 1,870 flights reported for the first six months were described generically as "commercial flights".

### 2.2 Textual Source Forensic Inspection
The authentic Arabic text of the SCAA semi-annual press announcement states:
> «سيّر مطار دمشق الدولي 1870 رحلة جوية خلال الفترة من 7 كانون الثاني وحتى 7 تموز 2025، تضمنت 1619 رحلة ركاب، و159 رحلة وفود رسمية ودبلوماسية، و66 رحلة حج، و26 رحلة إغاثية، وعملت عبره 12 شركة طيران.»

### 2.3 Disaggregated Category Breakdown

| Flight Category | Arabic Original | Flight Count | Share of Total | Semantic Interpretation |
| :--- | :--- | :---: | :---: | :--- |
| **Commercial Passenger Flights** | رحلات ركاب | **1,619** | 86.58% | Scheduled and charter revenue passenger flights |
| **Official Delegations** | رحلات وفود رسمية ودبلوماسية | **159** | 8.50% | Diplomatic, VIP, and sovereign state missions |
| **Seasonal Hajj Pilgrimage** | رحلات حج | **66** | 3.53% | Dedicated pilgrimage flights to/from Saudi Arabia |
| **Humanitarian & Relief** | رحلات إغاثية | **26** | 1.39% | Aid, cargo, and humanitarian emergency transport |
| **Total Reported Flights** | **إجمالي الرحلات المسيرة** | **1,870** | **100.00%** | **Exact sum: $1,619 + 159 + 66 + 26 = 1,870$** |

### 2.4 Epistemic Enforcement Rules
- The metric must be designated `total_reported_flights`.
- It must **not** be termed purely `commercial_flights` because 251 flights (13.42%) were non-commercial (state delegations, humanitarian relief, and special charter operations).

---

## 4. Correction 3: Airport FIDS API Classification & Date Overlap

### 4.1 Live Inspection of `https://damairport.gov.sy/api/flights.php`
On snapshot date `2026-10-11`, a live query of the official Damascus International Airport flight API returned **1,393 total flight records**.

### 4.2 Date Overlap & Status Cross-Tabulation
Every flight entry was audited for date relative to the snapshot timestamp (`2026-10-11`) and cross-tabulated against the portal's `status` field:

| Temporal Classification | Temporal Range | Total Records | `scheduled` | `cancelled` | `new-time` | `on-time` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Past Records (< 2026-10-11)** | 2026-10-01 to 2026-10-10 | **558** | 553 (99.10%) | 2 (0.36%) | 2 (0.36%) | 1 (0.18%) |
| **Today Records (= 2026-10-11)** | 2026-10-11 | **61** | 57 (93.44%) | 4 (6.56%) | 0 (0.00%) | 0 (0.00%) |
| **Future Records (> 2026-10-11)** | 2026-10-12 to 2026-10-31 | **774** | 774 (100.0%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) |
| **Total API Records** | **2026-10-01 to 2026-10-31** | **1,393** | **1,384 (99.35%)** | **6 (0.43%)** | **2 (0.14%)** | **1 (0.07%)** |

### 4.3 Operational Semantics Analysis: What Past Records Represent
- **553 out of 558 past records (99.10%)** retain the display status `scheduled`.
- Only 1 record carries status `on-time`, 2 carry `new-time`, and 2 carry `cancelled`.
- **Definitive Finding**: A past date on this endpoint does **not** represent a completed physical flight. It represents a scheduled timetable slot whose published flight date has passed without the website administrators updating the flight's terminal state.
- **Data Engine Invariant**: These 1,393 records represent a **Flight Information Display System (FIDS) timetable board**, not radar transponder fixes, runway sensor logs, or executed flight telemetry. Past records are ingested with status `commercial_schedule_only`, and future records with status `future_schedule`.

---

## 5. Correction 4: ADS-B Coverage & Terrain Shadowing Wording

### 5.1 The Problem
In earlier research notes, speculative assertions were made claiming that *"Anti-Lebanon mountain range terrain definitively eliminates ADS-B reception below FL150"*, and that *"all free historical flight datasets are unavailable"*.

### 5.2 Forensic Revision & Empirical Grounding
Without empirical radio-frequency line-of-sight analysis and feeder horizon measurements, attributing the lack of ground observations solely to mountain shielding is an unverified assumption.

### 5.3 Mandated Replacement Wording
1. **Low-Altitude Telemetry Wording**:
   > *"No low-altitude or near-airport observations were captured during the tested collection windows. The cause remains undetermined (could be lack of feeders, terrain obstruction, transmitter silencing, or API filtering)."*
2. **Historical Data Availability Wording**:
   > *"No suitable historical flight-level dataset has been successfully acquired from the free sources tested so far."*

These corrections replace speculative physical explanations with strictly bounded empirical observations.

---

## 6. Correction 5: Geographic Scope Precision

### 6.1 Strict Scope Taxonomy

| Scope Label | Strict Definition | Applicable Datasets |
| :--- | :--- | :--- |
| **`DAM`** | Claim source text explicitly and specifically restricts scope to Damascus International Airport (`OSDI`). | SCAA H1 2025 bulletin; official airport FIDS API (`damairport.gov.sy`). |
| **`SYRIA_NATIONAL`** | Sovereign national reporting aggregating all Syrian civil aviation without airport-level breakdown. | Central Bureau of Statistics (CBS) Annual Statistical Abstracts. |
| **`OSTT_FIR`** | Airspace overflight navigation telemetry crossing Damascus Flight Information Region. | SCAA Overflight Bulletins (19,951 in Sep 2026; 2,523 in Apr 2026). |
| **`DAM_ALP_LTK`** | Multi-airport commercial gateway composite aggregate across Damascus, Aleppo, and Latakia. | World Bank Syria Economic Monitor (SEM) dataset (578 rows). |
| **`reported_as_DAM_pending_primary_source_verification`** | Claim is reported in secondary media citing SCAA for Damascus Airport, but direct canonical primary URL or signed PDF remains unverified. | 2025 annual figures (12,476 flights, 1.43M pax); 2026 monthly figures (Sep, Jul, May, Apr); derived remainders. |

### 6.2 Application across the Evidence Register
All 27 claims previously classified as `unverified_source_url` and the 2 derived remainder claims have had their airport scope updated to `reported_as_DAM_pending_primary_source_verification`. This prevents conflating media assertions with verified primary aerodrome data.

---

## 7. Machine-Readable Register Consistency Audit

The machine-readable evidence register files (`reports/v2_9_2_evidence_register.csv` and `reports/v2_9_2_evidence_register.json`) have been regenerated to reflect all V2.9.3 corrections:

```text
================================================================================
EVIDENCE REGISTER STATUS AUDIT (48 ATOMIC CLAIMS)
================================================================================
- Total Claims Registered : 48
- unverified_source_url    : 27 claims (56.25%) -> Scope: reported_as_DAM_pending_primary_source_verification / OSTT_FIR
- verified_primary         :  9 claims (18.75%) -> Scope: DAM (API), DAM_ALP_LTK (SEM)
- verified_secondary       :  8 claims (16.67%) -> Scope: DAM (H1 Bulletin & Transition Dates)
- partially_verified       :  2 claims  (4.17%) -> Scope: reported_as_DAM_pending_primary_source_verification (Remainders)
- contradicted             :  2 claims  (4.17%) -> Rejected methodologies (1393 active ops, 75% SEM split)
- unverified               :  0 claims  (0.00%)
================================================================================
```

---

## 8. Database Integrity & Read-Only Verification

In strict accordance with project safety rules, the production database was kept in read-only mode throughout this audit:

- **Database Path**: `data/damascus_airport.db`
- **Cryptographic Hash (SHA-256)**:  
  `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`
- **Bit-for-Bit Hash Check**: **MATCH CONFIRMED** (Identical to baseline).
- **Core Table Row Counts**:
  - `flight_events`: 1,563 rows
  - `event_evidence`: 1,781 rows
  - `raw_source_records`: 1,607 rows
  - `airports`: 6 rows
  - `historical_daily_movements_2024`: 578 rows
  - `daily_airport_movements`: 40 rows
  - `coverage_audit_log`: 6 rows
  - `reconciliation_audit_log`: 4 rows
  - `evidence_ledger_audit`: 1 row
- **Code Regression Tests**: 141 / 141 passing (100%).  
  *(Note: Code-test execution confirms schema and pipeline invariants; it does not constitute proof of real-world historical flight occurrences).*

---

## 9. Conclusion & Next Steps

Version 2.9.3 establishes full consistency between documentary reality, mathematical remainders, and evidence taxonomy. 

### Key Epistemic Principles In Effect:
1. Mathematical remainders are explicitly defined as `annual_minus_reported_period_remainder` covering Jan 1–6 and Jul 8–Dec 31.
2. The H1 total of 1,870 is recognized as `total_reported_flights` across four categories.
3. Official FIDS API past records are proven to be scheduled slots rather than executed operations.
4. ADS-B limitations are framed empirically without speculative physical assertions.
5. All unverified primary claims are qualified as `reported_as_DAM_pending_primary_source_verification`.
