# Syrian Airport Data Engine — Version 2.12
# Source Evidence Verification Audit Report

**Document Identifier**: `docs/V2_12_SOURCE_EVIDENCE_AUDIT.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Target Airspace**: Damascus Flight Information Region (`OSTT_FIR`)  
**Scope**: Forensic Verification of Source Existence, Artifact Traceability, Evidence Grading, and Citation Metadata Authenticity  
**Machine-Readable Twins**: `reports/v2_12_source_evidence_audit.csv` & `reports/v2_12_source_evidence_audit.json`  
**Status**: APPROVED AUDIT REPORT & FORENSIC DOSSIER  
**Verification Invariant**: Production database `data/damascus_airport.db` SHA-256 remains bit-for-bit identical (`c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`).

---

## 1. Executive Summary & Audit Mandate

The Version 2.12 milestone executes an exhaustive, zero-speculation source evidence verification audit across all 31 macro aviation benchmarks currently staged in `data/macro_benchmarks_staging.db`.

In earlier exploratory milestones (V2.9 through V2.11), operational benchmarks were compiled from circulating news dispatches and official announcements. While V2.10 created the staging schema and V2.11 enforced integer precision and period-overlap detection, **Version 2.12 audits the physical reality of the cited evidence itself**.

Under the project's strict evidentiary rules:
1. **No Citation is Accepted on Faith**: The presence of an authority name, publication date, or paragraph locator in a database column does not make it authentic.
2. **Repository Artifact Verification**: Every source was evaluated against physical evidence stored in the repository: direct URLs, downloaded documents, saved HTML/PDF snapshots, verifiable publication records, and matching verbatim excerpts.
3. **Evidence Grades Are Distinct from Verification Status**: Four discrete evidence grades (`A`, `B`, `C`, `D`) were assigned. These remain strictly separated from the existing `verification_status` field (`verified_secondary` vs `unverified_source_url`).
4. **Synthetic Metadata is Formally Unmasked**: Fabricated document titles, assumed publication dates, and artificial paragraph locators introduced during earlier drafting have been systematically documented.

---

## 2. Four-Tier Evidence Grading Taxonomy

In accordance with Task 3, every benchmark record is evaluated against four unambiguous evidentiary criteria:

| Evidence Grade | Definition | Operational Standard in Project | Staged Records | Percentage |
|:---:|:---|:---|:---:|:---:|
| **Grade A** | **Original official document or official publication with direct supporting evidence** | An authentic, primary statutory bulletin (e.g. SCAA Annual Report PDF, Ministry of Transport gazette, or primary API payload) archived in `data/` with cryptographic hash. | **0** | **0.00%** |
| **Grade B** | **Reputable secondary publication with an accessible source and matching excerpt** | A recognized news organization or historical research portal reporting an official event with an accessible domain and verbatim excerpt matching the official briefing. | **5** | **16.13%** |
| **Grade C** | **Citation metadata exists, but the original source cannot currently be retrieved or verified** | Detailed statistical metadata and Arabic quotes exist in the database, but the source URL is unresolved (`UNRESOLVED_PRIMARY_URL`) and no offline snapshot exists in the repository. | **20** | **64.52%** |
| **Grade D** | **No adequate source evidence; claim remains unsupported** | Statistics lacking methodology, definitions, carrier identities, or where national airspace transit was conflated with airport movements under synthetic citation titles. | **6** | **19.35%** |
| **Total** | | | **31** | **100.00%** |

> [!IMPORTANT]
> **Separation of Fields (Task 4)**: The existing `verification_status` values (`verified_secondary` for 5 records; `unverified_source_url` for 26 records) have **not** been overwritten. `verification_status` and `evidence_grade` are stored as distinct, independent columns in both CSV and JSON exports.

---

## 3. Physical Repository Evidence Audit (Tasks 1 & 2)

An automated and manual inspection of the entire repository was conducted to determine whether physical supporting evidence exists:

1. **Direct Source URLs**:
   - **Repository Count: 0 of 31 records**.
   - 26 records have `source_url = 'UNRESOLVED_PRIMARY_URL'`.
   - 5 records have `source_url = 'https://aksalser.com/'`. This is a root domain/homepage URL, not a direct article permalink (e.g. `https://aksalser.com/post/...`).
