# Syrian Airport Data Engine — Version 2.13.1
# Internet Archive / Wayback Machine Availability Audit

**Document Identifier**: `docs/V2_13_1_WAYBACK_AVAILABILITY_AUDIT.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Scope**: Empirical CDX Index and Payload Content Verification Across Four Target Domains  
**Machine-Readable Twin**: `reports/v2_13_1_wayback_results.csv`  
**Status**: APPROVED EMPIRICAL AUDIT REPORT  
**Production Integrity Invariant**: `data/damascus_airport.db` SHA-256 verified identical (`c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`).

---

## 1. Executive Summary & Audit Mandate

In Version 2.13, Opportunity `REC-OPP-01` identified the Internet Archive / Wayback Machine as the "single best free source for historical flight schedules" and assigned it a "P0" immediate priority for recovering 2024–2026 schedules.

Version 2.13.1 subjects this hypothesis to rigorous empirical testing by querying the public Wayback Machine CDX Server API (`web.archive.org/cdx/search/cdx`) against the four target domains and URLs:
1. `damairport.gov.sy/api/flights.php` (Official airport FIDS endpoint)
2. `damairport.gov.sy` (Official airport portal root)
3. `syrianair.com` (National flag carrier website)
4. `chamwings.com` (Private Syrian carrier website)

---

## 2. Empirical CDX Query Findings Across Tested Targets

### 2.1 Target 1: `damairport.gov.sy/api/flights.php`
- **CDX Query**: `https://web.archive.org/cdx/search/cdx?url=damairport.gov.sy/api/flights.php&output=json`
- **Total Historical Snapshots Found**: **Exactly 1 snapshot** in the entire history of the Wayback Machine.
- **Snapshot Metadata**:
  * **Original URL**: `https://damairport.gov.sy/api/flights.php`
  * **Snapshot Timestamp**: `20260709234230` (2026-07-09T23:42:30 UTC)
  * **Archived Permalink**: `https://web.archive.org/web/20260709234230/https://damairport.gov.sy/api/flights.php`
  * **HTTP Status**: `200 OK`
  * **MIME Type**: `application/json`
  * **Cryptographic Digest**: `LWGQOMIVR7BG55CKGT4LXDRNUVKDA36L`
  * **Payload Size**: 68,891 bytes uncompressed (8,874 bytes gzipped)
- **Detailed Payload Analysis**:
  * The decompressed JSON payload was successfully retrieved and validated using `gzip.decompress()`.
  * Structure: Top-level keys `['ok', 'flights', 'settings', 'airlines']`.
  * **Flight Records Count**: Exactly **1,982 flight objects**.
  * **Flight Object Fields**: `['id', 'flightNumber', 'airline', 'direction', 'origin', 'originText', 'destination', 'destinationText', 'date', 'time', 'gate', 'aircraft', 'status', 'createdAt']`.
  * **Directional Segregation**: Explicitly segregated (`'arrival'` and `'departure'`).
  * **Geographic Scope**: Confirms Damascus International Airport (all arrivals terminate at DAM; all departures originate from DAM).
  * **Data Nature**: **Commercial Scheduled Timetable Only**. Contains scheduled date (`date`), scheduled time (`time`), gate, aircraft type, and operational status (e.g. `Scheduled`, `Landed`, `Departed`). **Does NOT contain radar/transponder touchdown timestamps.**
  * **Demonstrated Date Range**: Spans **2026-07-05 through 2026-09-09** across 67 discrete dates.
  * **Snapshots Found for 2024 or 2025**: **ZERO (0)**.
- **Evidentiary Verdict**: **Valuable single snapshot for Q3 2026 schedule benchmarking. Completely unavailable for 2024 and 2025.**

---

### 2.2 Target 2: `damairport.gov.sy` (Portal Root)
- **CDX Query**: `https://web.archive.org/cdx/search/cdx?url=damairport.gov.sy/&from=20240101&to=20261031&output=json`
- **Total Snapshots Found**: 19 snapshots, all concentrated between `2026-07-09` and `2026-08-10`.
- **Pre-2026 Analysis**: An unrestricted query for `url=damairport.gov.sy/*&to=20260630` returned **zero snapshots**. The domain was never captured by Internet Archive crawlers prior to July 2026.
- **Payload Inspection**:
  * The homepage is an HTML wrapper that renders a dynamic JavaScript/AJAX client.
  * The raw HTML snapshot does not contain embedded flight tables; flight information is fetched client-side from `/api/flights.php`.
