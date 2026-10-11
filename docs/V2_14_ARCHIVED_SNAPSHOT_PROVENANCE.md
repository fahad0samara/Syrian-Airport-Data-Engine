# Syrian Airport Data Engine — Version 2.14
# Archived Snapshot Provenance & Ingestion Verification

**Document Identifier**: `docs/V2_14_ARCHIVED_SNAPSHOT_PROVENANCE.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Target Endpoint**: `https://damairport.gov.sy/api/flights.php`  
**Archive Provider**: Internet Archive / Wayback Machine (`web.archive.org`)  
**Staging Database**: `data/archived_fids_staging.db`  
**Status**: APPROVED PROVENANCE SPECIFICATION  
**Production Integrity Invariant**: `data/damascus_airport.db` SHA-256 verified identical (`c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b`).

---

## 1. Executive Summary & Archival Retrieval Verification

Version 2.14 executes the physical retrieval, cryptographic verification, and audit staging of the single verified historical snapshot of Damascus International Airport's official Flight Information Display System (FIDS) API endpoint preserved in the Internet Archive.

The raw response bytes were fetched directly using the un-rewritten `id_` replay URL, permanently archived in `data/raw/snapshots/`, and ingested into a dedicated staging database (`data/archived_fids_staging.db`) completely isolated from the production flight database.

---

## 2. Cryptographic & Protocol Provenance Register

| Provenance Attribute | Verified System Value | Verification Method |
|---|---|---|
| **Archive Replay URL (`id_`)** | `https://web.archive.org/web/20260709234230id_/https://damairport.gov.sy/api/flights.php` | Direct HTTP GET query |
| **Original Aerodrome URL** | `https://damairport.gov.sy/api/flights.php` | Wayback Memento Link header |
| **Capture Timestamp (UTC)**| `2026-07-09T23:42:30Z` | CDX & Memento-Datetime header |
| **HTTP Response Status** | `200 OK` | Protocol response code |
| **Content-Type** | `application/json; charset=utf-8` | Server header |
| **Content-Encoding** | `gzip` | Server header & magic byte `1f 8b` |
| **WARC Source File** | `spn2-20260710001939/spn2-20260709212925-wwwb-spn07.us.archive.org-8000.warc.gz` | `x-archive-src` header |
| **Raw Downloaded Size** | `68,891` bytes | Local disk filesystem verification |
| **Raw Byte SHA-256** | `5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf` | Cryptographic SHA-256 digest |
| **Decompressed Byte Size** | `644,922` bytes | `gzip.decompress()` output |
| **Decompressed SHA-256** | `ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491` | Cryptographic SHA-256 digest |
| **Local Raw File Path** | `data/raw/snapshots/wayback_damairport_fids_20260709234230.raw` | Read-only preserved artifact |
| **Local JSON File Path** | `data/raw/snapshots/wayback_damairport_fids_20260709234230.json` | UTF-8 decoded JSON artifact |
| **JSON Parse Status** | Valid UTF-8 JSON object (Top-level dict) | `json.loads()` validation |
| **Total Flight Objects** | Exactly `1,982` objects | Array length of `flights` key |
| **Airlines Metadata Objects**| Exactly `14` objects | Array length of `airlines` key |

---

## 3. High-Level JSON Payload Structure

The decompressed JSON payload conforms to the following schema:

```json
{
  "ok": true,
  "flights": [
    {
      "id": "6cd07e1b-30e2-401e-84ec-9bb16e67fb42",
      "flightNumber": "RB 444",
      "airline": "السورية للطيران",
      "direction": "arrival",
      "origin": "DXB",
      "originText": "",
      "destination": "DAM",
      "destinationText": "",
      "date": "2026-07-06",
      "time": "05:00",
      "gate": "",
      "aircraft": "",
      "status": "scheduled",
      "createdAt": "2026-07-06T00:27:33Z"
    }
  ],
  "settings": {
    "pageSize": 5,
    "hideOlderThanDays": 3,
    "flightIconArrival": "/uploads/damascus-flight-arrival.webp?v=1782980905",
    "flightIconDeparture": "/uploads/damascus-flight-departure.webp?v=1782980911"
  },
  "airlines": [
    {
      "publicId": "75dd2e9272f4f541",
      "filter": "Syrian Airlines",
      "nameAr": "السورية للطيران",
      "nameEn": "Syrian Airlines"
    }
  ]
}
```

### Key Elements of the Payload:
1. **`ok`**: Boolean flag indicating successful database query on the live airport server at capture time.
2. **`flights`**: Array of 1,982 flight objects representing scheduled commercial movements.
3. **`settings`**: Configuration dictionary specifying that the public frontend display hides records older than 3 days (`hideOlderThanDays: 3`) and paginates by 5. This explains why only ~3 past days of flights (`2026-07-05` to `2026-07-08`) were preserved alongside forward scheduled flights through `2026-09-09`.
4. **`airlines`**: Array of 14 carrier metadata records providing official Arabic (`nameAr`), English (`nameEn`), and UI filter strings.

---

## 4. Ingestion Traceability Architecture

To ensure strict audibility, every record in the staging database (`data/archived_fids_staging.db`) is connected via foreign keys through a two-tiered provenance chain:

```
[ archived_snapshots ] (snap_wayback_20260709234230)
          |
          |-- 1:N
          v
[ archived_fids_raw_records ] (raw_00001_6cd07e1b, raw_json, record_hash)
          |
          |-- 1:1
          v
[ archived_fids_normalized ] (norm_00001_6cd07e1b, normalized fields, composite_key)
          |
          |-- 1:N
          v
[ archived_fids_validation_issues ] (issue tracking, field_name, severity)
```

- **`archived_snapshots`**: Stores immutable HTTP and cryptographic metadata of the download event.
- **`archived_fids_raw_records`**: Preserves the verbatim JSON string and SHA-256 record hash for every individual flight object.
- **`archived_fids_normalized`**: Contains normalized airport codes, standardized English and Arabic airline names, flight numbers without whitespace, and ISO 8601 UTC/local scheduled timestamps.
- **`archived_fids_validation_issues`**: Tracks field completeness, missing city text, and semantic warnings.
