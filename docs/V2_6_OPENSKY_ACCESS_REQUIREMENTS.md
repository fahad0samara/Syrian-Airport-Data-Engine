# Syrian Airport Data Engine — Version 2.6
# OpenSky Network Access Requirements & Policy Verification

**Document Identifier**: `docs/V2_6_OPENSKY_ACCESS_REQUIREMENTS.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Audit Date**: 2026-10-11  
**Verification Standard**: Official OpenSky Network Access Policies & Documentation  
**Status**: APPROVED POLICY SPECIFICATION  

---

## 1. Executive Summary & Policy Overview

The OpenSky Network (`opensky-network.org`) is a non-profit association based in Switzerland that operates an open, crowdsourced receiver network capturing ADS-B and Mode-S aircraft transponder signals.

Access to OpenSky data is strictly differentiated into two distinct tiers:
1. **Public / Registered REST API**: Access to live state vectors and short-term historical flight lists (capped at a rolling 30-day window; historical queries $>30$ days return `HTTP 403 Forbidden`).
2. **Trino / Impala SQL Historical Cluster**: Direct SQL querying capability against the multi-petabyte historical state vector tables (`state_vectors_data4`) dating back to 2013. Access to this cluster is **gated and requires a formal application process**.

This document forensically audits the official access criteria, eligibility boundaries, usage restrictions, rate limits, citation mandates, and legal terms governing historical Trino access.

---

## 2. Requirement-by-Requirement Evidence Register

Every policy item has been audited against official OpenSky Network documentation as of 2026-10-11:

| Policy Item / Requirement | Official Requirement Details | Supporting Documentation URL | Date Checked | Verification Status |
| :--- | :--- | :--- | :---: | :---: |
| **1. Historical Trino Target Audience** | Access to the Trino historical interface is primarily reserved for **university-affiliated researchers, governmental organizations, and aviation authorities** for aviation-related research and incident investigation. | `https://opensky-network.org/faq` and `https://opensky-network.org/my-opensky/request-data` | 2026-10-11 | **Verified** |
| **2. Independent / Private Researchers** | Private individuals seeking access for personal learning, hobbyist tracking, or private unverified projects are generally **ineligible** for direct Trino access. They are directed to the REST API (rolling 30-day window) or static public research datasets. | `https://opensky-network.org/faq` | 2026-10-11 | **Verified** |
| **3. Institutional Affiliation Mandate** | Institutional affiliation (university, research institute, civil aviation authority, or registered non-profit) is **required** for historical Trino cluster credentials. Non-profit organizations may be granted access on a case-by-case basis. | `https://opensky-network.org/faq` | 2026-10-11 | **Verified** |
| **4. Email Domain Requirements** | Applicants affiliated with an eligible institution must use their **affiliated institutional email address**. While American `.edu` addresses are common, international academic domains (`.ac.uk`, `.edu.sy`, `.de`, `.ch`, `.fr`, etc.) or recognized research institute domains are fully accepted. | `https://opensky-network.org/my-opensky/request-data` | 2026-10-11 | **Verified** |
| **5. Application Data Requirements** | Applicants must submit: (a) Principal Investigator / Researcher name, (b) institutional affiliation, (c) project title, (d) detailed abstract/purpose, (e) exact data scope (temporal/geographic bounds and tables), and (f) explicit statement of non-commercial academic use. | `https://opensky-network.org/my-opensky/request-data` | 2026-10-11 | **Verified** |
| **6. Commercial / For-Profit Use** | Any use by a commercial entity, for-profit company, or military contractor—regardless of the purpose—**requires a paid written license agreement**. Historical research access cannot be used to power commercial products. | `https://opensky-network.org/about/terms-of-use` | 2026-10-11 | **Verified** |
| **7. Operational Integration Ban** | Operational integration of OpenSky feeds into automated production systems, live operational dashboards, or real-time flight monitoring services requires a separate written operational license, even for non-profits. | `https://opensky-network.org/about/terms-of-use` | 2026-10-11 | **Verified** |
| **8. Trino Query Limits & Execution** | Trino queries are subject to cluster resource management. Long-running full-table scans without partition limits (`WHERE time BETWEEN ...`) are automatically terminated. Query result sets must be filtered spatially and temporally. | `https://opensky-network.org/data/data-tools` | 2026-10-11 | **Verified** |
| **9. Mandatory Citation / Attribution** | Any published output (academic paper, presentation, report, or website) utilizing OpenSky data **must cite the official foundational paper**: Schäfer et al., "Bringing Up OpenSky: A Large-scale ADS-B Sensor Network for Research", ACM/IEEE IPSN 2014. | `https://opensky-network.org/about/terms-of-use` | 2026-10-11 | **Verified** |
| **10. Data Retention & Redistribution** | Raw historical telemetry from OpenSky is provided under **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**. Redistribution of bulk raw telemetry is strictly prohibited; publication of derived statistical aggregates is permitted. | `https://opensky-network.org/about/terms-of-use` | 2026-10-11 | **Verified** |

---

## 3. Epistemic Assessment for Syrian Airport Data Engine

### Can an Independent Non-Commercial Project Apply?
1. **As an Unaffiliated Individual**: **NO**. Applications submitted using personal email addresses (`@gmail.com`, `@yahoo.com`) without institutional standing are rejected under OpenSky's standard intake policy.
2. **As an Affiliated Academic Project**: **YES**. If the applicant or project lead is affiliated with a recognized university, research laboratory, or non-profit academic institute, the project is **fully eligible** to apply for non-commercial historical Trino access.
3. **As an Independent Non-Profit**: **CASE-BY-CASE**. Registered civil research entities may apply by demonstrating legitimate non-commercial scientific research objectives and providing organizational documentation.

---

## 4. Operational Conditions for Trino Querying

Once access is granted, queries must conform to strict execution conditions:
1. **Time Partitioning**: Queries against `state_vectors_data4` must always include `time BETWEEN <start_epoch> AND <end_epoch>`, constrained to single-day or multi-hour windows.
2. **Spatial Bounding**: Latitudinal and longitudinal limits must be enforced in the `WHERE` clause (`lat BETWEEN 33.10 AND 33.70 AND lon BETWEEN 36.15 AND 36.85`) to avoid cluster-wide memory overflows.
3. **No Automated Daemon Ingestion**: Querying must be performed interactively or in small batch extracts for analytical research; automated daemon scripts querying Trino in production loops are prohibited.
