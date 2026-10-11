import sqlite3
import json
from pathlib import Path

def audit_coverage_and_database():
    conn = sqlite3.connect("data/damascus_airport.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("=" * 60)
    print("AUDIT: SOURCE_CHECKED_NO_RECORDS")
    print("=" * 60)
    cur.execute("""
        SELECT airport_id, count(1) as cnt, min(flight_date) as min_d, max(flight_date) as max_d,
               sources_checked, evidence_basis, notes
        FROM historical_coverage_matrix
        WHERE coverage_classification = 'source_checked_no_records'
        GROUP BY airport_id, sources_checked, evidence_basis, notes
    """)
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        print(f"Airport: {r['airport_id']} | Count: {r['cnt']} days ({r['min_d']} to {r['max_d']})")
        print(f"  Sources Checked: {r['sources_checked']}")
        print(f"  Evidence: {r['evidence_basis']}")
        print(f"  Notes: {r['notes']}\n")

    print("=" * 60)
    print("AUDIT: ALL CLASSIFICATIONS IN MATRIX")
    print("=" * 60)
    cur.execute("""
        SELECT coverage_classification, count(1) as cnt
        FROM historical_coverage_matrix
        GROUP BY coverage_classification
    """)
    for r in cur.fetchall():
        print(f"  {r['coverage_classification']}: {r['cnt']}")

    print("=" * 60)
    print("AUDIT: AIRPORTS IN DB vs CONFIGURED REGISTRY")
    print("=" * 60)
    cur.execute("SELECT airport_id, name, operational_status, airport_type, classification FROM airports")
    for r in cur.fetchall():
        print(f"  {r['airport_id']}: {r['name']} ({r['airport_type']}, {r['classification']}, {r['operational_status']})")

if __name__ == "__main__":
    audit_coverage_and_database()
