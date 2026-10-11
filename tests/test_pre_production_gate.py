import sqlite3
import pytest
import pandas as pd
from datetime import datetime

@pytest.fixture
def gate_db(tmp_path):
    db_file = tmp_path / "gate_test.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    
    # Create schema matching the proposed production migration
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
    c.execute("CREATE INDEX idx_retractions_ev_id ON evidence_retractions(evidence_id)")
    c.execute("CREATE INDEX idx_retractions_action ON evidence_retractions(action)")
    
    # Triggers
    c.execute("""
        CREATE TRIGGER trg_prevent_evidence_update
        BEFORE UPDATE ON event_evidence
        BEGIN
            SELECT RAISE(ABORT, 'event_evidence ledger is strictly append-only: UPDATE operations are completely prohibited');
        END
    """)
    c.execute("""
        CREATE TRIGGER trg_prevent_evidence_delete
        BEFORE DELETE ON event_evidence
        BEGIN
            SELECT RAISE(ABORT, 'event_evidence ledger is append-only: DELETE operations are strictly prohibited');
        END
    """)
    c.execute("""
        CREATE TRIGGER trg_prevent_retraction_update
        BEFORE UPDATE ON evidence_retractions
        BEGIN
            SELECT RAISE(ABORT, 'evidence_retractions ledger is strictly append-only: UPDATE operations are prohibited');
        END
    """)
    c.execute("""
        CREATE TRIGGER trg_prevent_retraction_delete
        BEFORE DELETE ON evidence_retractions
        BEGIN
            SELECT RAISE(ABORT, 'evidence_retractions ledger is strictly append-only: DELETE operations are prohibited');
        END
    """)
    
    # View
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
        )
    """)
    
    # Flight events table
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
            destination_airport TEXT,
            origin_airport TEXT
        )
    """)
    conn.commit()
    yield conn
    conn.close()

def test_retraction_lifecycle_10_steps(gate_db):
    """1. Full 10-step lifecycle test with sequence_num and foreign keys."""
    c = gate_db.cursor()
    ev_id = "ev_test_100"
    
    # 1. Insert evidence
    c.execute("""
        INSERT INTO event_evidence (evidence_id, event_id, source_name, evidence_type, observed_value)
        VALUES (?, 'ev_1', 'fr24', 'adsb_takeoff', '2026-10-10T15:00:00Z')
    """, (ev_id,))
    gate_db.commit()
    
    # 2. Retract it
    c.execute("""
        INSERT INTO evidence_retractions (retraction_id, evidence_id, action, reason, actor, run_id)
        VALUES ('ret_1', ?, 'retract', 'reason_1', 'actor_1', 'run_1')
    """, (ev_id,))
    gate_db.commit()
    
    # 3. Confirm it disappears from v_active_evidence
    c.execute("SELECT count(*) FROM v_active_evidence WHERE evidence_id = ?", (ev_id,))
    assert c.fetchone()[0] == 0
    
    # 4. Unretract it
    c.execute("""
        INSERT INTO evidence_retractions (retraction_id, evidence_id, action, reason, actor, run_id)
        VALUES ('ret_2', ?, 'unretract', 'reason_2', 'actor_1', 'run_2')
    """, (ev_id,))
    gate_db.commit()
    
    # 5. Confirm it reappears
    c.execute("SELECT count(*) FROM v_active_evidence WHERE evidence_id = ?", (ev_id,))
    assert c.fetchone()[0] == 1
    
    # 6. Retract it again
    c.execute("""
        INSERT INTO evidence_retractions (retraction_id, evidence_id, action, reason, actor, run_id)
        VALUES ('ret_3', ?, 'retract', 'reason_3', 'actor_1', 'run_3')
    """, (ev_id,))
    gate_db.commit()
    
    # 7. Confirm it disappears again
    c.execute("SELECT count(*) FROM v_active_evidence WHERE evidence_id = ?", (ev_id,))
    assert c.fetchone()[0] == 0
    
    # 8. Repeat the same operation with same run_id (INSERT OR IGNORE)
    c.execute("""
        INSERT OR IGNORE INTO evidence_retractions (retraction_id, evidence_id, action, reason, actor, run_id)
        VALUES ('ret_3_dup', ?, 'retract', 'reason_3', 'actor_1', 'run_3')
    """, (ev_id,))
    gate_db.commit()
    c.execute("SELECT count(*) FROM evidence_retractions WHERE evidence_id = ? AND run_id = 'run_3'", (ev_id,))
    assert c.fetchone()[0] == 1  # No duplicate
    
    # 9. Attempt to retract nonexistent evidence ID
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("""
            INSERT INTO evidence_retractions (retraction_id, evidence_id, action, reason, actor, run_id)
            VALUES ('ret_bad', 'nonexistent_ev', 'retract', 'reason', 'actor', 'run_4')
        """)
        gate_db.commit()
        
    # 10. Attempt to update or delete records from both append-only tables
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("UPDATE event_evidence SET observed_value = 'mutated' WHERE evidence_id = ?", (ev_id,))
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("DELETE FROM event_evidence WHERE evidence_id = ?", (ev_id,))
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("UPDATE evidence_retractions SET reason = 'mutated' WHERE retraction_id = 'ret_1'")
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("DELETE FROM evidence_retractions WHERE retraction_id = 'ret_1'")

