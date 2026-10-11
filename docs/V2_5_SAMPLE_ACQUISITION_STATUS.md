# Syrian Airport Data Engine — Version 2.5
# Historical Sample Acquisition Status & Provider Inquiries

**Document Identifier**: `docs/V2_5_SAMPLE_ACQUISITION_STATUS.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Audit Date**: 2026-10-11  
**Target Window**: 2024–2026 Historical Proof-of-Availability Window  
**Operating Standard**: STRICTLY READ-ONLY (No Pipeline Ingestion, No Unauthorized Outbound Submissions)  

---

## 1. Phase 1 — Systematic Review of Version 2.4 Documentation

Prior to preparing sample acquisition assets, a comprehensive cross-document consistency audit was performed on all Version 2.4 specifications:
- [`docs/V2_4_HISTORICAL_SAMPLE_REQUESTS.md`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/docs/V2_4_HISTORICAL_SAMPLE_REQUESTS.md)
- [`docs/V2_4_PROVIDER_COMPARISON.md`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/docs/V2_4_PROVIDER_COMPARISON.md)
- [`docs/V2_4_SAMPLE_VALIDATION_SPEC.md`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/docs/V2_4_SAMPLE_VALIDATION_SPEC.md)
- [`docs/V2_4_OFFICIAL_STATISTICS_ACQUISITION.md`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/docs/V2_4_OFFICIAL_STATISTICS_ACQUISITION.md)
- [`docs/V2_4_GO_NO_GO_DECISION.md`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/docs/V2_4_GO_NO_GO_DECISION.md)

### Audit Findings & Refinements
1. **OpenSky Eligibility Refinement**:
   - *Previous Assumption*: V2.4 noted that `.edu` domain email addresses were strictly required for OpenSky Trino access.
   - *Verified Evidence*: Direct inspection of official OpenSky Network data access documentation confirms that Trino historical access is reserved for **university-affiliated researchers, governmental organizations, and civil aviation authorities**. An institutional email is recommended to expedite verification, but the statutory criterion is **institutional research affiliation**, not strictly an American `.edu` top-level domain (accredited universities with `.ac.uk`, `.edu.sy`, `.de`, `.ch`, or research institutes are fully eligible).
2. **AviationStack Limitation Confirmed**:
   - V2.4 established that AviationStack self-service plans ($499.99/mo Business) enforce a hard **3-month sliding window**. This finding is confirmed and maintained: multi-year 2024 data cannot be retrieved on self-service plans.
3. **Target Dates Consistency**:
   - The eight strategic sampling dates (`2024-01-15`, `2024-03-15`, `2024-05-15`, `2024-07-15`, `2024-09-15`, `2024-10-10`, `2025-06-15`, and `2026-06-15`) are synchronized across all schemas.

---

## 2. Phase 2 — Sample Acquisition Workspace Architecture

An isolated directory hierarchy has been established within `data/` to ensure incoming sample records remain completely segregated from production database files (`data/damascus_airport.db`):

```text
data/historical_sample_review/
├── opensky/                    # Raw OpenSky Trino state vector JSON/CSV dumps
├── flightradar24/              # Raw Flightradar24 commercial sample extracts
├── flightaware/                # Raw FlightAware AeroAPI sample responses
├── official_statistics/        # Primary Syrian government PDFs and scanned bulletins
└── sample_manifests/          # Machine-readable JSON and human-readable Markdown manifests
    ├── manifest_template.json  # Formal JSON schema for incoming sample files
    └── TEMPLATE_MANIFEST.md    # Markdown manifest template
```

### Safety Invariant
> [!IMPORTANT]
> Files placed in `data/historical_sample_review/` are **never** loaded into the production database `damascus_airport.db`.
> All raw files are cryptographically hashed (SHA-256) upon receipt and evaluated solely through isolated Python scripts in `scratch/`.

---

## 3. Phase 3 — Final Provider Sample Requests (Ready to Send)

The following ready-to-send formal inquiries have been prepared for user authorization and dispatch.

---

### Request 1: Flightradar24 Commercial Data Services

- **Recipient**: `sales@fr24.com`, `api@fr24.com`
- **Subject**: *Commercial Inquiry: Historical Movement Sample & Availability Confirmation — Damascus (DAM / OSDI) [2024–2026]*
- **Operational Status**: `awaiting_provider_response` (Pending User Dispatch Approval)

```text
Dear Flightradar24 Commercial Data Services Team,

The Syrian Airport Data Engine research project is evaluating historical flight tracking data for Damascus International Airport (IATA: DAM, ICAO: OSDI) across the calendar period from January 2024 through June 2026.

