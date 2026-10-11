"""
Event Consistency Reassessment Engine
Syrian Airport Data Engine

Executes explicit, auditable event reassessments triggered by evidence retractions:
- Reads all active supporting evidence from `v_active_evidence`
- Preserves `physical_movement` if sufficient independent evidence remains
- Downgrades an event only when its active supporting physical evidence is insufficient
- Strictly prevents promotion of `scheduled_service` based on estimated timestamps
- Idempotent and transaction-safe
"""

import sqlite3
from typing import Optional, List, Dict, Any

def reassess_event_consistency(
    conn: sqlite3.Connection,
    event_id: Optional[str] = None,
    dry_run: bool = True
) -> List[Dict[str, Any]]:
    """
    Audits and optionally reconciles flight_events based on active evidence in v_active_evidence.
    """
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Check if v_active_evidence exists
    cur.execute("SELECT count(*) FROM sqlite_master WHERE type = 'view' AND name = 'v_active_evidence';")
    if cur.fetchone()[0] == 0:
        raise RuntimeError("Cannot execute reassessment: view 'v_active_evidence' does not exist in database!")
    
    if event_id:
        cur.execute("SELECT * FROM flight_events WHERE event_id = ?;", (event_id,))
        events = [dict(r) for r in cur.fetchall()]
    else:
        cur.execute("SELECT * FROM flight_events ORDER BY flight_date ASC, airport_id ASC;")
        events = [dict(r) for r in cur.fetchall()]
        
    audit_log = []
    
    for ev in events:
        eid = ev["event_id"]
        mtype = ev["movement_type"]
        current_nature = ev["record_nature"]
        
        # Query active evidence for this event
        cur.execute("""
            SELECT evidence_id, source_name, evidence_type, observed_value, raw_timestamp
            FROM v_active_evidence
            WHERE event_id = ?
        """, (eid,))
        active_evidence = [dict(r) for r in cur.fetchall()]
        
        active_takeoffs = [e for e in active_evidence if e["evidence_type"] in ("adsb_takeoff", "commercial_takeoff")]
        active_touchdowns = [e for e in active_evidence if e["evidence_type"] in ("adsb_touchdown", "commercial_touchdown")]
        active_estimates = [e for e in active_evidence if e["evidence_type"] in ("estimated_departure", "estimated_arrival")]
        
        has_active_physical = False
        if mtype == "departure" and len(active_takeoffs) > 0:
            has_active_physical = True
        elif mtype == "arrival" and len(active_touchdowns) > 0:
            has_active_physical = True
            
        action = "none"
        new_nature = current_nature
        reason = "consistent"
        
        # Case 1: Currently physical_movement but active physical evidence is retracted
        if current_nature == "physical_movement" and not has_active_physical:
            action = "downgrade"
            new_nature = "scheduled_service"
            reason = f"all_active_physical_{mtype}_evidence_retracted"
            
            if not dry_run:
                # Update flight_events safely
                if mtype == "departure":
                    cur.execute("""
                        UPDATE flight_events
                        SET record_nature = 'scheduled_service', actual_dep_time = NULL
                        WHERE event_id = ?
                    """, (eid,))
                else:
                    cur.execute("""
                        UPDATE flight_events
                        SET record_nature = 'scheduled_service', actual_arr_time = NULL
                        WHERE event_id = ?
                    """, (eid,))
                    
        # Case 2: Currently physical_movement with independent evidence remaining
        elif current_nature == "physical_movement" and has_active_physical:
            action = "preserve"
            reason = f"supported_by_{len(active_takeoffs if mtype == 'departure' else active_touchdowns)}_active_physical_observations"
            
        # Case 3: Currently scheduled_service
        elif current_nature == "scheduled_service":
            if not has_active_physical:
                action = "preserve"
                reason = "scheduled_service_no_physical_evidence"
            else:
                # Active physical telemetry exists
                action = "promote"
                new_nature = "physical_movement"
                reason = "active_physical_telemetry_available"
                if not dry_run:
                    cur.execute("""
                        UPDATE flight_events
                        SET record_nature = 'physical_movement'
                        WHERE event_id = ?
                    """, (eid,))
                    
        audit_entry = {
            "event_id": eid,
            "flight_number": ev["flight_number"],
            "airport_id": ev["airport_id"],
            "movement_type": mtype,
            "flight_date": ev["flight_date"],
            "previous_nature": current_nature,
            "new_nature": new_nature,
            "action": action,
            "reason": reason,
            "active_takeoff_count": len(active_takeoffs),
            "active_touchdown_count": len(active_touchdowns),
            "active_estimate_count": len(active_estimates)
        }
        
        if action != "preserve" or event_id is not None:
            audit_log.append(audit_entry)
            
    if not dry_run:
        conn.commit()
        
    return audit_log
