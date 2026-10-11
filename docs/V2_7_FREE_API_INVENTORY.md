# Syrian Airport Data Engine — Version 2.7
# Free Aviation APIs Inventory & Access Profile

**Document Identifier**: `docs/V2_7_FREE_API_INVENTORY.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Audit Date**: 2026-10-11  
**Target Standard**: Verified Documentation & Empirical Live Endpoint Validation  
**Operating Mode**: STRICTLY READ-ONLY (Research & Discovery Phase)  

---

## 1. Executive Summary

This inventory documents all evaluated public and free aviation data APIs capable of providing live or historical aircraft tracking data. Every source has been audited against its official documentation, terms of service, and verified through empirical HTTP requests from the Damascus evaluation environment.

---

## 2. Detailed API Inventory

### 1. OpenSky Network (REST API)

- **Provider**: OpenSky Network Association (Switzerland, non-profit)
- **Official Website**: `https://opensky-network.org/`
- **Official Documentation**: `https://openskynetwork.github.io/opensky-api/` and `https://opensky-network.org/apidoc/rest.html`
- **Base Endpoint**: `https://opensky-network.org/api/states/all`
- **Damascus Query Mechanism**: Bounding box query using parameters `lamin`, `lomin`, `lamax`, `lomax`.
  - Example for 150 km around OSDI:
    `GET https://opensky-network.org/api/states/all?lamin=32.06&lamax=34.76&lomin=34.89&lomax=38.13`
- **Authentication Model**:
  - *Anonymous*: Permitted without credentials.
  - *Authenticated Free*: Free registration on website provides username/password for higher rate limits.
- **Rate Limits & Constraints**:
  - *Anonymous*: 1 request per 10 seconds (10s time resolution).
  - *Registered Free*: 1 request per 5 seconds (5s time resolution).
- **Historical Data Availability (Standard REST)**:
  - Flight list endpoints (`/api/flights/departure`, `/api/flights/arrival`) are strictly capped at a **rolling 30-day window**.
  - Historical queries $>30$ days return `HTTP 403 Forbidden`.
  - Multi-year historical raw state vectors require approved institutional research access via the Trino SQL cluster.
- **License & Usage Restrictions**: Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0). Mandatory citation of Schäfer et al. (IPSN 2014). Operational commercial use prohibited without license.
- **Empirical Live Test Status**: **HTTP 200 OK** (Returned 10 aircraft in regional bounding box).

---

### 2. ADS-B.lol

- **Provider**: adsb.lol (Open-source, community-driven ADS-B aggregator)
- **Official Website**: `https://adsb.lol/`
- **Official Documentation**: `https://api.adsb.lol/docs` and `https://api.adsb.lol/api/openapi.json`
- **Base Endpoint**: `https://api.adsb.lol/v2/`
- **Damascus Query Mechanism**: Point / radius query accepting latitude, longitude, and radius in nautical miles (max 250 nm).
  - Example for 150 km (~81 nm) around OSDI:
    `GET https://api.adsb.lol/v2/point/33.4115/36.5156/81`
    *(Alternative: `GET /v2/lat/33.4115/lon/36.5156/dist/81`)*
- **Authentication Model**: **None (Completely Open & Free)**. No API key or registration required.
- **Rate Limits & Constraints**:
  - Standard fair-use policy: ~1 request per second per IP recommended.
  - Generous community limits; no hard paywall.
- **Historical Data Availability**:
  - Live real-time buffer only (~recent minutes).
  - No public historical REST query endpoint; historical database replays require bulk community tarball downloads or self-hosted archival.
- **Data Payload & Metadata**: Rich `readsb`-derived JSON schema containing `hex`, `flight` (callsign), `r` (registration), `t` (aircraft type), `desc` (aircraft description), `alt_baro`, `alt_geom`, `gs` (groundspeed), `ias`, `tas`, `track`, `baro_rate`, `squawk`, `emergency`, `category`, `lat`, `lon`, `rssi`, `dst` (distance from point in nm), `dir` (bearing from point).
- **License & Usage Restrictions**: Open community data. Non-commercial and community use encouraged; attribution to `adsb.lol` requested.
- **Empirical Live Test Status**: **HTTP 200 OK** (Returned 4 aircraft in 81 nm radius with rich metadata).

---

### 3. Airplanes.live

- **Provider**: Airplanes.live (Independent community flight tracking network)
- **Official Website**: `https://airplanes.live/`
- **Base Endpoint**: `https://api.airplanes.live/v2/`
- **Damascus Query Mechanism**: Syntactically designed for point queries (`/v2/point/{lat}/{lon}/{radius}`).
  - Example: `GET https://api.airplanes.live/v2/point/33.4115/36.5156/81`
- **Authentication Model**: **Restricted / Whitelist Required**.
- **Empirical Finding**:
  - Direct GET requests from automated clients return **HTTP 403 Forbidden** with official payload:
    `{"error": "Please contact us at contact@airplanes.live. Your email MUST include any links, a description of the project, and any information you deem appropriate."}`
- **Rate Limits & Constraints**: Undocumented public limits due to closed access gate.
- **Historical Data Availability**: Live web globe viewer; historical API closed to unapproved public.
- **License & Usage Restrictions**: Community non-commercial policy; requires pre-approved project registration via email.
- **Empirical Live Test Status**: **HTTP 403 Forbidden** (Access gated; requires developer whitelisting).

