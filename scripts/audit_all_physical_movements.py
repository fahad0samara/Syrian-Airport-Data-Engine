import sqlite3
import json
from pathlib import Path

def audit_all_physical_movements():
    conn = sqlite3.connect("data/damascus_airport.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
    SELECT event_id, airport_id, flight_number, movement_type, flight_date, flight_status,
           source, source_record_id, airline_name, operating_carrier, aircraft_model,
           aircraft_registration, aircraft_icao24,
           scheduled_dep_time, actual_dep_time, scheduled_arr_time, actual_arr_time,
           raw_scheduled_dep_time, raw_actual_dep_time, raw_scheduled_arr_time, raw_actual_arr_time,
           record_nature, quality_flags, raw_json
    FROM flight_events
    WHERE record_nature = 'physical_movement'
    ORDER BY airport_id, flight_date, movement_type, flight_number
    """)
    rows = [dict(r) for r in cur.fetchall()]
    total = len(rows)
    print(f"=== FULL CENSUS AUDIT: {total} PHYSICAL MOVEMENTS ===")

    stats = {
        "total": total,
        "by_airport": {},
        "by_direction": {},
        "by_status": {},
        "has_actual_timestamp": 0,
        "has_telemetry": 0, # has reg or hex or actual epoch
        "has_cross_source": 0,
        "evidence_type": {
            "direct_adsb_telemetry": 0,
            "multi_source_corroborated": 0,
            "official_status_and_time": 0,
            "commercial_feed_actual": 0
        },
        "unsupported_flagged": []
    }

    detailed_audit = []

    for r in rows:
        apt = r["airport_id"]
        stats["by_airport"][apt] = stats["by_airport"].get(apt, 0) + 1
        stats["by_direction"][r["movement_type"]] = stats["by_direction"].get(r["movement_type"], 0) + 1
        stats["by_status"][r["flight_status"]] = stats["by_status"].get(r["flight_status"], 0) + 1

        has_actual_time = bool(r["actual_dep_time"] or r["actual_arr_time"])
        if has_actual_time:
            stats["has_actual_timestamp"] += 1

        has_reg = bool(r["aircraft_registration"] and r["aircraft_registration"].strip())
        has_hex = bool(r["aircraft_icao24"] and r["aircraft_icao24"].strip())
        has_telemetry = has_reg or has_hex
        if has_telemetry:
            stats["has_telemetry"] += 1

        is_cross = "+" in r["source"]
        if is_cross:
            stats["has_cross_source"] += 1

        # Classify evidence tier
        if "flightradar24" in r["source"] and is_cross:
            ev_tier = "multi_source_corroborated"
        elif "flightradar24" in r["source"] and has_telemetry:
            ev_tier = "direct_adsb_telemetry"
        elif "damairport_official" in r["source"] or "alpairport_official" in r["source"]:
            ev_tier = "official_status_and_time"
        else:
            ev_tier = "commercial_feed_actual"
        stats["evidence_type"][ev_tier] += 1

        # Check for lack of evidence
        if not has_actual_time and r["flight_status"] not in ("landed", "departed"):
            stats["unsupported_flagged"].append(r["event_id"])

        detailed_audit.append({
            "event_id": r["event_id"],
            "airport_id": r["airport_id"],
            "flight_number": r["flight_number"],
            "operating_carrier": r["operating_carrier"] or r["airline_name"],
            "direction": r["movement_type"],
            "flight_date": r["flight_date"],
            "flight_status": r["flight_status"],
            "source": r["source"],
            "airframe_reg": r["aircraft_registration"],
            "airframe_hex": r["aircraft_icao24"],
            "actual_time": r["actual_dep_time"] if r["movement_type"] == "departure" else r["actual_arr_time"],
            "raw_actual_time": r["raw_actual_dep_time"] if r["movement_type"] == "departure" else r["raw_actual_arr_time"],
            "evidence_tier": ev_tier
        })

    print(f"By Airport: {stats['by_airport']}")
    print(f"By Direction: {stats['by_direction']}")
    print(f"By Status: {stats['by_status']}")
    print(f"Records with Actual Timestamp: {stats['has_actual_timestamp']}/{total} ({stats['has_actual_timestamp']/total*100:.1f}%)")
    print(f"Records with Airframe Telemetry (Reg/Hex): {stats['has_telemetry']}/{total} ({stats['has_telemetry']/total*100:.1f}%)")
    print(f"Records with Multi-Source Corroboration: {stats['has_cross_source']}/{total} ({stats['has_cross_source']/total*100:.1f}%)")
    print(f"Evidence Tiers: {stats['evidence_type']}")
    print(f"Unsupported Records Flagged: {len(stats['unsupported_flagged'])}")

    # Check the 1 DEZ record
    dez_records = [d for d in detailed_audit if d["airport_id"] == "DEZ"]
    print("\n--- DEIR EZ-ZOR (DEZ) PHYSICAL MOVEMENT ---")
    for d in dez_records:
        print(d)

    # Check sample ALP records
    alp_records = [d for d in detailed_audit if d["airport_id"] == "ALP"]
    print(f"\n--- ALEPPO (ALP) PHYSICAL MOVEMENTS ({len(alp_records)}) Sample 3 ---")
    for d in alp_records[:3]:
        print(d)

    # Check sample DAM records
    # Check direct ADS-B records
    adsb_records = [d for d in detailed_audit if d["evidence_tier"] == "direct_adsb_telemetry"]
    print(f"\n--- DIRECT ADS-B TELEMETRY RECORDS ({len(adsb_records)}) ---")
    for d in adsb_records:
        print(d)

    conn.close()

if __name__ == '__main__':
    audit_all_physical_movements()
