#!/usr/bin/env python3
"""
Production Database Migration: v2.1_evidence_retractions
Syrian Airport Data Engine

Implements strict Append-Only Evidence Retraction architecture:
- Creates `evidence_retractions` ledger with monotonic `sequence_num`
- Creates `v_active_evidence` view with deterministic ranking
- Enforces unconditional append-only triggers on `event_evidence` and `evidence_retractions`
- Guarantees transactional execution, foreign key validation, and zero loss of flight_events or historical evidence
"""

import sqlite3
import argparse
import hashlib
import sys
import shutil
from datetime import datetime, timezone
from pathlib import Path

MIGRATION_VERSION = "v2.1_evidence_retractions"
MIGRATION_DESCRIPTION = "Strict append-only evidence retractions ledger and active view"

def calculate_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def create_pre_migration_backup(db_path: Path) -> Path:
    if not db_path.exists():
        raise FileNotFoundError(f"Target database does not exist: {db_path}")
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = db_path.parent / f"backup_{db_path.stem}_pre_{MIGRATION_VERSION}_{timestamp}.db"
    
    shutil.copy2(db_path, backup_path)
    orig_hash = calculate_sha256(db_path)
    backup_hash = calculate_sha256(backup_path)
    
    if orig_hash != backup_hash:
        raise RuntimeError(f"Backup verification failed! Hashes do not match:\nOrig: {orig_hash}\nBackup: {backup_hash}")
    
    print(f"[BACKUP] Created verified backup: {backup_path}")
    print(f"[BACKUP] SHA-256: {backup_hash}")
    return backup_path

