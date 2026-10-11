# Syrian Airport Data Engine — Version 2.16
# Wayback Machine FIDS Archive Discovery Report

## 1. Executive Summary

This report documents the empirical discovery audit conducted across the Internet Archive (Wayback Machine) CDX Server index for the official Damascus International Airport (DAM / OSDI) flight information API (`damairport.gov.sy/api/flights.php`) and its historical variants.

The discovery process evaluated all available years (2024, 2025, 2026) using the public CDX interface (`https://web.archive.org/cdx/search/cdx`) with strict read-only access and polite rate limiting.

### Key Discovery Findings
1. **Pre-2026 Coverage**: Exactly **ZERO (0)** captures exist in the Wayback Machine for calendar years 2024 and 2025 for this endpoint or any of its host variants.
2. **2026 Coverage**: Exactly **5 unique captures** exist, all concentrated between July 9, 2026 and September 9, 2026.
3. **MIME Type Concordance**: 100% (5 of 5) of the discovered captures returned `HTTP 200 OK` with `application/json`.
4. **Unique Content Digests**: All 5 captures possess distinct SHA-1 content digests, representing 5 independent points in time.
5. **Replay Rate Limiting**: The public Wayback Machine replay endpoint enforces strict IP-level rate limiting (`HTTP 429 Too Many Requests`). Per project safety rules, the system stops safely without attempting to bypass access controls.

---

## 2. Target Endpoints & Discovery Methodology

The following endpoints were queried via the public CDX interface:
- `https://damairport.gov.sy/api/flights.php`
- `http://damairport.gov.sy/api/flights.php`
- `https://www.damairport.gov.sy/api/flights.php`
- `http://www.damairport.gov.sy/api/flights.php`
- `damairport.gov.sy/api/flights*` (query-parameterized variants)

### CDX Parameters Utilized
- `output=json`
- `limit=100`
- `fl=urlkey,timestamp,original,mimetype,statuscode,digest,length`

---

## 3. Comprehensive Discovered Capture Inventory

The 5 captures discovered in the Internet Archive index are detailed below:

| # | Wayback Timestamp | Capture Date | HTTP Status | MIME Type | Content Digest | Payload Length | Archive Availability | Retrieval Status | Preserved Locally |
| :-: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `20260709234230` | 2026-07-09 | 200 | `application/json` | `LWGQOMIVR7BG55CKGT4LXDRNUVKDA36L` | 67,953 B | Available | `acquired_locally` | **YES (Baseline)** |
| 2 | `20260720034051` | 2026-07-20 | 200 | `application/json` | `5XPJUI5F52UOB5LJFQS6V2H7QK53WMZV` | 2,847 B | Available | `rate_limited_429` | In Cache |
| 3 | `20260802011114` | 2026-08-02 | 200 | `application/json` | `5UXRH7MNTOJW3WZ4KTMODHCZASJTC45Y` | 3,219 B | Available | `rate_limited_429` | In Cache |
| 4 | `20260901001238` | 2026-09-01 | 200 | `application/json` | `MZOHYTG7ISAYZ24ZNYW5EO27E4CEGI4W` | 3,196 B | Available | `rate_limited_429` | In Cache |
| 5 | `20260909200343` | 2026-09-09 | 200 | `application/json` | `25PYEJCFKSNC5ZSM2MMZFOFEQRNIAFSJ` | 2,624 B | Available | `rate_limited_429` | In Cache |

*Source: Derived directly from `reports/v2_16_wayback_captures.csv`.*

---

## 4. Temporal & Categorical Analysis

### 4.1 Annual Breakdown
- **2024**: 0 captures (Domain unindexed for FIDS API)
- **2025**: 0 captures (Domain unindexed for FIDS API)
- **2026**: 5 captures (July: 2, August: 1, September: 2)

### 4.2 Endpoint Query Parameter Variants
The baseline snapshot (`20260709234230`) represents the unparameterized API call (`flights.php`), which returned the airport's full 67-day scheduled service buffer (1,982 records).
The subsequent 4 captures represent client-side AJAX requests with pagination and date filter query parameters:
- `paged=1&page=1&dir=all&wfloor=2026-07-17&dexact=2026-07-20` (July 20, 2026 daily window).
- `paged=1&page=auto&dir=arrival&wfloor=2026-07-30&dexact=2026-08-02` (August 2, 2026 arrival window).
- `paged=1&page=auto&dir=arrival&wfloor=2026-08-29&dexact=2026-09-01` (September 1, 2026 arrival window).
- `paged=1&page=auto&dir=arrival&wfloor=2026-09-06&dexact=2026-09-09` (September 9, 2026 arrival window).

---

## 5. Compliance With Safety & Governance Mandates

1. **Zero External Outreach**: No communications, credentials, or applications were transmitted.
2. **Rate Limit Handling**: Live replay calls encountered `HTTP 429 Too Many Requests`. The system safely halted acquisition without attempting denial-of-service or circumventing rate limiters.
3. **No Synthetic Extrapolations**: The absence of 2024 and 2025 captures is recorded transparently as an empirical null, without fabricating synthetic scheduled movements.
