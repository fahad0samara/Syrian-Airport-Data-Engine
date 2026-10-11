# Syrian Airport Data Engine — Version 2.12.2
# Unresolved Source Claims & Evidentiary Gaps Dossier

**Document Identifier**: `docs/V2_12_2_UNRESOLVED_SOURCE_CLAIMS.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Target Airspace**: Damascus Flight Information Region (`OSTT_FIR`)  
**Scope**: In-Depth Forensic Analysis of Missing Sources, Period Uncertainties, Carrier Identification Gaps, and Airspace Segregation  
**Machine-Readable Companion**: `reports/v2_12_2_source_verification.csv`  
**Status**: APPROVED FORENSIC GAP DOSSIER  
**Verification Invariant**: Production database `data/damascus_airport.db` SHA-256 remains bit-for-bit identical (`c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`).

---

## 1. Executive Summary & Audit Context

Under the data integrity standards of the Syrian Airport Data Engine, statistics that cannot be traced to a permanent canonical URL, an archived cryptographically hashed document, or an accessible article permalink cannot be accepted as fully verified.

The Version 2.12.2 audit systematically identified four discrete categories of evidentiary uncertainty across the 31 staged macro benchmark records:

1. **Missing Canonical Primary SCAA/SANA URLs (26 records)**: Official monthly and annual statistics widely circulated in secondary media digests, but direct canonical article slugs on `sana.sy` or raw PDF bulletins on `scaa.sy` remain unresolved.
2. **The April 2026 Reporting Boundary Discrepancy (5 airport records)**: A substantive conflict between the quoted Arabic text (`في نيسان 2026` / *"in April 2026"*) and the staged post-reopening operational window (`2026-04-08` to `2026-04-30`).
3. **Carrier-Level Disaggregation Vacuum (5 operating airline records)**: Source texts explicitly state the aggregate number of operating airlines (9, 12, 13, 16, 17), but omit all airline identities, names, and operational definitions.
4. **National Airspace Overflights Scope Conflation (2 records)**: Transit flights across Syrian sovereign airspace (`OSTT_FIR`) cannot be combined with Damascus International Airport runway throughput.

---

## 2. Dossier Item 1: Missing Canonical SCAA/SANA Bulletins (26 Records)

### 2.1 The Nature of the Evidence Gap
The following 26 benchmark records cite the Syrian Arab News Agency (SANA) and the General Authority of Civil Aviation and Air Transport (SCAA):
- **Calendar Year 2025 Annual Operational Totals** (4 records): 12,476 flights; 1,434,998 total passengers (715,392 arr / 719,606 dep).
- **Calendar Year 2026 Monthly Bulletins** (22 records): April (6 records), May (5 records), July (5 records), September (6 records).

While these statistics circulated widely in Syrian economic reports, business news roundups, and syndicated media dispatches:
- Direct, queryable canonical URLs on `http://sana.sy/` could not be resolved during automated or manual inspection.
- No direct PDF bulletins from the Ministry of Transport or SCAA are archived locally in `data/historical_sample_review/official_statistics/`.
- Descriptive English titles (e.g. `'Civil Aviation Annual Report 2025: Damascus Airport Operational Performance'`) and paragraph numbers were synthetically populated as research placeholders.

### 2.2 Evidentiary Standing
- **Source Access Status**: `not_found`
- **Verification Status**: `unverified_source_url`
- **Evidence Grade**: `C` (Citation metadata exists in database, but original source cannot currently be retrieved or verified).
- **Resolution Requirement**: To promote any of these 26 records to `verified_primary`, an authentic digital copy of the SCAA Annual/Monthly Statistical Report (or direct authenticated SANA wire dispatch) must be obtained and archived in `data/` with its SHA-256 hash.

---

## 3. Dossier Item 2: The April 2026 Reporting Boundary Discrepancy (5 Records)

### 3.1 The Evidence Conflict
- **Affected Benchmarks**:
  - `bmk_2026_04_flights`: 492 flights
  - `bmk_2026_04_passengers_total`: 34,347 passengers
  - `bmk_2026_04_passengers_arr`: 18,385 arriving passengers
  - `bmk_2026_04_passengers_dep`: 15,962 departing passengers
  - `bmk_2026_04_airlines`: 9 operating airlines