def apply_migration(db_path: Path, run_id: str = "prod_migration") -> dict:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    print(f"[MIGRATION] Applying {MIGRATION_VERSION} to: {db_path}")
    initial_hash = calculate_sha256(db_path)
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Verify foreign keys are enabled
    fk_status = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
    if fk_status != 1:
        conn.close()
        raise RuntimeError("Failed to enable foreign_keys pragma on SQLite connection!")
    
    cur = conn.cursor()
    
    # Baseline counts before migration
    cur.execute("SELECT count(*) FROM flight_events;")
    fe_pre = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM flight_events WHERE record_nature = 'physical_movement';")
    phys_pre = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM event_evidence;")
    ee_pre = cur.fetchone()[0]
    
    try:
        cur.execute("BEGIN IMMEDIATE;")
        
        # 1. Schema migrations table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                run_id TEXT,
                checksum TEXT
            )
        """)
        
        # 2. Create evidence_retractions table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS evidence_retractions (
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
        cur.execute("CREATE INDEX IF NOT EXISTS idx_retractions_ev_id ON evidence_retractions(evidence_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_retractions_action ON evidence_retractions(action);")
        
        # 3. Triggers on evidence_retractions
        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_prevent_retraction_update
            BEFORE UPDATE ON evidence_retractions
            BEGIN
                SELECT RAISE(ABORT, 'evidence_retractions ledger is strictly append-only: UPDATE operations are prohibited');
            END;
        """)
        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_prevent_retraction_delete
            BEFORE DELETE ON evidence_retractions
            BEGIN
                SELECT RAISE(ABORT, 'evidence_retractions ledger is strictly append-only: DELETE operations are prohibited');
            END;
        """)
        
        # 4. Strict unconditional append-only triggers on event_evidence
        cur.execute("DROP TRIGGER IF EXISTS trg_prevent_evidence_update;")
        cur.execute("""
            CREATE TRIGGER trg_prevent_evidence_update
            BEFORE UPDATE ON event_evidence
            BEGIN
                SELECT RAISE(ABORT, 'event_evidence ledger is strictly append-only: UPDATE operations are completely prohibited');
            END;
        """)
        cur.execute("DROP TRIGGER IF EXISTS trg_prevent_evidence_delete;")
        cur.execute("""
            CREATE TRIGGER trg_prevent_evidence_delete
            BEFORE DELETE ON event_evidence
            BEGIN
                SELECT RAISE(ABORT, 'event_evidence ledger is append-only: DELETE operations are strictly prohibited');
            END;
        """)
        
        # 5. Populate initial retractions if pre-existing retracted columns exist
        cur.execute("PRAGMA table_info(event_evidence);")
        ee_cols = [r["name"] for r in cur.fetchall()]
        retracted_migrated = 0
        if "validity_status" in ee_cols:
            cur.execute("""
                SELECT evidence_id, retraction_reason, observed_at, snapshot_path, snapshot_sha256
                FROM event_evidence
                WHERE validity_status = 'retracted'
            """)
            retracted_rows = cur.fetchall()
            for r in retracted_rows:
                ret_id = f"ret_init_{r['evidence_id']}"
                cur.execute("""
                    INSERT OR IGNORE INTO evidence_retractions (
                        retraction_id, evidence_id, action, reason, actor, run_id, observed_at, snapshot_path, snapshot_sha256
                    ) VALUES (?, ?, 'retract', coalesce(?, 'historical_retraction'), 'migration_seed', ?, coalesce(?, CURRENT_TIMESTAMP), ?, ?)
                """, (ret_id, r["evidence_id"], r["retraction_reason"], run_id, r["observed_at"], r["snapshot_path"], r["snapshot_sha256"]))
                retracted_migrated += 1
        
        # 6. Active Evidence View v_active_evidence
        cur.execute("DROP VIEW IF EXISTS v_active_evidence;")
        cur.execute("""
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
        
        # 7. Record migration in schema_migrations
        cur.execute("""
            INSERT OR REPLACE INTO schema_migrations (version, description, run_id, checksum)
            VALUES (?, ?, ?, ?)
        """, (MIGRATION_VERSION, MIGRATION_DESCRIPTION, run_id, initial_hash))
        
        # 8. Foreign key integrity check
        cur.execute("PRAGMA foreign_key_check;")
        fk_errors = cur.fetchall()
        if fk_errors:
            raise RuntimeError(f"Foreign key integrity check failed after migration: {fk_errors}")
        
        conn.commit()
        print("[MIGRATION] Transaction committed successfully.")
        
    except Exception as e:
        conn.rollback()
        conn.close()
        raise RuntimeError(f"Migration aborted and rolled back due to error: {e}") from e
    
    # Post-migration verification
    cur.execute("SELECT count(*) FROM flight_events;")
    fe_post = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM flight_events WHERE record_nature = 'physical_movement';")
    phys_post = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM event_evidence;")
    ee_post = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM v_active_evidence;")
    active_ee_post = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM evidence_retractions;")
    retractions_total = cur.fetchone()[0]
    
    conn.close()
    
    assert fe_pre == fe_post, f"flight_events count mismatch! pre={fe_pre}, post={fe_post}"
    assert phys_pre == phys_post, f"physical_movement count mismatch! pre={phys_pre}, post={phys_post}"
    assert ee_pre == ee_post, f"event_evidence count mismatch! pre={ee_pre}, post={ee_post}"
    
    post_hash = calculate_sha256(db_path)
    
    results = {
        "version": MIGRATION_VERSION,
        "flight_events": fe_post,
        "physical_movements": phys_post,
        "total_evidence": ee_post,
        "active_evidence": active_ee_post,
        "retractions_total": retractions_total,
        "retracted_migrated": retracted_migrated,
        "post_hash": post_hash
    }
    print(f"[MIGRATION SUCCESS] {results}")
    return results

