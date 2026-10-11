# Syrian Airport Data Engine — Version 2.6
# OpenSky Network Historical Research Access Application Package

**Document Identifier**: `docs/V2_6_OPENSKY_RESEARCH_PROPOSAL.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Audit & Preparation Date**: 2026-10-11  
**Status**: COMPLETE DRAFT APPLICATION (Awaiting Personal User Review & Institutional Details)  
**Governance Notice**: PREPARATION ONLY — NOT SUBMITTED  

---

## 1. Applicant & Institutional Information (User Placeholders)

> [!IMPORTANT]
> In accordance with strict anti-hallucination and safety rules, the assistant has **NOT** invented or assumed the applicant's name, institution, employer, or credentials.
> All personal and institutional fields are presented below as explicit placeholders for the user to populate prior to any submission.

| Application Field | Applicant Entry / User Placeholder |
| :--- | :--- |
| **Principal Investigator / Applicant Name** | `[USER_FULL_NAME]` |
| **Academic / Professional Title** | `[USER_TITLE / e.g., Senior Aviation Researcher, PhD Candidate, Faculty Member]` |
| **Primary Institutional Email** | `[USER_INSTITUTIONAL_EMAIL / e.g., name@university.edu or name@institution.org]` |
| **OpenSky Network Account Username** | `[USER_OPENSKY_USERNAME]` |
| **Applicant Institutional Affiliation** | `[USER_INSTITUTION_NAME / e.g., Department of Aerospace Engineering, University of ...]` |
| **Institution Country & Postal Address** | `[USER_INSTITUTION_ADDRESS]` |
| **Project Non-Commercial Declaration** | **Strictly Non-Commercial Academic Research** `[User to Confirm]` |
| **Research Supervisor / Faculty Sponsor** | `[FACULTY_SPONSOR_NAME (if student/graduate researcher) or N/A]` |

---

## 2. Formal Research Project Proposal

### 2.1 Project Title
**"Historical Aircraft Movement Observation and Data Quality Assessment at Damascus International Airport (OSDI)"**

### 2.2 Research Purpose & Context
Damascus International Airport (IATA: DAM, ICAO: OSDI, Aerodrome Reference Point: Lat 33.4150° N, Lon 36.5156° E, Elevation: 2,020 ft MSL) represents a critical civilian aviation gateway in the Levant. However, open academic literature regarding its historical civilian air traffic patterns, operational continuity, and telemetry sensor resilience between 2024 and 2026 is severely limited.

Due to the complex regional geopolitical environment, terrestrial crowdsourced receiver coverage across Syria is known to be sparse compared to Western Europe or North America. Furthermore, high-altitude regional overflights transiting the Damascus Flight Information Region (OSTT FIR) frequently overlap with terminal airspace, creating significant methodological challenges for automated air traffic monitoring.

This research project aims to establish a transparent, scientifically grounded methodology to evaluate ADS-B and Mode-S state-vector availability, assess terminal receiver continuity, evaluate approach and departure kinematics, and formulate uncertainty classifications for conflict-affected civilian aerodromes.

### 2.3 Core Research Questions
1. **Sensor Density & Visibility**: What is the historical availability, message frequency, and continuity of Mode-S state-vector observations captured around Damascus International Airport in the OpenSky Network repository from January 2024 to October 2026?
2. **Terminal Trajectory Discrimination**: To what extent can observed raw state-vector sequences differentiate high-altitude overflights transiting the Syrian FIR from aircraft maneuvering within the Damascus Terminal Maneuvering Area (TMA)?
3. **Runway Movement Qualification**: Can low-altitude kinematic state vectors (deceleration, rate of descent, track alignment with Runways 05R/23L and 05L/23R) reliably qualify candidate approach and departure movements in the absence of continuous ground-level surface radar?
4. **Coverage & Boundary Estimation**: What are the empirical spatial (horizontal radius and minimum barometric altitude) and temporal reception boundaries of OpenSky receivers covering the Damascus basin?
5. **Cross-Evidence Uncertainty Modeling**: How can OpenSky trajectory candidates be systematically cross-evaluated against other legally accessible macro datasets (e.g. official civil aviation NOTAMs, published schedule registries) without conflating unobserved periods with zero airport operations?

### 2.4 Research Scope & Target Aerodrome
- **Primary Aerodrome**: Damascus International Airport (ICAO: `OSDI`, IATA: `DAM`).
- **Aerodrome Reference Point (ARP)**: Lat `33.4150° N`, Lon `36.5156° E`, Elevation `2,020 ft MSL` (`616 m`).
- **Runway Configuration**: Runway 05R/23L (3,600 m × 45 m, bearing ~051° / 231° magnetic) and Runway 05L/23R (3,000 m × 45 m).
- **Geographic Bounding Box**:
  - *TMA Outer Analysis Boundary*: Lat `33.00° N` to `33.80° N`, Lon `36.10° E` to `36.95° E` (approx. 30 NM radius).
  - *Inner Runway Approach Box*: Lat `33.395° N` to `33.435° N`, Lon `36.490° E` to `36.545° E`.
- **Target Historical Temporal Scope**: `2024-01-01` to `2026-10-31` (with focused pilot evaluation across 8 benchmark calendar dates: `2024-01-15`, `2024-03-15`, `2024-05-15`, `2024-07-15`, `2024-09-15`, `2024-10-10`, `2025-06-15`, and `2026-06-15`).

---

## 3. Technical Data Requirements & Trino Methodology

### 3.1 Requested Database Tables & Fields
Access is requested to the historical state vector tables hosted on the OpenSky Trino SQL cluster:
- **Primary Table**: `state_vectors_data4`
- **Requested Fields**:
  - `time` (epoch timestamp in seconds)
  - `icao24` (24-bit Mode-S transponder aircraft address in hexadecimal)
  - `callsign` (broadcast 8-character flight callsign)
  - `lat` / `lon` (WGS-84 geographic position coordinates)
  - `velocity` (horizontal groundspeed in m/s)
  - `heading` (track angle in degrees clockwise from true north)
  - `vertrate` (vertical speed / barometric rate of climb or descent in m/s)
  - `baroaltitude` (barometric altitude in meters MSL)
  - `geoaltitude` (geometric / GNSS altitude in meters MSL)
  - `onground` (transponder squat-switch surface status flag)
  - `lastposupdate` (age of positional telemetry)

### 3.2 Proposed Query Methodology & Cluster Protection
To ensure minimal load on the shared OpenSky Trino cluster:
1. **Strict Partition Filtering**: Every query will strictly constrain the `time` column using partition bounds corresponding to single 24-hour evaluation dates (e.g. `time BETWEEN 1705276800 AND 1705363200`).
2. **Spatial Pre-Filtering**: Queries will enforce coordinate boundaries in the SQL `WHERE` clause, eliminating over 99.9% of global rows before aggregation.
3. **No Unbounded Scans**: No automated streaming loops or full-table joins will be dispatched. All extracts will be downloaded as small, highly targeted CSV extracts for local offline analysis.

### 3.3 Why Historical Trino Access is Essential
The standard OpenSky REST API enforces a rolling 30-day window (`/api/flights/departure` and `/api/flights/arrival` return `HTTP 403 Forbidden` for queries older than 30 days). Furthermore, REST flight endpoints synthesize flights based on heuristics optimized for dense European airspace, which frequently fail in sparse-coverage regions. Direct access to raw state vectors in Trino is the **only technical mechanism** capable of analyzing raw message frequency, altitude degradation curves, and transponder continuity for historical dates in 2024–2026.

---

## 4. Expected Research Outputs & Scientific Value

1. **Open Scientific Publication**: A peer-reviewed conference or journal paper evaluating receiver coverage resilience and trajectory qualification algorithms in low-sensor environments.
2. **Open-Source Methodology**: Transparent, documented Python algorithms for categorizing airspace overflights versus terminal approach candidates without promoting uncorroborated telemetry to confirmed landings.
3. **Epistemic Data Classification Standard**: A formal framework distinguishing *sensor voids* from *confirmed zero operations* (e.g., distinguishing an aerodrome closure from an ADS-B antenna outage).
4. **Mandatory OpenSky Attribution**: All publications, presentations, and technical documentation will explicitly cite the foundational OpenSky Network paper (Schäfer et al., IPSN 2014) and acknowledge the OpenSky Association.

---

## 5. Data Governance, Security & Retention Plan

1. **Non-Commercial Exclusivity**: All retrieved data will be utilized strictly for non-commercial academic research. No data will be monetized, licensed, or integrated into commercial software.
2. **Secure Local Staging**:
   - Extracted CSV files will be stored in an encrypted, isolated directory: `data/historical_sample_review/opensky/`.
   - Raw files will be cryptographically hashed (SHA-256) upon retrieval.
   - The production database `damascus_airport.db` will remain strictly isolated and read-only.
3. **No Bulk Redistribution**:
   - In compliance with OpenSky Network terms and CC BY-NC 4.0 licensing, raw state-vector dumps will **NOT** be published or redistributed in public software repositories.
   - Only aggregated statistical metrics (e.g. daily candidate movement counts, hourly coverage frequency graphs) will be included in published research.
4. **Data Purge / Retention Policy**:
   - Data will be retained on secure local storage only for the duration of the research evaluation. Upon completion of research dissemination, raw files will be archived or purged in accordance with institutional data management standards.
