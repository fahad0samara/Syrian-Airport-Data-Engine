# -*- coding: utf-8 -*-
"""
Tests for Syrian Air Traffic Monitor standalone page and API endpoints.
Validates scheduled arrivals/departures purity, explicit 48h ADS-B sample labeling, and exports.
"""
import io
import pandas as pd
from fastapi.testclient import TestClient

from src.api import app

client = TestClient(app)

def test_air_traffic_monitor_page_routes():
    """Verify both /monitor and /air-traffic serve the HTML monitor page."""
    res_monitor = client.get("/monitor")
    assert res_monitor.status_code == 200
    assert "text/html" in res_monitor.headers["content-type"]
    assert "مرصد الحركة الجوية السورية" in res_monitor.text
    assert "Syrian Air Traffic Monitor" in res_monitor.text

    res_air_traffic = client.get("/air-traffic")
    assert res_air_traffic.status_code == 200
    assert "مرصد الحركة الجوية السورية" in res_air_traffic.text

def test_original_index_page_preserved():
    """Ensure the existing index page at / and /data is completely preserved."""
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "Syrian Airport Data Engine" in res_root.text

    res_data = client.get("/data")
    assert res_data.status_code == 200

def test_air_traffic_kpis_default_october_2026():
    """Verify default KPIs for latest available month (October 2026) and explicit sample labeling."""
    res = client.get("/api/air-traffic/kpis")
    assert res.status_code == 200
    data = res.json()

    assert data["period"]["month"] == "2026-10"
    kpis = data["kpis"]
    # Total actual movements across Syria in Oct 2026 sample
    assert kpis["actual_movements"] == 131
    assert "October 9–10 sample only" in kpis["actual_movements_label"]
    assert kpis["scheduled_flights"] == 1572
    assert kpis["active_airlines"] > 0
    assert kpis["active_destinations"] > 0
    assert kpis["airports_covered"] == 3
    # Passengers strictly null
    assert kpis["passengers"] is None

    # Definitions are complete and explicitly define sample & airline scope
    defs = data["definitions"]
    assert "October 9–10 sample only" in defs["actual_movements"]
    assert "17 distinct carriers" in defs["active_airlines"]
    assert "scheduled_flights" in defs

def test_air_traffic_kpis_damascus_specific():
    """Verify DAM specific KPIs (98 actual movements in 48h sample)."""
    res = client.get("/api/air-traffic/kpis?airport_id=DAM")
    assert res.status_code == 200
    data = res.json()

    kpis = data["kpis"]
    assert kpis["actual_movements"] == 98
    assert "October 9–10 sample only" in kpis["actual_movements_label"]
    assert kpis["scheduled_flights"] == 1365
    assert kpis["airports_covered"] == 1
    assert kpis["passengers"] is None

def test_air_traffic_kpis_unobserved_month_september_2026():
    """Verify that unobserved actual movements in Sep 2026 are returned as None/null, not 0."""
    res = client.get("/api/air-traffic/kpis?month=2026-09")
    assert res.status_code == 200
    data = res.json()

    kpis = data["kpis"]
    assert kpis["actual_movements"] is None
    assert kpis["actual_movements_status"] == "unobserved_data_gap"
    assert kpis["scheduled_flights"] > 0
    assert kpis["passengers"] is None

def test_air_traffic_monthly_summary():
    """Verify monthly summary endpoint structure, scheduled arrivals/departures purity, and unobserved actuals handling."""
    res = client.get("/api/air-traffic/monthly-summary")
    assert res.status_code == 200
    data = res.json()

    assert "summary" in data
    assert data["count"] > 0

    # Check rows
    for r in data["summary"]:
        assert "month" in r
        assert "airport_id" in r
        assert "scheduled_flights" in r
        assert "scheduled_arrivals" in r
        assert "scheduled_departures" in r
        # Purity check: scheduled arrivals + scheduled departures MUST equal scheduled flights exactly
        assert r["scheduled_arrivals"] + r["scheduled_departures"] == r["scheduled_flights"]

        assert "passengers" in r
        # Passengers strictly None
        assert r["passengers"] is None

        if r["month"] == "2026-09":
            # Must be None/null, not 0
            assert r["actual_movements"] is None
        elif r["month"] == "2026-10" and r["airport_id"] == "DAM":
            assert r["actual_movements"] == 98
            # Exact pure scheduled counts for DAM
            assert r["scheduled_arrivals"] == 682
            assert r["scheduled_departures"] == 683
            assert r["scheduled_flights"] == 1365
            assert "October 9–10 sample only" in r["actual_movements_note"]

def test_air_traffic_filter_options():
    """Verify dropdown filter options endpoint."""
    res = client.get("/api/air-traffic/filter-options")
    assert res.status_code == 200
    data = res.json()

    assert "airports" in data
    assert "months" in data
    assert "airlines" in data
    assert "destinations" in data

    airport_ids = [a["airport_id"] for a in data["airports"]]
    assert "DAM" in airport_ids
    assert "ALP" in airport_ids

def test_air_traffic_export_events_csv_and_xlsx():
    """Verify CSV and XLSX export for detailed flight events."""
    # CSV
    res_csv = client.get("/api/air-traffic/export/events?format=csv&airport_id=DAM")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "attachment; filename=\"syrian_flight_events.csv\"" in res_csv.headers["content-disposition"]
    csv_text = res_csv.text
    assert "Date,Airport,Movement Type,Actual/Scheduled Classification" in csv_text
    assert "DAM" in csv_text
    assert "ADS-B Observed Movement — Commercial Tracking Data (October 9–10 sample only)" in csv_text

    # XLSX
    res_xlsx = client.get("/api/air-traffic/export/events?format=xlsx&airport_id=DAM")
    assert res_xlsx.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res_xlsx.headers["content-type"]

    # Verify excel file is readable by pandas
    excel_buf = io.BytesIO(res_xlsx.content)
    df = pd.read_excel(excel_buf)
    assert not df.empty
    assert "Airport" in df.columns
    assert "Actual/Scheduled Classification" in df.columns

def test_air_traffic_export_monthly_csv_and_xlsx():
    """Verify CSV and XLSX export for monthly summary."""
    # CSV
    res_csv = client.get("/api/air-traffic/export/monthly?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "Scheduled Arrivals" in res_csv.text
    assert "Scheduled Departures" in res_csv.text
    assert "ADS-B Observed Movements — Commercial Tracking Data (October 9–10 sample only)" in res_csv.text

    # XLSX
    res_xlsx = client.get("/api/air-traffic/export/monthly?format=xlsx")
    assert res_xlsx.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res_xlsx.headers["content-type"]

    excel_buf = io.BytesIO(res_xlsx.content)
    df = pd.read_excel(excel_buf)
    assert not df.empty
    assert "ADS-B Observed Movements — Commercial Tracking Data (October 9–10 sample only)" in df.columns
    assert "Scheduled Flights" in df.columns
    assert "Scheduled Arrivals" in df.columns
    assert "Scheduled Departures" in df.columns

    # Verify scheduled arrivals + departures == scheduled flights in every exported row
    for idx, row in df.iterrows():
        assert row["Scheduled Arrivals"] + row["Scheduled Departures"] == row["Scheduled Flights"]