Prior to entering into a commercial agreement (such as the Developer API Essential/Advanced tier or a bespoke historical data extract), we must establish whether Flightradar24 recorded physical aircraft operations at OSDI during this historical timeframe.

1. Proof-of-Availability Sample Request:
We request a small, complimentary proof-of-availability sample covering the following eight historical dates:
   - 2024-01-15
   - 2024-03-15
   - 2024-05-15
   - 2024-07-15
   - 2024-09-15
   - 2024-10-10
   - 2025-06-15
   - 2026-06-15

For each arrival and departure movement at OSDI on these dates, we require:
   a. Operating Flight Number / Call sign (and marketing codeshare, if present)
   b. Operating Airline Name and ICAO/IATA designator
   c. Aircraft Registration Mark (tail number) and 24-bit Mode-S ICAO24 Hex Address
   d. Origin and Destination aerodrome codes
   e. Scheduled, Estimated, and Actual Takeoff Times (ATD) and Landing Times (ATA)
   f. Upstream Telemetry Flag: Indication of whether ATD/ATA were derived from terrestrial ADS-B/MLAT, satellite ADS-B, or schedule progression
   g. Original Flightradar24 flight/record transaction identifier

2. Commercial & Contractual Terms Clarification:
   - Historical Completeness: What proportion of commercial movements at OSDI were tracked down to runway surface levels vs. airborne terminal fixes?
   - API Tier vs. Bespoke Archive: Does the Developer Essential tier ($90/mo) provide full programmatic access back to January 2024 for OSDI, or is the Advanced tier ($900/mo) required? What is the pricing for a one-time bespoke CSV historical extract covering 2024-01-01 to 2026-10-31?
   - Local Database Storage Rights: Does your developer/commercial agreement permit storing non-real-time historical event logs in an internal analytical SQLite database for ongoing academic research?
   - Downstream Publishing Rights: Are derivative statistical aggregates (e.g. monthly airport movement totals) permitted to be published in research reports?

We appreciate your assistance and look forward to receiving your sample extract and commercial quotation.

Sincerely,

Aviation Data Systems Team
Syrian Airport Data Engine Project
```

---

### Request 2: FlightAware Enterprise Sales & AeroAPI Support

- **Recipient**: `sales@flightaware.com`, `aeroapi@flightaware.com`
- **Subject**: *AeroAPI Enterprise Inquiry: Historical Flight Data Sample for Damascus International Airport (DAM / OSDI)*
- **Operational Status**: `awaiting_provider_response` (Pending User Dispatch Approval)

```text
Dear FlightAware Enterprise Team,

Our research team is evaluating commercial historical aviation data sources for Damascus International Airport (ICAO: OSDI, IATA: DAM) covering January 2024 to June 2026.

Given the regional ground receiver deficit in the Levant, we are specifically interested in whether FlightAware’s space-based Aireon 1090MHz ADS-B constellation captures arrival and departure movements at OSDI down to runway threshold levels, rather than solely high-altitude en-route overflights.

1. Proof-of-Availability Historical Sample:
Could FlightAware provide a proof-of-availability sample extract for OSDI covering eight benchmark test dates:
   - 2024-01-15
   - 2024-03-15
   - 2024-05-15
   - 2024-07-15
   - 2024-09-15
   - 2024-10-10
   - 2025-06-15
   - 2026-06-15

For each movement, please include:
   a. Flight identification: Operating call sign, flight number, and FlightAware flight ID (`fa_flight_id`)
   b. Codeshare metadata: Operating carrier vs. marketing carrier
   c. Aircraft identification: Registration tail number and 24-bit Mode-S ICAO24 hex address
   d. Timestamps: Scheduled, estimated, and actual OOOI times (specifically `actual_off` and `actual_on`)
   e. Data Origin & Sensor Provenance: Whether actual timestamps were derived from Aireon space-based ADS-B, terrestrial receivers, ANSP operational messages, or flight plan estimation

2. Technical & Commercial Inquiries:
   - Terminal Confirmation Capability: Can FlightAware confirm whether Aireon satellite telemetry provides low-altitude position updates down to aerodrome elevation (2,020 ft MSL) at OSDI to confirm runway landings and takeoffs?
   - Custom Historical Archive Pricing: What is the cost of a one-time historical CSV/JSON dataset for OSDI covering 2024-01-01 through 2026-10-31?
   - Evaluation Access: Can FlightAware provision a 7-day trial token with historical query capabilities for OSDI to evaluate endpoint data density?
   - Retention & Export Rights: What licensing terms govern internal SQLite database storage of historical flight records and derivative research publication?

We look forward to your response and sample dataset.

Best regards,

