"""
Syrian Airport Data Engine — Version 2.13
Historical Data Recovery Feasibility & Recovery Roadmap Report Generator

Generates:
- reports/v2_13_historical_source_inventory.csv
- reports/v2_13_historical_source_inventory.json
- reports/v2_13_coverage_gaps.csv
- reports/v2_13_recovery_opportunities.csv
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
# 1. Source Inventory Data
# =============================================================================
HISTORICAL_SOURCES: List[Dict[str, Any]] = [
    # Free & Public Sources
    {
        "source_id": "opensky_network",
        "provider_name": "OpenSky Network",
        "provider_category": "academic_research",
        "historical_availability": "Conditional",
        "earliest_date": "2013-01-01",
        "airport_specific": "Yes",
        "flight_level_data": "Yes",
        "actual_movement_timestamps": "Yes",
        "arrivals_departures_segregated": "Yes",
        "raw_export_available": "Yes",
        "authentication_required": "Institutional",
        "cost_category": "Free",
        "dam_coverage_evidence": "empirically_tested_sparse",
        "known_limitations": "Free REST API blocks historical queries (HTTP 403). Requires approved academic research application. Empirical testing in V2.7 proved zero ground receivers within 50 km of DAM; sees en-route overflights only (>FL300).",
        "recommendation": "CONDITIONAL GO"
    },
    {
        "source_id": "adsb_lol",
        "provider_name": "ADS-B.lol",
        "provider_category": "free_public",
        "historical_availability": "No",
        "earliest_date": "Live Only",
        "airport_specific": "No",
        "flight_level_data": "Partial",
        "actual_movement_timestamps": "No",
        "arrivals_departures_segregated": "No",
        "raw_export_available": "No",
        "authentication_required": "Not required",
        "cost_category": "Free",
        "dam_coverage_evidence": "empirically_tested_sparse",
        "known_limitations": "Live-only point/radius API. No historical REST query endpoints for airport movements. Zero ground coverage at Damascus in V2.7 live tests.",
        "recommendation": "NO-GO"
    },
    {
        "source_id": "adsb_fi",
        "provider_name": "ADSB.fi",
        "provider_category": "free_public",
        "historical_availability": "No",
        "earliest_date": "Live Only",
        "airport_specific": "No",
        "flight_level_data": "Partial",
        "actual_movement_timestamps": "No",
        "arrivals_departures_segregated": "No",
        "raw_export_available": "No",
        "authentication_required": "Not required",
        "cost_category": "Free",
        "dam_coverage_evidence": "empirically_tested_sparse",
        "known_limitations": "Live open-data API only. No historical arrival/departure search. Sees high-altitude overflights (FL310+) in Levant, but no low-altitude terminal fixes at OSDI.",
        "recommendation": "NO-GO"
    },
    {
        "source_id": "adsb_exchange_public",
        "provider_name": "ADS-B Exchange (Public Web)",
        "provider_category": "free_public",
        "historical_availability": "No",
        "earliest_date": "Live Only",
        "airport_specific": "No",
        "flight_level_data": "Partial",
        "actual_movement_timestamps": "No",
        "arrivals_departures_segregated": "No",
        "raw_export_available": "No",
        "authentication_required": "Not required",
        "cost_category": "Free",
        "dam_coverage_evidence": "blocked_paywall",
        "known_limitations": "Public tracking map is live-only. Historical queries require commercial RapidAPI enterprise subscription. No free historical airport data downloads.",
        "recommendation": "NO-GO"
    },
    {
        "source_id": "ourairports",
        "provider_name": "OurAirports",
        "provider_category": "free_public",
        "historical_availability": "Not applicable",
        "earliest_date": "Static Infrastructure",
        "airport_specific": "Yes",
        "flight_level_data": "No",
        "actual_movement_timestamps": "No",
        "arrivals_departures_segregated": "No",
        "raw_export_available": "Yes",
        "authentication_required": "Not required",
        "cost_category": "Free",
        "dam_coverage_evidence": "verified_in_repo",
        "known_limitations": "Provides open aeronautical metadata (runways, coordinates, frequencies, elevation) only. Does not record flight movements, schedules, or timestamps.",
        "recommendation": "NO-GO"
    },
    {
        "source_id": "flightradar24_public",
        "provider_name": "FlightRadar24 (Public / Web)",
        "provider_category": "free_public",
        "historical_availability": "Conditional",
        "earliest_date": "Rolling 7 Days",
        "airport_specific": "Yes",
        "flight_level_data": "Yes",
        "actual_movement_timestamps": "Partial",
        "arrivals_departures_segregated": "Yes",
        "raw_export_available": "No",
        "authentication_required": "Not required",
        "cost_category": "Free",
        "dam_coverage_evidence": "verified_in_repo",
        "known_limitations": "Free tier strictly limited to past 7 days of airport arrivals and departures. Raw downloads not provided. Older historical records require paid tier.",
        "recommendation": "CONDITIONAL GO"
    },
    {
        "source_id": "flightaware_public",
        "provider_name": "FlightAware (Public / Web)",
        "provider_category": "free_public",
        "historical_availability": "No",
        "earliest_date": "Past 48-72 Hours",
        "airport_specific": "Yes",
        "flight_level_data": "Yes",
        "actual_movement_timestamps": "Partial",
        "arrivals_departures_segregated": "Yes",
        "raw_export_available": "No",
        "authentication_required": "Not required",
        "cost_category": "Free",
        "dam_coverage_evidence": "blocked_paywall",
        "known_limitations": "Free public interface limited to recent 2-3 days. Historical queries older than 7 days require paid AeroAPI tier ($100+/mo).",
        "recommendation": "NO-GO"
    },
    {
        "source_id": "damairport_official",
        "provider_name": "Official Damascus Airport Website (damairport.gov.sy)",
        "provider_category": "official_authority",
        "historical_availability": "Conditional",
        "earliest_date": "Current FIDS Snapshot",
        "airport_specific": "Yes",
        "flight_level_data": "Yes",
        "actual_movement_timestamps": "No",
        "arrivals_departures_segregated": "Yes",
        "raw_export_available": "Yes",
        "authentication_required": "Not required",
        "cost_category": "Free",
        "dam_coverage_evidence": "verified_in_repo",
        "known_limitations": "Live FIDS endpoint (flights.php) provides current flight schedule; retains ~10-15 days of recent past schedules but no multi-year historical archive. Lacks actual transponder/radar timestamps.",
        "recommendation": "CONDITIONAL GO"
    },
    {
        "source_id": "scaa_publications",
        "provider_name": "Syrian Civil Aviation Authority (SCAA)",
        "provider_category": "official_authority",
        "historical_availability": "Yes",
        "earliest_date": "2024-01-01",
        "airport_specific": "Yes",
        "flight_level_data": "No",
        "actual_movement_timestamps": "No",
        "arrivals_departures_segregated": "Yes",
        "raw_export_available": "No",
        "authentication_required": "Not required",
        "cost_category": "Free",
        "dam_coverage_evidence": "unverified_quoted",
        "known_limitations": "Publishes aggregate macro statistics (annual, semi-annual, monthly flight and passenger totals). Does not provide flight-level logs. Physical PDFs/gazettes must be acquired to elevate from Grade C.",
        "recommendation": "GO"
    },
    {
        "source_id": "syrian_mot",
        "provider_name": "Syrian Ministry of Transport (MoT)",
        "provider_category": "official_authority",
        "historical_availability": "Yes",
        "earliest_date": "2024-01-01",
        "airport_specific": "Yes",
        "flight_level_data": "No",
        "actual_movement_timestamps": "No",
        "arrivals_departures_segregated": "Yes",
        "raw_export_available": "No",
        "authentication_required": "Not required",
        "cost_category": "Free",
        "dam_coverage_evidence": "unverified_quoted",
        "known_limitations": "Annual economic performance reviews summarize aggregate passenger and cargo volumes across Syrian transport infrastructure. Lacks individual flight events.",
        "recommendation": "GO"
    },
    {
        "source_id": "sana_news",
        "provider_name": "Syrian Arab News Agency (SANA)",
        "provider_category": "official_authority",
        "historical_availability": "Yes",
        "earliest_date": "2024-01-01",
        "airport_specific": "Yes",
        "flight_level_data": "Partial",
        "actual_movement_timestamps": "Partial",
        "arrivals_departures_segregated": "Partial",
        "raw_export_available": "No",
        "authentication_required": "Not required",
        "cost_category": "Free",
        "dam_coverage_evidence": "unverified_quoted",
        "known_limitations": "Reports official operational milestones (Dec 8 closure, Dec 18 domestic resumption, Jan 7 international resumption, Apr 8 reopening) and monthly aggregate traffic bulletins. Direct canonical permalinks currently unverified.",
        "recommendation": "CONDITIONAL GO"
    },
    {
        "source_id": "syria_economic_monitor",
        "provider_name": "Syria Economic Monitor (World Bank / Data Partnership)",
        "provider_category": "academic_research",
        "historical_availability": "Yes",
        "earliest_date": "2024-01-01",
        "airport_specific": "No",
        "flight_level_data": "No",
        "actual_movement_timestamps": "No",
        "arrivals_departures_segregated": "Yes",
        "raw_export_available": "Yes",
        "authentication_required": "Not required",
        "cost_category": "Free",
        "dam_coverage_evidence": "verified_in_repo",
        "known_limitations": "578 daily rows in repo (289 arr, 289 dep) covering 2024-01-01 to 2024-10-15. Strictly scoped to DAM_ALP_LTK (composite 3-airport gateway). Disaggregation into Damascus-specific data is mathematically prohibited.",
        "recommendation": "GO"
    },
    {
        "source_id": "wayback_machine",
        "provider_name": "Internet Archive / Wayback Machine",
        "provider_category": "open_archive",
        "historical_availability": "Yes",
        "earliest_date": "2024-01-01",
        "airport_specific": "Yes",
        "flight_level_data": "Yes",
        "actual_movement_timestamps": "Partial",
        "arrivals_departures_segregated": "Yes",
        "raw_export_available": "Yes",
        "authentication_required": "Not required",
        "cost_category": "Free",
        "dam_coverage_evidence": "unverified_quoted",
        "known_limitations": "Contains periodic web snapshots of damairport.gov.sy, syrianair.com, chamwings.com, and flightradar24.com/data/airports/dam. Granularity depends on crawl frequency; provides timetable snapshots and archived news dispatches.",
        "recommendation": "GO"
    },

    # Commercial Sources
    {
        "source_id": "flightradar24_commercial",
        "provider_name": "FlightRadar24 (Commercial / Business / Custom Data)",
        "provider_category": "commercial_aggregator",
        "historical_availability": "Yes",
        "earliest_date": "2020-01-01",
        "airport_specific": "Yes",
        "flight_level_data": "Yes",
        "actual_movement_timestamps": "Yes",
        "arrivals_departures_segregated": "Yes",
        "raw_export_available": "Yes",
        "authentication_required": "Required",
        "cost_category": "Subscription",
        "dam_coverage_evidence": "verified_in_repo",
        "known_limitations": "Business tier ($499/yr) offers up to 365 days of historical airport data. Multi-year raw CSV extracts require custom commercial sales quotation. Terrestrial receiver coverage in Syria is historically sparse; relies on MLAT and satellite ADS-B.",
        "recommendation": "CONDITIONAL GO"
    },
    {
        "source_id": "flightaware_aeroapi",
        "provider_name": "FlightAware (AeroAPI / Custom Reports)",
        "provider_category": "commercial_aggregator",
        "historical_availability": "Yes",
        "earliest_date": "2015-01-01",
        "airport_specific": "Yes",
        "flight_level_data": "Yes",
        "actual_movement_timestamps": "Yes",
        "arrivals_departures_segregated": "Yes",
        "raw_export_available": "Yes",
        "authentication_required": "Required",
        "cost_category": "Custom quotation",
        "dam_coverage_evidence": "blocked_paywall",
        "known_limitations": "AeroAPI historical tier ($100–$1,000+/mo) or custom airport reports ($500–$3,000). Commercial license restricts redistribution or open publication. Radar coverage over Damascus is limited; relies on GDS schedule progress updates.",
        "recommendation": "CONDITIONAL GO"
    },
    {
        "source_id": "adsb_exchange_commercial",
        "provider_name": "ADS-B Exchange (Commercial Historical)",
        "provider_category": "commercial_aggregator",
        "historical_availability": "Yes",
        "earliest_date": "2016-01-01",
        "airport_specific": "No",
        "flight_level_data": "Yes",
        "actual_movement_timestamps": "Yes",
        "arrivals_departures_segregated": "No",
        "raw_export_available": "Yes",
        "authentication_required": "Required",
        "cost_category": "Subscription",
        "dam_coverage_evidence": "blocked_paywall",
        "known_limitations": "Provides raw aircraft state vectors via RapidAPI ($100–$1,000/mo). Does not parse airport arrivals/departures; requires custom trajectory modeling to infer touchdowns. Lacks low-altitude receiver coverage at OSDI.",
        "recommendation": "NO-GO"
    },
    {
        "source_id": "cirium_historical",
        "provider_name": "Cirium (Ascend / Diio / Core Aviation)",
        "provider_category": "commercial_aggregator",
        "historical_availability": "Yes",
        "earliest_date": "2010-01-01",
        "airport_specific": "Yes",
        "flight_level_data": "Yes",
        "actual_movement_timestamps": "Partial",
        "arrivals_departures_segregated": "Yes",
        "raw_export_available": "Yes",
        "authentication_required": "Required",
        "cost_category": "Enterprise custom",
        "dam_coverage_evidence": "blocked_paywall",
        "known_limitations": "Enterprise custom contract required ($10,000+/yr). Focuses on published airline schedules, capacity, and flight status. Does not provide cheap ad-hoc extracts. Highly restricted redistribution terms.",
        "recommendation": "NO-GO"
    },
    {
        "source_id": "oag_historical",
        "provider_name": "OAG (Official Aviation Guide)",
        "provider_category": "commercial_aggregator",
        "historical_availability": "Yes",
        "earliest_date": "2000-01-01",
        "airport_specific": "Yes",
        "flight_level_data": "Yes",
        "actual_movement_timestamps": "No",
        "arrivals_departures_segregated": "Yes",
        "raw_export_available": "Yes",
        "authentication_required": "Required",
        "cost_category": "Enterprise custom",
        "dam_coverage_evidence": "blocked_paywall",
        "known_limitations": "Enterprise contract required ($5,000–$20,000+/yr). Contains published airline schedules, equipment, and frequencies, not physical transponder sensor proofs. High cost barrier for independent research.",
        "recommendation": "NO-GO"
    }
]

# =============================================================================
# 2. Historical Coverage Gaps Breakdown (2024-01-01 to Present)
# =============================================================================
COVERAGE_GAPS: List[Dict[str, Any]] = [
    {
        "period_id": "GAP-2024-P1",
        "period_start": "2024-01-01",
        "period_end": "2024-10-15",
        "calendar_days": 289,
        "period_name": "2024 Pre-Transition Gateway Monitoring",
        "verified_physical_movements": 0,
        "commercial_schedules": 0,
        "unverified_movement_observations": 0,
        "aggregate_airport_statistics": 578,  # 289 arr, 289 dep daily totals in SEM table
        "national_airspace_statistics": 0,
        "unknown_or_unavailable": 0,
        "coverage_state": "aggregate_composite_only",
        "primary_causes": "Flight-level physical radar data missing. Daily movements exist exclusively as multi-airport composite (DAM_ALP_LTK) from World Bank / SEM. Damascus-specific disaggregation is mathematically prohibited.",
        "recovery_feasibility": "medium"
    },
    {
        "period_id": "GAP-2024-P2",
        "period_start": "2024-10-16",
        "period_end": "2024-12-07",
        "calendar_days": 53,
        "period_name": "2024 Late Autumn Pre-Transition Vacuum",
        "verified_physical_movements": 0,
        "commercial_schedules": 0,
        "unverified_movement_observations": 0,
        "aggregate_airport_statistics": 0,
        "national_airspace_statistics": 0,
        "unknown_or_unavailable": 53,
        "coverage_state": "complete_gap",
        "primary_causes": "World Bank SEM coverage terminated on 2024-10-15. No FIDS feeds, no public radar snapshots, and no official bulletins archived for this 53-day window.",
        "recovery_feasibility": "low"
    },
    {
        "period_id": "GAP-2024-P3",
        "period_start": "2024-12-08",
        "period_end": "2024-12-17",
        "calendar_days": 10,
        "period_name": "December 2024 Emergency Airspace Suspension",
        "verified_physical_movements": 0,
        "commercial_schedules": 0,
        "unverified_movement_observations": 0,
        "aggregate_airport_statistics": 0,
        "national_airspace_statistics": 0,
        "unknown_or_unavailable": 10,
        "coverage_state": "complete_gap",
        "primary_causes": "Civil aviation operations halted under emergency NOTAM. Commercial flights zero, but ad-hoc evacuation/diplomatic flights unverified. Zero transponder records in repository.",
        "recovery_feasibility": "low"
    },
    {
        "period_id": "GAP-2024-P4",
        "period_start": "2024-12-18",
        "period_end": "2025-01-06",
        "calendar_days": 20,
        "period_name": "Domestic Flight Resumption & Pre-International Resumption",
        "verified_physical_movements": 0,
        "commercial_schedules": 0,
        "unverified_movement_observations": 0,
        "aggregate_airport_statistics": 0,
        "national_airspace_statistics": 0,
        "unknown_or_unavailable": 20,
        "coverage_state": "complete_gap",
        "primary_causes": "Domestic flights resumed Dec 18 (DAM-ALP); international flights remained closed. No daily flight logs archived. SCAA annual remainder excludes this window without itemization.",
        "recovery_feasibility": "medium"
    },
    {
        "period_id": "GAP-2025-H1",
        "period_start": "2025-01-07",
        "period_end": "2025-07-07",
        "calendar_days": 182,
        "period_name": "2025 SCAA 6-Month Post-Resumption Milestone",
        "verified_physical_movements": 0,
        "commercial_schedules": 0,
        "unverified_movement_observations": 0,
        "aggregate_airport_statistics": 1870,  # Staged as macro benchmark (1870 flights, 353k pax)
        "national_airspace_statistics": 0,
        "unknown_or_unavailable": 182,  # Daily flight-level records are entirely missing
        "coverage_state": "aggregate_macro_only",
        "primary_causes": "Official SCAA press conference reported 1,870 flights (1,619 pax, 159 deleg, 66 hajj, 26 relief) and 353,282 pax. Staged as macro benchmarks (Grade C). Daily flight-level telemetry completely missing.",
        "recovery_feasibility": "high"
    },
    {
        "period_id": "GAP-2025-H2",
        "period_start": "2025-07-08",
        "period_end": "2025-12-31",
        "calendar_days": 177,
        "period_name": "2025 Second Half Operational Expansion",
        "verified_physical_movements": 0,
        "commercial_schedules": 0,
        "unverified_movement_observations": 0,
        "aggregate_airport_statistics": 12476,  # Full annual figure 12,476 flights; remainder 10,606 excluded from benchmarks
        "national_airspace_statistics": 0,
        "unknown_or_unavailable": 177,
        "coverage_state": "aggregate_macro_only",
        "primary_causes": "Covered only by full-year annual total (12,476 flights; 1,434,998 pax) under unverified primary URL. Subtraction remainder (10,606 flights) is an analytical artifact. Zero daily flight events.",
        "recovery_feasibility": "medium"
    },
    {
        "period_id": "GAP-2026-Q1",
        "period_start": "2026-01-01",
        "period_end": "2026-04-07",
        "calendar_days": 97,
        "period_name": "2026 Airport Infrastructure Rehabilitation Closure",
        "verified_physical_movements": 0,
        "commercial_schedules": 0,
        "unverified_movement_observations": 0,
        "aggregate_airport_statistics": 0,
        "national_airspace_statistics": 0,
        "unknown_or_unavailable": 97,
        "coverage_state": "complete_gap",
        "primary_causes": "Damascus airport closed for comprehensive runway and terminal reconstruction prior to April 8 reopening. Commercial schedules zero; potential relief/state flights unrecorded.",
        "recovery_feasibility": "low"
    },
    {
        "period_id": "GAP-2026-M04",
        "period_start": "2026-04-08",
        "period_end": "2026-04-30",
        "calendar_days": 23,
        "period_name": "April 2026 Commercial Reopening",
        "verified_physical_movements": 0,
        "commercial_schedules": 0,
        "unverified_movement_observations": 0,
        "aggregate_airport_statistics": 492,  # 492 flights, 34k pax
        "national_airspace_statistics": 2523,  # OSTT_FIR overflights
        "unknown_or_unavailable": 23,
        "coverage_state": "aggregate_macro_only",
        "primary_causes": "SCAA/SANA reported 492 flights and 34,347 pax, but source excerpt quotes 'في نيسان 2026'; reporting boundary is unresolved. 2,523 overflights cover OSTT_FIR. Flight-level events missing.",
        "recovery_feasibility": "high"
    },
    {
        "period_id": "GAP-2026-M05",
        "period_start": "2026-05-01",
        "period_end": "2026-05-31",
        "calendar_days": 31,
        "period_name": "May 2026 Operational Ramp-Up",
        "verified_physical_movements": 0,
        "commercial_schedules": 0,
        "unverified_movement_observations": 0,
        "aggregate_airport_statistics": 1532,  # 1532 flights, 148k pax
        "national_airspace_statistics": 0,
        "unknown_or_unavailable": 31,
        "coverage_state": "aggregate_macro_only",
        "primary_causes": "Monthly bulletin reports 1,532 flights and 148,305 pax (Grade C). Zero daily flight events in repository.",
        "recovery_feasibility": "high"
    },
    {
        "period_id": "GAP-2026-M06",
        "period_start": "2026-06-01",
        "period_end": "2026-06-30",
        "calendar_days": 30,
        "period_name": "June 2026 Reporting Gap",
        "verified_physical_movements": 0,
        "commercial_schedules": 0,
        "unverified_movement_observations": 0,
        "aggregate_airport_statistics": 0,
        "national_airspace_statistics": 0,
        "unknown_or_unavailable": 30,
        "coverage_state": "complete_gap",
        "primary_causes": "No monthly bulletin staged. No flight events. Complete data vacuum.",
        "recovery_feasibility": "medium"
    },
    {
        "period_id": "GAP-2026-M07",
        "period_start": "2026-07-01",
        "period_end": "2026-07-31",
        "calendar_days": 31,
        "period_name": "July 2026 High Summer Peak",
        "verified_physical_movements": 0,
        "commercial_schedules": 0,
        "unverified_movement_observations": 0,
        "aggregate_airport_statistics": 2088,  # 2088 flights, 243k pax
        "national_airspace_statistics": 0,
        "unknown_or_unavailable": 31,
        "coverage_state": "aggregate_macro_only",
        "primary_causes": "Monthly bulletin reports 2,088 flights and 243,260 pax (Grade C). Zero daily flight events.",
        "recovery_feasibility": "high"
    },
    {
        "period_id": "GAP-2026-M08",
        "period_start": "2026-08-01",
        "period_end": "2026-08-31",
        "calendar_days": 31,
        "period_name": "August 2026 Reporting Gap",
        "verified_physical_movements": 0,
        "commercial_schedules": 0,
        "unverified_movement_observations": 0,
        "aggregate_airport_statistics": 0,
        "national_airspace_statistics": 0,
        "unknown_or_unavailable": 31,
        "coverage_state": "complete_gap",
        "primary_causes": "No monthly bulletin staged. No flight events. Complete data vacuum.",
        "recovery_feasibility": "medium"
    },
    {
        "period_id": "GAP-2026-M09",
        "period_start": "2026-09-01",
        "period_end": "2026-09-29",
        "calendar_days": 29,
        "period_name": "September 2026 Pre-Snapshot Window",
        "verified_physical_movements": 0,
        "commercial_schedules": 0,
        "unverified_movement_observations": 0,
        "aggregate_airport_statistics": 2022,  # 2022 flights, 229k pax
        "national_airspace_statistics": 19951,  # 19951 overflights
        "unknown_or_unavailable": 29,
        "coverage_state": "aggregate_macro_only",
        "primary_causes": "Monthly bulletin reports 2,022 flights, 229,693 pax, and 19,951 overflights (Grade C). Daily flight events do not begin until 2026-09-30.",
        "recovery_feasibility": "high"
    },
    {
        "period_id": "GAP-2026-SNAPSHOT",
        "period_start": "2026-09-30",
        "period_end": "2026-10-31",
        "calendar_days": 32,
        "period_name": "Active Ingestion & Snapshot Window",
        "verified_physical_movements": 207,  # Actual movement timestamps in flight_events
        "commercial_schedules": 1623,  # Scheduled services in flight_events
        "unverified_movement_observations": 3,
        "aggregate_airport_statistics": 1563,  # damascus_daily_movements table
        "national_airspace_statistics": 0,
        "unknown_or_unavailable": 0,
        "coverage_state": "active_snapshot_window",
        "primary_causes": "Only period in repository with flight-level events. Concentrated around recent snapshot; 207 verified physical movements, 1,623 scheduled flights (mostly future).",
        "recovery_feasibility": "high"
    }
]

# =============================================================================
# 3. Recovery Opportunities Inventory
# =============================================================================
RECOVERY_OPPORTUNITIES: List[Dict[str, Any]] = [
    {
        "opportunity_id": "REC-OPP-01",
        "source": "Internet Archive / Wayback Machine",
        "priority_level": "P0",
        "target_period": "2024-01-01 to 2026-09-29",
        "geographic_scope": "DAM",
        "data_granularity": "flight_level",
        "expected_fields": "flight_number, scheduled_time, origin_destination, airline_name, status",
        "evidence_quality": "scheduled_timetable",
        "acquisition_method": "Query Wayback Machine CDX API for snapshots of damairport.gov.sy/api/flights.php, syrianair.com timetables, and chamwings.com schedules.",
        "known_limitations": "Web crawls are periodic; provides published timetable schedules rather than actual radar transponder touchdown timestamps.",
        "estimated_cost_category": "Free",
        "confidence_level": "Medium",
        "actionable_next_step": "Run automated URL query against web.archive.org/cdx/search/cdx for damairport.gov.sy endpoints."
    },
    {
        "opportunity_id": "REC-OPP-02",
        "source": "Syrian Civil Aviation Authority (SCAA) Official Bulletins",
        "priority_level": "P1",
        "target_period": "2024-01-01 to 2026-09-30",
        "geographic_scope": "DAM",
        "data_granularity": "monthly_annual_macro",
        "expected_fields": "total_flights, arriving_passengers, departing_passengers, operating_airlines, cargo_tonnage",
        "evidence_quality": "primary_official",
        "acquisition_method": "Locate and download official SCAA Statistical Bulletins and Ministry of Transport Annual Reports from public governmental repositories.",
        "known_limitations": "Provides aggregate airport-level totals only; cannot reconstruct individual daily flights or aircraft airframes.",
        "estimated_cost_category": "Free",
        "confidence_level": "High",
        "actionable_next_step": "Retrieve raw SCAA 2025 Annual Report and 2026 monthly press releases to elevate staged Grade C benchmarks to Grade A."
    },
    {
        "opportunity_id": "REC-OPP-03",
        "source": "Wayback Machine FlightRadar24 Airport History",
        "priority_level": "P2",
        "target_period": "2024-01-01 to 2025-12-31",
        "geographic_scope": "DAM",
        "data_granularity": "flight_level",
        "expected_fields": "flight_number, airline, aircraft_model, registration, scheduled_time, actual_time",
        "evidence_quality": "secondary_curated",
        "acquisition_method": "Query Internet Archive for historical snapshots of flightradar24.com/data/airports/dam/arrivals and departures.",
        "known_limitations": "Availability depends on whether Internet Archive bots crawled FR24 airport pages during 2024-2025.",
        "estimated_cost_category": "Free",
        "confidence_level": "Medium",
        "actionable_next_step": "Audit CDX index for flightradar24.com/data/airports/dam/* snapshots."
    },
    {
        "opportunity_id": "REC-OPP-04",
        "source": "FlightRadar24 Business Subscription / Historical API",
        "priority_level": "P3",
        "target_period": "Past 365 Days (Rolling)",
        "geographic_scope": "DAM",
        "data_granularity": "flight_level",
        "expected_fields": "flight_number, actual_dep_time, actual_arr_time, aircraft_reg, icao24, route",
        "evidence_quality": "unfiltered_telemetry",
        "acquisition_method": "Purchase standard Business subscription ($499/year) to unlock 365 days of airport arrivals and departures.",
        "known_limitations": "Requires commercial subscription. Limited to past 365 days (cannot recover early 2024 without custom quotation). Syrian receiver coverage sparse.",
        "estimated_cost_category": "Commercial subscription",
        "confidence_level": "High",
        "actionable_next_step": "Evaluate project budget approval before initiating commercial procurement."
    },
    {
        "opportunity_id": "REC-OPP-05",
        "source": "FlightAware AeroAPI Historical Data Extract",
        "priority_level": "P3",
        "target_period": "2024-01-01 to 2026-09-30",
        "geographic_scope": "DAM",
        "data_granularity": "flight_level",
        "expected_fields": "ident, actual_off, actual_on, origin, destination, aircraft_type, registration",
        "evidence_quality": "secondary_curated",
        "acquisition_method": "Request custom historical airport report from FlightAware commercial sales team.",
        "known_limitations": "Requires custom quotation and budget. Data often relies on GDS schedule progress in regions with low terrestrial ADS-B receiver density.",
        "estimated_cost_category": "Custom quotation",
        "confidence_level": "Medium",
        "actionable_next_step": "Define exact historical date boundaries and request formal quotation if approved."
    },
    {
        "opportunity_id": "REC-OPP-06",
        "source": "OpenSky Network Historical Research Access",
        "priority_level": "P4",
        "target_period": "2024-01-01 to 2026-09-30",
        "geographic_scope": "OSTT_FIR",
        "data_granularity": "raw_state_vectors",
        "expected_fields": "time, icao24, lat, lon, altitude, velocity, track, callsign",
        "evidence_quality": "unfiltered_telemetry",
        "acquisition_method": "Submit the completed V2.6 OpenSky Academic Research Access application through an accredited university partner.",
        "known_limitations": "Requires formal institutional sponsorship. Zero ground receiver coverage at Damascus; only captures en-route flights (>FL300) transiting Syrian airspace.",
        "estimated_cost_category": "Free",
        "confidence_level": "Low",
        "actionable_next_step": "Awaits formal project sponsor authorization before academic submission."
    }
]

def generate_reports():
    # 1. Hash invariant check before
    hash_before = get_file_sha256(PROD_DB_PATH)
    assert hash_before == EXPECTED_PROD_HASH, f"Hash mismatch before: {hash_before}"
    print(f"Production DB Hash BEFORE: {hash_before}")

    # 2. Export Source Inventory (CSV & JSON)
    inv_csv_path = "reports/v2_13_historical_source_inventory.csv"
    inv_json_path = "reports/v2_13_historical_source_inventory.json"
    os.makedirs(os.path.dirname(inv_csv_path), exist_ok=True)

    with open(inv_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(HISTORICAL_SOURCES[0].keys()))
        writer.writeheader()
        writer.writerows(HISTORICAL_SOURCES)
    print(f"Exported: {inv_csv_path} ({len(HISTORICAL_SOURCES)} sources)")

    with open(inv_json_path, "w", encoding="utf-8") as f:
        json.dump(HISTORICAL_SOURCES, f, indent=2, ensure_ascii=False)
    print(f"Exported: {inv_json_path}")

    # 3. Export Coverage Gaps (CSV)
    gaps_csv_path = "reports/v2_13_coverage_gaps.csv"
    with open(gaps_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(COVERAGE_GAPS[0].keys()))
        writer.writeheader()
        writer.writerows(COVERAGE_GAPS)
    print(f"Exported: {gaps_csv_path} ({len(COVERAGE_GAPS)} chronological periods)")

    # 4. Export Recovery Opportunities (CSV)
    rec_csv_path = "reports/v2_13_recovery_opportunities.csv"
    with open(rec_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(RECOVERY_OPPORTUNITIES[0].keys()))
        writer.writeheader()
        writer.writerows(RECOVERY_OPPORTUNITIES)
    print(f"Exported: {rec_csv_path} ({len(RECOVERY_OPPORTUNITIES)} recovery opportunities)")

    # 5. Hash invariant check after
    hash_after = get_file_sha256(PROD_DB_PATH)
    assert hash_after == EXPECTED_PROD_HASH, f"Hash mismatch after: {hash_after}"
    print(f"\nProduction DB Hash AFTER:  {hash_after}")
    print(f"Production DB Untouched:   {hash_before == hash_after}")

if __name__ == "__main__":
    generate_reports()
