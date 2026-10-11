# Syrian Airport Data Engine — Version 2.14.1
# Flight Status Semantics & Sensor Evidence Segregation

## 1. Executive Summary

This audit establishes the rigorous semantic interpretation of flight status values present in the 1,982 archived Damascus International Airport (`DAM` / `OSDI`) FIDS records.

The primary objective is to enforce strict separation between:
1. **`scheduled_status`**: Forward timetable schedule intention.
2. **`displayed_status`**: The text flag presented on terminal flight display monitors.
3. **`actual_movement_evidence`**: Physical radar, ADS-B, or runway sensor touchdown telemetry.

A critical finding of this audit is that the single record bearing the status `"arrived"` represents **exclusively a public display observation** and contains **zero physical movement evidence**. It is strictly prohibited from being promoted to a physical movement.

---

## 2. Three-Dimensional Status Architecture

In previous data processing pipelines, flight status fields often collapsed schedule intention, display flags, and physical execution into a single attribute. Version 2.14.1 establishes strict orthogonal segregation across three dimensions:

```mermaid
flowchart TD
    subgraph Staging_Record_Dimensions["Archived Record Status Dimensions"]
        A["1. Scheduled Status<br/>('scheduled')<br/>Timetable Listing State"]
        B["2. Displayed Status<br/>('scheduled' | 'arrived')<br/>Terminal Board Indicator"]
        C["3. Actual Movement Evidence<br/>(Flag: 0 / False)<br/>Radar / ADS-B Sensor Telemetry"]
    end
    
    B -->|'arrived' flag present| D["Archived Display Observation"]
    C -->|Flag = 0 (No sensor data)| E["Physical Movement Classification Prohibited"]
    D -.-> E
```

### Definitive Attribute Definitions

1. **`scheduled_status`**: Represents the commercial schedule status of the flight in the airport's published timetable. For all 1,982 records, `scheduled_status = 'scheduled'`.
2. **`displayed_status`**: The raw text string served by the API endpoint to drive the public web interface and terminal display screens.
   - `scheduled`: 1,981 records (99.95%)
   - `arrived`: 1 record (0.05%)
3. **`actual_movement_evidence`**: A binary flag indicating whether the record is substantiated by cryptographic, transponder, or radar sensor data proving physical runway contact.
   - For all 1,982 records in this dataset, **`actual_movement_evidence = 0`**.

---

## 3. Forensic Analysis of the Single "arrived" Record

The complete source JSON representation of the single record bearing the status `"arrived"` was audited:

```json
{
  "id": "a3c520d5-a113-4646-bdff-c60c2e8e27b9",
  "flightNumber": "XH  728",
  "airline": "فلاي شام",
  "direction": "arrival",
  "origin": "DXB",
  "originText": "",
  "destination": "DAM",
  "destinationText": "",
  "date": "2026-07-06",
  "time": "00:20",
  "gate": "",
  "aircraft": "",
  "status": "arrived",
  "createdAt": "2026-07-06T00:27:33Z"
}
```

### Forensic Evidentiary Findings

1. **Absence of Sensor Telemetry**: The record contains no actual arrival timestamp (`actual_arr_time` is null/empty). The string `"00:20"` is strictly the scheduled timetable time.
2. **Absence of Airframe Identification**: The `aircraft` field is completely empty (`""`). No aircraft tail registration, serial number, or Mode-S 24-bit ICAO transponder address is provided.
3. **Absence of Operational Gate**: The `gate` assignment is completely empty (`""`).
4. **Creation Timestamp Proximity**: The record `createdAt` timestamp is `2026-07-06T00:27:33Z`. This indicates that approximately 7 minutes after the scheduled arrival time of 00:20 local time (which corresponds to 21:20 UTC on July 5), an automated system process or human website administrator toggled the website display label to `"arrived"`.
5. **No Verification of Actual Landing**: In civil aviation data verification, a display status on a public airport website is vulnerable to automatic scheduled-based state changes (time-elapsed triggers), manual operational overrides, and unrecorded diversions or cancellations.

### Strict Governance Invariant

> **MANDATORY INVARIANT**:
> Record `a3c520d5-a113-4646-bdff-c60c2e8e27b9` is classified as `archived_actual_movement_candidate` within the staging audit layer, but is **categorically prohibited from promotion to `physical_movement`**. It remains an unverified scheduled display observation.

---

## 4. Reconciled Status Distribution

The status distribution of all 1,982 records is summarized below and exported in machine-readable format:

| Original Raw Status | Normalized Status | Record Count | Percentage | Scheduled Status Concept | Displayed Status Concept | Actual Movement Evidence | Physical Movement Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `scheduled` | `scheduled` | 1,981 | 99.95% | `scheduled` | `scheduled` | 0 (None) | **PROHIBITED** (Scheduled service only) |
| `arrived` | `arrived` | 1 | 0.05% | `scheduled` | `arrived` | 0 (None) | **PROHIBITED** (Display flag without sensor proof) |
| **TOTAL** | — | **1,982** | **100.00%** | — | — | — | — |

---

## 5. Machine-Readable Export Reference

This breakdown is documented in [`reports/v2_14_1_status_distribution.csv`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/reports/v2_14_1_status_distribution.csv).
All entries explicitly declare `actual_movement_evidence_flag = 0` and `physical_movement_classification = 'PROHIBITED_UNVERIFIED_SENSOR_EVIDENCE'`.
