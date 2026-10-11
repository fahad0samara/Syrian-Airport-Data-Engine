# Syrian Airport Data Engine — Version 2.3
# Source Evidence Register & External Provider Verification

**Document Identifier**: `docs/V2_3_SOURCE_EVIDENCE_REGISTER.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Audit Date**: 2026-10-11  
**Verification Standard**: Evidence-Based / Anti-Hallucination Audit Protocol  
**Operational Status**: STRICTLY READ-ONLY (No Database Writes, No Ingestion Executed)  

---

## 1. Executive Summary & Verification Protocol

This document provides a rigorous, evidence-based audit of all 11 external aviation data sources and statistical authorities evaluated in Version 2.2 for historical flight movement reconstruction at Damascus International Airport (`DAM` / `OSDI`).

### Anti-Hallucination & Evidence Rules
1. **General Capability ≠ Airport Coverage**: A provider possessing global historical tracking infrastructure does not establish that historical telemetry or flight events exist for `DAM` / `OSDI`.
2. **Parameter Acceptance ≠ Data Existence**: The ability of an API to return `HTTP 200 OK` or accept `airport=DAM` / `dep_icao=OSDI` without an error does not prove that operational records exist for that parameter.
3. **Confirmed Pricing Only**: Subscription prices and rate limits are reported strictly from live official pricing documentation; unconfirmed or estimated rates are flagged as contradicted or unverified.
4. **Data Classification Integrity**: Every data field is strictly categorized by observation type:
   - `observed`: Real-time physical sensor telemetry (ADS-B, Mode-S, MLAT, primary radar).
   - `estimated`: Statistically modeled or calculated timestamps (linear interpolation, standard cruise/approach speed extrapolation).
   - `scheduled`: Published commercial airline timetable intentions (OAG, Cirium, airline GDS).
   - `aggregated`: Macro statistical totals across temporal periods or multi-airport clusters.
5. **Confidence Taxonomies**:
   - `verified`: Documented by direct official primary evidence, live verified endpoints, or verified contracts.
   - `partially_verified`: Core technical capability confirmed, but specific historical `DAM` coverage, pricing tier details, or access conditions are constrained or require external validation.
   - `unverified`: Claim lacks direct accessible primary evidence, live documentation, or verified document pages.
   - `contradicted`: Claim is proven false, inaccurate, or outdated by direct official documentation or production database queries.

---

## 2. Complete Source Evidence Register

### Source 1: OpenSky Network

| Field | Verification Record |
| :--- | :--- |
| **Provider / Authority Name** | OpenSky Network Association (Switzerland) |
| **Official Documentation URL** | `https://openskynetwork.github.io/opensky-api/` and `https://opensky-network.org/data/data-tools` |
| **Exact Documentation Section** | REST API: "REST API Reference — /api/flights/departure and /api/flights/arrival"; Historical Database: "Accessing the OpenSky Historical Database via Trino" |
| **Claim Being Verified** | OpenSky provides free historical flight movement data for Damascus Airport via its standard REST API. |
| **Evidence Supporting / Refuting Claim** | Direct REST API calls to `/api/flights/departure?airport=OSDI&begin=...` for dates older than 30 days return `HTTP 403 Forbidden` for anonymous access. Registered account REST queries are strictly capped at a 1-hour time window within a rolling 30-day window. Long-term historical state vectors (>30 days back to 2013) exist exclusively in the Trino/Impala SQL big data cluster. Access to Trino requires an approved academic/non-commercial institutional research agreement. |
| **Verification Date** | 2026-10-11 |
| **Access Requirements** | Academic/institutional email required; formal written research proposal submission to OpenSky Network Association board; manual approval required for Trino SQL cluster credentials. Commercial access is not granted under academic terms. |
| **Historical Date Range Documented** | 2013 to present (via Trino/Impala cluster only). REST API: Rolling 30 days maximum. |
| **DAM / OSDI Support** | Supported syntactically (`OSDI` recognized). However, low-altitude terminal and surface ADS-B receiver coverage in Damascus is extremely sparse. Ingested state vectors in the Syrian FIR primarily represent high-altitude overflights (>25,000 ft MSL). Runway touchdowns and surface takeoffs at `OSDI` are rarely recorded by terrestrial OpenSky feeders. |
| **Actual Movement Timestamps** | Available in state vectors (epoch timestamps with nanosecond/second precision) and Trino flight tables (`firstSeen`, `lastSeen`). However, these reflect the first and last recorded ADS-B radio transmission, NOT actual runway wheels-down (`ON`) or wheels-off (`OFF`) times. |
| **Data Nature** | `observed` (raw ADS-B Mode-S transponder messages and state vectors). |
| **Licensing & Redistribution** | Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0). Redistribution or commercial deployment in closed proprietary applications is strictly restricted. |
| **Confidence Classification** | **Partially Verified** (Trino historical schema and REST 30-day limit verified; free programmatic REST historical claim contradicted; terminal coverage at `OSDI` unverified/sparse). |

