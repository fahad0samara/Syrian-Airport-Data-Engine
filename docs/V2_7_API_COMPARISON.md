# Syrian Airport Data Engine — Version 2.7
# Comprehensive Aviation API Comparison & Technical Evaluation

**Document Identifier**: `docs/V2_7_API_COMPARISON.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Audit Date**: 2026-10-11  
**Target Standard**: Empirical Test Findings & Verified Official Documentation  
**Status**: APPROVED SPECIFICATION  

---

## 1. Executive Summary

This document presents a side-by-side technical, evidentiary, and operational comparison of all candidate aviation data APIs evaluated for Damascus International Airport (`DAM` / `OSDI`). Every evaluation metric is grounded in actual live test results executed on 2026-10-11 or cited directly from official provider documentation.

---

## 2. Side-by-Side API Comparison Table

| Field | OpenSky Network | ADS-B.lol | ADSB.fi | Airplanes.live | Flightradar24 | FlightAware | AviationStack |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Provider** | OpenSky Network | adsb.lol | ADSB.fi | Airplanes.live | Flightradar24 AB | FlightAware (Collins) | apilayer / Idera |
| **Free Access** | **Yes** (Free REST & Trino) | **Yes** (100% Free) | **Yes** (100% Free) | **Limited** (Gated) | **Limited** (No free API) | **Limited** (Live only) | **Limited** (Free 100 req) |
| **Authentication** | Optional (Anon) / Basic Auth | **None** | **None** | Email Whitelist | Required (API Key) | Required (API Key) | Required (API Key) |
| **Live Observations** | **Available** | **Available** | **Available** | Unavailable (HTTP 403) | Available (Paid) | Available (Standard) | Available (Paid/Free) |
| **Historical Observations**| **Restricted** (30d REST / Trino App) | **Unavailable** (Live only) | **Unavailable** (Live only) | **Unavailable** (Gated) | **Available** (Essential/Adv) | **Available** (Enterprise) | **Restricted** (3-mo limit) |
| **OSDI Coverage (Empirical)**| 0 within 50 km; 6 within 150 km | 0 within 50 km; 4 within 150 km | 0 within 50 km; 4 within 150 km | 0 (HTTP 403 Forbidden) | Documented High (Radar/Sat) | Documented High (Aireon) | Syntactic Filter Only |
| **ICAO24** | **Available** (100% valid hex) | **Available** (100% valid hex) | **Available** (100% valid hex) | Missing (HTTP 403) | Available | Available | Incomplete / Missing |
| **Callsign** | **Available** (100% trimmed) | **Available** (100% trimmed) | **Available** (100% trimmed) | Missing (HTTP 403) | Available | Available | Available (Scheduled) |
| **Position (Lat/Lon)** | **Available** (High precision) | **Available** (High precision) | **Available** (High precision) | Missing (HTTP 403) | Available | Available | Missing in Free/Basic |
| **Altitude** | **Available** (Baro & Geo ft) | **Available** (Baro & Geom ft) | **Available** (Baro & Geom ft) | Missing (HTTP 403) | Available | Available | Missing in Basic |
| **Timestamp** | **Available** (Epoch seconds) | **Available** (Epoch seconds) | **Available** (Epoch seconds) | Missing (HTTP 403) | Available (ATD/ATA) | Available (OOOI) | Available (Scheduled/Est) |
| **Rate Limits** | 1 req/10s (Anon), 1 req/5s (Reg) | Fair-use (~1 req/sec) | Fair-use (~1 req/sec) | Undocumented (Gated) | Tiered (100k–1M credits/mo)| Tiered ($100/mo min) | 100/mo (Free), 250k (Bus) |
| **License** | CC BY-NC 4.0 (Non-commercial) | Open community data | Open Data Commons | Community policy | Proprietary commercial | Proprietary commercial | Proprietary commercial |
| **Integration Priority**| **High** (Live + Trino App) | **High** (Live Poller) | **High** (Live Backup) | **Low** (Disqualified / 403) | **Medium** (Commercial quote) | **Medium** (Commercial quote) | **Low** (Disqualified) |

---

## 3. Reliability & Architectural Trade-off Analysis

### 3.1 Tier 1: Zero-Cost Live Open Ingestion Core (`ADS-B.lol` + `ADSB.fi`)
* **Strengths**:
  - Completely open without authentication tokens, keys, or registration hurdles.
  - Native `readsb` schema delivering full flight physics: 24-bit ICAO24 hex, callsign, tail registration, aircraft type, calibrated barometric altitude, geometric altitude, groundspeed, true track, vertical rate, squawk code, and receiver signal RSSI.
  - Generous rate limits (~1 query/second) allow continuous background polling without incurring financial cost.
  - Dual redundancy: If `adsb.lol` experiences downtime or network throttling, `ADSB.fi` provides an identical, drop-in replacement schema.
* **Limitations**:
  - Strictly real-time; **zero historical query endpoints**.
  - Current ground-level receiver deficit at Damascus means observations in the 0–50 km radius will be zero until a local feeder is established or an aircraft operates with sufficient altitude to clear the Lebanese mountain horizon.
* **Architectural Role**: Recommended as the primary zero-cost real-time continuous ingestion pipeline for forward accumulation.

---

### 3.2 Tier 2: Scientific Research & Deep Historical Anchor (`OpenSky Network`)
* **Strengths**:
  - Only open network with an indexed multi-petabyte historical state vector database (`state_vectors_data4`) dating back to 2013.
  - Rigorous scientific provenance backed by the OpenSky Network Association (Switzerland).
  - Clean anonymous REST API supporting geographic bounding box filtering.
* **Limitations**:
  - REST API is hard-capped at 30 days history; multi-year historical queries strictly require approved institutional academic credentials.
  - In anonymous mode, rate limits are restricted to 1 query per 10 seconds.
  - Terrestrial receiver coverage in Damascus terminal airspace is sparse.
* **Architectural Role**: Recommended for academic research access to query historical 2024–2026 state vectors via Trino once institutional credentials are approved.

---

### 3.3 Tier 3: Commercial Ground-Truth Escalation (`Flightradar24` & `FlightAware`)
* **Strengths**:
  - Commercial terrestrial receiver networks supplemented by space-based satellite ADS-B (Aireon on Iridium NEXT) provide the only verified continuous coverage of Syrian airspace down to aerodrome levels.
  - Verified `actual` takeoff (ATD) and landing (ATA) timestamps with complete tail registrations.
* **Limitations**:
  - High financial cost: $90/mo to $900/mo (FR24) or $100/mo minimum spend to bespoke enterprise contracting (FlightAware).
  - Strict commercial licensing: redistribution of raw feeds prohibited.
* **Architectural Role**: Retained for commercial proof-of-availability sampling and historical ground-truth corroboration if free telemetry proves insufficient.

---

### 3.4 Tier 4: Disqualified Sources (`Airplanes.live`, `ADSB.one`, `AviationStack`)
* **Airplanes.live**: Disqualified due to an automated `HTTP 403 Forbidden` access barrier requiring manual project whitelist emails.
* **ADSB.one**: Disqualified due to Cloudflare bot protection blocking automated requests.
* **AviationStack**: Disqualified due to a $499.99/mo Business tier enforcing a 3-month sliding window limitation that blocks 2024 historical access, combined with a lack of physical telemetry provenance.
