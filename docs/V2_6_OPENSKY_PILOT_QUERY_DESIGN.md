# Syrian Airport Data Engine — Version 2.6
# OpenSky Pilot Query Architecture & Trajectory Discrimination Design

**Document Identifier**: `docs/V2_6_OPENSKY_PILOT_QUERY_DESIGN.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Aerodrome Reference Point (ARP)**: Lat `33.4150° N`, Lon `36.5156° E` | Elevation: `2,020 ft MSL` (`616 m`)  
**Audit Date**: 2026-10-11  
**Target Standard**: Physics-Based Trajectory Segmentation & Cluster Resource Protection  
**Execution Posture**: SPECIFICATION ONLY (Query Execution Strictly Frozen Until Authorized)  

---

## 1. Executive Summary & Design Principles

This document establishes the reproducible SQL query architecture for extracting and analyzing historical OpenSky Network state vectors around Damascus International Airport (`DAM` / `OSDI`).

### Core Epistemic Principles
1. **Bounding Box Proximity ≠ Runway Movement**: The presence of an aircraft state vector inside a geographic coordinate box around Damascus does **not** prove that the aircraft took off or landed at OSDI. International airways transit directly overhead the Damascus VOR at FL250–FL410.
2. **Cluster Protection**: Queries must strictly enforce partition bounds on `time` and spatial bounding boxes on `lat` and `lon` in the primary SQL filter to prevent cluster timeouts or resource exhaustion on OpenSky's Trino cluster.
3. **Multi-Zone Trajectory Segmentation**: Raw telemetry must be segmented into distinct altitude bands and spatial zones before assigning movement candidate classifications.
4. **Execution Freeze**: Historical Trino queries must **not** be executed until research credentials are confirmed by OpenSky and user authorization is explicitly granted.

---

## 2. Temporal Pilot Parameters & Epoch Windows

The pilot query architecture targets the eight standardized benchmark dates. To ensure seamless reconciliation between UTC transponder messages and Damascus local operational days (`Asia/Damascus`, UTC+3), each query window spans from `00:00:00` to `23:59:59` UTC (with a 3-hour buffer at day boundaries to cover local midnight transitions):

| Target Sample Date | UTC Epoch Start (00:00:00 UTC) | UTC Epoch End (23:59:59 UTC) | Damascus Local Window Covered (UTC+3) |
| :---: | :---: | :---: | :---: |
| **`2024-01-15`** | `1705276800` | `1705363199` | 2024-01-15 03:00 to 2024-01-16 02:59 local |
| **`2024-03-15`** | `1710460800` | `1710547199` | 2024-03-15 03:00 to 2024-03-16 02:59 local |
| **`2024-05-15`** | `1715731200` | `1715817599` | 2024-05-15 03:00 to 2024-05-16 02:59 local |
| **`2024-07-15`** | `1721001600` | `1721087999` | 2024-07-15 03:00 to 2024-07-16 02:59 local |
| **`2024-09-15`** | `1726358400` | `1726444799` | 2024-09-15 03:00 to 2024-09-16 02:59 local |
| **`2024-10-10`** | `1728518400` | `1728604799` | 2024-10-10 03:00 to 2024-10-11 02:59 local |
| **`2025-06-15`** | `1750032000` | `1750118399` | 2025-06-15 03:00 to 2025-06-16 02:59 local |
| **`2026-06-15`** | `1781481600` | `1781567999` | 2026-06-15 03:00 to 2026-06-16 02:59 local |

---

## 3. Spatial Zonation & Altitude Banding Architecture

```mermaid
flowchart TD
    subgraph Horizontal Spatial Zones
        Z1[Zone 1: Regional FIR Buffer\nLat 32.8°–34.0° N, Lon 35.8°–37.2° E\nRadius ~50 NM]
        Z2[Zone 2: Damascus TMA Outer Box\nLat 33.00°–33.80° N, Lon 36.10°–36.95° E\nRadius ~25 NM]
        Z3[Zone 3: Intermediate Approach & Climbout Cone\nLat 33.25°–33.58° N, Lon 36.35°–36.70° E\nRadius ~10 NM along Rwy Bearings]
        Z4[Zone 4: Inner Runway Movement Area\nLat 33.400°–33.430° N, Lon 36.500°–36.535° E\nRunway Centerline Boundary]
        Z1 --> Z2 --> Z3 --> Z4
    end

    subgraph Vertical Altitude Bands
        AltA[Band A: High-Altitude Overflights\nAltitude >= 15,000 ft MSL / FL150+]
        AltB[Band B: Terminal Maneuvering\n5,000 ft MSL to 15,000 ft MSL]
        AltC[Band C: Low Approach / Climbout\n2,500 ft MSL to 5,000 ft MSL]
        AltD[Band D: Surface Threshold / Runway Area\n<= 2,150 ft MSL (Runway is 2,020 ft MSL)]
    end
