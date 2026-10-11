# Syrian Airport Data Engine — Version 2.4
# Historical Data Sample Request Specification & Outbound Inquiries

**Document Identifier**: `docs/V2_4_HISTORICAL_SAMPLE_REQUESTS.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Timezone**: `Asia/Damascus` (UTC+3)  
**Date of Specification**: 2026-10-11  
**Target Window**: 2024–2026 Strategic Historical Sampling  
**Operating Standard**: STRICTLY READ-ONLY (Proof of Availability & Feasibility Only)  

---

## 1. Executive Summary & Objective

Before authorizing any commercial subscription, developer contract, or pipeline implementation, the Syrian Airport Data Engine requires empirical **Proof of Availability**.

The objective is **not** to acquire the complete historical database, but to obtain a targeted, multi-temporal verification sample (8 specific calendar dates spanning 2024 to 2026) to establish:
1. Whether historical flight-level records for Damascus International Airport (`DAM` / `OSDI`) actually exist in commercial provider archives.
2. The physical fidelity and precision of available timestamps (specifically distinguishing `actual` runway touchdown/takeoff times from `estimated`, `scheduled`, or `inferred` times).
3. The presence of physical aircraft identity attributes (ICAO24 Mode-S hex codes and tail registrations).
4. The legal and contractual feasibility of data retention and research redistribution under provider terms.

---

## 2. Standardized Historical Sampling Dates

The following eight calendar dates have been selected to evaluate historical availability across seasonal cycles, regional geopolitical shifts, and multi-year coverage continuity:

| Sample Index | Target Flight Date | Operational Context & Evaluation Rationale |
| :---: | :---: | :--- |
| **D1** | `2024-01-15` | Mid-January 2024: Post-strike recovery period; evaluates baseline commercial schedule vs. active physical flights. |
| **D2** | `2024-03-15` | Mid-March 2024: Pre-Ramadan regional traffic; verifies Q1 2024 tracking continuity. |
| **D3** | `2024-05-15` | Mid-May 2024: Early summer schedule expansion; evaluates regional charter operations. |
| **D4** | `2024-07-15` | Mid-July 2024: Peak summer passenger traffic (Syrian Air, Cham Wings, regional Gulf links). |
| **D5** | `2024-09-15` | Mid-September 2024: Late summer operational benchmark; tests late Q3 2024 continuity. |
| **D6** | `2024-10-10` | 2024-10-10: Fall benchmark date; enables direct multi-source validation against existing baseline data. |
| **D7** | `2025-06-15` | Mid-June 2025: Mid-term historical benchmark; evaluates provider archive depth past 1-year retention. |
| **D8** | `2026-06-15` | Mid-June 2026: Recent operational benchmark; tests intermediate continuity prior to recent operational deep dives. |

---

## 3. Standardized Sample Data Schema

For every flight movement on the target dates, the provider must deliver the following standardized schema:

| Schema Attribute | Technical Type | Format / Allowed Values | Requirement Level | Semantic Definition |
| :--- | :--- | :--- | :---: | :--- |
| `airport_icao` | String | Exactly `OSDI` | **Mandatory** | ICAO location indicator for Damascus International Airport. |
| `airport_iata` | String | Exactly `DAM` | Mandatory | IATA aerodrome designator. |
| `movement_type` | String | `'arrival'` or `'departure'` | **Mandatory** | Direction of flight movement relative to OSDI. |
| `operating_flight_no` | String | E.g. `RB435`, `SAW501` | **Mandatory** | Call sign or operating flight number assigned to physical aircraft. |
| `marketing_flight_no`| String | E.g. `IR601`, `W5123` | Optional | Commercial marketing / codeshare flight designators. |
| `operating_airline` | String | E.g. `Syrian Air`, `Cham Wings`| Mandatory | Operating commercial air carrier or flight operator. |
| `aircraft_reg` | String | E.g. `YK-AKB`, `YK-BAA` | **High Priority** | Official national aircraft registration mark (tail number). |
| `icao24` | Hex String | 6-char hex, e.g. `74001B` | **High Priority** | Unique 24-bit Mode-S transponder aircraft address. |
| `origin_airport` | String | ICAO/IATA code | **Mandatory** | Point of departure. |
| `destination_airport`| String | ICAO/IATA code | **Mandatory** | Point of arrival. |
| `scheduled_departure`| ISO-8601 | `YYYY-MM-DDTHH:MM:SSZ` | Mandatory | Published timetable departure time. |
| `scheduled_arrival` | ISO-8601 | `YYYY-MM-DDTHH:MM:SSZ` | Mandatory | Published timetable arrival time. |
| `estimated_departure`| ISO-8601 | `YYYY-MM-DDTHH:MM:SSZ` | Optional | Modeled or ATC-estimated departure time. |
| `estimated_arrival` | ISO-8601 | `YYYY-MM-DDTHH:MM:SSZ` | Optional | Modeled or ATC-estimated arrival time. |
| `actual_departure` | ISO-8601 | `YYYY-MM-DDTHH:MM:SSZ` | **Critical** | Physical runway wheels-off (`OFF`) timestamp. |
| `actual_arrival` | ISO-8601 | `YYYY-MM-DDTHH:MM:SSZ` | **Critical** | Physical runway touchdown (`ON`) timestamp. |
| `observation_timestamp`| ISO-8601| `YYYY-MM-DDTHH:MM:SSZ` | Mandatory | Provider database ingestion / telemetry packet epoch. |
| `flight_status` | Enum | `landed`, `departed`, `cancelled`, `diverted`, `scheduled` | **Mandatory** | Final recorded operational outcome. |
| `source_record_id` | String | Provider primary key | **Mandatory** | Unique persistent transaction identifier in provider system. |

---

## 4. Strict Timestamp Taxonomy & Epistemic Boundaries

Every supplied timestamp must be categorized into one of four mutually exclusive epistemic states:

1. **`actual` (Physical Sensor Verification)**:
   - *Arrival*: Wheels-on-runway (`ON`) derived from multilateration (MLAT), surface transponder squat-switch (`onground = True` inside OSDI boundary), or ADS-B vertical speed drop to zero on runway centerline.
   - *Departure*: Wheels-off-runway (`OFF`) derived from takeoff acceleration roll and lift-off detection at aerodrome elevation.
   - *Constraint*: Must **never** be populated by copying scheduled or estimated times.
2. **`estimated` (Operational / Algorithmic Model)**:
   - Derived from active en-route radar fixes extrapolated along standard flight airways to the threshold.
   - Represents an educated calculation, not physical runway proof.
3. **`scheduled` (Timetable Intention)**:
   - Extracted from published airline Global Distribution Systems (GDS, OAG, Cirium, Innovata) prior to flight departure.
   - Does **not** confirm that aircraft departed or landed.
4. **`inferred` (Airborne Window Approximation)**:
   - Generated by recording the first airborne ADS-B message (`firstSeen`) or last airborne message (`lastSeen`) when surface line-of-sight is absent.
   - Must remain flagged as `inferred` and cannot be treated as actual touchdown/takeoff.

---

## 5. Outbound Inquiry Drafts for Commercial Providers

### Outbound Draft 1: Flightradar24 (Commercial Data Services)

**Recipient**: `sales@fr24.com` / `api@fr24.com`  
**Subject**: *Commercial Inquiry: Historical Movement Sample & Availability Confirmation — Damascus (DAM / OSDI) [2024–2026]*  

```text
Dear Flightradar24 Commercial Data Services Team,

