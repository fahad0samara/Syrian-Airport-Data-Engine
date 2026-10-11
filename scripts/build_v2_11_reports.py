"""
Syrian Airport Data Engine — Version 2.11
Build Macro Aviation Statistics Staging Layer & V2.11 Reports
"""

import os
import csv
import json
import sqlite3
from typing import List, Dict, Any
import sys
sys.path.insert(0, ".")
from src.macro_benchmarks import (
    init_macro_benchmarks_table,
    stage_macro_benchmarks,
    validate_benchmark_record,
    detect_overlapping_aggregations
)

MACRO_BENCHMARKS_V2_11: List[Dict[str, Any]] = [
    # =========================================================================
    # 1. Calendar Year 2025 Annual Operational Benchmarks (Complete Period)
    # =========================================================================
    {
        "benchmark_id": "bmk_2025_annual_flights",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2025-01-01",
        "reporting_period_end": "2025-12-31",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "reported_flights",
        "metric_value": 12476,
        "unit": "flights",
        "direction": "total",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-01-15",
        "source_reference": "SANA / Rebuilding Syria, 'Civil Aviation Annual Report 2025: Damascus Airport Operational Performance', published 2026-01-15, economic news dispatch citing SCAA annual operations review, paragraph 1.",
        "source_excerpt": "استقبل مطار دمشق الدولي خلال عام 2025 ما مجموعه 12,476 رحلة جوية",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2025_annual_passengers_total",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2025-01-01",
        "reporting_period_end": "2025-12-31",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "passengers",
        "metric_value": 1434998,
        "unit": "passengers",
        "direction": "total",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-01-15",
        "source_reference": "SANA / Rebuilding Syria, 'Civil Aviation Annual Report 2025: Damascus Airport Passenger Traffic', published 2026-01-15, economic review quoting SCAA statistics, paragraph 2.",
        "source_excerpt": "سجل المطار إجمالي عدد مسافرين بلغ 1,434,998 مسافراً خلال عام 2025",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2025_annual_passengers_arr",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2025-01-01",
        "reporting_period_end": "2025-12-31",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "arriving_passengers",
        "metric_value": 715392,
        "unit": "passengers",
        "direction": "arrival",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-01-15",
        "source_reference": "SANA / Rebuilding Syria, 'Civil Aviation Annual Report 2025: Directional Traffic Disaggregation', published 2026-01-15, quoting SCAA statistics, paragraph 3.",
        "source_excerpt": "بلغ عدد المسافرين القادمين عبر مطار دمشق الدولي 715,392 مسافراً",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2025_annual_passengers_dep",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2025-01-01",
        "reporting_period_end": "2025-12-31",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "departing_passengers",
        "metric_value": 719606,
        "unit": "passengers",
        "direction": "departure",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-01-15",
        "source_reference": "SANA / Rebuilding Syria, 'Civil Aviation Annual Report 2025: Directional Traffic Disaggregation', published 2026-01-15, quoting SCAA statistics, paragraph 3.",
        "source_excerpt": "بلغ عدد المسافرين المغادرين عبر مطار دمشق الدولي 719,606 مسافراً",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },

    # =========================================================================
    # 2. SCAA Reported Window (2025-01-07 to 2025-07-07, Partial Period)
    # =========================================================================
    {
        "benchmark_id": "bmk_2025_h1_reported_flights",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2025-01-07",
        "reporting_period_end": "2025-07-07",
        "period_completeness": "partial",
        "is_partial_period": 1,
        "metric_type": "reported_flights",
        "metric_value": 1870,
        "unit": "flights",
        "direction": "total",
        "geographic_scope": "DAM",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / AksAlSer",
        "source_url": "https://aksalser.com/",
        "source_publication_date": "2025-07-15",
        "source_reference": "AksAlSer / Yalla Syria News, 'Civil Aviation: 1,870 Flights via Damascus Airport in First Half of 2025', published 2025-07-15, quoting SCAA Director General press conference, paragraph 2.",
        "source_excerpt": "سيّر مطار دمشق الدولي 1870 رحلة جوية خلال الفترة من 7 كانون الثاني وحتى 7 تموز 2025 تضمنت 1619 رحلة ركاب و159 وفود و66 حج و26 إغاثية",
        "verification_status": "verified_secondary",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2025_h1_reported_passengers_total",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2025-01-07",
        "reporting_period_end": "2025-07-07",
        "period_completeness": "partial",
        "is_partial_period": 1,
        "metric_type": "passengers",
        "metric_value": 353282,
        "unit": "passengers",
        "direction": "total",
        "geographic_scope": "DAM",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / AksAlSer",
        "source_url": "https://aksalser.com/",
        "source_publication_date": "2025-07-15",
        "source_reference": "AksAlSer / Yalla Syria News, 'Civil Aviation: 353,282 Passengers via Damascus Airport in H1 2025', published 2025-07-15, quoting SCAA semi-annual press statement, paragraph 1.",
        "source_excerpt": "إجمالي عدد المسافرين بلغ 353,282 مسافراً خلال الفترة من 7 كانون الثاني وحتى 7 تموز 2025",
        "verification_status": "verified_secondary",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2025_h1_reported_passengers_arr",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2025-01-07",
        "reporting_period_end": "2025-07-07",
        "period_completeness": "partial",
        "is_partial_period": 1,
        "metric_type": "arriving_passengers",
        "metric_value": 178728,
        "unit": "passengers",
        "direction": "arrival",
        "geographic_scope": "DAM",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / AksAlSer",
        "source_url": "https://aksalser.com/",
        "source_publication_date": "2025-07-15",
        "source_reference": "AksAlSer / Yalla Syria News, 'Civil Aviation: H1 2025 Traffic Disaggregation', published 2025-07-15, quoting SCAA semi-annual bulletin, paragraph 3.",
        "source_excerpt": "بلغ عدد القادمين 178,728 مسافراً",
        "verification_status": "verified_secondary",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2025_h1_reported_passengers_dep",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2025-01-07",
        "reporting_period_end": "2025-07-07",
        "period_completeness": "partial",
        "is_partial_period": 1,
        "metric_type": "departing_passengers",
        "metric_value": 174554,
        "unit": "passengers",
        "direction": "departure",
        "geographic_scope": "DAM",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / AksAlSer",
        "source_url": "https://aksalser.com/",
        "source_publication_date": "2025-07-15",
        "source_reference": "AksAlSer / Yalla Syria News, 'Civil Aviation: H1 2025 Traffic Disaggregation', published 2025-07-15, quoting SCAA semi-annual bulletin, paragraph 3.",
        "source_excerpt": "بلغ عدد المغادرين 174,554 مسافراً",
        "verification_status": "verified_secondary",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2025_h1_reported_airlines",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2025-01-07",
        "reporting_period_end": "2025-07-07",
        "period_completeness": "partial",
        "is_partial_period": 1,
        "metric_type": "operating_airlines",
        "metric_value": 12,
        "unit": "airlines",
        "direction": "total",
        "geographic_scope": "DAM",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / AksAlSer",
        "source_url": "https://aksalser.com/",
        "source_publication_date": "2025-07-15",
        "source_reference": "AksAlSer / Yalla Syria News, 'Civil Aviation: Operating Carriers in H1 2025', published 2025-07-15, quoting SCAA semi-annual bulletin, paragraph 4.",
        "source_excerpt": "عملت 12 شركة طيران في المطار خلال هذه الفترة",
        "verification_status": "verified_secondary",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },

    # =========================================================================
    # 3. April 2026 Monthly Statistics (Partial Month: Apr 8–30 Post-Reopening)
    # =========================================================================
    {
        "benchmark_id": "bmk_2026_04_flights",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-04-08",
        "reporting_period_end": "2026-04-30",
        "period_completeness": "partial",
        "is_partial_period": 1,
        "metric_type": "reported_flights",
        "metric_value": 492,
        "unit": "flights",
        "direction": "total",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-05-05",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation: Traffic Resumption at Damascus International Airport (April 8–30, 2026)', published 2026-05-05, press release paragraph 1.",
        "source_excerpt": "تسجيل 492 رحلة جوية في نيسان 2026",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2026_04_passengers_total",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-04-08",
        "reporting_period_end": "2026-04-30",
        "period_completeness": "partial",
        "is_partial_period": 1,
        "metric_type": "passengers",
        "metric_value": 34347,
        "unit": "passengers",
        "direction": "total",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-05-05",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation: Traffic Resumption at Damascus International Airport (April 8–30, 2026)', published 2026-05-05, press release paragraph 2.",
        "source_excerpt": "حركة مسافرين بلغت 34,347 مسافراً",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2026_04_passengers_arr",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-04-08",
        "reporting_period_end": "2026-04-30",
        "period_completeness": "partial",
        "is_partial_period": 1,
        "metric_type": "arriving_passengers",
        "metric_value": 18385,
        "unit": "passengers",
        "direction": "arrival",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-05-05",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation: Traffic Resumption at Damascus International Airport (April 8–30, 2026)', published 2026-05-05, press release paragraph 3.",
        "source_excerpt": "بلغ عدد القادمين 18,385 مسافراً",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2026_04_passengers_dep",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-04-08",
        "reporting_period_end": "2026-04-30",
        "period_completeness": "partial",
        "is_partial_period": 1,
        "metric_type": "departing_passengers",
        "metric_value": 15962,
        "unit": "passengers",
        "direction": "departure",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-05-05",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation: Traffic Resumption at Damascus International Airport (April 8–30, 2026)', published 2026-05-05, press release paragraph 3.",
        "source_excerpt": "بلغ عدد المغادرين 15,962 مسافراً",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2026_04_airlines",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-04-08",
        "reporting_period_end": "2026-04-30",
        "period_completeness": "partial",
        "is_partial_period": 1,
        "metric_type": "operating_airlines",
        "metric_value": 9,
        "unit": "airlines",
        "direction": "total",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-05-05",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation: Operating Carriers Bulletin (April 8–30, 2026)', published 2026-05-05, paragraph 4.",
        "source_excerpt": "عملت 9 شركات طيران عبر المطار",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2026_04_overflights",
        "airport_icao": "OSTT",
        "airport_iata": None,
        "reporting_period_start": "2026-04-01",
        "reporting_period_end": "2026-04-30",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "airspace_overflights",
        "metric_value": 2523,
        "unit": "overflights",
        "direction": "total",
        "geographic_scope": "OSTT_FIR",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-05-05",
        "source_reference": "Syrian Arab News Agency (SANA), 'Air Navigation Directorate: April 2026 Airspace Overflights Report', published 2026-05-05, paragraph 5.",
        "source_excerpt": "سجلت الأجواء السورية عبور 2,523 طائرة خلال شهر نيسان",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },

    # =========================================================================
    # 4. May 2026 Monthly Statistics (Complete Month)
    # =========================================================================
    {
        "benchmark_id": "bmk_2026_05_flights",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-05-01",
        "reporting_period_end": "2026-05-31",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "reported_flights",
        "metric_value": 1532,
        "unit": "flights",
        "direction": "total",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-06-04",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation Directorate: May 2026 Air Traffic Bulletin', published 2026-06-04, press release paragraph 1.",
        "source_excerpt": "سجل المطار 1532 رحلة جوية في أيار 2026",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2026_05_passengers_total",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-05-01",
        "reporting_period_end": "2026-05-31",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "passengers",
        "metric_value": 148305,
        "unit": "passengers",
        "direction": "total",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-06-04",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation Directorate: May 2026 Air Traffic Bulletin', published 2026-06-04, press release paragraph 2.",
        "source_excerpt": "بلغ إجمالي المسافرين 148,305 مسافرين",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2026_05_passengers_arr",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-05-01",
        "reporting_period_end": "2026-05-31",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "arriving_passengers",
        "metric_value": 83357,
        "unit": "passengers",
        "direction": "arrival",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-06-04",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation Directorate: May 2026 Air Traffic Bulletin', published 2026-06-04, press release paragraph 3.",
        "source_excerpt": "بلغ عدد القادمين 83,357 مسافراً",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2026_05_passengers_dep",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-05-01",
        "reporting_period_end": "2026-05-31",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "departing_passengers",
        "metric_value": 64948,
        "unit": "passengers",
        "direction": "departure",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-06-04",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation Directorate: May 2026 Air Traffic Bulletin', published 2026-06-04, press release paragraph 3.",
        "source_excerpt": "بلغ عدد المغادرين 64,948 مسافراً",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2026_05_airlines",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-05-01",
        "reporting_period_end": "2026-05-31",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "operating_airlines",
        "metric_value": 13,
        "unit": "airlines",
        "direction": "total",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-06-04",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation Directorate: May 2026 Operating Airlines Bulletin', published 2026-06-04, paragraph 4.",
        "source_excerpt": "نفذت الرحلات 13 شركة طيران",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },

    # =========================================================================
    # 5. July 2026 Monthly Statistics (Complete Month)
    # =========================================================================
    {
        "benchmark_id": "bmk_2026_07_flights",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-07-01",
        "reporting_period_end": "2026-07-31",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "reported_flights",
        "metric_value": 2088,
        "unit": "flights",
        "direction": "total",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-08-04",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation Directorate: July 2026 Summer Passenger Traffic Bulletin', published 2026-08-04, press release paragraph 1.",
        "source_excerpt": "سجل المطار 2088 رحلة جوية في تموز 2026",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2026_07_passengers_total",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-07-01",
        "reporting_period_end": "2026-07-31",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "passengers",
        "metric_value": 243260,
        "unit": "passengers",
        "direction": "total",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-08-04",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation Directorate: July 2026 Summer Passenger Traffic Bulletin', published 2026-08-04, press release paragraph 2.",
        "source_excerpt": "بلغ إجمالي المسافرين 243,260 مسافراً",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2026_07_passengers_arr",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-07-01",
        "reporting_period_end": "2026-07-31",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "arriving_passengers",
        "metric_value": 147318,
        "unit": "passengers",
        "direction": "arrival",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-08-04",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation Directorate: July 2026 Summer Passenger Traffic Bulletin', published 2026-08-04, press release paragraph 3.",
        "source_excerpt": "بلغ عدد القادمين 147,318 مسافراً",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2026_07_passengers_dep",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-07-01",
        "reporting_period_end": "2026-07-31",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "departing_passengers",
        "metric_value": 95942,
        "unit": "passengers",
        "direction": "departure",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-08-04",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation Directorate: July 2026 Summer Passenger Traffic Bulletin', published 2026-08-04, press release paragraph 3.",
        "source_excerpt": "بلغ عدد المغادرين 95,942 مسافراً",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2026_07_airlines",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-07-01",
        "reporting_period_end": "2026-07-31",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "operating_airlines",
        "metric_value": 16,
        "unit": "airlines",
        "direction": "total",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-08-04",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation Directorate: July 2026 Summer Passenger Traffic Bulletin', published 2026-08-04, paragraph 4.",
        "source_excerpt": "شغلت 16 شركة طيران رحلاتها في تموز",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },

    # =========================================================================
    # 6. September 2026 Monthly Statistics (Complete Month)
    # =========================================================================
    {
        "benchmark_id": "bmk_2026_09_flights",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-09-01",
        "reporting_period_end": "2026-09-30",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "reported_flights",
        "metric_value": 2022,
        "unit": "flights",
        "direction": "total",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-10-04",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation Directorate: September 2026 Traffic Performance', published 2026-10-04, press release paragraph 1.",
        "source_excerpt": "سجل المطار 2022 رحلة جوية خلال شهر أيلول 2026",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2026_09_passengers_total",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-09-01",
        "reporting_period_end": "2026-09-30",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "passengers",
        "metric_value": 229693,
        "unit": "passengers",
        "direction": "total",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-10-04",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation Directorate: September 2026 Traffic Performance', published 2026-10-04, press release paragraph 2.",
        "source_excerpt": "إجمالي عدد المسافرين بلغ 229,693 مسافراً",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2026_09_passengers_arr",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-09-01",
        "reporting_period_end": "2026-09-30",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "arriving_passengers",
        "metric_value": 98693,
        "unit": "passengers",
        "direction": "arrival",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-10-04",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation Directorate: September 2026 Traffic Performance', published 2026-10-04, press release paragraph 3.",
        "source_excerpt": "بلغ عدد القادمين 98,693 مسافراً",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2026_09_passengers_dep",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-09-01",
        "reporting_period_end": "2026-09-30",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "departing_passengers",
        "metric_value": 131000,
        "unit": "passengers",
        "direction": "departure",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-10-04",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation Directorate: September 2026 Traffic Performance', published 2026-10-04, press release paragraph 3.",
        "source_excerpt": "بلغ عدد المغادرين 131,000 مسافر",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2026_09_airlines",
        "airport_icao": "OSDI",
        "airport_iata": "DAM",
        "reporting_period_start": "2026-09-01",
        "reporting_period_end": "2026-09-30",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "operating_airlines",
        "metric_value": 17,
        "unit": "airlines",
        "direction": "total",
        "geographic_scope": "reported_as_DAM_pending_primary_source_verification",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-10-04",
        "source_reference": "Syrian Arab News Agency (SANA), 'Civil Aviation Directorate: September 2026 Traffic Performance', published 2026-10-04, paragraph 4.",
        "source_excerpt": "شاركت 17 شركة طيران في تنفيذ الرحلات",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    },
    {
        "benchmark_id": "bmk_2026_09_overflights",
        "airport_icao": "OSTT",
        "airport_iata": None,
        "reporting_period_start": "2026-09-01",
        "reporting_period_end": "2026-09-30",
        "period_completeness": "complete",
        "is_partial_period": 0,
        "metric_type": "airspace_overflights",
        "metric_value": 19951,
        "unit": "overflights",
        "direction": "total",
        "geographic_scope": "OSTT_FIR",
        "source_name": "General Authority of Civil Aviation and Air Transport (SCAA) / SANA",
        "source_url": "UNRESOLVED_PRIMARY_URL",
        "source_publication_date": "2026-10-04",
        "source_reference": "Syrian Arab News Agency (SANA), 'Air Navigation Directorate: September 2026 Syrian Airspace Overflights Report', published 2026-10-04, paragraph 5.",
        "source_excerpt": "عدد الطائرات العابرة للأجواء السورية بلغ 19,951 طائرة",
        "verification_status": "unverified_source_url",
        "calculation_method": "official_report",
        "is_derived": 0,
        "collected_at": "2026-10-11T13:40:00Z"
    }
]