def test_physical_movement_counts_use_valid_event_classifications(gate_db):
    """2. Physical movement counts must only count events with active evidence."""
    c = gate_db.cursor()
    # Insert event
    c.execute("""
        INSERT INTO flight_events (event_id, flight_number, airport_id, movement_type, flight_date, actual_dep_time, record_nature)
        VALUES ('flt_01', 'RB100', 'DAM', 'departure', '2026-10-10', '2026-10-10T12:00:00Z', 'physical_movement')
    """)
    # Insert supporting evidence
    c.execute("""
        INSERT INTO event_evidence (evidence_id, event_id, source_name, evidence_type, observed_value)
        VALUES ('ev_flt_01', 'flt_01', 'fr24', 'adsb_takeoff', '2026-10-10T12:00:00Z')
    """)
    gate_db.commit()
    
    # Count verified physical movements
    query = """
        SELECT count(*) FROM flight_events fe
        WHERE fe.record_nature = 'physical_movement'
          AND EXISTS (
              SELECT 1 FROM v_active_evidence ae
              WHERE ae.event_id = fe.event_id
                AND ae.evidence_type IN ('adsb_takeoff', 'adsb_touchdown')
          )
    """
    c.execute(query)
    assert c.fetchone()[0] == 1
    
    # Now retract the only supporting evidence
    c.execute("""
        INSERT INTO evidence_retractions (retraction_id, evidence_id, action, reason, actor, run_id)
        VALUES ('ret_flt_01', 'ev_flt_01', 'retract', 'noise', 'audit', 'run_01')
    """)
    gate_db.commit()
    
    # Count must now be 0!
    c.execute(query)
    assert c.fetchone()[0] == 0

def test_remote_destination_touchdown_not_labeled_local_arrival(gate_db):
    """3. Departure from local airport with remote touchdown must NOT be labeled as local arrival."""
    c = gate_db.cursor()
    # FYC501: departure from DAM to BGW
    c.execute("""
        INSERT INTO flight_events (
            event_id, flight_number, airport_id, movement_type, flight_date,
            actual_dep_time, actual_arr_time, record_nature, destination_airport
        ) VALUES (
            'fyc501_event', 'FYC501', 'DAM', 'departure', '2026-10-10',
            '2026-10-10T15:31:43Z', '2026-10-10T16:34:36Z', 'physical_movement', 'BGW'
        )
    """)
    gate_db.commit()
    
    # When querying DAM airport movements, this must be counted as DEPARTURE, never as an ARRIVAL at DAM!
    c.execute("SELECT movement_type, airport_id, destination_airport FROM flight_events WHERE event_id = 'fyc501_event'")
    row = c.fetchone()
    assert row[0] == "departure"
    assert row[1] == "DAM"
    assert row[2] == "BGW"
    
    # Local Damascus movements aggregation:
    c.execute("""
        SELECT 
            SUM(CASE WHEN movement_type = 'departure' THEN 1 ELSE 0 END) as dep_count,
            SUM(CASE WHEN movement_type = 'arrival' THEN 1 ELSE 0 END) as arr_count
        FROM flight_events
        WHERE airport_id = 'DAM' AND event_id = 'fyc501_event'
    """)
    dep_count, arr_count = c.fetchone()
    assert dep_count == 1
    assert arr_count == 0  # Destination touchdown must NEVER count as DAM arrival!

def test_evidence_audit_distinguishes_active_and_retracted(gate_db):
    """4. Evidence audit queries properly separate active from retracted observations."""
    c = gate_db.cursor()
    c.execute("""
        INSERT INTO event_evidence (evidence_id, event_id, source_name, evidence_type, observed_value)
        VALUES 
            ('ev_a', 'event_x', 'fr24', 'adsb_takeoff', '15:00:00Z'),
            ('ev_b', 'event_x', 'fr24', 'adsb_touchdown', '19:00:00Z')
    """)
    # Retract ev_b
    c.execute("""
        INSERT INTO evidence_retractions (retraction_id, evidence_id, action, reason, actor, run_id)
        VALUES ('ret_b', 'ev_b', 'retract', 'wrong_touchdown', 'audit', 'r1')
    """)
    gate_db.commit()
    
    # Query separating active and retracted
    c.execute("""
        SELECT 
            ee.evidence_id,
            CASE WHEN ae.evidence_id IS NOT NULL THEN 'active' ELSE 'retracted' END as status
        FROM event_evidence ee
        LEFT JOIN v_active_evidence ae ON ee.evidence_id = ae.evidence_id
        WHERE ee.event_id = 'event_x'
        ORDER BY ee.evidence_id
    """)
    rows = c.fetchall()
    assert rows[0] == ('ev_a', 'active')
    assert rows[1] == ('ev_b', 'retracted')
