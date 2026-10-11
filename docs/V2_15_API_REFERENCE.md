# Syrian Airport Data Engine — Version 2.15
# Archived FIDS Analytics API Reference

## 1. Overview & Base URL

The Archived FIDS Analytics API is exposed under the dedicated namespace:

```
/api/archived-fids/
```

All responses return standard JSON with UTF-8 encoding (or CSV attachments for export routes) and include dataset provenance and the mandatory semantic warning:
> `"semantic_warning": "These records represent archived scheduled/displayed flight information, not verified physical aircraft movements."`

---

## 2. API Endpoints Catalog

### 1. `GET /api/archived-fids/summary`
Returns high-level aggregate metrics for the archived FIDS dataset, responsive to optional filters.

- **Query Parameters**:
  - `start_date` (*string*, optional): Lower date boundary (`YYYY-MM-DD`).
  - `end_date` (*string*, optional): Upper date boundary (`YYYY-MM-DD`).
  - `direction` (*string*, optional): `arrival`, `departure`, or `all`.
  - `airline` (*string*, optional): Filter by English name, Arabic name, or IATA code.
- **Sample Request**:
  `GET /api/archived-fids/summary?direction=arrival`
- **Sample Response**:
  ```json
  {
    "status": "success",
    "semantic_warning": "These records represent archived scheduled/displayed flight information, not verified physical aircraft movements.",
    "provenance": {
      "snapshot_id": "snap_wayback_20260709234230",
      "memento_timestamp": "2026-07-09T23:42:30Z",
      "date_coverage_start": "2026-07-05",
      "date_coverage_end": "2026-09-09",
      "consecutive_days": 67,
      "physical_movement_evidence_count": 0
    },
    "summary": {
      "total_archived_fids_records": 993,
      "scheduled_arrivals": 993,
      "scheduled_departures": 0,
      "calendar_days_covered": 67,
      "displayed_airline_brands_count": 14,
      "unique_scheduled_flight_numbers": 85,
      "status_distribution": { "scheduled": 992, "arrived": 1 },
      "duplicate_candidates_count": 0,
      "physical_movement_evidence_count": 0
    }
  }
  ```

---

### 2. `GET /api/archived-fids/daily`
Returns daily flight counts, directional breakdown, schedule variety, and duplicate indicators across the date range.

- **Query Parameters**: `start_date`, `end_date`, `direction`, `airline`.
- **Sample Response**:
  ```json
  {
    "status": "success",
    "total_days": 67,
    "daily_records": [
      {
        "flight_date": "2026-07-05",
        "total_scheduled_records": 64,
        "arrival_records": 33,
        "departure_records": 31,
        "unique_displayed_flight_numbers": 63,
        "unique_displayed_airline_brands": 12,
        "scheduled_status_count": 64,
        "other_display_status_count": 0,
        "duplicate_candidates_count": 0
      }
    ]
  }
  ```

---

### 3. `GET /api/archived-fids/airlines`
Returns the complete Displayed Airline Distribution, including Arabic and English brand names, IATA codes, share percentage, arrival/departure splits, and daily frequencies.

- **Query Parameters**: `start_date`, `end_date`, `direction`.
- **Sample Response**:
  ```json
  {
    "status": "success",
    "metric_label": "Displayed Airline Distribution",
    "total_displayed_records": 1982,
    "airline_brands_count": 14,
    "airlines": [
      {
        "displayed_airline_brand_ar": "طيران العربية",
        "displayed_airline_brand_en": "Air Arabia",
        "source_iata_code": "G9",
        "carrier_role_classification": "displayed_airline_brand",
        "total_displayed_records": 509,
        "percentage_of_total": "25.68%",
        "arrival_records": 256,
        "departure_records": 253,
        "distinct_flight_numbers": 12,
        "active_days_count": 67,
        "daily_frequency_active_days": 7.6,
        "is_operating_carrier_verified": false
      }
    ]
  }
  ```

---

### 4. `GET /api/archived-fids/routes`
Returns top origin airports, destination airports, and route pairs.

