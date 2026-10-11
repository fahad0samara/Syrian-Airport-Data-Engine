# Syrian Airport Data Engine — Version 2.4
# Provider Evidence, Sample Feasibility & Cost Comparison

**Document Identifier**: `docs/V2_4_PROVIDER_COMPARISON.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Audit Date**: 2026-10-11  
**Target Standard**: Verified Primary Pricing & Anti-Speculation Protocol  
**Status**: APPROVED SPECIFICATION  

---

## 1. Executive Summary & Epistemic Constraints

This document evaluates the commercial feasibility, data quality, access requirements, and cost structure of external aviation data providers for historical flight tracking at Damascus International Airport (`DAM` / `OSDI`).

### Anti-Speculation Rules
1. **No Invented Prices**: Pricing figures are reported strictly from live verified pricing schedules. Where enterprise customization or sales quotes are required, costs are formally recorded as `quote_required`.
2. **No Assumed Coverage**: General advertising claims ("Global ADS-B coverage") are not accepted as proof of historical tracking at Damascus.
3. **No Assumed Enterprise Capabilities**: We do not assume bespoke custom options exist unless documented in provider technical specifications or sales collateral.

---

## 2. In-Depth Provider Sample Feasibility

### 2.1 OpenSky Network

#### Access Application Requirements
Access to historical OpenSky data (>30 days into the past) is hosted on the OpenSky Trino/Impala SQL cluster and is strictly governed by the OpenSky Network Association (Switzerland).

1. **Institutional Affiliation Requirement**:
   - The OpenSky Network charter strictly restricts Trino direct SQL access to **academic institutions, universities, non-profit research organizations, or state regulatory bodies**.
   - An application **CANNOT** be submitted or approved without a verified institutional email (e.g., `.edu`, `.ac.uk`, or accredited research domain).
   - Commercial entities, private hobbyists, and unverified individual developers are denied Trino cluster credentials.
2. **Application Process**:
   - Submission of a formal written Research Proposal via the OpenSky portal (`https://opensky-network.org/apply-for-data`).
   - Must specify: Principal Investigator (PI), institutional affiliation, research project abstract, exact query parameters, data retention policies, and statement of non-commercial intent.
   - Processing time: 2 to 6 weeks. Access is granted only after manual review by the OpenSky Association Board.
3. **Access Governance Rule**:
   > [!IMPORTANT]
   > Syrian Airport Data Engine does **NOT** currently possess approved OpenSky Trino cluster credentials. No claim of access may be made until formal written approval is granted.

#### SQL Query Design for OSDI Historical Observations
When approved, queries against the `state_vectors_data4` table must isolate Damascus terminal airspace using tight spatial-temporal bounds to avoid cluster timeouts:

```sql
-- OpenSky Trino Historical Extraction Query Template: Damascus TMA
SELECT 
    time,
    icao24,
    callsign,
    lat,
    lon,
    velocity,
    heading,
    vertrate,
    baroaltitude,
    geoaltitude,
    onground,
    lastposupdate
FROM 
    state_vectors_data4
WHERE 
    time BETWEEN 1705276800 AND 1705363200 -- 2024-01-15 00:00:00 UTC to 23:59:59 UTC
    AND lat BETWEEN 33.2000 AND 33.6000     -- OSDI TMA Latitude window (+/- 0.2 deg)
    AND lon BETWEEN 36.3000 AND 36.7500     -- OSDI TMA Longitude window (+/- 0.25 deg)
    AND (baroaltitude < 5000 OR baroaltitude IS NULL)
ORDER BY 
    icao24, time ASC;
```

