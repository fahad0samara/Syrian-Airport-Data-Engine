# Syrian Airport Data Engine — Version 2.13.1
# ADS-B Telemetry Coverage Limitations & Evidentiary Boundaries

**Document Identifier**: `docs/V2_13_1_ADSB_COVERAGE_LIMITATIONS.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Target Airspace**: Damascus Flight Information Region (`OSTT_FIR`)  
**Scope**: Factual Reassessment of V2.7 and V2.8 Live Collection Experiments  
**Status**: APPROVED TECHNICAL REASSESSMENT  
**Production Integrity Invariant**: `data/damascus_airport.db` SHA-256 verified identical (`c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`).

---

## 1. Executive Summary & Audit Mandate

In Version 2.7 and Version 2.8, live telemetry queries were conducted against free crowdsourced ADS-B APIs (ADS-B.lol, ADSB.fi, OpenSky Network) to test whether runway movements at Damascus International Airport (`DAM` / `OSDI`) could be captured in real time.

In the subsequent V2.9 and V2.13 reports, several empirical observations were extended into unverified causal assertions—such as declaring that "zero ground receivers exist within 50 km of Damascus", "Anti-Lebanon mountain terrain is the confirmed cause of signal loss", "all ADS-B networks lose signal below FL150", and "no remote or satellite-based reception is possible near OSDI".

Version 2.13.1 performs a rigorous, evidence-based reassessment to separate:
1. What the API responses **actually demonstrated**.
2. What the short collection windows **actually demonstrated**.
3. What constitutes a **hypothesis (`hypothesis_unverified`)**.
4. What remains **fundamentally unknown**.

---

## 2. Four-Tier Evidentiary Separation

```
+----------------------------------------------------------------------------------------------------+
| TIER 1: WHAT API RESPONSES ACTUALLY DEMONSTRATED (Empirical Facts)                                 |
| - Queries centered on OSDI (33.411 N, 36.514 E) returned aircraft state vectors at cruise          |
|   altitudes (FL310–FL390) transiting Syrian airspace.                                              |
| - Zero state vectors were returned below 3,000 ft AGL or on the runway surface during query tests. |
| - OpenSky Network historical REST API returned HTTP 403 Forbidden to unauthenticated queries.      |
+----------------------------------------------------------------------------------------------------+
| TIER 2: WHAT SHORT COLLECTION WINDOWS DEMONSTRATED (Observation Scope Limits)                     |
| - Testing occurred across discrete, limited time intervals (a few hours to several days).          |
| - Proved that during those specific windows, the tested free APIs provided no low-altitude         |
|   terminal fixes for OSDI.                                                                         |
| - Did NOT prove annual coverage patterns or long-term operational feasibility.                    |
+----------------------------------------------------------------------------------------------------+
| TIER 3: HYPOTHESES REQUIRING UNVERIFIED CLASSIFICATION (hypothesis_unverified)                     |
| - "Zero ground receivers exist within 50 km" -> [hypothesis_unverified] (Feeder locations private) |
| - "Anti-Lebanon terrain is the confirmed cause of signal loss" -> [hypothesis_unverified]          |
| - "All ADS-B networks lose signal below FL150" -> [hypothesis_unverified] (Generalization)         |
| - "No remote or satellite-based reception is possible near OSDI" -> [hypothesis_unverified]       |
+----------------------------------------------------------------------------------------------------+
| TIER 4: WHAT REMAINS FUNDAMENTALLY UNKNOWN                                                         |
| - Real-time uptime, receiver sensitivity, and antenna elevations of regional volunteer feeders.    |
| - Commercial satellite ADS-B (Aireon, Spire) low-altitude terminal reception limits at OSDI.      |
| - Transponder operational discipline (Mode S / ADS-B vs Mode A/C) among local Syrian operators.    |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Itemized Deconstruction of Unverified Assertions

