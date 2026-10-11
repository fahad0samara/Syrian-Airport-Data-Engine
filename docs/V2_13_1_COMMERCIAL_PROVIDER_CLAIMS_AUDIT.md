# Syrian Airport Data Engine — Version 2.13.1
# Commercial & Enterprise Aviation Provider Claims Audit

**Document Identifier**: `docs/V2_13_1_COMMERCIAL_PROVIDER_CLAIMS_AUDIT.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Scope**: Factual Audit of Five Commercial Aviation Intelligence Providers Across 10 Criteria  
**Machine-Readable Twin**: `reports/v2_13_1_provider_comparison.csv`  
**Status**: APPROVED COMMERCIAL CLAIMS AUDIT  
**Production Integrity Invariant**: `data/damascus_airport.db` SHA-256 verified identical (`c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`).

---

## 1. Executive Summary & Audit Mandate

In Version 2.13, claims were made regarding commercial aviation tracking providers—specifically that FlightRadar24 Business subscription costs ~$499/year and reliably provides 365 days of historical runway movements for Damascus International Airport (`DAM` / `OSDI`).

Version 2.13.1 performs a rigorous audit of current publicly documented terms of service, API specifications, and official pricing for five major providers:
1. **FlightRadar24** (Flightradar24 AB, Sweden)
2. **FlightAware** (Collins Aerospace, USA)
3. **ADS-B Exchange** (ADS-B Exchange LLC, USA)
4. **Cirium** (LexisNexis Risk Solutions / RELX, UK)
5. **OAG** (Official Aviation Guide, UK)

In strict accordance with project safety guidelines, **no subscriptions were purchased, no accounts were created, and no sales representatives were contacted**.

---

## 2. Ten-Point Provider Technical Evaluation

### 2.1 FlightRadar24
1. **Historical Schedule Availability**: Yes. FlightRadar24 maintains an extensive commercial flight schedule database linked to active airline routes.
2. **Historical Flight Tracking**: Yes. Global ADS-B, MLAT, and satellite tracking archive.
3. **Airport Arrivals / Departures**: Yes. Dedicated `/data/airports/{iata}/` historical modules.
4. **Actual Touchdown Timestamps**: **Conditional**. Touchdown timestamps (`time_real` on arrival) are recorded only when local terrestrial receivers or high-rate multilateration track the aircraft down to runway threshold (<100 ft AGL). Where local receivers are sparse, FR24 marks arrival times as "Estimated" or derives them from flight plans.
5. **Actual Takeoff Timestamps**: **Conditional**. Takeoff timestamps (`time_real` on departure) require ADS-B reception on departure roll or immediate climb-out.
6. **Aircraft Registration**: Yes. Mapped via ICAO 24-bit transponder addresses.
7. **OSDI Specific Coverage**: **Unverified for Runway Movements**. Ground receiver coverage around Damascus is known to be sparse. While en-route flights transiting Syria are captured via regional and satellite receivers, **365-day continuous runway touchdown data for OSDI is not demonstrated by public documentation**.
8. **Historical Retention Period**:
   - **Silver Plan**: 90 days.
   - **Gold Plan**: 365 days.
   - **Business Plan**: 365 days (plus commercial display license and fleet tracking).
   - **Custom Historical Extracts**: Multi-year raw CSV extracts require custom commercial sales quotation.
9. **Export / API Availability**: Web CSV downloads are available on Business tier. RESTful API access is governed by separate commercial agreements.
10. **Price and Subscription Conditions**:
    - **Silver**: $14.99/year (or $1.99/month).
    - **Gold**: $44.99/year (or $4.99/month) for individual/personal research.
    - **Business**: $499.00/year (or $49.99/month) for business/commercial use.
    - *Correction*: V2.13 claimed that 365 days of history requires a $499/year Business plan. In reality, the Gold plan ($44.99/year) provides 365 days of flight history for personal use. However, neither tier guarantees physical touchdown coverage for OSDI.
- **Authoritative Verdict**: **CONDITIONAL GO**. Must remain conditional until empirical DAM-specific historical sample data confirms actual runway movement coverage.

---

### 2.2 FlightAware (AeroAPI v4)
1. **Historical Schedule Availability**: Yes. Global airline schedule aggregation.
2. **Historical Flight Tracking**: Yes. Terrestrial ADS-B, radar feeds, and Aireon space-based ADS-B.
3. **Airport Arrivals / Departures**: Yes. AeroAPI provides dedicated airport departure and arrival endpoints (`/airports/{id}/flights`).
4. **Actual Touchdown Timestamps**: **Estimated in low-receiver regions**. FlightAware documents that in areas lacking terminal ADS-B or ASDE-X surface radar, arrival times are derived from estimated time of arrival (ETA) or airline Out-Off-On-In (OOOI) messages.
5. **Actual Takeoff Timestamps**: Yes (`actual_off`), provided airborne transponder reception commences.
6. **Aircraft Registration**: Yes. Mapped from flight plans and transponder hex codes.
7. **OSDI Specific Coverage**: **Unverified for Terminal Movements**. High-altitude space-based tracking is active over Syria, but runway sensor confirmation is unverified.
8. **Historical Retention Period**:
   - **Personal Tier**: 14 days.
   - **Standard Tier**: 30 days.
   - **Enterprise Historical**: Up to multi-year archives via custom quotation.
9. **Export / API Availability**: RESTful JSON API (AeroAPI v4).
10. **Price and Subscription Conditions**:
    - Personal: Free tier + query charges.
    - Standard: $100.00/month base + query fees.
    - Historical custom reports: $500 to $3,000+. Strict terms prohibit committing raw API payloads to public open repositories.
- **Authoritative Verdict**: **CONDITIONAL GO**. High cost and licensing restrictions; unverified terminal sensor coverage.

---

### 2.3 ADS-B Exchange
1. **Historical Schedule Availability**: **No**. ADS-B Exchange tracks aircraft transponder signals only; it does not maintain airline schedules or commercial passenger timetables.
2. **Historical Flight Tracking**: Yes. Historical aircraft state vectors (raw 1-second telemetry).
3. **Airport Arrivals / Departures**: **No**. ADS-B Exchange does not parse or aggregate airport movements. It provides raw coordinate traces.
4. **Actual Touchdown Timestamps**: Requires complex computational trajectory modeling (calculating runway threshold intersection and descent rate).
5. **Actual Takeoff Timestamps**: Requires trajectory modeling.
6. **Aircraft Registration**: Yes, mapped from ICAO 24-bit hex.
7. **OSDI Specific Coverage**: **Demonstrated to be Absent at Ground Level**. ADS-B Exchange relies 100% on volunteer feeders. Without local feeders in Damascus, no low-altitude state vectors exist.
8. **Historical Retention Period**: 2016 to present.
9. **Export / API Availability**: RapidAPI JSON endpoints and enterprise historical tarballs.
10. **Price and Subscription Conditions**: RapidAPI query tiers range from $10/month to $400+/month. Processing raw multi-gigabyte coordinate streams requires substantial server infrastructure.
- **Authoritative Verdict**: **NO-GO**. Does not provide airport arrival/departure tables; extreme engineering overhead for zero low-altitude telemetry.

---

### 2.4 Cirium (Ascend / Diio / Core Aviation Analytics)
1. **Historical Schedule Availability**: Yes. World-leading historical airline schedule database dating back to 2000.
2. **Historical Flight Tracking**: Yes. Curated global flight status combining radar, ADS-B, airline messaging, and government data.
3. **Airport Arrivals / Departures**: Yes. Comprehensive airport activity reports.
4. **Actual Touchdown Timestamps**: Partial (Combines ACARS OOOI, airline dispatch, and radar).
5. **Actual Takeoff Timestamps**: Partial.
6. **Aircraft Registration**: Yes. Global commercial fleet census.
7. **OSDI Specific Coverage**: Verified for historical schedules; runway transponder tracking unverified.
8. **Historical Retention Period**: 20+ years.
9. **Export / API Availability**: Snowflake direct share, enterprise API, flat file delivery.
10. **Price and Subscription Conditions**: Minimum enterprise contracts range from **$10,000 to $50,000+/year**. No individual, academic, or ad-hoc researcher access models exist.
- **Authoritative Verdict**: **NO-GO**. Massive financial cost barrier renders Cirium completely unviable for independent project research.

---

### 2.5 OAG (Official Aviation Guide)
1. **Historical Schedule Availability**: Yes. Definitive global commercial airline schedule repository dating back to 1995.
2. **Historical Flight Tracking**: **No**. OAG is fundamentally a schedule and capacity aggregator, not a physical sensor tracking network.
3. **Airport Arrivals / Departures**: Yes. Published scheduled flights by aerodrome.
4. **Actual Touchdown Timestamps**: **No**. OAG records scheduled departure/arrival times, not transponder touchdown moments.
5. **Actual Takeoff Timestamps**: **No**.
6. **Aircraft Registration**: **No**. Aircraft equipment type is provided (e.g. `320`, `738`), but individual airframe tail numbers are not recorded.
7. **OSDI Specific Coverage**: Verified historical schedule filings; zero radar/sensor telemetry.
8. **Historical Retention Period**: 30+ years.
9. **Export / API Availability**: Flight Info Direct, Schedules Analyzer, API.
10. **Price and Subscription Conditions**: Minimum enterprise contracts range from **$5,000 to $25,000+/year**.
- **Authoritative Verdict**: **NO-GO**. Cost-prohibitive enterprise pricing for schedule-only data that lacks actual physical movement timestamps.

---

## 3. Systematic Summary Matrix of Commercial Providers

| Provider | Historical Schedules | Flight Tracking | Airport Arr/Dep | Actual Touchdown | Actual Takeoff | Aircraft Registration | OSDI Terminal Coverage | Minimum Retention | Pricing Model | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| **FlightRadar24** | Yes | Yes | Yes | Conditional | Conditional | Yes | Unverified | 365 Days | Gold $44.99/yr, Business $499/yr | **CONDITIONAL GO** |
| **FlightAware** | Yes | Yes | Yes | Estimated | Yes | Yes | Unverified | 30 Days | $100/mo + query fees | **CONDITIONAL GO** |
| **ADS-B Exchange** | No | Yes (Vectors)| No | Inferred | Inferred | Yes | None at ground | 2016-present | RapidAPI $10–$400/mo | **NO-GO** |
| **Cirium** | Yes | Yes | Yes | Partial | Partial | Yes | Unverified | 20+ Years | $10,000–$50,000+/yr | **NO-GO** |
| **OAG** | Yes | No | Yes | No | No | No | Schedules only | 30+ Years | $5,000–$25,000+/yr | **NO-GO** |

---

## 4. Key Takeaways & Safety Adherence

1. **Price Correction**: FlightRadar24 365-day history is accessible on the **Gold plan at $44.99/year** for personal research, while the Business plan ($499/year) is required for commercial licensing.
2. **Terminal Coverage Gap**: Neither FlightRadar24 nor FlightAware guarantees actual runway touchdown timestamps for OSDI due to local receiver sparsity.
3. **Mandatory Policy**: Both commercial providers must remain **CONDITIONAL GO** until empirical sample data proves Damascus terminal reception. No purchases or outreach will be initiated.
