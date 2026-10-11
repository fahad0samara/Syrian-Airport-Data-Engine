import sqlite3
import pytest
from fastapi.testclient import TestClient
from src.api import app
from src.reassessment import reassess_event_consistency

client = TestClient(app)

@pytest.fixture
def mock_db_with_retractions(tmp_path, monkeypatch):
    """
    Sets up an isolated test database with the migration schema, seeds test event
    and evidence, and points the API get_connection to it.
    """
    db_file = tmp_path / "test_api_retractions.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    
    # 1. Base tables
    c.execute("""
        CREATE TABLE airports (
            airport_id TEXT PRIMARY KEY,
            iata_code TEXT,
            icao_code TEXT,
            name TEXT
        )
    """)
    c.execute("INSERT INTO airports VALUES ('DAM', 'DAM', 'OSDI', 'Damascus International Airport')")
    
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
            quality_flags TEXT
        )
    """)
    
    c.execute("""
        CREATE TABLE event_evidence (
            evidence_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_record_id TEXT,
            evidence_type TEXT NOT NULL,
            observed_value TEXT NOT NULL,
            raw_timestamp TEXT,
            observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            snapshot_path TEXT,
            snapshot_sha256 TEXT,
            UNIQUE(event_id, source_name, evidence_type, observed_value)
        )
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
        )
    """)
    
    c.execute("""
        CREATE TRIGGER trg_prevent_evidence_update
        BEFORE UPDATE ON event_evidence
        BEGIN
            SELECT RAISE(ABORT, 'event_evidence ledger is strictly append-only: UPDATE operations are completely prohibited');
        END;
    """)
    c.execute("""
        CREATE TRIGGER trg_prevent_evidence_delete
        BEFORE DELETE ON event_evidence
        BEGIN
            SELECT RAISE(ABORT, 'event_evidence ledger is append-only: DELETE operations are strictly prohibited');
        END;
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
    
    # Seed single test physical departure
    c.execute("""
        INSERT INTO flight_events (
            event_id, flight_number, airport_id, movement_type, flight_date,
            actual_dep_time, record_nature, quality_flags
        ) VALUES (
            'ev_api_01', 'RB999', 'DAM', 'departure', '2026-10-10',
            '2026-10-10T14:00:00Z', 'physical_movement', 'verified'
        )
    """)
    
    c.execute("""
        INSERT INTO event_evidence (
            evidence_id, event_id, source_name, evidence_type, observed_value, raw_timestamp
        ) VALUES 
            ('eid_01', 'ev_api_01', 'flightradar24', 'adsb_takeoff', '2026-10-10T14:00:00Z', '1791640800'),
            ('eid_02', 'ev_api_01', 'flightradar24', 'aircraft_registration', 'YK-TEST', NULL)
    """)
    
    conn.commit()
    conn.close()
    
    def get_test_conn():
        cn = sqlite3.connect(str(db_file))
        cn.row_factory = sqlite3.Row
        cn.execute("PRAGMA foreign_keys = ON;")
        return cn
        
    monkeypatch.setattr("src.api.get_connection", get_test_conn)
    return str(db_file)

def test_api_evidence_initially_active(mock_db_with_retractions):
    """1. Evidence is initially active and returned by API."""
    res = client.get("/api/events/ev_api_01/evidence")
    assert res.status_code == 200
    data = res.json()
    assert data["event_id"] == "ev_api_01"
    assert data["evidence_count"] == 2
    assert data["active_count"] == 2
    assert data["retracted_count"] == 0
    assert all(e["ledger_status"] == "active" for e in data["evidence"])