```

### Justification of Selected Spatial & Temporal Bounds
1. **Outer TMA Radius (25–30 NM)**: Standard terminal holding, approach transitions, and standard instrument departures (SIDs) at OSDI maneuver within 25 NM of the Damascus VOR (`DAM`). Restricting extraction to this radius eliminates distant Beirut and Amman traffic while preserving full terminal descents.
2. **Intermediate Cone (10 NM along 051° / 231°)**: Runways 05R/23L and 05L/23R are aligned northeast-southwest. Aircraft on final approach establish on the localizer 8 to 12 NM from the threshold.
3. **Altitude Threshold (2,150 ft MSL)**: Damascus aerodrome elevation is 2,020 ft MSL. A threshold of 2,150 ft MSL accommodates standard barometric pressure deviations (QNH variance) while isolating true surface rollouts from low flybys.

---

## 4. Movement Discrimination & Qualification Framework

To prevent overcounting and historical hallucinations, incoming telemetry is partitioned into six operational classifications:

| Operational Category | Spatial Zone | Altitude Band | Kinematic Profile | Classification Outcome | Admitted to `verified_movements_count`? |
| :--- | :---: | :---: | :--- | :--- | :---: |
| **1. En-Route Overflight** | Zone 1 / 2 | Band A ($\ge 15,000$ ft) | Level flight, groundspeed $\ge 300\text{ kts}$, constant vertical rate | `overflight` | **NO** (Airspace transit only) |
| **2. Terminal-Area Observation** | Zone 2 | Band B ($5\text{k}–15\text{k}$ ft) | Maneuvering in TMA, no continuous descent to threshold | `terminal_area_transit` | **NO** (Terminal observation) |
| **3. Approach Candidate** | Zone 3 | Band C ($2.5\text{k}–5\text{k}$ ft) | Track $051^\circ \pm 7^\circ$ or $231^\circ \pm 7^\circ$, vertical rate $\le -300\text{ fpm}$, decelerating, drops off at $2.8\text{k}–3.5\text{k}$ ft | `approach_candidate` | **NO** (Candidate event only) |
| **4. Departure Candidate** | Zone 3 | Band C ($2.5\text{k}–5\text{k}$ ft) | Initial fix in departure corridor, climbing $\ge +800\text{ fpm}$, accelerating from $<180\text{ kts}$ | `departure_candidate` | **NO** (Candidate event only) |
| **5. Potential Ground Observation** | Zone 4 | Band D ($\le 2,150$ ft) | Transponder `onground = True`, groundspeed $<80\text{ kts}$, but single isolated packet | `potential_ground_observation`| **NO** (Sensor anomaly check) |
| **6. Confirmed Physical Movement** | Zone 4 | Band D ($\le 2,150$ ft) | $\ge 3$ consecutive surface fixes, ground roll profile, OR candidate corroborated by independent provider | **`confirmed_physical`** | **YES** (Admitted ground truth) |

---

## 5. Reproducible Trino SQL Pilot Script

The following parameterized SQL template represents the complete query design to be executed once Trino credentials are confirmed and authorized:

```sql
-- ============================================================================
-- Syrian Airport Data Engine — Version 2.6
-- Pilot Query: Damascus International Airport (OSDI) Historical Extraction
-- Target Date: 2024-01-15 (Example Execution Window)
-- ============================================================================

WITH raw_tma_vectors AS (
    SELECT 
        time,
        icao24,
        callsign,
        lat,
        lon,
        velocity * 1.94384 AS speed_kts,            -- Convert m/s to knots
        heading,
        vertrate * 196.85 AS vertrate_fpm,          -- Convert m/s to fpm
        baroaltitude * 3.28084 AS baroalt_ft,       -- Convert meters to feet
        geoaltitude * 3.28084 AS geoalt_ft,         -- Convert meters to feet
        onground,
        lastposupdate
    FROM 
        state_vectors_data4
    WHERE 
        -- Partition filter: Single calendar day (2024-01-15 00:00:00 to 23:59:59 UTC)
        time BETWEEN 1705276800 AND 1705363199
        -- Spatial pre-filter: Damascus TMA outer bounding box
        AND lat BETWEEN 33.0000 AND 33.8000
        AND lon BETWEEN 36.1000 AND 36.9500
),

