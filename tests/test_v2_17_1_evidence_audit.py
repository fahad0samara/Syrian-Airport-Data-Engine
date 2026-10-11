"""
Syrian Airport Data Engine — Version 2.17.1
Test Suite: Final Evidence and Classification Audit Verification
"""

import os
import json
import csv
import sqlite3
import hashlib
import pytest

PROD_DB = "data/damascus_airport.db"
EXPECTED_PROD_HASH = "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"

def get_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def test_v2_17_1_wayback_classification_audit():
    audit_path = "reports/v2_17_1_wayback_classification_audit.csv"
    assert os.path.exists(audit_path)
    with open(audit_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 5

    # Check baseline capture is complete
    baseline = [r for r in rows if r["capture_id"] == "snap_wayback_20260709234230"][0]
    assert baseline["completeness_classification"] == "complete"
    assert baseline["response_body_available"].startswith("YES")
    assert baseline["can_completeness_be_established"] == "YES"

    # Check 4 unretrieved captures are classified as unknown
    unretrieved = [r for r in rows if r["capture_id"] != "snap_wayback_20260709234230"]
    assert len(unretrieved) == 4
    for r in unretrieved:
        assert r["completeness_classification"] == "unknown"
        assert r["response_body_available"].startswith("NO")
        assert r["can_completeness_be_established"] == "NO"

def test_v2_17_1_adsb_claim_audit():
    claim_path = "reports/v2_17_1_adsb_claim_audit.csv"
    assert os.path.exists(claim_path)
    with open(claim_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 5

    categories = {r["access_classification"] for r in rows}
    assert "Authentication required" in categories
    assert "HTTP error or temporary service failure" in categories
    assert "Live-only access" in categories
    assert "Paid access" in categories
    assert "Not investigated" in categories

    # Ensure OpenSky is classified as Authentication required
    opensky = [r for r in rows if "OpenSky" in r["provider"]][0]
    assert opensky["access_classification"] == "Authentication required"
    assert "HTTP 403" in opensky["observed_response"]

    # Ensure ADS-B.lol and ADSB.fi are HTTP error / temporary service failure
    lol = [r for r in rows if "ADS-B.lol" in r["provider"]][0]
    assert lol["access_classification"] == "HTTP error or temporary service failure"
    assert "503" in lol["observed_response"]

    fi = [r for r in rows if "ADSB.fi" in r["provider"]][0]
    assert fi["access_classification"] == "HTTP error or temporary service failure"
    assert "400" in fi["observed_response"]

def test_v2_17_1_integrity_verification_json():
    json_path = "reports/v2_17_1_integrity_verification.json"
    assert os.path.exists(json_path)
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["integrity_status"] == "ALL_HASHES_MATCH_VERIFIED"
    for name, asset in data["protected_assets"].items():
        assert asset["matches"] is True, f"Asset {name} hash did not match expected"
        assert asset["actual_sha256"] == asset["expected_sha256"]

    adsb_audit = data["adsb_observations_audit"]
    assert adsb_audit["total_staged_observations"] == 16
    assert adsb_audit["unique_aircraft"] == 9
    assert adsb_audit["dam_movements_promoted"] == 0
    assert adsb_audit["confirmed_physical_movements"] == 0
    assert adsb_audit["classifications"]["overflight_observation"] == 15
    assert adsb_audit["classifications"]["regional_observation"] == 1

def test_v2_17_1_final_audit_doc():
    doc_path = "docs/V2_17_1_FINAL_AUDIT.md"
    assert os.path.exists(doc_path)
    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "ACCEPTED WITH LIMITATIONS" in content
    assert "snap_wayback_20260709234230" in content
    assert "authentication required" in content.lower()
    assert "Hypothesis (Unverified)" in content
    assert "Zero (0)" in content or "0" in content

def test_v2_17_1_production_db_immutability():
    current_hash = get_sha256(PROD_DB)
    assert current_hash == EXPECTED_PROD_HASH, f"Production database modified: {current_hash}"