We are conducting an evidentiary feasibility study for the Syrian Airport Data Engine, an aviation research platform monitoring operations at Damascus International Airport (IATA: DAM, ICAO: OSDI).

Prior to purchasing a commercial subscription (such as the Developer API Essential/Advanced tier or a custom historical data extraction), we must establish whether Flightradar24 possesses actual physical tracking records for OSDI across our target historical study window (January 2024 to June 2026).

Due to terrestrial receiver limitations in the Levant, we need to verify the density and quality of historical records before entering into a commercial agreement. Specifically:

1. Feasibility Sample Request:
Could your team provide a small, complimentary proof-of-availability sample for two historical test dates:
   - 2024-07-15
   - 2024-10-10
For all arrivals and departures at OSDI, we require:
   - Operating Call sign / Flight Number
   - Operating Aircraft Registration & ICAO24 Mode-S Hex Address
   - Actual Takeoff Time (ATD) and Actual Landing Time (ATA)
   - Quality flag indicating whether ATD/ATA were derived from terrestrial ADS-B/MLAT, satellite ADS-B, or estimated/scheduled schedules.

2. Commercial & Contractual Clarifications:
   - Developer API Pricing & History: Could you confirm whether the Essential tier ($90/month) provides full access to flights back to January 2024 for OSDI, or if the Advanced tier ($900/month) / bespoke historical archive is required?
   - Retention & Derivative Research Rights: Does the Flightradar24 Developer API agreement permit storing ingested historical movement records in an internal analytical SQLite database for ongoing academic/analytical reporting?
   - Bespoke Historical CSV Export: If an API subscription is not the optimal vehicle for historical backfills, what is the cost of a one-time historical CSV/JSON export covering all arrivals and departures at OSDI between 2024-01-01 and 2026-10-31?

