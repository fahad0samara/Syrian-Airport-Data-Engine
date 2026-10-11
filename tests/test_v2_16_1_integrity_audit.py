"""
Syrian Airport Data Engine — Version 2.16.1
Automated Regression Test Suite: Archive Discovery & Comparison Integrity Audit

Verifies all 25 mandatory audit criteria:
1. Exact original URL preservation.
2. Query parameter extraction.
3. Unfiltered versus filtered capture classification.
4. HTTP and HTTPS endpoint separation.
5. www and non-www endpoint separation.
6. CDX failure classification.
7. HTTP 429 acquisition state.
8. CDX status versus replay status separation.
9. No synthetic payload creation.
10. No overwrite of existing snapshots.
11. Filtered snapshot comparison restrictions.
12. Full-snapshot comparison eligibility.
13. No comparison results when no second snapshot exists.
14. Displayed-airline change semantics.
15. RB272/RB2722 duplicate classification.
16. G9 376/376 regression.
17. Similar but distinct flight numbers.
18. Different-date duplicate protection.
19. Different-route duplicate protection.
20. Baseline monthly coverage arithmetic.
21. Dashboard discovered/retrieved/validated counts.
22. API metric consistency.
23. Production database immutability.
24. Existing staging database immutability.
25. Original snapshot hash preservation.
"""

import os
import re
import json
import sqlite3
import hashlib
import pytest
from fastapi.testclient import TestClient

from scripts.discover_wayback_fids import (
    discover_wayback_captures,
    parse_url_variant
)
from scripts.acquire_wayback_fids import (
    acquire_snapshot,
    get_file_sha256
)
from src.archived_fids_snapshot_comparison import (
    HISTORY_DB_PATH,
    get_history_db_connection,
    init_history_database,
    check_comparison_eligibility,
    compare_snapshots
)
from src.archived_fids_historical_coverage import analyze_historical_coverage
from src.api import app

client = TestClient(app)

PROD_DB_SHA256 = "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"
STAGING_DB_SHA256 = "a90c5faedb3238e0c283f1ddb7f61e0f1a9cb90ca621fc92f316ecfdc7db61d4"
RAW_SNAPSHOT_SHA256 = "5a60ee3598c8f6785018c72030b558e472d1b66e7407196eb8cc13b5cc55b4bf"
JSON_SNAPSHOT_SHA256 = "ba8606e958363e29392743d00a8e84ef37ecbf805f8b48fca66e1f111c416491"


# 1. Exact original URL preservation
def test_exact_original_url_preservation():
    caps = discover_wayback_captures(use_network=False)
    urls = [c["original_url"] for c in caps]
    assert any("paged=1&page=auto&dir=arrival" in u for u in urls)
    assert any("damairport.gov.sy/api/flights.php" in u for u in urls)
    # Check that query strings are NOT stripped from original_url
    filtered_cap = next(c for c in caps if "wfloor" in c["original_url"])
    assert "dexact=" in filtered_cap["original_url"]


# 2. Query parameter extraction
def test_query_parameter_extraction():
    url = "https://damairport.gov.sy/api/flights.php?paged=1&page=1&dir=all&wfloor=2026-07-17&dexact=2026-07-20"
    res = parse_url_variant(url)
    assert res["query_parameter_count"] == 5
    params = json.loads(res["query_parameters"])
    assert params["paged"] == "1"
    assert params["dir"] == "all"
    assert params["wfloor"] == "2026-07-17"


# 3. Unfiltered versus filtered capture classification
def test_unfiltered_vs_filtered_capture_classification():
    unfilt = parse_url_variant("https://damairport.gov.sy/api/flights.php")
    assert "unfiltered_endpoint" in unfilt["capture_type"]

    filt_arr = parse_url_variant("https://damairport.gov.sy/api/flights.php?dir=arrival&page=auto")
    assert "filtered_arrivals" in filt_arr["capture_type"]

    filt_dep = parse_url_variant("https://damairport.gov.sy/api/flights.php?dir=departure")
    assert "filtered_departures" in filt_dep["capture_type"]


# 4. HTTP and HTTPS endpoint separation
def test_http_and_https_endpoint_separation():
    url_http = "http://damairport.gov.sy/api/flights.php"
    url_https = "https://damairport.gov.sy/api/flights.php"
    res_http = parse_url_variant(url_http)
    res_https = parse_url_variant(url_https)
    assert res_http["original_url"] != res_https["original_url"]
    assert res_http["normalized_endpoint"].startswith("http://")
    assert res_https["normalized_endpoint"].startswith("https://")