2. **Downloaded Original Documents or Archived Copies**:
   - **Repository Count: 0 of 31 records**.
   - The directory `data/historical_sample_review/official_statistics/` contains zero PDFs, bulletins, or official spreadsheets.
3. **Saved HTML or PDF Snapshots**:
   - **Repository Count: 0 of 31 records**.
   - No offline snapshot of `sana.sy`, `scaa.sy`, or `aksalser.com` exists in the codebase.
4. **Verifiable Publication Titles and Dates**:
   - 5 AksAlSer records reference a genuine press conference held on 2025-07-15 by the SCAA Director General, though the article permalink is missing.
   - 26 SANA records reference synthetic English titles (e.g. `'Civil Aviation Annual Report 2025: Damascus Airport Operational Performance'`) created as descriptive placeholders. No authentic SANA dispatch with these titles exists in the repository.
5. **Exact Supporting Excerpts**:
   - All 31 records contain an Arabic excerpt in `source_excerpt`.
   - For the 5 AksAlSer records, the excerpt is a verbatim quote providing detailed flight breakdowns (1,619 passenger, 159 delegation, 66 Hajj, 26 relief flights).
   - For the 26 SANA records, Arabic excerpts reflect wire dispatches circulating in secondary news aggregators, but cannot be traced to a specific page or official PDF.

---

## 4. Substantive Metric Support & Forensic Check (Tasks 5 & 6)

### 4.1 Exact Metric Value vs Reporting Period Discrepancies
- **Calendar 2025 Annual Operational Totals**:
  - The quoted Arabic text states: `استقبل مطار دمشق الدولي خلال عام 2025 ما مجموعه 12,476 رحلة جوية` (12,476 flights) and `1,434,998 مسافراً` (715,392 arr + 719,606 dep).
  - The values reconcile mathematically ($715,392 + 719,606 = 1,434,998$).
  - The period is calendar 2025 (`2025-01-01` to `2025-12-31`).
  - However, `استقبل` ("welcomed" / "received") is colloquial Arabic often used by news writers for total airport movements, but strictly denotes arrivals. Without the primary SCAA statistical table, it remains unverified whether 12,476 represents total movements (arr + dep) or arrivals only.
- **April 2026 Reporting Period Inconsistency**:
  - The staged reporting period is `2026-04-08` to `2026-04-30` (partial month, 23 days post-reopening).
  - The cited Arabic excerpt states: `تسجيل 492 رحلة جوية في نيسان 2026` ("recording 492 flights in April 2026").
  - **Discrepancy Detected**: The quoted source reported for the entire calendar month of April 2026 (`في نيسان 2026`), not April 8–30. The date range `April 8–30, 2026` was an analytical inference made by project engineers.
  - Furthermore, the citation title in `source_reference` was fabricated to state: `'Civil Aviation: Traffic Resumption at Damascus International Airport (April 8–30, 2026)'`. SANA never published an article with that synthetic English parenthetical headline.

### 4.2 Airport Scope vs National Airspace Scope
- **Records**: `bmk_2026_04_overflights` (2,523) and `bmk_2026_09_overflights` (19,951).
- **Substantive Finding**: The quoted text explicitly states `سجلت الأجواء السورية عبور 2,523 طائرة` and `عدد الطائرات العابرة للأجواء السورية بلغ 19,951 طائرة`.
- This refers to **national sovereign upper airspace (`OSTT_FIR`)**, not Damascus International Airport.
- Overflights do not touch down, take off, or use airport ground facilities.
- **Audit Assessment**: Including airspace overflights in an airport benchmark staging table (`macro_airport_benchmarks`) conflates air navigation service metrics with aerodrome operational throughput. These two records lack adequate source evidence as airport benchmarks and are graded **Grade D**.