def test_api_evidence_after_retraction(mock_db_with_retractions):
    """2. Evidence after retraction disappears from default API call and is flagged in audit."""
    conn = sqlite3.connect(mock_db_with_retractions)
    conn.execute("PRAGMA foreign_keys = ON;")
    # Retract the takeoff evidence
    conn.execute("""
        INSERT INTO evidence_retractions (retraction_id, evidence_id, action, reason, actor, run_id)
        VALUES ('ret_test_01', 'eid_01', 'retract', 'unverified_signal', 'auditor', 'run_01')
    """)
    conn.commit()
    conn.close()
    
    # Default call without include_retracted: only 1 active evidence remains (registration)
    res = client.get("/api/events/ev_api_01/evidence")
    assert res.status_code == 200
    data = res.json()
    assert data["evidence_count"] == 1
    assert data["active_count"] == 1
    assert data["evidence"][0]["evidence_id"] == "eid_02"
    
    # Audit call with include_retracted=True: both records visible, eid_01 marked retracted
    res_audit = client.get("/api/events/ev_api_01/evidence?include_retracted=true")
    assert res_audit.status_code == 200
    data_audit = res_audit.json()
    assert data_audit["evidence_count"] == 2
    assert data_audit["active_count"] == 1
    assert data_audit["retracted_count"] == 1
    
    retracted_row = next(e for e in data_audit["evidence"] if e["evidence_id"] == "eid_01")
    assert retracted_row["ledger_status"] == "retracted"
    assert retracted_row["retraction_reason"] == "unverified_signal"

def test_api_evidence_after_unretraction(mock_db_with_retractions):
    """3. Unretracting evidence restores it to active view in API."""
    conn = sqlite3.connect(mock_db_with_retractions)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("""
        INSERT INTO evidence_retractions (retraction_id, evidence_id, action, reason, actor, run_id)
        VALUES ('ret_test_02', 'eid_01', 'unretract', 're_verified_by_tower', 'auditor', 'run_02')
    """)
    conn.commit()
    conn.close()
    
    res = client.get("/api/events/ev_api_01/evidence")
    assert res.status_code == 200
    data = res.json()
    assert data["evidence_count"] == 2
    assert data["active_count"] == 2
    assert all(e["ledger_status"] == "active" for e in data["evidence"])

def test_api_event_classification_after_retraction_and_reassessment(mock_db_with_retractions):
    """4. Event classification degrades safely when physical evidence is retracted."""
    conn = sqlite3.connect(mock_db_with_retractions)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Retract takeoff evidence
    conn.execute("""
        INSERT INTO evidence_retractions (retraction_id, evidence_id, action, reason, actor, run_id)
        VALUES ('ret_test_03', 'eid_01', 'retract', 'noise', 'auditor', 'run_03')
    """)
    conn.commit()
    
    # Trigger explicit reassessment
    reassessment = reassess_event_consistency(conn, event_id="ev_api_01", dry_run=False)
    assert len(reassessment) == 1
    assert reassessment[0]["action"] == "downgrade"
    assert reassessment[0]["new_nature"] == "scheduled_service"
    conn.close()
    
    # Query API flights endpoint
    res = client.get("/api/flights?airport_id=DAM")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    flt = data["flights"][0]
    assert flt["record_nature"] == "scheduled_service"
    assert flt["actual_dep_time"] is None

def test_api_event_classification_after_unretraction_and_reassessment(mock_db_with_retractions):
    """5. Event classification is restored when physical evidence is unretracted."""
    conn = sqlite3.connect(mock_db_with_retractions)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # 1. First retract and downgrade
    conn.execute("""
        INSERT INTO evidence_retractions (retraction_id, evidence_id, action, reason, actor, run_id)
        VALUES ('ret_test_04a', 'eid_01', 'retract', 'initial_noise', 'auditor', 'run_04a')
    """)
    conn.commit()
    reassess_event_consistency(conn, event_id="ev_api_01", dry_run=False)
    
    # Verify it is scheduled_service
    cur = conn.cursor()
    cur.execute("SELECT record_nature FROM flight_events WHERE event_id = 'ev_api_01'")
    assert cur.fetchone()[0] == "scheduled_service"
    
    # 2. Unretract takeoff evidence
    conn.execute("""
        INSERT INTO evidence_retractions (retraction_id, evidence_id, action, reason, actor, run_id)
        VALUES ('ret_test_04b', 'eid_01', 'unretract', 'reconfirmed_by_radar', 'auditor', 'run_04b')
    """)
    conn.commit()
    
    # Trigger explicit reassessment
    reassessment = reassess_event_consistency(conn, event_id="ev_api_01", dry_run=False)
    assert len(reassessment) == 1
    assert reassessment[0]["action"] == "promote"
    assert reassessment[0]["new_nature"] == "physical_movement"
    conn.close()
    
    # Query API flights endpoint
    res = client.get("/api/flights?airport_id=DAM")
    assert res.status_code == 200
    data = res.json()
    flt = data["flights"][0]
    assert flt["record_nature"] == "physical_movement"