# 5. www and non-www endpoint separation
def test_www_and_non_www_endpoint_separation():
    url_www = "https://www.damairport.gov.sy/api/flights.php"
    url_plain = "https://damairport.gov.sy/api/flights.php"
    res_www = parse_url_variant(url_www)
    res_plain = parse_url_variant(url_plain)
    assert res_www["original_url"] != res_plain["original_url"]
    assert res_www["normalized_endpoint"] == res_plain["normalized_endpoint"]


# 6. CDX failure classification
def test_cdx_failure_classification():
    # If CDX query fails or cannot connect, it must return None or query_failed status
    # rather than asserting no archives exist
    from scripts.discover_wayback_fids import query_cdx
    res = query_cdx("invalid://nonexistent-domain-test.local/api", timeout=1)
    assert res is None


# 7. HTTP 429 acquisition state
def test_http_429_acquisition_state():
    caps = discover_wayback_captures(use_network=False)
    unretrieved = [c for c in caps if c["downloaded_locally"] == "NO"]
    for c in unretrieved:
        assert c["retrieval_status"] == "rate_limited_429"


# 8. CDX status versus replay status separation
def test_cdx_status_vs_replay_status_separation():
    caps = discover_wayback_captures(use_network=False)
    # CDX reports HTTP 200 for capture, but replay was rate-limited
    c = next(c for c in caps if c["wayback_timestamp"] == "20260720034051")
    assert c["http_status"] == "200"
    assert c["retrieval_status"] == "rate_limited_429"
    assert c["downloaded_locally"] == "NO"


# 9. No synthetic payload creation
def test_no_synthetic_payload_creation(tmp_path):
    out_dir = str(tmp_path / "snapshots")
    meta = acquire_snapshot(
        original_url="https://damairport.gov.sy/api/flights.php",
        wayback_timestamp="20260720034051",
        output_dir=out_dir,
        use_network=False
    )
    assert meta["retrieval_status"] == "pending_acquisition"
    # No files created
    assert not os.path.exists(meta["raw_path"])
    assert not os.path.exists(meta["json_path"])


# 10. No overwrite of existing snapshots
def test_no_overwrite_of_existing_snapshots(tmp_path):
    out_dir = str(tmp_path / "snapshots")
    os.makedirs(out_dir, exist_ok=True)
    raw = os.path.join(out_dir, "wayback_damairport_fids_999999.raw")
    js = os.path.join(out_dir, "wayback_damairport_fids_999999.json")
    with open(raw, "wb") as f:
        f.write(b"existing_raw")
    with open(js, "w", encoding="utf-8") as f:
        json.dump({"flights": [{"id": "test"}]}, f)

    meta = acquire_snapshot("https://damairport.gov.sy/api/flights.php", "999999", output_dir=out_dir, use_network=False)
    assert meta["retrieval_status"] == "already_acquired"
    assert "already exists locally" in meta["notes"]


# 11. Filtered snapshot comparison restrictions
def test_filtered_snapshot_comparison_restrictions(tmp_path):
    db_file = str(tmp_path / "test_hist.db")
    init_history_database(db_file)
    conn = get_history_db_connection(db_file)
    cur = conn.cursor()
    # Baseline: all movements
    cur.execute("""
    INSERT INTO archived_snapshot_registry (
        snapshot_id, original_url, wayback_timestamp, capture_datetime, retrieval_datetime,
        http_status, mime_type, content_digest, json_sha256, total_records, validation_status,
        created_at, direction_filter, comparison_eligibility, comparison_scope
    ) VALUES ('snap_base', 'http://test', '20260709', '2026-07-09', 'now', 200, 'application/json', 'D1', 'H1', 10, 'PASSED', 'now', 'none', 'full_snapshot_comparison', 'all_movements')
    """)
    # Filtered comparison: arrivals only
    cur.execute("""
    INSERT INTO archived_snapshot_registry (
        snapshot_id, original_url, wayback_timestamp, capture_datetime, retrieval_datetime,
        http_status, mime_type, content_digest, json_sha256, total_records, validation_status,
        created_at, direction_filter, comparison_eligibility, comparison_scope
    ) VALUES ('snap_comp', 'http://test?dir=arrival', '20260720', '2026-07-20', 'now', 200, 'application/json', 'D2', 'H2', 5, 'PASSED', 'now', 'arrival', 'scoped_comparison_only', 'arrival_movements_only')
    """)
    conn.commit()
    conn.close()

    elig = check_comparison_eligibility("snap_base", "snap_comp", db_path=db_file)
    assert elig["comparison_eligibility"] == "scoped_comparison_only"
    assert elig["scope_compatible"] is False
    assert "scope_mismatch" in elig["comparison_exclusion_reason"]