---

### 4. ADSB.fi (Community Open Data)

- **Provider**: ADSB.fi (Cooperative Nordic/European open ADS-B network)
- **Official Website**: `https://adsb.fi/`
- **Official Documentation**: `https://opendata.adsb.fi/`
- **Base Endpoint**: `https://opendata.adsb.fi/api/v2/`
- **Damascus Query Mechanism**: Point distance endpoint accepting latitude, longitude, and distance in nautical miles.
  - Example for 150 km (~81 nm) around OSDI:
    `GET https://opendata.adsb.fi/api/v2/lat/33.4115/lon/36.5156/dist/81`
- **Authentication Model**: **None (Completely Open & Free)**. No API key required.
- **Rate Limits & Constraints**: Standard fair-use policy (~1 req/sec). CORS-enabled.
- **Historical Data Availability**: Live feed only; daily raw dataset dumps available for research on opendata portal.
- **Data Payload & Metadata**: Complete `readsb` JSON output (`hex`, `flight`, `r`, `t`, `desc`, `alt_baro`, `alt_geom`, `gs`, `track`, `baro_rate`, `squawk`, `rssi`).
- **License & Usage Restrictions**: Open Data Commons / Creative Commons. Free for non-commercial and research use.
- **Empirical Live Test Status**: **HTTP 200 OK** (Returned 4 aircraft in 81 nm radius matching ADS-B.lol observations).

---

### 5. ADSB.one

- **Provider**: ADSB.one (Aggregated flight feed)
- **Official Website**: `https://adsb.one/`
- **Base Endpoint**: `https://api.adsb.one/v2/point/{lat}/{lon}/{radius}`
- **Authentication Model**: Cloudflare protected.
- **Empirical Finding**: Returns **HTTP 403 Forbidden** (Cloudflare bot management block). Unsuitable for programmatic automated research scripts.
- **Empirical Live Test Status**: **HTTP 403 Forbidden** (Blocked by Cloudflare).

---

### 6. ADS-B Exchange (RapidAPI Free Tier vs Paid)

- **Provider**: ADS-B Exchange (Jetnet, LLC)
- **Website**: `https://www.adsbexchange.com/`
- **API Portal**: RapidAPI (`https://rapidapi.com/adsbx/api/adsbexchange-com1`)
- **Access Profile**:
  - Previously offered open community feeds prior to Jetnet acquisition in 2023.
  - Current access is strictly commercialized via RapidAPI.
  - The "Basic" free tier on RapidAPI is limited to a nominal testing quota (~500 to 2,500 requests per month with strict rate limits and credit card validation required on RapidAPI).
- **Historical Data**: Gated behind enterprise sales contracts.
- **License**: Commercial proprietary terms.
- **Assessment**: Substantially inferior to adsb.lol and ADSB.fi for continuous free monitoring.

---

### 7. OurAirports (Static Reference Data)

- **Provider**: OurAirports Community
- **Official Website**: `https://ourairports.com/data/`
- **Access Profile**: Direct open CSV downloads (`airports.csv`, `runways.csv`).
- **Data Nature**: Static geospatial reference metadata only (Runway 05R/23L, elevation 2,020 ft, ARP 33.4150, 36.5156).
- **Operational Movement Data**: None.
- **License**: Public Domain (Creative Commons CC0 1.0).
- **Empirical Live Test Status**: **Verified Active** (Static reference baseline).

---

## 3. Discovered Free APIs Summary Matrix

| API / Provider Name | Primary Endpoint Pattern | Auth Model | Free Tier Limits | OSDI Live Query Support | Historical API Depth | Live Test Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **OpenSky Network** | `/api/states/all?lamin=...` | Anonymous / Basic Auth | 1 req/10s (Anon) / 1 req/5s (Reg) | **Yes** (Bounding box) | 30 days (REST) / 2013–pres (Trino) | **HTTP 200 OK** |
| **ADS-B.lol** | `/v2/point/{lat}/{lon}/{dist_nm}` | **None** | Fair use (~1 req/sec) | **Yes** (Lat/Lon/Radius) | Live only (No REST archive) | **HTTP 200 OK** |
| **ADSB.fi** | `/api/v2/lat/{lat}/lon/{lon}/dist/{nm}` | **None** | Fair use (~1 req/sec) | **Yes** (Lat/Lon/Radius) | Live only (Daily bulk dumps) | **HTTP 200 OK** |
| **Airplanes.live** | `/v2/point/{lat}/{lon}/{dist_nm}` | Email Whitelist | Gated / Closed | Syntactic only | Web viewer only | **HTTP 403 Forbidden** |
| **ADSB.one** | `/v2/point/{lat}/{lon}/{dist_nm}` | Blocked | Cloudflare Challenge | Blocked | None | **HTTP 403 Forbidden** |
| **ADS-B Exchange** | RapidAPI `/v2/lat/...` | RapidAPI Key | Micro trial / Card required | Syntactic | Enterprise paid | **Commercial Gated** |
| **OurAirports** | Static CSV Download | None (CC0) | Unlimited download | Static baseline only | N/A | **Verified Active** |
