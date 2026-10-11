"""
Test Suite: Provider-Level Evidence Independence & Provenance (Reconciled & Hardened)
Syrian Airport Data Engine — Version 2.1
"""

import sqlite3
import pytest
from pathlib import Path
from src.provider_independence import (
    resolve_provider_from_provenance,
    detect_telemetry_duplicates,
    evaluate_event_provider_independence,
    audit_production_database,
    ProvenanceRecord
)


@pytest.fixture
def isolated_db(tmp_path):
    """Creates an isolated database with the v2.1 schema for testing."""
    db_file = tmp_path / "test_provider_indep.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE airports (
            airport_id TEXT PRIMARY KEY,
            iata_code TEXT,
            icao_code TEXT,
            name TEXT
        );
    """)
    c.execute("INSERT INTO airports VALUES ('DAM', 'DAM', 'OSDI', 'Damascus International Airport');")

    c.execute("""
        CREATE TABLE flight_events (
            event_id TEXT PRIMARY KEY,
            flight_number TEXT NOT NULL,
            airport_id TEXT NOT NULL,
            movement_type TEXT NOT NULL,
            flight_date TEXT NOT NULL,
            scheduled_dep_time TEXT,
            actual_dep_time TEXT,
            estimated_dep_time TEXT,
            scheduled_arr_time TEXT,
            actual_arr_time TEXT,
            estimated_arr_time TEXT,
            record_nature TEXT NOT NULL,
            operating_flight_number TEXT,
            quality_flags TEXT
        );
    """)

    c.execute("""
        CREATE TABLE event_evidence (
            evidence_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL REFERENCES flight_events(event_id),
            source_name TEXT NOT NULL,
            source_record_id TEXT,
            evidence_type TEXT NOT NULL,
            observed_value TEXT NOT NULL,
            raw_timestamp TEXT,
            observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            snapshot_path TEXT,
            snapshot_sha256 TEXT
        );
    """)

    c.execute("""
        CREATE TABLE evidence_retractions (
            sequence_num INTEGER PRIMARY KEY AUTOINCREMENT,
            retraction_id TEXT UNIQUE NOT NULL,
            evidence_id TEXT NOT NULL REFERENCES event_evidence(evidence_id) ON DELETE RESTRICT,
            action TEXT NOT NULL CHECK(action IN ('retract', 'unretract')),
            reason TEXT NOT NULL,
            actor TEXT NOT NULL,
            run_id TEXT NOT NULL,
            observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            snapshot_path TEXT,
            snapshot_sha256 TEXT,
            UNIQUE(evidence_id, action, run_id)
        );
    """)

    c.execute("""
        CREATE VIEW v_active_evidence AS
        SELECT ee.*
        FROM event_evidence ee
        WHERE NOT EXISTS (
            SELECT 1
            FROM (
                SELECT evidence_id, action,
                       ROW_NUMBER() OVER (PARTITION BY evidence_id ORDER BY sequence_num DESC) as rn
                FROM evidence_retractions
            ) r
            WHERE r.evidence_id = ee.evidence_id
              AND r.rn = 1
              AND r.action = 'retract'
        );
    """)

    conn.commit()
    conn.close()
    return db_file


def test_evidence_count_reconciliation(isolated_db):
    """1. Total physical evidence must mathematically reconcile across physical movements and non-physical classifications."""
    conn = sqlite3.connect(str(isolated_db))
    cur = conn.cursor()

    # Seed events with various record natures
    cur.execute("""
        INSERT INTO flight_events (event_id, flight_number, airport_id, movement_type, flight_date, record_nature)
        VALUES
        ('ev_phys_1', 'RB101', 'DAM', 'departure', '2026-10-10', 'physical_movement'),
        ('ev_sched_1', 'FZ101', 'DAM', 'arrival', '2026-10-10', 'scheduled_service'),
        ('ev_code_1', 'EK101', 'DAM', 'arrival', '2026-10-10', 'marketing_codeshare'),
        ('ev_unv_1', 'DN101', 'DAM', 'departure', '2026-10-10', 'unverified_movement');
    """)

    # Seed physical evidence rows across all natures
    cur.execute("""
        INSERT INTO event_evidence (evidence_id, event_id, source_name, source_record_id, evidence_type, observed_value, raw_timestamp)
        VALUES
        ('ee_1', 'ev_phys_1', 'flightradar24', 'fr_1', 'adsb_takeoff', '2026-10-10T10:00:00Z', '1791626400'),
        ('ee_2', 'ev_phys_1', 'aviationstack', 'av_1', 'adsb_takeoff', '2026-10-10T10:00:00Z', '2026-10-10T10:00:00+00:00'),
        ('ee_3', 'ev_sched_1', 'flightradar24', 'fr_2', 'adsb_takeoff', '2026-10-10T08:00:00Z', '1791619200'),
        ('ee_4', 'ev_code_1', 'aviationstack', 'av_2', 'commercial_takeoff', '2026-10-10T06:00:00Z', '2026-10-10T06:00:00+00:00'),
        ('ee_5', 'ev_unv_1', 'aviationstack', 'av_3', 'commercial_touchdown', '2026-10-10T04:00:00Z', '2026-10-10T04:00:00+00:00');
    """)
    conn.commit()

    summary = audit_production_database(isolated_db)
    assert summary["total_physical_movements"] == 1
    assert summary["total_physical_evidence_all_events"] == 5
    assert summary["total_physical_evidence_on_physical_movements"] == 2
    assert summary["evidence_by_record_nature"]["physical_movement"] == 2
    assert summary["evidence_by_record_nature"]["scheduled_service"] == 1
    assert summary["evidence_by_record_nature"]["marketing_codeshare"] == 1
    assert summary["evidence_by_record_nature"]["unverified_movement"] == 1
    # Check mathematical sum
    assert sum(summary["evidence_by_record_nature"].values()) == 5
    conn.close()


def test_ambiguous_provider_identity():
    """2. Ambiguous, synthetic, or unverified provider sources must not be inferred as FR24 and must classify as independence_unknown."""
    prov, _ = resolve_provider_from_provenance(
        source_name="synthetic_feed+partner_feed",
        raw_ts="1791595721",  # 10-digit timestamp without verified FR24 lineage
        evidence_type="adsb_takeoff",
        source_record_id="partner_record_99"
    )
    assert prov == "independence_unknown"

    evidence = [{
        "evidence_id": "ee_ambig",
        "event_id": "flt_ambig",
        "source_name": "synthetic_feed+partner_feed",
        "source_record_id": "partner_record_99",
        "evidence_type": "adsb_takeoff",
        "observed_value": "2026-10-10T01:28:41Z",
        "raw_timestamp": "1791595721"
    }]
    res = evaluate_event_provider_independence("flt_ambig", evidence)
    assert res["provider_distinct"] == 0
    assert res["distinct_providers"] == []
    assert res["unknown_provenance_count"] == 1
    assert res["independence_status"] == "independence_unknown"


def test_different_api_providers_with_unknown_shared_upstream_lineage():
    """3. Different API providers (FR24 + Aviationstack) yield provider_distinct=2 but classify as unverified upstream lineage."""
    evidence = [
        {
            "evidence_id": "ev_fr",
            "event_id": "flt_multi",
            "source_name": "flightradar24",
            "source_record_id": "fr24_01",
            "evidence_type": "adsb_takeoff",
            "observed_value": "2026-10-10T01:28:41Z",
            "raw_timestamp": "1791595721"
        },
        {
            "evidence_id": "ev_avs",
            "event_id": "flt_multi",
            "source_name": "aviationstack",
            "source_record_id": "avs_01",
            "evidence_type": "adsb_takeoff",
            "observed_value": "2026-10-10T01:28:00Z",
            "raw_timestamp": "2026-10-10T04:28:00+00:00"
        }
    ]

    res = evaluate_event_provider_independence("flt_multi", evidence)
    assert res["provider_count"] == 2
    assert res["provider_distinct"] == 2
    assert sorted(res["distinct_providers"]) == ["aviationstack", "flightradar24"]
    assert res["independent_observation_count"] == 2
    assert res["duplicate_representations"] == 0
    # Must explicitly state that upstream sensor independence is unverified
    assert res["independence_status"] == "multi_provider_distinct_unverified_upstream"


def test_same_raw_observation_under_different_source_labels():
    """4. Direct FR24 and composite merged record sharing epoch 1791595721 represent 1 unique observation and 1 duplicate."""
    evidence = [
        {
            "evidence_id": "ev_direct",
            "event_id": "flt_dup",
            "source_name": "flightradar24",
            "source_record_id": "fr24_100",
            "evidence_type": "adsb_takeoff",
            "observed_value": "2026-10-10T01:28:41Z",
            "raw_timestamp": "1791595721"
        },
        {
            "evidence_id": "ev_composite",
            "event_id": "flt_dup",
            "source_name": "damairport_official+aviationstack+flightradar24",
            "source_record_id": "uuid-merged",
            "evidence_type": "adsb_takeoff",
            "observed_value": "2026-10-10T01:28:41Z",
            "raw_timestamp": "1791595721"
        }
    ]

    res = evaluate_event_provider_independence("flt_dup", evidence)
    assert res["provider_count"] == 2
    assert res["provider_distinct"] == 1
    assert res["independent_observation_count"] == 1
    assert res["duplicate_representations"] == 1
    assert res["independence_status"] == "single_provider"

    dup_rec = next(r for r in res["records"] if r["evidence_id"] == "ev_composite")
    assert dup_rec["is_duplicate"] is True
    assert dup_rec["duplicate_of"] == "ev_direct"


def test_duplicate_records_across_event_ids():
    """5. The same flight leg re-ingested under two different event IDs is detected as a duplicate representation."""
    leg_context = {
        "flight_number": "RB272",
        "flight_date": "2026-10-10",
        "airport_id": "DAM",
        "movement_type": "departure"
    }

    evidence_across_events = [
        {
            "evidence_id": "ev_ev1",
            "event_id": "event_id_alpha",
            "source_name": "flightradar24",
            "source_record_id": "fr24_5873711767",
            "evidence_type": "adsb_takeoff",
            "observed_value": "2026-10-10T14:30:00Z",
            "raw_timestamp": "1791642600"
        },
        {
            "evidence_id": "ev_ev2",
            "event_id": "event_id_beta",
            "source_name": "flightradar24",
            "source_record_id": "fr24_5873711767",
            "evidence_type": "adsb_takeoff",
            "observed_value": "2026-10-10T14:30:00Z",
            "raw_timestamp": "1791642600"
        }
    ]

    provenance = detect_telemetry_duplicates(evidence_across_events, flight_context=leg_context)
    assert len(provenance) == 2
    assert provenance[0].is_duplicate is False
    assert provenance[1].is_duplicate is True
    assert provenance[1].duplicate_of == "ev_ev1"


def test_same_flight_number_on_different_flight_legs_never_merged():
    """6. Distinct flight legs (e.g. Damascus departure vs Dubai arrival on next day) are strictly protected from merging."""
    leg_1 = {
        "flight_number": "RB272",
        "flight_date": "2026-10-09",
        "airport_id": "DAM",
        "movement_type": "departure"
    }
    leg_2 = {
        "flight_number": "RB272",
        "flight_date": "2026-10-10",
        "airport_id": "DAM",
        "movement_type": "departure"
    }

    # Two separate day departures
    ev1 = [{
        "evidence_id": "ev_leg1",
        "event_id": "event_day1",
        "source_name": "flightradar24",
        "source_record_id": "fr24_day1",
        "evidence_type": "adsb_takeoff",
        "observed_value": "2026-10-09T14:30:00Z",
        "raw_timestamp": "1791556200"
    }]
    ev2 = [{
        "evidence_id": "ev_leg2",
        "event_id": "event_day2",
        "source_name": "flightradar24",
        "source_record_id": "fr24_day2",
        "evidence_type": "adsb_takeoff",
        "observed_value": "2026-10-10T14:30:00Z",
        "raw_timestamp": "1791642600"
    }]

    res1 = evaluate_event_provider_independence("event_day1", ev1, flight_context=leg_1)
    res2 = evaluate_event_provider_independence("event_day2", ev2, flight_context=leg_2)

    assert res1["independent_observation_count"] == 1
    assert res1["duplicate_representations"] == 0
    assert res2["independent_observation_count"] == 1
    assert res2["duplicate_representations"] == 0


def test_missing_snapshots_with_valid_source_record_ids():
    """7. Missing raw snapshot file or null snapshot paths are handled gracefully without losing provenance."""
    evidence = [
        {
            "evidence_id": "ev_no_snap",
            "event_id": "flt_valid_srec",
            "source_name": "flightradar24",
            "source_record_id": "fr24_5873711767",
            "evidence_type": "adsb_takeoff",
            "observed_value": "2026-10-10T14:30:00Z",
            "raw_timestamp": "1791642600",
            "snapshot_path": None,
            "snapshot_sha256": None
        }
    ]

    res = evaluate_event_provider_independence("flt_valid_srec", evidence)
    assert res["provider_distinct"] == 1
    assert res["records"][0]["provider"] == "flightradar24"
    assert res["records"][0]["provider_record_id"] == "fr24_5873711767"
    assert res["records"][0]["snapshot_path"] is None


def test_unknown_provenance_never_counted_as_independent():
    """8. Records with unknown provenance must never be counted as independent witnesses."""
    evidence = [
        {
            "evidence_id": "ev_unverified",
            "event_id": "flt_unverified",
            "source_name": "unknown_source_lineage",
            "source_record_id": None,
            "evidence_type": "adsb_takeoff",
            "observed_value": "2026-10-10T14:30:00Z",
            "raw_timestamp": None
        }
    ]

    res = evaluate_event_provider_independence("flt_unverified", evidence)
    assert res["provider_distinct"] == 0
    assert res["independent_observation_count"] == 0
    assert res["unknown_provenance_count"] == 1
    assert res["independence_status"] == "independence_unknown"


def test_evidence_retraction_without_losing_provenance(isolated_db):
    """9. Retracting evidence leaves original provenance intact in event_evidence and updates active provider evaluation."""
    conn = sqlite3.connect(str(isolated_db))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO flight_events (event_id, flight_number, airport_id, movement_type, flight_date, record_nature)
        VALUES ('flt_ret_01', 'RB100', 'DAM', 'departure', '2026-10-10', 'physical_movement');
    """)

    cur.execute("""
        INSERT INTO event_evidence (evidence_id, event_id, source_name, source_record_id, evidence_type, observed_value, raw_timestamp)
        VALUES
        ('ev_fr', 'flt_ret_01', 'flightradar24', 'fr24_01', 'adsb_takeoff', '2026-10-10T10:00:00Z', '1791626400'),
        ('ev_avs', 'flt_ret_01', 'aviationstack', 'avs_01', 'adsb_takeoff', '2026-10-10T10:00:00Z', '2026-10-10T10:00:00+00:00');
    """)
    conn.commit()

    # Before retraction: provider_distinct = 2
    cur.execute("SELECT * FROM v_active_evidence WHERE event_id = 'flt_ret_01';")
    active_pre = [dict(r) for r in cur.fetchall()]
    res_pre = evaluate_event_provider_independence("flt_ret_01", active_pre)
    assert res_pre["provider_distinct"] == 2

    # Retract Aviationstack observation
    cur.execute("""
        INSERT INTO evidence_retractions (retraction_id, evidence_id, action, reason, actor, run_id)
        VALUES ('ret_01', 'ev_avs', 'retract', 'source_telemetry_error', 'auditor', 'run_audit');
    """)
    conn.commit()

    # Original evidence row in event_evidence is untouched and preserves provenance
    cur.execute("SELECT * FROM event_evidence WHERE evidence_id = 'ev_avs';")
    avs_row = dict(cur.fetchone())
    prov, _ = resolve_provider_from_provenance(avs_row["source_name"], avs_row["raw_timestamp"], avs_row["evidence_type"])
    assert prov == "aviationstack"

    # Active evidence now evaluates to single_provider (flightradar24)
    cur.execute("SELECT * FROM v_active_evidence WHERE event_id = 'flt_ret_01';")
    active_post = [dict(r) for r in cur.fetchall()]
    res_post = evaluate_event_provider_independence("flt_ret_01", active_post)
    assert res_post["provider_distinct"] == 1
    assert res_post["distinct_providers"] == ["flightradar24"]
    assert res_post["independence_status"] == "single_provider"

    conn.close()