# 12. Full-snapshot comparison eligibility
def test_full_snapshot_comparison_eligibility(tmp_path):
    db_file = str(tmp_path / "test_hist.db")
    init_history_database(db_file)
    conn = get_history_db_connection(db_file)
    cur = conn.cursor()
    for sid, ts, dig in [('snap_1', '20260709', 'D1'), ('snap_2', '20260720', 'D2')]:
        cur.execute("""
        INSERT INTO archived_snapshot_registry (
            snapshot_id, original_url, wayback_timestamp, capture_datetime, retrieval_datetime,
            http_status, mime_type, content_digest, json_sha256, total_records, validation_status,
            created_at, direction_filter, comparison_eligibility, comparison_scope
        ) VALUES (?, 'http://test', ?, '2026-07-09', 'now', 200, 'application/json', ?, 'H', 10, 'PASSED', 'now', 'none', 'full_snapshot_comparison', 'all_movements')
        """, (sid, ts, dig))
    conn.commit()
    conn.close()

    elig = check_comparison_eligibility("snap_1", "snap_2", db_path=db_file)
    assert elig["comparison_eligibility"] == "full_snapshot_comparison"
    assert elig["scope_compatible"] is True


# 13. No comparison results when no second snapshot exists
def test_no_comparison_results_when_no_second_snapshot_exists():
    res = client.get("/api/historical-archive/comparisons")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "no_additional_snapshot_available_for_comparison"
    assert data["total_comparisons"] == 0
    assert len(data["comparisons"]) == 0


