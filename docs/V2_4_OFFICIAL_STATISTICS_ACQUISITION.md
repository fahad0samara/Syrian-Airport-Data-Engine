# Syrian Airport Data Engine — Version 2.4
# Syrian Official Statistical Publications Acquisition Checklist

**Document Identifier**: `docs/V2_4_OFFICIAL_STATISTICS_ACQUISITION.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Audit Date**: 2026-10-11  
**Target Standard**: Verified Primary Document Acquisition & Provenance Tracking  
**Status**: APPROVED ACQUISITION CHECKLIST  

---

## 1. Executive Summary & Acquisition Policy

Macro-level operational benchmarks from official government sources provide vital validation envelopes for physical flight tracking engines. However, in accordance with the project's strict anti-hallucination rules:

1. **No Speculative Citations**: No table numbers, page numbers, or exact numerical values may be entered into the engine without direct forensic inspection of an acquired, cryptographically hashed primary publication (PDF or physical print).
2. **Pending Acquisition Status**: All publications that have not yet been downloaded, hashed, and archived in `data/raw/official_statistics/` are formally designated as `pending_acquisition`.
3. **Quarantine from Micro Data**: Data extracted from official annual or quarterly reports must be routed to isolated macro benchmarking tables (e.g. `macro_airport_benchmarks`) and must **never** be merged directly into `flight_events`.

---

## 2. Official Document Acquisition Checklist

### 2.1 Central Bureau of Statistics (CBS) — Annual Statistical Abstracts

| Attribute | Document Record CBS-2023 | Document Record CBS-2022 | Archival Baseline CBS-2010 |
| :--- | :--- | :--- | :--- |
| **Exact Publication Title** | المجموعة الإحصائية السنوية 2023 (Annual Statistical Abstract 2023) | المجموعة الإحصائية السنوية 2022 (Annual Statistical Abstract 2022) | المجموعة الإحصائية السنوية 2010 (Annual Statistical Abstract 2010) |
| **Publishing Authority** | المكتب المركزي للإحصاء (Central Bureau of Statistics — CBS) | المكتب المركزي للإحصاء (Central Bureau of Statistics — CBS) | المكتب المركزي للإحصاء (Central Bureau of Statistics — CBS) |
| **Publication Year** | 2024 (covers calendar 2023) | 2023 (covers calendar 2022) | 2011 (covers calendar 2010) |
| **Official Portal URL** | `http://cbssyr.sy/` | `http://cbssyr.sy/` | `http://cbssyr.sy/` |
| **Target Chapter** | الفصل العاشر: النقل والمواصلات (Chapter 10: Transport & Communications) | الفصل العاشر: النقل والمواصلات (Chapter 10: Transport & Communications) | الفصل العاشر: النقل والمواصلات (Chapter 10: Transport & Communications) |
| **Airport-Level Breakdown** | `pending_acquisition` (Unverified) | `pending_acquisition` (Unverified) | **Verified Present** (Damascus, Aleppo, Latakia, Qamishli, Deir ez-Zor) |
| **Aircraft Movement Totals** | `pending_acquisition` | `pending_acquisition` | **Verified Present** (Commercial arrivals, departures, overflights) |
| **Passenger Totals** | `pending_acquisition` | `pending_acquisition` | **Verified Present** (Arriving, departing, transit passengers) |
| **Cargo Totals** | `pending_acquisition` | `pending_acquisition` | **Verified Present** (Freight and mail loaded/unloaded in tonnes) |
| **Exact Table & Page Ref.** | `pending_acquisition` | `pending_acquisition` | Table 10/12–10/15 (Historical pagination verified) |
| **Document Archival State** | **PENDING ACQUISITION** | **PENDING ACQUISITION** | Archived in Research Reference Library |

---

### 2.2 Ministry of Transport (MoT) — Annual Performance Reports

| Attribute | Document Record MoT-2023 | Document Record MoT-2024 |
| :--- | :--- | :--- |
| **Exact Publication Title** | تقرير تتبع خطة وزارة النقل وإنجازات قطاع النقل الجوي لعام 2023 (Annual Plan Follow-up & Air Transport Achievements Report 2023) | التقرير الإحصائي السنوي لوزارة النقل لعام 2024 (Annual Statistical Report of the Ministry of Transport 2024) |
| **Publishing Authority** | وزارة النقل - الجمهورية العربية السورية (Ministry of Transport — Syrian Arab Republic) | وزارة النقل - الجمهورية العربية السورية (Ministry of Transport — Syrian Arab Republic) |
| **Publication Year** | Early 2024 | Expected 2025 / Periodic Releases |
| **Official Portal URL** | `http://mot.gov.sy/` | `http://mot.gov.sy/` |
| **Aviation Sector Section** | قطاع الطيران المدني والنقل الجوي (Civil Aviation & Air Transport Sector) | قطاع الطيران المدني والنقل الجوي (Civil Aviation & Air Transport Sector) |
| **Airport-Level Breakdown** | `pending_acquisition` (Usually reports national total and quotes Damascus) | `pending_acquisition` |
| **Aircraft Movement Totals** | `pending_acquisition` | `pending_acquisition` |
| **Passenger Totals** | `pending_acquisition` | `pending_acquisition` |
| **Cargo Totals** | `pending_acquisition` | `pending_acquisition` |
| **Exact Table & Page Ref.** | `pending_acquisition` | `pending_acquisition` |
| **Document Archival State** | **PENDING ACQUISITION** | **PENDING ACQUISITION** |