def test_same_telemetry_across_multiple_snapshots():
    """10. Same telemetry captured across multiple snapshots represents 1 unique observation and 1 duplicate."""
    evidence = [
        {
            "evidence_id": "ev_snap1",
            "event_id": "flt_snap",
            "source_name": "flightradar24",
            "source_record_id": "fr24_001",
            "evidence_type": "adsb_takeoff",
            "observed_value": "2026-10-10T12:00:00Z",
            "raw_timestamp": "1791633600",
            "snapshot_path": "data/raw/snapshots/flightradar24_20261010_01.json",
            "snapshot_sha256": "aaaa1111"
        },
        {
            "evidence_id": "ev_snap2",
            "event_id": "flt_snap",
            "source_name": "flightradar24",
            "source_record_id": "fr24_001",
            "evidence_type": "adsb_takeoff",
            "observed_value": "2026-10-10T12:00:00Z",
            "raw_timestamp": "1791633600",
            "snapshot_path": "data/raw/snapshots/flightradar24_20261010_02.json",
            "snapshot_sha256": "bbbb2222"
        }
    ]

    res = evaluate_event_provider_independence("flt_snap", evidence)
    assert res["provider_distinct"] == 1
    assert res["independent_observation_count"] == 1
    assert res["duplicate_representations"] == 1
    assert res["records"][0]["is_duplicate"] is False
    assert res["records"][1]["is_duplicate"] is True
    assert res["records"][1]["duplicate_of"] == "ev_snap1"