We appreciate your assistance in confirming data availability and look forward to your quotation and sample data.

Best regards,

Aviation Data Systems Team
Syrian Airport Data Engine Project
```

---

### Outbound Draft 2: FlightAware (AeroAPI / Enterprise Historical Services)

**Recipient**: `sales@flightaware.com` / `aeroapi@flightaware.com`  
**Subject**: *AeroAPI Enterprise Inquiry: Historical Flight Data Sample for Damascus International Airport (DAM / OSDI)*  

```text
Dear FlightAware Enterprise Team,

Our research team is evaluating commercial historical flight data sources for Damascus International Airport (ICAO: OSDI, IATA: DAM) covering the calendar period from January 2024 through October 2026.

We are interested in FlightAware’s space-based Aireon ADS-B capabilities, as terrestrial ADS-B coverage in Syria is historically constrained. Before committing to an AeroAPI contract or custom historical archive purchase, we must verify the level of actual movement coverage FlightAware recorded for OSDI during this timeframe.

1. Historical Proof-of-Availability Sample:
Could FlightAware provide a sample extract for two test dates (e.g., 2024-07-15 and 2024-10-10) for airport OSDI containing:
   - Flight identification (ident, fa_flight_id)
   - Aircraft registration and ICAO24 hex address
   - Out/Off/On/In (OOOI) actual timestamps (specifically actual_off and actual_on)
   - Data source origin (Aireon space-based ADS-B, terrestrial receiver, ANSP message, or schedule estimation)

2. Commercial Scoping & Contract Terms:
   - AeroAPI Standard vs. Custom Historical Archive: Given that self-service AeroAPI Standard tiers are restricted to 30 days of history, what is the minimum contractual commitment or custom order cost to retrieve full historical flight records for OSDI from 2024-01-01 to 2026-10-31?
   - Evaluation Trial: Can an evaluation API token or temporary trial access with historical query permissions be provisioned for 7 business days to test endpoint responses for airport OSDI?
   - Database Storage & Licensing: What are the licensing conditions regarding long-term local database retention of non-real-time historical event logs for analytical research?

We look forward to reviewing your sample data and commercial proposal.

Sincerely,

Aviation Data Systems Team
Syrian Airport Data Engine Project
```

---

## 6. Execution Governance

1. **Strictly Outbound Only**: These drafts are prepared for project leadership to send via authorized communication channels.
2. **No Automated Scraping**: No automated scripts, scrapers, or trial registration bots will be dispatched.
3. **No Financial Commitment**: No paid orders will be placed until sample files are received and verified against the Validation Specification.
