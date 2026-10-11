# V2.18.1 — Historical Coverage Integrity & Dataset Classification Audit
## Final Audit & Forensic Reconciliation Report

**Final Status: ACCEPTED WITH LIMITATIONS**

---

## 1. Executive Audit Summary

Milestone **V2.18.1** performed an evidence-based integrity audit and systematic correction of the results reported in Version 2.18.

### Primary Audit Verdicts:
1. **The 578 Daily 2024 Records are Strictly Regional Aggregate (`DAM_ALP_LTK`):**
   A forensic inspection of `historical_daily_movements_2024` in `data/damascus_airport.db` confirms that all 578 records originate from the **Syria Economic Monitor (World Bank / Data Partnership / AviationStack)** series. Every single record is explicitly scoped to `DAM_ALP_LTK`, representing aggregated commercial gateway operations across Damascus (DAM), Aleppo (ALP), and Latakia (LTK) combined. **Zero Damascus-specific disaggregated records exist in this series.**
   - These records are classified strictly as `regional_aggregate`.
   - They are NOT classified as DAM-specific.
   - Zero portion is allocated to DAM.
   - They are NOT used to calculate DAM-only daily or monthly totals.
   - They CANNOT fill Damascus historical coverage gaps.

2. **Zero (0) Verified Historical DAM Physical Movements Were Recovered:**
   No publicly downloadable historical dataset containing verified aircraft transponder telemetry or flight-level movement logs for Damascus International Airport was identified or recovered for the 2024–present window.

3. **Correction of Gatwick (EGKK) Relevance Scoring:**
   In V2.18, `DS-ZEN-002` (London Gatwick Airport) was scored 25/30 and marked as a "High-priority candidate (25-30)" simply because generic non-geographic criteria (open format, license, 2024 period) summed to 25. Under V2.18.1, **geographic relevance is enforced as a mandatory eligibility condition**: a dataset restricted to UK airspace (EGKK) is immediately disqualified as ineligible (<12 points), with score reduced to 5 and status set to `DISQUALIFIED_MANDATORY_CONDITION_FAILED`.

4. **Honest Download Accounting (Metadata vs. Datasets):**
   V2.18 downloaded **zero full datasets**. Only **four (4) small metadata, README, and query artifacts** totaling **37,172 bytes** were downloaded from OpenSky S3 and Harvard Dataverse. All reports and inventory records now explicitly state that only README manifests and search JSON were downloaded, never the underlying datasets.

5. **Corrected Monthly Coverage Classification (34 Months):**
   All 34 months between `2024-01` and `2026-10` now use strictly disciplined categories:
   - `2024-01` to `2024-10` (10 months): `regional_aggregate` (DAM_ALP_LTK multi-airport aggregate; 0 verified DAM movements).
   - `2024-11` and `2024-12` (2 months): `no_verified_dam_data` (SEM series terminated 2024-10-15; zero records in source).
   - `2025-01` to `2026-06` (18 months): `no_verified_dam_data` (confirmed historical data gap).
   - `2026-07` to `2026-09` (3 months): `dam_scheduled_fids` (official FIDS baseline snapshot; scheduled timetable data only, NOT physical movements).
   - `2026-10` (1 month): `live_regional_adsb` (live regional transponder fixes; 15 high-altitude overflights, 1 Beirut regional transit; 0 DAM movements).

---

## 2. Explicit Answers to Section 8 Final Decision Requirements

### 1. Whether the 578 records are DAM-specific or regional aggregate?
**The 578 records are strictly REGIONAL AGGREGATE (`DAM_ALP_LTK`).**
- **Original Dataset Identifier:** `DAM_ALP_LTK` (Syria Economic Monitor / AviationStack).
- **Original Source URL:** `https://datapartnership.org/syria-economic-monitor/notebooks/aviation/aviation_update.html`.
- **Original Publication / Provider:** Syria Economic Monitor (World Bank / Data Partnership).
- **Original Airport Scope:** `DAM_ALP_LTK` (Damascus, Aleppo, Latakia combined gateways).
- **Airport Codes Included:** DAM, ALP, LTK aggregated together.
- **Direction Representation:** Arrivals (289 rows) and Departures (289 rows) are separately represented.
- **Data Nature:** Derived transformations extracted from published Bokeh visualization models.
- **Airport Disaggregation:** Zero. No sub-totals for DAM exist.