def test_marketing_and_operating_flight_numbers_deduplication():
    """11. Codeshare flight sharing telemetry with operating flight number is identified as duplicate representation."""
    flight_context_operating = {
        "flight_number": "RB272",
        "operating_flight_number": "RB272",
        "flight_date": "2026-10-10",
        "airport_id": "DAM",
        "movement_type": "departure"
    }
    flight_context_marketing = {
        "flight_number": "EK2212",
        "operating_flight_number": "RB272",
        "flight_date": "2026-10-10",
        "airport_id": "DAM",
        "movement_type": "departure"
    }

    # Transponder telemetry from the same operating flight
    ev1 = {
        "evidence_id": "ev_rb272",
        "event_id": "ev_oper",
        "source_name": "flightradar24",
        "source_record_id": "fr24_telemetry_1",
        "evidence_type": "adsb_takeoff",
        "observed_value": "2026-10-10T14:30:00Z",
        "raw_timestamp": "1791642600"
    }
    ev2 = {
        "evidence_id": "ev_ek2212",
        "event_id": "ev_mktg",
        "source_name": "flightradar24",
        "source_record_id": "fr24_telemetry_1",
        "evidence_type": "adsb_takeoff",
        "observed_value": "2026-10-10T14:30:00Z",
        "raw_timestamp": "1791642600"
    }

    provenance = detect_telemetry_duplicates([ev1, ev2], flight_context=flight_context_marketing)
    assert len(provenance) == 2
    assert provenance[0].is_duplicate is False
    assert provenance[1].is_duplicate is True
    assert provenance[1].duplicate_of == "ev_rb272"


