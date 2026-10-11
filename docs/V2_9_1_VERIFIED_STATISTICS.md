# Syrian Airport Data Engine — Version 2.9.1
# Verified Historical Aviation Statistics Dossier (2024–2026)

**Document Identifier**: `docs/V2_9_1_VERIFIED_STATISTICS.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Standard**: Independent Mathematical Verification & Strict Provenance Traceability  
**Status**: APPROVED VERIFIED STATISTICS  

---

## 1. Executive Summary & Verification Protocol

This document compiles the audited, mathematically verified historical statistics for Damascus International Airport across 2024, 2025, and 2026. Every statistic included in this dossier has been:
1. Located in an authenticated sovereign dispatch or primary airport feed.
2. Verified specifically for aerodrome scope (Damascus Airport vs Syrian national aggregates).
3. Verified for movement semantics (actual executed operations vs scheduled timetable intentions).
4. Subjected to independent arithmetic sum and percentage recalculations.

---

## 2. Authenticated Calendar Year 2025 Statistics

The civil aviation operational benchmarks for calendar year 2025 originate from the **General Authority of Civil Aviation and Air Transport** (الهيئة العامة للطيران المدني والنقل الجوي) and official announcements published via the Syrian Arab News Agency (SANA).

### 2.1 Full-Year Operational Benchmarks (2025)

| Metric Description | Official Quoted Value | Independent Sum Recalculation | Percentage of Total | Provenance Status |
| :--- | :---: | :---: | :---: | :--- |
| **Total Commercial Aircraft Flights** | **12,476** | N/A (Reported primary integer) | 100.0% | `verified_primary` |
| **Total Passenger Volume** | **1,434,998** | $715,392 + 719,606 = \mathbf{1,434,998}$ | 100.0% | `verified_primary` |
| **Arriving Passengers** | **715,392** | Independently quoted | 49.853% | `verified_primary` |
| **Departing Passengers** | **719,606** | Independently quoted | 50.147% | `verified_primary` |
| **Average Daily Commercial Flights** | **34.18 flights/day** | $12,476 / 365\text{ days} = 34.1808$ | N/A | Mathematically verified |
| **Average Passengers per Flight** | **115.02 pax/flight** | $1,434,998 / 12,476 = 115.0207$ | N/A | Mathematically verified |

---

### 2.2 Semi-Annual Breakdown & Forensic Disambiguation (H1 vs H2 2025)

In Version 2.9, both H1 and H2 were presented as independent official reports. Forensic auditing clarifies that **H1 was an official primary semi-annual bulletin**, whereas **H2 was derived by arithmetic subtraction**:

| Metric | Official H1 2025 (Jan 7 – Jul 7) | Derived H2 2025 (Jul 8 – Dec 31) | Full Year 2025 Total | Provenance Disambiguation |
| :--- | :---: | :---: | :---: | :--- |
| **Commercial Flights** | **1,870** | **10,606** | **12,476** | H1 is `verified_primary`; H2 is `partially_verified` (derived remainder: $12,476 - 1,870$). |
| **Passenger Volume** | **353,282** | **1,081,716** | **1,434,998** | H1 is `verified_primary`; H2 is `partially_verified` (derived remainder: $1,434,998 - 353,282$). |
| **Arriving Passengers** | **178,728** | **536,664** | **715,392** | H1 is `verified_primary`; H2 is derived: $715,392 - 178,728$. |
| **Departing Passengers** | **174,554** | **545,052** | **719,606** | H1 is `verified_primary`; H2 is derived: $719,606 - 174,554$. |
| **Operating Days** | 182 days | 177 days *(Excl. Jan 1–6)* | 359 active days | Airport reopened Jan 7, 2025. |
| **Average Daily Flights** | **10.27 flights/day** | **59.92 flights/day** | **34.75 flights/day** | Validates the massive +483% operational expansion in H2. |

#### Authenticated Flight Category Breakdown for H1 2025:
The SCAA semi-annual bulletin published an exact disaggregation of the 1,870 H1 flights:
- Commercial Passenger Flights: **1,619 flights** (86.58%)
- Official State & Diplomatic Delegations: **159 flights** (8.50%)
- Seasonal Hajj Pilgrimage Flights: **66 flights** (3.53%)
- Humanitarian & Relief Operations: **26 flights** (1.39%)
- **Sum Verification**: $1,619 + 159 + 66 + 26 = \mathbf{1,870}$ flights (Exact mathematical match).
- Active Operating Airlines: **12 airlines**.

---

## 3. Authenticated Calendar Year 2026 Monthly Statistics

The Syrian Civil Aviation Authority publishes monthly operational summaries via SANA. Every figure has been forensically cross-checked:

| Operational Metric | April 2026 *(Apr 8–30)* | May 2026 *(Full Month)* | July 2026 *(Full Month)* | September 2026 *(Full Month)* |
| :--- | :---: | :---: | :---: | :---: |
| **Commercial Flights Executed** | **492** | **1,532** | **2,088** | **2,022** |
| *(Correction Note)* | *(V2.9 guessed ~350–400)* | *(Confirmed)* | *(Confirmed)* | *(Confirmed)* |
| **Total Passenger Volume** | **34,347** | **148,305** | **243,260** | **229,693** |
| *(Correction Note)* | *(V2.9 quoted >34,000)* | *(Confirmed)* | *(Confirmed)* | *(Confirmed)* |
| **Arriving Passengers** | **18,385** (53.53%) | **83,357** (56.21%) | **147,318** (60.56%) | **98,693** (42.97%) |
| **Departing Passengers** | **15,962** (46.47%) | **64,948** (43.79%) | **95,942** (39.44%) | **131,000** (57.03%) |
| **Directional Sum Check** | $18,385 + 15,962 = \mathbf{34,347}$ | $83,357 + 64,948 = \mathbf{148,305}$ | $147,318 + 95,942 = \mathbf{243,260}$ | $98,693 + 131,000 = \mathbf{229,693}$ |
| **Operating Commercial Airlines** | **9 airlines** | **13 airlines** | **16 airlines** | **17 airlines** |
| **Airspace Transit Overflights** | **2,523 overflights** | *(Not published in press)* | *(Not published in press)* | **19,951 overflights** |
| **Aerodrome Daily Flight Average** | **21.39 flights/day** | **49.42 flights/day** | **67.35 flights/day** | **67.40 flights/day** |
| **Average Passengers per Flight** | 69.81 pax/flight | 96.80 pax/flight | 116.50 pax/flight | 113.60 pax/flight |
| **Provenance Status** | `verified_primary` | `verified_primary` | `verified_primary` | `verified_primary` |

### Key Analytical Findings:
1. **Separation of Overflights**: In September 2026, SCAA explicitly distinguished between **2,022 runway flights at Damascus Airport** and **19,951 upper-airspace transit overflights**. This validates the engine's strict rejection of overflights as airport operations.
2. **Seasonal Expatriate Dynamics**: July 2026 exhibited high arrival concentration (60.56% arrivals; 147,318 in vs 95,942 out), while September 2026 exhibited post-summer outbound departure concentration (57.03% departures; 131,000 out vs 98,693 in).
3. **Summer Operational Plateau**: Average daily movements stabilized at **~67.4 flights/day** across both July and September 2026.

---

## 4. Forensic Audit of Official DAM Airport Flight API

A live, in-memory inspection of `https://damairport.gov.sy/api/flights.php` was executed:

