# Syrian Airport Data Engine — Version 2.16
# Historical Archive Coverage Analysis: Captures vs. Scheduled Service Dates

## 1. Executive Summary & Dual-Level Dimension Architecture

In historical aviation intelligence, conflating **archive crawl frequency** with **airport flight volume** introduces severe analytical distortions.

Version 2.16 enforces a strict dual-level separation:

1. **Snapshot Capture Coverage**:
   How many independent times web crawlers captured the API endpoint in a given month or year.
2. **Scheduled Service Date Coverage**:
   The actual calendar dates and flights represented *inside* the captured timetable displays.

A single snapshot captured on July 9, 2026 contains timetable projections extending 67 days into September. Conversely, 10 captures taken in one week might observe the exact same flights 10 times.

Under no circumstances may multiple snapshots be summed together to claim inflated "monthly flight totals".

---

## 2. Monthly Historical Coverage Census

The table below documents the verified breakdown from `reports/v2_16_monthly_archive_coverage.csv`:

| Month | Snapshot Captures | Unique Digests | Scheduled Service Range | Distinct Scheduled Dates | Total FIDS Observations | Deduplicated Source UUIDs | Scheduled Arrivals | Scheduled Departures | Displayed Airlines |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2026-07** | 2 | 2 | `2026-07-05` to `2026-07-31` | 27 days | 956 | 956 | 480 | 476 | 14 |
| **2026-08** | 1 | 1 | `2026-08-01` to `2026-08-31` | 31 days | 886 | 886 | 443 | 443 | 8 |
| **2026-09** | 2 | 2 | `2026-09-01` to `2026-09-09` | 9 days | 140 | 140 | 70 | 70 | 8 |
| **TOTAL** | **5** | **5** | **2026-07-05 to 2026-09-09** | **67 days** | **1,982** | **1,982** | **993** | **989** | **14** |

*Source: Derived directly from `reports/v2_16_monthly_archive_coverage.csv`.*

---

## 3. Deduplication and Overlap Invariant

### 3.1 Observation vs. Identity
- **Snapshot Record Observations**: The sum of rows across all ingested snapshots. If snapshot A has 1,982 rows and snapshot B has 28 rows for July 20, total observations equals 2,010.
- **Deduplicated Flight Identities**: Unique source UUIDs or composite schedule keys `(flight_number, scheduled_date, scheduled_time, direction, route)`.
- When reporting airport capacity, only **deduplicated flight identities** are presented.

### 3.2 Omission vs. Inactivity
- A missing scheduled date in an archive window indicates an **archive visibility gap**, NOT an absence of airport operations.
- For example, calendar years 2024 and 2025 possess zero Wayback captures of `/api/flights.php`. This proves that Internet Archive crawlers did not index the endpoint during that period; it does not mean Damascus International Airport was closed.