def test_genuinely_distinct_observations_same_second_preserved():
    """12. Two distinct observation types in the same second are preserved as distinct observations."""
    evidence = [
        {
            "evidence_id": "ev_to",
            "event_id": "flt_sec",
            "source_name": "flightradar24",
            "source_record_id": "fr24_to",
            "evidence_type": "adsb_takeoff",
            "observed_value": "2026-10-10T12:00:00Z",
            "raw_timestamp": "1791633600"
        },
        {
            "evidence_id": "ev_td",
            "event_id": "flt_sec",
            "source_name": "flightradar24",
            "source_record_id": "fr24_td",
            "evidence_type": "adsb_touchdown",
            "observed_value": "2026-10-10T12:00:00Z",
            "raw_timestamp": "1791633600"
        },
        {
            "evidence_id": "ev_avs_to",
            "event_id": "flt_sec",
            "source_name": "aviationstack",
            "source_record_id": "avs_to",
            "evidence_type": "adsb_takeoff",
            "observed_value": "2026-10-10T12:00:00Z",
            "raw_timestamp": "2026-10-10T15:00:00+00:00"
        }
    ]

    res = evaluate_event_provider_independence("flt_sec", evidence)
    # Both takeoff and touchdown for FR24 are preserved because evidence_type differs
    # Aviationstack takeoff is preserved because provider differs
    assert res["independent_observation_count"] == 3
    assert res["duplicate_representations"] == 0
    assert all(not r["is_duplicate"] for r in res["records"])


