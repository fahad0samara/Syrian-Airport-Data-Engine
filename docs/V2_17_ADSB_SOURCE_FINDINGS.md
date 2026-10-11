# V2.17 — Track B: Historical ADS-B Aircraft Observation Research

## 1. Executive Summary

Track B of Version 2.17 investigated the feasibility, access tiers, and empirical data availability of public ADS-B aircraft observation sources covering the Damascus International Airport airspace (**OSDI** / **DAM**):
- Reference Coordinates: `33.4115° N, 36.5156° E`
- Airfield Elevation: `2,020 ft AMSL`
- Timezone: `Asia/Damascus`
- Target Historical Period: `2024-01-01` to present.

The research evaluated four (4) major public flight-tracking services: **OpenSky Network**, **ADS-B.lol**, **ADSB.fi**, and **Airplanes.live**.

---

## 2. Source Access Classification Matrix

Under the V2.17 requirements, aviation telemetry sources must be rigorously classified into clear operational and legal access tiers:

| Provider | Service / Endpoint | Access Tier | Historical API Available? | Unauthenticated Result (DAM 2024–Present) | Cost Classification | Terms & Authentication Requirements |
|---|---|---|---|---|---|---|
| **OpenSky Network** | `api/states/all` (Live) | Free Anonymous Live | No (Live stream only) | **HTTP 200 OK** (Returns current live regional vectors) | Free Public | Anonymous rate limit: 1 req / 10s. |
| **OpenSky Network** | `api/flights/arrival`, `api/flights/departure`, `api/states/all?time=...` | Restricted Academic / Research Database | Yes, but restricted to authenticated research accounts | **HTTP 403 Forbidden** (`"Authenticate to get historical data"`, `"You cannot access historical flights"`) | Free Academic with formal institutional review | Account creation and research application required (strictly prohibited by V2.17 prompt). |
| **ADS-B.lol** | `api/v2/point/{lat}/{lon}/{rad}` (Live) | Free Community Live | No (Live point only) | **HTTP 200 OK** (Returns live aircraft within 81 nm) | Free Open Data | Community fair-use policy. |
| **ADS-B.lol** | `api/v2/history/point/...` | Bulk Global Archive | No per-point historical query API | **HTTP 503 Service Unavailable** (Endpoint not implemented) | Free Bulk Download | Unfiltered global daily tarballs hosted on cloud storage; no coordinate-query API. |
| **ADSB.fi** | `api/v2/lat/{lat}/lon/{lon}/dist/{rad}` (Live) | Free Community Live | No (Live point only) | **HTTP 200 OK** (Returns live aircraft within 81 nm) | Free Open Data | Open data community project. |
| **ADSB.fi** | `api/v2/history/...` | Unsupported | No historical service | **HTTP 400 Bad Request** | Free | No historical API available. |
| **Airplanes.live** | `api/v2/point/{lat}/{lon}/{rad}` | Free Community Live | No (Live point only) | **HTTP 200 OK** (Returns live aircraft within 81 nm) | Free Open Data | Live telemetry only. |

### Key Research Finding
**No public, unauthenticated, free API exists that allows historical coordinate-filtered ADS-B observation queries for Damascus International Airport.**
- OpenSky Network strictly restricts historical queries older than 1 hour to registered/approved accounts (returning HTTP 403). Under project constraints, creating accounts or submitting research applications is prohibited.
- Community networks (ADS-B.lol, ADSB.fi) do not operate per-point historical query APIs. ADS-B.lol offers multi-terabyte bulk global archive tarballs, but lacks an airport-specific historical query service.

---

## 3. Empirical Test Findings & Raw Provenance

Live API queries against the Damascus airspace (81 nm / 150 km radius) were conducted on `2026-10-11` and stored with cryptographic SHA-256 provenance in `data/raw/adsb/v2_17/`:

| Raw File | Provider | Query Endpoint | HTTP Status | File SHA-256 | Description |
|---|---|---|---|---|---|
| `adsb_lol_live_damascus_150km.json` | ADS-B.lol | `/v2/point/33.4115/36.5156/81` | 200 OK | `8d3db200a09f9827c9e2defe135d887701ee84fef3bd78f3682fd971cf754ba9` | 9 live aircraft detected in 150 km radius |
| `adsb_fi_live_damascus_150km.json` | ADSB.fi | `/api/v2/lat/33.4115/lon/36.5156/dist/81` | 200 OK | `6bb9c9669acd9931baee88ba38b533a0632f3bc3f62e507360ce62fba85b008a` | 7 live aircraft detected in 150 km radius |
| `opensky_live_damascus_region.json` | OpenSky Network | `/api/states/all?lamin=32.0...` | 200 OK | `f0ae6fc2e7e0aa71a2f25f3955b76403e4a9663514d97932fdae5293c9af7de8` | 12 live state vectors in regional box |
| `opensky_historical_arrival_denied.json` | OpenSky Network | `/api/flights/arrival?airport=OSDI` | 403 Forbidden | `910e4b1803a30cdca9b35dbc4e550d8343bdbf7f442988ab402af85312bd2e4f` | Proof of authentication barrier |
| `opensky_historical_states_denied.json` | OpenSky Network | `/api/states/all?time=1704067200` | 403 Forbidden | `82f6ea08c64990b31dc63121dce0e64263f65028e61122a2f27051b1ac0abdf8` | Proof of historical state barrier |
| `adsb_lol_historical_point_503.json` | ADS-B.lol | `/v2/history/point/...` | 503 Unavailable | `32f4c1e4c036d78d5bce0ddad05acdba6da51f8ccacf6deec8bb3fe529ec6ea7` | Proof of non-existent point history |

