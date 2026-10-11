"""
Syrian Airport Data Engine — Version 2.13.1
Historical Recovery Claims Validation & Feasibility Corrections Report Generator

Generates:
1. reports/v2_13_1_coverage_gaps.csv
   - Strictly separates Daily Coverage, Flight-Level Records, and Aggregate Statistics.
   - Corrects 2025 H1/annual remainder semantics, April 2026 unresolved boundary,
     September 2026 full-month scope, and SEM composite daily counts.
2. reports/v2_13_1_wayback_results.csv
   - Itemized audit of Wayback Machine CDX results for target URLs.
3. reports/v2_13_1_provider_comparison.csv
   - 10-point evaluation of commercial and public tracking providers based on demonstrated facts.
4. reports/v2_13_1_recovery_opportunities.csv
   - Reclassified opportunities with evidence-based decisions (GO, CONDITIONAL GO, NO-GO).
"""

import os
import csv
import json
import sqlite3
import hashlib
from typing import List, Dict, Any

PROD_DB_PATH = "data/damascus_airport.db"
STAGING_DB_PATH = "data/macro_benchmarks_staging.db"
EXPECTED_PROD_HASH = "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"

def get_file_sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

# =============================================================================
# 1. Separated Coverage Gaps Data (Dimension-Segregated)
# =============================================================================
# Note: Dimensions A (Daily Coverage), B (Flight-Level Records), and C (Aggregate Statistics)
# are clearly isolated into distinct, well-labeled columns.
COVERAGE_GAPS_V2_13_1: List[Dict[str, Any]] = [
    {
        "period_id": "GAP-2024-P1",
        "period_name": "2024 Pre-Transition Gateway Monitoring",
        "period_start": "2024-01-01",
        "period_end": "2024-10-15",
        "period_boundary_status": "explicit_daily_range",
        # Dimension A: Daily Coverage (DAM Specific)
        "calendar_days_total": 289,
        "dam_days_verified_physical": 0,
        "dam_days_schedule_only": 0,
        "dam_days_unverified_obs": 0,
        "dam_days_no_known_evidence": 0,
        "days_composite_only": 289,
        # Dimension B: Flight-Level Records in DB (DAM)
        "dam_flight_records_physical": 0,
        "dam_flight_records_scheduled": 0,
        "dam_flight_records_codeshare": 0,
        "dam_flight_records_unverified": 0,
        "other_airports_flight_records": 0,
        # Dimension C: Aggregate Statistics (Staged Benchmarks)
        "macro_reported_flights": "",
        "macro_total_passengers": "",
        "macro_arriving_passengers": "",
        "macro_departing_passengers": "",
        "macro_airline_count": "",
        "macro_airspace_overflights": "",
        "macro_geographic_scope": "DAM_ALP_LTK",
        "macro_reporting_period": "2024-01-01 to 2024-10-15",
        "evidence_classification": "aggregate_composite_only",
        "corrective_audit_notes": "578 rows in historical_daily_movements_2024 represent 289 calendar dates x 2 movement directions (arr/dep) for composite DAM_ALP_LTK, NOT 578 individual flights. Zero DAM-specific flight events exist."
    },
    {
        "period_id": "GAP-2024-P2",
        "period_name": "2024 Late Autumn Pre-Transition Vacuum",
        "period_start": "2024-10-16",
        "period_end": "2024-12-07",
        "period_boundary_status": "explicit_daily_range",
        "calendar_days_total": 53,
        "dam_days_verified_physical": 0,
        "dam_days_schedule_only": 0,
        "dam_days_unverified_obs": 0,
        "dam_days_no_known_evidence": 53,
        "days_composite_only": 0,
        "dam_flight_records_physical": 0,
        "dam_flight_records_scheduled": 0,
        "dam_flight_records_codeshare": 0,
        "dam_flight_records_unverified": 0,
        "other_airports_flight_records": 0,
        "macro_reported_flights": "",
        "macro_total_passengers": "",
        "macro_arriving_passengers": "",
        "macro_departing_passengers": "",
        "macro_airline_count": "",
        "macro_airspace_overflights": "",
        "macro_geographic_scope": "DAM",
        "macro_reporting_period": "2024-10-16 to 2024-12-07",
        "evidence_classification": "complete_gap",
        "corrective_audit_notes": "World Bank SEM daily monitoring ceased on 2024-10-15. Complete data vacuum across all categories."
    },
    {
        "period_id": "GAP-2024-P3",
        "period_name": "December 2024 Emergency Airspace Suspension",
        "period_start": "2024-12-08",
        "period_end": "2024-12-17",
        "period_boundary_status": "explicit_daily_range",
        "calendar_days_total": 10,
        "dam_days_verified_physical": 0,
        "dam_days_schedule_only": 0,
        "dam_days_unverified_obs": 0,
        "dam_days_no_known_evidence": 10,
        "days_composite_only": 0,
        "dam_flight_records_physical": 0,
        "dam_flight_records_scheduled": 0,
        "dam_flight_records_codeshare": 0,
        "dam_flight_records_unverified": 0,
        "other_airports_flight_records": 0,
        "macro_reported_flights": "",
        "macro_total_passengers": "",
        "macro_arriving_passengers": "",
        "macro_departing_passengers": "",
        "macro_airline_count": "",
        "macro_airspace_overflights": "",
        "macro_geographic_scope": "DAM",
        "macro_reporting_period": "2024-12-08 to 2024-12-17",
        "evidence_classification": "complete_gap",
        "corrective_audit_notes": "Emergency operational closure of Damascus airport. Commercial schedules zero; potential ad-hoc diplomatic/evacuation flights unverified."
    },
    {
        "period_id": "GAP-2024-P4",
        "period_name": "Domestic Flight Resumption & Pre-International Resumption",
        "period_start": "2024-12-18",
        "period_end": "2025-01-06",
        "period_boundary_status": "explicit_daily_range",
        "calendar_days_total": 20,
        "dam_days_verified_physical": 0,
        "dam_days_schedule_only": 0,
        "dam_days_unverified_obs": 0,
        "dam_days_no_known_evidence": 20,
        "days_composite_only": 0,
        "dam_flight_records_physical": 0,
        "dam_flight_records_scheduled": 0,
        "dam_flight_records_codeshare": 0,
        "dam_flight_records_unverified": 0,
        "other_airports_flight_records": 0,
        "macro_reported_flights": "",
        "macro_total_passengers": "",
        "macro_arriving_passengers": "",
        "macro_departing_passengers": "",
        "macro_airline_count": "",
        "macro_airspace_overflights": "",
        "macro_geographic_scope": "DAM",
        "macro_reporting_period": "2024-12-18 to 2025-01-06",
        "evidence_classification": "complete_gap",
        "corrective_audit_notes": "Domestic flights resumed Dec 18; international flights remained suspended until Jan 7. Zero daily flight records in repository."
    },
    {
        "period_id": "GAP-2025-H1",
        "period_name": "2025 SCAA 6-Month Post-Resumption Milestone",
        "period_start": "2025-01-07",
        "period_end": "2025-07-07",
        "period_boundary_status": "explicit_reported_dates",
        "calendar_days_total": 182,
        "dam_days_verified_physical": 0,
        "dam_days_schedule_only": 0,
        "dam_days_unverified_obs": 0,
        "dam_days_no_known_evidence": 182,
        "days_composite_only": 0,
        "dam_flight_records_physical": 0,
        "dam_flight_records_scheduled": 0,
        "dam_flight_records_codeshare": 0,
        "dam_flight_records_unverified": 0,
        "other_airports_flight_records": 0,
        "macro_reported_flights": "1870",
        "macro_total_passengers": "353282",
        "macro_arriving_passengers": "",
        "macro_departing_passengers": "",
        "macro_airline_count": "",
        "macro_airspace_overflights": "",
        "macro_geographic_scope": "DAM",
        "macro_reporting_period": "2025-01-07 to 2025-07-07",
        "evidence_classification": "aggregate_macro_only",
        "corrective_audit_notes": "SCAA official press conference reported 1,870 flights for the exact 6-month period 2025-01-07 to 2025-07-07. Staged at Grade C. Zero daily flight records."
    },
    {
        "period_id": "GAP-2025-ANNUAL",
        "period_name": "Full Year 2025 Annual Operational Total",
        "period_start": "2025-01-01",
        "period_end": "2025-12-31",
        "period_boundary_status": "full_calendar_year",
        "calendar_days_total": 365,
        "dam_days_verified_physical": 0,
        "dam_days_schedule_only": 0,
        "dam_days_unverified_obs": 0,
        "dam_days_no_known_evidence": 365,
        "days_composite_only": 0,
        "dam_flight_records_physical": 0,
        "dam_flight_records_scheduled": 0,
        "dam_flight_records_codeshare": 0,
        "dam_flight_records_unverified": 0,
        "other_airports_flight_records": 0,
        "macro_reported_flights": "12476",
        "macro_total_passengers": "1434998",
        "macro_arriving_passengers": "715392",
        "macro_departing_passengers": "719606",
        "macro_airline_count": "13",
        "macro_airspace_overflights": "",
        "macro_geographic_scope": "DAM",
        "macro_reporting_period": "2025-01-01 to 2025-12-31",
        "evidence_classification": "aggregate_macro_only",
        "corrective_audit_notes": "CORRECTION: 12,476 flights covers full year 2025. Must NOT be assigned to 2025-07-08 through 2025-12-31. The arithmetic remainder (10,606 flights) is NOT an independently reported H2 statistic."
    },
    {
        "period_id": "GAP-2026-Q1",
        "period_name": "2026 Airport Infrastructure Rehabilitation Closure",
        "period_start": "2026-01-01",
        "period_end": "2026-04-07",
        "period_boundary_status": "explicit_daily_range",
        "calendar_days_total": 97,
        "dam_days_verified_physical": 0,
        "dam_days_schedule_only": 0,
        "dam_days_unverified_obs": 0,
        "dam_days_no_known_evidence": 97,
        "days_composite_only": 0,
        "dam_flight_records_physical": 0,
        "dam_flight_records_scheduled": 0,
        "dam_flight_records_codeshare": 0,
        "dam_flight_records_unverified": 0,
        "other_airports_flight_records": 0,
        "macro_reported_flights": "",
        "macro_total_passengers": "",
        "macro_arriving_passengers": "",
        "macro_departing_passengers": "",
        "macro_airline_count": "",
        "macro_airspace_overflights": "",
        "macro_geographic_scope": "DAM",
        "macro_reporting_period": "2026-01-01 to 2026-04-07",
        "evidence_classification": "complete_gap",
        "corrective_audit_notes": "Damascus airport closed for runway and terminal rehabilitation. Scheduled operations zero."
    },
    {
        "period_id": "GAP-2026-M04",
        "period_name": "April 2026 Commercial Reopening",
        "period_start": "2026-04-08",
        "period_end": "2026-04-30",
        "period_boundary_status": "unresolved_source_wording",
        "calendar_days_total": 23,
        "dam_days_verified_physical": 0,
        "dam_days_schedule_only": 0,
        "dam_days_unverified_obs": 0,
        "dam_days_no_known_evidence": 23,
        "days_composite_only": 0,
        "dam_flight_records_physical": 0,
        "dam_flight_records_scheduled": 0,
        "dam_flight_records_codeshare": 0,
        "dam_flight_records_unverified": 0,
        "other_airports_flight_records": 0,
        "macro_reported_flights": "492",
        "macro_total_passengers": "34347",
        "macro_arriving_passengers": "",
        "macro_departing_passengers": "",
        "macro_airline_count": "11",
        "macro_airspace_overflights": "2523",
        "macro_geographic_scope": "DAM (Overflights: OSTT_FIR)",
        "macro_reporting_period": "April 2026 (Unresolved exact window)",
        "evidence_classification": "aggregate_macro_only",
        "corrective_audit_notes": "CORRECTION: Source excerpt states 'في نيسان 2026' without explicit day numbers. Reporting boundary is formally UNRESOLVED. Overflights (2,523) strictly describe OSTT_FIR."
    },
    {
        "period_id": "GAP-2026-M05",
        "period_name": "May 2026 Operational Ramp-Up",
        "period_start": "2026-05-01",
        "period_end": "2026-05-31",
        "period_boundary_status": "full_calendar_month",
        "calendar_days_total": 31,
        "dam_days_verified_physical": 0,
        "dam_days_schedule_only": 0,
        "dam_days_unverified_obs": 0,
        "dam_days_no_known_evidence": 31,
        "days_composite_only": 0,
        "dam_flight_records_physical": 0,
        "dam_flight_records_scheduled": 0,
        "dam_flight_records_codeshare": 0,
        "dam_flight_records_unverified": 0,
        "other_airports_flight_records": 0,
        "macro_reported_flights": "1532",
        "macro_total_passengers": "148305",
        "macro_arriving_passengers": "",
        "macro_departing_passengers": "",
        "macro_airline_count": "",
        "macro_airspace_overflights": "",
        "macro_geographic_scope": "DAM",
        "macro_reporting_period": "2026-05-01 to 2026-05-31",
        "evidence_classification": "aggregate_macro_only",
        "corrective_audit_notes": "Monthly bulletin reports 1,532 flights and 148,305 passengers. Staged at Grade C. Zero flight-level records."
    },
    {
        "period_id": "GAP-2026-M06",
        "period_name": "June 2026 Reporting Gap",
        "period_start": "2026-06-01",
        "period_end": "2026-06-30",
        "period_boundary_status": "full_calendar_month",
        "calendar_days_total": 30,
        "dam_days_verified_physical": 0,
        "dam_days_schedule_only": 0,
        "dam_days_unverified_obs": 0,
        "dam_days_no_known_evidence": 30,
        "days_composite_only": 0,
        "dam_flight_records_physical": 0,
        "dam_flight_records_scheduled": 0,
        "dam_flight_records_codeshare": 0,
        "dam_flight_records_unverified": 0,
        "other_airports_flight_records": 0,
        "macro_reported_flights": "",
        "macro_total_passengers": "",
        "macro_arriving_passengers": "",
        "macro_departing_passengers": "",
        "macro_airline_count": "",
        "macro_airspace_overflights": "",
        "macro_geographic_scope": "DAM",
        "macro_reporting_period": "2026-06-01 to 2026-06-30",
        "evidence_classification": "complete_gap",
        "corrective_audit_notes": "No monthly bulletin staged. No flight records. Complete reporting gap."
    },
    {
        "period_id": "GAP-2026-M07",
        "period_name": "July 2026 High Summer Peak",
        "period_start": "2026-07-01",
        "period_end": "2026-07-31",
        "period_boundary_status": "full_calendar_month",
        "calendar_days_total": 31,
        "dam_days_verified_physical": 0,
        "dam_days_schedule_only": 0,
        "dam_days_unverified_obs": 0,
        "dam_days_no_known_evidence": 31,
        "days_composite_only": 0,
        "dam_flight_records_physical": 0,
        "dam_flight_records_scheduled": 0,
        "dam_flight_records_codeshare": 0,
        "dam_flight_records_unverified": 0,
        "other_airports_flight_records": 0,
        "macro_reported_flights": "2088",
        "macro_total_passengers": "243260",
        "macro_arriving_passengers": "",
        "macro_departing_passengers": "",
        "macro_airline_count": "",
        "macro_airspace_overflights": "",
        "macro_geographic_scope": "DAM",
        "macro_reporting_period": "2026-07-01 to 2026-07-31",
        "evidence_classification": "aggregate_macro_only",
        "corrective_audit_notes": "Monthly bulletin reports 2,088 flights and 243,260 passengers. Staged at Grade C. Zero flight-level records."
    },
    {
        "period_id": "GAP-2026-M08",
        "period_name": "August 2026 Reporting Gap",
        "period_start": "2026-08-01",
        "period_end": "2026-08-31",
        "period_boundary_status": "full_calendar_month",
        "calendar_days_total": 31,
        "dam_days_verified_physical": 0,
        "dam_days_schedule_only": 0,
        "dam_days_unverified_obs": 0,
        "dam_days_no_known_evidence": 31,
        "days_composite_only": 0,
        "dam_flight_records_physical": 0,
        "dam_flight_records_scheduled": 0,
        "dam_flight_records_codeshare": 0,
        "dam_flight_records_unverified": 0,
        "other_airports_flight_records": 0,
        "macro_reported_flights": "",
        "macro_total_passengers": "",
        "macro_arriving_passengers": "",
        "macro_departing_passengers": "",
        "macro_airline_count": "",
        "macro_airspace_overflights": "",
        "macro_geographic_scope": "DAM",
        "macro_reporting_period": "2026-08-01 to 2026-08-31",
        "evidence_classification": "complete_gap",
        "corrective_audit_notes": "No monthly bulletin staged. No flight records. Complete reporting gap."
    },
    {
        "period_id": "GAP-2026-M09",
        "period_name": "September 2026 Full Calendar Month",
        "period_start": "2026-09-01",
        "period_end": "2026-09-30",
        "period_boundary_status": "full_calendar_month",
        "calendar_days_total": 30,
        "dam_days_verified_physical": 0,
        "dam_days_schedule_only": 1,  # 2026-09-30 is scheduled in DB
        "dam_days_unverified_obs": 0,
        "dam_days_no_known_evidence": 29,
        "days_composite_only": 0,
        "dam_flight_records_physical": 0,
        "dam_flight_records_scheduled": 63,  # Sep 30 scheduled flights
        "dam_flight_records_codeshare": 0,
        "dam_flight_records_unverified": 0,
        "other_airports_flight_records": 0,
        "macro_reported_flights": "2022",
        "macro_total_passengers": "229693",
        "macro_arriving_passengers": "",
        "macro_departing_passengers": "",
        "macro_airline_count": "",
        "macro_airspace_overflights": "19951",
        "macro_geographic_scope": "DAM (Overflights: OSTT_FIR)",
        "macro_reporting_period": "2026-09-01 to 2026-09-30",
        "evidence_classification": "aggregate_macro_only",
        "corrective_audit_notes": "CORRECTION: Monthly statistics describe the FULL calendar month (Sep 1-30), NOT Sep 1-29. Overflights (19,951) describe OSTT_FIR. Flight records begin on Sep 30."
    },
    {
        "period_id": "GAP-2026-SNAPSHOT",
        "period_name": "Active Ingestion & Snapshot Window",
        "period_start": "2026-09-30",
        "period_end": "2026-10-31",
        "period_boundary_status": "active_database_window",
        "calendar_days_total": 32,
        "dam_days_verified_physical": 2,  # 2026-10-09 and 2026-10-10
        "dam_days_schedule_only": 9,      # 2026-09-30 to 2026-10-08
        "dam_days_unverified_obs": 2,     # co-occurring on Oct 9 & 10
        "dam_days_no_known_evidence": 0,
        "days_composite_only": 0,
        "dam_flight_records_physical": 98,
        "dam_flight_records_scheduled": 1428,
        "dam_flight_records_codeshare": 34,
        "dam_flight_records_unverified": 3,
        "other_airports_flight_records": 267, # ALP 261 + DEZ 6
        "macro_reported_flights": "",
        "macro_total_passengers": "",
        "macro_arriving_passengers": "",
        "macro_departing_passengers": "",
        "macro_airline_count": "",
        "macro_airspace_overflights": "",
        "macro_geographic_scope": "DAM (plus ALP, DEZ)",
        "macro_reporting_period": "2026-09-30 to 2026-10-31",
        "evidence_classification": "active_snapshot_window",
        "corrective_audit_notes": "RECONCILED: Total flight_events is 1,830 across all airports. DAM-only total is 1,563. DAM physical movements = 98 (Oct 9 & 10 only). Total rows with actual timestamps = 163 for DAM, 207 across all airports."
    }
]