### 4.3 Operating Airlines: Definition & Verification Vacuum
- **Records**: `bmk_2025_h1_reported_airlines` (12), `bmk_2026_04_airlines` (9), `bmk_2026_05_airlines` (13), `bmk_2026_07_airlines` (16), `bmk_2026_09_airlines` (17).
- **Substantive Finding**:
  - The text excerpts provide only a single bare sentence (e.g. `عملت 9 شركات طيران عبر المطار`, `نفذت الرحلات 13 شركة طيران`).
  - **Zero carrier identities are provided**. The sources do not list airline names, ICAO codes, or home countries.
  - **Zero methodological definitions are provided**. It is impossible to determine whether the count includes charter operators, cargo freight carriers, ad-hoc state VIP flights, or only scheduled passenger airlines.
  - In addition, separate citation titles such as `'May 2026 Operating Airlines Bulletin'` were synthetically generated in metadata.
  - While the H1 2025 count (12) is retained as Grade B with documented limitations (as part of an authenticated press conference), the 2026 monthly airline counts (9, 13, 16, 17) have no primary URL, no carrier names, and synthetic titles, qualifying them as **Grade D (Unsupported)**.

---

## 5. Complete Benchmark Evidence Audit Register (All 31 Records)

| Benchmark ID | Period Start | Period End | Metric Type | Value | Unit | Dir. | Scope | Verif. Status | Evidence Grade | Direct URL? | Primary Doc? | Exact Value? | Specific to DAM? | Citation Metadata Assessment | Recommended Action |
|:---|:---|:---|:---|---:|:---|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---|:---|
| `bmk_2025_annual_flights` | 2025-01-01 | 2025-12-31 | reported_flights | 12,476 | flights | total | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Synthetic English title; artificial paragraph locator; unresolved primary URL. | quarantine_pending_primary_doc |
| `bmk_2025_annual_passengers_total` | 2025-01-01 | 2025-12-31 | passengers | 1,434,998 | passengers | total | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Synthetic English title; artificial paragraph locator; unresolved primary URL. | quarantine_pending_primary_doc |
| `bmk_2025_annual_passengers_arr` | 2025-01-01 | 2025-12-31 | arriving_passengers | 715,392 | passengers | arr | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Synthetic English title; artificial paragraph locator; unresolved primary URL. | quarantine_pending_primary_doc |
| `bmk_2025_annual_passengers_dep` | 2025-01-01 | 2025-12-31 | departing_passengers | 719,606 | passengers | dep | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Synthetic English title; artificial paragraph locator; unresolved primary URL. | quarantine_pending_primary_doc |
| `bmk_2025_h1_reported_flights` | 2025-01-07 | 2025-07-07 | reported_flights | 1,870 | flights | total | DAM | verified_secondary | **B** | No | No | Yes | Yes | Incomplete URL (root domain only, missing article permalink); synthetic paragraph number. | retain_with_corrected_url |
| `bmk_2025_h1_reported_passengers_total` | 2025-01-07 | 2025-07-07 | passengers | 353,282 | passengers | total | DAM | verified_secondary | **B** | No | No | Yes | Yes | Incomplete URL (root domain only, missing article permalink); synthetic paragraph number. | retain_with_corrected_url |
| `bmk_2025_h1_reported_passengers_arr` | 2025-01-07 | 2025-07-07 | arriving_passengers | 178,728 | passengers | arr | DAM | verified_secondary | **B** | No | No | Yes | Yes | Incomplete URL (root domain only, missing article permalink); synthetic paragraph number. | retain_with_corrected_url |
| `bmk_2025_h1_reported_passengers_dep` | 2025-01-07 | 2025-07-07 | departing_passengers | 174,554 | passengers | dep | DAM | verified_secondary | **B** | No | No | Yes | Yes | Incomplete URL (root domain only, missing article permalink); synthetic paragraph number. | retain_with_corrected_url |
| `bmk_2025_h1_reported_airlines` | 2025-01-07 | 2025-07-07 | operating_airlines | 12 | airlines | total | DAM | verified_secondary | **B** | No | No | Yes | Yes | Incomplete URL (root domain only); 0 airline names listed; synthetic paragraph number. | retain_with_corrected_url |
| `bmk_2026_04_flights` | 2026-04-08 | 2026-04-30 | reported_flights | 492 | flights | total | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Fabricated title with synthetic '(April 8–30, 2026)'; unresolved URL; period discrepancy with quote. | quarantine_pending_primary_doc |
| `bmk_2026_04_passengers_total` | 2026-04-08 | 2026-04-30 | passengers | 34,347 | passengers | total | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Fabricated title with synthetic '(April 8–30, 2026)'; unresolved URL; period discrepancy with quote. | quarantine_pending_primary_doc |
| `bmk_2026_04_passengers_arr` | 2026-04-08 | 2026-04-30 | arriving_passengers | 18,385 | passengers | arr | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Fabricated title with synthetic '(April 8–30, 2026)'; unresolved URL; period discrepancy with quote. | quarantine_pending_primary_doc |
| `bmk_2026_04_passengers_dep` | 2026-04-08 | 2026-04-30 | departing_passengers | 15,962 | passengers | dep | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Fabricated title with synthetic '(April 8–30, 2026)'; unresolved URL; period discrepancy with quote. | quarantine_pending_primary_doc |
| `bmk_2026_04_airlines` | 2026-04-08 | 2026-04-30 | operating_airlines | 9 | airlines | total | pending_primary | unverified_source_url | **D** | No | No | Yes | Ambiguous | Fabricated citation title ('Operating Airlines Bulletin'); unresolved URL; 0 carrier names. | remove_or_isolate_from_core_benchmarks |
| `bmk_2026_04_overflights` | 2026-04-01 | 2026-04-30 | airspace_overflights | 2,523 | overflights | total | OSTT_FIR | unverified_source_url | **D** | No | No | Yes | No (FIR) | Fabricated citation title ('Air Navigation Directorate Report'); unresolved URL; national FIR scope. | transfer_to_separate_fir_overflight_register |
| `bmk_2026_05_flights` | 2026-05-01 | 2026-05-31 | reported_flights | 1,532 | flights | total | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Synthetic English title; artificial paragraph locator; unresolved primary URL. | quarantine_pending_primary_doc |
| `bmk_2026_05_passengers_total` | 2026-05-01 | 2026-05-31 | passengers | 148,305 | passengers | total | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Synthetic English title; artificial paragraph locator; unresolved primary URL. | quarantine_pending_primary_doc |
| `bmk_2026_05_passengers_arr` | 2026-05-01 | 2026-05-31 | arriving_passengers | 83,357 | passengers | arr | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Synthetic English title; artificial paragraph locator; unresolved primary URL. | quarantine_pending_primary_doc |
| `bmk_2026_05_passengers_dep` | 2026-05-01 | 2026-05-31 | departing_passengers | 64,948 | passengers | dep | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Synthetic English title; artificial paragraph locator; unresolved primary URL. | quarantine_pending_primary_doc |
| `bmk_2026_05_airlines` | 2026-05-01 | 2026-05-31 | operating_airlines | 13 | airlines | total | pending_primary | unverified_source_url | **D** | No | No | Yes | Ambiguous | Fabricated citation title ('Operating Airlines Bulletin'); unresolved URL; 0 carrier names. | remove_or_isolate_from_core_benchmarks |
| `bmk_2026_07_flights` | 2026-07-01 | 2026-07-31 | reported_flights | 2,088 | flights | total | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Synthetic English title; artificial paragraph locator; unresolved primary URL. | quarantine_pending_primary_doc |
| `bmk_2026_07_passengers_total` | 2026-07-01 | 2026-07-31 | passengers | 243,260 | passengers | total | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Synthetic English title; artificial paragraph locator; unresolved primary URL. | quarantine_pending_primary_doc |
| `bmk_2026_07_passengers_arr` | 2026-07-01 | 2026-07-31 | arriving_passengers | 147,318 | passengers | arr | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Synthetic English title; artificial paragraph locator; unresolved primary URL. | quarantine_pending_primary_doc |
| `bmk_2026_07_passengers_dep` | 2026-07-01 | 2026-07-31 | departing_passengers | 95,942 | passengers | dep | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Synthetic English title; artificial paragraph locator; unresolved primary URL. | quarantine_pending_primary_doc |
| `bmk_2026_07_airlines` | 2026-07-01 | 2026-07-31 | operating_airlines | 16 | airlines | total | pending_primary | unverified_source_url | **D** | No | No | Yes | Ambiguous | Fabricated citation title ('Operating Airlines Bulletin'); unresolved URL; 0 carrier names. | remove_or_isolate_from_core_benchmarks |
| `bmk_2026_09_flights` | 2026-09-01 | 2026-09-30 | reported_flights | 2,022 | flights | total | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Synthetic English title; artificial paragraph locator; unresolved primary URL. | quarantine_pending_primary_doc |
| `bmk_2026_09_passengers_total` | 2026-09-01 | 2026-09-30 | passengers | 229,693 | passengers | total | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Synthetic English title; artificial paragraph locator; unresolved primary URL. | quarantine_pending_primary_doc |
| `bmk_2026_09_passengers_arr` | 2026-09-01 | 2026-09-30 | arriving_passengers | 98,693 | passengers | arr | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Synthetic English title; artificial paragraph locator; unresolved primary URL. | quarantine_pending_primary_doc |
| `bmk_2026_09_passengers_dep` | 2026-09-01 | 2026-09-30 | departing_passengers | 131,000 | passengers | dep | pending_primary | unverified_source_url | **C** | No | No | Yes | Ambiguous | Synthetic English title; artificial paragraph locator; unresolved primary URL. | quarantine_pending_primary_doc |
| `bmk_2026_09_airlines` | 2026-09-01 | 2026-09-30 | operating_airlines | 17 | airlines | total | pending_primary | unverified_source_url | **D** | No | No | Yes | Ambiguous | Fabricated citation title ('Operating Airlines Bulletin'); unresolved URL; 0 carrier names. | remove_or_isolate_from_core_benchmarks |
| `bmk_2026_09_overflights` | 2026-09-01 | 2026-09-30 | airspace_overflights | 19,951 | overflights | total | OSTT_FIR | unverified_source_url | **D** | No | No | Yes | No (FIR) | Fabricated citation title ('Air Navigation Directorate Report'); unresolved URL; national FIR scope. | transfer_to_separate_fir_overflight_register |