def validate_migration(db_path: Path) -> bool:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    
    print(f"[VALIDATION] Auditing migration state on {db_path}...")
    
    # 1. Check tables and views
    c.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view');")
    names = set(r["name"] for r in c.fetchall())
    assert "evidence_retractions" in names, "Missing table: evidence_retractions"
    assert "v_active_evidence" in names, "Missing view: v_active_evidence"
    assert "event_evidence" in names, "Missing table: event_evidence"
    assert "schema_migrations" in names, "Missing table: schema_migrations"
    
    # 2. Check foreign key validity
    c.execute("PRAGMA foreign_key_check;")
    fk_errors = c.fetchall()
    assert len(fk_errors) == 0, f"Foreign key check errors: {fk_errors}"
    
    # 3. Check trigger enforcement
    c.execute("SELECT name FROM sqlite_master WHERE type = 'trigger';")
    triggers = set(r["name"] for r in c.fetchall())
    assert "trg_prevent_evidence_update" in triggers, "Missing trigger: trg_prevent_evidence_update"
    assert "trg_prevent_evidence_delete" in triggers, "Missing trigger: trg_prevent_evidence_delete"
    assert "trg_prevent_retraction_update" in triggers, "Missing trigger: trg_prevent_retraction_update"
    assert "trg_prevent_retraction_delete" in triggers, "Missing trigger: trg_prevent_retraction_delete"
    
    # 4. Check active evidence consistency
    c.execute("SELECT count(*) FROM event_evidence;")
    total_ee = c.fetchone()[0]
    c.execute("SELECT count(*) FROM v_active_evidence;")
    active_ee = c.fetchone()[0]
    c.execute("""
        SELECT count(DISTINCT evidence_id) FROM (
            SELECT evidence_id, action,
                   ROW_NUMBER() OVER (PARTITION BY evidence_id ORDER BY sequence_num DESC) as rn
            FROM evidence_retractions
        ) WHERE rn = 1 AND action = 'retract';
    """)
    active_retractions = c.fetchone()[0]
    
    assert total_ee == (active_ee + active_retractions), f"Ledger sum mismatch: {active_ee} + {active_retractions} != {total_ee}"
    
    # 5. Check physical movement coverage
    c.execute("""
        SELECT count(*) FROM flight_events fe
        WHERE fe.record_nature = 'physical_movement'
          AND NOT EXISTS (
              SELECT 1 FROM v_active_evidence ae
              WHERE ae.event_id = fe.event_id
                AND ae.evidence_type IN ('adsb_takeoff', 'adsb_touchdown', 'commercial_takeoff', 'commercial_touchdown')
          )
    """)
    unsupported_phys = c.fetchone()[0]
    assert unsupported_phys == 0, f"Found {unsupported_phys} physical movements without active evidence!"
    
    conn.close()
    print("[VALIDATION PASSED] All post-migration invariants satisfied 100%.")
    return True

def rollback_migration(db_path: Path) -> bool:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    print(f"[ROLLBACK] Reverting {MIGRATION_VERSION} schema from: {db_path}")
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    
    try:
        c.execute("BEGIN IMMEDIATE;")
        c.execute("DROP VIEW IF EXISTS v_active_evidence;")
        c.execute("DROP TRIGGER IF EXISTS trg_prevent_retraction_update;")
        c.execute("DROP TRIGGER IF EXISTS trg_prevent_retraction_delete;")
        c.execute("DROP TABLE IF EXISTS evidence_retractions;")
        c.execute("DROP TRIGGER IF EXISTS trg_prevent_evidence_update;")
        c.execute("DROP TRIGGER IF EXISTS trg_prevent_evidence_delete;")
        
        # Restore pre-migration triggers
        c.execute("""
            CREATE TRIGGER trg_prevent_evidence_update
            BEFORE UPDATE ON event_evidence
            BEGIN
                SELECT RAISE(ABORT, 'event_evidence ledger is append-only: UPDATE operations are strictly prohibited');
            END;
        """)
        c.execute("""
            CREATE TRIGGER trg_prevent_evidence_delete
            BEFORE DELETE ON event_evidence
            BEGIN
                SELECT RAISE(ABORT, 'event_evidence ledger is append-only: DELETE operations are strictly prohibited');
            END;
        """)
        
        c.execute("DELETE FROM schema_migrations WHERE version = ?;", (MIGRATION_VERSION,))
        conn.commit()
        print("[ROLLBACK] Schema changes reverted successfully.")
    except Exception as e:
        conn.rollback()
        conn.close()
        raise RuntimeError(f"Rollback failed: {e}") from e
    
    conn.close()
    return True

def main():
    parser = argparse.ArgumentParser(description=f"Syrian Airport Data Engine Migration: {MIGRATION_VERSION}")
    parser.add_argument("--db-path", type=str, required=True, help="Path to SQLite database")
    parser.add_argument("--backup", action="store_true", help="Create verified pre-migration backup only")
    parser.add_argument("--apply", action="store_true", help="Apply the migration")
    parser.add_argument("--validate", action="store_true", help="Validate post-migration database state")
    parser.add_argument("--rollback", action="store_true", help="Roll back migration schema changes")
    parser.add_argument("--run-id", type=str, default="cli_run", help="Operational run identifier")
    
    args = parser.parse_args()
    db_file = Path(args.db_path)
    
    if args.backup:
        create_pre_migration_backup(db_file)
    elif args.apply:
        apply_migration(db_file, run_id=args.run_id)
    elif args.validate:
        validate_migration(db_file)
    elif args.rollback:
        rollback_migration(db_file)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