```json
{
  "total_returned_records": 1393,
  "distinct_flight_numbers": 133,
  "distinct_flight_dates": 31,
  "temporal_range": ["2026-10-01", "2026-10-31"],
  "past_records_before_2026_10_11": 558,
  "today_records_on_2026_10_11": 61,
  "future_records_after_2026_10_11": 774,
  "status_distribution": {
    "scheduled": 1384,
    "cancelled": 6,
    "new-time": 2,
    "on-time": 1
  },
  "direction_distribution": {
    "departure": 695,
    "arrival": 698
  },
  "unique_operating_airlines": 16,
  "exact_duplicate_keys": 0
}
```

### Critical Operational Semantics Correction:
- **V2.9 Flawed Claim**: Version 2.9 reported that all 1,393 flights staged from this endpoint were *"active operational flights"*.
- **V2.9.1 Audit Correction**:
  - **774 flights (55.56%)** are **future scheduled entries** for dates between October 12 and October 31, 2026.
  - **1,384 flights (99.35%)** hold the status `scheduled`, representing timetable intentions rather than physically executed touchdowns/takeoffs.
  - Only **6 flights (0.43%)** are tagged as `cancelled`.
  - Under engine invariants, these records must be ingested into `raw_source_records` and classified as `commercial_schedule_only` until the operational date passes and physical radar or airport status confirms completion.

---

## 5. Official Verification Summary Table

```mermaid
graph TD
    subgraph Sovereign Verified Macro Truth
        A["2025 Annual: 12,476 Flights | 1,434,998 Pax\n(715,392 Arr + 719,606 Dep)\nStatus: verified_primary"]
        B["H1 2025: 1,870 Flights | 353,282 Pax\n(1,619 Pax + 159 Deleg + 66 Hajj + 26 Relief)\nStatus: verified_primary"]
        C["2026 Monthly: Sep (2,022 Fl / 229k Pax) | Jul (2,088 Fl / 243k Pax)\nMay (1,532 Fl / 148k Pax) | Apr (492 Fl / 34k Pax)\nStatus: verified_primary"]
    end

    subgraph Derived Remainder Values
        D["H2 2025 Remainder: 10,606 Flights | 1,081,716 Pax\nStatus: partially_verified (Calculated Remainder)"]
    end

    subgraph Official Flight Board API
        E["damairport.gov.sy/api: 1,393 Records\n558 Past | 61 Today | 774 Future Scheduled\nStatus: verified_primary (Scheduled Semantics)"]
    end

    A --> D
    B --> D
```

This completes the verified statistical baseline for Damascus International Airport.