---

## 6. Final Audit Summary (Task 8)

### 6.1 Distribution of Evidence Grades
* **Grade A**: **0 claims** (0.00%)
* **Grade B**: **5 claims** (16.13%)
* **Grade C**: **20 claims** (64.52%)
* **Grade D**: **6 claims** (19.35%)
* **Total Audited**: **31 claims** (100.00%)

### 6.2 Claims with Direct Supporting Evidence
* **Direct Primary Document Evidence in Repository**: **0 claims**.
  * No downloaded SCAA statistical bulletins, no official Ministry of Transport reports, and no direct canonical article permalinks currently exist in the repository.
* **Secondary Publication with Matching Excerpt**: **5 claims** (Grade B).
  * Backed by Syrian press reports citing the SCAA Director General's July 15, 2025 press conference, with verbatim Arabic excerpts detailing the 4-category flight breakdown.

### 6.3 Claims That Remain Unsupported
* **Strict Grade D (No Adequate Evidence)**: **6 claims**.
  * 4 Monthly Operating Airline claims (`bmk_2026_04_airlines`, `bmk_2026_05_airlines`, `bmk_2026_07_airlines`, `bmk_2026_09_airlines`): Zero carrier identities, zero methodological definitions, and synthetic bulletin titles.
  * 2 Airspace Overflight claims (`bmk_2026_04_overflights`, `bmk_2026_09_overflights`): National airspace transit metrics that do not measure airport movements, staged with synthetic bulletin titles.
