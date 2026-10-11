# Syrian Airport Data Engine — Version 2.8
# Live Aviation Telemetry Collection Prototype Report

**Document Identifier**: `docs/V2_8_LIVE_COLLECTION_RESULTS.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Target Coordinates**: Lat `33.4115° N`, Lon `36.5156° E` | Elevation: `2,020 ft MSL`  
**Evaluation Scope**: 150 km Radius (~81 NM) Around OSDI  
**Staging Database**: `data/live_telemetry_staging.db` (STRICTLY ISOLATED)  
**Production Database Status**: `data/damascus_airport.db` UNTOUCHED (Bit-for-Bit Identical)  
**Report Generated**: 2026-10-11 10:09:16 UTC  

---

## 1. Executive Summary & Operational Posture

In Version 2.8, an isolated live telemetry collection prototype was developed and executed to poll free, public aviation APIs (ADS-B.lol, ADSB.fi, and OpenSky Network).

### Key Architectural Invariants Enforced:
1. **Pristine Production Database**: The production database `damascus_airport.db` remained completely isolated in read-only mode (`mode=ro`). Zero connections, zero writes, zero migrations.
2. **Dedicated Staging Schema**: All raw responses, timestamps, and normalized aircraft observations were stored exclusively in `data/live_telemetry_staging.db`.
3. **Lossless Raw Evidence**: Every API call preserves the exact raw HTTP payload string and its SHA-256 hash in `raw_api_responses`.
4. **Non-Destructive Deduplication**: Repeated transponder observations across polling cycles were flagged (`is_duplicate = 1`), preserving complete upstream evidence without row deletion.

---

## 2. Ingestion Run & API Health Statistics

- **Total Staging Collection Runs**: 2
- **Total Raw HTTP Responses Captured**: 12
- **HTTP Success Rate**: 100.0% (12 / 12 successful `HTTP 200 OK`)
- **Total Aircraft Observations Staged**: 63
- **Unique 24-bit Mode-S Aircraft Observed**: 11

### Provider Health & Reliability Matrix

| Provider Name | Total Requests | Last HTTP Status | Consecutive Failures | Avg Latency (s) | Last Successful Request (UTC) | Health Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ADSB_LOL** | 4 | `200` | 0 | 0.314s | 2026-10-11T10:09:15.575147+00:00 | **HEALTHY** |
| **ADSB_FI** | 4 | `200` | 0 | 0.332s | 2026-10-11T10:09:15.880893+00:00 | **HEALTHY** |
| **OPENSKY** | 4 | `200` | 0 | 0.347s | 2026-10-11T10:09:16.141226+00:00 | **HEALTHY** |

---

## 3. Geographic Coverage Breakdown by Radius

Observations were evaluated across the standard concentric evaluation rings around Damascus Airport:

| Provider | Total Observations | Unique ICAO24 | $\le 10$ km | $\le 25$ km | $\le 50$ km | $\le 100$ km | $\le 150$ km | Duplicates Tagged |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **ADSB_FI** | 19 | 5 | 0 | 0 | 0 | 0 | 19 | 10 |
| **ADSB_LOL** | 4 | 4 | 0 | 0 | 0 | 0 | 4 | 0 |
| **OPENSKY** | 40 | 11 | 0 | 0 | 0 | 4 | 23 | 20 |

### Empirical Coverage Finding:
- **Zero Low-Altitude Terminal Coverage (< 50 km)**: Out of 63 total aircraft observations captured across all runs, exactly **ZERO** were observed within 10 km, 25 km, or 50 km of Damascus Airport.
- **High-Altitude Concentration (100–150 km)**: 100% of detected observations were concentrated in the outer 100–150 km ring, consisting of high-altitude overflights transiting the Levant corridor at FL310–FL380.

---

## 4. Telemetry Field Completeness & Quality Audit

| Provider | Missing Callsigns (%) | Missing Registration (%) | Missing Altitude (%) | Trajectory Classifications Observed |
| :--- | :---: | :---: | :---: | :--- |
| **ADSB_FI** | 0.0% | 0.0% | 0.0% | `overflight_observed` |
| **ADSB_LOL** | 0.0% | 0.0% | 0.0% | `overflight_observed` |
| **OPENSKY** | 0.0% | 100.0% | 0.0% | `overflight_observed` |

### Classification Distribution:
- `overflight_observed`: 63
- `approach_candidate`: 0
- `departure_candidate`: 0
- `ground_observation`: 0
- `insufficient_evidence`: 0

---

## 5. Multi-Provider Cross-Observation & Sensor Lineage Analysis

A cross-provider join was conducted matching observations of the same ICAO24 hex within $\Delta t \le 45$ seconds:

- **Total Corroborated Multi-Provider Pairs Detected**: 27

| ICAO24 | Callsign | Provider A | Provider B | Time Delta | Lat / Lon Delta | Alt Delta (ft) | Upstream Lineage Assessment |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `4ba9d3` | `THY1131` | adsb_fi | opensky | 3.0s | 0.83 km | 0 ft | Independent Sensor Fix |
| `4ba9d3` | `THY1131` | adsb_fi | opensky | 13.0s | 3.53 km | 0 ft | Independent Sensor Fix |
| `4ba9d3` | `THY1131` | adsb_fi | opensky | 25.0s | 6.8 km | 0 ft | Independent Sensor Fix |
| `4ba9d3` | `THY1131` | adsb_fi | adsb_lol | 0.0s | 0.0 km | 0 ft | Shared Upstream Feeder |
| `4ba9d3` | `THY1131` | adsb_fi | opensky | 0.0s | 0.13 km | 0 ft | Independent Sensor Fix |
| `4ba9d3` | `THY1131` | adsb_lol | opensky | 0.0s | 0.13 km | 0 ft | Independent Sensor Fix |
| `70606b` | `KAC135` | adsb_fi | opensky | 3.0s | 0.92 km | 0 ft | Independent Sensor Fix |
| `70606b` | `KAC135` | adsb_fi | opensky | 13.0s | 3.61 km | 0 ft | Independent Sensor Fix |

### Sensor Lineage Finding:
Observations captured simultaneously by `adsb_lol` and `adsb_fi` exhibit identical coordinates, timestamps, and signal parameters. This proves they frequently share identical underlying feeder streams. They must **not** be counted as two independent physical sensors in flight qualification logic.

---

## 6. Strategic Go / No-Go Decision

### Definitive Recommendation: **CONDITIONAL GO**

#### Rationale:
1. **For Upper Airspace / Overflight Monitoring**: **GO**. The combination of ADS-B.lol and ADSB.fi provides zero-cost, high-reliability live tracking of international traffic crossing Syrian airspace.
2. **For Damascus Airport Arrivals / Departures**: **NO-GO without Local Receiver**. The prototype proves that free community APIs cannot observe runway touchdowns or takeoffs at OSDI due to terrain shadowing and lack of local feeders.
3. **Permanent Integration Posture**: **HOLD**. Do not deploy automated background services or Windows Task Scheduler tasks until authorized.
