# Syrian Airport Data Engine — Version 2.16
# Archived FIDS Snapshot Validation Standards & Results

## 1. Executive Summary

This document specifies the validation engine implemented in [`src/archived_fids_snapshot_validator.py`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/src/archived_fids_snapshot_validator.py).

Every FIDS snapshot acquired from the Internet Archive undergoes rigorous, independent multi-stage validation across five analytical pillars:
1. **JSON Structure & Schema Integrity**
2. **Flight Record Identity & UUID Auditing**
3. **Flight Movement Semantics**
4. **Timezone & Temporal Representation**
5. **Quality & Anomaly Profiling**

---

## 2. Five-Stage Validation Framework

### Stage A: Structural JSON Validation
- Validates parseable JSON syntax.
- Asserts that top-level JSON is an object containing expected keys: `ok`, `flights`, `settings`, `airlines`.
- Asserts that `flights` is an array of objects.

### Stage B: Record Identity & UUID Auditing
- Validates that every flight object possesses a valid RFC 4122 UUID in the `id` field.
- Checks for missing, null, or empty UUIDs.
- Evaluates UUID uniqueness within the snapshot.
- Detects exact byte-level duplicate objects via SHA-256 object hashing.
- Detects semantic candidate duplicates (identical schedule slots with prefix variants).

### Stage C: Flight Semantics & Invariants
- Segregates records into `arrival` and `departure`.
- Preserves original raw strings for:
  - `flightNumber`
  - `airline` (displayed marketing brand)
  - `origin` / `destination`
  - `date` / `time`
  - `status`
  - `createdAt`
- **Strict Prohibition**: Never infers certified AOC operator, aircraft registration, or actual takeoff/landing timestamps.

### Stage D: Timezone Interpretation
- Timestamps in the FIDS snapshot represent Damascus local wall-clock time (`Asia/Damascus`, `UTC+3`).
- Local timestamps are never silently overwritten or converted.
- Any derived UTC value is explicitly exported as a separate field (`derived_utc_timestamp`) clearly flagged as calculated.

### Stage E: Quality Metrics & Profiling
Computes comprehensive quality metrics including:
- Total records count.
- Directional distribution (arrivals vs. departures).
- Displayed status breakdown (`scheduled`, `arrived`, etc.).
- Displayed airline brand distribution (14 entities).
- Scheduled service date span (earliest date, latest date, calendar days covered).
- Missing field tallies.

---

## 3. Validation Audit Findings: Baseline Snapshot

Execution on `wayback_damairport_fids_20260709234230.json` yielded:

- **Validation Status**: `VALID_WITH_CANDIDATE_DUPLICATES`
- **Total Records**: **1,982**
- **Scheduled Arrivals**: **993** (50.10%)
- **Scheduled Departures**: **989** (49.90%)
- **Source UUIDs**: **1,982 unique RFC 4122 UUIDs**
- **Missing UUIDs**: **0**
- **Duplicate UUIDs**: **0**
- **Exact Duplicate Objects**: **0**
- **Semantic Candidate Duplicates**: **1 pair** (2 records: `G9 376` and `376` on 2026-07-08 at 13:55 DAM $\rightarrow$ SHJ)
- **Date Coverage**: 67 continuous calendar days (`2026-07-05` to `2026-09-09`)
- **Missing Required Fields**: **0** (All records contain flightNumber, date, time, direction)
- **Physical Movement Evidence Count**: **0**

The snapshot meets all criteria for historical scheduled-service analysis.