---

### Source 2: AviationStack

| Field | Verification Record |
| :--- | :--- |
| **Provider / Authority Name** | AviationStack (apilayer / Idera, Inc.) |
| **Official Documentation URL** | `https://aviationstack.com/documentation` and `https://aviationstack.com/pricing` |
| **Exact Documentation Section** | "Historical Flights Endpoint (`/v1/flights?flight_date=YYYY-MM-DD`)" and "Plan Features & Pricing Matrix" |
| **Claim Being Verified** | AviationStack provides historical flight movement records for Damascus Airport back to 2019 under a standard $249.99/month Business plan. |
| **Evidence Supporting / Refuting Claim** | **CONTRADICTED on pricing and historical depth**: Official pricing matrix establishes that the Business Plan is **$499.99/month** (billed monthly) or **$424.99/month** (billed annually at $5,099.88/year). The $249.99/month figure is completely obsolete. Furthermore, official documentation explicitly states that standard historical queries on paid self-service plans are restricted to a **3-month sliding window**. Full multi-year historical archives back to 2019 require a bespoke Enterprise contract with custom pricing. |
| **Verification Date** | 2026-10-11 |
| **Access Requirements** | Paid API Access Key (Business Plan at $499.99/mo minimum for historical endpoint; Enterprise for deep archives). |
| **Historical Date Range Documented** | Standard API: 3-month sliding window. Enterprise: 2019 to present upon contractual quotation. |
| **DAM / OSDI Support** | Syntactically supported via parameters `arr_icao=OSDI` and `dep_icao=OSDI`. Historical record density is subject to airline GDS feed reporting in Syria. |
| **Actual Movement Timestamps** | Partial. Provides schema fields `departure.actual` and `arrival.actual`. However, for regional non-radar operations, these fields are frequently populated with `estimated` or duplicated `scheduled` values without physical sensor verification. |
| **Data Nature** | Composite of `scheduled` (airline schedules), `estimated` (GDS tracking), and limited `observed` (third-party feeds). |
| **Licensing & Redistribution** | Proprietary commercial license. Internal business use only; raw data resale or external redistribution is prohibited without Enterprise licensing. |
| **Confidence Classification** | **Contradicted** (Pricing claim $249.99/mo contradicted by actual $499.99/mo price; unlimited historical back to 2019 via standard API contradicted by 3-month sliding window limitation). |

---

### Source 3: Flightradar24 (FR24)