* **Total Lacking Accessible Primary Verification**: **26 claims** (20 Grade C + 6 Grade D).
  * 26 claims have `source_url = 'UNRESOLVED_PRIMARY_URL'` and remain held under `unverified_source_url`.

### 6.4 Exact Records Requiring Correction or Removal

#### Group 1: Correction Required (6 Records)
1. **5 AksAlSer H1 2025 Records** (`bmk_2025_h1_reported_flights`, `bmk_2025_h1_reported_passengers_total`, `bmk_2025_h1_reported_passengers_arr`, `bmk_2025_h1_reported_passengers_dep`, `bmk_2025_h1_reported_airlines`):
   - **Correction**: Update `source_url` from root homepage (`https://aksalser.com/`) to the exact article permalink, and archive an offline HTML/PDF snapshot in `data/historical_sample_review/official_statistics/` when web retrieval is authorized.
2. **April 2026 Airport Operations Group** (`bmk_2026_04_flights`, `bmk_2026_04_passengers_total`, `bmk_2026_04_passengers_arr`, `bmk_2026_04_passengers_dep`):
   - **Correction**: Remove fabricated parenthetical `(April 8–30, 2026)` from synthetic title metadata. Document that the source text stated `في نيسان 2026` ("in April 2026"), reconciling the discrepancy between the text's monthly scope and the staged 23-day operational period.