Aviation Data Systems Team
Syrian Airport Data Engine Project
```

---

### Request 3: OpenSky Network Association (Research Access Application)

- **Submission Channel**: OpenSky Network Data Access Portal (`https://opensky-network.org/my-opensky/request-data`)
- **Target Interface**: Trino / Impala SQL Cluster Access (`state_vectors_data4`)
- **Operational Status**: `awaiting_user_approval` (Pending Research Institutional Review)

#### Application Profile & Justification Text
```text
Project Title: 
Empirical Reconstruction of Civilian Air Transport Continuity in Sanctioned and Conflict-Affected Regions: Damascus International Airport (DAM / OSDI) Case Study (2024–2026).

Applicant Organization: 
[Affiliated University / Non-Profit Academic Research Institute]

Principal Investigator: 
[PI Name & Institutional Title]

Research Abstract & Purpose:
This scientific study evaluates the continuity, resilience, and operational characteristics of civilian air transport at Damascus International Airport (ICAO: OSDI, elevation 2,020 ft MSL) from January 2024 through October 2026. The research aims to evaluate transponder reporting compliance, analyze approach and departure kinematics, and model terminal airspace connectivity. Access to the OpenSky Trino SQL historical cluster is required to query raw Mode-S state vectors for academic, non-commercial research purposes.

Specific Data Requirements:
1. Table: `state_vectors_data4`
2. Bounding Box: Latitude 33.10° N to 33.70° N; Longitude 36.15° E to 36.85° E (Damascus Terminal Maneuvering Area)
3. Target Temporal Window: Select dates between 2024-01-01 and 2026-10-31
4. Fields Requested: `time`, `icao24`, `callsign`, `lat`, `lon`, `velocity`, `heading`, `vertrate`, `baroaltitude`, `geoaltitude`, `onground`, `lastposupdate`

Statement of Compliance:
The applicant affirms that all data retrieved will be used exclusively for non-commercial academic research in strict compliance with the OpenSky Network terms and CC BY-NC 4.0 licensing. No raw state vectors will be redistributed or commercialized.
```

#### Test Query & Terminal Coverage Measurement Methodology
When Trino access is activated, terminal coverage at OSDI will be measured using the following automated SQL evaluation script:

```sql
-- Terminal Coverage & Minimum Descent Elevation Audit at OSDI
WITH o_tma AS (
    SELECT 
        icao24,
        callsign,
        time,
        baroaltitude,
        geoaltitude,
        velocity,
        vertrate,
        onground,
        lat,
        lon
    FROM state_vectors_data4
    WHERE time BETWEEN 1705276800 AND 1705363200 -- 2024-01-15 UTC
      AND lat BETWEEN 33.30 AND 33.52
      AND lon BETWEEN 36.40 AND 36.65
)
SELECT 
    icao24,
    callsign,
    MIN(baroaltitude) AS min_baro_alt_ft,
    MIN(geoaltitude) AS min_geo_alt_ft,
    MAX(CASE WHEN onground = TRUE THEN 1 ELSE 0 END) AS has_onground_flag,
    COUNT(*) AS total_terminal_fixes
FROM o_tma
GROUP BY icao24, callsign;
```

**Coverage Measurement Criteria**:
- If `min_baro_alt_ft` $> 3,500\text{ ft MSL}$ (airport is 2,020 ft MSL), the flight dropped off before touchdown $\rightarrow$ Classify as `probable_movement` or `unverified_movement`.
- If `min_baro_alt_ft` $\le 2,150\text{ ft MSL}$ and coordinates match runway centerline $\rightarrow$ Classify as `confirmed_physical`.

---

## 4. Source Status Summary Ledger

| Prospective Source | Procurement State | Evidence Backing Current State | Confidence Classification |
| :--- | :--- | :--- | :--- |
| **OpenSky Network** | `awaiting_user_approval` | Official terms require institutional affiliation; application draft ready. | **Partially Verified / Awaiting Approval** |
| **Flightradar24** | `awaiting_provider_response` | Commercial developer terms verified; sample inquiry draft finalized. | **Verified Capabilities / Pending Sample** |
| **FlightAware** | `awaiting_provider_response` | AeroAPI documentation verified; enterprise sample inquiry finalized. | **Verified Capabilities / Pending Sample** |
| **Syrian CBS & MoT** | `pending_acquisition` | Pre-2011 abstracts verified; post-2020 volumes require procurement. | **Unverified Specifics / Pending Acquisition** |
| **Syria Economic Monitor** | `sample_obtained_validated` | 578 rows verified in `historical_daily_movements_2024` as `DAM_ALP_LTK`. | **Verified Multi-Airport Aggregate** |
| **AviationStack** | `not_available` (Disqualified) | 3-month sliding window limitation documented; cannot access 2024. | **Contradicted (Disqualified)** |