#### Metric for Terminal Coverage & Runway Evidence
To evaluate receiver density at OSDI from OpenSky historical state vectors:
1. **Vertical Penetration Metric**: Lowest observed geometric/barometric altitude per trajectory approaching OSDI. If the minimum observed altitude is $> 3,500\text{ ft MSL}$ (airport elevation is 2,020 ft MSL), terminal receiver line-of-sight is absent.
2. **Runway Surface Detection Rate**: Percentage of suspected arrival/departure trajectories with $\ge 3$ consecutive messages inside the OSDI runway surface polygon with `onground = True` and groundspeed $< 80\text{ kts}$. Historically, this rate is estimated at $< 5\%$ due to Syrian feeder deficit.

---

### 2.2 Flightradar24 (FR24)

#### Feasibility & Terms Assessment
- **Sample Availability**: FR24 does not provide automated self-service free trials for historical developer tiers. However, the commercial data services team (`sales@fr24.com`) routinely provides a sample CSV extract (1–2 dates) upon formal written request to verify schema and local tracking density before enterprise contract execution.
- **Developer REST API Pricing**:
  - *Explorer*: $9.00/month (30 days history, 10,000 monthly credits). Insufficient for 2024 historical reconstruction.
  - *Essential*: $90.00/month (2 years rolling history, 100,000 monthly credits). Covers dates from late 2024 onward, but sliding window drops early 2024.
  - *Advanced*: $900.00/month (unlimited history back to May 2016, 1,000,000 monthly credits). Full historical coverage.
- **Consumer Scraping Ban**: Section 8 of the Flightradar24 Terms of Use strictly prohibits automated scraping or programmatic retrieval from consumer web accounts (Silver/Gold/Business). Any data extracted via scraping is contractually tainted and legally unviable.
- **Licensing & Retention**: Standard Developer API license allows internal storage of flight events in a client database; public redistribution or open-access publishing of raw feeds is prohibited.

---

### 2.3 FlightAware (AeroAPI v4)

#### Feasibility & Terms Assessment
- **Sample Availability**: Self-service accounts receive a personal API key with $0 monthly minimum, but **strictly zero historical access**. A historical sample for OSDI requires direct coordination with FlightAware Enterprise Sales (`sales@flightaware.com`).
- **AeroAPI Pricing Structure**:
  - *Personal*: $0/mo base + $0.005/query. Historical: 0 days (live and forward scheduled only).
  - *Standard*: $100.00/month minimum spend. Historical: Up to 30 days into the past.
  - *Enterprise / Custom Archive*: Custom contract required for multi-year historical queries back to January 2024.
- **Coverage Strength**: FlightAware ingests space-based 1090MHz ADS-B telemetry from the Aireon constellation (hosted on Iridium NEXT satellites). This provides continuous en-route visibility over Syrian airspace without relying on local terrestrial antenna feeders.
- **Actual Timestamp Fidelity**: FlightAware provides `actual_off` and `actual_on` derived from satellite transponder telemetry.

---

### 2.4 AviationStack

#### Feasibility & Elimination Notice
- **Self-Service Historical Restriction**: Official documentation confirms that self-service historical queries via `/v1/flights?flight_date=YYYY-MM-DD` are strictly restricted to a **3-month sliding window** on the Business Plan ($499.99/month).
- **Multi-Year 2024 Infeasibility**: The self-service plan **CANNOT** access January–October 2024 data.
- **Enterprise Status**: AviationStack marketing notes custom Enterprise options, but historical data depth, pricing, and timestamp veracity for regional airports in conflict zones are undocumented.
- **Veracity Deficit**: AviationStack historical records for regional Middle Eastern aerodromes consist heavily of static airline timetable schedules with duplicate "actual" fields. It does **not** provide independent physical sensor proof.
- **Decision**: Eliminated from consideration for historical backfill.

---

## 3. Comprehensive Evidence & Cost Comparison Matrix

