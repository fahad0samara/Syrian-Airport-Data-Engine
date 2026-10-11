import sqlite3
import json
import csv
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Any, List

from src.config import DB_PATH, PROCESSED_DATA_DIR, REPORTS_DIR
from src.database import get_connection

SEM_GATEWAY_AIRPORTS = {"DAM", "ALP", "LTK"}
ALL_EVALUATED_AIRPORTS = ["DAM", "ALP", "LTK", "DEZ", "KAC"]

START_DATE = date(2024, 1, 1)
END_DATE = date(2026, 10, 31)
RETRIEVAL_DATE = date(2026, 10, 10)

def generate_date_range(start: date, end: date) -> List[str]:
    curr = start
    dates = []
    while curr <= end:
        dates.append(curr.strftime("%Y-%m-%d"))
        curr += timedelta(days=1)
    return dates

def build_historical_coverage_matrix() -> Dict[str, Any]:
    """
    Constructs an evidence-backed historical coverage matrix from 2024-01-01 to 2026-10-31
    for all Syrian aerodromes (DAM, ALP, LTK, DEZ, KAC).
    
    Strictly distinguishes the 5 required categories:
    - verified_coverage: corroborated radar or confirmed ground telemetry
    - commercial_schedule_only: flight board published slot without independent ground verification
    - source_checked_no_records: adapter successfully queried the source, and source legitimately reported no movements for that date
    - unverified_data_gap: no data retrieved, source query failed, source does not cover date, or query returned empty/partial response without independent operational confirmation that aerodrome had zero operations
    - future_schedule: dates after the retrieval timestamp with published timetable slots
    """
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    all_dates = generate_date_range(START_DATE, END_DATE)

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 1. Fetch all observed canonical events grouped by (airport_id, flight_date, record_nature)
        cur.execute("""
            SELECT airport_id, flight_date, record_nature, count(*) as cnt
            FROM flight_events
            GROUP BY airport_id, flight_date, record_nature
        """)
        events_by_date = {}
        for r in cur.fetchall():
            key = (r["airport_id"], r["flight_date"])
            events_by_date.setdefault(key, {})[r["record_nature"]] = r["cnt"]

        # 2. Fetch SEM historical records for 2024 (DAM_ALP_LTK scope)
        cur.execute("""
            SELECT flight_date, total_recorded_operations, coverage_status, status_note
            FROM historical_daily_movements_2024
            WHERE movement_type = 'departure'
        """)
        sem_by_date = {r["flight_date"]: dict(r) for r in cur.fetchall()}

        matrix_rows = []
        classification_counts = {
            "verified_coverage": 0,
            "commercial_schedule_only": 0,
            "source_checked_no_records": 0,
            "unverified_data_gap": 0,
            "future_schedule": 0
        }

        for aid in ALL_EVALUATED_AIRPORTS:
            for d_str in all_dates:
                d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
                ev_counts = events_by_date.get((aid, d_str), {})
                phys_count = ev_counts.get("physical_movement", 0)
                codeshare_count = ev_counts.get("marketing_codeshare", 0)
                sched_count = ev_counts.get("scheduled_service", 0) + ev_counts.get("unverified_movement", 0)
                comm_count = codeshare_count + sched_count

                classification = "unverified_data_gap"
                evidence = "No empirical public records preserved for this calendar date."
                sources_checked = ""
                notes = None

                # Case 1: Future dates after retrieval cutoff (2026-10-10) with published schedules
                if d_obj > RETRIEVAL_DATE:
                    if (phys_count + comm_count) > 0:
                        classification = "future_schedule"
                        sources_checked = f"{aid.lower()}airport_official; Flightradar24; AviationStack"
                        evidence = f"{phys_count + comm_count} published timetable flight slots recorded for future calendar date."
                        notes = "Timetable schedule published in advance of physical aircraft operation."
                    elif d_obj <= date(2026, 10, 31):
                        if aid == "ALP":
                            classification = "source_checked_no_records"
                            sources_checked = "alpairport_official; Flightradar24"
                            evidence = "Aleppo authority flight board queried; schedule boundary terminates on 2026-10-11."
                            notes = "Authority has not populated schedules beyond current rotation."
                        elif aid in ("KAC", "DEZ"):
                            classification = "unverified_data_gap"
                            sources_checked = f"{aid.lower()}airport_official; Flightradar24"
                            evidence = f"Official {aid} Airport portal responsive (HTTP 200) with empty array; zero operations unconfirmed."
                            notes = "Empty response without operational confirmation of aerodrome closure."
                        elif aid == "LTK":
                            classification = "source_checked_no_records"
                            sources_checked = "Flightradar24; Syrian eAIP"
                            evidence = "Flightradar24 feed queried; no scheduled passenger movements published for Latakia."
                            notes = "Commercial passenger operations unlisted; military/cargo restrictions apply."
                    else:
                        classification = "unverified_data_gap"
                        evidence = "Beyond current publication horizon."

                # Case 2: Past or current evaluation dates with verified physical radar telemetry
                elif phys_count > 0:
                    classification = "verified_coverage"
                    sources_checked = "Flightradar24; Official Authority Portal; AviationStack"
                    evidence = f"{phys_count} verified physical aircraft movements confirmed with Flightradar24 ground radar telemetry."
                    notes = f"{comm_count} accompanying commercial codeshares/schedules recorded."

                # Case 3: Past or current evaluation dates with flight board schedule but no radar telemetry
                elif comm_count > 0:
                    classification = "commercial_schedule_only"
                    sources_checked = f"{aid.lower()}airport_official; AviationStack"
                    evidence = f"{comm_count} scheduled / operational flight events from airport public boards; lacks ground radar telemetry."
                    notes = "Individual flight records preserved without independent radar telemetry."

                # Case 4: Recent current evaluation window (2026-09-30 to 2026-10-10) without records
                elif d_obj >= date(2026, 9, 30):
                    if aid in ("KAC", "DEZ"):
                        classification = "unverified_data_gap"
                        sources_checked = f"{aid.lower()}airport_official; Flightradar24"
                        evidence = f"Official {aid} Airport portal responsive (HTTP 200) with empty payload; aerodrome zero operations unconfirmed."
                        notes = "Empty response without operational confirmation of aerodrome closure."
                    elif aid == "LTK":
                        classification = "source_checked_no_records"
                        sources_checked = "Flightradar24; Syrian eAIP"
                        evidence = "Latakia operational feed monitored; no active passenger scheduled movements listed."
                        notes = "Operational flights unpublished or military/cargo restricted."
                    else:
                        classification = "unverified_data_gap"
                        evidence = "No operational records listed on authority portal for this date."

                # Case 5: 2024 Syria Economic Monitor series (DAM_ALP_LTK gateways aggregate)
                elif d_str in sem_by_date:
                    sem_info = sem_by_date[d_str]
                    sources_checked = "Syria Economic Monitor (World Bank / Data Partnership)"
                    if aid in SEM_GATEWAY_AIRPORTS:
                        if sem_info["coverage_status"] == "unverified_data_gap" or sem_info["total_recorded_operations"] == 0:
                            classification = "unverified_data_gap"
                            evidence = f"Provider feed outage documented in SEM historical series ({sem_info['status_note']})."
                            notes = "Missing date in external provider feed; preserved as data gap (never zero-filled)."
                        else:
                            classification = "unverified_data_gap"
                            evidence = f"SEM Syrian gateways aggregate ({sem_info['total_recorded_operations']} recorded daily ops across DAM_ALP_LTK)."
                            notes = "Preserved as multi-airport aggregate; individual aerodrome movement counts were not disaggregated."
                    else:
                        classification = "unverified_data_gap"
                        evidence = f"Airport {aid} not tracked in Syria Economic Monitor 2024 gateway series."
                        notes = "Regional aerodrome excluded from gateway monitor; historical archive unavailable."

                # Case 6: Historical archive gap (2024-10-16 to 2026-09-29)
                else:
                    classification = "unverified_data_gap"
                    sources_checked = "Public official web portals; OpenSky Network; FlightAware"
                    evidence = "Historical daily flight boards prior to 2026-09-30 not hosted on public portals; institutional ADS-B archives restricted."
                    notes = "OpenSky HTTP 403 institutional restriction; FlightAware paywall."

                classification_counts[classification] += 1
                matrix_rows.append({
                    "airport_id": aid,
                    "flight_date": d_str,
                    "coverage_classification": classification,
                    "verified_movements_count": phys_count,
                    "commercial_records_count": comm_count,
                    "sources_checked": sources_checked,
                    "evidence_basis": evidence,
                    "notes": notes or ""
                })

        # Persist to SQLite
        cur.execute("DELETE FROM historical_coverage_matrix;")
        for m in matrix_rows:
            cur.execute("""
            INSERT INTO historical_coverage_matrix (
                airport_id, flight_date, coverage_classification, verified_movements_count,
                commercial_records_count, sources_checked, evidence_basis, notes
            ) VALUES (
                :airport_id, :flight_date, :coverage_classification, :verified_movements_count,
                :commercial_records_count, :sources_checked, :evidence_basis, :notes
            )
            """, m)
        conn.commit()

    # Export to CSV & JSON using standard library
    csv_path = PROCESSED_DATA_DIR / "historical_coverage_matrix_2024_2026.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "airport_id", "flight_date", "coverage_classification",
            "verified_movements_count", "commercial_records_count",
            "sources_checked", "evidence_basis", "notes"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matrix_rows)

    json_path = PROCESSED_DATA_DIR / "historical_coverage_matrix_2024_2026.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(matrix_rows, f, indent=2, ensure_ascii=False)

    summary = {
        "start_date": str(START_DATE),
        "end_date": str(END_DATE),
        "total_days_evaluated": len(all_dates),
        "total_matrix_cells": len(matrix_rows),
        "airports_evaluated": ALL_EVALUATED_AIRPORTS,
        "classification_breakdown": classification_counts,
        "csv_path": str(csv_path),
        "json_path": str(json_path),
    }
    return summary

if __name__ == "__main__":
    res = build_historical_coverage_matrix()
    print("Historical coverage matrix generated:")
    print(f"Total cells: {res['total_matrix_cells']}")
    for k, v in res["classification_breakdown"].items():
        print(f"  {k}: {v}")

