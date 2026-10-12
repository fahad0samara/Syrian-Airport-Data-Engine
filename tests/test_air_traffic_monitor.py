# -*- coding: utf-8 -*-
"""
Tests for Syrian Air Traffic Monitor standalone page and CSV-first API endpoints.
Validates:
1. Scheduled services are not counted as observed movements.
2. Only physical_movement records contribute to observed movement counts.
3. Marketing codeshare records are excluded from observed movement KPIs.
4. Unverified movement records are excluded from observed movement KPIs.
5. Scheduled services with cancelled status are still counted as scheduled services.
6. Scheduled services with diverted status are still counted as scheduled services.
7. Scheduled services with active or unknown status are handled correctly.
8. Missing observation records are not converted to zero movements.
9. No observed movement records returns the correct status without claiming zero actual flights.
10. Monitoring coverage remains unknown when no monitoring evidence exists.
11. Schedule coverage and observation coverage are calculated independently.
12. Airport, month, airline, and destination filters produce consistent results.
13. CSV and Excel exports preserve the correct record classifications and metric definitions.
14. Missing or invalid primary CSV produces a clear error and does not trigger SQL fallback.
15. Passenger values remain NULL when no source-backed passenger data exists.
16. Monthly aggregation never combines scheduled and observed movements.
17. Duplicate event IDs are handled according to existing methodology without inflating counts.
"""
import io
import tempfile
from pathlib import Path
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.api import app
from src.air_traffic_api import load_primary_flight_events, apply_filters, compute_schedule_coverage, compute_observation_coverage

client = TestClient(app)

def test_01_page_routes_and_main_dashboard_preserved():
    """Verify monitor page routes and confirm main / and /data dashboard is preserved."""
    res_monitor = client.get("/monitor")
    assert res_monitor.status_code == 200
    assert "مرصد الحركة الجوية السورية" in res_monitor.text
    assert "Syrian Air Traffic Monitor" in res_monitor.text

    res_air = client.get("/air-traffic")
    assert res_air.status_code == 200

    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "Syrian Airport Data Engine" in res_root.text

    res_data = client.get("/data")
    assert res_data.status_code == 200

def test_02_scheduled_services_not_counted_as_observed():
    """Verify scheduled services never count as observed movements."""
    res = client.get("/api/air-traffic/kpis?airport_id=DAM&month=2026-10")
    assert res.status_code == 200
    data = res.json()

    kpis = data["kpis"]
    sched = data["schedule_coverage"]
    obs = data["observation_coverage"]

    # DAM October 2026 pure figures
    assert sched["scheduled_service_records"] == 1365
    assert obs["observed_movements"] == 98
    # Ensure they are completely distinct and not conflated
    assert kpis["scheduled_flights"] != kpis["actual_movements"]
    assert kpis["actual_movements"] == 98
    assert kpis["scheduled_flights"] == 1365

def test_03_only_physical_movement_counted_in_observed():
    """Verify only physical_movement records contribute to observed movement counts."""
    df = load_primary_flight_events()
    dam_oct = df[(df["airport_id"] == "DAM") & (df["flight_date"].str.startswith("2026-10"))]

    obs = compute_observation_coverage(dam_oct)
    assert obs["observed_movements"] == 98
    assert obs["observed_arrivals"] == 48
    assert obs["observed_departures"] == 50
    assert obs["observed_arrivals"] + obs["observed_departures"] == 98

def test_04_codeshare_records_excluded_from_observed_kpis():
    """Verify marketing codeshare records are excluded from observed movement totals."""
    res = client.get("/api/air-traffic/kpis?airport_id=DAM&month=2026-10")
    data = res.json()

    kpis = data["kpis"]
    # 20 codeshare flights in landed/departed sample, 34 total in DAM Oct
    assert kpis["marketing_codeshares"] == 34
    # Observed movements must remain 98, strictly excluding the 34 codeshares
    assert kpis["actual_movements"] == 98