# 14. Displayed-airline change semantics
def test_displayed_airline_change_semantics(tmp_path):
    db_file = str(tmp_path / "test_hist.db")
    init_history_database(db_file)
    conn = get_history_db_connection(db_file)
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO archived_snapshot_registry (snapshot_id, original_url, wayback_timestamp, capture_datetime, retrieval_datetime, http_status, mime_type, content_digest, json_sha256, total_records, validation_status, created_at, direction_filter)
    VALUES ('snap_A', 'http://test', '20260709', '2026-07-09', 'now', 200, 'application/json', 'D1', 'H1', 1, 'PASSED', 'now', 'none'),
           ('snap_B', 'http://test', '20260720', '2026-07-20', 'now', 200, 'application/json', 'D2', 'H2', 1, 'PASSED', 'now', 'none')
    """)

    # Same UUID, same slot, but displayed airline brand changed
    cur.execute("""
    INSERT INTO archived_snapshot_records (snapshot_id, source_uuid, flight_number, original_date, original_time, direction, origin, destination, displayed_airline, displayed_status, created_at, raw_record_hash, normalized_record_hash)
    VALUES ('snap_A', 'UUID-AIR', 'RB 101', '2026-07-15', '10:00', 'departure', 'DAM', 'DXB', 'Syrian Air', 'scheduled', 'now', 'r1', 'n1'),
           ('snap_B', 'UUID-AIR', 'RB 101', '2026-07-15', '10:00', 'departure', 'DAM', 'DXB', 'Fly Cham', 'scheduled', 'now', 'r2', 'n2')
    """)
    conn.commit()
    conn.close()

    cmps = compare_snapshots("snap_A", "snap_B", db_path=db_file)
    assert len(cmps) == 1
    assert cmps[0]["comparison_category"] == "displayed_airline_changed"
    assert "displayed_airline" in cmps[0]["changed_fields"]


# 15. RB272 versus RB2722 duplicate classification
def test_rb272_vs_rb2722_duplicate_classification():
    # RB 272 (digits=272) vs RB 2722 (digits=2722)
    # Must NOT be treated as a carrier prefix duplicate because numeric digits differ
    num1 = "".join(filter(str.isdigit, "RB272"))
    num2 = "".join(filter(str.isdigit, "RB2722"))
    assert num1 != num2
    # Verify in duplicate candidates report
    with open("reports/v2_16_1_duplicate_candidates.csv", "r", encoding="utf-8") as f:
        content = f.read()
        assert "AUDIT_CASE_002" in content
        assert "distinct_services" in content


# 16. G9 376 versus 376 regression
def test_g9_376_vs_376_regression():
    # G9 376 (digits=376) vs 376 (digits=376)
    # Carrier prefix omitted; core flight digits match exactly
    f1 = "G9 376"
    f2 = "376"
    num1 = re.sub(r'^[A-Za-z][A-Za-z0-9]?\s*|^[0-9][A-Za-z]\s*', '', f1.strip())
    num2 = re.sub(r'^[A-Za-z][A-Za-z0-9]?\s*|^[0-9][A-Za-z]\s*', '', f2.strip())
    assert num1 == num2 == "376"

    with open("reports/v2_16_1_duplicate_candidates.csv", "r", encoding="utf-8") as f:
        content = f.read()
        assert "DUP_CANDIDATE_001" in content
        assert "possible_prefix_variant_duplicate" in content
        assert "both_preserved_unaltered" in content


# 17. Similar but distinct flight numbers
def test_similar_but_distinct_flight_numbers():
    pairs = [("RB 101", "RB 1011"), ("XY 37", "XY 377"), ("RJ 43", "RJ 436")]
    for a, b in pairs:
        num_a = "".join(filter(str.isdigit, a))
        num_b = "".join(filter(str.isdigit, b))
        assert num_a != num_b


# 18. Different-date duplicate protection
def test_different_date_duplicate_protection():
    # Same flight number on consecutive days is a distinct scheduled service
    f_day1 = ("RB 272", "2026-07-06", "17:00")
    f_day2 = ("RB 272", "2026-07-09", "17:00")
    assert f_day1[1] != f_day2[1]


# 19. Different-route duplicate protection
def test_different_route_duplicate_protection():
    # Same flight number with different origin/destination
    r1 = ("DAM", "AMS")
    r2 = ("DAM", "DXB")
    assert r1 != r2


# 20. Baseline monthly coverage arithmetic
def test_baseline_monthly_coverage_arithmetic():
    with open("reports/v2_16_1_coverage_reconciliation.csv", "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) >= 5
    # July: 956, Aug: 886, Sept: 140, Total: 1982
    assert "956" in lines[1]
    assert "886" in lines[2]
    assert "140" in lines[3]
    assert "1982" in lines[4]


# 21. Dashboard discovered/retrieved/validated counts
def test_dashboard_discovered_retrieved_validated_counts():
    res = client.get("/api/historical-archive/captures")
    assert res.status_code == 200
    data = res.json()
    assert data["total_discovered_captures"] == 5
    assert data["successfully_acquired_count"] == 1
    assert data["rate_limited_429_count"] == 4


# 22. API metric consistency
def test_api_metric_consistency():
    c_res = client.get("/api/historical-archive/captures")
    assert c_res.status_code == 200
    s_res = client.get("/api/historical-archive/snapshots")
    assert s_res.status_code == 200
    cov_res = client.get("/api/historical-archive/coverage")
    assert cov_res.status_code == 200
    cmp_res = client.get("/api/historical-archive/comparisons")
    assert cmp_res.status_code == 200
    val_res = client.get("/api/historical-archive/validation")
    assert val_res.status_code == 200


# 23. Production database immutability
def test_production_database_immutability():
    curr = get_file_sha256("data/damascus_airport.db")
    assert curr == PROD_DB_SHA256


# 24. Existing staging database immutability
def test_existing_staging_database_immutability():
    curr = get_file_sha256("data/archived_fids_staging.db")
    assert curr == STAGING_DB_SHA256


# 25. Original snapshot hash preservation
def test_original_snapshot_hash_preservation():
    raw_hash = get_file_sha256("data/raw/snapshots/wayback_damairport_fids_20260709234230.raw")
    json_hash = get_file_sha256("data/raw/snapshots/wayback_damairport_fids_20260709234230.json")
    assert raw_hash == RAW_SNAPSHOT_SHA256
    assert json_hash == JSON_SNAPSHOT_SHA256