| Field | Verification Record |
| :--- | :--- |
| **Provider / Authority Name** | Flightradar24 AB (Stockholm, Sweden) |
| **Official Documentation URL** | `https://fr24.com/developer` and `https://www.flightradar24.com/premium` |
| **Exact Documentation Section** | Developer Portal: "Flightradar24 Developer API Documentation — Historic Flight Data API"; Subscription Portal: "Premium Web Accounts" |
| **Claim Being Verified** | Flightradar24 offers programmatic historical movement access via its Developer API, while consumer web tiers allow low-cost scraping. |
| **Evidence Supporting / Refuting Claim** | Programmatic historical data is strictly governed by the Developer REST API. Official tiers: **Explorer** ($9/mo, 30 days history, 10,000 credits), **Essential** ($90/mo, 2 years history, 100,000 credits), **Advanced** ($900/mo, unlimited history back to May 2016, 1,000,000 credits). Web consumer plans (Silver $1.49/mo, Gold $3.99/mo, Business $49.99/mo) explicitly forbid automated data extraction, scripting, or scraping under Section 8 of the Flightradar24 Terms of Service. |
| **Verification Date** | 2026-10-11 |
| **Access Requirements** | Developer API Key (Essential tier at $90/mo required for 2024–2026 historical dates; Advanced at $900/mo for pre-2024). |
| **Historical Date Range Documented** | Essential: 2-year sliding window. Advanced: May 2016 to present. |
| **DAM / OSDI Support** | Fully supported. FR24 possesses the most extensive crowdsourced and satellite ADS-B receiver coverage in the Middle East. Flights to/from `DAM` / `OSDI` (Syrian Air, Cham Wings, Fly Baghdad, Mahan Air, etc.) are captured when transponders operate. |
| **Actual Movement Timestamps** | Available (`actual_takeoff_time`, `actual_landing_time` derived from MLAT/ADS-B altitude profiles down to runway threshold). |
| **Data Nature** | `observed` (terrestrial ADS-B, Mode-S, MLAT, and satellite ADS-B). |
| **Licensing & Redistribution** | Proprietary commercial developer license. API access permits internal application use; public redistribution of bulk historical data is restricted. Consumer screen-scraping violates legal terms. |
| **Confidence Classification** | **Verified** (Developer API pricing tiers, history windows, and programmatic terms verified; consumer scraping claims contradicted by legal terms). |

---

### Source 4: FlightAware (AeroAPI v4)

| Field | Verification Record |
| :--- | :--- |
| **Provider / Authority Name** | FlightAware LLC (Collins Aerospace / RTX) |
| **Official Documentation URL** | `https://www.flightaware.com/commercial/aeroapi/` and `https://flightaware.com/commercial/aeroapi/pricing` |
| **Exact Documentation Section** | "AeroAPI v4 Reference — `/airports/{id}/flights`" and "Pricing Schedule" |
| **Claim Being Verified** | FlightAware AeroAPI provides historical flight movement records for Damascus Airport under a free or low-cost self-service tier. |
| **Evidence Supporting / Refuting Claim** | Official AeroAPI pricing confirms three tiers: **Personal** ($0/mo base, $0.005/query, strictly **0 days of history** — live and future scheduled only); **Standard** ($100/mo minimum spend, historical queries up to 30 days); **Premium** ($1,000/mo minimum spend, extended historical queries). Multi-year historical flight data for 2024–2026 requires custom Enterprise contracting. |
| **Verification Date** | 2026-10-11 |
| **Access Requirements** | Commercial AeroAPI Contract. Minimum $100/mo spend for rolling 30 days; Enterprise quote for historical bulk archives back to 2024. |
| **Historical Date Range Documented** | Personal: 0 days (live only). Standard: 30 days. Enterprise: Historical archives back to 2011. |
| **DAM / OSDI Support** | Fully supported (`OSDI`). Enhanced by space-based Aireon 1090MHz ADS-B payloads hosted on the Iridium NEXT satellite constellation, providing continuous en-route coverage over Syria regardless of local terrestrial receiver stations. |
| **Actual Movement Timestamps** | Full OOOI timestamps (`gate_out`, `wheels_off`, `wheels_on`, `gate_in`) where reported; runway `wheels_on` / `wheels_off` calculated from satellite/terrestrial ADS-B position reports. |
| **Data Nature** | `observed` (space-based and terrestrial ADS-B) combined with ANSP and airline flight operational feeds. |
| **Licensing & Redistribution** | Commercial proprietary license. Strict contractual prohibitions on unauthorized redistribution or public repository publishing. |
| **Confidence Classification** | **Verified** (AeroAPI pricing structure and historical minimums verified; low-cost self-service historical claim contradicted). |

---

