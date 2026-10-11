# Syrian Airport Data Engine — Version 2.16
# Historical FIDS Archive Provenance & Storage Architecture

## 1. Provenance Hierarchy & Chain of Custody

The historical flight information display system (FIDS) archive originates from public snapshots captured by the Internet Archive (Wayback Machine) from the official government web server of Damascus International Airport:
- **Authority**: General Authority of Civil Aviation (GACA) / Ministry of Transport, Syrian Arab Republic.
- **Official Host Domain**: `damairport.gov.sy`
- **Official API Endpoint**: `/api/flights.php`
- **Replay Host**: `https://web.archive.org/web/`
- **Baseline Snapshot Memento**: `2026-07-09T23:42:30Z` (`20260709234230`)

---

## 2. Cryptographic Storage & File Invariants

All acquired snapshots are stored deterministically under `data/raw/snapshots/` using dual-file preservation:
1. **Raw Wire Bytes (`.raw`)**: Exactly preserves the byte-for-byte stream transmitted by the server (including gzip compression headers where present).
2. **Decompressed JSON (`.json`)**: Formatted, human-readable JSON payload used for validation, normalized staging, and analytics.

### Baseline Cryptographic Hash Manifest

| File Identifier | Path | Size | SHA-256 Hash |
| :--- | :--- | :---: | :--- |
| **Raw Snapshot** | `data/raw/snapshots/wayback_damairport_fids_20260709234230.raw` | 68,891 B | `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf` |
| **JSON Snapshot** | `data/raw/snapshots/wayback_damairport_fids_20260709234230.json` | 644,922 B | `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491` |

Both files are marked immutable and cryptographically protected against tampering, deletion, or synthetic modification.

---

## 3. Database Isolation Architecture

To maintain strict data integrity, three completely independent database domains exist in the Syrian Airport Data Engine:

```
[ Production Layer ]
data/damascus_airport.db (SHA-256 protected, 1,830 verified physical/operational events)
        │
        ▼ (Strict Isolation Boundary — No cross-writes)
[ Baseline FIDS Analytics Layer ]
data/archived_fids_staging.db (Baseline 1,982 normalized records)
data/archived_fids_analytics.db (Baseline analytics views & API cache)
        │
        ▼ (Strict Isolation Boundary — No cross-writes)
[ Multi-Snapshot Historical Archive Layer ]
data/archived_fids_history_staging.db (Multi-snapshot registry, cross-snapshot comparisons)
```

### Table Structure in `data/archived_fids_history_staging.db`:
- **`archived_snapshot_registry`**: Registers every discovered and acquired snapshot, capture timestamp, HTTP status, and validation status.
- **`archived_snapshot_records`**: Preserves normalized records for all snapshots with foreign key cascade to registry.
- **`snapshot_comparison_results`**: Records pairwise comparison results across snapshots.
- **`snapshot_validation_issues`**: Logs any schema, syntax, or UUID anomalies discovered during validation.

---

## 4. Fundamental Semantic Distinction

All records within this archive are classified strictly as **`scheduled_service`**:
- **Physical Movement Evidence Count**: Strictly **`0`**.
- **Radar / Transponder Telemetry**: None.
- **AOC Carrier Certification**: None (Displayed entities represent commercial marketing brands).
- Under no circumstances may any historical FIDS snapshot record be promoted to `physical_movement` without independent sensor, ADS-B, or tower verification.