### 3.1 Assertion 1: "There are zero ground receivers within 50 km of Damascus"
- **Status**: **`hypothesis_unverified`**
- **Evidentiary Basis**:
  * Community networks (ADS-B.lol, ADSB.fi, ADS-B Exchange) intentionally anonymize or obscure the physical coordinates of volunteer receiver stations for security and privacy reasons.
  * No public or official receiver-location registry was audited that conclusively proves the absence of receiving equipment within 50 km.
  * The absence of low-altitude aircraft messages in an API payload can occur for multiple alternative reasons:
    1. Lack of aircraft operating within line-of-sight during the query window.
    2. Feeder station temporary power or internet connectivity outage.
    3. API rate limiting, geographic filtering, or backend ingestion latency.
    4. Local transponder transmission suppression or GPS jamming.
  * **Correct Engineering Statement**: During the tested collection intervals, free crowdsourced APIs did not return low-altitude transponder observations within 50 km of OSDI. The specific number and exact physical coordinates of active or dormant receivers remain unverified.

---

### 3.2 Assertion 2: "Anti-Lebanon mountain terrain is the confirmed cause of missing observations"
- **Status**: **`hypothesis_unverified`**
- **Evidentiary Basis**:
  * Radio line-of-sight (RLOS) obstruction by the Anti-Lebanon mountain range is a plausible theoretical radio-frequency propagation model for receivers situated west of Damascus (e.g. in Lebanon or along the Mediterranean coast).
  * However, no electromagnetic field measurements, signal-to-noise ratio (SNR) logs, or Fresnel zone diffraction studies were conducted in this project to verify that terrain obstruction is the actual cause of missing terminal packets.
  * Observers to the south (Jordan), east (desert corridor), or north may experience completely different topography.
  * **Correct Engineering Statement**: Line-of-sight radio propagation models indicate potential terrain shielding from western stations, but terrain obstruction has not been instrumented or empirically established as the sole or primary cause of missing observations.

---

### 3.3 Assertion 3: "All ADS-B networks lose signal below FL150"
- **Status**: **`hypothesis_unverified`**
- **Evidentiary Basis**:
  * In V2.7, several observed en-route aircraft trajectories disappeared from API feeds around FL150–FL180 while in Syrian airspace.
  * Extrapolating this to all aircraft, all approach paths, and all networks is an over-generalization.
  * Different receiver setups with high-gain directional antennas, low-noise amplifiers (LNAs), or receivers situated at high elevations (e.g. Mount Hermon or Jordanian plateaus) may achieve substantially lower reception floors.
  * Commercial networks (FlightRadar24, FlightAware) employ proprietary multilateration (MLAT) clusters and satellite payloads that do not share the limitations of free community REST feeds.
  * **Correct Engineering Statement**: Discrete observations showed transponder track dropouts below approximately FL150 in free API samples, but this threshold is not a demonstrated universal limit across all networks or operating conditions.

---

### 3.4 Assertion 4: "No remote or satellite-based reception is possible near OSDI"
- **Status**: **`hypothesis_unverified` (Factually Contradicted by Satellite ADS-B Physics)**
- **Evidentiary Basis**:
  * Space-based ADS-B constellations (such as Aireon hosted on Iridium NEXT satellites, and Spire Global nanosatellites) orbit in Low Earth Orbit (LEO) at altitudes of 780 km.
  * Space-based receivers look down from space and are **completely unaffected by terrestrial mountain ridges, valleys, or horizon distance limits**.
  * Commercial flight tracking providers (FlightAware and FlightRadar24) ingest space-based ADS-B data feeds specifically to track aircraft over remote, oceanic, and mountainous terrain where ground stations do not exist.
  * **Correct Engineering Statement**: While free community networks rely predominantly on terrestrial volunteer antennas, satellite-based ADS-B reception over Damascus is technically viable and operates independently of terrestrial terrain shielding.

---

## 4. Operational Boundaries for Future Data Modeling

To preserve total evidentiary integrity, all future engineering analyses within the Syrian Airport Data Engine must adhere to three non-negotiable guidelines:

1. **Avoid Unproven Causal Declarations**: Label unmeasured explanations for missing signals as `hypothesis_unverified`.
2. **Distinguish Sensor Reality from Hypothesis**: Report exact numerical parameters returned by APIs (e.g. `altitude: 33000`, `latitude: 33.411`) without extrapolating unrecorded physical causes.
3. **Acknowledge Space-Based Capabilities**: Distinguish terrestrial volunteer ADS-B networks (which have demonstrated low-altitude coverage gaps at Damascus) from commercial space-based constellations (whose coverage at OSDI remains unverified but technically viable).