# =============================================================================
# 2. Wayback Machine Empirical Results
# =============================================================================
WAYBACK_AUDIT_RESULTS: List[Dict[str, Any]] = [
    {
        "target_tested": "damairport.gov.sy/api/flights.php",
        "original_url": "https://damairport.gov.sy/api/flights.php",
        "snapshot_timestamp": "20260709234230",
        "archived_url": "https://web.archive.org/web/20260709234230/https://damairport.gov.sy/api/flights.php",
        "http_status": "200",
        "mimetype": "application/json",
        "digest": "LWGQOMIVR7BG55CKGT4LXDRNUVKDA36L",
        "content_length_bytes": "68891 (gzipped: 8874)",
        "contains_actual_flight_info": "Yes",
        "flight_records_count": 1982,
        "identifies_dam_osdi": "Yes (Damascus Airport FIDS API)",
        "movement_data_nature": "scheduled_timetable_only",
        "actual_touchdown_takeoff_timestamps": "No",
        "arrivals_departures_distinguished": "Yes",
        "demonstrated_date_range": "2026-07-05 to 2026-09-09",
        "snapshots_found_2024_2025": 0,
        "availability_verdict": "single_snapshot_2026_only",
        "audit_finding": "Exactly ONE snapshot exists in entire Wayback history. Contains 1,982 scheduled flight objects spanning July 5 to Sept 9, 2026. Zero snapshots exist for 2024 or 2025."
    },
    {
        "target_tested": "damairport.gov.sy",
        "original_url": "https://damairport.gov.sy/",
        "snapshot_timestamp": "20260709222226 to 20260810022046",
        "archived_url": "https://web.archive.org/web/20260709222226/https://damairport.gov.sy/",
        "http_status": "200",
        "mimetype": "text/html",
        "digest": "TPVIZJVQ4CUHWNZVW4CGNKZHL7LWZ3FI (sample)",
        "content_length_bytes": "36269 (sample)",
        "contains_actual_flight_info": "No (Dynamic AJAX shell)",
        "flight_records_count": 0,
        "identifies_dam_osdi": "Yes (Homepage branding)",
        "movement_data_nature": "html_frontend_shell",
        "actual_touchdown_takeoff_timestamps": "No",
        "arrivals_departures_distinguished": "No",
        "demonstrated_date_range": "2026-07-09 to 2026-08-10",
        "snapshots_found_2024_2025": 0,
        "availability_verdict": "no_flight_data_in_html",
        "audit_finding": "19 homepage snapshots exist, all in July-August 2026. Static HTML does not embed flight tables (loaded client-side via AJAX). Zero snapshots exist for 2024 or 2025."
    },
    {
        "target_tested": "syrianair.com",
        "original_url": "https://www.syrianair.com/",
        "snapshot_timestamp": "20240110181156 to 20260130164910",
        "archived_url": "https://web.archive.org/web/20240225092444/https://www.syrianair.com/",
        "http_status": "200, 301, 404",
        "mimetype": "text/html, image/png",
        "digest": "BTDQW4OAZO5VJBG7HTP6L2JEZQJBIISE (sample)",
        "content_length_bytes": "1076 to 1268",
        "contains_actual_flight_info": "No",
        "flight_records_count": 0,
        "identifies_dam_osdi": "No (Minimal redirect shell)",
        "movement_data_nature": "none",
        "actual_touchdown_takeoff_timestamps": "No",
        "arrivals_departures_distinguished": "No",
        "demonstrated_date_range": "2024-2026 (No timetable)",
        "snapshots_found_2024_2025": 0, # zero flight schedule snapshots
        "availability_verdict": "unavailable_no_schedules",
        "audit_finding": "Archived pages are minimal redirects (~1 KB) or asset links. Zero flight schedule, timetable, or booking search results archived."
    },
    {
        "target_tested": "chamwings.com",
        "original_url": "https://chamwings.com/",
        "snapshot_timestamp": "20240104221726 to 20240306093431",
        "archived_url": "https://web.archive.org/web/20240131192933/https://chamwings.com/",
        "http_status": "200, 301",
        "mimetype": "text/html",
        "digest": "VTVUASE4A5B2TXDUHUIFJXREA4W2MQWV (sample)",
        "content_length_bytes": "24862 (sample)",
        "contains_actual_flight_info": "No",
        "flight_records_count": 0,
        "identifies_dam_osdi": "Mentioned in news promo text only",
        "movement_data_nature": "promotional_homepage_only",
        "actual_touchdown_takeoff_timestamps": "No",
        "arrivals_departures_distinguished": "No",
        "demonstrated_date_range": "2024-2026 (No timetable)",
        "snapshots_found_2024_2025": 0, # zero flight schedule snapshots
        "availability_verdict": "unavailable_no_schedules",
        "audit_finding": "116 homepage snapshots in 2024. HTML contains marketing banners and news posts. Does not contain flight timetables, daily flight numbers, or scheduled times."
    }
]

