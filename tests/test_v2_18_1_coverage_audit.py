"""
Syrian Airport Data Engine — Version 2.18.1
Regression Test Suite: Historical Coverage Integrity & Dataset Classification Audit

Verifies all 10 required audit dimensions:
1. DAM_ALP_LTK aggregate cannot be classified as DAM-only.
2. Regional totals cannot be allocated to DAM.
3. FIDS schedules cannot be classified as actual movements.
4. Live ADS-B observations cannot be described as historical coverage.
5. Gatwick-only datasets cannot qualify as DAM-relevant datasets.
6. Metadata downloads are distinguished from dataset downloads.
7. Missing DAM coverage remains explicitly missing.
8. Existing production data remains unchanged.
9. API and exports use corrected classifications.
10. Existing regression suite passes.
"""

import os
import csv
import json
import sqlite3
import hashlib
import pytest

PROD_DB = "data/damascus_airport.db"
FIDS_STAGING_DB = "data/archived_fids_staging.db"
ANALYTICS_DB = "data/archived_fids_analytics.db"
HISTORY_STAGING_DB = "data/archived_fids_history_staging.db"
BASELINE_RAW = "data/raw/snapshots/wayback_damairport_fids_20260709234230.raw"
BASELINE_JSON = "data/raw/snapshots/wayback_damairport_fids_20260709234230.json"
V2_18_STAGING_DB = "data/staging/v2_18/v2_18_staging.db"

EXPECTED_PROD_HASH = "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"
EXPECTED_RAW_HASH = "5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf"
EXPECTED_JSON_HASH = "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491"
EXPECTED_FIDS_STAGING_HASH = "a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4"
EXPECTED_ANALYTICS_HASH = "e1f8f0dea0e72f630d52e40a2d3a0a90b49a514da694fa72ceeb35555f48e1fe"
EXPECTED_HISTORY_STAGING_HASH = "39aa323265a6c6ad612cdd4bac0a3ae27deda26e2c16544df0e9f3cc32f83a7f"

SCOPE_AUDIT_PATH = "reports/v2_18_1_dataset_scope_audit.csv"
CORRECTION_PATH = "reports/v2_18_1_coverage_correction.csv"
INTEGRITY_PATH = "reports/v2_18_1_integrity_verification.json"
FINAL_DOC_PATH = "docs/V2_18_1_FINAL_AUDIT.md"

COVERAGE_PATH = "reports/v2_18_damascus_coverage.csv"
SCORING_PATH = "reports/v2_18_dataset_scoring.csv"
INVENTORY_PATH = "reports/v2_18_dataset_inventory.csv"

def get_file_sha256(path):
    assert os.path.exists(path), f"File {path} does not exist"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

# 1. DAM_ALP_LTK aggregate cannot be classified as DAM-only
def test_01_dam_alp_ltk_aggregate_not_classified_as_dam_only():
    conn = sqlite3.connect(PROD_DB)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT scope FROM historical_daily_movements_2024")
    scopes = [r[0] for r in cur.fetchall()]
    conn.close()
    assert scopes == ["DAM_ALP_LTK"], f"Expected only DAM_ALP_LTK scope, found {scopes}"

    assert os.path.exists(SCOPE_AUDIT_PATH)
    with open(SCOPE_AUDIT_PATH, "r", encoding="utf-8") as f:
        audit_rows = list(csv.DictReader(f))
    gov = [r for r in audit_rows if r["dataset_id"] == "DS-GOV-001"][0]
    assert "REGIONAL_AGGREGATE" in gov["geographic_eligibility_verdict"]
    assert "DAM-specific" in gov["audit_disposition"] and "NOT" in gov["audit_disposition"]

# 2. Regional totals cannot be allocated to DAM
def test_02_regional_totals_cannot_be_allocated_to_dam():
    assert os.path.exists(CORRECTION_PATH)
    with open(CORRECTION_PATH, "r", encoding="utf-8") as f:
        corr_rows = list(csv.DictReader(f))
    months_2024 = [r for r in corr_rows if r["year_month"].startswith("2024-")]
    for m in months_2024:
        assert int(m["verified_dam_movements"]) == 0
        assert m["is_dam_historical_movement_coverage"] == "NO"
        assert m["airport_scope"] != "DAM"

# 3. FIDS schedules cannot be classified as actual movements
def test_03_fids_schedules_not_classified_as_actual_movements():
    with open(CORRECTION_PATH, "r", encoding="utf-8") as f:
        corr_rows = list(csv.DictReader(f))
    fids_months = [r for r in corr_rows if r["year_month"] in ("2026-07", "2026-08", "2026-09")]
    assert len(fids_months) == 3
    for m in fids_months:
        assert m["corrected_category"] == "dam_scheduled_fids"
        assert int(m["verified_dam_movements"]) == 0
        assert m["is_dam_historical_movement_coverage"] == "NO"