- **Query Parameters**: `start_date`, `end_date`, `direction`, `airline`, `limit` (default 20).
- **Sample Response**:
  ```json
  {
    "status": "success",
    "top_destinations": [
      { "airport_code": "DXB", "movement_type": "departure", "scheduled_flight_count": 193 }
    ],
    "top_routes": [
      {
        "route_pair": "DAM-SHJ",
        "origin_iata": "DAM",
        "destination_iata": "SHJ",
        "movement_type": "departure",
        "scheduled_records_count": 253,
        "unique_displayed_flight_numbers": 6,
        "distinct_airlines_count": 2,
        "airlines_list": "Air Arabia,Fly Cham"
      }
    ]
  }
  ```

---

### 5. `GET /api/archived-fids/hourly`
Returns the 24-hour schedule distribution grouped by original local Damascus wall-clock hour (`Asia/Damascus` / `UTC+3`).

- **Query Parameters**: `start_date`, `end_date`, `direction`, `airline`.
- **Sample Response**:
  ```json
  {
    "status": "success",
    "timezone": "Asia/Damascus (UTC+3)",
    "hourly_distribution": [
      { "hour_local": "00", "hour_label": "00:00–00:59", "arrivals": 44, "departures": 16, "total": 60 },
      { "hour_local": "01", "hour_label": "01:00–01:59", "arrivals": 64, "departures": 5, "total": 69 }
    ]
  }
  ```

---

### 6. `GET /api/archived-fids/weekly`
Returns period averages, weekday distribution (Monday to Sunday), and lists of busiest and quietest calendar days.

- **Query Parameters**: `start_date`, `end_date`, `direction`, `airline`.
- **Sample Response**:
  ```json
  {
    "status": "success",
    "period_statistics": {
      "total_calendar_days": 67,
      "total_scheduled_records": 1982,
      "average_records_per_calendar_day": 29.58,
      "average_arrivals_per_calendar_day": 14.82,
      "average_departures_per_calendar_day": 14.76
    },
    "weekday_distribution": [
      { "weekday_index": 0, "weekday_name": "Monday", "average_flights_per_weekday": 32.2 }
    ]
  }
  ```

---

### 7. `GET /api/archived-fids/duplicate-candidates`
Exposes the registered duplicate candidate pair (`G9 376` & `376`).

- **Sample Response**:
  ```json
  {
    "status": "success",
    "duplicate_candidate_pairs_count": 1,
    "candidates": [
      {
        "candidate_id": "DUP_CANDIDATE_001",
        "group_type": "possible_prefix_variant_duplicate",
        "source_uuid_1": "e5ada70d-5245-46d4-b043-bf469c1d104f",
        "flight_number_1": "G9 376",
        "source_uuid_2": "2d2a0935-da5e-42c4-ad15-e10b4e2291ee",
        "flight_number_2": "376",
        "scheduled_date": "2026-07-08",
        "scheduled_time": "13:55",
        "duplicate_classification": "possible_prefix_variant_duplicate",
        "review_status": "requires_manual_review"
      }
    ],
    "policy_note": "Both source records are preserved unaltered in the database. Neither record is deleted, merged, or suppressed."
  }
  ```

---

### 8. `GET /api/archived-fids/coverage`
Returns dataset provenance, coverage boundaries, and evidence zero-flag.

---

### 9. `GET /api/archived-fids/export/csv`
Streams CSV data for download.
- **Parameters**: `dataset` (`daily`, `airlines`, `routes`, `hourly`, `weekly`, `duplicates`, `records`), plus optional filters.
- **Response**: `Content-Type: text/csv`, attachment filename `archived_fids_{dataset}.csv`.

---

### 10. `GET /api/archived-fids/export/json`
Returns analytical dataset in JSON format.
- **Parameters**: `dataset` (`summary`, `daily`, `airlines`, `routes`, `hourly`, `weekly`, `duplicates`, `records`), plus optional filters.

---

## 3. Error Codes & Validation

- `400 Bad Request`: Returned when date formats are invalid, `start_date > end_date`, or an invalid `direction` is provided.
- `404 Not Found`: Returned when requesting an unrecognized export dataset.