- **The Quoted Excerpt**: `تسجيل 492 رحلة جوية في نيسان 2026` (*"recording 492 flights in April 2026"*).
- **The Staged Dates**: `reporting_period_start = '2026-04-08'`, `reporting_period_end = '2026-04-30'` (23 days).
- **The Operational Event**: Damascus International Airport was officially reopened for scheduled commercial flights on **April 8, 2026**, following extensive infrastructure rehabilitation.

### 3.2 Analysis & Epistemic Decision
1. **The Conflict**: The text excerpt quotes "in April 2026", which in standard aviation reporting denotes a full calendar month (April 1–30). The attribution to April 8–30 was an inference made by project engineers based on the known reopening date.
2. **The Unresolved Question**: Did the SCAA statistic cover only the active post-reopening period (April 8–30), or did it represent all flights during calendar April (with zero flights before April 8, or including pre-reopening diplomatic/test flights)?
3. **Strict Epistemic Rule Enforced**:
   - In accordance with V2.12.1 and V2.12.2 rules, **we do not assume April 8–30 from the reopening date, nor do we invent a replacement period**.
   - `period_support_status` is formally classified as **`unresolved`**.
   - `excerpt_match_status` is classified as **`partial_match`** (the numerical value matches, but the period window is ambiguous).
   - `reporting_period_status` is set to **`unresolved_period_boundary`**.
   - The staged dates (`2026-04-08` to `2026-04-30`) are preserved with an explicit uncertainty flag until the primary SCAA bulletin clarifies the exact coverage dates.

---

## 4. Dossier Item 3: The Carrier-Level Disaggregation Vacuum (5 Records)

### 4.1 The Evidence Gap
- **Affected Benchmarks**:
  - `bmk_2025_h1_reported_airlines`: 12 airlines (Jan 7 to Jul 7, 2025)
  - `bmk_2026_04_airlines`: 9 airlines (April 2026)
  - `bmk_2026_05_airlines`: 13 airlines (May 2026)
  - `bmk_2026_07_airlines`: 16 airlines (July 2026)
  - `bmk_2026_09_airlines`: 17 airlines (September 2026)
- **The Excerpts**:
  - `عملت 12 شركة طيران في المطار خلال هذه الفترة`
  - `عملت 9 شركات طيران عبر المطار`
  - `نفذت الرحلات 13 شركة طيران`
  - `شغلت 16 شركة طيران رحلاتها في تموز`
  - `شاركت 17 شركة طيران في تنفيذ الرحلات`

### 4.2 Epistemic Distinction
- **What is Supported**: The source text directly and unambiguously reports the aggregate numerical count (9, 12, 13, 16, 17). Therefore, `excerpt_supports_value = True` and `supports_numerical_count = True`.
- **What is Missing**: **Zero carrier names or ICAO codes are provided**.
  - No list of airlines exists in any cited source.
  - No operational criteria are stated: Did SCAA count cargo operators (e.g. Cham Wings Cargo), government VIP flights, foreign charter operators, or only scheduled passenger airlines?
- **Strict Rule Enforced**:
  - We do not infer or hallucinate carrier identities.
  - The records remain graded as **Grade C** with `has_carrier_level_detail = False`.
  - The claims are kept as `unverified_source_url` (except H1 which is `verified_secondary`).

---

## 5. Dossier Item 4: Airspace Transit Statistics Segregation (2 Records)

### 5.1 The Evidence Scope
- **Affected Benchmarks**:
  - `bmk_2026_04_overflights`: 2,523 transit aircraft (April 2026)
  - `bmk_2026_09_overflights`: 19,951 transit aircraft (September 2026)
- **The Excerpts**:
  - `سجلت الأجواء السورية عبور 2,523 طائرة خلال شهر نيسان` (*"Syrian airspace recorded 2,523 transit aircraft during April"*)
  - `عدد الطائرات العابرة للأجواء السورية بلغ 19,951 طائرة` (*"Number of aircraft transiting Syrian airspace was 19,951"*)