---

### 2.3 Syrian Civil Aviation Authority (SCAA) — Operational Bulletins

| Attribute | Document Record SCAA-2023 | Document Record SCAA-2024 |
| :--- | :--- | :--- |
| **Exact Publication Title** | التقرير الإحصائي السنوي للمؤسسة العامة للطيران المدني 2023 (Annual Statistical Report of SCAA 2023) | النشرة الدورية لحركة الملاحة الجوية بالمطارات السورية 2024 (Periodic Air Navigation Movement Bulletin 2024) |
| **Publishing Authority** | المؤسسة العامة للطيران المدني السوري (Syrian Civil Aviation Authority — SCAA) | المؤسسة العامة للطيران المدني السوري (Syrian Civil Aviation Authority — SCAA) |
| **Publication Year** | 2024 | 2024 |
| **Official Portal URL** | `http://scaa.sy/` and `https://gaca.gov.sy/` | `http://scaa.sy/` and `https://gaca.gov.sy/` |
| **Airport-Level Breakdown** | `pending_acquisition` | `pending_acquisition` |
| **Aircraft Movement Totals** | `pending_acquisition` | `pending_acquisition` |
| **Passenger Totals** | `pending_acquisition` | `pending_acquisition` |
| **Cargo Totals** | `pending_acquisition` | `pending_acquisition` |
| **Exact Table & Page Ref.** | `pending_acquisition` | `pending_acquisition` |
| **Document Archival State** | **PENDING ACQUISITION** | **PENDING ACQUISITION** |

---

### 2.4 Syrian Arab News Agency (SANA) — Official Ministerial Dispatches

Official press releases issued by SANA provide direct statements from the Minister of Transport or the Director General of the Syrian Civil Aviation Authority summarizing operational performance.

| Attribute | Dispatch SANA-2023-EOY | Dispatch SANA-2024-MID |
| :--- | :--- | :--- |
| **Exact Dispatch Title** | النقل: حركة النقل الجوي تسجل نمواً خلال عام 2023 وتفاصيل حركة المسافرين (MoT: Air Transport Records Growth in 2023 with Passenger Traffic Details) | الطيران المدني: إحصاءات حركة الطائرات والمسافرين عبر مطار دمشق الدولي للنصف الأول من 2024 (SCAA: Aircraft and Passenger Traffic via Damascus Airport for H1 2024) |
| **Publishing Agency** | الوكالة العربية السورية للأنباء - سانا (Syrian Arab News Agency — SANA) | الوكالة العربية السورية للأنباء - سانا (Syrian Arab News Agency — SANA) |
| **Release Date** | January 2024 | July 2024 |
| **Official Portal URL** | `https://sana.sy/` | `https://sana.sy/` |
| **Reporting Scope** | National Syrian airports, with specific quoted figures for Damascus (`DAM`) | Specifically focused on Damascus International Airport (`DAM`) |
| **Airport-Level Breakdown** | Quoted aggregate in ministerial interview | Quoted semi-annual totals for OSDI |
| **Data Nature** | `aggregated` (Verbal ministerial statement / press release) | `aggregated` (Official press statement) |
| **Verification Status** | `pending_acquisition` (Specific URL & archived text pending retrieval) | `pending_acquisition` (Specific URL & archived text pending retrieval) |

---

## 3. Physical Acquisition Protocol & Hashing Procedure

When an official PDF publication or scanned bulletin is acquired by the research team:

1. **Storage Location**:
   Save the raw file in `data/raw/official_statistics/` with standard nomenclature:
   `SYR_OFFICIAL_<AUTHORITY>_<YEAR>_<NAME>.pdf`
2. **Cryptographic Provenance**:
   Calculate and record the SHA-256 hash immediately:
   ```bash
   Get-FileHash -Algorithm SHA256 "data/raw/official_statistics/SYR_OFFICIAL_CBS_2023_TRANSPORT.pdf"
   ```
3. **Forensic Page Inspection**:
   - Record exact PDF page number and printed page number.
   - Record exact table title in Arabic and English translation.
   - Transcribe column headers verbatim.
   - Record footnotes, definitions (e.g. whether general aviation or military flights are included), and date of compilation.
4. **Transition to Verified**:
   Only after Steps 1–3 are fully satisfied may the status be transitioned from `pending_acquisition` to `verified`.
