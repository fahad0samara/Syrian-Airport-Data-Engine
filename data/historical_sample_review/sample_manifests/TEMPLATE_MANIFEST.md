# Historical Sample Acquisition Manifest Template

**Manifest Identifier**: `MNF-YYYYMMDD-<PROVIDER>-OSDI`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Audit Standard**: Syrian Airport Data Engine V2.5 Isolation & Provenance Protocol  

---

## 1. Provider & Acquisition Metadata

- **Provider Name**: `[ opensky | flightradar24 | flightaware | official_statistics | other ]`
- **Original Filename**: `[ e.g., osdi_historical_sample_2024.csv ]`
- **Acquisition Date**: `YYYY-MM-DD`
- **Acquisition Channel**: `[ e.g., Authorized Sales Email | Trino Query Export | Official Government Gazette ]`
- **Requested Historical Dates**:
  - `2024-01-15`
  - `2024-03-15`
  - `2024-05-15`
  - `2024-07-15`
  - `2024-09-15`
  - `2024-10-10`
  - `2025-06-15`
  - `2026-06-15`
- **Airport Identifiers Confirmed**: ICAO `OSDI`, IATA `DAM`

---

## 2. Cryptographic Integrity & File Attributes

- **Local Storage Path**: `data/historical_sample_review/<provider>/<original_filename>`
- **File Size (Bytes)**: `0`
- **Raw File SHA-256**: `[ SHA-256 hex string ]`
- **Format**: `[ CSV | JSON | Parquet | PDF ]`

---

## 3. Licensing, Retention & Export Boundaries

- **License / Contract Reference**: `[ e.g., Flightradar24 Commercial Evaluation Terms ]`
- **Usage Restrictions**: `[ e.g., Strictly internal evaluation; no commercial redistribution ]`
- **Retention Permissions**: `[ permanent_local_db_allowed | temporary_eval_cache_only | mandatory_purge_required ]`
- **Export Permissions**: `[ permitted_public | permitted_academic_derivative_only | prohibited ]`

---

## 4. Operational Status & Assessment Summary

- **Sample Status**: `[ pending_outreach | awaiting_provider_response | sample_received | sample_declined ]`
- **Validation Status**: `[ unvalidated | partially_validated | validated_accepted | validated_rejected ]`
- **Total Records Ingested**: `0`
- **Movement Direction Breakdown**:
  - Arrivals: `0`
  - Departures: `0`
- **Classification Distribution**:
  - `confirmed_physical`: `0`
  - `corroborated_physical`: `0`
  - `probable_movement`: `0`
  - `unverified_movement`: `0`
  - `scheduled_service`: `0`
- **Reviewer Notes & Action Items**:
  - `[ Notes ]`