# =============================================================================
# 3. Commercial & Public Tracking Provider Claims Audit
# =============================================================================
PROVIDER_COMPARISON_V2_13_1: List[Dict[str, Any]] = [
    {
        "provider_name": "FlightRadar24",
        "category": "commercial_aggregator",
        "historical_schedule_availability": "Yes (Airline schedule database)",
        "historical_flight_tracking": "Yes (Historical aircraft tracks)",
        "airport_arrivals_departures": "Yes (Airport data module)",
        "actual_touchdown_timestamps": "Conditional (Requires MLAT/ADS-B ground receiver lock)",
        "actual_takeoff_timestamps": "Conditional (Requires MLAT/ADS-B ground receiver lock)",
        "aircraft_registration": "Yes (Tail numbers tracked when transponder emits)",
        "osdi_coverage_demonstrated": "Unverified historical terminal coverage (Known receiver sparsity around DAM)",
        "historical_retention_period": "90d (Silver $14.99/yr), 365d (Gold $44.99/yr, Business $499/yr), Custom quote for multi-year",
        "export_api_availability": "CSV download on Business tier; REST API via commercial contract",
        "pricing_and_terms": "Gold $44.99/yr (personal), Business $499/yr (commercial use). Multi-year OSDI extracts require bespoke sales quote.",
        "factual_verdict": "CONDITIONAL GO",
        "audit_notes": "CORRECTION: Gold tier provides 365 days of personal history at $44.99/yr; Business is $499/yr. Neither plan guarantees runway touchdown data for OSDI due to local receiver sparsity. Must remain CONDITIONAL GO until DAM coverage is proven."
    },
    {
        "provider_name": "FlightAware",
        "category": "commercial_aggregator",
        "historical_schedule_availability": "Yes (Global airline schedule feed)",
        "historical_flight_tracking": "Yes (Aireon space-based ADS-B + terrestrial)",
        "airport_arrivals_departures": "Yes (AeroAPI airport endpoints)",
        "actual_touchdown_timestamps": "Estimated in low-receiver regions (relies on flight plan duration or GDS OOOI)",
        "actual_takeoff_timestamps": "Estimated in low-receiver regions",
        "aircraft_registration": "Yes (When available in flight plan or transponder)",
        "osdi_coverage_demonstrated": "Unverified terminal sensor coverage (En-route Aireon coverage demonstrated)",
        "historical_retention_period": "14d (Personal $0), 30d (Standard $100/mo), Custom quote for multi-year",
        "export_api_availability": "AeroAPI v4 (JSON / REST)",
        "pricing_and_terms": "AeroAPI Standard $100/mo base + query charges. Custom historical airport report $500–$3,000+. Strict non-redistribution terms.",
        "factual_verdict": "CONDITIONAL GO",
        "audit_notes": "AeroAPI provides structured airport queries but historical access older than 30 days requires enterprise pricing. In low-receiver areas, arrival times are estimated rather than sensor-confirmed."
    },
    {
        "provider_name": "ADS-B Exchange",
        "category": "commercial_aggregator",
        "historical_schedule_availability": "No (Tracking and state vectors only; no schedule database)",
        "historical_flight_tracking": "Yes (Raw aircraft state vectors)",
        "airport_arrivals_departures": "No (Does not parse airport arrivals/departures)",
        "actual_touchdown_timestamps": "Requires complex spatial trajectory interpolation to infer runway contact",
        "actual_takeoff_timestamps": "Requires complex spatial trajectory interpolation",
        "aircraft_registration": "Yes (ICAO 24-bit hex code to registration database)",
        "osdi_coverage_demonstrated": "No low-altitude receiver data near Damascus",
        "historical_retention_period": "Historical state vectors available via RapidAPI (2016-present)",
        "export_api_availability": "RapidAPI JSON / Enterprise bulk data",
        "pricing_and_terms": "RapidAPI tiers $10/mo to $400+/mo. High engineering cost to process billions of vectors.",
        "factual_verdict": "NO-GO",
        "audit_notes": "Does not provide parsed airport movements. Raw coordinate data cannot reconstruct runway touchdowns without terrestrial receivers at Damascus."
    },
    {
        "provider_name": "Cirium",
        "category": "enterprise_aviation_analytics",
        "historical_schedule_availability": "Yes (Comprehensive historical airline schedules back to 2000)",
        "historical_flight_tracking": "Yes (Curated historical flight status)",
        "airport_arrivals_departures": "Yes (Diio / Ascend airport movement feeds)",
        "actual_touchdown_timestamps": "Partial (Combines ACARS, ASDI, and airline GDS status)",
        "actual_takeoff_timestamps": "Partial (Combines ACARS, ASDI, and airline GDS status)",
        "aircraft_registration": "Yes (Global aircraft fleet register)",
        "osdi_coverage_demonstrated": "Verified schedule history; physical runway radar coverage unverified",
        "historical_retention_period": "20+ years historical archive",
        "export_api_availability": "Enterprise Snowflake share, flat files, API",
        "pricing_and_terms": "Enterprise contract required: $10,000 to $50,000+/year. No individual or ad-hoc researcher pricing.",
        "factual_verdict": "NO-GO",
        "audit_notes": "Enterprise contract required ($10,000+). Restrictive commercial licensing. Cost-prohibitive for independent project."
    },
    {
        "provider_name": "OAG",
        "category": "enterprise_aviation_analytics",
        "historical_schedule_availability": "Yes (Official Aviation Guide global schedule archive since 1995)",
        "historical_flight_tracking": "No (OAG is fundamentally a schedule/capacity aggregator, not a sensor network)",
        "airport_arrivals_departures": "Yes (Scheduled flights by airport)",
        "actual_touchdown_timestamps": "No (Schedule data only)",
        "actual_takeoff_timestamps": "No (Schedule data only)",
        "aircraft_registration": "No (Equipment type code e.g. 320, 738 only)",
        "osdi_coverage_demonstrated": "Verified historical schedule filings; zero physical radar telemetry",
        "historical_retention_period": "30+ years",
        "export_api_availability": "Schedules Analyzer / Direct data feeds",
        "pricing_and_terms": "Enterprise contract required: $5,000 to $25,000+/year.",
        "factual_verdict": "NO-GO",
        "audit_notes": "Provides scheduled airline filings rather than physical transponder-confirmed operations. Enterprise cost barrier ($5,000+)."
    },
    {
        "provider_name": "OpenSky Network",
        "category": "academic_research",
        "historical_schedule_availability": "No (Pure transponder sensor network)",
        "historical_flight_tracking": "Yes (Raw state vectors and flight table)",
        "airport_arrivals_departures": "Yes (/flights/arrival and /flights/departure endpoints)",
        "actual_touchdown_timestamps": "Calculated only when low-altitude receiver coverage exists",
        "actual_takeoff_timestamps": "Calculated only when low-altitude receiver coverage exists",
        "aircraft_registration": "Yes (Mapped from ICAO 24-bit hex)",
        "osdi_coverage_demonstrated": "Zero low-altitude / runway coverage at OSDI (Proven in V2.7)",
        "historical_retention_period": "2013-present (Academic database)",
        "export_api_availability": "Impala / Trino SQL interface, Python pyopensky, CSV",
        "pricing_and_terms": "Free for non-commercial academic research. Historical queries return HTTP 403 Forbidden to anonymous users.",
        "factual_verdict": "NO-GO for airport movements (CONDITIONAL GO for FIR overflights)",
        "audit_notes": "MANDATE COMPLIANCE: User explicitly prohibits emails, applications, institutional requests, or external outreach. OpenSky remains in inventory as a documented data source, but all external-contact tasks are removed."
    }
]