### 5.2 Segregation from Airport Operations
- Overflights represent upper airspace navigation events (`OSTT_FIR` / Damascus Area Control Centre), not ground operations at Damascus International Airport (`DAM`).
- They do not use runways, taxiways, gates, or passenger terminals.
- **Rule Enforced**:
  - Tagged with `is_airport_throughput = 0`.
  - Excluded from any Damascus airport throughput or movement queries.
  - Preserved in the staging layer for future migration to a standalone Syrian FIR statistics ledger (`syrian_fir_overflights_ledger`).

---

## 6. Dossier Item 5: AksAlSer H1 2025 Missing Article Permalink (5 Records)

### 6.1 The Evidence Status
- **Target Records**:
  - `bmk_2025_h1_reported_flights`: 1,870 flights
  - `bmk_2025_h1_reported_passengers_total`: 353,282 passengers
  - `bmk_2025_h1_reported_passengers_arr`: 178,728 arriving passengers
  - `bmk_2025_h1_reported_passengers_dep`: 174,554 departing passengers
  - `bmk_2025_h1_reported_airlines`: 12 airlines
- **Source**: `General Authority of Civil Aviation and Air Transport (SCAA) / AksAlSer`
- **Quoted Text**: Verbatim Arabic transcript of the SCAA Director General press conference held on 2025-07-15, detailing 1,619 passenger, 159 delegation, 66 Hajj, and 26 relief flights.
- **The Source URL**: `https://aksalser.com/` (root domain).

### 6.2 Why Grade C is Enforced
- Under V2.12.1 and V2.12.2 rules, Grade B strictly requires an accessible direct article permalink and a matching excerpt.
- A root domain URL (`https://aksalser.com/`) is insufficient because visiting it does not retrieve the historical article.
- Because no local HTML/PDF snapshot is stored in `data/`, the source access status is **`homepage_only`**, and the evidence grade is **`Grade C`**.
- `verification_status` remains preserved as **`verified_secondary`**.
- **Resolution Step**: Update `source_url` with the exact article slug or archive an offline snapshot in `data/historical_sample_review/official_statistics/` when web access is permitted.

---

## 7. Action Matrix for Historical Evidence Resolution

| Benchmark Group | Current Evidence Grade | Current Verification Status | Source Access Status | Immediate Technical Constraint | Future Resolution Action |
|:---|:---:|:---:|:---:|:---|:---|
| **AksAlSer H1 2025 (5 Records)** | **C** | `verified_secondary` | `homepage_only` | Missing direct article permalink | Locate canonical article permalink on `aksalser.com`; archive HTML snapshot. |
| **2025 Annual Totals (4 Records)** | **C** | `unverified_source_url` | `not_found` | Unresolved primary SANA/SCAA URL | Obtain SCAA 2025 Annual Statistical Bulletin PDF; archive with SHA-256. |
| **April 2026 Airport Movements (5 Records)** | **C** | `unverified_source_url` | `not_found` | Unresolved reporting window & missing primary URL | Inspect primary SCAA April 2026 bulletin to verify exact coverage dates. |
| **April 2026 Overflights (1 Record)** | **C** | `unverified_source_url` | `not_found` | National airspace metric in airport staging | Transfer to dedicated `syrian_fir_overflights_ledger`. |
| **May 2026 Monthly Stats (5 Records)** | **C** | `unverified_source_url` | `not_found` | Missing primary SCAA/SANA bulletin | Obtain SCAA May 2026 Air Traffic Bulletin PDF; archive with SHA-256. |
| **July 2026 Monthly Stats (5 Records)** | **C** | `unverified_source_url` | `not_found` | Missing primary SCAA/SANA bulletin | Obtain SCAA July 2026 Summer Bulletin PDF; archive with SHA-256. |
| **September 2026 Airport Movements (5 Records)** | **C** | `unverified_source_url` | `not_found` | Missing primary SCAA/SANA bulletin | Obtain SCAA September 2026 Traffic Performance PDF; archive with SHA-256. |
| **September 2026 Overflights (1 Record)** | **C** | `unverified_source_url` | `not_found` | National airspace metric in airport staging | Transfer to dedicated `syrian_fir_overflights_ledger`. |

---

## 8. Conclusion

The Version 2.12.2 audit establishes total transparency regarding the evidence underlying macro aviation statistics. By enforcing honest, empirical reporting standards, the Syrian Airport Data Engine eliminates speculative assumptions, maintains strict data safety, and prepares a pristine foundation for future historical ingestion.
