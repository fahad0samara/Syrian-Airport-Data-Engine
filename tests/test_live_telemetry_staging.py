"""
Syrian Airport Data Engine — Version 2.8
Unit and Integration Tests for Isolated Live Aviation Telemetry Staging

Verifies:
1. Strict database isolation (data/live_telemetry_staging.db vs data/damascus_airport.db).
2. Staging schema creation (collection_runs, raw_api_responses, aircraft_observations, provider_health).
3. Raw API response hashing (SHA-256 lossless storage).
4. Non-destructive deduplication (is_duplicate = 1, duplicate_of_id preserved, zero row deletion).
5. Trajectory classification rules (ground_observation, overflight_observed, approach_candidate, departure_candidate, insufficient_evidence).
6. Coordinate and 24-bit Mode-S hex validation.
7. Unit distance and bounding box calculations.
8. Readsb (ADS-B.lol / ADSB.fi) and OpenSky payload parsers.
9. Provider health matrix updating.
10. Markdown report generation from staging database.
"""

import os
import json
import math
import hashlib
import sqlite3
import pytest
from datetime import datetime, timezone

from scripts.live_aviation_collector import (
    OSDI_LAT,
    OSDI_LON,
    haversine_km,
    get_bounding_box,
    is_valid_hex,
    classify_observation,
    StagingDatabase,
    LiveAviationCollector,
    generate_v2_8_report,
)


@pytest.fixture
def temp_staging_db(tmp_path):
    """Fixture providing a temporary, isolated staging SQLite database."""
    db_file = str(tmp_path / "test_live_telemetry_staging.db")
    staging_db = StagingDatabase(db_file)
    return staging_db


class TestStagingSchemaAndIsolation:
    """Tests schema setup, foreign keys, and absolute isolation from production."""

    def test_schema_tables_and_indexes(self, temp_staging_db):
        with temp_staging_db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cur.fetchall()}
            assert "collection_runs" in tables
            assert "raw_api_responses" in tables
            assert "aircraft_observations" in tables
            assert "provider_health" in tables

            cur.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = {row[0] for row in cur.fetchall()}
            assert "idx_obs_icao24_time" in indexes
            assert "idx_obs_provider_time" in indexes
            assert "idx_obs_distance" in indexes

    def test_foreign_key_enforcement(self, temp_staging_db):
        with temp_staging_db.get_connection() as conn:
            cur = conn.cursor()
            # Inserting observation referencing non-existent raw_response_id must fail
            with pytest.raises(sqlite3.IntegrityError):
                cur.execute("""
                    INSERT INTO aircraft_observations (
                        provider, icao24, raw_response_id, classification,
                        observed_at_utc, collected_at_utc
                    ) VALUES ('adsb_fi', '400a1b', 99999, 'overflight_observed',
                              '2026-10-11T12:00:00Z', '2026-10-11T12:00:01Z')
                """)

    def test_production_db_isolation(self, temp_staging_db):
        """Ensure staging database path is isolated and does not touch production DB."""
        assert "damascus_airport.db" not in temp_staging_db.db_path
        assert os.path.exists(temp_staging_db.db_path)


class TestTelemetryValidationAndCalculations:
    """Tests geometry, coordinate validation, and Mode-S hex checks."""

    def test_hex_validation(self):
        assert is_valid_hex("400a1b") is True
        assert is_valid_hex("A0B1C2") is True
        assert is_valid_hex("123456") is True
        assert is_valid_hex("400A1B") is True
        # Invalid cases
        assert is_valid_hex("400A1") is False       # 5 chars
        assert is_valid_hex("400A1B2") is False     # 7 chars
        assert is_valid_hex("400G1B") is False      # Non-hex character
        assert is_valid_hex("") is False
        assert is_valid_hex(None) is False
        assert is_valid_hex(123456) is False

    def test_haversine_distance(self):
        # Distance to self is 0
        assert haversine_km(OSDI_LAT, OSDI_LON, OSDI_LAT, OSDI_LON) == 0.0
        # Distance between OSDI and Beirut Airport (OLBA: 33.8209, 35.4884) ~115 km
        d_olba = haversine_km(OSDI_LAT, OSDI_LON, 33.8209, 35.4884)
        assert 100.0 < d_olba < 130.0

    def test_bounding_box(self):
        bbox = get_bounding_box(OSDI_LAT, OSDI_LON, 150.0)
        assert bbox["lamin"] < OSDI_LAT < bbox["lamax"]
        assert bbox["lomin"] < OSDI_LON < bbox["lomax"]
        # Latitude range: 150 km / 111 km/deg ~ 1.35 deg
        assert abs(bbox["lamax"] - OSDI_LAT - 1.35) < 0.05
        assert abs(OSDI_LAT - bbox["lamin"] - 1.35) < 0.05


