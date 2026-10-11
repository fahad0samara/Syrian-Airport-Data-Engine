# V2.16.1 — URL Variant Audit
## Wayback Machine Endpoint Discovery, Classification & Query Parameter Scoping

**Syrian Airport Data Engine — Version 2.16.1**  
**Audit Date:** 2026-10-11  
**Dataset Analyzed:** Official Damascus Airport Flight Information Display System (FIDS) API  
**Baseline Snapshot ID:** `snap_wayback_20260709234230`

---

## 1. Executive Summary

This audit establishes the rigorous technical classification of all URL variants identified during the Wayback Machine CDX discovery phase for Damascus International Airport's flight information API (`damairport.gov.sy/api/flights.php`).

In Version 2.16, five distinct captures were identified. This audit verifies that these captures represent fundamentally different query parameters, scopes, and schemas. Treating all captured endpoints as identical full-schedule snapshots violates comparative integrity. Filtered captures (e.g. arrivals-only, single-date, or paginated results) cannot be evaluated directly against an unfiltered snapshot without inducing severe false-positive schedule drops and synthetic discrepancy metrics.

---

## 2. Complete Inventory of Discovered URL Variants

A total of 5 captures were cataloged in [`reports/v2_16_1_url_variant_audit.csv`](../reports/v2_16_1_url_variant_audit.csv) and `archived_snapshot_registry`:

| Capture Timestamp | Discovered URL | Scheme | Host | Path | Query Parameters | Capture Type | Scope Compatibility |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **20260709234230** | `https://damairport.gov.sy/api/flights.php` | `https` | `damairport.gov.sy` | `/api/flights.php` | None | `unfiltered_endpoint` | `full_snapshot_comparison` |
| **20260715120410** | `https://damairport.gov.sy/api/flights.php?direction=arrival` | `https` | `damairport.gov.sy` | `/api/flights.php` | `direction=arrival` | `filtered_arrivals` | `scoped_comparison_only` |
| **20260720081522** | `http://damairport.gov.sy/api/flights.php` | `http` | `damairport.gov.sy` | `/api/flights.php` | None | `unfiltered_endpoint` | `full_snapshot_comparison` |
| **20260801163000** | `https://damairport.gov.sy/api/flights.php?date=2026-07-20` | `https` | `damairport.gov.sy` | `/api/flights.php` | `date=2026-07-20` | `filtered_date` | `scoped_comparison_only` |
| **20260815141045** | `https://damairport.gov.sy/api/flights.php?page=1` | `https` | `damairport.gov.sy` | `/api/flights.php` | `page=1` | `paginated_response` | `scoped_comparison_only` |

---

## 3. Structural Breakdown & Query Parameter Semantics

### 3.1. Scheme Separation: HTTPS vs. HTTP
- **Capture 20260709234230** utilized HTTPS (`https://damairport.gov.sy/api/flights.php`).
- **Capture 20260720081522** was indexed under plain HTTP (`http://damairport.gov.sy/api/flights.php`).
- **Audit Rule:** Scheme normalization must preserve the exact requested URL for cryptographic and provenance auditability. While HTTP and HTTPS endpoints may serve identical backend data depending on server-side redirect behavior, they are recorded with distinct raw URLs in the archive registry.

### 3.2. Host and Subdomain Verification
- All 5 captures target `damairport.gov.sy`. No `www.damairport.gov.sy` variants were indexed in this batch. Any future `www` captures must be classified explicitly to detect potential canonicalization discrepancies or differing CDN caching policies.

### 3.3. Direction Filtering: `?direction=arrival` (Capture 20260715120410)
- **Parameter:** `direction=arrival`
- **Payload Effect:** Restricts the server response exclusively to inbound movements. Departures are excluded by definition.
- **Integrity Rule:** Comparing this snapshot against the baseline without a directional filter will report all 989 baseline departures as "missing / cancelled". Such a comparison is logically invalid. Any comparison against this capture MUST be restricted to `direction == 'arrival'`.

### 3.4. Temporal Filtering: `?date=2026-07-20` (Capture 20260801163000)
- **Parameter:** `date=2026-07-20`
- **Payload Effect:** Restricts the server response exclusively to flights scheduled for July 20, 2026.
- **Integrity Rule:** A single-date capture cannot establish 67-day trend analysis or net schedule growth. Cross-snapshot comparison must be scoped strictly to the intersecting date (`2026-07-20`).

### 3.5. Pagination Filtering: `?page=1` (Capture 20260815141045)
- **Parameter:** `page=1`
- **Payload Effect:** Returns a single page of results (typically 20, 50, or 100 items depending on API defaults) rather than the complete scheduled flight manifest.
- **Integrity Rule:** Paginated responses lack completeness guarantees. Unless all subsequent pages are retrieved and concatenated, records missing from page 1 must NOT be marked as removed or discontinued.

---

## 4. Normalization & Comparison Rules

To prevent misleading analytics, the engine enforces the following normalization rules:

1. **Endpoint Normalization:** All URLs are parsed into scheme, host, path, and sorted query dictionary.
2. **Canonical Eligibility Determination:**
   - Unfiltered endpoints (`direction=none`, `date=none`, `page=none`) are marked `full_snapshot_comparison`.
   - Direction-filtered endpoints are marked `scoped_comparison_only` with `comparison_scope: arrival_movements_only` or `departure_movements_only`.
   - Date-filtered endpoints are marked `scoped_comparison_only` with `comparison_scope: single_date_only`.
   - Paginated endpoints are marked `scoped_comparison_only` with `comparison_scope: paginated_subset`.
3. **Incompatible Pair Rejection:**
   If a full snapshot is compared with a scoped snapshot without explicit scope alignment, the comparison engine rejects the execution with `scope_mismatch` and logs an explanatory exclusion notice.

---

## 5. Audit Conclusion

The 5 discovered Wayback captures do not represent 5 identical snapshots of the Damascus Airport schedule. Only 2 represent unfiltered endpoints (`20260709234230` and `20260720081522`), while the remaining 3 represent filtered subsets (`arrival`, `single_date`, and `paginated`). Strict URL variant parsing ensures that downstream comparison routines cannot produce synthetic discrepancies or misrepresent filtered omissions as flight cancellations.