def test_05_unverified_records_excluded_from_observed_kpis():
    """Verify unverified movement records are excluded from observed movement totals."""
    res = client.get("/api/air-traffic/kpis?airport_id=DAM&month=2026-10")
    data = res.json()

    kpis = data["kpis"]
    assert kpis["unverified_movements"] == 3
    # Observed movements must strictly exclude unverified movements (remains 98)
    assert kpis["actual_movements"] == 98

def test_06_scheduled_services_with_cancelled_diverted_active_unknown_status():
    """Verify scheduled services include cancelled, diverted, active, unknown statuses."""
    df = load_primary_flight_events()
    dam_oct = df[(df["airport_id"] == "DAM") & (df["flight_date"].str.startswith("2026-10"))]
    sched = dam_oct[dam_oct["record_nature"] == "scheduled_service"]

    # All scheduled service statuses
    status_counts = sched["flight_status"].value_counts().to_dict()
    assert status_counts.get("scheduled") == 1335
    assert status_counts.get("active") == 14
    assert status_counts.get("unknown") == 10
    assert status_counts.get("cancelled") == 4
    assert status_counts.get("diverted") == 2
    # Sum must equal 1365 exactly
    assert sum(status_counts.values()) == 1365

    cov = compute_schedule_coverage(dam_oct)
    assert cov["scheduled_service_records"] == 1365

def test_07_missing_observation_records_not_converted_to_zero():
    """Verify that dates without observation records return None/null, not 0."""
    res = client.get("/api/air-traffic/kpis?airport_id=DAM&month=2026-09")
    assert res.status_code == 200
    data = res.json()

    kpis = data["kpis"]
    obs = data["observation_coverage"]

    # September 2026 had no ADS-B telemetry
    assert kpis["actual_movements"] is None
    assert obs["observed_movements"] is None
    assert obs["observed_arrivals"] is None
    assert obs["observed_departures"] is None
    assert obs["status"] == "No Observed Movement Records"

def test_08_no_observed_movement_records_status_semantics():
    """Verify 'No Observed Movement Records' does not imply zero flights occurred."""
    res = client.get("/api/air-traffic/kpis?airport_id=DAM&month=2026-09")
    data = res.json()

    obs = data["observation_coverage"]
    assert obs["status"] == "No Observed Movement Records"
    assert "No Observed Movement Records" in obs["methodology_note"]
    assert "does not mean zero flights occurred" in obs["methodology_note"]

def test_09_monitoring_coverage_unknown_semantics():
    """Verify monitoring coverage outside observed dates is explicitly marked Unknown."""
    res = client.get("/api/air-traffic/kpis?airport_id=DAM&month=2026-10")
    data = res.json()

    obs = data["observation_coverage"]
    assert obs["monitoring_outside_status"] == "Monitoring Coverage Unknown"
    assert "Monitoring Coverage Unknown" in obs["methodology_note"]

def test_10_schedule_and_observation_coverage_independent():
    """Verify schedule coverage and actual observation coverage are calculated independently."""
    res = client.get("/api/air-traffic/coverage?airport_id=DAM&month=2026-10")
    assert res.status_code == 200
    data = res.json()

    sched = data["schedule_coverage"]
    obs = data["observation_coverage"]

    # Independent dates and windows
    assert sched["status"] == "Available"
    assert sched["scheduled_dates_count"] == 31
    assert sched["first_scheduled_date"] == "2026-10-01"
    assert sched["last_scheduled_date"] == "2026-10-31"

    assert obs["status"] == "Observed Movements Available"
    assert obs["observed_dates_count"] == 2
    assert obs["first_observed_date"] == "2026-10-09"
    assert obs["last_observed_date"] == "2026-10-10"
    assert obs["observed_dates"] == ["2026-10-09", "2026-10-10"]