| Provider / Channel | Historical Sample Availability | Historical Date Depth | DAM-Specific Terminal Coverage | Actual Timestamp Quality | Aircraft ID (Reg / Hex) | Licensing & Retention Restrictions | One-Time Sample Cost | Monthly Subscription Cost | Custom Historical Archive Cost | Remaining Critical Uncertainties |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **OpenSky Network** | Available upon research approval | 2013 to present (Trino SQL) | Sparse / En-route dominant | Epoch timestamps; surface touchdown unverified | Yes (`icao24`, reg mapped) | CC BY-NC 4.0; strictly non-commercial; no raw resale | **Free** ($0) | **Free** ($0) | **Free** ($0) | Institutional approval required; surface receiver line-of-sight deficit at OSDI. |
| **Flightradar24** | Available via sales inquiry | May 2016 to present (Adv.) | High (Regional feeders + satellite) | High (ATD/ATA from MLAT/ADS-B) | Complete (`reg`, `hex`) | Commercial developer license; internal retention permitted | **Free** (Pre-sales sample) | **$90/mo** (Essential) / **$900/mo** (Adv.) | `quote_required` | Minimum contractual commitment for 2024 historical bulk export. |
| **FlightAware** | Available via enterprise sales | 2011 to present (Enterprise) | High (Space-based Aireon ADS-B) | High (Actual OOOI `wheels_on`/`off`) | Complete (`reg`, `hex`) | Enterprise commercial; internal database retention permitted | `quote_required` (Evaluation trial) | **$100/mo min** (Standard) | `quote_required` | Enterprise minimum spend threshold; surface vs. satellite altitude resolution at OSDI. |
| **ADS-B Exchange** | Sample data files on site | 2016 to present (Raw bulk) | Low/Unverified at surface | Raw message epoch; no synthesized OOOI | Yes (Unfiltered transponder) | Commercial license (Jetnet); no public repository mirroring | `unknown` | `quote_required` (RapidAPI) | `quote_required` (Jetnet enterprise) | Historical presence of active feeders in Damascus city/suburbs is doubtful. |
| **AviationStack** | None for 2024 (3-mo limit) | 3-month sliding window | Syntactic filter only | Low (Schedules & estimations) | Incomplete (Frequently missing) | Commercial API license; no external redistribution | Not available for 2024 | **$499.99/mo** (Business) | `quote_required` (Enterprise) | Cannot access 2024 on self-service; timestamps lack sensor provenance. |
| **ICAO Data+** | Trial preview via portal | Multi-decade annual/monthly | Macro airport reporting | None (Monthly aggregate counts only) | None | Strict ICAO copyright; redistribution prohibited | `unknown` | `quote_required` (Annual subscription) | `quote_required` | 2–3 year reporting lag for Syrian state returns; no daily or flight-level events. |
| **Syrian SCAA / MoT** | Public government portals | Select annual reports | Official sovereign authority | None (NOTAM effective windows only) | Official fleet registry | Syrian state sovereign domain | **Free** ($0) | **Free** ($0) | **Free** ($0) | No electronic per-flight API; documents require manual physical/PDF acquisition. |
| **Syrian CBS** | Printed abstracts / PDF | Multi-decade annual | Macro chapter tables | None (Annual totals only) | None | National statistical office | **Free** ($0) | **Free** ($0) | **Free** ($0) | Recent 2020–2024 PDFs pending acquisition; airport-level breakdown unverified. |

---

## 4. Key Strategic Takeaways

1. **Top Commercial Candidates**: Flightradar24 (Developer Advanced / Essential) and FlightAware (AeroAPI Enterprise) are the only two providers possessing both satellite/terrestrial sensor coverage and verifiable `actual` timestamps for Damascus.
2. **Top Open Academic Candidate**: OpenSky Network represents the sole zero-cost physical telemetry archive, but is contingent upon academic institutional affiliation and will yield mostly approach/climbout candidates rather than confirmed touchdown events.
3. **Disqualified Candidates**: AviationStack is disqualified due to its $499.99/mo cost, 3-month window restriction, and reliance on scheduled/estimated data. Consumer web scraping is legally and technically disqualified across all platforms.