### Source 5: ADS-B Exchange (ADSBx)

| Field | Verification Record |
| :--- | :--- |
| **Provider / Authority Name** | ADS-B Exchange (Jetnet, LLC) |
| **Official Documentation URL** | `https://www.adsbexchange.com/` and `https://www.adsbexchange.com/data-samples/` |
| **Exact Documentation Section** | "API Documentation", "Data Samples", and "Enterprise Historical Replay Services" |
| **Claim Being Verified** | ADS-B Exchange provides open, unfeeder-censored historical telemetry tracking Damascus Airport runway movements. |
| **Evidence Supporting / Refuting Claim** | ADSBx is renowned for unfiltered data (no aircraft blocking/censoring). However, access to historical query APIs is commercialized via RapidAPI and Jetnet Enterprise. Crucially, ADSBx relies on terrestrial crowdsourced receivers. While high-altitude overflights (>25,000 ft) over Syrian airspace are recorded by border feeders in Lebanon, Jordan, and Cyprus, ground-level reception at `OSDI` (airport elevation 2,020 ft MSL) requires line-of-sight receivers within Damascus. Historical receiver density in Damascus has been near-zero. |
| **Verification Date** | 2026-10-11 |
| **Access Requirements** | Commercial subscription via RapidAPI (usage-based) or Jetnet Enterprise agreement for historical raw trace downloads. |
| **Historical Date Range Documented** | Historical daily raw archive files available from 2016 to present (bulk JSON tarballs). |
| **DAM / OSDI Support** | Syrian airspace supported for high-altitude overflights. Terminal approach and runway touchdown coverage at `OSDI` is unverified and empirically missing for most regional dates due to lack of local terrestrial feeders. |
| **Actual Movement Timestamps** | Raw telemetry contains epoch seconds for received messages. However, runway touchdown/takeoff events are not synthesized by ADSBx; user must reconstruct trajectories. |
| **Data Nature** | `observed` (unfiltered Mode-S and ADS-B messages). |
| **Licensing & Redistribution** | Commercial proprietary terms (Jetnet). Scraping or unauthorized mirroring is strictly prohibited. |
| **Confidence Classification** | **Partially Verified** (Platform capability and raw archive structure verified; terminal/runway coverage for `DAM` unverified and physically constrained by feeder topology). |

---

### Source 6: Syrian Civil Aviation Authority (SCAA)

| Field | Verification Record |
| :--- | :--- |
| **Provider / Authority Name** | Syrian Civil Aviation Authority (المؤسسة العامة للطيران المدني السوري) |
| **Official Documentation URL** | `http://scaa.sy/` and `https://gaca.gov.sy/` (eAIP portal) |
| **Exact Documentation Section** | "Aeronautical Information Publication (AIP)", "NOTAM Office", and "Civil Aviation Law No. 33" |
| **Claim Being Verified** | SCAA provides an automated API or downloadable electronic dataset of daily historical flight movements for Damascus Airport. |
| **Evidence Supporting / Refuting Claim** | Direct inspection of SCAA and eAIP portals confirms that SCAA publishes statutory regulatory documents, Aeronautical Information Publications (AIP Syria), airport charts, and NOTAMs (e.g. runway closures, airspace restrictions). SCAA does **NOT** maintain a public operational API, electronic daily flight movements archive, or downloadable time-series CSV/JSON files. Operational movement statistics are compiled internally for government reporting and released only as periodic macro press summaries. |
| **Verification Date** | 2026-10-11 |
| **Access Requirements** | AIP and NOTAM portals require registered aviation user access or public navigation query. No flight movement API exists. |
| **Historical Date Range Documented** | AIP and NOTAMs: Current and immediate historical archive (1–2 years). Daily flight logs: Not published publicly. |
| **DAM / OSDI Support** | Primary sovereign aerodrome of authority. |
| **Actual Movement Timestamps** | Not available via public digital channels. |
| **Data Nature** | `aggregated` (press releases) and statutory operational notices (NOTAMs). |
| **Licensing & Redistribution** | Official government sovereign property (Syrian Arab Republic). |
| **Confidence Classification** | **Verified** (Legal authority, institutional mandate, and NOTAM/eAIP portals verified; electronic historical flight movement API contradicted/non-existent). |

