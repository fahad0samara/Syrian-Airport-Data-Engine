"""
Timestamp Provenance & Evidence Taxonomy Correction Engine
Syrian Airport Data Engine — Version 2.20.5

Enforces strict timestamp semantics in the application layer:
1. Only source fields explicitly representing actual/real timestamps may populate actual fields.
2. Estimated timestamps must never populate actual fields.
3. Scheduled timestamps must never populate actual fields.
4. Missing actual timestamps remain null.
5. Preserves the original raw source payload and source field name.
6. Does not infer a physical movement from an estimated timestamp.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from collections import defaultdict

DAMASCUS_TZ = ZoneInfo("Asia/Damascus")

# 40 events identified where estimated timestamps were mapped to actual fields in flight_events
ESTIMATED_IN_ACTUAL_EVENTS: Dict[str, Dict[str, Any]] = {
    # 9 physical_movement departure events where foreign destination arrival ETA was mapped to actual_arr_time
    "6f3f3b3c16844646": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "departure", "flight": "PC771"},
    "339297a946c498c3": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "departure", "flight": "XY230"},
    "ed1a39d3aa27b295": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "departure", "flight": "EY562"},
    "c5dbcfdfa11cb7b3": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "departure", "flight": "FYC521"},
    "14175fe4b51cfa91": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "departure", "flight": "FYC727"},
    "ca726fcf8dc8a9df": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "departure", "flight": "FZ1114"},
    "81d8452b0a0b029f": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "departure", "flight": "G9376"},
    "f6afc1b400abecc6": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "departure", "flight": "RB441"},
    "85e816d0ed6253c6": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "departure", "flight": "XY592"},

    # 31 scheduled_service events where estimated departure or arrival was mapped to actual fields
    "ebbb2ef5f7ab759c": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "arrival", "flight": "FZ1191"},
    "8ac27ea339ce9326": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "arrival", "flight": "G9351"},
    "0c2bc8bc07b082e7": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "arrival", "flight": "3L456"},
    "940e9ab59df40177": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "arrival", "flight": "FZ1191"},
    "5080817825bafe34": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "arrival", "flight": "G9351"},
    "0a42d9b15f88603b": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "arrival", "flight": "RJ433"},
    "3524fb07f594da11": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "arrival", "flight": "XY229"},
    "ebc42abf6aa5ea9c": {"raw_field": "time.estimated.departure", "target_field": "actual_dep_time", "correct_field": "estimated_dep_time", "movement": "arrival", "flight": "G9351"},
    "8497422faec026ad": {"raw_field": "time.estimated.departure", "target_field": "actual_dep_time", "correct_field": "estimated_dep_time", "movement": "arrival", "flight": "XQ808"},
    "4d1bb226d3e5b33e": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "arrival", "flight": "VF317"},
    "e8f0ec5e3c44c85e": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "arrival", "flight": "VF591"},
    "c1b86a292e2b8449": {"raw_field": "time.estimated.departure", "target_field": "actual_dep_time", "correct_field": "estimated_dep_time", "movement": "arrival", "flight": "XY377"},
    "6e9ccc725c3b169e": {"raw_field": "time.estimated.departure", "target_field": "actual_dep_time", "correct_field": "estimated_dep_time", "movement": "departure", "flight": "G9376"},
    "2bf0ecb1ec6710bf": {"raw_field": "time.estimated.departure", "target_field": "actual_dep_time", "correct_field": "estimated_dep_time", "movement": "departure", "flight": "VF318"},
    "5831ce0a6370bfbe": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "arrival", "flight": "FYC522"},
    "d25e1e9000d0755b": {"raw_field": "time.estimated.departure", "target_field": "actual_dep_time", "correct_field": "estimated_dep_time", "movement": "arrival", "flight": "FYC728"},
    "8ea516585dbbdf5e": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "arrival", "flight": "VF317"},
    "78e4584fff8d8db2": {"raw_field": "time.estimated.departure", "target_field": "actual_dep_time", "correct_field": "estimated_dep_time", "movement": "arrival", "flight": "XY377"},
    "0ba6fcaa740988fe": {"raw_field": "time.estimated.departure", "target_field": "actual_dep_time", "correct_field": "estimated_dep_time", "movement": "departure", "flight": "RB272"},
    "768c17d5df43ecf3": {"raw_field": "time.estimated.departure", "target_field": "actual_dep_time", "correct_field": "estimated_dep_time", "movement": "departure", "flight": "VF318"},
    "6bc29421a851a18d": {"raw_field": "time.estimated.departure", "target_field": "actual_dep_time", "correct_field": "estimated_dep_time", "movement": "arrival", "flight": "EY561"},
    "51cc663b38bc7df7": {"raw_field": "time.estimated.departure", "target_field": "actual_dep_time", "correct_field": "estimated_dep_time", "movement": "arrival", "flight": "G9363"},
    "b1ae2ce4a8f34b5a": {"raw_field": "time.estimated.departure", "target_field": "actual_dep_time", "correct_field": "estimated_dep_time", "movement": "arrival", "flight": "G9375"},
    "a47846504421ffc7": {"raw_field": "time.estimated.departure", "target_field": "actual_dep_time", "correct_field": "estimated_dep_time", "movement": "arrival", "flight": "G9433"},
    "2aa4ee6f73e0f144": {"raw_field": "time.estimated.departure", "target_field": "actual_dep_time", "correct_field": "estimated_dep_time", "movement": "arrival", "flight": "QR410"},
    "092de51eac9b78e9": {"raw_field": "time.estimated.departure", "target_field": "actual_dep_time", "correct_field": "estimated_dep_time", "movement": "arrival", "flight": "RB444"},
    "f25f071416ef33e0": {"raw_field": "time.estimated.departure", "target_field": "actual_dep_time", "correct_field": "estimated_dep_time", "movement": "arrival", "flight": "TK848"},
    "f1d1a2360948b303": {"raw_field": "time.estimated.departure", "target_field": "actual_dep_time", "correct_field": "estimated_dep_time", "movement": "departure", "flight": "EY562"},
    "d6420e85d3e001ef": {"raw_field": "time.estimated.departure", "target_field": "actual_dep_time", "correct_field": "estimated_dep_time", "movement": "departure", "flight": "TUAF154"},
    "d6088a84e8aa8f04": {"raw_field": "time.estimated.arrival", "target_field": "actual_arr_time", "correct_field": "estimated_arr_time", "movement": "arrival", "flight": "J9179"},
    "cdc36216646c747c": {"raw_field": "time.estimated.departure", "target_field": "actual_dep_time", "correct_field": "estimated_dep_time", "movement": "arrival", "flight": "RB342"},
}

def correct_flight_record_semantics(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adjusts timestamp semantics in the application layer:
    - Guarantees separate existence of all 6 timestamp fields:
      scheduled_dep_time, estimated_dep_time, actual_dep_time,
      scheduled_arr_time, estimated_arr_time, actual_arr_time.
    - Moves estimated timestamps that were mapped into actual fields over to estimated fields.
    - Sets actual timestamp fields to None when no genuine actual/real timestamp exists.
    - Recomputes actual_movement_date and estimated_movement_date strictly from actual and estimated times.
    """
    eid = record.get("event_id")
    mtype = record.get("movement_type")
    nature = record.get("record_nature")

    # Initialize all 6 fields
    sched_dep = record.get("scheduled_dep_time")
    est_dep = record.get("estimated_dep_time")
    act_dep = record.get("actual_dep_time")

    sched_arr = record.get("scheduled_arr_time")
    est_arr = record.get("estimated_arr_time")
    act_arr = record.get("actual_arr_time")

    raw_sched_dep = record.get("raw_scheduled_dep_time")
    raw_est_dep = record.get("raw_estimated_dep_time")
    raw_act_dep = record.get("raw_actual_dep_time")

    raw_sched_arr = record.get("raw_scheduled_arr_time")
    raw_est_arr = record.get("raw_estimated_arr_time")
    raw_act_arr = record.get("raw_actual_arr_time")

    # Apply correction if event is in the audited estimated-in-actual inventory
    if eid in ESTIMATED_IN_ACTUAL_EVENTS:
        info = ESTIMATED_IN_ACTUAL_EVENTS[eid]
        target_fld = info["target_field"]
        correct_fld = info["correct_field"]

        if target_fld == "actual_dep_time":
            # Shift actual_dep_time to estimated_dep_time
            if act_dep and not est_dep:
                est_dep = act_dep
                raw_est_dep = raw_act_dep
            act_dep = None
            raw_act_dep = None
        elif target_fld == "actual_arr_time":
            # Shift actual_arr_time to estimated_arr_time
            if act_arr and not est_arr:
                est_arr = act_arr
                raw_est_arr = raw_act_arr
            act_arr = None
            raw_act_arr = None

    # Strict semantic enforcement: If record_nature is scheduled_service, it cannot have actual timestamps
    if nature in ("scheduled_service", "scheduled_timetable"):
        if act_dep:
            if not est_dep:
                est_dep = act_dep
                raw_est_dep = raw_act_dep
            act_dep = None
            raw_act_dep = None
        if act_arr:
            if not est_arr:
                est_arr = act_arr
                raw_est_arr = raw_act_arr
            act_arr = None
            raw_act_arr = None

    # Derive local operational dates
    sched_date = record.get("flight_date")
    actual_m_date = None
    estimated_m_date = None

    relevant_act_ts = act_dep if mtype == "departure" else act_arr
    if not relevant_act_ts:
        relevant_act_ts = act_dep or act_arr

    if relevant_act_ts:
        try:
            dt_utc = datetime.fromisoformat(relevant_act_ts.replace("Z", "+00:00"))
            actual_m_date = dt_utc.astimezone(DAMASCUS_TZ).date().isoformat()
        except Exception:
            actual_m_date = None

    relevant_est_ts = est_dep if mtype == "departure" else est_arr
    if not relevant_est_ts:
        relevant_est_ts = est_dep or est_arr

    if relevant_est_ts:
        try:
            dt_utc = datetime.fromisoformat(relevant_est_ts.replace("Z", "+00:00"))
            estimated_m_date = dt_utc.astimezone(DAMASCUS_TZ).date().isoformat()
        except Exception:
            estimated_m_date = None

    record["scheduled_dep_time"] = sched_dep
    record["estimated_dep_time"] = est_dep
    record["actual_dep_time"] = act_dep
    record["scheduled_arr_time"] = sched_arr
    record["estimated_arr_time"] = est_arr
    record["actual_arr_time"] = act_arr

    record["raw_scheduled_dep_time"] = raw_sched_dep
    record["raw_estimated_dep_time"] = raw_est_dep
    record["raw_actual_dep_time"] = raw_act_dep
    record["raw_scheduled_arr_time"] = raw_sched_arr
    record["raw_estimated_arr_time"] = raw_est_arr
    record["raw_actual_arr_time"] = raw_act_arr

    record["scheduled_flight_date"] = sched_date
    record["actual_movement_date"] = actual_m_date
    record["estimated_movement_date"] = estimated_m_date

    return record