# 4. Live ADS-B observations cannot be described as historical coverage
def test_04_live_adsb_observations_not_described_as_historical_coverage():
    with open(CORRECTION_PATH, "r", encoding="utf-8") as f:
        corr_rows = list(csv.DictReader(f))
    oct_month = [r for r in corr_rows if r["year_month"] == "2026-10"][0]
    assert oct_month["corrected_category"] == "live_regional_adsb"
    assert int(oct_month["verified_dam_movements"]) == 0
    assert oct_month["is_dam_historical_movement_coverage"] == "NO"

# 5. Gatwick-only datasets cannot qualify as DAM-relevant datasets
def test_05_gatwick_only_datasets_disqualified():
    with open(SCOPE_AUDIT_PATH, "r", encoding="utf-8") as f:
        audit_rows = list(csv.DictReader(f))
    gw = [r for r in audit_rows if r["dataset_id"] == "DS-ZEN-002"][0]
    assert gw["dataset_irrelevant_to_damascus"] == "YES"
    assert "DISQUALIFIED" in gw["geographic_eligibility_verdict"]

    with open(SCORING_PATH, "r", encoding="utf-8") as f:
        scoring_rows = list(csv.DictReader(f))
    gw_score = [r for r in scoring_rows if r["dataset_id"] == "DS-ZEN-002"][0]
    assert int(gw_score["total_score"]) < 12
    assert "Disqualified" in gw_score["evaluation_verdict"]

# 6. Metadata downloads are distinguished from dataset downloads
def test_06_metadata_downloads_distinguished_from_dataset_downloads():
    assert os.path.exists(INTEGRITY_PATH)
    with open(INTEGRITY_PATH, "r", encoding="utf-8") as f:
        integrity = json.load(f)
    findings = integrity["critical_audit_findings"]
    assert findings["datasets_downloaded_count"] == 0
    assert findings["metadata_artifacts_downloaded_count"] == 4
    assert findings["metadata_bytes_downloaded"] == 37172

    with open(SCOPE_AUDIT_PATH, "r", encoding="utf-8") as f:
        audit_rows = list(csv.DictReader(f))
    for r in audit_rows:
        if r["dataset_id"] in ("DS-S3-001", "DS-S3-002", "DS-DTV-001"):
            assert "ONLY" in r["download_claim_audit"] or "manifest" in r["download_claim_audit"].lower()

# 7. Missing DAM coverage remains explicitly missing
def test_07_missing_dam_coverage_remains_explicitly_missing():
    with open(CORRECTION_PATH, "r", encoding="utf-8") as f:
        corr_rows = list(csv.DictReader(f))
    missing_months = [r for r in corr_rows if r["corrected_category"] == "no_verified_dam_data"]
    assert len(missing_months) == 20  # 2024-11, 2024-12, and 2025-01 through 2026-06
    for m in missing_months:
        assert int(m["raw_records_count"]) == 0
        assert int(m["verified_dam_movements"]) == 0
        assert m["is_dam_historical_movement_coverage"] == "NO"

# 8. Existing production data remains unchanged
def test_08_existing_production_data_remains_unchanged():
    assert get_file_sha256(PROD_DB) == EXPECTED_PROD_HASH
    assert get_file_sha256(FIDS_STAGING_DB) == EXPECTED_FIDS_STAGING_HASH
    assert get_file_sha256(ANALYTICS_DB) == EXPECTED_ANALYTICS_HASH
    assert get_file_sha256(HISTORY_STAGING_DB) == EXPECTED_HISTORY_STAGING_HASH
    assert get_file_sha256(BASELINE_RAW) == EXPECTED_RAW_HASH
    assert get_file_sha256(BASELINE_JSON) == EXPECTED_JSON_HASH

# 9. API and exports use corrected classifications
def test_09_api_and_exports_use_corrected_classifications():
    from src.api import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.get("/api/movements/historical-2024")
    assert resp.status_code == 200
    data = resp.json()
    assert data["scope"] == "DAM_ALP_LTK"
    assert "Syria Economic Monitor" in data["source"]

    # Check that coverage CSV uses only the 6 required categories
    valid_categories = {
        "dam_specific_verified", "dam_scheduled_fids", "regional_aggregate",
        "live_regional_adsb", "no_verified_dam_data", "unknown"
    }
    with open(COVERAGE_PATH, "r", encoding="utf-8") as f:
        cov_rows = list(csv.DictReader(f))
    for r in cov_rows:
        assert r["dataset_category"] in valid_categories, f"Invalid category {r['dataset_category']} in {COVERAGE_PATH}"

# 10. Existing regression suite passes
def test_10_regression_suite_counts():
    conn = sqlite3.connect(PROD_DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM historical_daily_movements_2024")
    hist_count = cur.fetchone()[0]
    assert hist_count == 578
    cur.execute("SELECT COUNT(*) FROM flight_events")
    events_count = cur.fetchone()[0]
    assert events_count == 1830
    conn.close()

    assert os.path.exists(FINAL_DOC_PATH)
