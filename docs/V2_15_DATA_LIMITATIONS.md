# Syrian Airport Data Engine — Version 2.15
# Archived FIDS Data Limitations & Evidentiary Boundaries

## 1. Executive Summary

This document establishes the official evidentiary boundaries, data limitations, and interpretation rules for the archived Damascus International Airport (`DAM` / `OSDI`) FIDS dataset analyzed in Version 2.15.

Analysts, engineers, and downstream consumers must strictly adhere to these boundaries to prevent false empirical claims.

---

## 2. Fundamental Boundary: Scheduled Services vs. Physical Movements

### The 0 Physical Movement Evidence Invariant
$$\text{physical\_movement\_evidence\_count} = 0$$

All 1,982 records in this dataset originate from an archived HTTP API endpoint (`damairport.gov.sy/api/flights.php`) that drove public passenger departure and arrival screens.

| Data Characteristic | Archived FIDS Snapshot | Verified Production Movement (`flight_events`) |
| :--- | :--- | :--- |
| **Data Nature** | Forward timetable schedule / display board | Empirically observed physical takeoff/landing |
| **Sensor Telemetry** | **None** (0 ADS-B, 0 radar, 0 Mode-S) | FR24 ADS-B receiver telemetry / radar contact |
| **Actual Runway Contact** | **Unverified** | Confirmed touchdown or takeoff timestamp |
| **Airframe Equipment** | Empty string (`""`) | Specific aircraft registration & ICAO hex code |
| **Operational Gate** | Empty string (`""`) | Verified airport terminal stand/gate |

### Interpretation Rules
1. **Never Promote to Physical Movement**: A scheduled flight in this dataset must never be inserted into production tables as a confirmed physical movement.
2. **Missing Records $\neq$ Zero Physical Operations**: Military flights, government delegations, unscheduled cargo operations, private aviation, and unlisted humanitarian charters do not appear on commercial public FIDS displays. Therefore, a day with 2 scheduled commercial flights does not mean only 2 physical aircraft landed at Damascus International Airport.

---

## 3. Carrier Role Boundary: Displayed Brand vs. Operating Carrier

The `airline` field in the snapshot reflects the **Displayed Airline Brand** shown on terminal monitors.

### Critical Limitations
1. **No Air Operator Certificate (AOC) Identity**: The source feed does not specify which certified legal carrier operated the aircraft.
2. **ACMI Wet-Leases**: Flights displayed under brands like `Dan Air` (`دان أير`) or `Fly Cham` (`فلاي شام`) may be operated via third-party wet-lease agreements.
3. **Codeshare and Subsidiary Masking**: Flights under `طيران العربية` (Air Arabia) encompass rotations bearing both `G9` (Sharjah) and `3L` (Abu Dhabi) prefixes.
4. **Mandatory Policy**: All analytics outputs must use the label **`Displayed Airline Distribution`** and flag `is_operating_carrier_verified = FALSE`. Operating carriers must never be guessed from flight numbers.

---

## 4. Status Boundary: Display Flag vs. Physical Landing

The dataset contains:
- `scheduled`: 1,981 records (99.95%)
- `arrived`: 1 record (0.05%)

### Forensic Truth of the "arrived" Record
- **Flight**: `XH 728`, DXB $\rightarrow$ DAM, scheduled `2026-07-06 00:20`, created `2026-07-06T00:27:33Z`.
- **Finding**: Approximately 7 minutes after scheduled arrival, an automated website script or airport operator updated the web portal display flag to `"arrived"`.
- **Evidentiary Absence**: The payload contains **no actual arrival timestamp**, no ground radar contact, and no airframe registration. In civil aviation data verification, a website text flag does not constitute proof of physical landing. It is classified strictly as an `archived_actual_movement_candidate` and prohibited from physical movement verification.

---

## 5. Duplicate Candidate Boundary: Non-Destructive Preservation

On `2026-07-08` at `13:55` (DAM $\rightarrow$ SHJ, `طيران العربية`):
- `e5ada70d-5245-46d4-b043-bf469c1d104f`: `G9 376` (created July 4)
- `2d2a0935-da5e-42c4-ad15-e10b4e2291ee`: `376` (created July 7)

### Policy
Both records are retained in the database. Deleting or merging records based on algorithmic deduction destroys source auditability. Both records are flagged with:
- Classification: `possible_prefix_variant_duplicate`
- Status: `requires_manual_review`

---

## 6. Temporal Scope & Extrapolation Prohibition

- **Temporal Coverage**: Exactly **67 consecutive days** from `2026-07-05` to `2026-09-09`.
- **Extrapolation Prohibition**: Analysts must **never extrapolate** this 67-day summer schedule to full-year 2026 totals or represent these numbers as Damascus annual airport statistics.
- **Derived UTC Timestamps**: Local times represent `Asia/Damascus` (`UTC+3`). UTC timestamps are mathematically derived by subtracting 3 hours and must always be labeled as derived.