---

### Source 7: Syrian Ministry of Transport (MoT)

| Field | Verification Record |
| :--- | :--- |
| **Provider / Authority Name** | Ministry of Transport — Syrian Arab Republic (وزارة النقل - الجمهورية العربية السورية) |
| **Official Documentation URL** | `http://mot.gov.sy/` |
| **Exact Documentation Section** | "Civil Aviation Sector Overview" and "Annual Transport Sector Performance Reports" |
| **Claim Being Verified** | The Syrian Ministry of Transport publishes daily flight event databases for Damascus International Airport. |
| **Evidence Supporting / Refuting Claim** | MoT is the cabinet-level ministry overseeing civil aviation, maritime, and land transport. Inspection of official ministerial portals confirms that MoT publishes quarterly and annual macro reports summarizing total passenger counts, air cargo volumes, and aggregate flight movements across Syrian airports. MoT does **NOT** publish individual daily flight movement records, callsign-level logs, or queryable APIs. |
| **Verification Date** | 2026-10-11 |
| **Access Requirements** | Public government website access. |
| **Historical Date Range Documented** | Annual reports covering select calendar years (e.g. 2018–2023 summary totals). |
| **DAM / OSDI Support** | Aggregated across national airports (Damascus, Aleppo, Latakia, Qamishli). |
| **Actual Movement Timestamps** | Not available. |
| **Data Nature** | `aggregated` (annual and quarterly macro statistics). |
| **Licensing & Redistribution** | Syrian government public information. |
| **Confidence Classification** | **Verified** (Ministerial authority and annual macro reporting verified; daily flight movement API contradicted). |

---

### Source 8: Syrian Central Bureau of Statistics (CBS)

| Field | Verification Record |
| :--- | :--- |
| **Provider / Authority Name** | Central Bureau of Statistics — Syrian Arab Republic (المكتب المركزي للإحصاء) |
| **Official Documentation URL** | `http://cbssyr.sy/` |
| **Exact Documentation Section** | "Annual Statistical Abstract (المجموعة الإحصائية السنوية) — Chapter 10: Transport and Communications (النقل والمواصلات)" |
| **Claim Being Verified** | CBS Annual Statistical Abstract Chapter 10 provides detailed, airport-specific annual and monthly breakdowns of aircraft movements, passenger arrivals/departures, and cargo for Damascus International Airport. |
| **Evidence Supporting / Refuting Claim** | CBS is the official national statistical office of Syria. It compiles the Annual Statistical Abstract. While historical abstracts prior to 2011 contained detailed aerodrome-level tables (e.g. aircraft movements, passengers, and freight at Damascus, Aleppo, and Latakia), the exact table numbers, page numbers, and whether airport-specific breakdowns are published for recent years (2020–2024) **cannot be confirmed** without direct inspection of the specific printed or PDF volumes. Consequently, any specific claim regarding recent Chapter 10 table numbers (e.g., "Table 10/4") or page ranges must remain classified as **unverified**. |
| **Verification Date** | 2026-10-11 |
| **Access Requirements** | Official CBS portal download or official library acquisition. |
| **Historical Date Range Documented** | Annual abstracts published intermittently from the 1970s through early 2020s. |
| **DAM / OSDI Support** | Historically supported as national aggregate and major gateway. Recent year airport-level granularity is unverified. |
| **Actual Movement Timestamps** | None (annual and monthly macro summaries only). |
| **Data Nature** | `aggregated` (macro annual statistical tables). |
| **Licensing & Redistribution** | Official statistical publication of the Syrian Arab Republic. |
| **Confidence Classification** | **Partially Verified / Unverified Specifics** (Institutional mandate and publication of Chapter 10 Transport verified; specific recent table numbers, page numbers, and Damascus-specific granularity unverified). |

---

### Source 9: Syria Economic Monitor (SEM) / World Bank