class TestTrajectoryClassification:
    """Tests V2.8 trajectory classification logic."""

    def test_ground_observation(self):
        # Explicit on-ground flag
        assert classify_observation(alt_baro=2050, alt_geom=2050, gs=10, vr=0, dist=1.2, onground=True) == "ground_observation"
        # Ground criteria near airport: dist <= 5km, alt <= 2200ft, low speed
        assert classify_observation(alt_baro=2100, alt_geom=2100, gs=50, vr=0, dist=3.0, onground=False) == "ground_observation"

    def test_overflight_observed(self):
        # High altitude >= 15000 ft
        assert classify_observation(alt_baro=36000, alt_geom=36000, gs=480, vr=0, dist=110, onground=False) == "overflight_observed"
        # Mid-altitude transit
        assert classify_observation(alt_baro=18000, alt_geom=18000, gs=350, vr=100, dist=60, onground=False) == "overflight_observed"

    def test_approach_candidate(self):
        # Near airport (<=30km), below 10,000 ft, descending (vr < -300)
        assert classify_observation(alt_baro=5000, alt_geom=5000, gs=180, vr=-800, dist=22, onground=False) == "approach_candidate"

    def test_departure_candidate(self):
        # Near airport (<=25km), below 10,000 ft, climbing (vr > 500)
        assert classify_observation(alt_baro=4000, alt_geom=4000, gs=210, vr=1200, dist=15, onground=False) == "departure_candidate"

    def test_insufficient_evidence(self):
        # Missing altitude
        assert classify_observation(alt_baro=None, alt_geom=None, gs=200, vr=0, dist=20, onground=False) == "insufficient_evidence"
        # Missing distance
        assert classify_observation(alt_baro=10000, alt_geom=10000, gs=200, vr=0, dist=None, onground=False) == "insufficient_evidence"