def build_v2_11_staging_and_reports():
    staging_db_path = os.path.join("data", "macro_benchmarks_staging.db")
    csv_report_path = os.path.join("reports", "v2_11_macro_statistics_report.csv")
    json_report_path = os.path.join("reports", "v2_11_macro_statistics_report.json")
    
    os.makedirs("data", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    
    # 1. Overlapping aggregation audit
    overlaps = detect_overlapping_aggregations(MACRO_BENCHMARKS_V2_11)
    print("=== PERIOD OVERLAP AUDIT ===")
    print(f"Identified {len(overlaps)} overlapping period pairs that MUST NOT be summed.")
    for ov in overlaps[:3]:
        print(f"  - {ov}")
    if len(overlaps) > 3:
        print(f"  ... and {len(overlaps) - 3} more overlapping pairs.")
        
    # 2. Reset and build staging database
    if os.path.exists(staging_db_path):
        os.remove(staging_db_path)
        
    conn = sqlite3.connect(staging_db_path)
    init_macro_benchmarks_table(conn)
    
    inserted, errors = stage_macro_benchmarks(conn, MACRO_BENCHMARKS_V2_11)
    if errors:
        print("Staging Errors Encountered:")
        for e in errors:
            print(f"  - {e}")
        raise RuntimeError("Validation errors occurred during macro benchmarks staging")
        
    print(f"\nSuccessfully staged {inserted} benchmark records into {staging_db_path}")
    
    # 3. Export V2.11 CSV Report
    fieldnames = list(MACRO_BENCHMARKS_V2_11[0].keys())
    with open(csv_report_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(MACRO_BENCHMARKS_V2_11)
    print(f"Exported V2.11 CSV Report to {csv_report_path}")
    
    # 4. Export V2.11 JSON Report
    with open(json_report_path, "w", encoding="utf-8") as f:
        json.dump(MACRO_BENCHMARKS_V2_11, f, indent=2, ensure_ascii=False)
    print(f"Exported V2.11 JSON Report to {json_report_path}")
    
    # Also keep v2_10 preview updated with new schema fields
    v2_10_csv = os.path.join("reports", "v2_10_macro_benchmarks_preview.csv")
    v2_10_json = os.path.join("reports", "v2_10_macro_benchmarks_preview.json")
    with open(v2_10_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(MACRO_BENCHMARKS_V2_11)
    with open(v2_10_json, "w", encoding="utf-8") as f:
        json.dump(MACRO_BENCHMARKS_V2_11, f, indent=2, ensure_ascii=False)
        
    # Print completeness summary
    cur = conn.cursor()
    cur.execute("SELECT period_completeness, count(*) FROM macro_airport_benchmarks GROUP BY period_completeness")
    for r in cur.fetchall():
        print(f"  - period_completeness '{r[0]}': {r[1]} benchmarks")
        
    conn.close()

if __name__ == "__main__":
    build_v2_11_staging_and_reports()