| Field | Verification Record |
| :--- | :--- |
| **Provider / Authority Name** | The World Bank Group (Middle East and North Africa Region) |
| **Official Documentation URL** | `https://www.worldbank.org/en/country/syria/publication/syria-economic-monitor` |
| **Exact Documentation Section** | Semi-annual economic report series and associated aviation activity indicators (derived from World Bank research datasets). |
| **Claim Being Verified** | The SEM dataset in the repository represents daily Damascus International Airport flight movements and establishes an OpenSky outage baseline. |
| **Evidence Supporting / Refuting Claim** | **CONTRADICTED**: Direct inspection of the production database table `historical_daily_movements_2024` (578 rows) reveals that every single record is explicitly assigned `scope = 'DAM_ALP_LTK'` with description *"Aggregated gateway operations across Syria (Damascus, Aleppo, Latakia)"*. The underlying source is recorded as *"Syria Economic Monitor (AviationStack purchase, DAM_ALP_LTK)"*. The World Bank research team purchased aggregate national gateway flight counts from AviationStack. It is impossible to isolate `DAM` movements from this aggregate without introducing arbitrary assumptions. Furthermore, query of the 15 zero-operation rows establishes the actual data gap dates as Jan 28–30, Apr 29–30, and Jun 7–9 (the claim that Jan 20–23 were pilot gap dates is completely contradicted). |
| **Verification Date** | 2026-10-11 |
| **Access Requirements** | Public World Bank publication access; raw dataset embedded in repository migration `v2.0_historical_benchmarks`. |
| **Historical Date Range Documented** | 2024-01-01 to 2024-10-15 (289 calendar days, 578 arrival/departure rows). |
| **DAM / OSDI Support** | **Not airport-specific**. Composite aggregate of three airports (`DAM`, `ALP`, `LTK`). |
| **Actual Movement Timestamps** | None (daily integer count aggregates). |
| **Data Nature** | `aggregated` (daily total operations by movement category). |
| **Licensing & Redistribution** | World Bank Open Data terms (CC BY 4.0). Internal research reuse permitted. |
| **Confidence Classification** | **Contradicted as a DAM-specific benchmark**; **Verified as a multi-airport aggregate macro series**. |

---

### Source 10: ICAO Data+ (International Civil Aviation Organization)

| Field | Verification Record |
| :--- | :--- |
| **Provider / Authority Name** | International Civil Aviation Organization (ICAO, UN Specialized Agency) |
| **Official Documentation URL** | `https://www.icao.int/dataplus/` and `https://applications.icao.int/dataservices/` |
| **Exact Documentation Section** | "ICAO Data+ — Airport Traffic Module (Air Transport Reporting Form IS-1)" |
| **Claim Being Verified** | ICAO Data+ provides verified daily physical flight movement records for Damascus International Airport. |
| **Evidence Supporting / Refuting Claim** | ICAO Data+ compiles official statistical returns submitted by Contracting States under the Chicago Convention. The Airport Traffic module (Form IS-1) collects monthly and annual commercial aircraft movements, passenger traffic, and cargo. It does **NOT** record individual flight events, callsigns, or daily timestamps. Furthermore, Syrian state statistical reporting to ICAO has experienced substantial multi-year reporting delays and gaps since 2011. |
| **Verification Date** | 2026-10-11 |
| **Access Requirements** | Paid commercial subscription / institutional license to ICAO Data+ platform. |
| **Historical Date Range Documented** | Historical annual and monthly data extending over several decades, subject to national reporting compliance. |
| **DAM / OSDI Support** | Supported in reporting nomenclature (`OSDI` / `DAM`). |
| **Actual Movement Timestamps** | None (monthly and annual macro totals only). |
| **Data Nature** | `aggregated` (official macro statistical returns). |
| **Licensing & Redistribution** | ICAO proprietary copyright. Commercial subscription prohibits redistribution. |
| **Confidence Classification** | **Partially Verified** (Platform capability and Form IS-1 schema verified; daily movement availability contradicted; recent Syrian reporting regularity unverified). |

---

### Source 11: OurAirports