### 2. Whether any verified DAM-specific 2024 records exist?
**No.** There are zero verified DAM-specific historical movement records in the 2024 dataset.

### 3. Corrected DAM historical coverage?
- **Verified DAM Physical Movements (2024-01 to Present):** **0 months, 0 flights.**
- **Scheduled Timetable Displays (FIDS):** **3 months** (`2026-07`, `2026-08`, `2026-09`) with 1,982 scheduled flight records across 67 consecutive calendar dates.
- **Regional Macro Benchmark Aggregate:** **10 months** (`2024-01` to `2024-10`) with 578 aggregate gateway rows across DAM_ALP_LTK.
- **Live Regional ADS-B Sample:** **1 month** (`2026-10`) with 16 transponder fixes (15 overflights, 1 regional transit; 0 DAM movements).
- **Unverified Historical Data Gap:** **20 months** (`2024-11`, `2024-12`, and `2025-01` through `2026-06`).

### 4. Corrected dataset download counts?
- **Full Datasets Downloaded:** **0** (Zero).
- **Metadata, README, and Query Artifacts Downloaded:** **4** artifacts totaling **37,172 bytes** in `data/raw/public_datasets/v2_18/`.
  1. `opensky_flights_v5_readme.txt` (360 bytes)
  2. `opensky_flights_v5_license.txt` (14,973 bytes)
  3. `opensky_aircraft_metadata_readme.txt` (554 bytes)
  4. `harvard_dataverse_damascus_search.json` (21,285 bytes)

### 5. Misleading coverage claims found and corrected?
- **Claim Corrected:** V2.18 stated that 2024 was "covered by official airport statistics for DAM" based on 578 records. -> **Corrected:** Clarified that the 578 records are `DAM_ALP_LTK` regional aggregate benchmarks, not DAM-specific data.
- **Claim Corrected:** V2.18 classified London Gatwick TMA (EGKK) as a "High-priority candidate (25-30)". -> **Corrected:** Geographic relevance made mandatory; EGKK disqualified as ineligible (<12 points).
- **Claim Corrected:** V2.18 implied 4 datasets were downloaded. -> **Corrected:** Clarified that only 4 metadata/sample README files were downloaded (37,172 bytes total).

### 6. Whether API/dashboard outputs required correction?
- The existing FastAPI endpoint `/api/movements/historical-2024` and `/api/movements/multi-airport` already returned `"scope": "DAM_ALP_LTK"` and `"source": "Syria Economic Monitor (World Bank / Data Partnership)"`, strictly preventing conflation with single-airport data.
- Monthly coverage CSV (`reports/v2_18_damascus_coverage.csv`) and staging database (`v2_18_staging.db`) were corrected to use the exact required categories (`regional_aggregate`, `dam_scheduled_fids`, `live_regional_adsb`, `no_verified_dam_data`).

### 7. Protected file hash verification?
All six protected databases and raw snapshots were verified byte-for-byte and remain 100% unchanged:
- `data/damascus_airport.db`: `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b` (MATCH)
- `data/archived_fids_staging.db`: `a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4` (MATCH)
- `data/archived_fids_analytics.db`: `e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe` (MATCH)
- `data/archived_fids_history_staging.db`: `39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f` (MATCH)
- `data/raw/snapshots/wayback_damairport_fids_20260709234230.raw`: `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf` (MATCH)
- `data/raw/snapshots/wayback_damairport_fids_20260709234230.json`: `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491` (MATCH)

### 8. Full test results?
All 385 tests in the complete repository test suite passed with 0 failures.

---

## 3. Deliverables Inventory

1. Scope Audit Report: `reports/v2_18_1_dataset_scope_audit.csv`
2. Coverage Correction Report: `reports/v2_18_1_coverage_correction.csv`
3. Integrity Verification JSON: `reports/v2_18_1_integrity_verification.json`
4. Final Forensic Audit Document: `docs/V2_18_1_FINAL_AUDIT.md`
5. Updated Monthly Coverage: `reports/v2_18_damascus_coverage.csv`
6. Updated Candidate Inventory: `reports/v2_18_dataset_inventory.csv`
7. Updated Candidate Scoring: `reports/v2_18_dataset_scoring.csv`
8. Regression Test Suite: `tests/test_v2_18_1_coverage_audit.py`
