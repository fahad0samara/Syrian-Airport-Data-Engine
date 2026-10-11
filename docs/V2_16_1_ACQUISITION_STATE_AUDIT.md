# V2.16.1 — Acquisition State Audit
## Physical File Verification, Cryptographic Hashes & Replay Acquisition Audit

**Syrian Airport Data Engine — Version 2.16.1**  
**Audit Date:** 2026-10-11  
**Target Resource:** Official Damascus International Airport FIDS API Captures  
**Storage Path:** `data/raw/snapshots/`

---

## 1. Executive Summary

This audit assesses the physical acquisition state of historical FIDS captures in the Syrian Airport Data Engine. 

Key finding: **Exactly one snapshot is physically acquired and cryptographically verified on disk** (`20260709234230`). The remaining four captures cataloged during CDX index discovery (`20260715120410`, `20260720081522`, `20260801163000`, `20260815141045`) were encountered with HTTP 429 rate limiting during replay retrieval. In accordance with strict project rules, **zero synthetic payloads were created, zero placeholder files were written to disk, and no unauthorized external attempts were made to bypass rate limits**.

---

## 2. Inventory of Discovered vs. Acquired Captures

| Snapshot ID | Wayback Timestamp | CDX Status | Local Physical Files | Retrieval State | Record Count | Validation Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `snap_wayback_20260709234230` | `20260709234230` | 200 | `.raw` and `.json` present | `already_acquired` | 1,982 | `PASSED` |
| `snap_wayback_20260715120410` | `20260715120410` | 200 | None | `rate_limited_429` | 0 | `PENDING_ACQUISITION` |
| `snap_wayback_20260720081522` | `20260720081522` | 200 | None | `rate_limited_429` | 0 | `PENDING_ACQUISITION` |
| `snap_wayback_20260801163000` | `20260801163000` | 200 | None | `rate_limited_429` | 0 | `PENDING_ACQUISITION` |
| `snap_wayback_20260815141045` | `20260815141045` | 200 | None | `rate_limited_429` | 0 | `PENDING_ACQUISITION` |

---

## 3. Cryptographic Verification of Acquired Snapshot Files

The baseline snapshot acquired on 2026-07-09 was re-verified against its established cryptographic signatures:

### 3.1. Raw Archive Response File
- **Path:** `data/raw/snapshots/wayback_damairport_fids_20260709234230.raw`
- **File Size:** 48,735 bytes
- **Expected SHA-256:** `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf`
- **Actual Verified SHA-256:** `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf`
- **Integrity Status:** `MATCH_EXACT`

### 3.2. Normalized Decompressed JSON File
- **Path:** `data/raw/snapshots/wayback_damairport_fids_20260709234230.json`
- **File Size:** 399,564 bytes
- **Expected SHA-256:** `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491`
- **Actual Verified SHA-256:** `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491`
- **Integrity Status:** `MATCH_EXACT`

---

## 4. Verification of Non-Acquired Captures

The audit verified that no empty or mock files were placed in `data/raw/snapshots/` for the 4 rate-limited captures:

1. `data/raw/snapshots/wayback_damairport_fids_20260715120410.raw`: `DOES_NOT_EXIST` (Verified)
2. `data/raw/snapshots/wayback_damairport_fids_20260720081522.raw`: `DOES_NOT_EXIST` (Verified)
3. `data/raw/snapshots/wayback_damairport_fids_20260801163000.raw`: `DOES_NOT_EXIST` (Verified)
4. `data/raw/snapshots/wayback_damairport_fids_20260815141045.raw`: `DOES_NOT_EXIST` (Verified)

No synthetic rows were inserted into `archived_snapshot_records` for these 4 captures. Row count for unacquired captures is strictly 0.

---

## 5. Non-Destructive Invariant Protection

- **No Overwrite:** Existing snapshot files are protected by existence checks. If a file exists and matches its hash, re-download is skipped (`retrieval_status: "already_acquired"`).
- **No Synthetic Records:** Tests and routines never mock payload content into production or staging tables.
- **Audit Logging:** Replay failures are recorded truthfully as `rate_limited_429`, ensuring complete transparency to downstream analysts and UI users.

---

## 6. Audit Conclusion

Physical archive acquisition is currently limited to 1 baseline snapshot (`20260709234230`) totaling 1,982 records. Four discovered captures remain unacquired due to HTTP 429 rate limiting. System state truthfully reflects this reality with zero data contamination.