class TestLosslessEvidenceAndDeduplication:
    """Tests raw response SHA-256 hashing and non-destructive deduplication."""

    def test_raw_response_hashing(self, temp_staging_db):
        collector = LiveAviationCollector(db_path=temp_staging_db.db_path)
        with temp_staging_db.get_connection() as conn:
            conn.execute("INSERT INTO collection_runs (run_id, provider, started_at) VALUES ('TEST_RUN_1', 'adsb_fi', '2026-10-11T12:00:00Z')")
            conn.commit()

        raw_payload = json.dumps({"now": 1728648000, "ac": []})
        raw_bytes = raw_payload.encode("utf-8")
        expected_hash = hashlib.sha256(raw_bytes).hexdigest()

        mock_res = {
            "status": 200,
            "body_str": raw_payload,
            "body_bytes": raw_bytes,
            "t_req": "2026-10-11T12:00:00Z",
            "t_resp": "2026-10-11T12:00:01Z",
            "elapsed": 0.45,
            "error": None,
        }

        collector._process_readsb_response("adsb_fi", "https://mock.adsb.fi/api", mock_res, "TEST_RUN_1")

        with temp_staging_db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM raw_api_responses WHERE response_id = 1")
            row = cur.fetchone()
            assert row is not None
            assert row["provider"] == "adsb_fi"
            assert row["http_status"] == 200
            assert row["response_hash"] == expected_hash
            assert row["raw_response"] == raw_payload

    def test_non_destructive_deduplication(self, temp_staging_db):
        collector = LiveAviationCollector(db_path=temp_staging_db.db_path)
        with temp_staging_db.get_connection() as conn:
            conn.execute("INSERT INTO collection_runs (run_id, provider, started_at) VALUES ('TEST_RUN_1', 'adsb_fi', '2026-10-11T12:00:00Z')")
            conn.commit()

        ac_data = [{
            "hex": "76aa81",
            "flight": "SYR101",
            "r": "YK-AKB",
            "lat": 33.45,
            "lon": 36.55,
            "alt_baro": 33000,
            "alt_geom": 33200,
            "gs": 450,
            "track": 180,
            "baro_rate": 0,
        }]

        payload_1 = json.dumps({"now": 1728648000, "ac": ac_data})
        res_1 = {
            "status": 200,
            "body_str": payload_1,
            "body_bytes": payload_1.encode("utf-8"),
            "t_req": "2026-10-11T12:00:00Z",
            "t_resp": "2026-10-11T12:00:01Z",
            "elapsed": 0.3,
            "error": None,
        }

        # Polling cycle 1
        collector._process_readsb_response("adsb_fi", "https://mock.adsb.fi/api", res_1, "TEST_RUN_1")

        # Polling cycle 2 (15 seconds later with same aircraft)
        payload_2 = json.dumps({"now": 1728648015, "ac": ac_data})
        res_2 = {
            "status": 200,
            "body_str": payload_2,
            "body_bytes": payload_2.encode("utf-8"),
            "t_req": "2026-10-11T12:00:15Z",
            "t_resp": "2026-10-11T12:00:16Z",
            "elapsed": 0.3,
            "error": None,
        }
        collector._process_readsb_response("adsb_fi", "https://mock.adsb.fi/api", res_2, "TEST_RUN_1")

        with temp_staging_db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT observation_id, provider, icao24, is_duplicate, duplicate_of_id FROM aircraft_observations ORDER BY observation_id ASC")
            rows = cur.fetchall()
            assert len(rows) == 2, "Both rows must be preserved in the staging database"
            
            # Row 1 is canonical
            assert rows[0]["is_duplicate"] == 0
            assert rows[0]["duplicate_of_id"] is None
            
            # Row 2 is flagged as duplicate without deletion
            assert rows[1]["is_duplicate"] == 1
            assert rows[1]["duplicate_of_id"] == rows[0]["observation_id"]


class TestPayloadParsers:
    """Tests readsb and opensky payload parsers including millisecond epoch handling."""

    def test_readsb_millisecond_timestamp_parsing(self, temp_staging_db):
        collector = LiveAviationCollector(db_path=temp_staging_db.db_path)
        with temp_staging_db.get_connection() as conn:
            conn.execute("INSERT INTO collection_runs (run_id, provider, started_at) VALUES ('RUN_MS', 'adsb_lol', '2026-10-11T12:00:00Z')")
            conn.commit()

        # ADS-B.lol returns 13-digit millisecond epoch timestamps
        ms_epoch = 1728648000000  # 2024-10-11T12:00:00Z
        payload = json.dumps({
            "now": ms_epoch,
            "ac": [{
                "hex": "400a1b",
                "flight": "BAW123",
                "lat": 33.6,
                "lon": 36.8,
                "alt_baro": 37000,
            }]
        })
        res = {
            "status": 200,
            "body_str": payload,
            "body_bytes": payload.encode("utf-8"),
            "t_req": "2026-10-11T12:00:00Z",
            "t_resp": "2026-10-11T12:00:01Z",
            "elapsed": 0.35,
            "error": None,
        }
        out = collector._process_readsb_response("adsb_lol", "https://api.adsb.lol/v2/point/33/36/81", res, "RUN_MS")
        assert out["obs_count"] == 1

        with temp_staging_db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM aircraft_observations WHERE provider = 'adsb_lol'")
            row = cur.fetchone()
            assert row["icao24"] == "400a1b"
            assert row["callsign"] == "BAW123"
            assert "2024-10-11" in row["observed_at_utc"]

    def test_opensky_vector_parsing(self, temp_staging_db):
        collector = LiveAviationCollector(db_path=temp_staging_db.db_path)
        with temp_staging_db.get_connection() as conn:
            conn.execute("INSERT INTO collection_runs (run_id, provider, started_at) VALUES ('RUN_OS', 'opensky', '2026-10-11T12:00:00Z')")
            conn.commit()

        # OpenSky returns state vectors with metric units
        server_epoch = 1728648000
        states = [
            [
                "484555",       # 0: icao24
                "KLM432 ",      # 1: callsign
                "Netherlands",  # 2: origin_country
                1728647990,     # 3: time_position
                1728647995,     # 4: last_contact
                36.70,          # 5: longitude
                33.50,          # 6: latitude
                10668.0,        # 7: baro_altitude (m) -> ~35,000 ft
                False,          # 8: on_ground
                240.0,          # 9: velocity (m/s) -> ~466 kts
                120.5,          # 10: true_track
                -2.5,           # 11: vertical_rate (m/s) -> ~-492 fpm
                None,           # 12: sensors
                10800.0,        # 13: geo_altitude (m)
                "1000",         # 14: squawk
                False,          # 15: spi
                0,              # 16: position_source
            ]
        ]
        payload = json.dumps({"time": server_epoch, "states": states})
        res = {
            "status": 200,
            "body_str": payload,
            "body_bytes": payload.encode("utf-8"),
            "t_req": "2026-10-11T12:00:00Z",
            "t_resp": "2026-10-11T12:00:01Z",
            "elapsed": 0.5,
            "error": None,
        }
        out = collector._process_opensky_response("opensky", "https://opensky-network.org/api/states/all", res, "RUN_OS")
        assert out["obs_count"] == 1

        with temp_staging_db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM aircraft_observations WHERE provider = 'opensky'")
            row = cur.fetchone()
            assert row["icao24"] == "484555"
            assert row["callsign"] == "KLM432"
            # Converted altitude: 10668 * 3.28084 ~ 35000 ft
            assert abs(row["altitude_baro"] - 35000) < 50
            # Converted groundspeed: 240 * 1.94384 ~ 466.5 kts
            assert abs(row["groundspeed"] - 466.5) < 5
            assert row["classification"] == "overflight_observed"


