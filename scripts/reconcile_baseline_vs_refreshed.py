import json
from pathlib import Path
import sys

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.normalizer import (
    normalize_official_portal_flights,
    normalize_aviationstack,
    normalize_flightradar24,
    deduplicate_with_audit
)
from src.config import RAW_DATA_DIR

def load_dataset_from_snapshots(prefix: str):
    snap_dir = RAW_DATA_DIR / "snapshots"
    all_raw_events = []

    # 1. DAM official
    dam_f = sorted(snap_dir.glob(f"{prefix}*_damairport_official_flights_raw.json"))
    if dam_f:
        with open(dam_f[0], "r", encoding="utf-8") as f:
            d = json.load(f)
            flist = d.get("flights", []) if isinstance(d, dict) else d
            all_raw_events.extend(normalize_official_portal_flights(flist, "DAM"))

    # 2. ALP official
    alp_f = sorted(snap_dir.glob(f"{prefix}*_alpairport_official_flights_raw.json"))
    if alp_f:
        with open(alp_f[0], "r", encoding="utf-8") as f:
            d = json.load(f)
            flist = d.get("flights", []) if isinstance(d, dict) else d
            all_raw_events.extend(normalize_official_portal_flights(flist, "ALP"))

    # 3. AviationStack
    as_dep_f = RAW_DATA_DIR / "aviationstack_dam_departures_raw.json"
    as_arr_f = RAW_DATA_DIR / "aviationstack_dam_arrivals_raw.json"
    if as_dep_f.exists():
        with open(as_dep_f, "r", encoding="utf-8") as f:
            d = json.load(f)
            all_raw_events.extend(normalize_aviationstack(d.get("data", []), "departure", "DAM"))
    if as_arr_f.exists():
        with open(as_arr_f, "r", encoding="utf-8") as f:
            d = json.load(f)
            all_raw_events.extend(normalize_aviationstack(d.get("data", []), "arrival", "DAM"))

    # 4. Flightradar24
    for code, apt_id in [("dam", "DAM"), ("alp", "ALP"), ("dez", "DEZ")]:
        arr_snaps = sorted(snap_dir.glob(f"{prefix}*_flightradar24_{code}_arrivals_raw.json"))
        dep_snaps = sorted(snap_dir.glob(f"{prefix}*_flightradar24_{code}_departures_raw.json"))
        if arr_snaps:
            with open(arr_snaps[0], "r", encoding="utf-8") as f:
                d = json.load(f)
                all_raw_events.extend(normalize_flightradar24(d, "arrival", apt_id))
        if dep_snaps:
            with open(dep_snaps[0], "r", encoding="utf-8") as f:
                d = json.load(f)
                all_raw_events.extend(normalize_flightradar24(d, "departure", apt_id))

    canonical_events, audit_log, stats = deduplicate_with_audit(all_raw_events)
    return canonical_events, audit_log, stats

def reconcile():
    print("=== RECONCILING BASELINE (20261010_144553) VS REFRESHED (20261010_162853) ===")
    base_events, base_audit, base_stats = load_dataset_from_snapshots("20261010_1445")
    ref_events, ref_audit, ref_stats = load_dataset_from_snapshots("20261010_162")

    print(f"Baseline raw events: {base_stats['total_raw_events']} -> Canonical: {len(base_events)}")
    print(f"  Merges: {base_stats['merged_verified_count']}, Flagged: {base_stats['flagged_ambiguous_count']}")

    print(f"Refreshed raw events: {ref_stats['total_raw_events']} -> Canonical: {len(ref_events)}")
    print(f"  Merges: {ref_stats['merged_verified_count']}, Flagged: {ref_stats['flagged_ambiguous_count']}")

    base_map = {e["event_id"]: e for e in base_events}
    ref_map = {e["event_id"]: e for e in ref_events}

    added_ids = set(ref_map.keys()) - set(base_map.keys())
    removed_ids = set(base_map.keys()) - set(ref_map.keys())
    common_ids = set(base_map.keys()) & set(ref_map.keys())

    print(f"\nAdded canonical IDs in refreshed: {len(added_ids)}")
    for eid in sorted(added_ids):
        e = ref_map[eid]
        print(f"  + Added: {eid} | {e['airport_id']} | {e['flight_number']} | {e['movement_type']} | {e['flight_date']} | status={e['flight_status']} | src={e['source']}")

    print(f"\nRemoved canonical IDs in refreshed: {len(removed_ids)}")
    for eid in sorted(removed_ids):
        e = base_map[eid]
        print(f"  - Removed: {eid} | {e['airport_id']} | {e['flight_number']} | {e['movement_type']} | {e['flight_date']} | status={e['flight_status']} | src={e['source']}")

    changed_events = []
    for eid in common_ids:
        b = base_map[eid]
        r = ref_map[eid]
        diffs = {}
        for k in b.keys():
            if k == "raw_json": continue
            if b.get(k) != r.get(k):
                diffs[k] = (b.get(k), r.get(k))
        if diffs:
            changed_events.append((eid, diffs))

    print(f"\nCommon events with field changes: {len(changed_events)}")
    for eid, diffs in changed_events[:10]:
        print(f"  ~ Changed: {eid}: {diffs}")

    # Audit log differences (merges)
    print("\n=== RECONCILING MERGES (322 vs 319) ===")
    base_merges = [a for a in base_audit if a["resolution_status"] == "MERGED_VERIFIED"]
    ref_merges = [a for a in ref_audit if a["resolution_status"] == "MERGED_VERIFIED"]

    def merge_key(m):
        return (m["airport_id"], m["flight_number"], m["movement_type"], m["flight_date"], m["source_a"], m["source_b"])

    base_merge_keys = {merge_key(m): m for m in base_merges}
    ref_merge_keys = {merge_key(m): m for m in ref_merges}

    lost_merges = set(base_merge_keys.keys()) - set(ref_merge_keys.keys())
    new_merges = set(ref_merge_keys.keys()) - set(base_merge_keys.keys())

    print(f"Merges in baseline but not in refreshed: {len(lost_merges)}")
    for k in lost_merges:
        m = base_merge_keys[k]
        print(f"  - Lost merge: {k} (lead: {m['canonical_event_id']}, time diff: {m['time_difference_minutes']}m)")

    print(f"Merges in refreshed but not in baseline: {len(new_merges)}")
    for k in new_merges:
        m = ref_merge_keys[k]
        print(f"  + New merge: {k} (lead: {m['canonical_event_id']}, time diff: {m['time_difference_minutes']}m)")

if __name__ == '__main__':
    reconcile()