- **Evidentiary Verdict**: **Zero flight records exist in the HTML snapshots. Zero coverage for 2024 or 2025.**

---

### 2.3 Target 3: `syrianair.com`
- **CDX Query**: `https://web.archive.org/cdx/search/cdx?url=syrianair.com/*&from=20240101&to=20261031&output=json`
- **Total Unique URLs Found (2024–2026)**: Exactly 6 unique paths.
- **Path Breakdown**:
  * `http://www.syrianair.com/`: HTTP 301 redirect.
  * `https://www.syrianair.com/`: Landing page (~1.2 KB) with basic placeholder text.
  * Asset files: `butterfly.png`, `flag.png`.
  * Outdated ASP endpoints: `sub.asp` (HTTP 404), `sub.aspTarom` (HTTP 301).
- **Flight Data Content**:
  * Detailed inspection of the 200 OK HTML snapshots (e.g. `2024-02-25`, `2024-05-16`) confirmed **zero flight schedule tables, timetables, or historical flight logs**.
- **Evidentiary Verdict**: **Completely unavailable. No historical flight information can be recovered from syrianair.com via Wayback Machine.**

---

### 2.4 Target 4: `chamwings.com`
- **CDX Query**: `https://web.archive.org/cdx/search/cdx?url=chamwings.com/*&from=20240101&to=20261031&output=json`
- **Total Snapshots Found**: 116 snapshots across 2024.
- **Payload Content Analysis**:
  * Snapshot `2024-01-31` (`https://web.archive.org/web/20240131192933id_/https://chamwings.com/`) was decompressed and parsed using BeautifulSoup.
  * The page contains promotional news articles (e.g. "Special offer for Damascus-Doha flight across Kuwait") and an interactive JavaScript flight booking widget.
  * **Keyword Frequency**: `DAM` appears 5 times in promotional text; `OSDI` appears 0 times; `arrival` appears 0 times; `departure` appears 1 time in a form label.
  * **Flight Tables**: Zero structured timetables or tabular flight schedules exist in the static HTML.
- **Evidentiary Verdict**: **Unavailable for tabular flight data. Marketing text only; cannot recover historical flight movements.**

---

## 3. Systematic Summary Matrix of Wayback Findings

| Target URL | Total Snapshots (2024-2026) | Snapshots in 2024-2025 | Contains Flight Info? | Movement Nature | Earliest Usable Date | Demonstrable Range | Actionable Verdict |
|---|---|---|---|---|---|---|---|
| `damairport.gov.sy/api/flights.php` | **1** | **0** | **Yes** (1,982 flights) | Scheduled Timetable | `2026-07-05` | 2026-07-05 to 2026-09-09 | **GO (Single 2026 Snapshot)** |
| `damairport.gov.sy/` | **19** | **0** | No (AJAX shell) | None | N/A | None | **NO-GO** |
| `syrianair.com/*` | **20** | 18 (Redirects) | No | None | N/A | None | **NO-GO** |
| `chamwings.com/*` | **116** | 116 (Promo) | No (Marketing HTML)| None | N/A | None | **NO-GO** |

---

## 4. Authoritative Conclusions & Impact on Recovery Roadmap

1. **Rebuttal of V2.13 Assumption**: The V2.13 finding that the Internet Archive is a viable source for 2024 and 2025 Damascus flight schedules is **factually disproven**. No snapshots of `damairport.gov.sy` exist prior to July 2026, and airline websites do not archive timetable tables.
2. **Actionable Scope**: The Wayback Machine can recover exactly **one dataset**: the 1,982 scheduled flights contained in the `2026-07-09` capture of `damairport.gov.sy/api/flights.php`.
3. **Implication for 2024–2025**: Free open-web archival scraping cannot solve the 2024–2025 flight-level data gap. Other avenues (commercial historical aggregators or official sovereign statistical gazettes) must be relied upon.