class TestProviderHealthAndReport:
    """Tests provider health tracking transitions and report generation."""

    def test_provider_health_transitions(self, temp_staging_db):
        collector = LiveAviationCollector(db_path=temp_staging_db.db_path)
        with temp_staging_db.get_connection() as conn:
            # 1. Success -> healthy
            collector.update_health(conn, "adsb_fi", 200, 0.45, None)
            conn.commit()

            cur = conn.cursor()
            cur.execute("SELECT * FROM provider_health WHERE provider = 'adsb_fi'")
            row = cur.fetchone()
            assert row["current_status"] == "healthy"
            assert row["consecutive_failures"] == 0
            assert row["last_http_status"] == 200

            # 2. Failure -> degraded
            collector.update_health(conn, "adsb_fi", 503, 0.1, "HTTP 503: Service Unavailable")
            conn.commit()
            cur.execute("SELECT * FROM provider_health WHERE provider = 'adsb_fi'")
            row = cur.fetchone()
            assert row["current_status"] == "degraded"
            assert row["consecutive_failures"] == 1

            # 3. Two more failures -> failing (>= 3 consecutive failures)
            collector.update_health(conn, "adsb_fi", 503, 0.1, "HTTP 503")
            collector.update_health(conn, "adsb_fi", 503, 0.1, "HTTP 503")
            conn.commit()
            cur.execute("SELECT * FROM provider_health WHERE provider = 'adsb_fi'")
            row = cur.fetchone()
            assert row["current_status"] == "failing"
            assert row["consecutive_failures"] == 3

    def test_report_generation(self, temp_staging_db, tmp_path):
        report_out = str(tmp_path / "TEST_REPORT.md")
        collector = LiveAviationCollector(db_path=temp_staging_db.db_path)

        # Populate a sample run
        with temp_staging_db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO collection_runs (run_id, provider, started_at) VALUES ('R1', 'multi', '2026-10-11T10:00:00Z')")
            collector.update_health(conn, "adsb_fi", 200, 0.25, None)
            conn.commit()

        # Generate report
        generate_v2_8_report(db_path=temp_staging_db.db_path, report_out=report_out)
        assert os.path.exists(report_out)

        with open(report_out, "r", encoding="utf-8") as f:
            content = f.read()

        assert "Live Aviation Telemetry Collection Prototype Report" in content
        assert "Damascus International Airport" in content
        assert "CONDITIONAL GO" in content
        assert "Provider Health & Reliability Matrix" in content