import json
from pathlib import Path

MISLABELED_EVIDENCE_MAP: Dict[str, Dict[str, Any]] = {}
_audit_file = Path(__file__).parent.parent / "reports" / "v2_20_6_mislabeled_evidence_audit.json"
if _audit_file.exists():
    try:
        with open(_audit_file, "r", encoding="utf-8") as _f:
            _data = json.load(_f)
            MISLABELED_EVIDENCE_MAP = {r["evidence_id"]: r for r in _data}
    except Exception:
        pass


def correct_evidence_item(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classifies evidence items accurately:
    If evidence was derived from estimated timestamps rather than actual Mode-S
    telemetry or physical sensor contacts, reclassifies evidence_type to
    estimated_departure / estimated_arrival and marks is_estimated=True.
    Preserves original_evidence_type and provides visible correction history.
    """
    ev = dict(evidence)
    ev_id = ev.get("evidence_id")
    ev_type = ev.get("evidence_type", "")
    ev["original_evidence_type"] = ev.get("original_evidence_type") or ev_type

    if ev_id and ev_id in MISLABELED_EVIDENCE_MAP:
        info = MISLABELED_EVIDENCE_MAP[ev_id]
        ev["evidence_type"] = info["corrected_semantic_interpretation"]
        ev["is_estimated"] = True
        ev["original_raw_source_field"] = info["original_raw_source_field"]
        ev["raw_source_field"] = info["original_raw_source_field"]
        ev["correction_status"] = info["correction_status"]
        ev["correction_history"] = [
            {
                "action": "reclassify_semantic_interpretation",
                "original_classification": info["original_evidence_type"],
                "corrected_classification": info["corrected_semantic_interpretation"],
                "source_field": info["original_raw_source_field"],
                "mechanism": "read_time_semantic_correction",
                "ledger_status": "immutable_ledger_preserved",
                "reason": info["reason"]
            }
        ]
        return ev

    # Fallback heuristic if not in map
    raw_payload = str(ev.get("raw_payload", "") or "")
    is_est = False
    if "estimated" in raw_payload:
        if ev_type in ("adsb_takeoff", "commercial_takeoff"):
            ev["evidence_type"] = "estimated_departure"
            is_est = True
        elif ev_type in ("adsb_touchdown", "commercial_touchdown"):
            ev["evidence_type"] = "estimated_arrival"
            is_est = True

    ev["is_estimated"] = is_est
    if is_est:
        ev["correction_status"] = "derived_at_read_time_immutable_ledger_preserved"
        ev["correction_history"] = [
            {
                "action": "reclassify_semantic_interpretation",
                "original_classification": ev_type,
                "corrected_classification": ev["evidence_type"],
                "mechanism": "read_time_semantic_correction",
                "ledger_status": "immutable_ledger_preserved",
                "reason": "Derived from payload containing estimated timestamp rather than physical telemetry."
            }
        ]
    else:
        ev["correction_status"] = ev.get("ledger_status", "active")
        ev["correction_history"] = []

    return ev


def resolve_defensible_movement_identity(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluates candidate flight event records and resolves distinct real-world commercial movement legs,
    operating flight service callsigns, and ambiguous candidates.

    Multi-Factor Movement Identity Rules:
    1. Operational candidates must have record_nature == 'physical_movement' and a verified actual timestamp.
    2. Missing actual timestamps cannot establish an operational movement (classified as ambiguous).
    3. Multiple provider observations within 60m merge into 1 movement leg if airframe registrations do not conflict.
    4. Conflicting airframe registrations with overlapping/close timestamps are flagged as AMBIGUOUS (not merged).
    5. Two legs operating under the same callsign >180m apart split into 2 distinct resolved movement legs.
    6. Marketing codeshares matched to an operating flight do not inflate movement counts.
    7. Unmatched marketing codeshares are counted as distinct unresolved candidate movements in ambiguous_movement_identity_count.
    """
    operational_records = []
    codeshares = []
    unverified = []
    scheduled = []

    for r in records:
        nature = r.get("record_nature")
        if nature == "physical_movement":
            operational_records.append(r)
        elif nature == "marketing_codeshare":
            codeshares.append(r)
        elif nature == "unverified_movement":
            unverified.append(r)
        else:
            scheduled.append(r)

    # Group operational records by (airport_id, local_movement_date, movement_type, callsign)
    grouped_ops = defaultdict(list)
    ambiguous_count = 0
    resolved_movement_legs = []

    for r in operational_records:
        mtype = r.get("movement_type", "departure")
        callsign = (r.get("operating_flight_number") or r.get("flight_number") or "").strip().upper()
        apt = (r.get("airport_id") or "").strip().upper()

        act_ts = r.get("actual_dep_time") if mtype == "departure" else r.get("actual_arr_time")
        if not act_ts:
            act_ts = r.get("actual_dep_time") or r.get("actual_arr_time")

        if not act_ts:
            # Missing actual timestamp cannot establish movement
            ambiguous_count += 1
            continue

        try:
            dt = datetime.fromisoformat(act_ts.replace("Z", "+00:00"))
            local_date = dt.astimezone(DAMASCUS_TZ).date().isoformat()
        except Exception:
            local_date = r.get("flight_date")

        key = (apt, local_date, mtype, callsign)
        grouped_ops[key].append({
            "record": r,
            "parsed_dt": dt,
            "actual_ts": act_ts,
            "registration": (r.get("aircraft_registration") or "").strip().upper(),
            "carrier": (r.get("operating_carrier") or r.get("airline_name") or "").strip().lower(),
            "callsign": callsign,
            "airport_id": apt,
            "local_date": local_date,
            "movement_type": mtype,
        })

    resolved_movement_count = 0
    operating_callsigns = set()

    for (apt, local_date, mtype, callsign), cand_list in grouped_ops.items():
        if callsign:
            operating_callsigns.add(callsign)

        # Sort candidates deterministically by timestamp, event_id, and registration
        cand_list.sort(key=lambda x: (x["parsed_dt"], str(x["record"].get("event_id") or ""), x["registration"]))

        if len(cand_list) == 1:
            resolved_movement_count += 1
            resolved_movement_legs.append(cand_list[0])
            continue

        # Partition candidates into independent operational components separated by > 180m
        components = []
        current_comp = [cand_list[0]]
        for i in range(1, len(cand_list)):
            gap_m = (cand_list[i]["parsed_dt"] - cand_list[i-1]["parsed_dt"]).total_seconds() / 60.0
            if gap_m > 180.0:
                components.append(current_comp)
                current_comp = [cand_list[i]]
            else:
                current_comp.append(cand_list[i])
        components.append(current_comp)

        # Evaluate each operational component
        for comp in components:
            if len(comp) == 1:
                # Single candidate with > 180m separation from other legs
                resolved_movement_count += 1
                resolved_movement_legs.append(comp[0])
                continue

            # Check if any adjacent gap falls into the ambiguous window (60m < gap <= 180m)
            has_ambig_gap = False
            for i in range(1, len(comp)):
                gap_m = (comp[i]["parsed_dt"] - comp[i-1]["parsed_dt"]).total_seconds() / 60.0
                if gap_m > 60.0:
                    has_ambig_gap = True
                    break

            if has_ambig_gap:
                # Delta is between 60m and 180m: too large to merge, too small for distinct turnaround leg
                ambiguous_count += 1
                continue

            # All adjacent gaps <= 60m. Enforce complete linkage: total spread (diameter) <= 60m
            spread_m = (comp[-1]["parsed_dt"] - comp[0]["parsed_dt"]).total_seconds() / 60.0
            if spread_m > 60.0:
                # Transitive chaining hazard: pairwise spread exceeds 60m single-movement tolerance
                ambiguous_count += 1
                continue

            # Within 60m single-movement tolerance: check registration and carrier consistency
            regs = set(x["registration"] for x in comp if x["registration"])
            carriers = set(x["carrier"] for x in comp if x["carrier"])
            if len(regs) > 1:
                # Conflicting airframes in same departure slot cannot merge
                ambiguous_count += 1
            elif len(carriers) > 1:
                # Conflicting carriers
                ambiguous_count += 1
            else:
                # Merged multi-provider commercial corroboration of same physical movement
                resolved_movement_count += 1
                resolved_movement_legs.append(comp[0])

    # Match codeshares against resolved operational movement legs
    matched_codeshares = 0
    unmatched_codeshares_rows = 0
    unmatched_codeshare_candidates = set()

    op_keys = set((l["airport_id"], l["local_date"], l["movement_type"], l["callsign"]) for l in resolved_movement_legs)

    for cs in codeshares:
        cs_mtype = cs.get("movement_type", "departure")
        cs_apt = (cs.get("airport_id") or "").strip().upper()
        cs_date = cs.get("flight_date")
        target_op = (cs.get("operating_flight_number") or "").strip().upper()
        cs_num = (cs.get("flight_number") or "").strip().upper()

        target_key = (cs_apt, cs_date, cs_mtype, target_op)
        if target_op and target_key in op_keys:
            matched_codeshares += 1
        else:
            unmatched_codeshares_rows += 1
            # Distinct unresolved target candidate
            unmatched_codeshare_candidates.add((cs_apt, cs_date, cs_mtype, target_op or cs_num))

    total_ambiguous = ambiguous_count + len(unmatched_codeshare_candidates)

    return {
        "resolved_commercial_movement_count": resolved_movement_count,
        "unique_operating_flight_count": len(operating_callsigns),
        "ambiguous_movement_identity_count": total_ambiguous,
        "matched_codeshare_record_count": matched_codeshares,
        "unmatched_codeshare_record_count": unmatched_codeshares_rows,
        "unverified_record_count": len(unverified),
        "scheduled_service_count": len(scheduled),
        "source_record_count": len(records),
        "total_records": len(records),
    }