---

## 4. Damascus (OSDI) Airport Association Rules

A foundational rule of Version 2.17 is that an aircraft observed within 150 km of Damascus must **NEVER** be counted as a DAM airport movement without positive, multi-parameter trajectory evidence.

### 4.1 Trajectory Classification Schema
1. `airport_surface_observation`: Confirmed transponder fix on airport grounds (`dist <= 5 km`, `alt <= 2,200 ft`, `onground = True`, `speed < 80 kts`).
2. `approach_candidate`: Inbound flight within 30 km descending toward OSDI runways (`alt < 10,000 ft`, `vertrate < -300 fpm`).
3. `departure_candidate`: Outbound flight within 25 km climbing away from OSDI runways (`alt < 10,000 ft`, `vertrate > +500 fpm`).
4. `overflight_observation`: High-altitude cruising aircraft passing through Syrian/regional airspace (`alt >= 15,000 ft`). **EXCLUDED FROM DAM MOVEMENT COUNTS.**
5. `regional_observation`: Aircraft operating at regional airports or neighboring FIRs (e.g. Beirut Rafic Hariri Airport, Amman, Tel Aviv) located `> 50 km` from OSDI. **EXCLUDED FROM DAM MOVEMENT COUNTS.**
6. `airport_association_unverified`: Fixes lacking continuous trajectory or elevation profiles.

### 4.2 Empirical Classification of Observed Aircraft
Analysis of the 16 staged observations across ADS-B.lol and ADSB.fi revealed:
- **0 Surface Observations**: Zero aircraft detected on the Damascus runway or taxiways.
- **0 Approach Candidates**: Zero aircraft descending on an approach course to DAM.
- **0 Departure Candidates**: Zero aircraft climbing out from DAM.
- **10 Overflight Observations**: Transcontinental flights at cruise altitude (e.g., Gulf Air `GFA004` at FL390, Emirates `UAE7V` at FL400, Emirates `UAE7TR` at FL360).
- **6 Regional Observations**: Flights operating in adjacent Lebanese airspace (e.g., Middle East Airlines `MEA428` departing Beirut OLBA climbing through 10,175 ft at 2,432 fpm, heading 339° NW; `MEA325` passing over Mount Lebanon corridor at 22,375 ft).

**Physical Movement Promotion:** **0 records promoted**. In strict accordance with data governance rules, no observed aircraft was classified as a verified Damascus movement.

---

## 5. Sensor Independence vs. Provider Independence

Section 5.B4 emphasizes:
> *"Do not treat two APIs using the same upstream ADS-B feed as independent sensor corroboration. Distinguish provider independence from sensor independence."*

Our multi-provider capture revealed that **ADS-B.lol** and **ADSB.fi** share identical underlying receiver telemetry:
- Aircraft `GFA004` (ICAO24: `89408c`, B789):
  - ADS-B.lol fix: Lat `34.328339`, Lon `35.512745`, Speed `472.2 kts`, Alt `38,975 ft`.
  - ADSB.fi fix: Lat `34.328339`, Lon `35.512745`, Speed `472.2 kts`, Alt `39,000 ft`.
- Aircraft `MEA428` (ICAO24: `748021`, A332):
  - Reported concurrently across both providers with identical coordinates.

*Conclusion:* ADS-B.lol and ADSB.fi are independent web APIs, but they federate and share the same underlying volunteer receiver network (via readsb/tar1090/ultrafeeder protocols). They do **NOT** provide independent sensor corroboration.

---

## 6. Historical Data Gap Assessment

1. **Target Window (2024-01-01 to Present):** Confirmed access limitation for historical ADS-B flight-level observations via public unauthenticated query APIs.
2. **Receiver Station Distribution & Terrain Hypothesis:**
   - *Status:* Unverified hypothesis.
   - It has been hypothesized that topographical terrain to the west of Damascus (Anti-Lebanon Mountain range) could theoretically impede VHF Line-of-Sight signals from receivers stationed in neighboring jurisdictions to low-altitude traffic at OSDI (airfield elevation 2,020 ft).
   - *Audit Correction:* Because no direct RF propagation study, feeder station coordinate audit, or empirical receiver site survey has been conducted, this hypothesis is NOT asserted as a factual conclusion. Furthermore, terrain causality must NOT be inferred solely from the absence of nearby aircraft observations in a single snapshot.
3. **Absence of Synthetic Data:** In strict compliance with project safety constraints, zero synthetic movements or interpolated tracks were fabricated. The absence of accessible historical ADS-B queries is documented truthfully as an empirical access limitation.