# =============================================================================
# 4. Reassessed Recovery Opportunities
# =============================================================================
RECOVERY_OPPORTUNITIES_V2_13_1: List[Dict[str, Any]] = [
    {
        "opportunity_id": "REC-OPP-01-V2131",
        "opportunity_title": "Wayback Machine 2026-07-09 FIDS Snapshot Ingestion",
        "decision": "GO",
        "exact_target": "https://web.archive.org/web/20260709234230/https://damairport.gov.sy/api/flights.php",
        "evidence_supporting_availability": "CDX verified: 1 snapshot on 2026-07-09 (digest LWGQOMIVR7BG55CKGT4LXDRNUVKDA36L). Tested payload contains 1,982 JSON flight objects.",
        "actual_demonstrated_date_range": "2026-07-05 to 2026-09-09",
        "geographic_scope": "DAM",
        "data_granularity": "flight_level_schedules",
        "known_limitations": "Scheduled timetable and passenger display status only; no actual radar touchdown timestamps. Covers only July 5 to Sept 9, 2026. Zero snapshots exist for 2024 or 2025.",
        "cost_evidence": "$0.00 (Public web archive)",
        "next_practical_step": "Stage the 1,982 flight objects into an archival timetable staging table without modifying production database."
    },
    {
        "opportunity_id": "REC-OPP-02-V2131",
        "opportunity_title": "Wayback Machine Historical Schedule Recovery (2024-2025)",
        "decision": "NO-GO",
        "exact_target": "damairport.gov.sy, syrianair.com, chamwings.com",
        "evidence_supporting_availability": "CDX audited across all 3 domains: ZERO flight schedule, timetable, or FIDS snapshots exist for 2024 or 2025.",
        "actual_demonstrated_date_range": "None (0 dates demonstrated)",
        "geographic_scope": "DAM",
        "data_granularity": "none",
        "known_limitations": "Domains were either not archived (damairport.gov.sy), archived as redirects (syrianair.com), or archived without flight tables (chamwings.com).",
        "cost_evidence": "$0.00",
        "next_practical_step": "Acknowledge that Wayback Machine cannot recover 2024 or 2025 flight schedules. Close this recovery path."
    },
    {
        "opportunity_id": "REC-OPP-03-V2131",
        "opportunity_title": "SCAA & MoT Sovereign Statistical Publications",
        "decision": "CONDITIONAL GO",
        "exact_target": "Official SCAA Annual Aviation Reports and Monthly Gazettes",
        "evidence_supporting_availability": "31 aggregate macro benchmarks staged in data/macro_benchmarks_staging.db (Grade C from secondary reports). Primary PDFs not yet stored in repo.",
        "actual_demonstrated_date_range": "2025-01-07 to 2026-09-30 (Selected annual/monthly aggregates)",
        "geographic_scope": "DAM (Overflights: OSTT_FIR)",
        "data_granularity": "monthly_annual_macro_aggregates",
        "known_limitations": "Provides aggregate flight and passenger counts; cannot reconstruct individual tail numbers or daily flight records.",
        "cost_evidence": "$0.00 (Sovereign publications)",
        "next_practical_step": "Locate and download official primary PDF publications or gazettes from verified government digital portals to elevate records to Grade A."
    },
    {
        "opportunity_id": "REC-OPP-04-V2131",
        "opportunity_title": "FlightRadar24 Airport History Data Evaluation",
        "decision": "CONDITIONAL GO",
        "exact_target": "FlightRadar24 Airport History (OSDI / DAM)",
        "evidence_supporting_availability": "Public interface confirms flight tracking exists; Gold plan offers 365 days of personal history ($44.99/yr), Business is $499/yr.",
        "actual_demonstrated_date_range": "Rolling 365 days (Requires account)",
        "geographic_scope": "DAM",
        "data_granularity": "flight_level_movements",
        "known_limitations": "Terminal radar coverage at Damascus is unverified; relies on MLAT and satellite ADS-B. Commercial purchase required. Redistribution restricted.",
        "cost_evidence": "Gold $44.99/yr, Business $499/yr. Commercial procurement required.",
        "next_practical_step": "Retain on hold. Do not purchase subscriptions or contact sales."
    },
    {
        "opportunity_id": "REC-OPP-05-V2131",
        "opportunity_title": "FlightAware AeroAPI Custom Report Evaluation",
        "decision": "CONDITIONAL GO",
        "exact_target": "FlightAware AeroAPI / Custom Historical Report",
        "evidence_supporting_availability": "Documented enterprise capability for historical airport movements.",
        "actual_demonstrated_date_range": "Historical multi-year (Requires enterprise contract)",
        "geographic_scope": "DAM",
        "data_granularity": "flight_level_movements",
        "known_limitations": "Expensive ($500–$3,000+). Arrival timestamps estimated in low-receiver regions. Restrictive licensing.",
        "cost_evidence": "$100/mo base (30 days) to $1,500+ for historical reports.",
        "next_practical_step": "Retain on hold. Do not purchase or initiate vendor contact."
    },
    {
        "opportunity_id": "REC-OPP-06-V2131",
        "opportunity_title": "OpenSky Network External Outreach / Application",
        "decision": "NO-GO (Operational Task Removed)",
        "exact_target": "OpenSky Network Academic Research Access",
        "evidence_supporting_availability": "Historical API requires approved credentials (returns 403 to anonymous). V2.7 proved zero low-altitude Damascus coverage.",
        "actual_demonstrated_date_range": "En-route overflights only (>FL300)",
        "geographic_scope": "OSTT_FIR (Airspace only, not OSDI runway)",
        "data_granularity": "raw_state_vectors",
        "known_limitations": "Zero ground receivers at Damascus. Cannot observe runway touchdowns.",
        "cost_evidence": "$0.00 (Academic)",
        "next_practical_step": "MANDATE COMPLIANCE: All external outreach, emails, applications, and account creations are prohibited and removed from action items."
    }
]

