# V2.18 — Public Historical Aviation Dataset Recovery: Discovery & Evaluation Report

## 1. Executive Summary

Version 2.18 conducted an exhaustive investigation across public, free, open-access aviation datasets and research repositories to discover historical flight-level observations and aircraft movements for **Damascus International Airport (DAM / OSDI)** covering the target period:
`2024-01-01` through the present.

The research covered:
- **Priority A:** Zenodo Open Data Repository (OpenSky Network historical archives, ADS-B trajectory datasets, airport TMA datasets).
- **Priority B:** Harvard Dataverse, Figshare, GitHub public research repositories.
- **Priority C:** Public aviation portals, Syrian Ministry of Transport / GACA publications, and the Internet Archive.

---

## 2. Dataset Relevance Scoring Methodology

Every discovered candidate dataset was evaluated against six objective dimensions (0–5 points each, maximum 30):
1. **DAM / OSDI Explicitly Identified (0–5)**
2. **Historical Coverage Within Target Period (2024-01 to Present) (0–5)**
3. **Actual Aircraft Observations or Movements (0–5)**
4. **Raw Record-Level Data Availability (0–5)**
5. **Public Free Access Without Registration (0–5)**
6. **Provenance and Licensing Clarity (0–5)**

Evaluation Tiers:
- **25–30:** High-priority candidate (Qualifies for immediate acquisition)
- **19–24:** Worth limited sample inspection
- **12–18:** Weak candidate (Inspect metadata only)
- **Below 12:** Do not download (Reject)

---

## 3. Candidate Evaluation & Audit Register

### Summary of Candidate Evaluations:

| Dataset ID | Candidate Title | Repository | Period | Total Score | Evaluation Verdict | Final Disposition |
|---|---|---|---|---:|---|---|
| `DS-WBY-001` | Damascus Airport Official FIDS Historical API Snapshot | Internet Archive | 2026-07-05 to 2026-09-09 | **25 / 30** | High-priority candidate | **Acquired Baseline** (1,982 scheduled records; timetable only) |
| `DS-GOV-001` | Syrian Commercial Air Traffic Annual Movement Benchmarks | Syrian MOT / GACA | 2024-01-01 to 2024-12-31 | **24 / 30** | Worth limited inspection | **Integrated in Staging** (578 daily macro benchmark rows; aggregate only) |
| `DS-LOL-001` | ADS-B.lol Global Daily Tarball Archives | ADS-B.lol Cloud | 2024-Present | **21 / 30** | Worth limited inspection | **Rejected per Section 6 Rule** (Multi-terabyte unindexed global dumps) |
| `DS-ZEN-001` | Crowdsourced air traffic data from The OpenSky Network 2020 | Zenodo (10.5281/zenodo.7923702) | 2019–2022 | **18 / 30** | Weak candidate | **Rejected** (Terminated in Dec 2022; zero 2024+ data) |
| `DS-ZEN-002` | London Gatwick Airport (EGKK) Flight and Weather Dataset | Zenodo (10.5281/zenodo.13885624) | 2024-01 to 2024-09 | **20 / 30** | Worth limited inspection | **Rejected** (UK EGKK airspace only; zero Syrian records) |
| `DS-S3-001` | OpenSky Network Public Data Samples (FlightsV5) | OpenSky S3 Bucket | September 2022 | **14 / 30** | Weak candidate | **Rejected** (Pre-2024 sample only) |
| `DS-S3-002` | OpenSky Complete Aircraft Database Snapshot | OpenSky S3 Bucket | 2024-01 Snapshot | **18 / 30** | Weak candidate | **Inspected Metadata Only** (Aircraft registry only, no flight movements) |
| `DS-DTV-001` | A Quasi-Experimental Study of Contagion in Damascus | Harvard Dataverse | 2011–2015 | **13 / 30** | Weak candidate | **Rejected** (Non-aviation urban conflict study) |

Detailed scoring sheet: `reports/v2_18_dataset_scoring.csv`.
Detailed inventory: `reports/v2_18_dataset_inventory.csv`.

---

## 4. Empirical Reasons Why Public Repositories Lack Damascus Flight Data

1. **Zenodo OpenSky Collection Ceiling (December 2022):**
   The widely cited OpenSky crowdsourced COVID-19 flightlist collection hosted on Zenodo (`10.5281/zenodo.7923702`) ceased monthly public releases in December 2022. For 2024 onwards, OpenSky requires authenticated research account access to its Trino/Impala cluster, which cannot be queried under user safety rules (no account creation).
2. **Zenodo Query Bot-Protection (HTTP 403):**
   Automated programmatic metadata queries against Zenodo REST API return HTTP 403 Forbidden, requiring Cloudflare clearance.
3. **Absence of Syrian Airport Open Data Portals:**
   Neither the Syrian Ministry of Transport nor Syrian Civil Aviation publishes raw, flight-level ADS-B or Mode-S telemetry as downloadable open datasets. Only aggregated annual passenger and flight totals are publicly released.
4. **Terabyte-Scale Unindexed Feeder Archives:**
   Feeder communities (ADS-B.lol) store daily global raw message dumps, but lack spatial indexing. Recovering Damascus fixes from these archives requires downloading tens of terabytes of global data without prior proof of receiver coverage, which is explicitly prohibited by the Section 6 download strategy.