| Field | Verification Record |
| :--- | :--- |
| **Provider / Authority Name** | OurAirports (Megawhat Ventures / Community-Maintained) |
| **Official Documentation URL** | `https://ourairports.com/data/` |
| **Exact Documentation Section** | "OurAirports Open Data Downloads — `airports.csv`, `runways.csv`, `airport-frequencies.csv`" |
| **Claim Being Verified** | OurAirports provides historical operational flight tracking or aircraft movement records for Damascus International Airport. |
| **Evidence Supporting / Refuting Claim** | **CONTRADICTED for flight movements**: Direct inspection of OurAirports data exports confirms that OurAirports is exclusively a **static aeronautical reference directory**. It contains aerodrome metadata for `OSDI` / `DAM` (coordinates: Lat 33.4150, Lon 36.5156; elevation: 2,020 ft MSL; runways: 05R/23L, 05L/23R; tower/approach radio frequencies). It does **NOT** record, ingest, or export any historical flight movements, time-series operations, or passenger statistics. |
| **Verification Date** | 2026-10-11 |
| **Access Requirements** | Open access (Public Domain / Creative Commons 0). Direct CSV downloads. |
| **Historical Date Range Documented** | Current aerodrome reference infrastructure (updated periodically by community volunteers). |
| **DAM / OSDI Support** | Aerodrome metadata fully present (`ident: OSDI`, `iata_code: DAM`, `name: Damascus International Airport`). |
| **Actual Movement Timestamps** | Completely absent. |
| **Data Nature** | Static geospatial and infrastructural reference metadata. |
| **Licensing & Redistribution** | Public Domain (Creative Commons CC0 1.0). Unrestricted reuse. |
| **Confidence Classification** | **Verified for static reference data**; **Contradicted for operational flight movement tracking**. |

---

## 3. Comparative Source Evidence Matrix

| Provider / Authority | Movement Tracking Nature | Historical Range | DAM Specificity | Timestamps Available | Access Status / Commercial Tier | Confidence Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **OpenSky Network** | `observed` (ADS-B) | 2013–Pres (Trino) | En-route only (Sparse surface) | Raw message epoch | Academic Research Agreement Required | **Partially Verified** |
| **AviationStack** | `scheduled` / `estimated` | 3-Mo sliding (Std) | Parameter filter | Partial / unverified actuals | Business ($499.99/mo) / Enterprise | **Contradicted** (Price/Depth) |
| **Flightradar24** | `observed` (ADS-B/MLAT) | May 2016–Pres | High (Regional receivers/sat) | Exact ATD/ATA | Essential ($90/mo) / Advanced ($900/mo) | **Verified** |
| **FlightAware** | `observed` / `scheduled` | 2011–Pres (Ent) | High (Space-based ADS-B) | Exact OOOI | Standard ($100/mo) / Enterprise | **Verified** |
| **ADS-B Exchange** | `observed` (Unfiltered) | 2016–Pres (Raw) | En-route only (Sparse surface) | Raw message epoch | Jetnet Commercial Agreement | **Partially Verified** |
| **Syrian Civil Aviation** | Statutory notices / AIP | Current / periodic | Primary authority | None (NOTAM times only) | Public portal / No digital movement API | **Verified** (No API) |
| **Syrian MoT** | `aggregated` (Macro) | Annual / quarterly | National aggregate | None | Public government portal | **Verified** (Macro only) |
| **Syrian CBS** | `aggregated` (Macro) | Multi-decade annual | Historical only | None | Public government publication | **Partially Verified** |
| **Syria Economic Mon.** | `aggregated` (Macro) | 2024-01 to 2024-10 | Composite (`DAM_ALP_LTK`) | None | Open Data (Repository embedded) | **Contradicted** (DAM specific) |
| **ICAO Data+** | `aggregated` (Macro) | Annual/monthly lag | National / airport returns | None | Paid subscription | **Partially Verified** |
| **OurAirports** | Static infrastructure | Current state | Complete metadata | None | Public Domain (CC0) | **Verified** (Static only) |