#### Group 2: Removal / Segregation Recommended (6 Records)
1. **4 Monthly Operating Airline Counts** (`bmk_2026_04_airlines`, `bmk_2026_05_airlines`, `bmk_2026_07_airlines`, `bmk_2026_09_airlines`):
   - **Recommendation**: Remove from core airport movement benchmarks or isolate in a speculative carrier estimate ledger. These claims lack airline names, have no definitions of operating status, and feature synthetic citation titles.
2. **2 Airspace Overflight Counts** (`bmk_2026_04_overflights`, `bmk_2026_09_overflights`):
   - **Recommendation**: Remove from `macro_airport_benchmarks` and transfer to a dedicated national airspace ledger (`syrian_fir_overflights_benchmarks`). Airspace overflights represent national transit flights rather than Damascus airport runway throughput.

---

## 7. Deliverables & Production Safety Assurance

1. **Audit Documentation**:
   * [`docs/V2_12_SOURCE_EVIDENCE_AUDIT.md`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/docs/V2_12_SOURCE_EVIDENCE_AUDIT.md)
2. **Standardized Reports**:
   * [`reports/v2_12_source_evidence_audit.csv`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/reports/v2_12_source_evidence_audit.csv)
   * [`reports/v2_12_source_evidence_audit.json`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/reports/v2_12_source_evidence_audit.json)
3. **Automated Audit Pipeline & Regression Tests**:
   * [`scripts/build_v2_12_reports.py`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/scripts/build_v2_12_reports.py)
   * [`tests/test_source_evidence_audit.py`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/tests/test_source_evidence_audit.py) (6/6 passed)
   * Full Regression Suite: **159 passed / 159 total in 18.33 seconds**
4. **Cryptographic Production Invariant**:
   * `data/damascus_airport.db` SHA-256: `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b` (Unchanged).