segmented_trajectories AS (
    SELECT 
        time,
        icao24,
        callsign,
        lat,
        lon,
        speed_kts,
        heading,
        vertrate_fpm,
        baroalt_ft,
        onground,
        -- Distance from Aerodrome Reference Point (ARP: Lat 33.4150, Lon 36.5156) in nautical miles (approx)
        SQRT(POW((lat - 33.4150) * 60.0, 2) + POW((lon - 36.5156) * 60.0 * COS(RADIANS(33.4150)), 2)) AS dist_arp_nm,
        -- Spatial Zone Tagging
        CASE 
            WHEN lat BETWEEN 33.4000 AND 33.4300 AND lon BETWEEN 36.5000 AND 36.5350 THEN 'Zone_4_Runway'
            WHEN lat BETWEEN 33.2500 AND 33.5800 AND lon BETWEEN 36.3500 AND 36.7000 THEN 'Zone_3_Cone'
            ELSE 'Zone_2_TMA'
        END AS spatial_zone,
        -- Altitude Band Tagging
        CASE 
            WHEN baroalt_ft <= 2150.0 OR (baroalt_ft IS NULL AND onground = TRUE) THEN 'Band_D_Surface'
            WHEN baroalt_ft < 5000.0 THEN 'Band_C_LowApproach'
            WHEN baroalt_ft < 15000.0 THEN 'Band_B_TMA'
            ELSE 'Band_A_Overflight'
        END AS altitude_band
    FROM 
        raw_tma_vectors
),

trajectory_aggregates AS (
    SELECT 
        icao24,
        callsign,
        MIN(time) AS first_seen_epoch,
        MAX(time) AS last_seen_epoch,
        COUNT(*) AS total_fixes,
        MIN(baroalt_ft) AS min_baro_alt,
        MAX(baroalt_ft) AS max_baro_alt,
        MIN(dist_arp_nm) AS min_dist_arp,
        MAX(CASE WHEN onground = TRUE THEN 1 ELSE 0 END) AS has_onground_true,
        SUM(CASE WHEN spatial_zone = 'Zone_4_Runway' AND (baroalt_ft <= 2150.0 OR onground = TRUE) THEN 1 ELSE 0 END) AS surface_fixes
    FROM 
        segmented_trajectories
    GROUP BY 
        icao24, callsign
)

-- Final Movement Classification Output
SELECT 
    icao24,
    callsign,
    from_unixtime(first_seen_epoch) AS first_seen_utc,
    from_unixtime(last_seen_epoch) AS last_seen_utc,
    total_fixes,
    min_baro_alt,
    min_dist_arp,
    surface_fixes,
    CASE 
        -- Confirmed Physical: Multiple surface fixes inside runway polygon
        WHEN surface_fixes >= 3 THEN 'confirmed_physical'
        -- Potential Ground: 1 or 2 surface fixes (requires inspection)
        WHEN surface_fixes BETWEEN 1 AND 2 THEN 'potential_ground_observation'
        -- Approach Candidate: Descends close to ARP along approach corridor
        WHEN min_baro_alt < 4000.0 AND min_dist_arp < 8.0 THEN 'approach_candidate'
        -- Departure Candidate: Climbs out of immediate TMA
        WHEN min_baro_alt < 5000.0 AND min_dist_arp < 10.0 THEN 'departure_candidate'
        -- Terminal Area Transit: Low altitude maneuvering
        WHEN min_baro_alt < 15000.0 THEN 'terminal_area_transit'
        -- En-Route Overflight: High altitude
        ELSE 'en_route_overflight'
    END AS trajectory_classification
FROM 
    trajectory_aggregates
ORDER BY 
    first_seen_epoch ASC;
```

---

## 6. Execution Governance & Cluster Etiquette

1. **Test Query Execution**:
   - The above query will be tested on **one date only** (`2024-01-15`) initially to evaluate Trino execution time, memory usage, and result record count.
   - Batch extraction for the remaining 7 benchmark dates will only proceed if the test query executes in under 60 seconds with zero cluster warnings.
2. **Local Archival**:
   - Query outputs will be exported directly as CSV files named `OSDI_OPENSKY_PILOT_<YYYYMMDD>.csv` into `data/historical_sample_review/opensky/`.
   - File SHA-256 will be logged immediately in a dedicated manifest.