def test_11_filter_consistency_across_metrics():
    """Verify airport, month, airline, and destination filters produce consistent results."""
    # Filter by Cham Wings
    res = client.get("/api/air-traffic/kpis?airport_id=DAM&month=2026-10&airline=Cham%20Wings%20Airlines")
    assert res.status_code == 200
    data = res.json()

    kpis = data["kpis"]
    sched = data["schedule_coverage"]
    obs = data["observation_coverage"]

    assert kpis["scheduled_flights"] == sched["scheduled_service_records"]
    assert kpis["actual_movements"] == obs["observed_movements"]
    assert sched["scheduled_arrivals"] + sched["scheduled_departures"] == sched["scheduled_service_records"]

def test_12_exports_preserve_record_classifications():
    """Verify CSV and XLSX exports preserve record_nature and classification."""
    # CSV events export
    res = client.get("/api/air-traffic/export/events?format=csv&airport_id=DAM&month=2026-10")
    assert res.status_code == 200
    csv_text = res.text

    assert "Actual/Scheduled Classification" in csv_text
    assert "Record Nature Key" in csv_text
    assert "Evidence / Source" in csv_text
    assert "Evidence Classification" in csv_text
    assert "physical_movement" in csv_text
    assert "scheduled_service" in csv_text

    # Excel coverage export
    res_cov = client.get("/api/air-traffic/export/coverage?format=xlsx&airport_id=DAM&month=2026-10")
    assert res_cov.status_code == 200
    df = pd.read_excel(io.BytesIO(res_cov.content))
    assert not df.empty
    assert "Schedule Coverage Status" in df.columns
    assert "Observation Coverage Status" in df.columns
    assert "Monitoring Coverage Outside Observed Dates" in df.columns

def test_13_missing_primary_csv_returns_clear_error():
    """Verify missing primary CSV produces a clear 500 error and does NOT trigger SQL fallback."""
    fake_path = Path("data/processed/non_existent_flight_events.csv")
    with pytest.raises(Exception) as exc_info:
        load_primary_flight_events(fake_path)
    assert "is missing" in str(exc_info.value.detail)

def test_14_invalid_schema_csv_returns_clear_error():
    """Verify CSV missing required columns produces a clear 500 error."""
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv") as tf:
        tf.write("flight_date,airport_id\n2026-10-01,DAM\n")
        temp_name = tf.name

    try:
        with pytest.raises(Exception) as exc_info:
            load_primary_flight_events(Path(temp_name))
        assert "missing required columns" in str(exc_info.value.detail)
    finally:
        Path(temp_name).unlink(missing_ok=True)

def test_15_passenger_values_remain_null():
    """Verify passenger values remain strictly None / null across all endpoints."""
    res_kpis = client.get("/api/air-traffic/kpis?airport_id=DAM&month=2026-10")
    assert res_kpis.json()["kpis"]["passengers"] is None

    res_summary = client.get("/api/air-traffic/monthly-summary?airport_id=DAM")
    for r in res_summary.json()["summary"]:
        assert r["passengers"] is None

def test_16_monthly_aggregation_never_combines_scheduled_and_observed():
    """Verify monthly summary separates scheduled arrivals/departures from observed ones."""
    res = client.get("/api/air-traffic/monthly-summary?airport_id=DAM&month=2026-10")
    assert res.status_code == 200
    data = res.json()["summary"][0]

    assert data["scheduled_flights"] == 1365
    assert data["scheduled_arrivals"] == 682
    assert data["scheduled_departures"] == 683
    assert data["actual_movements"] == 98
    assert data["observed_arrivals"] == 48
    assert data["observed_departures"] == 50
    # Scheduled arrivals + departures == scheduled flights
    assert data["scheduled_arrivals"] + data["scheduled_departures"] == data["scheduled_flights"]
    # Observed arrivals + departures == actual movements
    assert data["observed_arrivals"] + data["observed_departures"] == data["actual_movements"]

def test_17_unique_event_ids_no_inflation():
    """Verify event IDs in primary CSV are unique and no silent inflation exists."""
    df = load_primary_flight_events()
    assert df["event_id"].nunique() == len(df)
    assert len(df) == 1830