def generate_v2_13_1_reports():
    # 1. Verify production DB hash invariant before
    hash_before = get_file_sha256(PROD_DB_PATH)
    assert hash_before == EXPECTED_PROD_HASH, f"Hash mismatch before: {hash_before}"
    print(f"Production DB Hash BEFORE: {hash_before}")

    # 2. Export Coverage Gaps
    gaps_path = "reports/v2_13_1_coverage_gaps.csv"
    os.makedirs(os.path.dirname(gaps_path), exist_ok=True)
    with open(gaps_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(COVERAGE_GAPS_V2_13_1[0].keys()))
        writer.writeheader()
        writer.writerows(COVERAGE_GAPS_V2_13_1)
    print(f"Exported: {gaps_path} ({len(COVERAGE_GAPS_V2_13_1)} periods)")

    # 3. Export Wayback Audit Results
    wayback_path = "reports/v2_13_1_wayback_results.csv"
    with open(wayback_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(WAYBACK_AUDIT_RESULTS[0].keys()))
        writer.writeheader()
        writer.writerows(WAYBACK_AUDIT_RESULTS)
    print(f"Exported: {wayback_path} ({len(WAYBACK_AUDIT_RESULTS)} targets)")

    # 4. Export Provider Comparison
    prov_path = "reports/v2_13_1_provider_comparison.csv"
    with open(prov_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(PROVIDER_COMPARISON_V2_13_1[0].keys()))
        writer.writeheader()
        writer.writerows(PROVIDER_COMPARISON_V2_13_1)
    print(f"Exported: {prov_path} ({len(PROVIDER_COMPARISON_V2_13_1)} providers)")

    # 5. Export Reassessed Recovery Opportunities
    opp_path = "reports/v2_13_1_recovery_opportunities.csv"
    with open(opp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(RECOVERY_OPPORTUNITIES_V2_13_1[0].keys()))
        writer.writeheader()
        writer.writerows(RECOVERY_OPPORTUNITIES_V2_13_1)
    print(f"Exported: {opp_path} ({len(RECOVERY_OPPORTUNITIES_V2_13_1)} opportunities)")

    # 6. Verify production DB hash invariant after
    hash_after = get_file_sha256(PROD_DB_PATH)
    assert hash_after == EXPECTED_PROD_HASH, f"Hash mismatch after: {hash_after}"
    print(f"Production DB Hash AFTER:  {hash_after}")
    print(f"Production DB Untouched:   {hash_before == hash_after}")

if __name__ == "__main__":
    generate_v2_13_1_reports()
