import os
import sys
import sqlite3
import hashlib
import csv
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, ".")
from src.api import app

client = TestClient(app)

SIX_PROTECTED_ASSETS = {
    "data/damascus_airport.db": "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b",
    "data/archived_fids_staging.db": "a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4",
    "data/archived_fids_analytics.db": "e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe",
    "data/archived_fids_history_staging.db": "39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f",
    "data/raw/snapshots/wayback_damairport_fids_20260709234230.raw": "5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf",
    "data/raw/snapshots/wayback_damairport_fids_20260709234230.json": "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491",
}

# 1. Six Protected Asset Cryptographic Hash Verification
def test_01_six_protected_assets_hash_verification():
    for path, expected_hash in SIX_PROTECTED_ASSETS.items():
        assert os.path.exists(path), f"File missing: {path}"
        with open(path, "rb") as f:
            computed_hash = hashlib.sha256(f.read()).hexdigest()
        assert computed_hash == expected_hash, f"Hash mismatch for {path}! Expected {expected_hash}, got {computed_hash}"

# 2. Physical Movement Event Audit CSV Verification
def test_02_physical_movement_audit_csv_integrity():
    csv_path = "reports/v2_19_2_physical_movement_audit.csv"
    assert os.path.exists(csv_path)

    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 131, f"Expected 131 physical movements audited, got {len(rows)}"

    dam_rows = [r for r in rows if r["airport_id"] == "DAM"]
    alp_rows = [r for r in rows if r["airport_id"] == "ALP"]
    dez_rows = [r for r in rows if r["airport_id"] == "DEZ"]

    assert len(dam_rows) == 98
    assert len(alp_rows) == 32
    assert len(dez_rows) == 1

    # Verify 100% timestamp provenance
    for r in rows:
        assert r["timestamp_provenance_verified"] == "YES"
        assert r["runway_sensor_evidence_present"] == "NO"
        assert r["movement_evidence_classification"] == "commercial_operational_status_timestamp"

# 3. Verified Endpoint Filtering Logic Check
def test_03_verified_endpoint_filtering_logic():
    res = client.get("/api/movements/verified?airport_id=DAM&limit=200")
    assert res.status_code == 200
    data = res.json()
    assert data["record_nature"] == "physical_movement"
    assert data["airport_filter"] == "DAM"
    assert len(data["movements"]) == 98

    for m in data["movements"]:
        assert m["airport_id"] == "DAM"
        assert m["record_nature"] == "physical_movement"
        actual_ts = m["actual_dep_time"] if m["movement_type"] == "departure" else m["actual_arr_time"]
        assert actual_ts is not None

# 4. Regional Aggregate Cannot Be Exported Under DAM-Only Label
def test_04_regional_aggregate_not_exported_under_dam_label():
    # Attempting to export regional 2024 series under a DAM-only label must return 404
    for invalid_dataset in ["damascus_historical_2024", "damascus_movements_2024", "dam_2024"]:
        res = client.get(f"/api/export/{invalid_dataset}")
        assert res.status_code == 404

    # Valid export historical_2024 exists and returns multi-airport data
    res_valid = client.get("/api/export/historical_2024?format=csv")
    assert res_valid.status_code == 200
    content = res_valid.content.decode("utf-8")
    assert "DAM_ALP_LTK" in content or "movement_date" in content or "flight_date" in content

# 5. Taxonomy Invariant: Overflight Multi-Parameter Classification
def test_05_overflight_multi_parameter_classification():
    obs_file = "reports/v2_18_recovered_observations.csv"
    with open(obs_file, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for r in rows:
        if r["classification"] == "overflight_observation":
            # Multi-parameter check: high altitude AND high distance AND cruise speed
            assert float(r["altitude_baro_ft"]) >= 20000.0
            assert float(r["distance_to_dam_km"]) > 80.0
            assert float(r["speed_kts"]) > 350.0