def test_different_movement_types_and_airports_never_merged():
    """13. Different movement types (departure vs arrival) or airports (DAM vs ALP) are never merged."""
    ctx_dam_dep = {
        "flight_number": "RB101",
        "flight_date": "2026-10-10",
        "airport_id": "DAM",
        "movement_type": "departure"
    }
    ctx_dxb_arr = {
        "flight_number": "RB101",
        "flight_date": "2026-10-10",
        "airport_id": "DXB",
        "movement_type": "arrival"
    }

    ev_dam = [{
        "evidence_id": "ev_dam",
        "event_id": "ev_1",
        "source_name": "flightradar24",
        "source_record_id": "fr24_dam",
        "evidence_type": "adsb_takeoff",
        "observed_value": "2026-10-10T08:00:00Z",
        "raw_timestamp": "1791619200"
    }]
    ev_dxb = [{
        "evidence_id": "ev_dxb",
        "event_id": "ev_2",
        "source_name": "flightradar24",
        "source_record_id": "fr24_dxb",
        "evidence_type": "adsb_touchdown",
        "observed_value": "2026-10-10T11:00:00Z",
        "raw_timestamp": "1791630000"
    }]

    res_dam = evaluate_event_provider_independence("ev_1", ev_dam, flight_context=ctx_dam_dep)
    res_dxb = evaluate_event_provider_independence("ev_2", ev_dxb, flight_context=ctx_dxb_arr)

    assert res_dam["independent_observation_count"] == 1
    assert res_dam["duplicate_representations"] == 0
    assert res_dxb["independent_observation_count"] == 1
    assert res_dxb["duplicate_representations"] == 0

